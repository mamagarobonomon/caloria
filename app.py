from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime, timedelta, date
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from apscheduler.schedulers.background import BackgroundScheduler
import os
import json
import requests
import logging
from PIL import Image
# import speech_recognition as sr  # Temporarily disabled for Python 3.13 compatibility
import io
import base64
import hashlib

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'caloria-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///caloria.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# API Keys (set as environment variables)
app.config['SPOONACULAR_API_KEY'] = os.environ.get('SPOONACULAR_API_KEY')
app.config['OPENAI_API_KEY'] = os.environ.get('OPENAI_API_KEY')
app.config['GOOGLE_CLOUD_API_KEY'] = os.environ.get('GOOGLE_CLOUD_API_KEY')
app.config['MANYCHAT_API_TOKEN'] = os.environ.get('MANYCHAT_API_TOKEN')

db = SQLAlchemy(app)
CORS(app)

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    whatsapp_id = db.Column(db.String(50), unique=True, nullable=False)
    first_name = db.Column(db.String(100), nullable=True)
    last_name = db.Column(db.String(100), nullable=True)
    weight = db.Column(db.Float, nullable=True)  # in kg
    height = db.Column(db.Float, nullable=True)  # in cm
    age = db.Column(db.Integer, nullable=True)
    gender = db.Column(db.String(10), nullable=True)  # 'male' or 'female'
    activity_level = db.Column(db.String(20), nullable=True)  # sedentary, lightly_active, moderately_active, very_active, extra_active
    goal = db.Column(db.String(20), nullable=True)  # lose_weight, maintain, gain_weight
    bmr = db.Column(db.Float, nullable=True)  # Basal Metabolic Rate
    daily_calorie_goal = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    quiz_completed = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    food_logs = db.relationship('FoodLog', backref='user', lazy=True, cascade='all, delete-orphan')
    daily_stats = db.relationship('DailyStats', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def calculate_bmr(self):
        """Calculate BMR using Harris-Benedict formula"""
        if not all([self.weight, self.height, self.age, self.gender]):
            return None
        
        if self.gender.lower() == 'male':
            bmr = 88.362 + (13.397 * self.weight) + (4.799 * self.height) - (5.677 * self.age)
        else:
            bmr = 447.593 + (9.247 * self.weight) + (3.098 * self.height) - (4.330 * self.age)
        
        return round(bmr, 2)
    
    def calculate_daily_calorie_goal(self):
        """Calculate daily calorie goal based on BMR, activity level, and goal"""
        if not self.bmr:
            return None
        
        # Activity multipliers
        activity_multipliers = {
            'sedentary': 1.2,
            'lightly_active': 1.375,
            'moderately_active': 1.55,
            'very_active': 1.725,
            'extra_active': 1.9
        }
        
        maintenance_calories = self.bmr * activity_multipliers.get(self.activity_level, 1.2)
        
        # Goal adjustments
        if self.goal == 'lose_weight':
            return round(maintenance_calories - 500, 2)  # 500 calorie deficit
        elif self.goal == 'gain_weight':
            return round(maintenance_calories + 500, 2)  # 500 calorie surplus
        else:
            return round(maintenance_calories, 2)  # maintenance
    
    def update_calculated_values(self):
        """Update BMR and daily calorie goal"""
        self.bmr = self.calculate_bmr()
        self.daily_calorie_goal = self.calculate_daily_calorie_goal()

class FoodLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    food_name = db.Column(db.String(200), nullable=False)
    calories = db.Column(db.Float, nullable=False)
    protein = db.Column(db.Float, default=0)  # in grams
    carbs = db.Column(db.Float, default=0)  # in grams
    fat = db.Column(db.Float, default=0)  # in grams
    fiber = db.Column(db.Float, default=0)  # in grams
    sodium = db.Column(db.Float, default=0)  # in mg
    portion_size = db.Column(db.String(100), nullable=True)
    food_score = db.Column(db.Integer, default=3)  # 1-5 scale
    analysis_method = db.Column(db.String(20), nullable=False)  # 'photo', 'text', 'voice'
    raw_input = db.Column(db.Text, nullable=True)  # Original input for reference
    image_path = db.Column(db.String(200), nullable=True)  # Path to uploaded image
    confidence_score = db.Column(db.Float, default=0.5)  # 0-1 confidence in analysis
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    @property
    def created_date(self):
        return self.created_at.date()

class DailyStats(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    total_calories = db.Column(db.Float, default=0)
    total_protein = db.Column(db.Float, default=0)
    total_carbs = db.Column(db.Float, default=0)
    total_fat = db.Column(db.Float, default=0)
    total_fiber = db.Column(db.Float, default=0)
    total_sodium = db.Column(db.Float, default=0)
    meals_logged = db.Column(db.Integer, default=0)
    goal_calories = db.Column(db.Float, default=0)
    calorie_difference = db.Column(db.Float, default=0)  # actual - goal
    recommendations_sent = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('user_id', 'date', name='unique_user_date'),)

class AdminUser(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# Food Analysis Services
class FoodAnalysisService:
    @staticmethod
    def analyze_food_image(image_path, user_description=None):
        """Analyze food from image using Spoonacular API"""
        try:
            api_key = app.config['SPOONACULAR_API_KEY']
            if not api_key:
                return FoodAnalysisService._fallback_analysis("Image analysis", user_description)
            
            # Read and encode image
            with open(image_path, 'rb') as img_file:
                img_data = base64.b64encode(img_file.read()).decode()
            
            # Use Spoonacular's image analysis endpoint
            url = "https://api.spoonacular.com/food/images/analyze"
            headers = {"Content-Type": "application/json"}
            data = {
                "imageBase64": img_data,
                "apiKey": api_key
            }
            
            response = requests.post(url, headers=headers, json=data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                return FoodAnalysisService._process_spoonacular_response(result, user_description)
            else:
                return FoodAnalysisService._fallback_analysis("Image analysis", user_description)
                
        except Exception as e:
            app.logger.error(f"Image analysis error: {str(e)}")
            return FoodAnalysisService._fallback_analysis("Image analysis", user_description)
    
    @staticmethod
    def analyze_food_text(text_description):
        """Analyze food from text description using Spoonacular API"""
        try:
            api_key = app.config['SPOONACULAR_API_KEY']
            if not api_key:
                return FoodAnalysisService._fallback_analysis("Text analysis", text_description)
            
            # Use Spoonacular's recipe/ingredient parsing
            url = f"https://api.spoonacular.com/recipes/parseIngredients"
            params = {
                "ingredientList": text_description,
                "servings": 1,
                "includeNutrition": True,
                "apiKey": api_key
            }
            
            response = requests.post(url, params=params, timeout=30)
            
            if response.status_code == 200:
                results = response.json()
                if results and len(results) > 0:
                    return FoodAnalysisService._process_ingredient_response(results[0], text_description)
            
            return FoodAnalysisService._fallback_analysis("Text analysis", text_description)
            
        except Exception as e:
            app.logger.error(f"Text analysis error: {str(e)}")
            return FoodAnalysisService._fallback_analysis("Text analysis", text_description)
    
    @staticmethod
    def analyze_food_voice(audio_file_path):
        """Analyze food from voice using speech-to-text then text analysis"""
        try:
            # Convert speech to text - temporarily disabled for Python 3.13
            # r = sr.Recognizer()
            # with sr.AudioFile(audio_file_path) as source:
            #     audio = r.record(source)
            #     text = r.recognize_google(audio)
            text = "Voice recognition temporarily disabled"
            
            app.logger.info(f"Voice transcription: {text}")
            
            # Analyze the transcribed text
            return FoodAnalysisService.analyze_food_text(text)
            
        except Exception as e:
            app.logger.error(f"Voice analysis error: {str(e)}")
            return FoodAnalysisService._fallback_analysis("Voice analysis", "audio file")
    
    @staticmethod
    def _process_spoonacular_response(spoonacular_data, user_description=None):
        """Process Spoonacular API response and extract nutrition data"""
        try:
            # Extract nutrition information from Spoonacular response
            nutrition = spoonacular_data.get('nutrition', {})
            nutrients = nutrition.get('nutrients', [])
            
            # Map nutrients by name
            nutrient_map = {}
            for nutrient in nutrients:
                nutrient_map[nutrient.get('name', '').lower()] = nutrient.get('amount', 0)
            
            food_name = spoonacular_data.get('category', {}).get('name', 'Unknown food')
            if user_description:
                food_name = user_description
            
            return {
                'food_name': food_name,
                'calories': nutrient_map.get('calories', 0),
                'protein': nutrient_map.get('protein', 0),
                'carbs': nutrient_map.get('carbohydrates', 0),
                'fat': nutrient_map.get('fat', 0),
                'fiber': nutrient_map.get('fiber', 0),
                'sodium': nutrient_map.get('sodium', 0),
                'confidence_score': spoonacular_data.get('confidence', 0.7),
                'food_score': FoodAnalysisService._calculate_food_score(
                    nutrient_map.get('calories', 0),
                    nutrient_map.get('protein', 0),
                    nutrient_map.get('fiber', 0),
                    nutrient_map.get('sodium', 0)
                )
            }
        except Exception as e:
            app.logger.error(f"Error processing Spoonacular response: {str(e)}")
            return FoodAnalysisService._fallback_analysis("API analysis", user_description)
    
    @staticmethod
    def _process_ingredient_response(ingredient_data, text_description):
        """Process Spoonacular ingredient parsing response"""
        try:
            nutrition = ingredient_data.get('nutrition', {})
            nutrients = nutrition.get('nutrients', [])
            
            # Map nutrients by name
            nutrient_map = {}
            for nutrient in nutrients:
                nutrient_map[nutrient.get('name', '').lower()] = nutrient.get('amount', 0)
            
            food_name = ingredient_data.get('name', text_description)
            
            return {
                'food_name': food_name,
                'calories': nutrient_map.get('calories', 0),
                'protein': nutrient_map.get('protein', 0),
                'carbs': nutrient_map.get('carbohydrates', 0),
                'fat': nutrient_map.get('fat', 0),
                'fiber': nutrient_map.get('fiber', 0),
                'sodium': nutrient_map.get('sodium', 0),
                'confidence_score': 0.8,
                'food_score': FoodAnalysisService._calculate_food_score(
                    nutrient_map.get('calories', 0),
                    nutrient_map.get('protein', 0),
                    nutrient_map.get('fiber', 0),
                    nutrient_map.get('sodium', 0)
                )
            }
        except Exception as e:
            app.logger.error(f"Error processing ingredient response: {str(e)}")
            return FoodAnalysisService._fallback_analysis("Ingredient analysis", text_description)
    
    @staticmethod
    def _fallback_analysis(analysis_type, description):
        """Fallback analysis when APIs fail"""
        # Simple keyword-based estimation
        description_lower = (description or "").lower()
        
        # Basic calorie estimates based on keywords
        calorie_estimates = {
            'soup': 200, 'salad': 150, 'pizza': 300, 'burger': 500,
            'sandwich': 350, 'pasta': 400, 'rice': 200, 'bread': 80,
            'apple': 80, 'banana': 105, 'chicken': 250, 'beef': 300,
            'fish': 200, 'vegetables': 50, 'cheese': 100
        }
        
        estimated_calories = 250  # default
        food_name = description or "Unknown food"
        
        for keyword, calories in calorie_estimates.items():
            if keyword in description_lower:
                estimated_calories = calories
                break
        
        return {
            'food_name': food_name,
            'calories': estimated_calories,
            'protein': estimated_calories * 0.15 / 4,  # rough estimate
            'carbs': estimated_calories * 0.55 / 4,
            'fat': estimated_calories * 0.30 / 9,
            'fiber': 3,
            'sodium': 400,
            'confidence_score': 0.3,  # low confidence for fallback
            'food_score': 3
        }
    
    @staticmethod
    def _calculate_food_score(calories, protein, fiber, sodium):
        """Calculate food health score (1-5 scale)"""
        score = 3  # baseline
        
        # High protein bonus
        if protein > 20:
            score += 1
        elif protein > 10:
            score += 0.5
        
        # High fiber bonus
        if fiber > 5:
            score += 1
        elif fiber > 3:
            score += 0.5
        
        # High sodium penalty
        if sodium > 800:
            score -= 1
        elif sodium > 500:
            score -= 0.5
        
        # High calorie penalty for single serving
        if calories > 600:
            score -= 1
        elif calories > 400:
            score -= 0.5
        
        return max(1, min(5, round(score)))

# Utility Services
class DailyStatsService:
    @staticmethod
    def update_daily_stats(user_id, food_log):
        """Update daily statistics when a new food log is added"""
        today = food_log.created_date
        
        # Get or create daily stats record
        daily_stats = DailyStats.query.filter_by(user_id=user_id, date=today).first()
        if not daily_stats:
            user = User.query.get(user_id)
            daily_stats = DailyStats(
                user_id=user_id,
                date=today,
                goal_calories=user.daily_calorie_goal or 2000
            )
            db.session.add(daily_stats)
        
        # Recalculate totals from all food logs for this day
        food_logs = FoodLog.query.filter_by(user_id=user_id).filter(
            FoodLog.created_at >= datetime.combine(today, datetime.min.time()),
            FoodLog.created_at < datetime.combine(today + timedelta(days=1), datetime.min.time())
        ).all()
        
        daily_stats.total_calories = sum(log.calories for log in food_logs)
        daily_stats.total_protein = sum(log.protein for log in food_logs)
        daily_stats.total_carbs = sum(log.carbs for log in food_logs)
        daily_stats.total_fat = sum(log.fat for log in food_logs)
        daily_stats.total_fiber = sum(log.fiber for log in food_logs)
        daily_stats.total_sodium = sum(log.sodium for log in food_logs)
        daily_stats.meals_logged = len(food_logs)
        daily_stats.calorie_difference = daily_stats.total_calories - daily_stats.goal_calories
        daily_stats.updated_at = datetime.utcnow()
        
        db.session.commit()
        return daily_stats
    
    @staticmethod
    def generate_recommendations(daily_stats):
        """Generate personalized recommendations based on daily intake"""
        recommendations = []
        
        # Calorie recommendations
        if daily_stats.calorie_difference < -200:
            recommendations.append("You're significantly under your calorie goal. Consider adding a healthy snack! 🍎")
        elif daily_stats.calorie_difference > 200:
            recommendations.append("You've exceeded your calorie goal. Try lighter options for your next meal. 🥗")
        else:
            recommendations.append("Great job staying close to your calorie goal! 🎯")
        
        # Protein recommendations
        protein_target = daily_stats.goal_calories * 0.15 / 4  # 15% of calories from protein
        if daily_stats.total_protein < protein_target * 0.7:
            recommendations.append("Try adding more protein sources like chicken, fish, or legumes. 💪")
        
        # Fiber recommendations
        if daily_stats.total_fiber < 20:
            recommendations.append("Add more fiber with leafy greens, beans, or whole grains! 🌱")
        
        # Sodium warning
        if daily_stats.total_sodium > 2000:
            recommendations.append("Watch your sodium intake - try fresh herbs instead of salt! 🧂")
        
        return recommendations

class ManyChatService:
    @staticmethod
    def send_message(subscriber_id, text, quick_replies=None):
        """Send message to user via ManyChat API"""
        try:
            api_token = app.config['MANYCHAT_API_TOKEN']
            if not api_token:
                app.logger.warning("ManyChat API token not configured")
                return False
            
            url = "https://api.manychat.com/fb/sending/sendContent"
            headers = {
                'Authorization': f'Bearer {api_token}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'subscriber_id': subscriber_id,
                'data': {
                    'version': 'v2',
                    'content': {
                        'messages': [{
                            'type': 'text',
                            'text': text
                        }]
                    }
                }
            }
            
            if quick_replies:
                payload['data']['content']['messages'][0]['quick_replies'] = quick_replies
            
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            return response.status_code == 200
            
        except Exception as e:
            app.logger.error(f"Error sending ManyChat message: {str(e)}")
            return False

# Routes

# Admin Panel Routes
@app.route('/admin')
def admin_login():
    if 'admin_id' in session:
        return redirect(url_for('admin_dashboard'))
    return render_template('admin/login.html')

@app.route('/admin/login', methods=['POST'])
def admin_login_post():
    username = request.form['username']
    password = request.form['password']
    
    admin = AdminUser.query.filter_by(username=username, is_active=True).first()
    
    if admin and admin.check_password(password):
        session['admin_id'] = admin.id
        return redirect(url_for('admin_dashboard'))
    else:
        flash('Invalid credentials', 'error')
        return redirect(url_for('admin_login'))

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_id', None)
    return redirect(url_for('admin_login'))

@app.route('/admin/dashboard')
def admin_dashboard():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))
    
    # Get statistics
    total_users = User.query.count()
    active_users = User.query.filter_by(is_active=True).count()
    completed_quizzes = User.query.filter_by(quiz_completed=True).count()
    total_food_logs = FoodLog.query.count()
    
    # Recent users
    recent_users = User.query.order_by(User.created_at.desc()).limit(10).all()
    
    # Recent food logs
    recent_logs = FoodLog.query.join(User).order_by(FoodLog.created_at.desc()).limit(20).all()
    
    return render_template('admin/dashboard.html', 
                         total_users=total_users,
                         active_users=active_users,
                         completed_quizzes=completed_quizzes,
                         total_food_logs=total_food_logs,
                         recent_users=recent_users,
                         recent_logs=recent_logs)

@app.route('/admin/users')
def admin_users():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))
    
    page = request.args.get('page', 1, type=int)
    users = User.query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False)
    
    return render_template('admin/users.html', users=users)

