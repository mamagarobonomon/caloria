"""
Input Validation Service for Caloria Application
Provides comprehensive validation for all user inputs and webhook data
"""

import re
import urllib.parse
from typing import Dict, List, Tuple, Any, Optional
from config.constants import AppConstants, StatusCodes
from exceptions import ValidationException, WebhookValidationException

class ValidationService:
    """Service for validating various types of input data"""
    
    @staticmethod
    def validate_webhook_input(data: Dict[str, Any]) -> Tuple[List[str], Dict[str, Any]]:
        """
        Validate and sanitize webhook input data
        Returns: (errors, cleaned_data)
        """
        errors = []
        cleaned_data = {}
        
        if not isinstance(data, dict):
            errors.append("Invalid data format: expected JSON object")
            return errors, cleaned_data
        
        # Validate subscriber_id
        subscriber_id = data.get('id', data.get('subscriber_id', '')).strip()
        if not subscriber_id:
            errors.append("Missing subscriber_id")
        elif len(subscriber_id) > AppConstants.MAX_SUBSCRIBER_ID_LENGTH:
            errors.append(f"subscriber_id too long (max {AppConstants.MAX_SUBSCRIBER_ID_LENGTH} characters)")
        elif not re.match(r'^[a-zA-Z0-9_-]+$', subscriber_id):
            errors.append("subscriber_id contains invalid characters")
        else:
            cleaned_data['subscriber_id'] = subscriber_id
        
        # Validate and sanitize text input
        text = data.get('text', data.get('message_text', '')).strip()
        if text:
            if len(text) > AppConstants.MAX_TEXT_LENGTH:
                errors.append(f"Text too long (max {AppConstants.MAX_TEXT_LENGTH} characters)")
            else:
                # Sanitize text (remove potential script tags, etc.)
                cleaned_text = ValidationService._sanitize_text(text)
                cleaned_data['text'] = cleaned_text
        
        # Validate URLs if present
        url_fields = ['url', 'image_url', 'attachment_url', 'media_url', 'file_url']
        for field in url_fields:
            if field in data:
                url = data[field]
                if url and not ValidationService._is_valid_url(url):
                    errors.append(f"Invalid URL format in {field}")
                else:
                    cleaned_data[field] = url
        
        # Validate first_name and last_name
        for field in ['first_name', 'last_name']:
            if field in data:
                name = data[field].strip() if data[field] else ''
                if name:
                    if len(name) > 100:
                        errors.append(f"{field} too long (max 100 characters)")
                    elif not re.match(r'^[a-zA-ZÀ-ÿ\u00f1\u00d1\s\'-]+$', name):
                        errors.append(f"{field} contains invalid characters")
                    else:
                        cleaned_data[field] = name
        
        return errors, cleaned_data
    
    @staticmethod
    def validate_user_profile_data(data: Dict[str, Any]) -> Tuple[List[str], Dict[str, Any]]:
        """Validate user profile data from quiz"""
        errors = []
        cleaned_data = {}
        
        # Validate weight
        if 'weight' in data:
            try:
                weight = float(data['weight'])
                if weight < AppConstants.MIN_WEIGHT or weight > AppConstants.MAX_WEIGHT:
                    errors.append(f"Weight must be between {AppConstants.MIN_WEIGHT} and {AppConstants.MAX_WEIGHT} kg")
                else:
                    cleaned_data['weight'] = weight
            except (ValueError, TypeError):
                errors.append("Invalid weight format")
        
        # Validate height
        if 'height' in data:
            try:
                height = float(data['height'])
                if height < AppConstants.MIN_HEIGHT or height > AppConstants.MAX_HEIGHT:
                    errors.append(f"Height must be between {AppConstants.MIN_HEIGHT} and {AppConstants.MAX_HEIGHT} cm")
                else:
                    cleaned_data['height'] = height
            except (ValueError, TypeError):
                errors.append("Invalid height format")
        
        # Validate age
        if 'age' in data:
            try:
                age = int(data['age'])
                if age < AppConstants.MIN_AGE or age > AppConstants.MAX_AGE:
                    errors.append(f"Age must be between {AppConstants.MIN_AGE} and {AppConstants.MAX_AGE}")
                else:
                    cleaned_data['age'] = age
            except (ValueError, TypeError):
                errors.append("Invalid age format")
        
        # Validate gender
        if 'gender' in data:
            gender = data['gender'].lower().strip()
            if gender in ['male', 'female', 'other']:
                cleaned_data['gender'] = gender
            else:
                errors.append("Gender must be 'male', 'female', or 'other'")
        
        # Validate activity level
        if 'activity_level' in data:
            activity_level = data['activity_level'].lower().strip()
            valid_levels = ['sedentary', 'lightly_active', 'moderately_active', 'very_active', 'extra_active']
            if activity_level in valid_levels:
                cleaned_data['activity_level'] = activity_level
            else:
                errors.append(f"Activity level must be one of: {', '.join(valid_levels)}")
        
        # Validate goal
        if 'goal' in data:
            goal = data['goal'].lower().strip()
            valid_goals = ['lose_weight', 'maintain', 'gain_weight', 'build_muscle']
            if goal in valid_goals:
                cleaned_data['goal'] = goal
            else:
                errors.append(f"Goal must be one of: {', '.join(valid_goals)}")
        
        return errors, cleaned_data
    
    @staticmethod
    def validate_food_data(data: Dict[str, Any]) -> Tuple[List[str], Dict[str, Any]]:
        """Validate food analysis data"""
        errors = []
        cleaned_data = {}
        
        # Validate food_name
        if 'food_name' in data:
            food_name = data['food_name'].strip()
            if len(food_name) > AppConstants.MAX_FOOD_NAME_LENGTH:
                errors.append(f"Food name too long (max {AppConstants.MAX_FOOD_NAME_LENGTH} characters)")
            else:
                cleaned_data['food_name'] = food_name
        
        # Validate nutritional values
        nutrition_fields = ['calories', 'protein', 'carbs', 'fat', 'fiber', 'sodium']
        for field in nutrition_fields:
            if field in data:
                try:
                    value = float(data[field])
                    if value < 0:
                        errors.append(f"{field} cannot be negative")
                    elif field == 'calories' and value > AppConstants.MAX_CALORIES:
                        errors.append(f"Calories too high (max {AppConstants.MAX_CALORIES})")
                    else:
                        cleaned_data[field] = value
                except (ValueError, TypeError):
                    errors.append(f"Invalid {field} format")
        
        # Validate confidence score
        if 'confidence_score' in data:
            try:
                confidence = float(data['confidence_score'])
                if 0 <= confidence <= 1:
                    cleaned_data['confidence_score'] = confidence
                else:
                    errors.append("Confidence score must be between 0 and 1")
            except (ValueError, TypeError):
                errors.append("Invalid confidence score format")
        
        return errors, cleaned_data
    
    @staticmethod
    def validate_mercadopago_webhook(data: Dict[str, Any]) -> Tuple[List[str], Dict[str, Any]]:
        """Validate Mercado Pago webhook data"""
        errors = []
        cleaned_data = {}
        
        # Required fields for MP webhook
        required_fields = ['id', 'type', 'data']
        for field in required_fields:
            if field not in data:
                errors.append(f"Missing required field: {field}")
            else:
                cleaned_data[field] = data[field]
        
        # Validate webhook type
        if 'type' in data:
            webhook_type = data['type']
            valid_types = [
                'subscription_preapproval',
                'subscription_authorized_payment',
                'subscription_preapproval_plan'
            ]
            if webhook_type not in valid_types:
                errors.append(f"Invalid webhook type: {webhook_type}")
        
        # Validate data.id
        if 'data' in data and isinstance(data['data'], dict):
            if 'id' not in data['data']:
                errors.append("Missing data.id in webhook payload")
        
        return errors, cleaned_data
    
    @staticmethod
    def _sanitize_text(text: str) -> str:
        """Sanitize text input to prevent XSS and other attacks"""
        if not text:
            return ""
        
        # Remove potential script tags and other dangerous content
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r'javascript:', '', text, flags=re.IGNORECASE)
        text = re.sub(r'on\w+\s*=', '', text, flags=re.IGNORECASE)
        
        # Normalize whitespace
        text = ' '.join(text.split())
        
        return text
    
    @staticmethod
    def _is_valid_url(url: str) -> bool:
        """Validate URL format and security"""
        if not url:
            return False
        
        try:
            parsed = urllib.parse.urlparse(url)
            
            # Must have scheme and netloc
            if not parsed.scheme or not parsed.netloc:
                return False
            
            # Only allow http/https
            if parsed.scheme not in ['http', 'https']:
                return False
            
            # Basic security checks
            if any(danger in url.lower() for danger in ['javascript:', 'data:', 'file:', 'ftp:']):
                return False
            
            return True
            
        except Exception:
            return False
    
    @staticmethod
    def validate_admin_credentials(username: str, password: str) -> Tuple[List[str], Dict[str, str]]:
        """Validate admin login credentials"""
        errors = []
        cleaned_data = {}
        
        # Validate username
        username = username.strip() if username else ''
        if not username:
            errors.append("Username is required")
        elif len(username) > 80:
            errors.append("Username too long (max 80 characters)")
        elif not re.match(r'^[a-zA-Z0-9_-]+$', username):
            errors.append("Username contains invalid characters")
        else:
            cleaned_data['username'] = username
        
        # Validate password
        if not password:
            errors.append("Password is required")
        elif len(password) < AppConstants.MIN_PASSWORD_LENGTH:
            errors.append(f"Password too short (min {AppConstants.MIN_PASSWORD_LENGTH} characters)")
        else:
            cleaned_data['password'] = password
        
        return errors, cleaned_data

