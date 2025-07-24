"""
Application Constants for Caloria
Centralized location for all magic numbers, strings, and configuration values
"""

class AppConstants:
    """Core application constants"""
    
    # File upload limits
    MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB
    MAX_TEXT_LENGTH = 1000
    MAX_SUBSCRIBER_ID_LENGTH = 50
    MAX_FOOD_NAME_LENGTH = 200
    
    # API timeouts (seconds)
    DOWNLOAD_TIMEOUT = 30
    WEBHOOK_TIMEOUT = 22  # Mercado Pago requirement
    API_REQUEST_TIMEOUT = 30
    SPOONACULAR_TIMEOUT = 30
    GOOGLE_CLOUD_TIMEOUT = 30
    
    # Food analysis confidence scores
    MIN_CONFIDENCE_SCORE = 0.3
    DEFAULT_CONFIDENCE = 0.5
    FALLBACK_CONFIDENCE = 0.2
    HIGH_CONFIDENCE_THRESHOLD = 0.7
    
    # Subscription settings
    DEFAULT_TRIAL_DAYS = 1
    MAX_FREE_MEALS = 3
    TRIAL_DURATION_HOURS = 24
    
    # Image processing
    SUPPORTED_IMAGE_FORMATS = ['.jpg', '.jpeg', '.png', '.webp']
    IMAGE_QUALITY = 85
    MAX_IMAGE_DIMENSION = 2048
    IMAGE_COMPRESSION_THRESHOLD = 1024 * 1024  # 1MB
    
    # Database settings
    DEFAULT_PAGE_SIZE = 20
    MAX_PAGE_SIZE = 100
    QUERY_TIMEOUT = 30
    
    # Rate limiting
    DEFAULT_RATE_LIMIT = "200 per day"
    WEBHOOK_RATE_LIMIT = "100 per hour"
    API_RATE_LIMIT = "50 per minute"
    ADMIN_RATE_LIMIT = "1000 per hour"
    
    # Security
    MIN_PASSWORD_LENGTH = 8
    SESSION_TIMEOUT_HOURS = 24
    WEBHOOK_SIGNATURE_TOLERANCE = 300  # 5 minutes
    
    # Nutrition ranges (validation)
    MIN_CALORIES = 0
    MAX_CALORIES = 5000
    MIN_WEIGHT = 30  # kg
    MAX_WEIGHT = 300  # kg
    MIN_HEIGHT = 100  # cm
    MAX_HEIGHT = 250  # cm
    MIN_AGE = 10
    MAX_AGE = 120

class StatusCodes:
    """HTTP and application status codes"""
    
    # HTTP Status Codes
    OK = 200
    CREATED = 201
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    RATE_LIMITED = 429
    INTERNAL_ERROR = 500
    
    # Application Status Codes
    ANALYSIS_SUCCESS = "analysis_success"
    ANALYSIS_FAILED = "analysis_failed"
    WEBHOOK_PROCESSED = "webhook_processed"
    WEBHOOK_FAILED = "webhook_failed"

class Messages:
    """User-facing messages"""
    
    # Error messages
    INVALID_IMAGE = "❌ No se pudo procesar la imagen. Por favor envía una foto clara de tu comida."
    INVALID_AUDIO = "❌ No se pudo procesar el audio. Por favor envía un mensaje de voz claro."
    INVALID_TEXT = "❌ No se pudo procesar el texto. Por favor describe tu comida."
    RATE_LIMIT_EXCEEDED = "⏰ Has enviado muchos mensajes. Por favor espera un momento."
    SYSTEM_ERROR = "🚨 Error del sistema. Por favor intenta nuevamente en unos minutos."
    
    # Success messages
    ANALYSIS_COMPLETE = "✅ Análisis nutricional completado"
    SUBSCRIPTION_CREATED = "🎉 Suscripción creada exitosamente"
    QUIZ_COMPLETED = "🎯 Quiz completado. ¡Calculando tu plan personalizado!"
    
    # Help messages
    HELP_TEXT = """
💡 **Cómo usar Caloria:**
📸 Envía una foto de tu comida
📝 Describe lo que comiste (ej: "1 manzana")
🎤 Envía un mensaje de voz
🔄 Escribe "REINICIAR" para empezar de nuevo
"""

class APIEndpoints:
    """External API endpoints"""
    
    # Spoonacular
    SPOONACULAR_BASE = "https://api.spoonacular.com"
    SPOONACULAR_CLASSIFY = f"{SPOONACULAR_BASE}/food/images/classify"
    SPOONACULAR_ANALYZE = f"{SPOONACULAR_BASE}/food/images/analyze"
    SPOONACULAR_PARSE = f"{SPOONACULAR_BASE}/recipes/parseIngredients"
    
    # ManyChat
    MANYCHAT_BASE = "https://api.manychat.com"
    MANYCHAT_SEND = f"{MANYCHAT_BASE}/fb/sending/sendContent"
    
    # Mercado Pago
    MP_BASE = "https://api.mercadopago.com"
    MP_PREAPPROVAL = f"{MP_BASE}/preapproval"
    MP_AUTHORIZED_PAYMENTS = f"{MP_BASE}/authorized_payments"
    
    # Google Cloud
    GOOGLE_VISION_BASE = "https://vision.googleapis.com/v1"
    GOOGLE_SPEECH_BASE = "https://speech.googleapis.com/v1"

class LogLevels:
    """Logging levels and categories"""
    
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
    
    # Log categories
    WEBHOOK = "webhook"
    API = "api"
    DATABASE = "database"
    SECURITY = "security"
    PERFORMANCE = "performance"
    USER_ACTION = "user_action" 