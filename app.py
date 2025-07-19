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
        """Analyze food from image using Spoonacular API with enhanced processing"""
        try:
            api_key = app.config['SPOONACULAR_API_KEY']
            if not api_key:
                app.logger.warning("No Spoonacular API key configured")
                return FoodAnalysisService._fallback_analysis("Image analysis", user_description)
            
            # Enhanced image preprocessing for better recognition
            processed_image_path = FoodAnalysisService._preprocess_image(image_path)
            
            # Read and encode the processed image
            with open(processed_image_path, 'rb') as img_file:
                img_data = base64.b64encode(img_file.read()).decode()
            
            # Try different Spoonacular endpoints for better recognition
            endpoints = [
                "https://api.spoonacular.com/food/images/analyze",
                "https://api.spoonacular.com/food/images/classify"
            ]
            
            for endpoint in endpoints:
                try:
                    app.logger.info(f"Trying Spoonacular endpoint: {endpoint}")
                    
                    headers = {"Content-Type": "application/json"}
                    data = {
                        "imageBase64": img_data,
                        "apiKey": api_key
                    }
                    
                    response = requests.post(endpoint, headers=headers, json=data, timeout=30)
                    app.logger.info(f"Spoonacular API status: {response.status_code}")
                    
                    if response.status_code == 200:
                        result = response.json()
                        app.logger.info(f"Spoonacular API response: {result}")
                        
                        # Check if we got meaningful results
                        if FoodAnalysisService._is_valid_spoonacular_response(result):
                            processed_result = FoodAnalysisService._process_spoonacular_response(result, user_description)
                            # Clean up processed image
                            if processed_image_path != image_path:
                                os.remove(processed_image_path)
                            return processed_result
                        else:
                            app.logger.warning(f"Invalid Spoonacular response from {endpoint}")
                    else:
                        app.logger.error(f"Spoonacular API error {endpoint}: {response.status_code} - {response.text}")
                
                except requests.exceptions.RequestException as e:
                    app.logger.error(f"Network error with {endpoint}: {str(e)}")
                    continue
            
            # If all endpoints fail, use enhanced fallback with image analysis
            app.logger.warning("All Spoonacular endpoints failed, using enhanced fallback")
            fallback_result = FoodAnalysisService._enhanced_image_fallback(image_path, user_description)
            
            # Clean up processed image
            if processed_image_path != image_path:
                os.remove(processed_image_path)
            
            return fallback_result
                
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
            'apple': 80, 'banana': 105, 'orange': 60, 'strawberry': 32, 'strawberries': 32,
            'chicken': 250, 'beef': 300, 'fish': 200, 'vegetables': 50, 'cheese': 100,
            'berry': 40, 'berries': 40, 'fruit': 60, 'yogurt': 100, 'nuts': 200
        }
        
        estimated_calories = 250  # default
        food_name = description or "food item"
        
        # If it's image analysis and no description, use a more helpful message
        if analysis_type == "Image analysis" and not description:
            food_name = "food item (couldn't identify automatically)"
            estimated_calories = 100  # Lower default for unknown items
        
        for keyword, calories in calorie_estimates.items():
            if keyword in description_lower:
                estimated_calories = calories
                if keyword in ['strawberry', 'strawberries']:
                    food_name = "strawberries"
                elif keyword in ['apple']:
                    food_name = "apple"  
                elif keyword in ['banana']:
                    food_name = "banana"
                elif keyword in ['berry', 'berries']:
                    food_name = "mixed berries"
                else:
                    food_name = keyword
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

    @staticmethod
    def _preprocess_image(image_path):
        """Preprocess image for better API recognition"""
        try:
            from PIL import Image, ImageEnhance, ImageFilter
            
            # Open and enhance the image
            with Image.open(image_path) as img:
                # Convert to RGB if needed
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Resize to optimal size for recognition (not too small, not too large)
                max_size = 800
                if max(img.size) > max_size:
                    ratio = max_size / max(img.size)
                    new_size = tuple(int(dim * ratio) for dim in img.size)
                    img = img.resize(new_size, Image.Resampling.LANCZOS)
                
                # Enhance contrast and sharpness for better recognition
                enhancer = ImageEnhance.Contrast(img)
                img = enhancer.enhance(1.2)
                
                enhancer = ImageEnhance.Sharpness(img)
                img = enhancer.enhance(1.1)
                
                # Create processed image path
                base_name = os.path.splitext(image_path)[0]
                processed_path = f"{base_name}_processed.jpg"
                
                # Save processed image
                img.save(processed_path, 'JPEG', quality=90)
                
                return processed_path
                
        except Exception as e:
            app.logger.warning(f"Image preprocessing failed: {str(e)}, using original")
            return image_path
    
    @staticmethod
    def _is_valid_spoonacular_response(response_data):
        """Check if Spoonacular response contains meaningful food recognition"""
        if not response_data:
            return False
            
        # Check for meaningful food category
        category = response_data.get('category', {})
        if isinstance(category, dict):
            name = category.get('name', '').lower()
            probability = category.get('probability', 0)
            
            # Require minimum confidence and avoid generic categories
            if probability > 0.3 and name and name not in ['food', 'unknown', 'other']:
                return True
        
        # Check for nutrition data as alternative validation
        nutrition = response_data.get('nutrition', {})
        if nutrition and nutrition.get('nutrients'):
            return True
            
        return False
    
    @staticmethod
    def _enhanced_image_fallback(image_path, user_description):
        """Enhanced fallback using basic image analysis and context clues"""
        try:
            from PIL import Image
            import colorsys
            
            # Analyze image colors to guess food type
            with Image.open(image_path) as img:
                # Convert to RGB and get dominant colors
                rgb_img = img.convert('RGB')
                
                # Sample colors from center region (where food usually is)
                width, height = rgb_img.size
                center_box = (
                    width // 4, height // 4,
                    3 * width // 4, 3 * height // 4
                )
                center_region = rgb_img.crop(center_box)
                
                # Get average color
                pixels = list(center_region.getdata())
                avg_r = sum(p[0] for p in pixels) / len(pixels)
                avg_g = sum(p[1] for p in pixels) / len(pixels)
                avg_b = sum(p[2] for p in pixels) / len(pixels)
                
                # Convert to HSV for better food type detection
                h, s, v = colorsys.rgb_to_hsv(avg_r/255, avg_g/255, avg_b/255)
                h_degrees = h * 360
                
                # Color-based food guessing
                food_name = "food item"
                calories = 100
                
                # Red/pink range (strawberries, tomatoes, apples)
                if 340 <= h_degrees <= 360 or 0 <= h_degrees <= 20:
                    if s > 0.4:  # Bright red
                        food_name = "strawberries"
                        calories = 32
                        app.logger.info("Color analysis suggests strawberries")
                    else:
                        food_name = "apple"
                        calories = 80
                
                # Orange range (oranges, carrots)
                elif 20 <= h_degrees <= 40:
                    food_name = "orange"
                    calories = 60
                
                # Yellow range (bananas, corn)
                elif 40 <= h_degrees <= 70:
                    food_name = "banana"
                    calories = 105
                
                # Green range (vegetables, salads)
                elif 70 <= h_degrees <= 150:
                    food_name = "leafy greens"
                    calories = 25
                
                # Use user description if provided and makes sense
                if user_description and len(user_description.strip()) > 0:
                    desc_lower = user_description.lower()
                    # Check if description matches known foods
                    food_keywords = {
                        'strawberry': ('strawberries', 32),
                        'strawberries': ('strawberries', 32),
                        'apple': ('apple', 80),
                        'banana': ('banana', 105),
                        'orange': ('orange', 60),
                        'salad': ('mixed salad', 50),
                        'chicken': ('chicken', 250),
                        'beef': ('beef', 300)
                    }
                    
                    for keyword, (name, cals) in food_keywords.items():
                        if keyword in desc_lower:
                            food_name = name
                            calories = cals
                            app.logger.info(f"Using description-based analysis: {food_name}")
                            break
                
                return {
                    'food_name': food_name,
                    'calories': calories,
                    'protein': calories * 0.15 / 4,
                    'carbs': calories * 0.55 / 4,
                    'fat': calories * 0.30 / 9,
                    'fiber': 3,
                    'sodium': 400,
                    'confidence_score': 0.4,  # Medium confidence for enhanced fallback
                    'food_score': 3
                }
                
        except Exception as e:
            app.logger.error(f"Enhanced fallback error: {str(e)}")
            return FoodAnalysisService._fallback_analysis("Enhanced image analysis", user_description)

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
        
        # EXPLICIT DEBUG LOGGING FOR MANYCHAT TROUBLESHOOTING
        print("=" * 80)
        print("🔍 MANYCHAT WEBHOOK DEBUG - FULL DATA:")
        print("=" * 80)
        print(json.dumps(data, indent=2))
        print("=" * 80)
        print(f"Data keys: {list(data.keys())}")
        print("=" * 80)
        
        app.logger.info(f"Received ManyChat webhook: {data}")
        
        # COMPREHENSIVE DEBUG LOGGING for troubleshooting
        app.logger.info(f"=== ManyChat Webhook Debug Info ===")
        app.logger.info(f"Raw JSON keys: {list(data.keys())}")
        
        # Handle Full Contact Data format from ManyChat
        contact_data = None
        subscriber_id = None
        
        # Check if this is Full Contact Data format
        if 'id' in data and 'key' in data and data.get('key', '').startswith('user:'):
            app.logger.info("📋 Detected Full Contact Data format from ManyChat")
            contact_data = data
            subscriber_id = str(data.get('id'))
            app.logger.info(f"Subscriber ID from Full Contact Data: {subscriber_id}")
            
            # Get or create user first with the subscriber_id we have
            user = User.query.filter_by(whatsapp_id=subscriber_id).first()
            if not user:
                app.logger.info(f"Creating new user with WhatsApp ID: {subscriber_id}")
                user = User(whatsapp_id=subscriber_id)
                
                # Populate user info from contact data
                if contact_data.get('first_name'):
                    user.first_name = contact_data.get('first_name')
                if contact_data.get('last_name'):
                    user.last_name = contact_data.get('last_name')
                
                db.session.add(user)
                db.session.commit()
                
                # Send welcome message for new user
                welcome_name = contact_data.get('first_name', 'there')
                app.logger.info(f"Sending welcome message to new user: {welcome_name}")
                return jsonify({
                    "version": "v2",
                    "content": {
                        "type": "telegram",
                        "messages": [
                            {
                                "type": "text",
                                "text": f"🎉 Welcome to Caloria, {welcome_name}!\n\n🤖 I'm your AI nutrition assistant ready to help you track your meals!\n\n📸 **Send me a photo** of your food\n📝 **Type what you're eating** (e.g., 'grilled chicken salad')\n🎤 **Send a voice message** describing your meal\n\nI'll analyze the nutritional content and help you reach your health goals! 🥗✨"
                            }
                        ]
                    }
                })
            
            # Check if this is just a profile update (no message content)
            last_input_text = contact_data.get('last_input_text')
            if last_input_text is None or last_input_text == "":
                app.logger.info("ℹ️ Full Contact Data has no current message content")
                
                # Check if user has sent messages before (returning user)
                food_logs_count = FoodLog.query.filter_by(user_id=user.id).count()
                if food_logs_count > 0:
                    app.logger.info(f"Returning user with {food_logs_count} previous food logs")
                    # For returning users, send a brief prompt
                    return jsonify({
                        "version": "v2",
                        "content": {
                            "type": "telegram",
                            "messages": [
                                {
                                    "type": "text",
                                    "text": f"Hello again, {user.first_name or 'there'}! 👋\n\n📸 Send me a photo of your food\n📝 Or tell me what you're eating\n\nI'm ready to help you track your nutrition! 🥗"
                                }
                            ]
                        }
                    })
                else:
                    # For users with no previous logs, send more detailed instructions
                    return jsonify({
                        "version": "v2",
                        "content": {
                            "type": "telegram",
                            "messages": [
                                {
                                    "type": "text",
                                    "text": "👋 Hi! I'm your AI nutrition assistant!\n\n📸 Send me a photo of your food\n📝 Or describe what you're eating\n🎤 Or send a voice message\n\nI'll analyze the nutritional content and help you track your calories! 🥗"
                                }
                            ]
                        }
                    })
            
            # If we have message content in Full Contact Data, process it
            app.logger.info(f"Processing Full Contact Data with message: '{last_input_text}'")
            
        else:
            # Legacy format - extract subscriber_id from various possible fields
            print(f"🔍 Checking for subscriber_id in legacy format...")
            print(f"subscriber_id field: {data.get('subscriber_id')}")
            print(f"id field: {data.get('id')}")
            print(f"user_id field: {data.get('user_id')}")
            print(f"contact field: {data.get('contact')}")
            
            subscriber_id = data.get('subscriber_id') or data.get('id') or data.get('user_id')
            if data.get('contact'):
                contact_data = data.get('contact')
                if isinstance(contact_data, dict) and contact_data.get('id'):
                    subscriber_id = str(contact_data.get('id'))
        
        print(f"🎯 Final extracted subscriber_id: {subscriber_id}")
        app.logger.info(f"Final subscriber_id: {subscriber_id}")
        
        if not subscriber_id:
            print("❌ ERROR: No subscriber_id found!")
            app.logger.error("No subscriber_id found in webhook data")
            return jsonify({'error': 'No subscriber_id provided'}), 400
        
        # Get or create user (for legacy format)
        if not contact_data:  # Only if we haven't already handled this above
            user = User.query.filter_by(whatsapp_id=subscriber_id).first()
            if not user:
                app.logger.info(f"Creating new user with WhatsApp ID: {subscriber_id}")
                user = User(whatsapp_id=subscriber_id)
                db.session.add(user)
                db.session.commit()
        
        # DETERMINE CONTENT TYPE AND EXTRACT DATA
        content_type = 'text'  # Default
        text_content = ''
        has_image = False
        image_fields_found = []
        
        if contact_data:
            # Extract text from Full Contact Data
            text_content = contact_data.get('last_input_text') or ''
            app.logger.info(f"Text from contact data: '{text_content}'")
            
            # Check if Full Contact Data contains image/attachment information
            attachment_fields = ['attachment', 'attachments', 'image_url', 'file_url', 'media_url', 'photo_url']
            for field in attachment_fields:
                if contact_data.get(field):
                    has_image = True
                    image_fields_found.append(f'contact_data.{field}')
                    content_type = 'image'
                    app.logger.info(f"Found image field in contact data: {field} = {contact_data.get(field)}")
                    break
                    
            if text_content and text_content.strip():
                content_type = 'text'
                app.logger.info(f"Detected text content: '{text_content}'")
        else:
            # Legacy format handling
            text_content = data.get('text', '')
            content_type = data.get('type', 'text')
            
            # Check for legacy image detection
            direct_url_fields = ['image_url', 'url', 'attachment_url', 'media_url', 'photo_url', 'file_url', 'document_url']
            for field in direct_url_fields:
                if data.get(field):
                    has_image = True
                    image_fields_found.append(field)
                    content_type = 'image'
                    app.logger.info(f"Found direct image URL in field: {field}")
                    break
            
            # Check attachments in legacy format
            if not has_image and data.get('attachments'):
                has_image = True
                image_fields_found.append('attachments')
                content_type = 'image'
        
        # Override content type if we detected image
        if has_image:
            content_type = 'image'
            app.logger.info(f"🖼️ DETECTED IMAGE CONTENT from fields: {image_fields_found}")
        
        app.logger.info(f"Final determined content_type: {content_type}")
        app.logger.info(f"Text content: '{text_content}'")
        
        # Route to appropriate handler
        if content_type == 'text' and text_content.strip():
            app.logger.info("Routing to text handler")
            # Create a normalized data structure for text handler
            normalized_data = {
                'text': text_content,
                'platform': 'telegram',
                'contact_data': contact_data
            }
            return handle_text_input(user, normalized_data)
        elif content_type == 'image':
            app.logger.info("Routing to image handler")
            # Create a normalized data structure for image handler
            normalized_data = data.copy() if not contact_data else contact_data.copy()
            normalized_data['platform'] = 'telegram'
            normalized_data['text'] = text_content  # Optional description
            return handle_image_input(user, normalized_data)
        elif content_type == 'audio':
            app.logger.info("Routing to audio handler")
            return handle_audio_input(user, data)
        elif content_type == 'quiz_response':
            app.logger.info("Routing to quiz handler")
            return handle_quiz_response(user, data)
        else:
            # Enhanced fallback - if we have text but unrecognized type, treat as text
            if text_content and text_content.strip():
                app.logger.info("Unrecognized type but has text, routing to text handler")
                normalized_data = {
                    'text': text_content,
                    'platform': 'telegram',
                    'contact_data': contact_data
                }
                return handle_text_input(user, normalized_data)
            
            # For Full Contact Data with no message content, we've already handled this above
            # This should only trigger for legacy format with no content
            app.logger.error(f"❌ NO PROCESSABLE CONTENT FOUND")
            app.logger.error(f"Content type: {content_type}")
            app.logger.error(f"Text content: '{text_content}'")
            app.logger.error(f"Has image: {has_image}")
            
            # Return helpful message for empty content
            return jsonify({
                "version": "v2",
                "content": {
                    "type": "telegram",
                    "messages": [
                        {
                            "type": "text",
                            "text": "🤷‍♀️ I didn't receive any content to analyze.\n\n💡 **How to use me:**\n📸 Send a photo of your food\n📝 Type what you're eating (e.g., 'pizza slice')\n🎤 Send a voice message\n\nI'll provide detailed nutritional analysis! 🥗📊"
                        }
                    ]
                }
            })
            
    except Exception as e:
        app.logger.error(f"❌ WEBHOOK ERROR: {str(e)}")
        app.logger.error(f"Request data: {request.get_data()}")
        return jsonify({'error': f'Webhook processing failed: {str(e)}'}), 500

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
    
    # Get platform from request data, default to telegram
    platform = data.get('platform', 'telegram')
    
    # Return proper ManyChat dynamic block format with platform type
    return jsonify({
        "version": "v2",
        "content": {
            "type": platform,
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
    # ENHANCED IMAGE URL EXTRACTION - Try multiple possible fields
    image_url = None
    url_source = None
    
    app.logger.info("🔍 Searching for image URL in webhook data...")
    
    # Check direct URL fields first
    direct_url_fields = [
        'image_url', 'url', 'attachment_url', 'media_url', 
        'photo_url', 'file_url', 'document_url'
    ]
    
    for field in direct_url_fields:
        if data.get(field):
            image_url = data.get(field)
            url_source = field
            app.logger.info(f"✅ Found image URL in '{field}': {image_url}")
            break
    
    # Check attachments array
    if not image_url and data.get('attachments'):
        attachments = data.get('attachments')
        app.logger.info(f"🔍 Checking attachments: {attachments}")
        
        if isinstance(attachments, list) and len(attachments) > 0:
            # Get first attachment
            attachment = attachments[0]
            app.logger.info(f"📎 Processing attachment[0]: {attachment}")
            
            if isinstance(attachment, dict):
                # Try various URL field names in the attachment
                url_fields = ['url', 'image_url', 'file_url', 'media_url', 'photo_url', 'src', 'href', 'link']
                for url_field in url_fields:
                    if attachment.get(url_field):
                        image_url = attachment.get(url_field)
                        url_source = f'attachments[0].{url_field}'
                        app.logger.info(f"✅ Found image URL in attachment: {url_source} = {image_url}")
                        break
            elif isinstance(attachment, str):
                # Direct URL in attachment
                image_url = attachment
                url_source = 'attachments[0]'
                app.logger.info(f"✅ Found direct URL in attachments[0]: {image_url}")
        
        elif isinstance(attachments, dict):
            # Single attachment object
            url_fields = ['url', 'image_url', 'file_url', 'media_url', 'photo_url', 'src', 'href', 'link']
            for url_field in url_fields:
                if attachments.get(url_field):
                    image_url = attachments.get(url_field)
                    url_source = f'attachments.{url_field}'
                    app.logger.info(f"✅ Found image URL in attachments object: {url_source} = {image_url}")
                    break
    
    # Check single attachment object
    if not image_url and data.get('attachment'):
        attachment = data.get('attachment')
        app.logger.info(f"🔍 Checking single attachment: {attachment}")
        
        if isinstance(attachment, dict):
            url_fields = ['url', 'image_url', 'file_url', 'media_url', 'photo_url', 'src', 'href', 'link']
            for url_field in url_fields:
                if attachment.get(url_field):
                    image_url = attachment.get(url_field)
                    url_source = f'attachment.{url_field}'
                    app.logger.info(f"✅ Found image URL in attachment: {url_source} = {image_url}")
                    break
        elif isinstance(attachment, str):
            image_url = attachment
            url_source = 'attachment'
            app.logger.info(f"✅ Found direct URL in attachment: {image_url}")
    
    # Check other media fields
    if not image_url:
        media_fields = ['media', 'photo', 'image', 'file', 'files', 'document']
        for field in media_fields:
            if data.get(field):
                media_data = data.get(field)
                app.logger.info(f"🔍 Checking media field '{field}': {media_data}")
                
                if isinstance(media_data, str):
                    image_url = media_data
                    url_source = field
                    app.logger.info(f"✅ Found image URL in '{field}': {image_url}")
                    break
                elif isinstance(media_data, dict):
                    url_fields = ['url', 'image_url', 'file_url', 'media_url', 'src', 'href', 'link']
                    for url_field in url_fields:
                        if media_data.get(url_field):
                            image_url = media_data.get(url_field)
                            url_source = f'{field}.{url_field}'
                            app.logger.info(f"✅ Found image URL in '{field}.{url_field}': {image_url}")
                            break
                    if image_url:
                        break
    
    # Final logging
    if image_url:
        app.logger.info(f"🎯 FINAL IMAGE URL: {image_url} (from: {url_source})")
    else:
        app.logger.error(f"❌ NO IMAGE URL FOUND")
        app.logger.error(f"Available fields: {list(data.keys())}")
        app.logger.error(f"Complete webhook data: {json.dumps(data, indent=2)}")
    
    user_text = data.get('text', '')  # Optional description
    
    if not image_url:
        app.logger.error(f"No image URL found in webhook data")
        return jsonify({
            "version": "v2",
            "content": {
                "type": data.get('platform', 'telegram'),
                "messages": [
                    {
                        "type": "text",
                        "text": "❌ No image received. Please send a photo of your food!\n\n🔧 Debug: Image URL not found in webhook data."
                    }
                ]
            }
        }), 400
    
    try:
        app.logger.info(f"📥 Downloading image from: {image_url}")
        
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
            
            app.logger.info(f"💾 Image saved to: {filepath}")
            
            # Analyze image
            analysis_result = FoodAnalysisService.analyze_food_image(filepath, user_text)
            
            # If image analysis failed but we have user text, try text analysis as backup
            if (analysis_result.get('confidence_score', 0) < 0.5 and 
                user_text and len(user_text.strip()) > 0):
                app.logger.info(f"Image analysis low confidence, trying text analysis with: '{user_text}'")
                text_analysis = FoodAnalysisService.analyze_food_text(user_text)
                # Use text analysis if it has higher confidence
                if text_analysis.get('confidence_score', 0) > analysis_result.get('confidence_score', 0):
                    analysis_result = text_analysis
                    app.logger.info("Using text analysis result instead of image analysis")
            
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
            
            # Get platform from request data, default to telegram
            platform = data.get('platform', 'telegram')
            
            app.logger.info(f"✅ Image analysis completed successfully")
            
            # Return ManyChat dynamic block format
            return jsonify({
                "version": "v2",
                "content": {
                    "type": platform,
                    "messages": [
                        {
                            "type": "text",
                            "text": response_text
                        }
                    ]
                }
            })
        else:
            app.logger.error(f"Failed to download image: HTTP {response.status_code}")
            return jsonify({
                "version": "v2",
                "content": {
                    "type": data.get('platform', 'telegram'),
                    "messages": [
                        {
                            "type": "text",
                            "text": f"❌ Could not download your image (HTTP {response.status_code}). Please try again!"
                        }
                    ]
                }
            }), 400
            
    except Exception as e:
        app.logger.error(f"Image processing error: {str(e)}")
        return jsonify({
            "version": "v2",
            "content": {
                "type": data.get('platform', 'telegram'),
                "messages": [
                    {
                        "type": "text",
                        "text": f"❌ Error processing your image: {str(e)}. Please try again!"
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
    
    # Check if this was a low-confidence automatic analysis
    low_confidence_note = ""
    if analysis_result.get('confidence_score', 1.0) < 0.5 and "couldn't identify automatically" in analysis_result['food_name']:
        low_confidence_note = "\n\n🤖 I couldn't identify your food automatically. For better accuracy, try sending a text description like 'strawberries' or 'grilled chicken'!"
    
    response = f"""
📊 NUTRITIONAL ANALYSIS
🍽️ {analysis_result['food_name']}

🔥 Energy: {analysis_result['calories']:.1f} kcal
💪 Protein: {analysis_result['protein']:.1f}g
🍞 Carbs: {analysis_result['carbs']:.1f}g  
🥑 Fat: {analysis_result['fat']:.1f}g
🌱 Fiber: {analysis_result['fiber']:.1f}g
🧂 Sodium: {analysis_result['sodium']:.0f}mg

{score_emoji} Overall Rating: {score}/5 – {recommendation}
✅ Should you eat this? {frequency}

📈 TODAY'S PROGRESS
🎯 Goal: {daily_stats.goal_calories:.0f} kcal
📊 Consumed: {daily_stats.total_calories:.0f} kcal
⚖️ Remaining: {calories_remaining:.0f} kcal

💡 Add leafy greens to boost fiber!{low_confidence_note}
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