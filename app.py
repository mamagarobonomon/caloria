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

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()
from PIL import Image
import io
import base64
import hashlib
import tempfile
from urllib.parse import urlparse

# Google Cloud imports
try:
    from google.cloud import vision
    from google.cloud import speech
    from google.oauth2 import service_account
    GOOGLE_CLOUD_AVAILABLE = True
except ImportError:
    GOOGLE_CLOUD_AVAILABLE = False
    # Note: app.logger will be available after Flask app is created

app = Flask(__name__)

# Validate environment before configuration
def validate_environment():
    """Validate required environment variables"""
    required_vars = ['SECRET_KEY']
    missing = []
    
    for var in required_vars:
        if not os.environ.get(var):
            missing.append(var)
    
    if missing:
        print(f"⚠️ Missing environment variables: {missing}")
    
    # Check database configuration
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        print("⚠️ DATABASE_URL not set, using SQLite fallback")
    else:
        print(f"📊 Database configured: {db_url.split('://')[0].upper()}")
    
    # Validate production environment
    if os.environ.get('FLASK_ENV') == 'production' and db_url and 'sqlite' in db_url:
        print("🚨 WARNING: SQLite not recommended for production environment")
    
    return True

# Validate environment
validate_environment()

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
app.config['TELEGRAM_BOT_TOKEN'] = os.environ.get('TELEGRAM_BOT_TOKEN')

# Mercado Pago Configuration
app.config['MERCADO_PAGO_ACCESS_TOKEN'] = os.environ.get('MERCADO_PAGO_ACCESS_TOKEN')
app.config['MERCADO_PAGO_PUBLIC_KEY'] = os.environ.get('MERCADO_PAGO_PUBLIC_KEY') 
app.config['MERCADO_PAGO_WEBHOOK_SECRET'] = os.environ.get('MERCADO_PAGO_WEBHOOK_SECRET')
app.config['MERCADO_PAGO_PLAN_ID'] = os.environ.get('MERCADO_PAGO_PLAN_ID', '2c938084939f84900193a80bf21f01c8')
app.config['SUBSCRIPTION_TRIAL_DAYS'] = int(os.environ.get('SUBSCRIPTION_TRIAL_DAYS', '1'))
app.config['SUBSCRIPTION_PRICE_ARS'] = float(os.environ.get('SUBSCRIPTION_PRICE_ARS', '499900.0'))  # $4999.00 ARS (~$5 USD)

db = SQLAlchemy(app)
CORS(app)

# Database connection validation
def validate_database_connection():
    """Validate database connection on startup"""
    try:
        with app.app_context():
            # Test database connection (modern SQLAlchemy syntax)
            from sqlalchemy import text
            with db.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            
            # Log current configuration
            db_uri = app.config['SQLALCHEMY_DATABASE_URI']
            if 'sqlite' in db_uri.lower():
                print("⚠️  Using SQLite database")
            else:
                print(f"✅ Connected to: {db_uri.split('://')[0].upper()}")
                
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

# Validate database connection
if not validate_database_connection():
    print("🚨 CRITICAL: Database connection failed!")
    if os.environ.get('FLASK_ENV') == 'production':
        print("🚨 Production requires working database connection")
        # In production, you might want to: raise Exception("Database connection required")
    else:
        print("🔧 Development mode: continuing with potentially broken database")

# Custom Jinja filters
@app.template_filter('from_json')
def from_json_filter(value):
    """Parse JSON string in Jinja templates"""
    try:
        if value:
            return json.loads(value)
        return {}
    except (json.JSONDecodeError, TypeError):
        return {}

# Log Google Cloud availability
if not GOOGLE_CLOUD_AVAILABLE:
    print("⚠️ Google Cloud libraries not available. Install with: pip install google-cloud-vision google-cloud-speech")

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
    
    # NEW: Subscription fields
    subscription_tier = db.Column(db.String(20), default='trial_pending')  # trial_pending, trial_active, active, cancelled, expired
    subscription_status = db.Column(db.String(20), default='inactive')  # inactive, trial_active, active, cancelled, expired
    trial_start_time = db.Column(db.DateTime, nullable=True)
    trial_end_time = db.Column(db.DateTime, nullable=True)
    mercadopago_subscription_id = db.Column(db.String(100), nullable=True)
    cancellation_reason = db.Column(db.String(200), nullable=True)
    reengagement_scheduled = db.Column(db.DateTime, nullable=True)
    last_payment_date = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    food_logs = db.relationship('FoodLog', backref='user', lazy=True, cascade='all, delete-orphan')
    daily_stats = db.relationship('DailyStats', backref='user', lazy=True, cascade='all, delete-orphan')
    subscription = db.relationship('Subscription', backref='user', uselist=False, cascade='all, delete-orphan')
    payment_transactions = db.relationship('PaymentTransaction', backref='user', lazy=True, cascade='all, delete-orphan')
    trial_activities = db.relationship('TrialActivity', backref='user', lazy=True, cascade='all, delete-orphan')
    
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
    
    # NEW: Subscription helper methods
    def is_trial_active(self):
        """Check if user is in active trial period"""
        if not self.trial_start_time or not self.trial_end_time:
            return False
        return (self.subscription_status == 'trial_active' and 
                datetime.utcnow() < self.trial_end_time)
    
    def is_subscription_active(self):
        """Check if user has active subscription (trial or paid)"""
        return self.subscription_status in ['trial_active', 'active']
    
    def get_trial_time_remaining(self):
        """Get remaining trial time in hours"""
        if not self.is_trial_active():
            return 0
        remaining = self.trial_end_time - datetime.utcnow()
        return max(0, remaining.total_seconds() / 3600)  # Return hours
    
    def can_access_premium_features(self):
        """Check if user can access premium features"""
        return self.is_subscription_active()

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

class Subscription(db.Model):
    id = db.Column(db.String(50), primary_key=True)  # Mercado Pago subscription ID
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    plan_id = db.Column(db.String(50), nullable=False)  # Mercado Pago plan ID
    status = db.Column(db.String(20), nullable=False)  # active, cancelled, expired, pending
    payment_method = db.Column(db.String(50), nullable=True)
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(3), default='ARS')
    frequency = db.Column(db.String(20), default='monthly')  # monthly, yearly
    next_payment_date = db.Column(db.DateTime, nullable=True)
    trial_period_days = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    cancelled_at = db.Column(db.DateTime, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class PaymentTransaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    subscription_id = db.Column(db.String(50), db.ForeignKey('subscription.id'), nullable=True)
    mp_payment_id = db.Column(db.String(50), nullable=False)  # Mercado Pago payment ID
    mp_preference_id = db.Column(db.String(50), nullable=True)  # Mercado Pago preference ID
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(3), default='ARS')
    status = db.Column(db.String(20), nullable=False)  # approved, pending, rejected, cancelled
    payment_method = db.Column(db.String(50), nullable=True)
    transaction_type = db.Column(db.String(20), nullable=False)  # subscription, trial, one_time
    external_reference = db.Column(db.String(100), nullable=True)  # For tracking
    mp_response = db.Column(db.Text, nullable=True)  # Store full MP response for debugging
    payment_date = db.Column(db.DateTime, default=datetime.utcnow)
    processed_at = db.Column(db.DateTime, nullable=True)

class TrialActivity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    activity_type = db.Column(db.String(50), nullable=False)  # message_sent, food_analyzed, feature_used
    activity_data = db.Column(db.Text, nullable=True)  # JSON data about the activity
    hour_mark = db.Column(db.Integer, nullable=True)  # Hour into trial (0-23)
    engagement_score = db.Column(db.Float, default=0.0)  # Calculated engagement score
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ReengagementSchedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    campaign_type = db.Column(db.String(50), nullable=False)  # week_1, month_1, seasonal
    scheduled_date = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, sent, cancelled
    message_sent = db.Column(db.Boolean, default=False)
    response_received = db.Column(db.Boolean, default=False)
    conversion_result = db.Column(db.String(20), nullable=True)  # converted, declined, no_response
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    sent_at = db.Column(db.DateTime, nullable=True)

