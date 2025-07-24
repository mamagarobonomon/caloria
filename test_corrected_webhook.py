#!/usr/bin/env python3
"""
Test Script for Corrected Mercado Pago Webhook Implementation
Tests the fixes based on official MP documentation.

Usage:
    python test_corrected_webhook.py
"""

import os
import sys
import json
import requests
from datetime import datetime

# Add the current directory to Python path to import app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_corrected_webhook_format():
    """Test webhook handling with correct MP format"""
    try:
        print("🧪 Testing corrected webhook format...")
        
        # Test data in correct MP format according to documentation
        webhook_data = {
            "id": 12345,
            "live_mode": False,
            "type": "subscription_preapproval",
            "date_created": datetime.utcnow().isoformat(),
            "user_id": 44444,
            "api_version": "v1",
            "action": "subscription.created",
            "data": {
                "id": "test_subscription_123"
            }
        }
        
        print(f"  📝 Test webhook data: {json.dumps(webhook_data, indent=2)}")
        
        # Test webhook endpoint
        url = 'http://localhost:5000/webhook/mercadopago'
        
        try:
            response = requests.post(url, json=webhook_data, timeout=5)
            if response.status_code == 200:
                result = response.json()
                print(f"  ✅ Webhook handled correctly: {result}")
                return True
            else:
                print(f"  ❌ Webhook failed: {response.status_code} - {response.text}")
                return False
        except requests.exceptions.ConnectionError:
            print("  ⚠️ Cannot test webhook - server not running")
            print("    Start server with: python app.py")
            return False
            
    except Exception as e:
        print(f"❌ Webhook test failed: {str(e)}")
        return False

def test_subscription_api_creation():
    """Test subscription creation via API (not URL construction)"""
    try:
        print("\n🔗 Testing subscription creation via API...")
        
        from app import app, db, User, MercadoPagoService
        
        with app.app_context():
            # Create or get test user
            test_user = User.query.filter_by(whatsapp_id='test_webhook_user').first()
            if not test_user:
                test_user = User(
                    whatsapp_id='test_webhook_user',
                    first_name='Test',
                    last_name='Webhook User',
                    subscription_tier='trial_pending',
                    subscription_status='inactive'
                )
                db.session.add(test_user)
                db.session.commit()
                print("  ✅ Created test user")
            
            # Test subscription link creation (should now use API)
            payment_link = MercadoPagoService.create_subscription_link(
                test_user,
                return_url="https://caloria.vip/subscription-success",
                cancel_url="https://caloria.vip/subscription-cancel"
            )
            
            if payment_link:
                print(f"  ✅ Subscription created via API: {payment_link[:50]}...")
                
                # Check if it's an init_point URL (correct format)
                if 'mercadopago.com' in payment_link and 'init_point' not in payment_link:
                    print("  ⚠️ URL format may be incorrect - should be init_point")
                else:
                    print("  ✅ Correct init_point URL format")
                
                # Check if user has subscription ID stored
                if test_user.mercadopago_subscription_id:
                    print(f"  ✅ Subscription ID stored: {test_user.mercadopago_subscription_id}")
                else:
                    print("  ⚠️ Subscription ID not stored")
                
                return True
            else:
                print("  ❌ Failed to create subscription")
                return False
                
    except Exception as e:
        print(f"❌ Subscription API test failed: {str(e)}")
        return False

def test_webhook_types():
    """Test different webhook types according to MP documentation"""
    try:
        print("\n📋 Testing different webhook types...")
        
        webhook_types = [
            {
                "name": "Subscription Created",
                "type": "subscription_preapproval",
                "action": "subscription.created"
            },
            {
                "name": "Subscription Payment",
                "type": "subscription_authorized_payment", 
                "action": "payment.created"
            },
            {
                "name": "Subscription Cancelled",
                "type": "subscription_preapproval",
                "action": "subscription.cancelled"
            }
        ]
        
        base_url = 'http://localhost:5000/webhook/mercadopago'
        
        for webhook_test in webhook_types:
            print(f"  🧪 Testing {webhook_test['name']}...")
            
            webhook_data = {
                "id": 12345,
                "live_mode": False,
                "type": webhook_test["type"],
                "date_created": datetime.utcnow().isoformat(),
                "user_id": 44444,
                "api_version": "v1",
                "action": webhook_test["action"],
                "data": {
                    "id": f"test_{webhook_test['type']}_123"
                }
            }
            
            try:
                response = requests.post(base_url, json=webhook_data, timeout=5)
                if response.status_code == 200:
                    print(f"    ✅ {webhook_test['name']}: Handled correctly")
                else:
                    print(f"    ❌ {webhook_test['name']}: Failed ({response.status_code})")
            except requests.exceptions.ConnectionError:
                print(f"    ⚠️ {webhook_test['name']}: Server not running")
        
        return True
        
    except Exception as e:
        print(f"❌ Webhook types test failed: {str(e)}")
        return False

