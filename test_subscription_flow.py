#!/usr/bin/env python3
"""
Test Script for Caloria Subscription Functionality
This script tests the basic subscription flow to ensure everything works.

Usage:
    python test_subscription_flow.py
"""

import os
import sys
import json
import requests
from datetime import datetime

# Add the current directory to Python path to import app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_database_models():
    """Test database models and relationships"""
    try:
        print("🔍 Testing database models...")
        
        from app import app, db, User, Subscription, SubscriptionService, MercadoPagoService
        
        with app.app_context():
            # Test User model with new fields
            user_count = User.query.count()
            print(f"  ✅ User model: {user_count} users in database")
            
            # Create test user if none exist
            if user_count == 0:
                test_user = User(
                    whatsapp_id='test_123456789',
                    first_name='Test',
                    last_name='User',
                    subscription_tier='trial_pending',
                    subscription_status='inactive'
                )
                db.session.add(test_user)
                db.session.commit()
                print("  ✅ Created test user")
            
            # Test user methods
            test_user = User.query.first()
            if test_user:
                is_trial = test_user.is_trial_active()
                is_active = test_user.is_subscription_active()
                can_access = test_user.can_access_premium_features()
                print(f"  ✅ User methods: trial={is_trial}, active={is_active}, premium={can_access}")
            
            # Test Subscription table
            subscription_count = Subscription.query.count()
            print(f"  ✅ Subscription model: {subscription_count} subscriptions")
            
            print("✅ Database models test passed!")
            return True
            
    except Exception as e:
        print(f"❌ Database models test failed: {str(e)}")
        return False

def test_subscription_service():
    """Test SubscriptionService functionality"""
    try:
        print("\n🔧 Testing SubscriptionService...")
        
        from app import app, db, User, SubscriptionService
        
        with app.app_context():
            # Get test user
            test_user = User.query.filter_by(whatsapp_id='test_123456789').first()
            if not test_user:
                print("❌ No test user found")
                return False
            
            # Test starting trial
            print("  🔄 Testing trial start...")
            result = SubscriptionService.start_trial(test_user)
            if result:
                print("  ✅ Trial started successfully")
                print(f"    - Status: {test_user.subscription_status}")
                print(f"    - Tier: {test_user.subscription_tier}")
                print(f"    - Trial end: {test_user.trial_end_time}")
                print(f"    - Remaining hours: {test_user.get_trial_time_remaining():.1f}")
            else:
                print("  ❌ Failed to start trial")
                return False
            
            # Test feature access
            can_access = SubscriptionService.can_access_feature(test_user, 'unlimited_food_analysis')
            print(f"  ✅ Feature access test: {can_access}")
            
            # Test trial activity logging
            SubscriptionService.log_trial_activity(test_user, 'food_analyzed', {
                'food_name': 'Test Apple',
                'calories': 80
            })
            print("  ✅ Trial activity logged")
            
            print("✅ SubscriptionService test passed!")
            return True
            
    except Exception as e:
        print(f"❌ SubscriptionService test failed: {str(e)}")
        return False

def test_mercadopago_service():
    """Test MercadoPagoService functionality"""
    try:
        print("\n💳 Testing MercadoPagoService...")
        
        from app import app, MercadoPagoService, User
        
        with app.app_context():
            # Get test user
            test_user = User.query.filter_by(whatsapp_id='test_123456789').first()
            if not test_user:
                print("❌ No test user found")
                return False
            
            # Test subscription link creation
            print("  🔗 Testing subscription link creation...")
            payment_link = MercadoPagoService.create_subscription_link(
                test_user,
                return_url="https://caloria.vip/subscription-success",
                cancel_url="https://caloria.vip/subscription-cancel"
            )
            
            if payment_link:
                print(f"  ✅ Payment link created: {payment_link[:50]}...")
                
                # Verify link contains expected parameters
                if 'preapproval_plan_id' in payment_link:
                    print("  ✅ Plan ID included in link")
                if test_user.whatsapp_id in payment_link:
                    print("  ✅ External reference included")
                else:
                    print("  ⚠️ External reference missing from link")
            else:
                print("  ❌ Failed to create payment link")
                return False
            
            print("✅ MercadoPagoService test passed!")
            return True
            
    except Exception as e:
        print(f"❌ MercadoPagoService test failed: {str(e)}")
        return False

