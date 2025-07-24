"""
Sample Tests for Webhook Handlers
Demonstrates testing patterns and best practices for the Caloria application
"""

import pytest
import json
from unittest.mock import patch, Mock
from datetime import datetime

@pytest.mark.webhook
class TestManyChannelWebhookHandler:
    """Test ManyChat webhook functionality"""
    
    def test_text_webhook_creates_user_and_food_log(self, client, mock_manychat_webhook_data, mock_spoonacular_response):
        """Test that text webhook creates user and food log"""
        
        with patch('requests.post') as mock_post:
            # Mock Spoonacular API response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_spoonacular_response
            mock_post.return_value = mock_response
            
            # Send webhook request
            response = client.post(
                '/webhook/manychat',
                data=json.dumps(mock_manychat_webhook_data),
                content_type='application/json'
            )
            
            assert response.status_code == 200
            
            # Verify response contains food analysis
            response_data = json.loads(response.data)
            assert 'food_analysis' in response_data
            assert response_data['food_analysis']['food_name'] == 'apple'
            assert response_data['food_analysis']['calories'] == 95
    
    def test_invalid_webhook_data_returns_error(self, client):
        """Test that invalid webhook data returns validation error"""
        
        invalid_data = {
            "invalid": "data"
        }
        
        response = client.post(
            '/webhook/manychat',
            data=json.dumps(invalid_data),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        response_data = json.loads(response.data)
        assert 'error' in response_data
        assert 'validation' in response_data['error'].lower()
    
    def test_help_command_returns_help_text(self, client):
        """Test that help command returns help information"""
        
        help_data = {
            "id": "test_subscriber_123",
            "text": "help"
        }
        
        response = client.post(
            '/webhook/manychat',
            data=json.dumps(help_data),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert 'Cómo usar Caloria' in response_data['message']
    
    def test_quiz_start_command(self, client):
        """Test quiz start functionality"""
        
        quiz_data = {
            "id": "test_subscriber_123",
            "text": "quiz start"
        }
        
        response = client.post(
            '/webhook/manychat',
            data=json.dumps(quiz_data),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert 'quiz_status' in response_data
        assert response_data['quiz_status'] == 'started'
        assert 'next_step' in response_data
    
    @pytest.mark.slow
    def test_image_webhook_processing(self, client, sample_image_url):
        """Test image webhook processing"""
        
        image_data = {
            "id": "test_subscriber_123",
            "image_url": sample_image_url
        }
        
        with patch('requests.get') as mock_get, \
             patch('handlers.food_analysis_handlers.FoodAnalysisHandler._analyze_image_comprehensive') as mock_analyze:
            
            # Mock image download
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.content = b'fake_image_data'
            mock_response.headers = {'content-type': 'image/jpeg'}
            mock_get.return_value = mock_response
            
            # Mock image analysis
            mock_analyze.return_value = {
                'food_name': 'Pizza Slice',
                'calories': 285,
                'protein': 12,
                'carbs': 36,
                'fat': 10,
                'fiber': 2,
                'sodium': 640,
                'confidence_score': 0.82,
                'analysis_method': 'image'
            }
            
            response = client.post(
                '/webhook/manychat',
                data=json.dumps(image_data),
                content_type='application/json'
            )
            
            assert response.status_code == 200
            response_data = json.loads(response.data)
            assert 'food_analysis' in response_data
            assert response_data['food_analysis']['food_name'] == 'Pizza Slice'

@pytest.mark.webhook
class TestMercadoPagoWebhookHandler:
    """Test Mercado Pago webhook functionality"""
    
    def test_subscription_webhook_processing(self, client, test_user, mock_mercadopago_webhook_data):
        """Test subscription webhook processing"""
        
        # Update test user with MP subscription ID
        test_user.mercadopago_subscription_id = "MP-SUB-123456789"
        
        with patch('handlers.webhook_handlers.MercadoPagoWebhookHandler._fetch_mp_subscription') as mock_fetch:
            mock_fetch.return_value = {
                'id': 'MP-SUB-123456789',
                'status': 'authorized',
                'payer_id': 'test_payer'
            }
            
            response = client.post(
                '/webhook/mercadopago',
                data=json.dumps(mock_mercadopago_webhook_data),
                content_type='application/json'
            )
            
            assert response.status_code == 200
            response_data = json.loads(response.data)
            assert response_data['status'] == 'processed'
    
    def test_invalid_mp_webhook_returns_error(self, client):
        """Test that invalid MP webhook data returns error"""
        
        invalid_data = {
            "invalid": "webhook_data"
        }
        
        response = client.post(
            '/webhook/mercadopago',
            data=json.dumps(invalid_data),
            content_type='application/json'
        )
        
        assert response.status_code == 400

@pytest.mark.unit
class TestWebhookValidation:
    """Test webhook validation functionality"""
    
    def test_validate_webhook_input_success(self):
        """Test successful webhook input validation"""
        from services.validation_service import ValidationService
        
        valid_data = {
            "id": "test_subscriber_123",
            "text": "1 apple",
            "first_name": "Test",
            "last_name": "User"
        }
        
        errors, cleaned_data = ValidationService.validate_webhook_input(valid_data)
        
        assert len(errors) == 0
        assert cleaned_data['subscriber_id'] == "test_subscriber_123"
        assert cleaned_data['text'] == "1 apple"
        assert cleaned_data['first_name'] == "Test"
    
    def test_validate_webhook_input_missing_id(self):
        """Test webhook validation with missing subscriber ID"""
        from services.validation_service import ValidationService
        
        invalid_data = {
            "text": "1 apple"
        }
        
        errors, cleaned_data = ValidationService.validate_webhook_input(invalid_data)
        
        assert len(errors) > 0
        assert any("subscriber_id" in error for error in errors)
    
    def test_validate_webhook_input_text_too_long(self):
        """Test webhook validation with text too long"""
        from services.validation_service import ValidationService
        
        invalid_data = {
            "id": "test_subscriber_123",
            "text": "a" * 1001  # Exceeds MAX_TEXT_LENGTH
        }
        
        errors, cleaned_data = ValidationService.validate_webhook_input(invalid_data)
        
        assert len(errors) > 0
        assert any("too long" in error for error in errors)
    
    def test_validate_webhook_input_invalid_url(self):
        """Test webhook validation with invalid URL"""
        from services.validation_service import ValidationService
        
        invalid_data = {
            "id": "test_subscriber_123",
            "image_url": "not-a-valid-url"
        }
        
        errors, cleaned_data = ValidationService.validate_webhook_input(invalid_data)
        
        assert len(errors) > 0
        assert any("Invalid URL" in error for error in errors)

@pytest.mark.integration
class TestWebhookIntegration:
    """Integration tests for webhook functionality"""
    
    def test_complete_food_analysis_flow(self, client, integration_test_setup, mock_spoonacular_response):
        """Test complete food analysis flow from webhook to database"""
        
        webhook_data = {
            "id": "integration_test_user",
            "first_name": "Integration",
            "last_name": "Test",
            "text": "2 bananas"
        }
        
        with patch('requests.post') as mock_post:
            # Mock Spoonacular API
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_spoonacular_response
            mock_post.return_value = mock_response
            
            # Send webhook
            response = client.post(
                '/webhook/manychat',
                data=json.dumps(webhook_data),
                content_type='application/json'
            )
            
            assert response.status_code == 200
            
            # Verify user was created
            from app import User, FoodLog
            user = User.query.filter_by(whatsapp_id="integration_test_user").first()
            assert user is not None
            assert user.first_name == "Integration"
            
            # Verify food log was created
            food_log = FoodLog.query.filter_by(user_id=user.id).first()
            assert food_log is not None
            assert food_log.analysis_method == "text"
            assert food_log.original_input == "2 bananas"

@pytest.mark.unit
class TestWebhookMetrics:
    """Test webhook metrics collection"""
    
    def test_webhook_metrics_recorded(self):
        """Test that webhook metrics are properly recorded"""
        from services.metrics_service import WebhookMetrics, metrics
        
        # Reset metrics
        metrics.reset_metrics()
        
        # Record webhook events
        WebhookMetrics.record_webhook_received('manychat', 'test_user')
        WebhookMetrics.record_webhook_processed('manychat', True, 150.5, 'test_user')
        
        # Verify metrics were recorded
        assert metrics.get_counter_value('webhook_received') > 0
        assert metrics.get_counter_value('webhook_processed') > 0
        
        timing_stats = metrics.get_timing_stats('webhook_processing')
        assert timing_stats['count'] == 1
        assert timing_stats['avg_ms'] == 150.5

@pytest.mark.performance
class TestWebhookPerformance:
    """Performance tests for webhook processing"""
    
    def test_webhook_response_time(self, client, performance_timer, mock_spoonacular_response):
        """Test that webhook processing is within acceptable time limits"""
        
        webhook_data = {
            "id": "perf_test_user",
            "text": "1 apple"
        }
        
        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_spoonacular_response
            mock_post.return_value = mock_response
            
            performance_timer.start()
            
            response = client.post(
                '/webhook/manychat',
                data=json.dumps(webhook_data),
                content_type='application/json'
            )
            
            performance_timer.stop()
            
            assert response.status_code == 200
            
            # Webhook should respond within 2 seconds
            assert performance_timer.duration < 2.0
    
    def test_concurrent_webhook_processing(self, client):
        """Test handling of concurrent webhook requests"""
        import threading
        import time
        
        results = []
        
        def send_webhook(subscriber_id):
            webhook_data = {
                "id": f"concurrent_user_{subscriber_id}",
                "text": "help"
            }
            
            response = client.post(
                '/webhook/manychat',
                data=json.dumps(webhook_data),
                content_type='application/json'
            )
            
            results.append(response.status_code)
        
        # Send 5 concurrent requests
        threads = []
        for i in range(5):
            thread = threading.Thread(target=send_webhook, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # All requests should succeed
        assert len(results) == 5
        assert all(status == 200 for status in results) 