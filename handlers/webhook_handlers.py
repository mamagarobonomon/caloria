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

class ManyChannelWebhookHandler:
    """Handler for ManyChat webhook requests"""
    
    def __init__(self, db, user_model, food_log_model):
        self.db = db
        self.User = user_model
        self.FoodLog = food_log_model
        self.logger = caloria_logger
    
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
        """Route webhook content to appropriate handler"""
        subscriber_id = data['subscriber_id']
        
        # Check for different content types
        if 'text' in data and data['text']:
            return self._handle_text_message(subscriber_id, data['text'])
        
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
        from handlers.food_analysis_handlers import FoodAnalysisHandler
        
        # Initialize food analysis handler
        food_handler = FoodAnalysisHandler(self.db, self.User, self.FoodLog)
        
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
        """Handle image message from user"""
        from handlers.food_analysis_handlers import FoodAnalysisHandler
        
        food_handler = FoodAnalysisHandler(self.db, self.User, self.FoodLog)
        return food_handler.analyze_food_image(subscriber_id, image_url)
    
    def _handle_attachment_message(self, subscriber_id: str, attachment_url: str) -> Dict[str, Any]:
        """Handle attachment (audio/voice) message from user"""
        from handlers.food_analysis_handlers import FoodAnalysisHandler
        
        food_handler = FoodAnalysisHandler(self.db, self.User, self.FoodLog)
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
        
        quiz_handler = QuizHandler(self.db, self.User)
        return quiz_handler.process_quiz_input(subscriber_id, text)
    
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
        
        return user

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
            db, models['User'], models['FoodLog']
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