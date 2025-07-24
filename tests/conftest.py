"""
Test Configuration and Fixtures for Caloria Application
Provides pytest configuration and common fixtures for all tests
"""

import pytest
import tempfile
import os
from datetime import datetime, date
from unittest.mock import Mock, patch
import json

# Test environment setup
@pytest.fixture(scope='session', autouse=True)
def setup_test_environment():
    """Setup test environment variables"""
    os.environ['FLASK_ENV'] = 'testing'
    os.environ['TESTING'] = 'true'
    os.environ['SECRET_KEY'] = 'test-secret-key'
    os.environ['SPOONACULAR_API_KEY'] = 'test-spoonacular-key'
    os.environ['MANYCHAT_API_TOKEN'] = 'test-manychat-token'
    
    # Use in-memory database for tests
    os.environ['DATABASE_URL'] = 'sqlite:///:memory:'

@pytest.fixture
def app():
    """Create and configure test Flask application"""
    from app import create_app
    
    # Create temporary database
    db_fd, db_path = tempfile.mkstemp()
    
    app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': f'sqlite:///{db_path}',
        'WTF_CSRF_ENABLED': False,
        'SECRET_KEY': 'test-secret-key'
    })
    
    with app.app_context():
        from app import db
        db.create_all()
        
        # Create test admin user
        from app import AdminUser
        admin = AdminUser(username='testadmin', email='test@admin.com')
        admin.set_password('testpass')
        db.session.add(admin)
        db.session.commit()
    
    yield app
    
    # Cleanup
    os.close(db_fd)
    os.unlink(db_path)

@pytest.fixture
def client(app):
    """Flask test client"""
    return app.test_client()

@pytest.fixture
def db(app):
    """Database fixture"""
    from app import db as _db
    
    with app.app_context():
        yield _db

@pytest.fixture
def admin_user(db):
    """Create test admin user"""
    from app import AdminUser
    
    admin = AdminUser(username='testadmin', email='test@caloria.com')
    admin.set_password('password123')
    db.session.add(admin)
    db.session.commit()
    
    return admin

@pytest.fixture
def test_user(db):
    """Create test user"""
    from app import User
    
    user = User(
        whatsapp_id='test_user_123',
        first_name='Test',
        last_name='User',
        is_active=True,
        quiz_completed=True,
        gender='male',
        age=30,
        weight=70.0,
        height=175.0,
        activity_level='moderately_active',
        goal='maintain',
        daily_calorie_goal=2000,
        subscription_status='trial_active',
        created_at=datetime.utcnow(),
        last_interaction=datetime.utcnow()
    )
    
    db.session.add(user)
    db.session.commit()
    
    return user

@pytest.fixture
def test_food_log(db, test_user):
    """Create test food log entry"""
    from app import FoodLog
    
    food_log = FoodLog(
        user_id=test_user.id,
        food_name='Test Apple',
        calories=95,
        protein=0.5,
        carbs=25,
        fat=0.3,
        fiber=4,
        sodium=2,
        confidence_score=0.85,
        analysis_method='text',
        original_input='1 apple',
        created_at=datetime.utcnow()
    )
    
    db.session.add(food_log)
    db.session.commit()
    
    return food_log

