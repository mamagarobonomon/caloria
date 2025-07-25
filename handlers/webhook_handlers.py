"""
Webhook Handlers for Caloria Application
Modular handlers for different webhook types to improve code organization
"""

import json
import requests
import time
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
from flask import request

from config.constants import AppConstants, StatusCodes, Messages, APIEndpoints
from services.validation_service import ValidationService, SecurityService
from services.logging_service import caloria_logger, LogTimer
from services.metrics_service import WebhookMetrics
from services.caching_service import invalidate_user_related_cache
from exceptions import WebhookValidationException, APIException

# Add imports for enhanced food analysis
from handlers.enhanced_food_analysis import EnhancedFoodAnalysisHandler
from handlers.food_analysis_handlers import FoodAnalysisHandler
from handlers.quiz_handlers import QuizHandler

class ManyChannelWebhookHandler:
    """Handler for ManyChat webhook requests"""
    
    def __init__(self, db, models):
        self.db = db
        self.models = models
        self.logger = caloria_logger
        
        # Initialize handlers
        self.food_analysis_handler = FoodAnalysisHandler(db, models['User'], models['FoodLog'])
        
        # NEW: Initialize enhanced food analysis handler
        self.enhanced_food_handler = EnhancedFoodAnalysisHandler(db, models['User'], models['FoodLog'])
        
        self.quiz_handler = QuizHandler(db, models['User'])
    
    def process_webhook(self, request_data: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
        """Process ManyChat webhook with comprehensive validation and handling"""
        start_time = time.time()
        
        try:
            # Record webhook reception
            webhook_type = request_data.get('type', 'manychat')
            user_id = request_data.get('id', 'unknown')
            WebhookMetrics.record_webhook_received(webhook_type, user_id)
            
            self.logger.log_webhook_received(
                webhook_type, 
                len(json.dumps(request_data)), 
                user_id
            )
            
            # Validate webhook data
            errors, cleaned_data = ValidationService.validate_webhook_input(request_data)
            if errors:
                raise WebhookValidationException(
                    f"Validation failed: {', '.join(errors)}",
                    webhook_type=webhook_type,
                    missing_fields=errors
                )
            
            # Process based on content type
            response_data = self._route_webhook_content(cleaned_data)
            
            # Record successful processing
            processing_time = (time.time() - start_time) * 1000
            WebhookMetrics.record_webhook_processed(
                webhook_type, True, processing_time, user_id
            )
            
            self.logger.log_webhook_processed(
                webhook_type, processing_time / 1000, True, user_id
            )
            
            return response_data, StatusCodes.OK
            
        except WebhookValidationException as e:
            processing_time = (time.time() - start_time) * 1000
            WebhookMetrics.record_webhook_processed(
                webhook_type, False, processing_time, user_id
            )
            
            self.logger.log_webhook_error(
                webhook_type, e, json.dumps(request_data)[:500], user_id
            )
            
            return {
                'error': 'Validation failed',
                'message': Messages.INVALID_TEXT,
                'details': e.details
            }, StatusCodes.BAD_REQUEST
            
        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            WebhookMetrics.record_webhook_processed(
                webhook_type, False, processing_time, user_id
            )
            
            self.logger.log_webhook_error(
                webhook_type, e, json.dumps(request_data)[:500], user_id
            )
            
            return {
                'error': 'Processing failed',
                'message': Messages.SYSTEM_ERROR
            }, StatusCodes.INTERNAL_ERROR
    
    def _route_webhook_content(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Route webhook content to appropriate handler with enhanced analysis support"""
        subscriber_id = data['subscriber_id']
        
        # Check for quick reply (button press) first
        if 'quick_reply' in data:
            payload = data['quick_reply'].get('payload', '')
            return self._handle_quick_reply_message(subscriber_id, payload)
        
        # Check for different content types
        elif 'text' in data and data['text']:
            # Check if this might be a clarification for pending analysis
            return self._handle_text_clarification(subscriber_id, data['text'])
        
        elif 'image_url' in data or 'url' in data:
            image_url = data.get('image_url') or data.get('url')
            return self._handle_image_message(subscriber_id, image_url)
        
        elif 'attachment_url' in data:
            return self._handle_attachment_message(subscriber_id, data['attachment_url'])
        
        else:
            # Check for user profile updates
            if any(field in data for field in ['first_name', 'last_name']):
                return self._handle_profile_update(subscriber_id, data)
            
            return {
                'status': 'received',
                'message': 'No actionable content found'
            }
    
    def _handle_text_message(self, subscriber_id: str, text: str) -> Dict[str, Any]:
        """Handle text message from user"""
        
        # Use the initialized food analysis handler
        food_handler = self.food_analysis_handler
        
        # Check for special commands
        text_lower = text.lower().strip()
        
        if text_lower in ['help', 'ayuda', '?']:
            return {'message': Messages.HELP_TEXT}
        
        elif text_lower in ['reset', 'reiniciar', 'restart']:
            return self._handle_reset_command(subscriber_id)
        
        elif text_lower.startswith('quiz'):
            return self._handle_quiz_command(subscriber_id, text)
        
        else:
            # Treat as food description
            return food_handler.analyze_food_text(subscriber_id, text)
    
    def _handle_image_message(self, subscriber_id: str, image_url: str) -> Dict[str, Any]:
        """Handle image message with enhanced analysis and clarification"""
        
        # Use enhanced food analysis handler for images
        self.logger.info(f"🔍 Starting enhanced food analysis for {subscriber_id}")
        
        try:
            # Step 1: Analyze photo and generate clarification questions
            analysis_response = self.enhanced_food_handler.analyze_food_photo_with_clarification(
                subscriber_id, image_url
            )
            
            if 'error' in analysis_response:
                # Fallback to basic analysis if enhanced fails
                self.logger.warning("Enhanced analysis failed, using fallback")
                basic_response = self.food_analysis_handler.analyze_food_image(subscriber_id, image_url)
                return {'message': basic_response.get('message', 'Analysis completed')}
            
            # Return clarification response with buttons (convert to ManyChat format)
            return self._convert_enhanced_response_to_manychat(analysis_response)
            
        except Exception as e:
            # Final fallback to basic analysis
            self.logger.error(f"Enhanced image analysis failed: {str(e)}")
            from handlers.food_analysis_handlers import FoodAnalysisHandler
            food_handler = FoodAnalysisHandler(self.db, self.models['User'], self.models['FoodLog'])
            return food_handler.analyze_food_image(subscriber_id, image_url)
    
    def _handle_attachment_message(self, subscriber_id: str, attachment_url: str) -> Dict[str, Any]:
        """Handle attachment (audio/voice) message from user"""
        from handlers.food_analysis_handlers import FoodAnalysisHandler
        
        food_handler = FoodAnalysisHandler(self.db, self.models['User'], self.models['FoodLog'])
        return food_handler.analyze_food_audio(subscriber_id, attachment_url)
    
    def _handle_profile_update(self, subscriber_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle user profile update"""
        try:
            user = self._get_or_create_user(subscriber_id)
            
            # Update available fields
            if 'first_name' in data:
                user.first_name = data['first_name']
            if 'last_name' in data:
                user.last_name = data['last_name']
            
            user.last_interaction = datetime.utcnow()
            self.db.session.commit()
            
            # Invalidate user cache
            invalidate_user_related_cache(user.id)
            
            self.logger.log_user_action(
                'profile_updated',
                {'fields': list(data.keys())},
                str(user.id)
            )
            
            return {
                'status': 'profile_updated',
                'message': '✅ Perfil actualizado correctamente'
            }
            
        except Exception as e:
            self.db.session.rollback()
            self.logger.error(f"Profile update failed for {subscriber_id}", e)
            return {
                'error': 'profile_update_failed',
                'message': Messages.SYSTEM_ERROR
            }
    
    def _handle_reset_command(self, subscriber_id: str) -> Dict[str, Any]:
        """Handle user reset command"""
        try:
            user = self._get_or_create_user(subscriber_id)
            
            # Reset user's daily progress
            user.quiz_completed = False
            user.current_quiz_step = 0
            user.last_interaction = datetime.utcnow()
            self.db.session.commit()
            
            # Invalidate user cache
            invalidate_user_related_cache(user.id)
            
            self.logger.log_user_action('user_reset', user_id=str(user.id))
            
            return {
                'status': 'reset_completed',
                'message': '🔄 Estado reiniciado. ¡Empecemos de nuevo!'
            }
            
        except Exception as e:
            self.db.session.rollback()
            self.logger.error(f"Reset failed for {subscriber_id}", e)
            return {
                'error': 'reset_failed',
                'message': Messages.SYSTEM_ERROR
            }
    
    def _handle_quiz_command(self, subscriber_id: str, text: str) -> Dict[str, Any]:
        """Handle quiz-related commands"""
        from handlers.quiz_handlers import QuizHandler
        
        quiz_handler = QuizHandler(self.db, self.models['User'])
        return quiz_handler.process_quiz_input(subscriber_id, text)
    
    def _get_or_create_user(self, subscriber_id: str):
        """Get existing user or create new one with language detection"""
        user = self.models['User'].query.filter_by(whatsapp_id=subscriber_id).first()
        
        if not user:
            user = self.models['User'](
                whatsapp_id=subscriber_id,
                is_active=True,
                language='es',  # Default to Spanish
                created_at=datetime.utcnow(),
                last_interaction=datetime.utcnow()
            )
            self.db.session.add(user)
            self.db.session.commit()
            
            self.logger.log_user_action(
                'user_created',
                {'whatsapp_id': subscriber_id, 'language': 'es'},
                str(user.id)
            )
        else:
            # Update last interaction
            user.last_interaction = datetime.utcnow()
            self.db.session.commit()
        
        return user

    def _convert_enhanced_response_to_manychat(self, enhanced_response: Dict[str, Any]) -> Dict[str, Any]:
        """Convert enhanced analysis response to ManyChat format"""
        if 'content' in enhanced_response and 'messages' in enhanced_response['content']:
            message = enhanced_response['content']['messages'][0]
            return {
                'message': message['text'],
                'quick_replies': message.get('quick_replies', []),
                'session_key': enhanced_response.get('session_key')
            }
        
        return {'message': 'Analysis completed'}
    
    def _handle_quick_reply_message(self, subscriber_id: str, payload: str) -> Dict[str, Any]:
        """Handle quick reply button presses (Analyze/New Log) - BILINGUAL"""
        try:
            user = self._get_or_create_user(subscriber_id)
            user_lang = user.language or 'es'  # Default to Spanish
            
            self.logger.info(f"📱 Processing quick reply: {payload} for {subscriber_id} in {user_lang}")
            
            if payload.startswith('analyze_food:'):
                # Extract session key from payload
                session_key = payload.replace('analyze_food:', '')
                
                # Process final analysis without additional clarifications
                analysis_response = self.enhanced_food_handler.process_user_clarification(
                    subscriber_id, session_key, user_input=None
                )
                
                # Convert multi-part response to single message for ManyChat
                return self._convert_multipart_response(analysis_response)
                
            elif payload == 'new_food_log':
                # Reset and prompt for new food log (language-aware)
                messages = {
                    'es': '📸 ¡Listo para un nuevo registro! Envíame una foto de tu comida o describe lo que comiste.',
                    'en': '📸 Ready for a new food log! Send me a photo of your meal, or describe what you ate.'
                }
                return {
                    'message': messages.get(user_lang, messages['es'])
                }
            
            elif payload.startswith('set_language:'):
                # Handle language switching
                new_lang = payload.replace('set_language:', '')
                if new_lang in ['es', 'en']:
                    user.language = new_lang
                    self.db.session.commit()
                    
                    welcome_messages = {
                        'es': '🇪🇸 Idioma cambiado a español. ¡Ahora puedes enviar fotos de tu comida para análisis nutricional!',
                        'en': '🇺🇸 Language switched to English. Now you can send photos of your food for nutritional analysis!'
                    }
                    return {
                        'message': welcome_messages[new_lang],
                        'language_set': new_lang
                    }
            
            else:
                error_messages = {
                    'es': 'Acción desconocida. Por favor intenta de nuevo.',
                    'en': 'Unknown action. Please try again.'
                }
                return {'message': error_messages.get(user_lang, error_messages['es'])}
                
        except Exception as e:
            user_lang = getattr(self._get_or_create_user(subscriber_id), 'language', 'es')
            self.logger.error(f"Quick reply handling failed: {str(e)}", e)
            error_messages = {
                'es': '❌ Lo siento, algo salió mal. Por favor intenta de nuevo.',
                'en': '❌ Sorry, something went wrong. Please try again.'
            }
            return {'message': error_messages.get(user_lang, error_messages['es'])}

    def _convert_multipart_response(self, analysis_response: Dict[str, Any]) -> Dict[str, Any]:
        """Convert multi-part analysis response to single ManyChat message"""
        if 'content' in analysis_response and 'messages' in analysis_response['content']:
            messages = analysis_response['content']['messages']
            
            # Combine all messages into one with separators
            combined_text = []
            for i, msg in enumerate(messages):
                if i > 0:  # Add separator between messages
                    combined_text.append("---")
                combined_text.append(msg['text'])
            
            return {
                'message': '\n\n'.join(combined_text),
                'analysis_complete': True
            }
        
        return {'message': 'Analysis completed'}
    
    def _handle_text_clarification(self, subscriber_id: str, text: str) -> Dict[str, Any]:
        """Handle text messages that might be clarifications for pending analysis"""
        try:
            # Check if there's a pending analysis session for this user
            session_key = self._get_pending_session_key(subscriber_id)
            
            if session_key:
                # Process as clarification
                self.logger.info(f"🔍 Processing clarification for session {session_key}")
                analysis_response = self.enhanced_food_handler.process_user_clarification(
                    subscriber_id, session_key, user_input=text
                )
                
                return self._convert_multipart_response(analysis_response)
            
            else:
                # Handle as regular text analysis
                return self._handle_regular_text_analysis(subscriber_id, text)
                
        except Exception as e:
            self.logger.error(f"Text clarification handling failed: {str(e)}", e)
            return self._handle_regular_text_analysis(subscriber_id, text)

    def _handle_regular_text_analysis(self, subscriber_id: str, text: str) -> Dict[str, Any]:
        """Handle regular text-based food analysis - BILINGUAL"""
        try:
            # Check for quiz flow first
            user = self._get_or_create_user(subscriber_id)
            user_lang = user.language or 'es'
            
            if not user.quiz_completed:
                # Handle quiz response
                quiz_response = self.quiz_handler.handle_quiz_response(user, {
                    'text': text,
                    'subscriber_id': subscriber_id
                })
                return {'message': quiz_response.get('message', 'Quiz response processed')}
            
            # Handle food analysis
            analysis_response = self.food_analysis_handler.analyze_food_text(subscriber_id, text)
            
            if 'error' in analysis_response:
                error_messages = {
                    'es': '❌ Lo siento, no pude analizar tu descripción de comida. Por favor intenta de nuevo.',
                    'en': '❌ Sorry, I couldn\'t analyze your food description. Please try again.'
                }
                return {'message': error_messages.get(user_lang, error_messages['es'])}
            
            return {'message': analysis_response.get('message', 'Food analysis completed')}
            
        except Exception as e:
            user_lang = getattr(self._get_or_create_user(subscriber_id), 'language', 'es')
            self.logger.error(f"Regular text analysis failed: {str(e)}", e)
            error_messages = {
                'es': '❌ Lo siento, algo salió mal. Por favor intenta de nuevo.',
                'en': '❌ Sorry, something went wrong. Please try again.'
            }
            return {'message': error_messages.get(user_lang, error_messages['es'])}

    def _detect_user_language(self, data: Dict[str, Any], subscriber_id: str) -> str:
        """Detect user language from message content or set default"""
        user = self._get_or_create_user(subscriber_id)
        
        # If user already has language set, use it
        if user.language:
            return user.language
        
        # Try to detect from message content
        text = data.get('text', '').lower()
        
        # Spanish indicators
        spanish_indicators = ['hola', 'comida', 'análisis', 'español', 'gracias', 'por favor']
        # English indicators  
        english_indicators = ['hello', 'food', 'analysis', 'english', 'thanks', 'please']
        
        spanish_score = sum(1 for word in spanish_indicators if word in text)
        english_score = sum(1 for word in english_indicators if word in text)
        
        detected_lang = 'en' if english_score > spanish_score else 'es'
        
        # Set detected language for user
        user.language = detected_lang
        self.db.session.commit()
        
        return detected_lang

    def _get_pending_session_key(self, subscriber_id: str) -> Optional[str]:
        """Get the most recent session key for user if exists"""
        try:
            from services.caching_service import cache
            
            # Look for recent session keys (within last hour)
            import time
            current_time = int(time.time())
            
            # Check last few minutes for active sessions
            for minutes_ago in range(60):  # Check last 60 minutes
                timestamp = current_time - (minutes_ago * 60)
                
                # Check various timestamp formats
                for time_offset in range(-30, 31):  # +/- 30 seconds
                    test_key = f"food_analysis_{subscriber_id}_{timestamp + time_offset}"
                    if cache.get(test_key):
                        return test_key
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error retrieving session key: {str(e)}")
            return None

class MercadoPagoWebhookHandler:
    """Handler for Mercado Pago webhook requests"""
    
    def __init__(self, db, user_model, subscription_model):
        self.db = db
        self.User = user_model
        self.Subscription = subscription_model
        self.logger = caloria_logger
    
    def process_webhook(self, request_data: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
        """Process Mercado Pago webhook"""
        start_time = time.time()
        
        try:
            webhook_type = request_data.get('type', 'mercadopago')
            WebhookMetrics.record_webhook_received(webhook_type)
            
            self.logger.log_webhook_received(
                webhook_type,
                len(json.dumps(request_data))
            )
            
            # Validate Mercado Pago webhook structure
            errors, cleaned_data = ValidationService.validate_mercadopago_webhook(request_data)
            if errors:
                raise WebhookValidationException(
                    f"MP webhook validation failed: {', '.join(errors)}",
                    webhook_type=webhook_type,
                    missing_fields=errors
                )
            
            # Process based on webhook type
            response_data = self._route_mp_webhook(cleaned_data)
            
            # Record successful processing
            processing_time = (time.time() - start_time) * 1000
            WebhookMetrics.record_webhook_processed(
                webhook_type, True, processing_time
            )
            
            return response_data, StatusCodes.OK
            
        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            WebhookMetrics.record_webhook_processed(
                webhook_type, False, processing_time
            )
            
            self.logger.log_webhook_error(
                webhook_type, e, json.dumps(request_data)[:500]
            )
            
            return {
                'error': 'MP webhook processing failed',
                'message': 'Failed to process payment webhook'
            }, StatusCodes.INTERNAL_ERROR
    
    def _route_mp_webhook(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Route Mercado Pago webhook to appropriate handler"""
        webhook_type = data['type']
        webhook_id = data['id']
        data_id = data['data']['id']
        
        if webhook_type == 'subscription_preapproval':
            return self._handle_subscription_webhook(data_id)
        
        elif webhook_type == 'subscription_authorized_payment':
            return self._handle_payment_webhook(data_id)
        
        else:
            self.logger.warning(f"Unknown MP webhook type: {webhook_type}")
            return {
                'status': 'ignored',
                'message': f'Webhook type {webhook_type} not handled'
            }
    
    def _handle_subscription_webhook(self, preapproval_id: str) -> Dict[str, Any]:
        """Handle subscription status changes"""
        try:
            # Fetch subscription details from Mercado Pago
            subscription_data = self._fetch_mp_subscription(preapproval_id)
            
            # Find user by MP subscription ID
            user = self.User.query.filter_by(
                mercadopago_subscription_id=preapproval_id
            ).first()
            
            if not user:
                self.logger.warning(f"User not found for MP subscription: {preapproval_id}")
                return {
                    'status': 'user_not_found',
                    'message': 'User not found for subscription'
                }
            
            # Update user subscription status
            old_status = user.subscription_status
            new_status = self._map_mp_status_to_user_status(subscription_data['status'])
            
            if old_status != new_status:
                user.subscription_status = new_status
                user.last_interaction = datetime.utcnow()
                
                if new_status == 'cancelled':
                    user.is_active = False
                
                self.db.session.commit()
                
                # Invalidate user cache
                invalidate_user_related_cache(user.id)
                
                self.logger.log_subscription_event(
                    'status_changed',
                    preapproval_id,
                    {
                        'old_status': old_status,
                        'new_status': new_status,
                        'mp_status': subscription_data['status']
                    },
                    str(user.id)
                )
            
            return {
                'status': 'processed',
                'subscription_status': new_status
            }
            
        except Exception as e:
            self.db.session.rollback()
            self.logger.error(f"Subscription webhook processing failed: {str(e)}", e)
            return {
                'error': 'subscription_processing_failed',
                'message': 'Failed to process subscription update'
            }
    
    def _handle_payment_webhook(self, payment_id: str) -> Dict[str, Any]:
        """Handle individual payment notifications"""
        try:
            # This would fetch payment details and update records
            self.logger.info(f"Processing payment webhook: {payment_id}")
            
            return {
                'status': 'processed',
                'payment_id': payment_id
            }
            
        except Exception as e:
            self.logger.error(f"Payment webhook processing failed: {str(e)}", e)
            return {
                'error': 'payment_processing_failed',
                'message': 'Failed to process payment update'
            }
    
    def _fetch_mp_subscription(self, preapproval_id: str) -> Dict[str, Any]:
        """Fetch subscription details from Mercado Pago API"""
        # This would make actual API call to MP
        # Placeholder implementation
        return {
            'id': preapproval_id,
            'status': 'authorized',
            'payer_id': 'unknown'
        }
    
    def _map_mp_status_to_user_status(self, mp_status: str) -> str:
        """Map Mercado Pago status to user subscription status"""
        status_mapping = {
            'pending': 'trial_pending',
            'authorized': 'active',
            'paused': 'paused',
            'cancelled': 'cancelled',
            'expired': 'expired'
        }
        return status_mapping.get(mp_status, 'unknown')

class WebhookRouter:
    """Central router for all webhook types"""
    
    def __init__(self, db, models):
        self.db = db
        self.models = models
        self.manychat_handler = ManyChannelWebhookHandler(
            db, models
        )
        self.mercadopago_handler = MercadoPagoWebhookHandler(
            db, models['User'], models.get('Subscription')
        )
    
    def route_webhook(self, webhook_type: str, request_data: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
        """Route webhook to appropriate handler"""
        try:
            if webhook_type == 'manychat':
                return self.manychat_handler.process_webhook(request_data)
            
            elif webhook_type == 'mercadopago':
                return self.mercadopago_handler.process_webhook(request_data)
            
            else:
                caloria_logger.warning(f"Unknown webhook type: {webhook_type}")
                return {
                    'error': 'unknown_webhook_type',
                    'message': f'Webhook type {webhook_type} not supported'
                }, StatusCodes.BAD_REQUEST
                
        except Exception as e:
            caloria_logger.error(f"Webhook routing failed for {webhook_type}", e)
            return {
                'error': 'webhook_routing_failed',
                'message': Messages.SYSTEM_ERROR
            }, StatusCodes.INTERNAL_ERROR 