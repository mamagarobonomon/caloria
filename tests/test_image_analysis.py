#!/usr/bin/env python3
"""
Quick Image Analysis Test for Caloria
Simple script to test food image analysis functionality
"""

import os
import sys
import json
import requests
import base64
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def quick_api_test(image_path: str) -> dict:
    """Quick test using the deployed API"""
    print(f"🔬 Testing image analysis: {os.path.basename(image_path)}")
    
    # Convert image to base64
    with open(image_path, 'rb') as img_file:
        image_data = base64.b64encode(img_file.read()).decode('utf-8')
    
    # Test via webhook (simpler endpoint)
    webhook_url = "https://caloria.vip/webhook/manychat"
    
    payload = {
        "subscriber": {"id": "test_user_quick"},
        "type": "image", 
        "image_url": f"data:image/jpeg;base64,{image_data}",
        "test_mode": True
    }
    
    try:
        response = requests.post(webhook_url, json=payload, timeout=30)
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"API returned {response.status_code}: {response.text[:100]}"}
    except Exception as e:
        return {"error": str(e)}

def quick_local_test(image_path: str) -> dict:
    """Quick test using local imports"""
    try:
        from app import app, db, User, FoodLog
        from handlers.food_analysis_handlers import FoodAnalysisHandler
        
        with app.app_context():
            handler = FoodAnalysisHandler(db, User, FoodLog)
            
            # Read image data
            with open(image_path, 'rb') as img_file:
                image_data = img_file.read()
            
            # Run analysis
            result = handler._analyze_image_comprehensive(
                image_data=image_data,
                image_url=f"file://{os.path.abspath(image_path)}"
            )
            return result
            
    except ImportError:
        return {"error": "Local imports not available. Run from project root with dependencies installed."}
    except Exception as e:
        return {"error": f"Local analysis failed: {str(e)}"}

def print_results(result: dict):
    """Print formatted results"""
    if "error" in result:
        print(f"❌ Error: {result['error']}")
        return
    
    print("\n🍽️ Analysis Results:")
    print("-" * 40)
    
    if "food_description" in result:
        print(f"📋 Description: {result['food_description']}")
    
    if "food_items" in result:
        print("🥗 Items detected:")
        for item in result.get('food_items', []):
            if isinstance(item, dict):
                name = item.get('item', item.get('name', 'Unknown'))
                weight = item.get('weight_grams', 'Unknown')
                print(f"   • {name}: {weight}g")
            else:
                print(f"   • {item}")
    
    if "nutrition" in result:
        nutrition = result['nutrition']
        print(f"📊 Nutrition:")
        print(f"   Calories: {nutrition.get('calories', 'N/A')} kcal")
        print(f"   Protein: {nutrition.get('protein', 'N/A')}g")
    
    if "confidence_score" in result:
        confidence = result['confidence_score']
        print(f"🎯 Confidence: {confidence*100:.1f}%")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python test_image_analysis.py <image_path>")
        print("Example: python test_image_analysis.py ../sample_food.jpg")
        sys.exit(1)
    
    image_path = sys.argv[1]
    
    if not os.path.exists(image_path):
        print(f"❌ Image not found: {image_path}")
        sys.exit(1)
    
    print("🚀 Caloria Image Analysis Test")
    print("=" * 40)
    
    # Try API first
    print("\n🌐 Testing with deployed API...")
    api_result = quick_api_test(image_path)
    print_results(api_result)
    
    # Try local if API fails
    if "error" in api_result:
        print("\n🔬 Trying local analysis...")
        local_result = quick_local_test(image_path)
        print_results(local_result)
    
    print("\n✅ Test complete!") 