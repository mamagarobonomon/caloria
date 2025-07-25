#!/usr/bin/env python3
"""
Caloria Photo Analysis Testing Script
Tests food image analysis through the Caloria system locally or via API
"""

import os
import sys
import json
import time
import requests
import base64
from typing import Dict, Any, Optional
from pathlib import Path

# Add the project root to Python path for local imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def load_image_as_base64(image_path: str) -> str:
    """Load image file and convert to base64"""
    try:
        with open(image_path, 'rb') as img_file:
            image_data = img_file.read()
            return base64.b64encode(image_data).decode('utf-8')
    except FileNotFoundError:
        print(f"❌ Error: Image file not found: {image_path}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error loading image: {str(e)}")
        sys.exit(1)

def test_local_analysis(image_path: str) -> Dict[str, Any]:
    """Test food analysis using local imports"""
    print("🔬 Testing with local food analysis system...")
    
    try:
        # Import required modules
        from app import app, db, User, FoodLog
        from handlers.enhanced_food_analysis import EnhancedFoodAnalysisHandler
        from handlers.food_analysis_handlers import FoodAnalysisHandler
        
        with app.app_context():
            # Initialize handlers
            enhanced_handler = EnhancedFoodAnalysisHandler(db, User, FoodLog)
            basic_handler = FoodAnalysisHandler(db, User, FoodLog)
            
            # Convert image to bytes
            with open(image_path, 'rb') as img_file:
                image_data = img_file.read()
            
            # Test with enhanced handler first
            try:
                print("🤖 Trying Enhanced Food Analysis (Gemini Vision)...")
                result = enhanced_handler.analyze_food_photo_with_clarification(
                    subscriber_id="test_user_photo_analysis",
                    image_url=f"file://{os.path.abspath(image_path)}"
                )
                result['analysis_method'] = 'enhanced_gemini_vision'
                return result
                
            except Exception as e:
                print(f"⚠️ Enhanced analysis failed: {str(e)}")
                print("🔄 Falling back to basic analysis...")
                
                # Fallback to basic handler
                result = basic_handler._analyze_image_comprehensive(
                    image_data=image_data,
                    image_url=f"file://{os.path.abspath(image_path)}"
                )
                result['analysis_method'] = 'basic_fallback'
                return result
                
    except ImportError as e:
        print(f"❌ Local import failed: {str(e)}")
        print("💡 Make sure you're running from the project directory with dependencies installed")
        return None
    except Exception as e:
        print(f"❌ Local analysis failed: {str(e)}")
        return None