class SystemActivityLog(db.Model):
    """Log system events separate from food logs"""
    __tablename__ = 'system_activity_log'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    activity_type = db.Column(db.String(50), nullable=False)  # 'registration', 'quiz_completed', 'subscription_created', 'trial_started', 'trial_ended', 'subscription_cancelled'
    activity_data = db.Column(db.Text)  # JSON data with additional details
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    user = db.relationship('User', backref='system_activities')
    
    def __repr__(self):
        return f'<SystemActivityLog {self.activity_type} for User {self.user_id}>'
    
    @staticmethod
    def log_activity(user_id, activity_type, activity_data=None, ip_address=None, user_agent=None):
        """Log a system activity"""
        try:
            activity_data_json = json.dumps(activity_data) if activity_data else None
            
            activity = SystemActivityLog(
                user_id=user_id,
                activity_type=activity_type,
                activity_data=activity_data_json,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            db.session.add(activity)
            db.session.commit()
            
            app.logger.info(f"System activity logged: {activity_type} for user {user_id}")
            return activity
            
        except Exception as e:
            app.logger.error(f"Error logging system activity: {str(e)}")
            db.session.rollback()
            return None

# Mercado Pago and Subscription Services
class MercadoPagoService:
    @staticmethod
    def create_subscription_link(user, return_url=None, cancel_url=None):
        """Create Mercado Pago subscription link for user"""
        try:
            access_token = app.config['MERCADO_PAGO_ACCESS_TOKEN']
            plan_id = app.config['MERCADO_PAGO_PLAN_ID']
            
            if not access_token:
                app.logger.error("Mercado Pago access token not configured")
                return None
            
            # FIXED: Create subscription via API with webhook URL (required for subscriptions)
            # According to MP docs, webhooks for subscriptions must be configured during creation
            webhook_url = f"https://caloria.vip/webhook/mercadopago"
            
            # Create subscription via API instead of just constructing URL
            url = "https://api.mercadopago.com/preapproval"
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            subscription_data = {
                "preapproval_plan_id": plan_id,
                "payer_email": f"{user.whatsapp_id}@caloria.app",  # Required field
                "external_reference": user.whatsapp_id,
                "notification_url": webhook_url,  # CRITICAL: Webhook URL must be set here
                "back_url": return_url if return_url else f"https://caloria.vip/subscription-success?user={user.id}",
                "auto_recurring": {
                    "frequency": 1,
                    "frequency_type": "months",
                    "transaction_amount": app.config.get('SUBSCRIPTION_PRICE_ARS', 499900.0) / 100,  # Convert cents to pesos
                    "currency_id": "ARS"
                }
            }
            
            app.logger.info(f"Creating subscription via API for user {user.id}")
            response = requests.post(url, headers=headers, json=subscription_data, timeout=30)
            
            if response.status_code in [200, 201]:
                result = response.json()
                subscription_id = result.get('id')
                init_point = result.get('init_point')
                
                if init_point:
                    app.logger.info(f"Subscription created successfully: {subscription_id}")
                    
                    # Store subscription ID for tracking
                    user.mercadopago_subscription_id = subscription_id
                    user.subscription_status = 'trial_pending'
                    db.session.commit()
                    
                    return init_point
                else:
                    app.logger.error(f"No init_point in MP response: {result}")
                    return None
            else:
                app.logger.error(f"MP API error: {response.status_code} - {response.text}")
                return None
            
        except Exception as e:
            app.logger.error(f"Error creating Mercado Pago subscription: {str(e)}")
            return None
    
    @staticmethod
    def verify_webhook_signature(data, signature):
        """Verify Mercado Pago webhook signature for security"""
        try:
            webhook_secret = app.config['MERCADO_PAGO_WEBHOOK_SECRET']
            if not webhook_secret:
                app.logger.warning("Mercado Pago webhook secret not configured - skipping verification")
                return True  # Allow for now during development
            
            # TODO: Implement proper signature verification
            # For now, return True to allow webhooks during development
            return True
            
        except Exception as e:
            app.logger.error(f"Error verifying webhook signature: {str(e)}")
            return False
    
    @staticmethod
    def get_subscription_details(subscription_id):
        """Get subscription details from Mercado Pago API"""
        try:
            access_token = app.config['MERCADO_PAGO_ACCESS_TOKEN']
            if not access_token:
                return None
            
            # FIXED: Use correct endpoint according to MP documentation
            # For subscriptions: https://api.mercadopago.com/preapproval/search
            url = f"https://api.mercadopago.com/preapproval/{subscription_id}"
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                return response.json()
            else:
                app.logger.error(f"Error getting subscription details: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            app.logger.error(f"Error fetching subscription details: {str(e)}")
            return None

class SubscriptionService:
    @staticmethod
    def start_trial(user):
        """Start trial period for user"""
        try:
            now = datetime.utcnow()
            trial_days = app.config['SUBSCRIPTION_TRIAL_DAYS']
            
            user.subscription_status = 'trial_active'
            user.subscription_tier = 'premium'  # Give premium access during trial
            user.trial_start_time = now
            user.trial_end_time = now + timedelta(days=trial_days)
            
            db.session.commit()
            
            # Log trial activity
            SubscriptionService.log_trial_activity(user, 'trial_started', {
                'trial_duration_hours': trial_days * 24,
                'start_time': now.isoformat()
            })
            
            # Log trial start to system activity log
            SystemActivityLog.log_activity(
                user_id=user.id,
                activity_type='trial_started',
                activity_data={
                    'trial_duration_hours': trial_days * 24,
                    'start_time': now.isoformat(),
                    'end_time': user.trial_end_time.isoformat()
                }
            )
            
            app.logger.info(f"Started trial for user {user.id}, ends at {user.trial_end_time}")
            return True
            
        except Exception as e:
            app.logger.error(f"Error starting trial for user {user.id}: {str(e)}")
            db.session.rollback()
            return False
    
    @staticmethod
    def end_trial(user, reason='expired'):
        """End trial period for user"""
        try:
            user.subscription_status = 'expired' if reason == 'expired' else 'cancelled'
            user.subscription_tier = 'free'
            user.trial_end_time = datetime.utcnow()
            user.cancellation_reason = reason
            
            db.session.commit()
            
            # Log trial activity
            SubscriptionService.log_trial_activity(user, 'trial_ended', {
                'reason': reason,
                'end_time': datetime.utcnow().isoformat()
            })
            
            # Schedule re-engagement if cancelled
            if reason == 'cancelled':
                SubscriptionService.schedule_reengagement(user, days=7)
            
            app.logger.info(f"Ended trial for user {user.id}, reason: {reason}")
            return True
            
        except Exception as e:
            app.logger.error(f"Error ending trial for user {user.id}: {str(e)}")
            db.session.rollback()
            return False
    
    @staticmethod
    def activate_subscription(user, subscription_id):
        """Activate paid subscription for user"""
        try:
            user.subscription_status = 'active'
            user.subscription_tier = 'premium'
            user.mercadopago_subscription_id = subscription_id
            user.last_payment_date = datetime.utcnow()
            
            # Clear trial end time since now they're paid
            user.trial_end_time = None
            
            db.session.commit()
            
            app.logger.info(f"Activated subscription for user {user.id}, MP ID: {subscription_id}")
            return True
            
        except Exception as e:
            app.logger.error(f"Error activating subscription for user {user.id}: {str(e)}")
            db.session.rollback()
            return False
    
    @staticmethod
    def log_trial_activity(user, activity_type, activity_data=None):
        """Log trial activity for analytics"""
        try:
            if not user.is_trial_active():
                return  # Don't log if not in trial
            
            # Calculate hour mark in trial
            hour_mark = 0
            if user.trial_start_time:
                elapsed = datetime.utcnow() - user.trial_start_time
                hour_mark = int(elapsed.total_seconds() / 3600)
            
            activity = TrialActivity(
                user_id=user.id,
                activity_type=activity_type,
                activity_data=json.dumps(activity_data) if activity_data else None,
                hour_mark=hour_mark,
                engagement_score=SubscriptionService._calculate_engagement_score(activity_type)
            )
            
            db.session.add(activity)
            db.session.commit()
            
        except Exception as e:
            app.logger.error(f"Error logging trial activity: {str(e)}")
    
    @staticmethod
    def _calculate_engagement_score(activity_type):
        """Calculate engagement score for different activities"""
        engagement_scores = {
            'trial_started': 1.0,
            'food_analyzed': 2.0,
            'message_responded': 1.5,
            'feature_explored': 1.0,
            'goal_updated': 2.5,
            'trial_ended': 0.0
        }
        return engagement_scores.get(activity_type, 1.0)
    
    @staticmethod
    def schedule_reengagement(user, days=7):
        """Schedule re-engagement campaign for user"""
        try:
            scheduled_date = datetime.utcnow() + timedelta(days=days)
            
            # Check if already scheduled
            existing = ReengagementSchedule.query.filter_by(
                user_id=user.id, 
                campaign_type='week_1',
                status='pending'
            ).first()
            
            if existing:
                return  # Already scheduled
            
            reengagement = ReengagementSchedule(
                user_id=user.id,
                campaign_type='week_1',
                scheduled_date=scheduled_date
            )
            
            db.session.add(reengagement)
            user.reengagement_scheduled = scheduled_date
            db.session.commit()
            
            app.logger.info(f"Scheduled re-engagement for user {user.id} on {scheduled_date}")
            
        except Exception as e:
            app.logger.error(f"Error scheduling re-engagement: {str(e)}")
    
    @staticmethod
    def can_access_feature(user, feature):
        """Check if user can access specific feature"""
        if not user.is_subscription_active():
            return False
        
        # All premium features available during trial and paid subscription
        premium_features = [
            'unlimited_food_analysis',
            'detailed_nutrition_reports', 
            'meal_planning',
            'advanced_recommendations',
            'progress_tracking',
            'priority_support'
        ]
        
        return feature in premium_features

# Food Analysis Services
class FoodAnalysisService:
    @staticmethod
    def _get_google_cloud_credentials():
        """Get Google Cloud credentials from environment"""
        try:
            # Try to get credentials from GOOGLE_APPLICATION_CREDENTIALS file
            credentials_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
            if credentials_path and os.path.exists(credentials_path):
                return service_account.Credentials.from_service_account_file(credentials_path)
            
            # Try to get from GOOGLE_CLOUD_KEY_JSON environment variable
            key_json = os.environ.get('GOOGLE_CLOUD_KEY_JSON')
            if key_json:
                import json
                key_data = json.loads(key_json)
                return service_account.Credentials.from_service_account_info(key_data)
            
            # Fall back to default credentials (when running on Google Cloud)
            from google.auth import default
            credentials, project = default()
            return credentials
            
        except Exception as e:
            app.logger.error(f"Error getting Google Cloud credentials: {str(e)}")
            return None

    @staticmethod
    def analyze_food_image(image_path, user_description=None):
        """Analyze food from image using Google Cloud Vision API as primary, Spoonacular as fallback"""
        try:
            app.logger.info("🔍 Starting Google Cloud Vision API food analysis")
            
            # First try Google Cloud Vision API
            if GOOGLE_CLOUD_AVAILABLE:
                vision_result = FoodAnalysisService._analyze_image_with_google_vision(image_path, user_description)
                if vision_result and vision_result.get('confidence_score', 0) > 0.3:
                    app.logger.info("✅ Google Cloud Vision analysis successful")
                    return vision_result
                else:
                    app.logger.warning("⚠️ Google Cloud Vision analysis low confidence, trying Spoonacular fallback")
            
            # Fallback to Spoonacular API
            app.logger.info("🔄 Falling back to Spoonacular API")
            spoonacular_result = FoodAnalysisService._analyze_image_with_spoonacular(image_path, user_description)
            if spoonacular_result and spoonacular_result.get('confidence_score', 0) > 0.3:
                app.logger.info("✅ Spoonacular fallback successful")
                return spoonacular_result
            
            # Final fallback to enhanced image analysis
            app.logger.warning("⚠️ All APIs failed, using enhanced fallback")
            return FoodAnalysisService._enhanced_image_fallback(image_path, user_description)
                
        except Exception as e:
            app.logger.error(f"Image analysis error: {str(e)}")
            return FoodAnalysisService._fallback_analysis("Image analysis", user_description)

    @staticmethod
    def _analyze_image_with_google_vision(image_path, user_description=None):
        """Analyze image using Google Cloud Vision API"""
        try:
            credentials = FoodAnalysisService._get_google_cloud_credentials()
            if not credentials:
                app.logger.warning("No Google Cloud credentials available")
                return None
                
            # Initialize Vision API client
            client = vision.ImageAnnotatorClient(credentials=credentials)
            
            # Read image file
            with open(image_path, 'rb') as image_file:
                content = image_file.read()
            
            image = vision.Image(content=content)
            
            # Perform label detection
            response = client.label_detection(image=image)
            labels = response.label_annotations
            
            # Perform object localization (better for food items)
            objects = client.object_localization(image=image).localized_object_annotations
            
            # Process results to find food items
            food_items = []
            confidence_scores = []
            
            # Check object detection results first (more specific)
            for obj in objects:
                name = obj.name.lower()
                score = obj.score
                if any(food_word in name for food_word in ['food', 'fruit', 'vegetable', 'meat', 'dish', 'drink', 'beverage']):
                    food_items.append(name)
                    confidence_scores.append(score)
                    app.logger.info(f"📍 Object detected: {name} (confidence: {score:.2f})")
            
            # Check label detection results
            for label in labels:
                name = label.description.lower()
                score = label.score
                if any(food_word in name for food_word in ['food', 'fruit', 'vegetable', 'meat', 'dish', 'cuisine', 'ingredient', 'produce', 'snack', 'meal']):
                    food_items.append(name)
                    confidence_scores.append(score)
                    app.logger.info(f"🏷️ Label detected: {name} (confidence: {score:.2f})")
            
            if not food_items:
                app.logger.warning("No food items detected by Google Vision")
                return None
            
            # Use the highest confidence food item
            best_idx = confidence_scores.index(max(confidence_scores))
            detected_food = food_items[best_idx]
            confidence = confidence_scores[best_idx]
            
            # Use user description if provided, otherwise use detected food
            food_name = user_description if user_description and user_description.strip() else detected_food
            
            app.logger.info(f"🎯 Best food detection: {detected_food} -> using: {food_name}")
            
            # Get nutritional data from Spoonacular
            nutrition_data = FoodAnalysisService._get_nutrition_from_spoonacular(food_name)
            if nutrition_data:
                nutrition_data['confidence_score'] = min(confidence + 0.1, 0.9)  # Boost confidence slightly
                nutrition_data['food_name'] = food_name
                return nutrition_data
            else:
                # Generate estimated nutrition if Spoonacular fails
                return FoodAnalysisService._generate_nutrition_estimate(food_name, confidence)
                
        except Exception as e:
            app.logger.error(f"Google Cloud Vision error: {str(e)}")
            return None

    @staticmethod
    def _analyze_image_with_spoonacular(image_path, user_description=None):
        """Analyze image using Spoonacular API (fallback)"""
        try:
            api_key = app.config['SPOONACULAR_API_KEY']
            if not api_key:
                app.logger.warning("No Spoonacular API key configured")
                return None
            
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
            
            # Clean up processed image
            if processed_image_path != image_path and os.path.exists(processed_image_path):
                os.remove(processed_image_path)
                
            return None
                
        except Exception as e:
            app.logger.error(f"Spoonacular analysis error: {str(e)}")
            return None

    @staticmethod
    def _get_nutrition_from_spoonacular(food_name):
        """Get nutritional data from Spoonacular for identified food"""
        try:
            api_key = app.config['SPOONACULAR_API_KEY']
            if not api_key:
                return None
                
            # Use Spoonacular's recipe/ingredient parsing for nutrition
            url = f"https://api.spoonacular.com/recipes/parseIngredients"
            params = {
                "ingredientList": food_name,
                "servings": 1,
                "includeNutrition": True,
                "apiKey": api_key
            }
            
            response = requests.post(url, params=params, timeout=30)
            
            if response.status_code == 200:
                results = response.json()
                if results and len(results) > 0:
                    return FoodAnalysisService._process_ingredient_response(results[0], food_name)
            
            return None
            
        except Exception as e:
            app.logger.error(f"Spoonacular nutrition lookup error: {str(e)}")
            return None

    @staticmethod
    def _generate_nutrition_estimate(food_name, confidence):
        """Generate estimated nutrition when APIs fail"""
        # Enhanced keyword-based estimation
        food_lower = food_name.lower()
        
        # More comprehensive calorie estimates
        calorie_estimates = {
            'apple': 80, 'banana': 105, 'orange': 60, 'strawberry': 32, 'strawberries': 32,
            'grape': 60, 'grapes': 60, 'cherry': 50, 'cherries': 50, 'peach': 60, 'pear': 85,
            'pineapple': 50, 'watermelon': 30, 'cantaloupe': 35, 'honeydew': 36,
            'broccoli': 25, 'carrot': 25, 'spinach': 20, 'lettuce': 15, 'tomato': 20,
            'cucumber': 15, 'bell pepper': 25, 'onion': 40, 'garlic': 150, 'potato': 160,
            'sweet potato': 100, 'corn': 90, 'green beans': 35, 'peas': 80,
            'chicken': 250, 'beef': 300, 'pork': 280, 'fish': 200, 'salmon': 220,
            'tuna': 130, 'shrimp': 100, 'turkey': 200, 'bacon': 540, 'ham': 145,
            'egg': 70, 'cheese': 100, 'milk': 60, 'yogurt': 100, 'butter': 720,
            'bread': 80, 'rice': 200, 'pasta': 200, 'pizza': 300, 'burger': 500,
            'sandwich': 350, 'salad': 150, 'soup': 200, 'cookie': 150, 'cake': 350,
            'nuts': 200, 'almonds': 580, 'peanuts': 560, 'cashews': 550,
            'avocado': 160, 'olive oil': 880, 'coconut': 350
        }
        
        estimated_calories = 100  # default
        
        # Find best match
        for keyword, calories in calorie_estimates.items():
            if keyword in food_lower:
                estimated_calories = calories
                break
        
        return {
            'food_name': food_name,
            'calories': estimated_calories,
            'protein': estimated_calories * 0.15 / 4,  # 15% of calories from protein
            'carbs': estimated_calories * 0.55 / 4,    # 55% from carbs
            'fat': estimated_calories * 0.30 / 9,      # 30% from fat
            'fiber': 3,
            'sodium': 400,
            'confidence_score': max(confidence, 0.4),  # Minimum confidence
            'food_score': 3
        }

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
        """Analyze food from voice using Google Cloud Speech-to-Text then text analysis"""
        try:
            app.logger.info("🎤 Starting Google Cloud Speech-to-Text analysis")
            
            # Try Google Cloud Speech-to-Text first
            if GOOGLE_CLOUD_AVAILABLE:
                transcribed_text = FoodAnalysisService._transcribe_audio_with_google(audio_file_path)
                if transcribed_text:
                    app.logger.info(f"✅ Google Speech transcription: '{transcribed_text}'")
                    # Analyze the transcribed text
                    return FoodAnalysisService.analyze_food_text(transcribed_text)
            
            # Fallback to basic response
            app.logger.warning("⚠️ Google Cloud Speech not available")
            return FoodAnalysisService._fallback_analysis("Voice analysis", "voice message - please describe your food in text")
            
        except Exception as e:
            app.logger.error(f"Voice analysis error: {str(e)}")
            return FoodAnalysisService._fallback_analysis("Voice analysis", "audio file")

    @staticmethod
    def _transcribe_audio_with_google(audio_file_path):
        """Transcribe audio using Google Cloud Speech-to-Text"""
        try:
            credentials = FoodAnalysisService._get_google_cloud_credentials()
            if not credentials:
                app.logger.warning("No Google Cloud credentials available for speech")
                return None
                
            # Initialize Speech client
            client = speech.SpeechClient(credentials=credentials)
            
            # Read audio file
            with open(audio_file_path, 'rb') as audio_file:
                content = audio_file.read()
            
            # Configure recognition
            audio = speech.RecognitionAudio(content=content)
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.WEBM_OPUS,  # Try different encodings
                sample_rate_hertz=16000,
                language_code="en-US",
                alternative_language_codes=["en-GB", "es-ES", "fr-FR"],  # Multi-language support
                enable_automatic_punctuation=True,
                enable_word_confidence=True,
                model="latest_long"  # Best model for general use
            )
            
            # Perform recognition
            response = client.recognize(config=config, audio=audio)
            
            # Process results
            for result in response.results:
                if result.alternatives:
                    transcript = result.alternatives[0].transcript
                    confidence = result.alternatives[0].confidence
                    app.logger.info(f"🎯 Speech recognition: '{transcript}' (confidence: {confidence:.2f})")
                    return transcript
            
            app.logger.warning("No speech recognized by Google Cloud")
            return None
            
        except Exception as e:
            app.logger.error(f"Google Cloud Speech error: {str(e)}")
            # Try with different audio encoding
            try:
                # Alternative encoding attempt
                config = speech.RecognitionConfig(
                    encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                    sample_rate_hertz=44100,
                    language_code="en-US"
                )
                response = client.recognize(config=config, audio=audio)
                for result in response.results:
                    if result.alternatives:
                        return result.alternatives[0].transcript
            except:
                pass
            
            return None
    
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

# Subscription API Routes
@app.route('/api/create-subscription', methods=['POST'])
def create_subscription():
    """Create Mercado Pago subscription link for user"""
    try:
        data = request.get_json()
        subscriber_id = data.get('subscriber_id')
        plan_type = data.get('plan_type', 'premium')
        
        if not subscriber_id:
            return jsonify({'error': 'subscriber_id is required'}), 400
        
        user = User.query.filter_by(whatsapp_id=subscriber_id).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Check if user already has active subscription
        if user.is_subscription_active():
            return jsonify({'error': 'User already has active subscription'}), 400
        
        # Generate success and cancel URLs
        success_url = f"https://caloria.vip/subscription-success?user={user.id}&ref={user.whatsapp_id}"
        cancel_url = f"https://caloria.vip/subscription-cancel?user={user.id}"
        
        # Create Mercado Pago subscription link
        payment_link = MercadoPagoService.create_subscription_link(user, success_url, cancel_url)
        
        if not payment_link:
            return jsonify({'error': 'Failed to create payment link'}), 500
        
        # Update user status to indicate subscription is pending
        user.subscription_status = 'trial_pending'
        db.session.commit()
        
        return jsonify({
            'payment_link': payment_link,
            'plan_type': plan_type,
            'user_id': user.id,
            'trial_days': app.config['SUBSCRIPTION_TRIAL_DAYS'],
            'success': True
        })
        
    except Exception as e:
        app.logger.error(f"Error creating subscription: {str(e)}")
        return jsonify({'error': 'Failed to create subscription'}), 500

@app.route('/webhook/mercadopago', methods=['POST'])
def mercadopago_webhook():
    """Handle Mercado Pago webhooks for subscription events"""
    try:
        data = request.get_json()
        
        # Get webhook signature from headers
        signature = request.headers.get('x-signature', '')
        
        # Verify webhook authenticity
        if not MercadoPagoService.verify_webhook_signature(data, signature):
            app.logger.warning("Invalid Mercado Pago webhook signature")
            return jsonify({'error': 'Invalid signature'}), 401
        
        app.logger.info(f"Received Mercado Pago webhook: {data}")
        
        # FIXED: Handle correct MP webhook format according to documentation
        # MP sends: {"id": 12345, "live_mode": true, "type": "subscription_preapproval", 
        #           "action": "subscription.created", "data": {"id": "999999999"}}
        
        webhook_type = data.get('type')  # subscription_preapproval, subscription_authorized_payment, etc.
        action = data.get('action', '')  # subscription.created, subscription.updated, etc.
        webhook_data = data.get('data', {})
        resource_id = webhook_data.get('id')  # The actual subscription/payment ID
        
        app.logger.info(f"Webhook type: {webhook_type}, action: {action}, resource_id: {resource_id}")
        
        # Handle subscription-related webhooks
        if webhook_type == 'subscription_preapproval':
            result = handle_subscription_webhook(resource_id, action)
        elif webhook_type == 'subscription_authorized_payment':
            result = handle_subscription_payment_webhook(resource_id, action)
        else:
            app.logger.warning(f"Unknown webhook type: {webhook_type}")
            # Still return 200 to acknowledge receipt
            return jsonify({'status': 'ignored'})
        
        if result:
            # REQUIRED: Return HTTP 200 within 22 seconds according to MP docs
            return jsonify({'status': 'ok'})
        else:
            return jsonify({'status': 'error'}), 500
        
    except Exception as e:
        app.logger.error(f"Mercado Pago webhook error: {str(e)}")
        # Still return 200 to avoid retries for malformed requests
        return jsonify({'error': 'Webhook processing failed'}), 200

def handle_subscription_webhook(subscription_id, action):
    """Process subscription webhook events - FIXED format"""
    try:
        if not subscription_id:
            app.logger.error("No subscription ID in webhook data")
            return False
        
        app.logger.info(f"Processing subscription webhook: {subscription_id}, action: {action}")
        
        # Get subscription details from Mercado Pago using correct endpoint
        subscription_details = MercadoPagoService.get_subscription_details(subscription_id)
        if not subscription_details:
            app.logger.error(f"Could not get subscription details for {subscription_id}")
            return False
        
        # Extract relevant information from correct MP response format
        external_reference = subscription_details.get('external_reference')
        status = subscription_details.get('status')
        payer_email = subscription_details.get('payer_email', '')
        
        app.logger.info(f"Subscription {subscription_id} status: {status}, external_ref: {external_reference}")
        
        # Find user by external reference (WhatsApp ID)
        user = User.query.filter_by(whatsapp_id=external_reference).first()
        if not user:
            app.logger.error(f"User not found for external reference: {external_reference}")
            return False
        
        # Process based on subscription status and action
        if status == 'authorized' and 'created' in action:
            # Subscription approved - start trial
            app.logger.info(f"Starting trial for user {user.id}")
            SubscriptionService.start_trial(user)
            user.mercadopago_subscription_id = subscription_id
            db.session.commit()
            
            # Send trial started message via ManyChat
            send_trial_started_message(user)
            
        elif status == 'cancelled' or 'cancelled' in action:
            # Subscription cancelled
            app.logger.info(f"Subscription cancelled for user {user.id}")
            SubscriptionService.end_trial(user, reason='cancelled')
            
            # Send cancellation message
            send_subscription_cancelled_message(user)
            
        elif status == 'pending':
            # Payment pending
            app.logger.info(f"Subscription pending for user {user.id}")
            user.subscription_status = 'trial_pending'
            db.session.commit()
        
        return True
        
    except Exception as e:
        app.logger.error(f"Error handling subscription webhook: {str(e)}")
        return False

def handle_subscription_payment_webhook(payment_id, action):
    """Process subscription payment webhook events - NEW"""
    try:
        app.logger.info(f"Processing subscription payment webhook: {payment_id}, action: {action}")
        
        # Get payment details from correct endpoint
        access_token = app.config['MERCADO_PAGO_ACCESS_TOKEN']
        url = f"https://api.mercadopago.com/authorized_payments/{payment_id}"
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            payment_details = response.json()
            
            # Extract payment information
            preapproval_id = payment_details.get('preapproval_id')
            status = payment_details.get('status')
            amount = payment_details.get('transaction_amount', 0)
            
            app.logger.info(f"Payment {payment_id} for subscription {preapproval_id}: {status}")
            
            # Find user by subscription ID
            user = User.query.filter_by(mercadopago_subscription_id=preapproval_id).first()
            if user:
                if status == 'approved':
                    # Payment successful - activate subscription
                    SubscriptionService.activate_subscription(user, preapproval_id)
                    app.logger.info(f"Activated subscription for user {user.id}")
                elif status == 'rejected':
                    # Payment failed - end trial
                    SubscriptionService.end_trial(user, reason='payment_failed')
                    app.logger.info(f"Payment failed for user {user.id}")
                
                return True
            else:
                app.logger.error(f"User not found for subscription {preapproval_id}")
                return False
        else:
            app.logger.error(f"Error getting payment details: {response.status_code}")
            return False
        
    except Exception as e:
        app.logger.error(f"Error handling payment webhook: {str(e)}")
        return False

def handle_payment_webhook(webhook_data):
    """Process payment webhook events - DEPRECATED, kept for compatibility"""
    try:
        payment_id = webhook_data.get('id')
        if not payment_id:
            return False
        
        # Log the payment event for backwards compatibility
        app.logger.info(f"Legacy payment webhook received for payment {payment_id}")
        
        return True
        
    except Exception as e:
        app.logger.error(f"Error handling payment webhook: {str(e)}")
        return False

def send_trial_started_message(user):
    """Send trial started message via ManyChat"""
    try:
        trial_hours = user.get_trial_time_remaining()
        
        message = f"""
🎉 ¡Bienvenido a Caloria Premium!

Tu prueba gratuita de 24 horas ha comenzado.

✨ **Ahora tienes acceso a:**
📊 Análisis ilimitados de comidas
🎯 Recomendaciones personalizadas avanzadas
📈 Seguimiento detallado de progreso
💬 Soporte prioritario

⏰ **Tiempo restante:** {trial_hours:.1f} horas

🍎 **¡Empecemos!** Envía una foto de tu próxima comida para ver el análisis premium en acción.
        """.strip()
        
        # Send via ManyChat
        ManyChatService.send_message(user.whatsapp_id, message)
        
        # Log trial activity
        SubscriptionService.log_trial_activity(user, 'trial_started', {
            'message_sent': True,
            'trial_hours': trial_hours
        })
        
    except Exception as e:
        app.logger.error(f"Error sending trial started message: {str(e)}")

def send_subscription_cancelled_message(user):
    """Send subscription cancelled message via ManyChat"""
    try:
        message = """
😔 **Suscripción Cancelada**

Tu prueba gratuita ha sido cancelada y ya no tienes acceso a las funciones premium.

❌ **Ya no tienes acceso a:**
• Análisis ilimitados de comidas
• Recomendaciones avanzadas
• Seguimiento detallado

💭 **¿Cambio de opinión?**
Siempre puedes volver cuando estés listo. Te contactaremos en una semana con una oferta especial.

¡Gracias por probar Caloria! 👋
        """.strip()
        
        ManyChatService.send_message(user.whatsapp_id, message)
        
    except Exception as e:
        app.logger.error(f"Error sending cancellation message: {str(e)}")

@app.route('/subscription-success')
def subscription_success():
    """Handle successful subscription redirect from Mercado Pago"""
    try:
        user_id = request.args.get('user')
        external_ref = request.args.get('ref')
        
        if user_id:
            user = User.query.get(user_id)
            if user:
                app.logger.info(f"Subscription success redirect for user {user.id}")
                
                # Show success page
                return render_template('subscription_success.html', user=user)
        
        return render_template('subscription_success.html', user=None)
        
    except Exception as e:
        app.logger.error(f"Error in subscription success: {str(e)}")
        return render_template('subscription_success.html', user=None)

@app.route('/subscription-cancel')
def subscription_cancel():
    """Handle cancelled subscription redirect from Mercado Pago"""
    try:
        user_id = request.args.get('user')
        
        if user_id:
            user = User.query.get(user_id)
            if user:
                app.logger.info(f"Subscription cancelled by user {user.id}")
                return render_template('subscription_cancel.html', user=user)
        
        return render_template('subscription_cancel.html', user=None)
        
    except Exception as e:
        app.logger.error(f"Error in subscription cancel: {str(e)}")
        return render_template('subscription_cancel.html', user=None)

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
    
    # Get basic statistics
    total_users = User.query.count()
    active_users = User.query.filter_by(is_active=True).count()
    completed_quizzes = User.query.filter_by(quiz_completed=True).count()
    total_food_logs = FoodLog.query.count()
    
    # Get subscription statistics
    trial_pending_users = User.query.filter_by(subscription_tier='trial_pending').count()
    trial_active_users = User.query.filter_by(subscription_tier='trial_active').count()
    paid_subscribers = User.query.filter_by(subscription_tier='active').count()
    cancelled_subscriptions = User.query.filter_by(subscription_tier='cancelled').count()
    
    # Calculate conversion rates
    quiz_completion_rate = (completed_quizzes / total_users * 100) if total_users > 0 else 0
    trial_conversion_rate = (trial_active_users / completed_quizzes * 100) if completed_quizzes > 0 else 0
    paid_conversion_rate = (paid_subscribers / trial_active_users * 100) if trial_active_users > 0 else 0
    
    # Recent users
    recent_users = User.query.order_by(User.created_at.desc()).limit(10).all()
    
    # Recent food logs (actual food logs only)
    recent_food_logs = FoodLog.query.join(User).order_by(FoodLog.created_at.desc()).limit(15).all()
    
    # Recent system activities (registration, quiz, subscriptions)
    recent_activities = SystemActivityLog.query.join(User).order_by(SystemActivityLog.created_at.desc()).limit(15).all()
    
    # Revenue calculations (monthly)
    subscription_price = app.config.get('SUBSCRIPTION_PRICE_ARS', 499900.0) / 100  # Convert centavos to pesos
    monthly_revenue = paid_subscribers * subscription_price
    
    return render_template('admin/dashboard.html', 
                         # Basic stats
                         total_users=total_users,
                         active_users=active_users,
                         completed_quizzes=completed_quizzes,
                         total_food_logs=total_food_logs,
                         
                         # Subscription stats
                         trial_pending_users=trial_pending_users,
                         trial_active_users=trial_active_users,
                         paid_subscribers=paid_subscribers,
                         cancelled_subscriptions=cancelled_subscriptions,
                         
                         # Conversion rates
                         quiz_completion_rate=round(quiz_completion_rate, 1),
                         trial_conversion_rate=round(trial_conversion_rate, 1),
                         paid_conversion_rate=round(paid_conversion_rate, 1),
                         
                         # Revenue
                         monthly_revenue=monthly_revenue,
                         subscription_price=subscription_price,
                         
                         # Recent data
                         recent_users=recent_users,
                         recent_food_logs=recent_food_logs,
                         recent_activities=recent_activities)

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
        
        # Handle different ManyChat webhook formats
        contact_data = None
        subscriber_id = None
        
        # DETECT TELEGRAM FILE_ID FORMAT (External Request from ManyChat)
        if ('file_id' in data or 'telegram_file_id' in data):
            app.logger.info("📁 Detected Telegram file_id format from ManyChat External Request")
            print("📁 Detected Telegram file_id format from ManyChat External Request")
            
            # Extract file_id and subscriber info
            file_id = data.get('file_id') or data.get('telegram_file_id')
            subscriber_id = data.get('subscriber_id') or data.get('user_id') or data.get('id')
            
            if file_id and subscriber_id:
                subscriber_id = str(subscriber_id)
                app.logger.info(f"Processing Telegram file_id: {file_id} for subscriber: {subscriber_id}")
                print(f"Processing Telegram file_id: {file_id} for subscriber: {subscriber_id}")
                
                # Get Telegram Bot Token
                telegram_bot_token = app.config.get('TELEGRAM_BOT_TOKEN')
                if not telegram_bot_token:
                    app.logger.error("❌ TELEGRAM_BOT_TOKEN not configured")
                    return jsonify({
                        "version": "v2", 
                        "content": {
                            "type": "telegram",
                            "messages": [{
                                "type": "text",
                                "text": "❌ Telegram Bot Token not configured. Please contact support."
                            }]
                        }
                    }), 500
                
                # Get or create user
                user = User.query.filter_by(whatsapp_id=subscriber_id).first()
                if not user:
                    app.logger.info(f"Creating new user from file_id request: {subscriber_id}")
                    print(f"Creating new user from file_id request: {subscriber_id}")
                    user = User(whatsapp_id=subscriber_id)
                    
                    # Get user info if available
                    if data.get('first_name'):
                        user.first_name = data.get('first_name')
                    if data.get('last_name'):
                        user.last_name = data.get('last_name')
                    
                    db.session.add(user)
                    db.session.commit()
                
                # Download image using Telegram Bot API
                app.logger.info(f"📥 Downloading image via Telegram Bot API")
                print(f"📥 Downloading image via Telegram Bot API")
                
                image_filepath = download_telegram_image(file_id, telegram_bot_token)
                if not image_filepath:
                    app.logger.error("Failed to download image from Telegram")
                    return jsonify({
                        "version": "v2",
                        "content": {
                            "type": "telegram", 
                            "messages": [{
                                "type": "text",
                                "text": "❌ Failed to download your image. Please try again!"
                            }]
                        }
                    }), 400
                
                # Process the downloaded image
                app.logger.info(f"🖼️ Processing downloaded Telegram image: {image_filepath}")
                print(f"🖼️ Processing downloaded Telegram image: {image_filepath}")
                
                try:
                    # Get optional description text
                    user_text = data.get('message_text') or data.get('description') or ''
                    
                    # Analyze image
                    analysis_result = FoodAnalysisService.analyze_food_image(image_filepath, user_text)
                    
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
                        analysis_method='telegram_photo',
                        raw_input=user_text,
                        image_path=image_filepath,
                        confidence_score=analysis_result['confidence_score']
                    )
                    
                    db.session.add(food_log)
                    db.session.commit()
                    
                    # Update daily stats
                    daily_stats = DailyStatsService.update_daily_stats(user.id, food_log)
                    
                    # Format response message
                    response_text = format_analysis_response(analysis_result, daily_stats, user)
                    
                    app.logger.info(f"✅ Telegram image analysis completed successfully")
                    print(f"✅ Telegram image analysis completed successfully")
                    
                    # Return ManyChat response (no external_message_callback needed for External Request)
                    return jsonify({
                        "version": "v2",
                        "content": {
                            "type": "telegram",
                            "messages": [{
                                "type": "text",
                                "text": response_text + "\n\n📸 Send another photo or 📝 describe more food to continue tracking!"
                            }]
                        }
                    })
                    
                except Exception as e:
                    app.logger.error(f"Error processing Telegram image: {str(e)}")
                    return jsonify({
                        "version": "v2",
                        "content": {
                            "type": "telegram",
                            "messages": [{
                                "type": "text", 
                                "text": f"❌ Error analyzing your image: {str(e)}. Please try again!"
                            }]
                        }
                    }), 500
            else:
                missing_field = "file_id" if not file_id else "subscriber_id"
                app.logger.error(f"Missing {missing_field} in Telegram file_id request")
                return jsonify({'error': f'Missing {missing_field} in request'}), 400
        
        # DETECT EXTERNAL MESSAGE CALLBACK FORMAT
        elif ('subscriber_id' in data or 'attachment_url' in data or 'message_text' in data):
            app.logger.info("📨 Detected External Message Callback format from ManyChat")
            print("📨 Detected External Message Callback format from ManyChat")
            
            # Extract subscriber ID
            subscriber_id = data.get('subscriber_id') or data.get('user_id') or data.get('id')
            if subscriber_id:
                subscriber_id = str(subscriber_id)
                app.logger.info(f"Subscriber ID from External Message Callback: {subscriber_id}")
                print(f"Subscriber ID from External Message Callback: {subscriber_id}")
                
                # Get or create user
                user = User.query.filter_by(whatsapp_id=subscriber_id).first()
                if not user:
                    app.logger.info(f"Creating new user from External Message Callback: {subscriber_id}")
                    print(f"Creating new user from External Message Callback: {subscriber_id}")
                    user = User(whatsapp_id=subscriber_id)
                    
                    # Get user info if available
                    if data.get('first_name'):
                        user.first_name = data.get('first_name')
                    if data.get('last_name'):
                        user.last_name = data.get('last_name')
                    
                    db.session.add(user)
                    db.session.commit()
                    
                    # Log registration activity
                    SystemActivityLog.log_activity(
                        user_id=user.id,
                        activity_type='registration',
                        activity_data={'source': 'external_message_callback', 'platform': 'telegram'},
                        ip_address=request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR')),
                        user_agent=request.headers.get('User-Agent')
                    )
                
                # HANDLE EXTERNAL MESSAGE CALLBACK CONTENT
                message_text = data.get('message_text') or data.get('last_input_text') or ''
                attachment_url = data.get('attachment_url') or data.get('last_input_attachment_url')
                message_type = data.get('message_type') or data.get('last_input_type')
                
                app.logger.info(f"External Message Callback - Text: '{message_text}', Attachment: '{attachment_url}', Type: '{message_type}'")
                print(f"External Message Callback - Text: '{message_text}', Attachment: '{attachment_url}', Type: '{message_type}'")
                
                # Route based on content type
                if attachment_url and attachment_url.strip():
                    app.logger.info("🖼️ Processing image from External Message Callback")
                    print("🖼️ Processing image from External Message Callback")
                    # Create normalized data for image handler
                    normalized_data = {
                        'image_url': attachment_url,
                        'attachment_url': attachment_url,
                        'url': attachment_url,
                        'text': message_text,
                        'platform': 'telegram'
                    }
                    return handle_image_input(user, normalized_data)
                elif message_text and message_text.strip():
                    app.logger.info("📝 Processing text from External Message Callback")
                    print("📝 Processing text from External Message Callback")
                    # Create normalized data for text handler
                    normalized_data = {
                        'text': message_text,
                        'platform': 'telegram'
                    }
                    return handle_text_input(user, normalized_data)
                else:
                    app.logger.info("ℹ️ External Message Callback with no content, sending prompt")
                    print("ℹ️ External Message Callback with no content, sending prompt")
                    return jsonify({
                        "version": "v2",
                        "content": {
                            "type": "telegram",
                            "messages": [
                                {
                                    "type": "text",
                                    "text": f"Hi {user.first_name or 'there'}! 👋\n\n📸 Send me a photo of your food\n📝 Or tell me what you're eating\n\nI'm ready to analyze your nutrition! 🥗"
                                }
                            ]
                        }
                    })
            else:
                app.logger.error("No subscriber_id found in External Message Callback")
                print("No subscriber_id found in External Message Callback")
                return jsonify({'error': 'No subscriber_id provided in External Message Callback'}), 400
        
        # DETECT FULL CONTACT DATA FORMAT (for user profiles)
        elif 'id' in data and 'key' in data and data.get('key', '').startswith('user:'):
            app.logger.info("📋 Detected Full Contact Data format from ManyChat")
            print("📋 Detected Full Contact Data format from ManyChat")
            
            # COMPREHENSIVE DEBUG LOGGING FOR FULL CONTACT DATA
            app.logger.info("🔍 FULL CONTACT DATA ANALYSIS:")
            print("🔍 FULL CONTACT DATA ANALYSIS:")
            app.logger.info(f"All keys in Full Contact Data: {list(data.keys())}")
            print(f"All keys in Full Contact Data: {list(data.keys())}")
            for key, value in data.items():
                if key not in ['key', 'id', 'first_name', 'last_name', 'name']:  # Skip basic fields
                    app.logger.info(f"  📝 {key}: {value} (type: {type(value)})")
                    print(f"  📝 {key}: {value} (type: {type(value)})")
            
            contact_data = data
            subscriber_id = str(data.get('id'))
            app.logger.info(f"Subscriber ID from Full Contact Data: {subscriber_id}")
            print(f"Subscriber ID from Full Contact Data: {subscriber_id}")
            
            # Check if this is just a profile update (no message content)
            last_input_text = contact_data.get('last_input_text')
            
            # ENHANCED IMAGE DETECTION FOR FULL CONTACT DATA
            has_image = False
            image_fields_found = []
            
            # Check common image/attachment fields in Full Contact Data
            image_field_names = [
                'attachment', 'attachments', 'image_url', 'file_url', 'media_url', 
                'photo_url', 'document_url', 'media', 'file', 'image', 'photo',
                'last_input_type', 'content_type', 'message_type', 'input_type'
            ]
            
            app.logger.info("🔍 Checking for image indicators in Full Contact Data...")
            print("🔍 Checking for image indicators in Full Contact Data...")
            for field in image_field_names:
                if field in contact_data:
                    value = contact_data.get(field)
                    app.logger.info(f"  Found field '{field}': {value}")
                    print(f"  Found field '{field}': {value}")
                    
                    # Check if field indicates image content
                    if field in ['last_input_type', 'content_type', 'message_type', 'input_type']:
                        if value and ('image' in str(value).lower() or 'photo' in str(value).lower() or 'file' in str(value).lower()):
                            has_image = True
                            image_fields_found.append(f"{field}={value}")
                            app.logger.info(f"  ✅ DETECTED IMAGE from type field: {field}={value}")
                            print(f"  ✅ DETECTED IMAGE from type field: {field}={value}")
                    elif value and (isinstance(value, str) and ('http' in value or 'url' in value.lower())):
                        has_image = True
                        image_fields_found.append(f"{field}={value}")
                        app.logger.info(f"  ✅ DETECTED IMAGE from URL field: {field}={value}")
                        print(f"  ✅ DETECTED IMAGE from URL field: {field}={value}")
                    elif value and value != "":
                        # Non-empty value in a potential image field
                        has_image = True
                        image_fields_found.append(f"{field}={value}")
                        app.logger.info(f"  ✅ DETECTED IMAGE from non-empty field: {field}={value}")
                        print(f"  ✅ DETECTED IMAGE from non-empty field: {field}={value}")
            
            # Also check for custom fields that might contain image data
            custom_fields = contact_data.get('custom_fields', {})
            if custom_fields:
                app.logger.info(f"🔍 Checking custom_fields: {custom_fields}")
                print(f"🔍 Checking custom_fields: {custom_fields}")
                for field, value in custom_fields.items():
                    if value and ('http' in str(value) or 'image' in str(field).lower() or 'photo' in str(field).lower()):
                        has_image = True
                        image_fields_found.append(f"custom_fields.{field}={value}")
                        app.logger.info(f"  ✅ DETECTED IMAGE from custom field: {field}={value}")
                        print(f"  ✅ DETECTED IMAGE from custom field: {field}={value}")
            
            app.logger.info(f"📊 Image detection result: has_image={has_image}, fields={image_fields_found}")
            print(f"📊 Image detection result: has_image={has_image}, fields={image_fields_found}")
            
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
                
                # Send welcome message with External Message Callback for new user
                welcome_name = contact_data.get('first_name', 'there')
                app.logger.info(f"Sending welcome message with External Message Callback to new user: {welcome_name}")
                return jsonify({
                    "version": "v2",
                    "content": {
                        "type": "telegram",
                        "messages": [
                            {
                                "type": "text",
                                "text": f"🎉 Welcome to Caloria, {welcome_name}!\n\n🤖 I'm your AI nutrition assistant ready to help you track your meals!\n\n📸 **Send me a photo** of your food and I'll analyze it!"
                            }
                        ],
                        "external_message_callback": {
                            "url": "https://caloria.vip/webhook/manychat",
                            "method": "post",
                            "payload": {
                                "subscriber_id": "{{user_id}}",
                                "first_name": "{{first_name}}",
                                "last_name": "{{last_name}}",
                                "message_text": "{{last_input_text}}",
                                "attachment_url": "{{last_input_attachment_url}}",
                                "message_type": "{{last_input_type}}"
                            },
                            "timeout": 1800
                        }
                    }
                })
            
            # HANDLE IMAGE UPLOADS IN FULL CONTACT DATA
            if has_image:
                app.logger.info("🖼️ Processing image from Full Contact Data")
                # Route directly to image handler
                normalized_data = contact_data.copy()
                normalized_data['platform'] = 'telegram'
                normalized_data['text'] = last_input_text or ''  # Optional description
                return handle_image_input(user, normalized_data)
            
            # Check if this is just a profile update (no message content)
            if last_input_text is None or last_input_text == "":
                app.logger.info("ℹ️ Full Contact Data has no current message content")
                
                # Check if user has sent messages before (returning user)
                food_logs_count = FoodLog.query.filter_by(user_id=user.id).count()
                if food_logs_count > 0:
                    app.logger.info(f"Returning user with {food_logs_count} previous food logs - sending External Message Callback")
                    # For returning users, send a brief prompt with External Message Callback
                    return jsonify({
                        "version": "v2",
                        "content": {
                            "type": "telegram",
                            "messages": [
                                {
                                    "type": "text",
                                    "text": f"Hello again, {user.first_name or 'there'}! 👋\n\n📸 Send me a photo of your food\n📝 Or tell me what you're eating\n\nI'm ready to help you track your nutrition! 🥗"
                                }
                            ],
                            "external_message_callback": {
                                "url": "https://caloria.vip/webhook/manychat",
                                "method": "post",
                                "payload": {
                                    "subscriber_id": "{{user_id}}",
                                    "first_name": "{{first_name}}",
                                    "last_name": "{{last_name}}",
                                    "message_text": "{{last_input_text}}",
                                    "attachment_url": "{{last_input_attachment_url}}",
                                    "message_type": "{{last_input_type}}"
                                },
                                "timeout": 1800
                            }
                        }
                    })
                else:
                    # For users with no previous logs, send more detailed instructions with External Message Callback
                    return jsonify({
                        "version": "v2",
                        "content": {
                            "type": "telegram",
                            "messages": [
                                {
                                    "type": "text",
                                    "text": "👋 Hi! I'm your AI nutrition assistant!\n\n📸 Send me a photo of your food\n📝 Or describe what you're eating\n🎤 Or send a voice message\n\nI'll analyze the nutritional content and help you track your calories! 🥗"
                                }
                            ],
                            "external_message_callback": {
                                "url": "https://caloria.vip/webhook/manychat",
                                "method": "post",
                                "payload": {
                                    "subscriber_id": "{{user_id}}",
                                    "first_name": "{{first_name}}",
                                    "last_name": "{{last_name}}",
                                    "message_text": "{{last_input_text}}",
                                    "attachment_url": "{{last_input_attachment_url}}",
                                    "message_type": "{{last_input_type}}"
                                },
                                "timeout": 1800
                            }
                        }
                    })
            
            # If we have message content in Full Contact Data, process it
            app.logger.info(f"Processing Full Contact Data with text message: '{last_input_text}'")
            
        else:
            # Legacy format - extract subscriber_id from various possible fields
            subscriber_id = data.get('subscriber_id') or data.get('id') or data.get('user_id')
            if data.get('contact'):
                contact_data = data.get('contact')
                if isinstance(contact_data, dict) and contact_data.get('id'):
                    subscriber_id = str(contact_data.get('id'))
        
        app.logger.info(f"Final subscriber_id: {subscriber_id}")
        
        if not subscriber_id:
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
    response_text = format_analysis_response(analysis_result, daily_stats, user)
    
    # Get platform from request data, default to telegram
    platform = data.get('platform', 'telegram')
    
    # Return ManyChat dynamic block format with External Message Callback for continued interaction
    return jsonify({
        "version": "v2",
        "content": {
            "type": platform,
            "messages": [
                {
                    "type": "text",
                    "text": response_text + "\n\n📸 Send another photo or 📝 describe more food to continue tracking!"
                }
            ],
            "external_message_callback": {
                "url": "https://caloria.vip/webhook/manychat",
                "method": "post",
                "payload": {
                    "subscriber_id": "{{user_id}}",
                    "first_name": "{{first_name}}",
                    "last_name": "{{last_name}}",
                    "message_text": "{{last_input_text}}",
                    "attachment_url": "{{last_input_attachment_url}}",
                    "message_type": "{{last_input_type}}"
                },
                "timeout": 3600
            }
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
            response_text = format_analysis_response(analysis_result, daily_stats, user)
            
            # Get platform from request data, default to telegram
            platform = data.get('platform', 'telegram')
            
            app.logger.info(f"✅ Image analysis completed successfully")
            
            # Return ManyChat dynamic block format with External Message Callback for continued interaction
            return jsonify({
                "version": "v2",
                "content": {
                    "type": platform,
                    "messages": [
                        {
                            "type": "text",
                            "text": response_text + "\n\n📸 Send another photo or 📝 describe more food to continue tracking!"
                        }
                    ],
                    "external_message_callback": {
                        "url": "https://caloria.vip/webhook/manychat",
                        "method": "post",
                        "payload": {
                            "subscriber_id": "{{user_id}}",
                            "first_name": "{{first_name}}",
                            "last_name": "{{last_name}}",
                            "message_text": "{{last_input_text}}",
                            "attachment_url": "{{last_input_attachment_url}}",
                            "message_type": "{{last_input_type}}"
                        },
                        "timeout": 3600
                    }
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
            response_text = format_analysis_response(analysis_result, daily_stats, user)
            
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
    question_number = data.get('question_number', 0)
    
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
    
    # PHASE 2A: Add subscription mentions at questions 10-11
    subscription_teaser = ""
    if question_number in [10, 11]:
        subscription_teaser = f"""

💎 ¡Por cierto, {user.first_name or 'amigo'}!
Al finalizar este quiz tendrás acceso a nuestro plan PREMIUM:
✨ Análisis ilimitado de comidas
🎯 Recomendaciones personalizadas avanzadas  
📊 Seguimiento detallado de micronutrientes
⚡ ¡Prueba GRATIS por 24 horas completas!

🎉 ¡Solo quedan {15 - question_number} preguntas más!"""

    # Check if quiz is completed
    quiz_completed = data.get('quiz_completed', False) or question_number >= 15
    
    if quiz_completed:
        # Calculate BMR and daily calorie goal
        user.update_calculated_values()
        user.quiz_completed = True
        
        # PHASE 2A: Create subscription at quiz completion
        app.logger.info(f"Quiz completed for user {user.id}, creating subscription...")
        
        # Log quiz completion activity to both trial activity and system activity log
        SubscriptionService.log_trial_activity(user, 'quiz_completed', {
            'question_count': 15,
            'completion_time': datetime.utcnow().isoformat()
        })
        
        # Log quiz completion to system activity log
        SystemActivityLog.log_activity(
            user_id=user.id,
            activity_type='quiz_completed',
            activity_data={
                'goal': user.goal,
                'bmr': user.bmr,
                'daily_calorie_goal': user.daily_calorie_goal,
                'completion_time': datetime.utcnow().isoformat()
            }
        )
        
        # Create Mercado Pago subscription
        subscription_link = MercadoPagoService.create_subscription_link(
            user,
            return_url=f"https://caloria.vip/subscription-success?user={user.id}",
            cancel_url=f"https://caloria.vip/subscription-cancel?user={user.id}"
        )
        
        # Log subscription creation activity
        if subscription_link:
            SystemActivityLog.log_activity(
                user_id=user.id,
                activity_type='subscription_created',
                activity_data={
                    'subscription_link': subscription_link,
                    'price_ars': app.config.get('SUBSCRIPTION_PRICE_ARS', 499900.0) / 100
                }
            )
        
        db.session.commit()
        
        if subscription_link:
            # Generate welcome message with subscription offer
            welcome_message = f"""
🎉 ¡Felicitaciones {user.first_name}! Has completado tu perfil nutricional.

📊 TU PLAN PERSONALIZADO:
🎯 Objetivo: {user.goal.replace('_', ' ').title()}
🔥 Calorías diarias: {user.daily_calorie_goal:.0f} kcal
💪 Metabolismo basal: {user.bmr:.0f} kcal

🌟 ¡AHORA DESBLOQUEA EL PODER COMPLETO!

💎 CALORIA PREMIUM - 24 HORAS GRATIS:
✅ Análisis ILIMITADO de comidas (vs 3 gratis)
✅ Recomendaciones personalizadas avanzadas
✅ Seguimiento de micronutrientes detallado
✅ Planificación de comidas inteligente
✅ Soporte prioritario 24/7

💰 Después de tu prueba: Solo $4999.00 ARS/mes
🚫 Cancela cuando quieras, sin compromisos

🎁 ¡Activa tu prueba GRATUITA ahora!
👇 Haz clic para comenzar:"""
            
            # Return response with payment link
            return jsonify({
                "version": "v2",
                "content": {
                    "type": "telegram",
                    "messages": [
                        {
                            "type": "text",
                            "text": welcome_message
                        },
                        {
                            "type": "text", 
                            "text": f"🔗 ENLACE DE ACTIVACIÓN:\n{subscription_link}\n\n⚡ ¡Válido por 30 minutos!"
                        }
                    ],
                    "external_message_callback": {
                        "url": "https://caloria.vip/webhook/manychat",
                        "method": "post",
                        "payload": {
                            "subscriber_id": "{{user_id}}",
                            "first_name": "{{first_name}}",
                            "last_name": "{{last_name}}",
                            "message_text": "{{last_input_text}}",
                            "attachment_url": "{{last_input_attachment_url}}",
                            "message_type": "{{last_input_type}}"
                        },
                        "timeout": 3600
                    }
                }
            })
        else:
            # Fallback if subscription creation fails
            app.logger.error(f"Failed to create subscription for user {user.id}")
            
            fallback_message = f"""
🎉 Welcome to Caloria, {user.first_name}!

📊 Your personalized profile:
🎯 Daily Calorie Goal: {user.daily_calorie_goal:.0f} kcal
💪 Goal: {user.goal.replace('_', ' ').title()}
🔥 BMR: {user.bmr:.0f} kcal

Ready to start tracking your meals! Send me photos, descriptions, or voice messages of your food! 📸🍽️

⚠️ Subscription service temporarily unavailable. You can still track {3} meals today!"""
            
            return jsonify({
                "version": "v2",
                "content": {
                    "type": "telegram",
                    "messages": [
                        {
                            "type": "text",
                            "text": fallback_message
                        }
                    ],
                    "external_message_callback": {
                        "url": "https://caloria.vip/webhook/manychat",
                        "method": "post",
                        "payload": {
                            "subscriber_id": "{{user_id}}",
                            "first_name": "{{first_name}}",
                            "last_name": "{{last_name}}",
                            "message_text": "{{last_input_text}}",
                            "attachment_url": "{{last_input_attachment_url}}",
                            "message_type": "{{last_input_type}}"
                        },
                        "timeout": 3600
                    }
                }
            })
    else:
        # Quiz in progress - return current progress with subscription teaser
        progress_message = f"""
✅ Pregunta {question_number} completada!

📋 Progreso: {question_number}/15 ({int(question_number/15*100)}%)
{subscription_teaser}

👉 ¡Continúa con la siguiente pregunta!"""
        
        return jsonify({
            "version": "v2",
            "content": {
                "type": "telegram", 
                "messages": [
                    {
                        "type": "text",
                        "text": progress_message
                    }
                ]
            }
        })

def format_analysis_response(analysis_result, daily_stats, user=None):
    """Format the food analysis response message with premium features for trial users"""
    
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
    
    # PHASE 2A: Enhanced premium response for trial users
    premium_features = ""
    trial_status = ""
    
    if user and user.is_trial_active():
        # Log trial activity
        SubscriptionService.log_trial_activity(user, 'food_analysis_premium', {
            'food_name': analysis_result['food_name'],
            'calories': analysis_result['calories'],
            'confidence_score': analysis_result.get('confidence_score', 0)
        })
        
        # Get trial time remaining
        trial_time_remaining = user.get_trial_time_remaining()
        hours_left = int(trial_time_remaining.total_seconds() // 3600) if trial_time_remaining else 0
        minutes_left = int((trial_time_remaining.total_seconds() % 3600) // 60) if trial_time_remaining else 0
        
        trial_status = f"\n\n🌟 **ANÁLISIS PREMIUM ACTIVO**\n⚡ Tiempo restante: {hours_left}h {minutes_left}m de tu prueba gratuita"
        
        # Enhanced premium features
        premium_features = f"""

💎 **ANÁLISIS PREMIUM COMPLETO:**

🧬 **MICRONUTRIENTES DETALLADOS:**
• Vitamina C: ~{analysis_result['calories'] * 0.1:.1f}mg (estimado)
• Calcio: ~{analysis_result['protein'] * 15:.0f}mg  
• Hierro: ~{analysis_result['carbs'] * 0.2:.1f}mg
• Potasio: ~{analysis_result['fat'] * 25:.0f}mg

⏰ **TIMING ÓPTIMO:**
• Mejor momento: {"Desayuno/Mañana" if score >= 4 else "Almuerzo" if score >= 3 else "Ocasional"}
• Pre-entreno: {"✅ Excelente" if analysis_result['carbs'] > 20 else "⚠️ Agregar carbohidratos"}
• Post-entreno: {"✅ Perfecto" if analysis_result['protein'] > 15 else "💪 Agregar proteína"}

🎯 **RECOMENDACIONES PERSONALIZADAS:**
• Para tu objetivo ({user.goal.replace('_', ' ').title()}): {_get_goal_specific_advice(analysis_result, user.goal)}
• Frecuencia ideal: {frequency.lower()}
• Mejores combinaciones: {_get_food_combinations(analysis_result)}

📊 **PROGRESO AVANZADO:**
• Análisis realizados hoy: ILIMITADO ♾️ 
• Calidad nutricional promedio: {((score + daily_stats.food_logs_count * 3) / (daily_stats.food_logs_count + 1)):.1f}/5
• Tendencia semanal: {"📈 Mejorando" if score >= 3 else "📊 Estable"}"""
        
    elif user and user.can_access_premium_features():
        # Paid subscription features
        trial_status = "\n\n👑 **MIEMBRO PREMIUM** - Acceso completo"
        premium_features = premium_features.replace("ANÁLISIS PREMIUM ACTIVO", "MIEMBRO PREMIUM ACTIVO")
    elif user:
        # Free user - limited features
        daily_analyses = getattr(daily_stats, 'food_logs_count', 0)
        free_limit = 3
        remaining_free = max(0, free_limit - daily_analyses)
        
        if remaining_free > 0:
            trial_status = f"\n\n🆓 Análisis gratuitos restantes hoy: {remaining_free}/{free_limit}"
        else:
            trial_status = f"\n\n🔒 Límite diario alcanzado ({free_limit} análisis)\n💎 ¡Activa tu prueba gratuita de 24h para análisis ilimitado!"
        
        premium_features = f"""

💎 **¡DESBLOQUEA ANÁLISIS PREMIUM!**
✨ Micronutrientes detallados
⏰ Timing óptimo de comidas  
🎯 Recomendaciones personalizadas
📊 Progreso avanzado y tendencias
♾️ Análisis ilimitados

🎁 **¡PRUEBA GRATIS 24 HORAS!**
Solo $4999.00 ARS/mes después (cancela cuando quieras)"""

    # Basic analysis response
    response = f"""
📊 ANÁLISIS NUTRICIONAL
🍽️ {analysis_result['food_name']}

🔥 Energía: {analysis_result['calories']:.1f} kcal
💪 Proteína: {analysis_result['protein']:.1f}g
🍞 Carbohidratos: {analysis_result['carbs']:.1f}g  
🥑 Grasa: {analysis_result['fat']:.1f}g
🌱 Fibra: {analysis_result['fiber']:.1f}g
🧂 Sodio: {analysis_result['sodium']:.0f}mg

{score_emoji} Puntuación: {score}/5 – {recommendation}
✅ ¿Deberías comerlo? {frequency}

📈 PROGRESO DE HOY
🎯 Meta: {daily_stats.goal_calories:.0f} kcal
📊 Consumido: {daily_stats.total_calories:.0f} kcal
⚖️ Restante: {calories_remaining:.0f} kcal{trial_status}{premium_features}

💡 Consejo rápido: ¡Agrega vegetales verdes para más fibra!{low_confidence_note}
    """.strip()
    
    return response

def _get_goal_specific_advice(analysis_result, goal):
    """Get personalized advice based on user's goal"""
    if goal == 'lose_weight':
        if analysis_result['calories'] < 200:
            return "Perfecto para pérdida de peso - bajo en calorías"
        elif analysis_result['fiber'] > 5:
            return "Excelente - la fibra te mantendrá satisfecho"
        else:
            return "Moderado - considera porciones más pequeñas"
    elif goal == 'gain_weight':
        if analysis_result['calories'] > 300:
            return "Excelente para ganar peso - denso en calorías"
        else:
            return "Bien - combina con frutos secos para más calorías"
    elif goal == 'build_muscle':
        if analysis_result['protein'] > 15:
            return "Perfecto para construir músculo - alto en proteína"
        else:
            return "Bien - agrega una fuente de proteína"
    else:  # maintain_weight
        return "Ideal para mantenimiento - balanceado"

def _get_food_combinations(analysis_result):
    """Suggest food combinations based on nutritional profile"""
    if analysis_result['carbs'] > analysis_result['protein'] * 2:
        return "Agrega proteína (pollo, pescado, huevos)"
    elif analysis_result['protein'] > analysis_result['carbs'] * 2:
        return "Combina con carbohidratos complejos (quinoa, avena)"
    elif analysis_result['fat'] > 15:
        return "Equilibra con vegetales frescos"
    else:
        return "Combina con vegetales de hojas verdes"

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

# Add new function for Telegram Bot API integration
def download_telegram_image(file_id, telegram_bot_token):
    """Download image from Telegram using file_id"""
    try:
        app.logger.info(f"📥 Downloading Telegram image with file_id: {file_id}")
        
        # Step 1: Get file info from Telegram
        get_file_url = f"https://api.telegram.org/bot{telegram_bot_token}/getFile"
        params = {'file_id': file_id}
        
        response = requests.get(get_file_url, params=params, timeout=30)
        if response.status_code != 200:
            app.logger.error(f"Failed to get file info from Telegram: {response.status_code}")
            return None
            
        file_info = response.json()
        if not file_info.get('ok'):
            app.logger.error(f"Telegram API error: {file_info}")
            return None
            
        file_path = file_info['result']['file_path']
        app.logger.info(f"📁 Telegram file_path: {file_path}")
        
        # Step 2: Download the actual file
        download_url = f"https://api.telegram.org/file/bot{telegram_bot_token}/{file_path}"
        app.logger.info(f"🔗 Downloading from: {download_url}")
        
        image_response = requests.get(download_url, timeout=30)
        if image_response.status_code != 200:
            app.logger.error(f"Failed to download image: {image_response.status_code}")
            return None
            
        # Step 3: Save to temporary file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"telegram_{file_id}_{timestamp}.jpg"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        with open(filepath, 'wb') as f:
            f.write(image_response.content)
            
        app.logger.info(f"✅ Telegram image saved to: {filepath}")
        return filepath
        
    except Exception as e:
        app.logger.error(f"Error downloading Telegram image: {str(e)}")
        return None

# NEW: Analytics API endpoint
@app.route('/api/subscription-analytics', methods=['GET'])
def subscription_analytics():
    """Get subscription analytics and conversion metrics"""
    try:
        with app.app_context():
            # Basic user metrics
            total_users = User.query.count()
            quiz_completed_users = User.query.filter_by(quiz_completed=True).count()
            trial_pending_users = User.query.filter_by(subscription_tier='trial_pending').count()
            trial_active_users = User.query.filter_by(subscription_tier='trial_active').count()
            paid_users = User.query.filter_by(subscription_tier='active').count()
            cancelled_users = User.query.filter_by(subscription_tier='cancelled').count()
            
            # Conversion rates
            quiz_completion_rate = (quiz_completed_users / total_users * 100) if total_users > 0 else 0
            trial_conversion_rate = (trial_active_users / quiz_completed_users * 100) if quiz_completed_users > 0 else 0
            paid_conversion_rate = (paid_users / trial_active_users * 100) if trial_active_users > 0 else 0
            
            # Trial activity analytics
            trial_activities = TrialActivity.query.all()
            activity_types = {}
            engagement_scores = []
            
            for activity in trial_activities:
                activity_type = activity.activity_type
                activity_types[activity_type] = activity_types.get(activity_type, 0) + 1
                if activity.engagement_score:
                    engagement_scores.append(activity.engagement_score)
            
            avg_engagement = sum(engagement_scores) / len(engagement_scores) if engagement_scores else 0
            
            # Recent subscription trends (last 7 days)
            week_ago = datetime.utcnow() - timedelta(days=7)
            recent_signups = User.query.filter(User.created_at >= week_ago).count()
            recent_trials = User.query.filter(
                User.trial_start_time >= week_ago if hasattr(User, 'trial_start_time') else False
            ).count()
            
            analytics_data = {
                'user_metrics': {
                    'total_users': total_users,
                    'quiz_completed': quiz_completed_users,
                    'trial_pending': trial_pending_users,
                    'trial_active': trial_active_users,
                    'paid_subscribers': paid_users,
                    'cancelled': cancelled_users
                },
                'conversion_rates': {
                    'quiz_completion': round(quiz_completion_rate, 2),
                    'trial_conversion': round(trial_conversion_rate, 2),
                    'paid_conversion': round(paid_conversion_rate, 2)
                },
                'engagement': {
                    'activity_types': activity_types,
                    'average_engagement_score': round(avg_engagement, 2),
                    'total_trial_activities': len(trial_activities)
                },
                'trends': {
                    'recent_signups_7d': recent_signups,
                    'recent_trials_7d': recent_trials
                },
                'phase_2a_status': {
                    'implementation': 'complete',
                    'quiz_integration': 'active',
                    'trial_features': 'active',
                    'telegram_testing': 'ready',
                    'whatsapp_deployment': 'pending_api_approval'
                }
            }
            
            return jsonify(analytics_data)
            
    except Exception as e:
        app.logger.error(f"Analytics error: {str(e)}")
        return jsonify({'error': 'Analytics unavailable'}), 500

# NEW: Enhanced trial activity logging
class AnalyticsService:
    @staticmethod
    def log_conversion_event(user, event_type, event_data=None):
        """Log conversion events for analytics"""
        try:
            # Log to trial activity if user is in trial
            if user.is_trial_active() if hasattr(user, 'is_trial_active') else False:
                SubscriptionService.log_trial_activity(user, event_type, event_data)
            
            # Log conversion milestones
            conversion_events = {
                'user_registered': 1.0,
                'quiz_started': 2.0,
                'quiz_q10_reached': 3.0,  # First subscription mention
                'quiz_q11_reached': 3.5,  # Second subscription mention
                'quiz_completed': 5.0,
                'subscription_link_generated': 7.0,
                'trial_started': 10.0,
                'first_premium_analysis': 8.0,
                'trial_extended_24h': 6.0,
                'subscription_converted': 15.0,
                'subscription_cancelled': -5.0
            }
            
            engagement_score = conversion_events.get(event_type, 1.0)
            
            # Store in database for analytics
            app.logger.info(f"Analytics: {user.whatsapp_id} - {event_type} (score: {engagement_score})")
            
        except Exception as e:
            app.logger.error(f"Analytics logging error: {str(e)}")
    
    @staticmethod
    def get_user_conversion_funnel():
        """Get conversion funnel data"""
        try:
            with app.app_context():
                funnel_data = {
                    'registered': User.query.count(),
                    'quiz_started': User.query.filter(User.first_name.isnot(None)).count(),
                    'quiz_completed': User.query.filter_by(quiz_completed=True).count(),
                    'trial_started': User.query.filter(User.trial_start_time.isnot(None)).count(),
                    'converted_to_paid': User.query.filter_by(subscription_tier='active').count()
                }
                
                # Calculate conversion rates
                for i, (step, count) in enumerate(list(funnel_data.items())[1:]):
                    prev_step, prev_count = list(funnel_data.items())[i]
                    rate = (count / prev_count * 100) if prev_count > 0 else 0
                    funnel_data[f'{step}_rate'] = round(rate, 2)
                
                return funnel_data
                
        except Exception as e:
            app.logger.error(f"Funnel analytics error: {str(e)}")
            return {}

# Add analytics logging to quiz handler
def handle_quiz_response_with_analytics(user, data):
    """Enhanced quiz handler with analytics logging"""
    question_number = data.get('question_number', 0)
    
    # Log analytics events
    if question_number == 1:
        AnalyticsService.log_conversion_event(user, 'quiz_started')
    elif question_number == 10:
        AnalyticsService.log_conversion_event(user, 'quiz_q10_reached')
    elif question_number == 11:
        AnalyticsService.log_conversion_event(user, 'quiz_q11_reached')
    elif question_number >= 15:
        AnalyticsService.log_conversion_event(user, 'quiz_completed')
    
    # Call original quiz handler
    return handle_quiz_response(user, data)

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
    
# Health check endpoints (moved outside __main__ block)
@app.route('/health/database')
def database_health():
    """Database health check endpoint"""
    try:
        with app.app_context():
            from sqlalchemy import text
            # Modern SQLAlchemy syntax
            with db.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            user_count = User.query.count()
        
        db_uri = app.config['SQLALCHEMY_DATABASE_URI']
        return {
            "status": "healthy",
            "database": db_uri.split('://')[0].upper(),
            "user_count": user_count,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy", 
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }, 500

@app.route('/health')
def general_health():
    """General application health check"""
    return {
        "status": "healthy",
        "application": "Caloria",
        "timestamp": datetime.utcnow().isoformat()
    }

if __name__ == '__main__':

    # Use port 5001 to avoid conflicts with other projects
    port = int(os.getenv('PORT', 5001))
    app.run(debug=True, host='0.0.0.0', port=port) 