@app.route('/admin/users/<int:user_id>')
def admin_user_detail(user_id):
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))
    
    user = User.query.get_or_404(user_id)
    
    # Get recent food logs
    food_logs = FoodLog.query.filter_by(user_id=user_id).order_by(FoodLog.created_at.desc()).limit(50).all()
    
    # Get recent daily stats
    daily_stats = DailyStats.query.filter_by(user_id=user_id).order_by(DailyStats.date.desc()).limit(30).all()
    
    return render_template('admin/user_detail.html', user=user, food_logs=food_logs, daily_stats=daily_stats)

# ManyChat Webhook Routes
@app.route('/webhook/manychat', methods=['POST'])
def manychat_webhook():
    """Handle incoming webhooks from ManyChat"""
    try:
        data = request.get_json()
        app.logger.info(f"Received ManyChat webhook: {data}")
        
        # Extract user information
        subscriber_id = data.get('subscriber_id')
        if not subscriber_id:
            return jsonify({'error': 'No subscriber_id provided'}), 400
        
        # Get or create user
        user = User.query.filter_by(whatsapp_id=subscriber_id).first()
        if not user:
            user = User(whatsapp_id=subscriber_id)
            db.session.add(user)
            db.session.commit()
        
        # Handle different types of content
        content_type = data.get('type', 'text')  # Default to 'text' if missing
        
        # If type is empty string or None, default to text if we have text content
        if not content_type and data.get('text'):
            content_type = 'text'
        
        if content_type == 'text':
            return handle_text_input(user, data)
        elif content_type == 'image':
            return handle_image_input(user, data)
        elif content_type == 'audio':
            return handle_audio_input(user, data)
        elif content_type == 'quiz_response':
            return handle_quiz_response(user, data)
        else:
            # If we have text but unrecognized type, treat as text
            if data.get('text'):
                return handle_text_input(user, data)
            return jsonify({'message': 'Content type not supported'}), 400
            
    except Exception as e:
        app.logger.error(f"Webhook error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

def handle_text_input(user, data):
    """Handle text input from user"""
    text = data.get('text', '')
    
    # Analyze text for food content
    analysis_result = FoodAnalysisService.analyze_food_text(text)
    
    # Create food log
    food_log = FoodLog(
        user_id=user.id,
        food_name=analysis_result['food_name'],
        calories=analysis_result['calories'],
        protein=analysis_result['protein'],
        carbs=analysis_result['carbs'],
        fat=analysis_result['fat'],
        fiber=analysis_result['fiber'],
        sodium=analysis_result['sodium'],
        food_score=analysis_result['food_score'],
        analysis_method='text',
        raw_input=text,
        confidence_score=analysis_result['confidence_score']
    )
    
    db.session.add(food_log)
    db.session.commit()
    
    # Update daily stats
    daily_stats = DailyStatsService.update_daily_stats(user.id, food_log)
    
    # Format response message
    response_text = format_analysis_response(analysis_result, daily_stats)
    
    # Return ManyChat dynamic block format
    return jsonify({
        "version": "v2",
        "content": {
            "messages": [
                {
                    "type": "text",
                    "text": response_text
                }
            ]
        }
    })

def handle_image_input(user, data):
    """Handle image input from user"""
    image_url = data.get('image_url')
    user_text = data.get('text', '')  # Optional description
    
    if not image_url:
        return jsonify({
            "version": "v2",
            "content": {
                "messages": [
                    {
                        "type": "text",
                        "text": "❌ No image received. Please send a photo of your food!"
                    }
                ]
            }
        }), 400
    
    try:
        # Download and save image
        response = requests.get(image_url, timeout=30)
        if response.status_code == 200:
            # Generate unique filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"food_{user.id}_{timestamp}.jpg"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            # Save image
            with open(filepath, 'wb') as f:
                f.write(response.content)
            
            # Analyze image
            analysis_result = FoodAnalysisService.analyze_food_image(filepath, user_text)
            
            # Create food log
            food_log = FoodLog(
                user_id=user.id,
                food_name=analysis_result['food_name'],
                calories=analysis_result['calories'],
                protein=analysis_result['protein'],
                carbs=analysis_result['carbs'],
                fat=analysis_result['fat'],
                fiber=analysis_result['fiber'],
                sodium=analysis_result['sodium'],
                food_score=analysis_result['food_score'],
                analysis_method='photo',
                raw_input=user_text,
                image_path=filepath,
                confidence_score=analysis_result['confidence_score']
            )
            
            db.session.add(food_log)
            db.session.commit()
            
            # Update daily stats
            daily_stats = DailyStatsService.update_daily_stats(user.id, food_log)
            
            # Format response message
            response_text = format_analysis_response(analysis_result, daily_stats)
            
            # Return ManyChat dynamic block format
            return jsonify({
                "version": "v2",
                "content": {
                    "messages": [
                        {
                            "type": "text",
                            "text": response_text
                        }
                    ]
                }
            })
        else:
            return jsonify({
                "version": "v2",
                "content": {
                    "messages": [
                        {
                            "type": "text",
                            "text": "❌ Could not download your image. Please try again!"
                        }
                    ]
                }
            }), 400
            
    except Exception as e:
        app.logger.error(f"Image processing error: {str(e)}")
        return jsonify({
            "version": "v2",
            "content": {
                "messages": [
                    {
                        "type": "text",
                        "text": "❌ Error processing your image. Please try again!"
                    }
                ]
            }
        }), 500

def handle_audio_input(user, data):
    """Handle audio input from user"""
    audio_url = data.get('audio_url')
    
    if not audio_url:
        return jsonify({
            "version": "v2",
            "content": {
                "messages": [
                    {
                        "type": "text",
                        "text": "❌ No audio received. Please send a voice message!"
                    }
                ]
            }
        }), 400
    
    try:
        # Download audio file
        response = requests.get(audio_url, timeout=30)
        if response.status_code == 200:
            # Generate unique filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"voice_{user.id}_{timestamp}.wav"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            # Save audio file
            with open(filepath, 'wb') as f:
                f.write(response.content)
            
            # Analyze audio (speech to text + food analysis)
            analysis_result = FoodAnalysisService.analyze_food_voice(filepath)
            
            # Create food log
            food_log = FoodLog(
                user_id=user.id,
                food_name=analysis_result['food_name'],
                calories=analysis_result['calories'],
                protein=analysis_result['protein'],
                carbs=analysis_result['carbs'],
                fat=analysis_result['fat'],
                fiber=analysis_result['fiber'],
                sodium=analysis_result['sodium'],
                food_score=analysis_result['food_score'],
                analysis_method='voice',
                raw_input="Voice message",
                confidence_score=analysis_result['confidence_score']
            )
            
            db.session.add(food_log)
            db.session.commit()
            
            # Update daily stats
            daily_stats = DailyStatsService.update_daily_stats(user.id, food_log)
            
            # Format response message
            response_text = format_analysis_response(analysis_result, daily_stats)
            
            # Clean up audio file
            os.remove(filepath)
            
            # Return ManyChat dynamic block format
            return jsonify({
                "version": "v2",
                "content": {
                    "messages": [
                        {
                            "type": "text",
                            "text": response_text
                        }
                    ]
                }
            })
        else:
            return jsonify({
                "version": "v2",
                "content": {
                    "messages": [
                        {
                            "type": "text",
                            "text": "❌ Could not download your audio. Please try again!"
                        }
                    ]
                }
            }), 400
            
    except Exception as e:
        app.logger.error(f"Audio processing error: {str(e)}")
        return jsonify({
            "version": "v2",
            "content": {
                "messages": [
                    {
                        "type": "text",
                        "text": "❌ Error processing your audio. Please try again!"
                    }
                ]
            }
        }), 500

def handle_quiz_response(user, data):
    """Handle quiz responses from user"""
    quiz_data = data.get('quiz_data', {})
    
    # Update user profile with quiz responses
    if 'weight' in quiz_data:
        user.weight = float(quiz_data['weight'])
    if 'height' in quiz_data:
        user.height = float(quiz_data['height'])
    if 'age' in quiz_data:
        user.age = int(quiz_data['age'])
    if 'gender' in quiz_data:
        user.gender = quiz_data['gender']
    if 'activity_level' in quiz_data:
        user.activity_level = quiz_data['activity_level']
    if 'goal' in quiz_data:
        user.goal = quiz_data['goal']
    if 'first_name' in quiz_data:
        user.first_name = quiz_data['first_name']
    if 'last_name' in quiz_data:
        user.last_name = quiz_data['last_name']
    
    # Calculate BMR and daily calorie goal
    user.update_calculated_values()
    user.quiz_completed = True
    
    db.session.commit()
    
    # Generate welcome message with personalized goals
    welcome_message = f"""
🎉 Welcome to Caloria, {user.first_name}!

Your personalized profile:
📊 Daily Calorie Goal: {user.daily_calorie_goal:.0f} kcal
🎯 Goal: {user.goal.replace('_', ' ').title()}
💪 BMR: {user.bmr:.0f} kcal

Ready to start tracking your meals! Send me photos, descriptions, or voice messages of your food, and I'll help you stay on track! 📸🍽️
    """.strip()
    
    # Return ManyChat dynamic block format
    return jsonify({
        "version": "v2",
        "content": {
            "messages": [
                {
                    "type": "text",
                    "text": welcome_message
                }
            ]
        }
    })

def format_analysis_response(analysis_result, daily_stats):
    """Format the food analysis response message"""
    
    # Determine food score emoji and recommendation
    score = analysis_result['food_score']
    if score >= 4:
        score_emoji = "⭐"
        recommendation = "Excellent choice!"
        frequency = "Often"
    elif score >= 3:
        score_emoji = "👍"
        recommendation = "Good choice!"
        frequency = "Regularly"
    else:
        score_emoji = "⚠️"
        recommendation = "Consider healthier alternatives"
        frequency = "Occasionally"
    
    # Calculate calories remaining
    calories_remaining = daily_stats.goal_calories - daily_stats.total_calories
    
    response = f"""
📊 **Nutritional Analysis:**
🍽️ {analysis_result['food_name']}
🔥 **Energy:** {analysis_result['calories']:.1f} kcal
**Protein:** {analysis_result['protein']:.1f}g
**Carbs:** {analysis_result['carbs']:.1f}g  
**Fat:** {analysis_result['fat']:.1f}g
**Fiber:** {analysis_result['fiber']:.1f}g
**Sodium:** {analysis_result['sodium']:.0f}mg

{score_emoji} **Overall Rating:** {score}/5 – {recommendation}
✅ **Should you eat this?** {frequency}

📈 **Today's Progress:**
🎯 Goal: {daily_stats.goal_calories:.0f} kcal
📊 Consumed: {daily_stats.total_calories:.0f} kcal
⚖️ Remaining: {calories_remaining:.0f} kcal

🍃 Add leafy greens to boost fiber!
    """.strip()
    
    return response

# API Routes for external integrations
@app.route('/api/users', methods=['GET'])
def api_get_users():
    """API endpoint to get all users (for admin)"""
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    users = User.query.all()
    return jsonify([{
        'id': user.id,
        'whatsapp_id': user.whatsapp_id,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'quiz_completed': user.quiz_completed,
        'created_at': user.created_at.isoformat(),
        'is_active': user.is_active
    } for user in users])

@app.route('/api/users/<int:user_id>/stats', methods=['GET'])
def api_get_user_stats(user_id):
    """Get user's daily statistics"""
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    days = request.args.get('days', 30, type=int)
    start_date = date.today() - timedelta(days=days)
    
    stats = DailyStats.query.filter(
        DailyStats.user_id == user_id,
        DailyStats.date >= start_date
    ).order_by(DailyStats.date.desc()).all()
    
    return jsonify([{
        'date': stat.date.isoformat(),
        'total_calories': stat.total_calories,
        'goal_calories': stat.goal_calories,
        'total_protein': stat.total_protein,
        'total_carbs': stat.total_carbs,
        'total_fat': stat.total_fat,
        'meals_logged': stat.meals_logged,
        'calorie_difference': stat.calorie_difference
    } for stat in stats])

# Daily update scheduler
def send_daily_updates():
    """Send daily summary messages to all active users"""
    try:
        yesterday = date.today() - timedelta(days=1)
        
        # Get all users who logged food yesterday
        users_with_stats = db.session.query(User).join(DailyStats).filter(
            DailyStats.date == yesterday,
            User.is_active == True,
            User.quiz_completed == True
        ).all()
        
        for user in users_with_stats:
            daily_stats = DailyStats.query.filter_by(
                user_id=user.id, 
                date=yesterday
            ).first()
            
            if daily_stats and not daily_stats.recommendations_sent:
                # Generate recommendations
                recommendations = DailyStatsService.generate_recommendations(daily_stats)
                
                # Format daily summary message
                summary_message = f"""
📊 **Daily Summary for {yesterday.strftime('%B %d')}**

🔥 Calories: {daily_stats.total_calories:.0f}/{daily_stats.goal_calories:.0f} kcal
💪 Protein: {daily_stats.total_protein:.1f}g
🍞 Carbs: {daily_stats.total_carbs:.1f}g  
🥑 Fat: {daily_stats.total_fat:.1f}g
🌱 Fiber: {daily_stats.total_fiber:.1f}g
🍽️ Meals logged: {daily_stats.meals_logged}

📝 **Recommendations:**
{chr(10).join('• ' + rec for rec in recommendations)}

Keep up the great work! 💪✨
                """.strip()
                
                # Send message via ManyChat
                if ManyChatService.send_message(user.whatsapp_id, summary_message):
                    daily_stats.recommendations_sent = True
                    db.session.commit()
                
        app.logger.info(f"Sent daily updates to {len(users_with_stats)} users")
        
    except Exception as e:
        app.logger.error(f"Error sending daily updates: {str(e)}")

# Initialize scheduler
scheduler = BackgroundScheduler()
scheduler.add_job(
    func=send_daily_updates,
    trigger="cron", 
    hour=20,  # 8 PM
    minute=0
)

# Basic routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/privacy-policy')
def privacy_policy():
    return render_template('privacy_policy.html')

@app.route('/terms-and-conditions')
def terms_conditions():
    return render_template('terms_conditions.html')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        
        # Create default admin user if none exists
        if not AdminUser.query.first():
            admin = AdminUser(
                username='admin',
                email='admin@caloria.com'
            )
            admin.set_password('admin123')  # Change this in production!
            db.session.add(admin)
            db.session.commit()
            print("Created default admin user: admin/admin123")
    
    # Start scheduler
    if not scheduler.running:
        scheduler.start()
    
    # Use port 5001 to avoid conflicts with other projects
    port = int(os.getenv('PORT', 5001))
    app.run(debug=True, host='0.0.0.0', port=port) 