@pytest.fixture
def test_daily_stats(db, test_user):
    """Create test daily stats"""
    from app import DailyStats
    
    daily_stats = DailyStats(
        user_id=test_user.id,
        date=date.today(),
        goal_calories=2000,
        total_calories=1800,
        total_protein=90,
        total_carbs=200,
        total_fat=60,
        total_fiber=25,
        total_sodium=1200,
        meals_logged=3,
        calorie_difference=-200,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    db.session.add(daily_stats)
    db.session.commit()
    
    return daily_stats

# Mock fixtures for external services
@pytest.fixture
def mock_spoonacular_response():
    """Mock Spoonacular API response"""
    return [
        {
            "id": 9003,
            "name": "apple",
            "consistency": 0.85,
            "nutrition": {
                "nutrients": [
                    {"name": "Calories", "amount": 95, "unit": "kcal"},
                    {"name": "Protein", "amount": 0.5, "unit": "g"},
                    {"name": "Carbohydrates", "amount": 25, "unit": "g"},
                    {"name": "Fat", "amount": 0.3, "unit": "g"},
                    {"name": "Fiber", "amount": 4, "unit": "g"},
                    {"name": "Sodium", "amount": 2, "unit": "mg"}
                ]
            }
        }
    ]

@pytest.fixture
def mock_google_vision_response():
    """Mock Google Cloud Vision API response"""
    return Mock(
        text_annotations=[
            Mock(description="Fresh Apple Red Delicious")
        ]
    )

@pytest.fixture
def mock_google_speech_response():
    """Mock Google Cloud Speech API response"""
    return Mock(
        results=[
            Mock(alternatives=[
                Mock(transcript="Una manzana roja")
            ])
        ]
    )

@pytest.fixture
def mock_manychat_webhook_data():
    """Mock ManyChat webhook data"""
    return {
        "id": "test_subscriber_123",
        "first_name": "Test",
        "last_name": "User",
        "text": "1 apple",
        "type": "text"
    }

@pytest.fixture
def mock_mercadopago_webhook_data():
    """Mock Mercado Pago webhook data"""
    return {
        "id": "12345",
        "type": "subscription_preapproval",
        "data": {
            "id": "MP-SUB-123456789"
        }
    }

# Test data factories
@pytest.fixture
def user_factory(db):
    """Factory for creating test users"""
    def _create_user(**kwargs):
        from app import User
        
        defaults = {
            'whatsapp_id': f'test_user_{datetime.utcnow().timestamp()}',
            'first_name': 'Test',
            'last_name': 'User',
            'is_active': True,
            'created_at': datetime.utcnow(),
            'last_interaction': datetime.utcnow()
        }
        defaults.update(kwargs)
        
        user = User(**defaults)
        db.session.add(user)
        db.session.commit()
        
        return user
    
    return _create_user

@pytest.fixture
def food_log_factory(db):
    """Factory for creating test food logs"""
    def _create_food_log(user_id, **kwargs):
        from app import FoodLog
        
        defaults = {
            'user_id': user_id,
            'food_name': 'Test Food',
            'calories': 100,
            'protein': 5,
            'carbs': 15,
            'fat': 3,
            'fiber': 2,
            'sodium': 50,
            'confidence_score': 0.75,
            'analysis_method': 'text',
            'original_input': 'test food',
            'created_at': datetime.utcnow()
        }
        defaults.update(kwargs)
        
        food_log = FoodLog(**defaults)
        db.session.add(food_log)
        db.session.commit()
        
        return food_log
    
    return _create_food_log

# Utility fixtures
@pytest.fixture
def auth_headers(admin_user, client):
    """Get authentication headers for admin"""
    with client.session_transaction() as sess:
        sess['admin_id'] = admin_user.id
        sess['admin_username'] = admin_user.username
    
    return {'Content-Type': 'application/json'}

@pytest.fixture
def sample_image_url():
    """Sample image URL for testing"""
    return "https://example.com/test-food-image.jpg"

@pytest.fixture
def sample_audio_url():
    """Sample audio URL for testing"""
    return "https://example.com/test-audio-message.ogg"

# Performance testing fixtures
@pytest.fixture
def performance_timer():
    """Timer for performance testing"""
    import time
    
    class Timer:
        def __init__(self):
            self.start_time = None
            self.end_time = None
        
        def start(self):
            self.start_time = time.time()
        
        def stop(self):
            self.end_time = time.time()
        
        @property
        def duration(self):
            if self.start_time and self.end_time:
                return self.end_time - self.start_time
            return None
    
    return Timer()

# Integration test fixtures
@pytest.fixture
def integration_test_setup(app, db):
    """Setup for integration tests"""
    with app.app_context():
        # Clear any existing data
        from app import User, FoodLog, DailyStats, SystemActivityLog
        
        db.session.query(SystemActivityLog).delete()
        db.session.query(DailyStats).delete()
        db.session.query(FoodLog).delete()
        db.session.query(User).delete()
        db.session.commit()
        
        yield
        
        # Cleanup after tests
        db.session.query(SystemActivityLog).delete()
        db.session.query(DailyStats).delete()
        db.session.query(FoodLog).delete()
        db.session.query(User).delete()
        db.session.commit()

# Error testing fixtures
@pytest.fixture
def mock_api_error():
    """Mock API error for testing error handling"""
    def _mock_error(status_code=500, message="API Error"):
        error = Mock()
        error.status_code = status_code
        error.text = message
        error.json.return_value = {"error": message}
        return error
    
    return _mock_error

# Configuration for pytest
def pytest_configure(config):
    """Configure pytest"""
    # Add custom markers
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )
    config.addinivalue_line(
        "markers", "api: marks tests that test API endpoints"
    )
    config.addinivalue_line(
        "markers", "webhook: marks tests that test webhook functionality"
    )

# Test collection configuration
def pytest_collection_modifyitems(config, items):
    """Modify test collection"""
    for item in items:
        # Add unit marker to all tests by default
        if not any(marker.name in ['integration', 'slow'] for marker in item.iter_markers()):
            item.add_marker(pytest.mark.unit)
        
        # Add slow marker to tests that might be slow
        if 'integration' in item.name or 'api' in item.name:
            item.add_marker(pytest.mark.slow) 