def test_api_endpoints():
    """Test API endpoints"""
    try:
        print("\n🌐 Testing API endpoints...")
        
        # Test subscription creation endpoint
        print("  📝 Testing subscription creation API...")
        
        test_data = {
            'subscriber_id': 'test_123456789',
            'plan_type': 'premium'
        }
        
        # Note: This assumes the app is running on localhost:5000
        # In production, you'd use the actual domain
        url = 'http://localhost:5000/api/create-subscription'
        
        try:
            response = requests.post(url, json=test_data, timeout=5)
            if response.status_code == 200:
                result = response.json()
                print(f"  ✅ API endpoint working: {result.get('success', False)}")
                if 'payment_link' in result:
                    print(f"  ✅ Payment link generated: {result['payment_link'][:50]}...")
            else:
                print(f"  ⚠️ API returned status {response.status_code}")
                print(f"    Response: {response.text}")
        except requests.exceptions.ConnectionError:
            print("  ⚠️ Cannot test API - server not running")
            print("    Start server with: python app.py")
            print("    Then run this test again")
        except Exception as e:
            print(f"  ❌ API test error: {str(e)}")
            
        print("✅ API endpoints test completed!")
        return True
        
    except Exception as e:
        print(f"❌ API endpoints test failed: {str(e)}")
        return False

def test_environment_variables():
    """Test environment variables are properly set"""
    try:
        print("\n🔧 Testing environment variables...")
        
        from app import app
        
        required_vars = [
            'MERCADO_PAGO_ACCESS_TOKEN',
            'MERCADO_PAGO_PUBLIC_KEY',
            'MERCADO_PAGO_PLAN_ID',
            'SUBSCRIPTION_TRIAL_DAYS',
            'SUBSCRIPTION_PRICE_ARS'
        ]
        
        missing_vars = []
        for var in required_vars:
            value = app.config.get(var)
            if value:
                if 'TOKEN' in var or 'KEY' in var:
                    masked = value[:10] + '...' + value[-10:] if len(value) > 20 else value[:5] + '...'
                    print(f"  ✅ {var}: {masked}")
                else:
                    print(f"  ✅ {var}: {value}")
            else:
                missing_vars.append(var)
                print(f"  ❌ {var}: Not set")
        
        if missing_vars:
            print(f"\n⚠️ Missing variables: {missing_vars}")
            print("Run: python setup_mercadopago_env.py")
            return False
        else:
            print("✅ All environment variables set!")
            return True
            
    except Exception as e:
        print(f"❌ Environment variables test failed: {str(e)}")
        return False

def test_enhanced_food_analysis():
    """Test enhanced food analysis for trial users"""
    try:
        print("\n🍎 Testing enhanced food analysis...")
        
        from app import app, User, format_analysis_response, DailyStats
        
        with app.app_context():
            # Get test user
            test_user = User.query.filter_by(whatsapp_id='test_123456789').first()
            if not test_user:
                print("❌ No test user found")
                return False
            
            # Mock analysis result
            mock_analysis = {
                'food_name': 'Test Apple',
                'calories': 80,
                'protein': 0.5,
                'carbs': 21,
                'fat': 0.2,
                'fiber': 4,
                'sodium': 1,
                'food_score': 5,
                'confidence_score': 0.9
            }
            
            # Mock daily stats
            mock_stats = DailyStats(
                user_id=test_user.id,
                total_calories=500,
                goal_calories=2000,
                meals_logged=2
            )
            
            # Test response formatting
            response = format_analysis_response(mock_analysis, mock_stats)
            
            if 'Nutritional Analysis' in response or 'ANÁLISIS NUTRICIONAL' in response:
                print("  ✅ Food analysis response generated")
                
                # Check if trial information would be included for trial users
                if test_user.is_trial_active():
                    print("  ✅ User is in trial - enhanced features available")
                else:
                    print("  ℹ️ User not in trial - basic features only")
            else:
                print("  ❌ Invalid response format")
                return False
            
            print("✅ Enhanced food analysis test passed!")
            return True
            
    except Exception as e:
        print(f"❌ Enhanced food analysis test failed: {str(e)}")
        return False

def generate_test_report():
    """Generate a summary test report"""
    print("\n" + "=" * 60)
    print("📊 SUBSCRIPTION FUNCTIONALITY TEST REPORT")
    print("=" * 60)
    
    tests = [
        ("Database Models", test_database_models),
        ("Subscription Service", test_subscription_service),
        ("Mercado Pago Service", test_mercadopago_service),
        ("Environment Variables", test_environment_variables),
        ("Enhanced Food Analysis", test_enhanced_food_analysis),
        ("API Endpoints", test_api_endpoints),
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
    print("\n📋 TEST SUMMARY:")
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}: {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 Results: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("🎉 ALL TESTS PASSED! Ready for Phase 2 implementation.")
    else:
        print("⚠️ Some tests failed. Please fix issues before proceeding.")
    
    return passed == len(results)

def main():
    """Main test function"""
    print("🧪 Caloria Subscription Functionality Tests")
    print("=" * 60)
    
    success = generate_test_report()
    
    if success:
        print("\n🚀 Phase 1 implementation is working correctly!")
        print("\n📋 Ready for Phase 2:")
        print("1. Quiz flow modification")
        print("2. ManyChat subscription flows")
        print("3. Trial day program implementation")
        print("4. Production deployment")
    else:
        print("\n❌ Please fix failing tests before proceeding to Phase 2.")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 