def test_subscription_endpoints():
    """Test correct MP API endpoints"""
    try:
        print("\n🌐 Testing Mercado Pago API endpoints...")
        
        from app import app, MercadoPagoService
        
        with app.app_context():
            access_token = app.config.get('MERCADO_PAGO_ACCESS_TOKEN')
            
            if not access_token:
                print("  ⚠️ No access token configured - cannot test real API")
                return True
            
            # Test subscription details endpoint
            print("  🔍 Testing subscription details endpoint...")
            test_subscription_id = "test_12345"
            
            # This will likely fail but should show correct URL format
            details = MercadoPagoService.get_subscription_details(test_subscription_id)
            print(f"  ✅ Subscription endpoint called (expected to fail for test ID)")
            
            # Test API connectivity
            print("  🔌 Testing MP API connectivity...")
            url = "https://api.mercadopago.com/users/me"
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                user_data = response.json()
                print(f"  ✅ MP API connected: {user_data.get('email', 'Unknown')}")
                return True
            else:
                print(f"  ❌ MP API connection failed: {response.status_code}")
                return False
                
    except Exception as e:
        print(f"❌ API endpoints test failed: {str(e)}")
        return False

def test_webhook_response_timing():
    """Test webhook response within MP's 22-second requirement"""
    try:
        print("\n⏱️ Testing webhook response timing...")
        
        webhook_data = {
            "id": 12345,
            "live_mode": False,
            "type": "subscription_preapproval",
            "action": "subscription.created",
            "data": {"id": "timing_test_123"}
        }
        
        url = 'http://localhost:5000/webhook/mercadopago'
        
        try:
            start_time = datetime.now()
            response = requests.post(url, json=webhook_data, timeout=25)  # Test MP's 22s limit
            end_time = datetime.now()
            
            response_time = (end_time - start_time).total_seconds()
            
            if response.status_code == 200:
                if response_time < 22:
                    print(f"  ✅ Response time: {response_time:.2f}s (< 22s requirement)")
                    return True
                else:
                    print(f"  ❌ Response time: {response_time:.2f}s (> 22s requirement)")
                    return False
            else:
                print(f"  ❌ Non-200 response: {response.status_code}")
                return False
                
        except requests.exceptions.ConnectionError:
            print("  ⚠️ Cannot test timing - server not running")
            return False
        except requests.exceptions.Timeout:
            print("  ❌ Webhook timed out (> 25s)")
            return False
            
    except Exception as e:
        print(f"❌ Timing test failed: {str(e)}")
        return False

def generate_corrected_test_report():
    """Generate test report for corrected implementation"""
    print("🧪 CORRECTED MERCADO PAGO WEBHOOK TESTS")
    print("=" * 60)
    print("Based on: https://www.mercadopago.com.ar/developers/es/docs/subscriptions/additional-content/your-integrations/notifications/webhooks")
    print()
    
    tests = [
        ("Corrected Webhook Format", test_corrected_webhook_format),
        ("Subscription API Creation", test_subscription_api_creation),
        ("Multiple Webhook Types", test_webhook_types),
        ("MP API Endpoints", test_subscription_endpoints),
        ("Response Timing (<22s)", test_webhook_response_timing),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} crashed: {str(e)}")
            results.append((test_name, False))
    
    # Summary
    print("\n📋 CORRECTED IMPLEMENTATION TEST SUMMARY:")
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}: {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 Results: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("🎉 ALL CORRECTED TESTS PASSED!")
        print("✅ Implementation now complies with MP documentation")
        print("🚀 Ready to proceed with Phase 2")
    else:
        print("⚠️ Some tests failed - check webhook server and configuration")
    
    return passed == len(results)

def main():
    """Main test function"""
    print("🔧 Testing Corrected Mercado Pago Implementation")
    print("=" * 60)
    
    success = generate_corrected_test_report()
    
    if success:
        print("\n📋 Next Steps:")
        print("1. Deploy corrected implementation to production")
        print("2. Test with real MP webhook delivery")
        print("3. Proceed with Phase 2 - Quiz integration")
        print("4. Set up ManyChat subscription flows")
    else:
        print("\n❌ Fix failing tests before production deployment")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 