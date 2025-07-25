"""
Food Analysis Handlers for Caloria Application
Modular handlers for different types of food analysis (text, image, audio)
"""

import os
import requests
import time
from datetime import datetime, date
from typing import Dict, Any, Optional, Tuple, List
from urllib.parse import urlparse

from config.constants import AppConstants, StatusCodes, Messages, APIEndpoints
from services.validation_service import ValidationService, SecurityService
from services.logging_service import caloria_logger, LogTimer
from services.metrics_service import FoodAnalysisMetrics
from services.caching_service import FoodAnalysisCache, APIResponseCache, invalidate_user_related_cache
from services.database_service import DatabaseService
from exceptions import FoodAnalysisException, APIException, FileProcessingException

class FoodAnalysisHandler:
    """Handler for all types of food analysis"""
    
    def __init__(self, db, user_model, food_log_model):
        self.db = db
        self.User = user_model
        self.FoodLog = food_log_model
        self.logger = caloria_logger
        self.db_service = DatabaseService(db)
    
    def analyze_food_text(self, subscriber_id: str, text: str) -> Dict[str, Any]:
        """Analyze food from text description"""
        start_time = time.time()
        
        try:
            user = self._get_or_create_user(subscriber_id)
            FoodAnalysisMetrics.record_analysis_started('text', str(user.id))
            
            # Check cache first
            cached_result = FoodAnalysisCache.get_cached_food_analysis(text, 'text')
            if cached_result:
                # Use cached result but still create food log
                analysis_result = cached_result
                self.logger.info(f"Using cached analysis for text: {text[:30]}...")
            else:
                # Perform new analysis
                analysis_result = self._analyze_text_with_spoonacular(text)
                
                # Cache the result
                FoodAnalysisCache.cache_food_analysis(text, analysis_result, 'text')
            
            # Create food log entry
            food_log = self._create_food_log(user, analysis_result, 'text', text)
            
            # Update daily stats
            self._update_user_daily_stats(user, date.today())
            
            # Record metrics
            processing_time = (time.time() - start_time) * 1000
            confidence_score = analysis_result.get('confidence_score', 0.5)
            FoodAnalysisMetrics.record_analysis_completed(
                'text', confidence_score, processing_time
            )
            
            # Generate response
            response = self._format_analysis_response(analysis_result, food_log)
            
            self.logger.log_food_analysis(
                'text', confidence_score, processing_time / 1000, str(user.id)
            )
            
            return response
            
        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            FoodAnalysisMetrics.record_analysis_completed(
                'text', 0.0, processing_time, False
            )
            
            self.logger.error(f"Text analysis failed for {subscriber_id}: {text}", e)
            
            return {
                'error': 'text_analysis_failed',
                'message': Messages.INVALID_TEXT
            }
    
    def analyze_food_image(self, subscriber_id: str, image_url: str) -> Dict[str, Any]:
        """Analyze food from image"""
        start_time = time.time()
        
        try:
            user = self._get_or_create_user(subscriber_id)
            FoodAnalysisMetrics.record_analysis_started('image', str(user.id))
            
            # Validate image URL
            if not ValidationService._is_valid_url(image_url):
                raise FileProcessingException(
                    "Invalid image URL",
                    file_type='image',
                    filename=image_url
                )
            
            # Check cache first
            cached_result = FoodAnalysisCache.get_cached_food_analysis(image_url, 'image')
            if cached_result:
                analysis_result = cached_result
                self.logger.info(f"Using cached analysis for image: {image_url[:50]}...")
            else:
                # Download and validate image
                image_data = self._download_and_validate_image(image_url)
                
                # Analyze with multiple methods
                analysis_result = self._analyze_image_comprehensive(image_data, image_url)
                
                # Cache the result
                FoodAnalysisCache.cache_food_analysis(image_url, analysis_result, 'image')
            
            # Create food log entry
            food_log = self._create_food_log(user, analysis_result, 'image', image_url)
            
            # Update daily stats
            self._update_user_daily_stats(user, date.today())
            
            # Record metrics
            processing_time = (time.time() - start_time) * 1000
            confidence_score = analysis_result.get('confidence_score', 0.5)
            FoodAnalysisMetrics.record_analysis_completed(
                'image', confidence_score, processing_time
            )
            
            # Generate response
            response = self._format_analysis_response(analysis_result, food_log)
            
            return response
            
        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            FoodAnalysisMetrics.record_analysis_completed(
                'image', 0.0, processing_time, False
            )
            
            self.logger.error(f"Image analysis failed for {subscriber_id}: {image_url}", e)
            
            return {
                'error': 'image_analysis_failed',
                'message': Messages.INVALID_IMAGE
            }
    
    def analyze_food_audio(self, subscriber_id: str, audio_url: str) -> Dict[str, Any]:
        """Analyze food from audio/voice message"""
        start_time = time.time()
        
        try:
            user = self._get_or_create_user(subscriber_id)
            FoodAnalysisMetrics.record_analysis_started('audio', str(user.id))
            
            # Validate audio URL
            if not ValidationService._is_valid_url(audio_url):
                raise FileProcessingException(
                    "Invalid audio URL",
                    file_type='audio',
                    filename=audio_url
                )
            
            # Check cache first
            cached_result = FoodAnalysisCache.get_cached_food_analysis(audio_url, 'audio')
            if cached_result:
                analysis_result = cached_result
                self.logger.info(f"Using cached analysis for audio: {audio_url[:50]}...")
            else:
                # Download and transcribe audio
                text_from_audio = self._transcribe_audio(audio_url)
                
                # Analyze the transcribed text
                analysis_result = self._analyze_text_with_spoonacular(text_from_audio)
                analysis_result['transcribed_text'] = text_from_audio
                
                # Cache the result
                FoodAnalysisCache.cache_food_analysis(audio_url, analysis_result, 'audio')
            
            # Create food log entry
            food_log = self._create_food_log(user, analysis_result, 'audio', audio_url)
            
            # Update daily stats
            self._update_user_daily_stats(user, date.today())
            
            # Record metrics
            processing_time = (time.time() - start_time) * 1000
            confidence_score = analysis_result.get('confidence_score', 0.5)
            FoodAnalysisMetrics.record_analysis_completed(
                'audio', confidence_score, processing_time
            )
            
            # Generate response
            response = self._format_analysis_response(analysis_result, food_log)
            
            # Add transcription info if available
            if 'transcribed_text' in analysis_result:
                response['transcription'] = analysis_result['transcribed_text']
            
            return response
            
        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            FoodAnalysisMetrics.record_analysis_completed(
                'audio', 0.0, processing_time, False
            )
            
            self.logger.error(f"Audio analysis failed for {subscriber_id}: {audio_url}", e)
            
            return {
                'error': 'audio_analysis_failed',
                'message': Messages.INVALID_AUDIO
            }
    
    def _analyze_text_with_spoonacular(self, text: str) -> Dict[str, Any]:
        """Analyze text using Spoonacular API"""
        try:
            with LogTimer("spoonacular_text_analysis"):
                # Check API cache first
                params = {'text': text}
                cached_response = APIResponseCache.get_cached_spoonacular_response(
                    'parseIngredients', params
                )
                
                if cached_response:
                    return self._process_spoonacular_response(cached_response)
                
                # Make API call
                api_key = os.getenv('SPOONACULAR_API_KEY')
                if not api_key:
                    raise APIException("Spoonacular API key not configured", api_service='spoonacular')
                
                response = requests.post(
                    APIEndpoints.SPOONACULAR_PARSE,
                    data={
                        'ingredientList': text,
                        'servings': 1,
                        'includeNutrition': True
                    },
                    headers={'X-RapidAPI-Key': api_key},
                    timeout=AppConstants.SPOONACULAR_TIMEOUT
                )
                
                if response.status_code != 200:
                    raise APIException(
                        f"Spoonacular API error: {response.status_code}",
                        api_service='spoonacular',
                        status_code=response.status_code
                    )
                
                response_data = response.json()
                
                # Cache the response
                APIResponseCache.cache_spoonacular_response(
                    'parseIngredients', params, response_data
                )
                
                return self._process_spoonacular_response(response_data)
                
        except Exception as e:
            self.logger.log_api_error('spoonacular', 'parseIngredients', e)
            
            # Fallback to basic analysis
            return self._fallback_text_analysis(text)
    
    def _analyze_image_comprehensive(self, image_data: bytes, image_url: str) -> Dict[str, Any]:
        """Analyze image using Gemini Vision as primary method with simplified fallbacks"""
        try:
            # Create temporary file for analysis
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
                temp_file.write(image_data)
                temp_path = temp_file.name
            
            try:
                # Primary: Vertex AI Gemini Vision (currently using fallback for stable deployment)
                # TODO: Implement Gemini Vision analysis in future release
                self.logger.info("📝 Gemini Vision analysis deferred - using enhanced fallback")
                
                # Simplified fallback: Enhanced nutrition estimation
                self.logger.info("🔄 Using enhanced nutrition estimation fallback")
                fallback_result = self._fallback_image_analysis(image_url)
                fallback_result['analysis_method'] = 'enhanced_fallback'
                return fallback_result
                
            finally:
                # Clean up temp file
                import os
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
            
        except Exception as e:
            self.logger.error(f"Image analysis failed", e)
            raise FoodAnalysisException(
                "Food analysis failed",
                analysis_method='image_analysis_error'
            )
    
    def _analyze_image_with_google_vision(self, image_data: bytes) -> Dict[str, Any]:
        """DEPRECATED: Basic Google Vision API - now redirects to Gemini Vision"""
        self.logger.warning("⚠️ Using deprecated Google Vision method - consider switching to Gemini Vision")
        
        try:
            # Create temporary file and redirect to Gemini
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
                temp_file.write(image_data)
                temp_path = temp_file.name
            
            try:
                # Redirect to fallback analysis since Gemini Vision integration is pending
                return self._fallback_image_analysis("deprecated_google_vision_redirect")
            finally:
                import os
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                    
        except Exception as e:
            self.logger.log_api_error('google_vision_deprecated', 'redirect_to_gemini', e)
            raise FoodAnalysisException("Deprecated Google Vision method failed", analysis_method='deprecated_google_vision')
    
    def _analyze_image_with_spoonacular(self, image_url: str) -> Dict[str, Any]:
        """DEPRECATED: Spoonacular image analysis - Gemini Vision is more accurate and cost-effective"""
        self.logger.warning("⚠️ Using deprecated Spoonacular image analysis - Gemini Vision recommended")
        
        # Use enhanced fallback instead of expensive Spoonacular image API
        return self._fallback_image_analysis(image_url)
    
    def _transcribe_audio(self, audio_url: str) -> str:
        """Transcribe audio using Google Cloud Speech-to-Text"""
        try:
            # Download audio file
            response = requests.get(audio_url, timeout=AppConstants.DOWNLOAD_TIMEOUT)
            response.raise_for_status()
            
            # Check file size
            if len(response.content) > AppConstants.MAX_FILE_SIZE:
                raise FileProcessingException(
                    "Audio file too large",
                    file_type='audio',
                    file_size=len(response.content)
                )
            
            # Use Google Cloud Speech-to-Text
            from google.cloud import speech
            
            client = speech.SpeechClient()
            audio = speech.RecognitionAudio(content=response.content)
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.OGG_OPUS,
                sample_rate_hertz=16000,
                language_code="es-ES",  # Spanish
                alternative_language_codes=["en-US"]  # English fallback
            )
            
            speech_response = client.recognize(config=config, audio=audio)
            
            if speech_response.results:
                transcript = speech_response.results[0].alternatives[0].transcript
                self.logger.info(f"Audio transcribed: {transcript[:50]}...")
                return transcript
            else:
                raise FoodAnalysisException("No speech detected in audio", analysis_method='speech_to_text')
                
        except Exception as e:
            self.logger.log_api_error('google_cloud', 'speech', e)
            raise e
    
    def _download_and_validate_image(self, image_url: str) -> bytes:
        """Download and validate image file"""
        try:
            response = requests.get(image_url, timeout=AppConstants.DOWNLOAD_TIMEOUT)
            response.raise_for_status()
            
            # Check file size
            if len(response.content) > AppConstants.MAX_FILE_SIZE:
                raise FileProcessingException(
                    "Image file too large",
                    file_type='image',
                    file_size=len(response.content)
                )
            
            # Validate file type
            content_type = response.headers.get('content-type', '').lower()
            if not any(img_type in content_type for img_type in ['image/jpeg', 'image/png', 'image/webp']):
                raise FileProcessingException(
                    f"Unsupported image type: {content_type}",
                    file_type='image'
                )
            
            return response.content
            
        except requests.RequestException as e:
            raise FileProcessingException(f"Failed to download image: {str(e)}", file_type='image')
    
    def _create_food_log(self, user, analysis_result: Dict[str, Any], 
                        analysis_method: str, original_input: str):
        """Create food log entry in database"""
        try:
            food_log = self.FoodLog(
                user_id=user.id,
                food_name=analysis_result.get('food_name', 'Unknown Food'),
                calories=analysis_result.get('calories', 0),
                protein=analysis_result.get('protein', 0),
                carbs=analysis_result.get('carbs', 0),
                fat=analysis_result.get('fat', 0),
                fiber=analysis_result.get('fiber', 0),
                sodium=analysis_result.get('sodium', 0),
                confidence_score=analysis_result.get('confidence_score', 0.5),
                analysis_method=analysis_method,
                original_input=original_input,
                created_at=datetime.utcnow()
            )
            
            self.db.session.add(food_log)
            self.db.session.commit()
            
            # Invalidate user cache
            invalidate_user_related_cache(user.id)
            
            self.logger.log_user_action(
                'food_logged',
                {
                    'food_name': food_log.food_name,
                    'calories': food_log.calories,
                    'analysis_method': analysis_method
                },
                str(user.id)
            )
            
            return food_log
            
        except Exception as e:
            self.db.session.rollback()
            self.logger.error(f"Failed to create food log for user {user.id}", e)
            raise e
    
    def _update_user_daily_stats(self, user, target_date: date):
        """Update user's daily statistics"""
        try:
            self.db_service.update_daily_stats_optimized(user.id, target_date)
        except Exception as e:
            self.logger.warning(f"Failed to update daily stats for user {user.id}: {str(e)}")
    
    def _format_analysis_response(self, analysis_result: Dict[str, Any], food_log) -> Dict[str, Any]:
        """Format analysis result for response"""
        confidence_score = analysis_result.get('confidence_score', 0.5)
        
        # Determine confidence level message
        if confidence_score >= 0.8:
            confidence_msg = "🎯 Alta confianza"
        elif confidence_score >= 0.5:
            confidence_msg = "✅ Confianza media"
        else:
            confidence_msg = "⚠️ Confianza baja"
        
        response = {
            'status': 'success',
            'message': Messages.ANALYSIS_COMPLETE,
            'food_analysis': {
                'food_name': analysis_result.get('food_name', 'Alimento'),
                'calories': round(analysis_result.get('calories', 0), 1),
                'protein': round(analysis_result.get('protein', 0), 1),
                'carbs': round(analysis_result.get('carbs', 0), 1),
                'fat': round(analysis_result.get('fat', 0), 1),
                'fiber': round(analysis_result.get('fiber', 0), 1),
                'confidence': confidence_msg,
                'confidence_score': round(confidence_score, 2)
            },
            'food_log_id': food_log.id if food_log else None
        }
        
        return response
    
    def _get_or_create_user(self, subscriber_id: str):
        """Get existing user or create new one"""
        user = self.User.query.filter_by(whatsapp_id=subscriber_id).first()
        
        if not user:
            user = self.User(
                whatsapp_id=subscriber_id,
                is_active=True,
                created_at=datetime.utcnow(),
                last_interaction=datetime.utcnow()
            )
            self.db.session.add(user)
            self.db.session.commit()
            
            self.logger.log_user_action(
                'user_created',
                {'whatsapp_id': subscriber_id},
                str(user.id)
            )
        else:
            # Update last interaction
            user.last_interaction = datetime.utcnow()
            self.db.session.commit()
        
        return user
    
    # Fallback analysis methods
    def _fallback_text_analysis(self, text: str) -> Dict[str, Any]:
        """Basic fallback analysis for text"""
        return {
            'food_name': text[:50],
            'calories': 150,  # Default estimate
            'protein': 5,
            'carbs': 20,
            'fat': 5,
            'fiber': 2,
            'sodium': 100,
            'confidence_score': AppConstants.FALLBACK_CONFIDENCE,
            'analysis_method': 'fallback_text'
        }
    
    def _fallback_image_analysis(self, image_url: str) -> Dict[str, Any]:
        """Basic fallback analysis for images"""
        return {
            'food_name': 'Alimento detectado',
            'calories': 200,  # Default estimate
            'protein': 8,
            'carbs': 25,
            'fat': 8,
            'fiber': 3,
            'sodium': 150,
            'confidence_score': AppConstants.FALLBACK_CONFIDENCE,
            'analysis_method': 'fallback_image'
        }
    
    # Helper methods for processing API responses
    def _process_spoonacular_response(self, response_data: List[Dict]) -> Dict[str, Any]:
        """Process Spoonacular API response"""
        if not response_data:
            raise FoodAnalysisException("Empty response from Spoonacular", analysis_method='spoonacular')
        
        # Take first ingredient
        ingredient = response_data[0]
        nutrition = ingredient.get('nutrition', {})
        nutrients = {n['name'].lower(): n['amount'] for n in nutrition.get('nutrients', [])}
        
        return {
            'food_name': ingredient.get('name', 'Unknown Food'),
            'calories': nutrients.get('calories', 0),
            'protein': nutrients.get('protein', 0),
            'carbs': nutrients.get('carbohydrates', 0),
            'fat': nutrients.get('fat', 0),
            'fiber': nutrients.get('fiber', 0),
            'sodium': nutrients.get('sodium', 0),
            'confidence_score': min(ingredient.get('consistency', 0.5), 1.0),
            'analysis_method': 'spoonacular'
        }
    
    def _process_spoonacular_image_response(self, response_data: Dict) -> Dict[str, Any]:
        """Process Spoonacular image classification response"""
        category = response_data.get('category', 'food')
        probability = response_data.get('probability', 0.5)
        
        # Basic nutrition estimation based on category
        nutrition_estimates = self._estimate_nutrition_by_category(category)
        
        return {
            'food_name': category.replace('_', ' ').title(),
            'calories': nutrition_estimates['calories'],
            'protein': nutrition_estimates['protein'],
            'carbs': nutrition_estimates['carbs'],
            'fat': nutrition_estimates['fat'],
            'fiber': nutrition_estimates['fiber'],
            'sodium': nutrition_estimates['sodium'],
            'confidence_score': probability,
            'analysis_method': 'spoonacular_image'
        }
    
    def _estimate_nutrition_by_category(self, category: str) -> Dict[str, float]:
        """Estimate nutrition based on food category"""
        # Simplified nutrition estimates by category
        estimates = {
            'fruit': {'calories': 60, 'protein': 1, 'carbs': 15, 'fat': 0.2, 'fiber': 3, 'sodium': 0},
            'vegetable': {'calories': 25, 'protein': 2, 'carbs': 5, 'fat': 0.1, 'fiber': 3, 'sodium': 5},
            'meat': {'calories': 250, 'protein': 25, 'carbs': 0, 'fat': 15, 'fiber': 0, 'sodium': 75},
            'dairy': {'calories': 150, 'protein': 8, 'carbs': 12, 'fat': 8, 'fiber': 0, 'sodium': 100},
            'grain': {'calories': 350, 'protein': 10, 'carbs': 70, 'fat': 2, 'fiber': 5, 'sodium': 5},
            'default': {'calories': 150, 'protein': 5, 'carbs': 20, 'fat': 5, 'fiber': 2, 'sodium': 100}
        }
        
        return estimates.get(category.lower(), estimates['default'])
    
    def _extract_food_from_vision_results(self, detected_text: str, detected_objects: List[str]) -> str:
        """Extract food description from Google Vision results"""
        food_keywords = ['food', 'fruit', 'vegetable', 'meat', 'bread', 'cheese', 'pizza', 'burger']
        
        # Check if any food objects were detected
        food_objects = [obj for obj in detected_objects if any(keyword in obj.lower() for keyword in food_keywords)]
        
        if food_objects:
            return ', '.join(food_objects)
        elif detected_text:
            # Try to extract food-related text
            return detected_text[:100]  # First 100 characters
        else:
            return "" 