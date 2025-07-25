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
    # Add Vertex AI for prompt-based image analysis
    import vertexai
    from vertexai.generative_models import GenerativeModel, Part
    import google.genai as genai
    GOOGLE_CLOUD_AVAILABLE = True
    VERTEX_AI_AVAILABLE = True
except ImportError:
    GOOGLE_CLOUD_AVAILABLE = False
    VERTEX_AI_AVAILABLE = False
    # Note: app.logger will be available after Flask app is created

# ===== NEW: Import all modular services and handlers =====
from config.constants import AppConstants, StatusCodes, APIEndpoints, LogLevels
from exceptions import (
    CaloriaException, ValidationException, FoodAnalysisException, 
    APIException, DatabaseException, handle_exceptions
)

# Services
from services.logging_service import caloria_logger, LogTimer
from services.validation_service import ValidationService, SecurityService
from services.rate_limiting_service import RateLimitingService
from services.database_service import DatabaseService
from services.caching_service import CacheService
from services.metrics_service import (
    MetricsService, WebhookMetrics, FoodAnalysisMetrics, 
    DatabaseMetrics, APIMetrics, SubscriptionMetrics
)

# Handlers
from handlers.webhook_handlers import WebhookRouter, ManyChannelWebhookHandler, MercadoPagoWebhookHandler
from handlers.food_analysis_handlers import FoodAnalysisHandler
from handlers.quiz_handlers import QuizHandler

# Middleware
from middleware.error_handlers import ErrorHandler

# Monitoring
from monitoring.health_checks import HealthChecker, register_health_checks

# Initialize global services
metrics_service = MetricsService()
webhook_metrics = WebhookMetrics()
food_analysis_metrics = FoodAnalysisMetrics()
database_metrics = DatabaseMetrics()
api_metrics = APIMetrics()
subscription_metrics = SubscriptionMetrics()

# ===== END: New imports =====

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
app.config['MAX_CONTENT_LENGTH'] = AppConstants.MAX_FILE_SIZE  # 16MB max file size

# API Keys (set as environment variables)
# app.config['SPOONACULAR_API_KEY'] = os.environ.get('SPOONACULAR_API_KEY')  # Removed - using Gemini Vision AI only
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

# ===== NEW: Initialize all services with app and database =====
# Initialize rate limiting service
rate_limiting_service = RateLimitingService()
rate_limiting_service.init_app(app)

# Initialize database service
database_service = DatabaseService(db)

# Initialize error handling middleware
error_handler = ErrorHandler()
error_handler.init_app(app)

# Setup structured logging
caloria_logger.info("Caloria application starting up", 
    details={"google_cloud_available": GOOGLE_CLOUD_AVAILABLE},
    category="startup")
# ===== END: Service initialization =====

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
    
    # NEW: Language support
    language = db.Column(db.String(5), default='es')  # 'es' for Spanish (default), 'en' for English
    
    # Quiz progress tracking
    current_quiz_step = db.Column(db.Integer, default=0)
    quiz_data = db.Column(db.Text, nullable=True)  # JSON string for quiz responses
    last_interaction = db.Column(db.DateTime, default=datetime.utcnow)
    
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

# ===== NEW: Initialize modular handlers with models after models are defined =====
# Initialize food analysis handler
food_analysis_handler = FoodAnalysisHandler(db, User, FoodLog)

# Initialize quiz handler  
quiz_handler = QuizHandler(db, User)

# Initialize webhook router with models
models = {
    'User': User,
    'FoodLog': FoodLog,
    'Subscription': Subscription,
    'DailyStats': DailyStats,
    'SystemActivityLog': SystemActivityLog,
    'TrialActivity': TrialActivity
}
webhook_router = WebhookRouter(db, models)

# Initialize health checker
health_checker = HealthChecker(db)

caloria_logger.info("Handler model references set successfully",
    details={"models_configured": list(models.keys())},
    category="startup")
# ===== END: Handler model configuration =====

# ===== NEW: Create simplified services for missing functionality =====
class SubscriptionService:
    """Simplified subscription service to maintain functionality"""
    
    @staticmethod
    def start_trial(user):
        """Start trial period for user"""
        try:
            from datetime import datetime, timedelta
            now = datetime.utcnow()
            trial_days = app.config.get('SUBSCRIPTION_TRIAL_DAYS', 1)
            
            user.subscription_status = 'trial_active'
            user.subscription_tier = 'premium'
            user.trial_start_time = now
            user.trial_end_time = now + timedelta(days=trial_days)
            
            db.session.commit()
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
                return
            
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
                engagement_score=1.0  # Simplified scoring
            )
            
            db.session.add(activity)
            db.session.commit()
            
        except Exception as e:
            app.logger.error(f"Error logging trial activity: {str(e)}")

class MercadoPagoService:
    """Simplified MercadoPago service to maintain functionality"""
    
    @staticmethod
    def get_subscription_details(subscription_id):
        """Get subscription details from Mercado Pago API"""
        try:
            access_token = app.config['MERCADO_PAGO_ACCESS_TOKEN']
            if not access_token:
                return None
            
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