class SecurityService:
    """Service for security-related operations"""
    
    @staticmethod
    def verify_webhook_signature(payload: bytes, signature: str, secret: str, tolerance: int = AppConstants.WEBHOOK_SIGNATURE_TOLERANCE) -> bool:
        """Verify webhook signature using HMAC"""
        if not payload or not signature or not secret:
            return False
        
        try:
            import hmac
            import hashlib
            import time
            
            # Extract timestamp and signature from header (format: t=timestamp,v1=signature)
            signature_elements = {}
            for element in signature.split(','):
                key, value = element.split('=', 1)
                signature_elements[key] = value
            
            timestamp = int(signature_elements.get('t', 0))
            expected_signature = signature_elements.get('v1', '')
            
            # Check timestamp tolerance
            if abs(time.time() - timestamp) > tolerance:
                return False
            
            # Compute expected signature
            signed_payload = f"{timestamp}.{payload.decode('utf-8')}"
            computed_signature = hmac.new(
                secret.encode('utf-8'),
                signed_payload.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            # Compare signatures
            return hmac.compare_digest(expected_signature, computed_signature)
            
        except Exception:
            return False
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize filename for safe storage"""
        if not filename:
            return "unknown"
        
        # Remove path separators and dangerous characters
        filename = re.sub(r'[<>:"/\\|?*]', '', filename)
        filename = re.sub(r'\.\.', '', filename)  # Remove parent directory references
        
        # Limit length
        if len(filename) > 100:
            name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
            filename = name[:95] + ('.' + ext if ext else '')
        
        return filename or "sanitized"
    
    @staticmethod
    def is_safe_file_type(filename: str, allowed_types: List[str] = None) -> bool:
        """Check if file type is safe"""
        if not filename:
            return False
        
        if allowed_types is None:
            allowed_types = AppConstants.SUPPORTED_IMAGE_FORMATS
        
        _, ext = filename.rsplit('.', 1) if '.' in filename else ('', '')
        return f'.{ext.lower()}' in allowed_types 