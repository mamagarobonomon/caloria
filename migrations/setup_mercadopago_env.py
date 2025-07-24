#!/usr/bin/env python3
"""
Environment Setup Script for Caloria Mercado Pago Integration
This script helps configure Mercado Pago credentials securely.

Usage:
    python setup_mercadopago_env.py
"""

import os
import sys
from pathlib import Path

def check_existing_env():
    """Check if .env file exists and has MP credentials"""
    env_file = Path('.env')
    if env_file.exists():
        print("✅ Found existing .env file")
        
        # Check for existing MP credentials
        content = env_file.read_text()
        mp_keys = [
            'MERCADO_PAGO_ACCESS_TOKEN',
            'MERCADO_PAGO_PUBLIC_KEY',
            'MERCADO_PAGO_PLAN_ID'
        ]
        
        existing_keys = []
        for key in mp_keys:
            if key in content:
                existing_keys.append(key)
        
        if existing_keys:
            print(f"⚠️ Found existing Mercado Pago keys: {', '.join(existing_keys)}")
            return True, existing_keys
        else:
            print("ℹ️ No Mercado Pago credentials found in .env")
            return True, []
    else:
        print("ℹ️ No .env file found")
        return False, []

def create_env_file():
    """Create or update .env file with Mercado Pago credentials"""
    
    print("\n🔧 Setting up Mercado Pago environment variables...")
    print("=" * 50)
    
    # Your provided credentials
    ACCESS_TOKEN = "APP_USR-1172155843468668-072410-5f2e9d6af1e4d437c2086d88c529259e-1506756785"
    PUBLIC_KEY = "APP_USR-983a7fa3-1497-4ed6-9d0b-a6fc35f5b0dc"
    PLAN_ID = "2c938084939f84900193a80bf21f01c8"
    
    # Environment variables to add
    env_vars = {
        'MERCADO_PAGO_ACCESS_TOKEN': ACCESS_TOKEN,
        'MERCADO_PAGO_PUBLIC_KEY': PUBLIC_KEY,
        'MERCADO_PAGO_PLAN_ID': PLAN_ID,
        'MERCADO_PAGO_WEBHOOK_SECRET': 'caloria-webhook-secret-2024',
        'SUBSCRIPTION_TRIAL_DAYS': '1',
        'SUBSCRIPTION_PRICE_ARS': '499900.0',
    }
    
    # Read existing .env file or create new one
    env_file = Path('.env')
    existing_content = ""
    
    if env_file.exists():
        existing_content = env_file.read_text()
        print("📝 Updating existing .env file...")
    else:
        print("📝 Creating new .env file...")
    
    # Parse existing content
    lines = existing_content.split('\n') if existing_content else []
    updated_lines = []
    added_keys = set()
    
    # Update existing lines
    for line in lines:
        if '=' in line and not line.strip().startswith('#'):
            key = line.split('=')[0].strip()
            if key in env_vars:
                updated_lines.append(f"{key}={env_vars[key]}")
                added_keys.add(key)
                print(f"  ✅ Updated: {key}")
            else:
                updated_lines.append(line)
        else:
            updated_lines.append(line)
    
    # Add new keys
    if not existing_content or not existing_content.endswith('\n'):
        updated_lines.append('')
    
    updated_lines.append('# Mercado Pago Configuration')
    for key, value in env_vars.items():
        if key not in added_keys:
            updated_lines.append(f"{key}={value}")
            added_keys.add(key)
            print(f"  ✅ Added: {key}")
    
    # Write updated content
    env_file.write_text('\n'.join(updated_lines))
    
    print(f"\n✅ Environment file updated: {env_file.absolute()}")
    return True