def test_api_analysis(image_path: str, api_base_url: str = "https://caloria.vip") -> Dict[str, Any]:
    """Test food analysis via API call to deployed system"""
    print(f"🌐 Testing with deployed API at {api_base_url}...")
    
    try:
        # Load image as base64
        image_base64 = load_image_as_base64(image_path)
        
        # Prepare API request
        api_url = f"{api_base_url}/api/analyze-food"
        
        payload = {
            "subscriber_id": "test_user_api_analysis",
            "message_type": "image",
            "image_data": f"data:image/jpeg;base64,{image_base64}",
            "test_mode": True
        }
        
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Caloria-Photo-Analysis-Test/1.0"
        }
        
        print("📤 Sending image to API...")
        response = requests.post(api_url, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            result['analysis_method'] = 'deployed_api'
            result['api_response_time'] = response.elapsed.total_seconds()
            return result
        else:
            print(f"❌ API request failed with status {response.status_code}")
            print(f"Response: {response.text[:200]}...")
            return None
            
    except requests.RequestException as e:
        print(f"❌ API request failed: {str(e)}")
        return None
    except Exception as e:
        print(f"❌ API analysis failed: {str(e)}")
        return None

def test_webhook_simulation(image_path: str, api_base_url: str = "https://caloria.vip") -> Dict[str, Any]:
    """Simulate a ManyChat webhook with image data"""
    print(f"📱 Testing with ManyChat webhook simulation at {api_base_url}...")
    
    try:
        # Load image as base64
        image_base64 = load_image_as_base64(image_path)
        
        # Simulate ManyChat webhook payload
        webhook_url = f"{api_base_url}/webhook/manychat"
        
        payload = {
            "subscriber": {
                "id": "test_subscriber_webhook"
            },
            "type": "image",
            "image_url": f"data:image/jpeg;base64,{image_base64}",
            "test_mode": True,
            "timestamp": int(time.time())
        }
        
        headers = {
            "Content-Type": "application/json",
            "X-Hub-Signature": "test-signature",
            "User-Agent": "ManyChat-Webhook-Test/1.0"
        }
        
        print("📤 Sending webhook request...")
        response = requests.post(webhook_url, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            result['analysis_method'] = 'webhook_simulation'
            result['webhook_response_time'] = response.elapsed.total_seconds()
            return result
        else:
            print(f"❌ Webhook request failed with status {response.status_code}")
            print(f"Response: {response.text[:200]}...")
            return None
            
    except requests.RequestException as e:
        print(f"❌ Webhook request failed: {str(e)}")
        return None
    except Exception as e:
        print(f"❌ Webhook simulation failed: {str(e)}")
        return None

def format_analysis_results(result: Dict[str, Any]) -> str:
    """Format analysis results for display"""
    if not result:
        return "❌ No results to display"
    
    output = []
    output.append("="*60)
    output.append("🍽️  CALORIA FOOD ANALYSIS RESULTS")
    output.append("="*60)
    
    # Analysis method
    method = result.get('analysis_method', 'unknown')
    output.append(f"🔬 Analysis Method: {method}")
    
    # Timing information
    if 'response_time' in result:
        output.append(f"⏱️  Processing Time: {result['response_time']:.2f}s")
    elif 'api_response_time' in result:
        output.append(f"⏱️  API Response Time: {result['api_response_time']:.2f}s")
    elif 'webhook_response_time' in result:
        output.append(f"⏱️  Webhook Response Time: {result['webhook_response_time']:.2f}s")
    
    output.append("")
    
    # Food description
    if 'food_description' in result:
        output.append(f"📋 Food Description:")
        output.append(f"   {result['food_description']}")
        output.append("")
    
    # Individual items
    if 'food_items' in result and result['food_items']:
        output.append("🥗 Individual Food Items:")
        for item in result['food_items']:
            if isinstance(item, dict):
                name = item.get('item', item.get('name', 'Unknown'))
                weight = item.get('weight_grams', item.get('weight', 'Unknown'))
                method = item.get('cooking_method', item.get('preparation', ''))
                method_str = f" ({method})" if method else ""
                output.append(f"   • {name}: {weight}g{method_str}")
            else:
                output.append(f"   • {item}")
        output.append("")
    
    # Nutrition information
    if 'nutrition' in result:
        nutrition = result['nutrition']
        output.append("📊 Nutrition Information:")
        output.append(f"   Calories: {nutrition.get('calories', 'N/A')} kcal")
        output.append(f"   Protein: {nutrition.get('protein', 'N/A')}g")
        output.append(f"   Carbs: {nutrition.get('carbohydrates', 'N/A')}g")
        output.append(f"   Fat: {nutrition.get('fat', 'N/A')}g")
        output.append(f"   Fiber: {nutrition.get('fiber', 'N/A')}g")
        output.append("")
    
    # Confidence and analysis details
    if 'confidence_score' in result:
        confidence = result['confidence_score']
        confidence_pct = f"{confidence*100:.1f}%" if confidence <= 1 else f"{confidence:.1f}%"
        output.append(f"🎯 Confidence Score: {confidence_pct}")
    
    if 'analysis_details' in result:
        output.append(f"🔍 Analysis Details: {result['analysis_details']}")
    
    # Error information
    if 'error' in result:
        output.append(f"❌ Error: {result['error']}")
    
    # Raw response for debugging
    if 'debug_info' in result:
        output.append("\n🐛 Debug Information:")
        output.append(json.dumps(result['debug_info'], indent=2))
    
    output.append("="*60)
    
    return "\n".join(output)

def main():
    """Main function to run photo analysis tests"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Caloria photo analysis system")
    parser.add_argument("image_path", help="Path to the image file to analyze")
    parser.add_argument("--method", choices=["local", "api", "webhook", "all"], 
                       default="all", help="Testing method to use")
    parser.add_argument("--api-url", default="https://caloria.vip", 
                       help="Base URL for API testing")
    parser.add_argument("--output", help="File to save results (optional)")
    parser.add_argument("--verbose", "-v", action="store_true", 
                       help="Enable verbose output")
    
    args = parser.parse_args()
    
    # Verify image file exists
    if not os.path.exists(args.image_path):
        print(f"❌ Error: Image file not found: {args.image_path}")
        sys.exit(1)
    
    print("🚀 Starting Caloria Photo Analysis Test")
    print(f"📷 Image: {args.image_path}")
    print(f"🔧 Method: {args.method}")
    print("="*60)
    
    results = {}
    
    # Run tests based on method
    if args.method in ["local", "all"]:
        result = test_local_analysis(args.image_path)
        if result:
            results["local"] = result
    
    if args.method in ["api", "all"]:
        result = test_api_analysis(args.image_path, args.api_url)
        if result:
            results["api"] = result
    
    if args.method in ["webhook", "all"]:
        result = test_webhook_simulation(args.image_path, args.api_url)
        if result:
            results["webhook"] = result
    
    # Display results
    print("\n" + "="*60)
    print("📊 ANALYSIS RESULTS SUMMARY")
    print("="*60)
    
    if not results:
        print("❌ No successful analyses completed")
        sys.exit(1)
    
    for method, result in results.items():
        print(f"\n🔬 {method.upper()} ANALYSIS:")
        print(format_analysis_results(result))
    
    # Save results if requested
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\n💾 Results saved to: {args.output}")
    
    print("\n✅ Analysis complete!")

if __name__ == "__main__":
    main() 