# ===== END: Simplified services =====

# Mercado Pago and Subscription Services - using new modular services
from services.database_service import DatabaseService
from handlers.food_analysis_handlers import FoodAnalysisHandler

# Utility Services - now using modular services
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
        
        # Use new modular webhook router to handle subscription creation
        try:
            response_data, status_code = webhook_router.route_webhook('subscription_create', {
                'user_id': user.id,
                'plan_type': plan_type
            })
            return jsonify(response_data), status_code
        except Exception as e:
            app.logger.error(f"Error creating subscription: {str(e)}")
            return jsonify({'error': 'Failed to create subscription'}), 500
        
    except Exception as e:
        app.logger.error(f"Error creating subscription: {str(e)}")
        return jsonify({'error': 'Failed to create subscription'}), 500

def handle_subscription_webhook(subscription_id, action):
    """Process subscription webhook events - FIXED format"""
    try:
        if not subscription_id:
            app.logger.error("No subscription ID in webhook data")
            return False
        
        app.logger.info(f"Processing subscription webhook: {subscription_id}, action: {action}")
        
        # Get subscription details from Mercado Pago API
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

@app.route('/admin/system-status')
def admin_system_status():
    """Admin page for system status monitoring"""
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))
    
    try:
        # Get comprehensive system health data
        health_data = health_checker.get_overall_health()
        
        # Get specific health checks
        database_health = health_checker._check_database_health()
        cache_health = health_checker._check_cache_performance()
        api_health = health_checker._check_external_apis_health()
        metrics_data = health_checker._check_application_metrics()
        
        # Get version and uptime info
        version_info = health_checker._get_application_version()
        uptime_seconds = health_checker._get_uptime_seconds()
        
        # Format uptime for display
        uptime_hours = uptime_seconds // 3600
        uptime_minutes = (uptime_seconds % 3600) // 60
        uptime_display = f"{int(uptime_hours)}h {int(uptime_minutes)}m"
        
        # Determine status colors for UI
        status_colors = {
            'healthy': 'success',
            'degraded': 'warning', 
            'unhealthy': 'danger',
            'unknown': 'secondary'
        }
        
        return render_template('admin/system_status.html',
                             health_data=health_data,
                             database_health=database_health,
                             cache_health=cache_health,
                             api_health=api_health,
                             metrics_data=metrics_data,
                             version_info=version_info,
                             uptime_display=uptime_display,
                             status_colors=status_colors)
        
    except Exception as e:
        app.logger.error(f"Error loading system status: {str(e)}")
        flash('Error loading system status', 'error')
        return redirect(url_for('admin_dashboard'))

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

# ===== NEW: Modern Webhook Routes using Modular Handlers =====

# ManyChat Webhook Routes
@app.route('/webhook/manychat', methods=['POST'])
@rate_limiting_service.limiter.limit("100 per minute")
def manychat_webhook():
    """Handle incoming webhooks from ManyChat using modular handlers"""
    import time
    start_time = time.time()
    
    try:
        # Validate and sanitize input
        request_data = request.get_json()
        errors, sanitized_data = ValidationService.validate_webhook_input(request_data)
        
        if errors:
            caloria_logger.warning("Webhook validation failed", details={
                "errors": errors,
                "data": request_data
            })
            return jsonify({
                "version": "v2",
                "content": {
                    "type": "text", 
                    "text": "❌ Invalid request data"
                }
            }), StatusCodes.BAD_REQUEST
        
        # Track webhook metrics
        user_id = sanitized_data.get('id', 'unknown')
        webhook_metrics.record_webhook_received('manychat', user_id)
        
        # Route to appropriate handler
        response_data, status_code = webhook_router.route_webhook('manychat', sanitized_data)
        
        # Track successful processing
        processing_time_ms = (time.time() - start_time) * 1000
        webhook_metrics.record_webhook_processed('manychat', True, processing_time_ms, user_id)
        
        caloria_logger.info("ManyChat webhook processed successfully", details={
            "status_code": status_code,
            "processing_time_ms": processing_time_ms,
            "subscriber_id": sanitized_data.get('subscriber_id')
        })
        
        return jsonify(response_data), status_code
        
    except CaloriaException as e:
        processing_time_ms = (time.time() - start_time) * 1000
        webhook_metrics.record_webhook_processed('manychat', False, processing_time_ms)
        
        caloria_logger.error(f"ManyChat webhook error: {e.message}", error=e, details={
            "error_code": e.error_code,
            "details": e.details
        })
        return jsonify({
            "version": "v2",
            "content": {"type": "text", "text": "❌ Service temporarily unavailable"}
        }), StatusCodes.INTERNAL_SERVER_ERROR
        
    except Exception as e:
        processing_time_ms = (time.time() - start_time) * 1000
        webhook_metrics.record_webhook_processed('manychat', False, processing_time_ms)
        
        caloria_logger.error(f"Unexpected webhook error: {str(e)}", error=e)
        return jsonify({
            "version": "v2", 
            "content": {"type": "text", "text": "❌ Unexpected error occurred"}
        }), StatusCodes.INTERNAL_SERVER_ERROR