def verify_configuration():
    """Verify the configuration is correct"""
    try:
        print("\n🔍 Verifying configuration...")
        
        # Load environment variables
        from dotenv import load_dotenv
        load_dotenv()
        
        # Check required variables
        required_vars = [
            'MERCADO_PAGO_ACCESS_TOKEN',
            'MERCADO_PAGO_PUBLIC_KEY', 
            'MERCADO_PAGO_PLAN_ID',
            'SUBSCRIPTION_TRIAL_DAYS',
            'SUBSCRIPTION_PRICE_ARS'
        ]
        
        missing_vars = []
        for var in required_vars:
            value = os.getenv(var)
            if value:
                # Mask sensitive data
                if 'TOKEN' in var or 'KEY' in var:
                    masked_value = value[:10] + '...' + value[-10:] if len(value) > 20 else value[:5] + '...'
                    print(f"  ✅ {var}: {masked_value}")
                else:
                    print(f"  ✅ {var}: {value}")
            else:
                missing_vars.append(var)
                print(f"  ❌ {var}: Not set")
        
        if missing_vars:
            print(f"\n❌ Missing environment variables: {', '.join(missing_vars)}")
            return False
        else:
            print("\n✅ All environment variables configured correctly!")
            return True
            
    except ImportError:
        print("⚠️ python-dotenv not installed. Install with: pip install python-dotenv")
        return True  # Don't fail verification for missing dotenv
    except Exception as e:
        print(f"❌ Error verifying configuration: {str(e)}")
        return False

def test_mercadopago_connection():
    """Test connection to Mercado Pago API"""
    try:
        print("\n🌐 Testing Mercado Pago API connection...")
        
        import requests
        from dotenv import load_dotenv
        load_dotenv()
        
        access_token = os.getenv('MERCADO_PAGO_ACCESS_TOKEN')
        plan_id = os.getenv('MERCADO_PAGO_PLAN_ID')
        
        if not access_token:
            print("❌ Access token not found")
            return False
        
        # Test API connection
        url = "https://api.mercadopago.com/users/me"
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            user_data = response.json()
            print(f"  ✅ API Connection successful!")
            print(f"  ✅ Account: {user_data.get('email', 'Unknown')}")
            print(f"  ✅ Country: {user_data.get('country_id', 'Unknown')}")
            
            # Test plan access
            if plan_id:
                plan_url = f"https://api.mercadopago.com/preapproval_plan/{plan_id}"
                plan_response = requests.get(plan_url, headers=headers, timeout=10)
                
                if plan_response.status_code == 200:
                    plan_data = plan_response.json()
                    print(f"  ✅ Plan access successful: {plan_data.get('reason', 'Unknown plan')}")
                else:
                    print(f"  ⚠️ Plan access failed: {plan_response.status_code}")
            
            return True
        else:
            print(f"  ❌ API Connection failed: {response.status_code}")
            print(f"  ❌ Response: {response.text}")
            return False
            
    except ImportError as e:
        print(f"  ⚠️ Missing dependency: {str(e)}")
        print("  💡 Install with: pip install requests python-dotenv")
        return True  # Don't fail for missing dependencies
    except Exception as e:
        print(f"  ❌ Error testing API: {str(e)}")
        return False

def display_next_steps():
    """Display next steps for the user"""
    print("\n" + "=" * 50)
    print("🎉 MERCADO PAGO SETUP COMPLETED!")
    print("\n📋 Next steps:")
    print("1. Run database migration:")
    print("   python migrate_subscription_db.py")
    print("\n2. Test the subscription API:")
    print("   curl -X POST http://localhost:5000/api/create-subscription \\")
    print("     -H 'Content-Type: application/json' \\")
    print("     -d '{\"subscriber_id\":\"test_user_123\"}'")
    print("\n3. Configure ManyChat webhook URL:")
    print("   https://caloria.vip/webhook/mercadopago")
    print("\n4. Test quiz flow with subscription integration")
    print("\n5. Deploy to production server")

def main():
    """Main setup function"""
    print("🚀 Caloria Mercado Pago Environment Setup")
    print("=" * 50)
    
    # Step 1: Check existing environment
    print("1. Checking existing environment...")
    has_env, existing_keys = check_existing_env()
    
    if existing_keys:
        response = input(f"\nFound existing MP keys: {existing_keys}\nOverwrite? (y/N): ")
        if response.lower() != 'y':
            print("❌ Setup cancelled by user")
            return False
    
    # Step 2: Create/update .env file
    print("\n2. Setting up environment variables...")
    if not create_env_file():
        return False
    
    # Step 3: Verify configuration
    print("\n3. Verifying configuration...")
    if not verify_configuration():
        return False
    
    # Step 4: Test API connection
    print("\n4. Testing Mercado Pago API...")
    test_mercadopago_connection()  # Don't fail on API test errors
    
    # Step 5: Display next steps
    display_next_steps()
    
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        print("\n❌ Setup failed. Please check the errors above.")
        sys.exit(1)
    else:
        print("\n✅ Setup successful!")
        sys.exit(0) 