# MercadoPago Webhook Routes
@app.route('/webhook/mercadopago', methods=['POST'])
@rate_limiting_service.limiter.limit("200 per minute")
def mercadopago_webhook():
    """Handle Mercado Pago webhooks using modular handlers"""
    import time
    start_time = time.time()
    
    try:
        # Validate webhook signature
        payload = request.get_data()
        signature = request.headers.get('x-signature', '')
        
        if not SecurityService.verify_webhook_signature(payload, signature, app.config.get('MERCADO_PAGO_WEBHOOK_SECRET', '')):
            caloria_logger.warning("Invalid MercadoPago webhook signature", details={
                "signature": signature
            })
            return jsonify({'error': 'Invalid signature'}), StatusCodes.UNAUTHORIZED
        
        # Validate and sanitize input
        request_data = request.get_json()
        errors, sanitized_data = ValidationService.validate_mercadopago_webhook(request_data)
        
        if errors:
            caloria_logger.warning("MercadoPago webhook validation failed", details={
                "errors": errors
            })
            return jsonify({'error': 'Invalid webhook data'}), StatusCodes.BAD_REQUEST
        
        # Track webhook metrics
        webhook_metrics.record_webhook_received('mercadopago')
        
        # Route to appropriate handler
        response_data, status_code = webhook_router.route_webhook('mercadopago', sanitized_data)
        
        # Track successful processing
        processing_time_ms = (time.time() - start_time) * 1000
        webhook_metrics.record_webhook_processed('mercadopago', True, processing_time_ms)
        
        caloria_logger.info("MercadoPago webhook processed successfully", details={
            "status_code": status_code,
            "processing_time_ms": processing_time_ms,
            "webhook_type": sanitized_data.get('type')
        })
        
        return jsonify(response_data), status_code
        
    except CaloriaException as e:
        processing_time_ms = (time.time() - start_time) * 1000
        webhook_metrics.record_webhook_processed('mercadopago', False, processing_time_ms)
        
        caloria_logger.error(f"MercadoPago webhook error: {e.message}", error=e, details={
            "error_code": e.error_code
        })
        return jsonify({'status': 'error'}), StatusCodes.INTERNAL_SERVER_ERROR
        
    except Exception as e:
        processing_time_ms = (time.time() - start_time) * 1000
        webhook_metrics.record_webhook_processed('mercadopago', False, processing_time_ms)
        
        caloria_logger.error(f"Unexpected MercadoPago webhook error: {str(e)}", error=e)
        return jsonify({'status': 'error'}), StatusCodes.INTERNAL_SERVER_ERROR


# Legacy function removed - now handled by modular food_analysis_handlers.py

# Legacy function removed - now handled by modular food_analysis_handlers.py

# Legacy function removed - now handled by modular food_analysis_handlers.py

# Legacy function removed - now handled by modular quiz_handlers.py

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

# Analytics service for quiz handling - now integrated into modular quiz handler
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
    
    # Use modular quiz handler
    return quiz_handler.handle_quiz_response(user, data)

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
    
# ===== NEW: Comprehensive Health Check Endpoints =====
# Register all health check routes from the monitoring service
register_health_checks(app, db)

@app.route('/health/')
def health_overview():
    """Overall application health status"""
    return health_checker.get_overall_health()

@app.route('/health/ready')
def readiness_probe():
    """Kubernetes readiness probe"""
    return health_checker.check_readiness()

@app.route('/health/live')
def liveness_probe():
    """Kubernetes liveness probe"""
    return health_checker.check_liveness()

@app.route('/health/metrics')
def metrics_endpoint():
    """Application metrics endpoint"""
    return health_checker.get_metrics()

@app.route('/health/database')
def database_health():
    """Database health and performance check"""
    return health_checker.check_database_health()

@app.route('/health/cache')
def cache_health():
    """Cache performance and status"""
    return health_checker.check_cache_health()

@app.route('/health/version')
def version_info():
    """Application version and build info"""
    return health_checker.get_version_info()

# Legacy health endpoint for backward compatibility
@app.route('/health')
def general_health():
    """Legacy health endpoint - redirects to comprehensive health"""
    return health_checker.get_overall_health()

# ===== END: Health Check Endpoints =====

# ===== NEW: Application Factory for Testing =====
def create_app(config=None):
    """Application factory for testing"""
    test_app = Flask(__name__)
    
    # Copy configuration from main app
    test_app.config.update(app.config)
    
    # Override with test config if provided
    if config:
        test_app.config.update(config)
    
    # Initialize extensions
    db.init_app(test_app)
    
    # Copy routes from main app
    for rule in app.url_map.iter_rules():
        if rule.endpoint != 'static':
            view_func = app.view_functions[rule.endpoint]
            test_app.add_url_rule(rule.rule, rule.endpoint, view_func, methods=rule.methods)
    
    return test_app

# ===== END: Application Factory =====

if __name__ == '__main__':

    # Use port 5001 to avoid conflicts with other projects
    port = int(os.getenv('PORT', 5001))
    app.run(debug=True, host='0.0.0.0', port=port) 