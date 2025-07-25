"""
Enhanced Food Analysis Handler for Comprehensive Food Logging
Implements detailed Gemini Vision AI analysis with clarification questions and multi-part responses
"""

import os
import time
import json
import requests
import tempfile
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, date

# Google Cloud imports for Gemini Vision AI
try:
    import vertexai
    from vertexai.generative_models import GenerativeModel, Part
    VERTEX_AI_AVAILABLE = True
except ImportError:
    VERTEX_AI_AVAILABLE = False

from services.logging_service import caloria_logger, LogTimer
from services.metrics_service import FoodAnalysisMetrics
from services.caching_service import FoodAnalysisCache
from services.validation_service import ValidationService
from exceptions import FoodAnalysisException, FileProcessingException
from config.constants import AppConstants


class EnhancedFoodAnalysisHandler:
    """Enhanced food analysis with detailed Gemini Vision AI and interactive clarification"""
    
    def __init__(self, db, user_model, food_log_model):
        self.db = db
        self.User = user_model
        self.FoodLog = food_log_model
        self.logger = caloria_logger
        
        # Initialize Gemini Vision AI
        if VERTEX_AI_AVAILABLE:
            try:
                # Initialize Vertex AI with project settings
                project_id = os.getenv('GOOGLE_CLOUD_PROJECT_ID', 'caloria-nutrition-bot')
                location = os.getenv('GOOGLE_CLOUD_LOCATION', 'us-central1')
                vertexai.init(project=project_id, location=location)
                self.gemini_model = GenerativeModel('gemini-2.5-flash-002')
                self.gemini_available = True
                self.logger.info("✅ Gemini Vision AI initialized successfully")
            except Exception as e:
                self.logger.error(f"❌ Failed to initialize Gemini Vision AI: {str(e)}")
                self.gemini_available = False
        else:
            self.gemini_available = False
            self.logger.warning("⚠️ Vertex AI not available - using fallback analysis")
    
    def analyze_food_photo_with_clarification(self, subscriber_id: str, image_url: str) -> Dict[str, Any]:
        """
        Step 1: Analyze food photo and generate clarification questions
        Returns detailed description with clarification questions and buttons
        """
        start_time = time.time()
        
        try:
            user = self._get_or_create_user(subscriber_id)
            FoodAnalysisMetrics.record_analysis_started('enhanced_image', str(user.id))
            
            # Download and validate image
            image_data = self._download_and_validate_image(image_url)
            
            # Analyze with Gemini Vision AI
            analysis_result = self._analyze_with_gemini_vision(image_data)
            
            # Generate clarification questions
            clarification_questions = self._generate_clarification_questions(analysis_result)
            
            # Store preliminary analysis in session/cache for later use
            session_key = f"food_analysis_{subscriber_id}_{int(time.time())}"
            preliminary_data = {
                'analysis_result': analysis_result,
                'image_url': image_url,
                'clarification_questions': clarification_questions,
                'timestamp': datetime.utcnow().isoformat(),
                'user_id': user.id
            }
            
            FoodAnalysisCache.set(session_key, preliminary_data, ttl=3600)  # 1 hour TTL
            
            # Format response with clarification
            response = self._format_clarification_response(analysis_result, clarification_questions, session_key)
            
            processing_time = (time.time() - start_time) * 1000
            self.logger.info(f"Enhanced photo analysis completed in {processing_time:.2f}ms")
            
            return response
            
        except Exception as e:
            self.logger.error(f"Enhanced photo analysis failed for {subscriber_id}", e)
            return {
                'error': 'enhanced_analysis_failed',
                'message': '❌ Sorry, I couldn\'t analyze your photo. Please try again with a clearer image.'
            }
    
    def process_user_clarification(self, subscriber_id: str, session_key: str, user_input: str = None) -> Dict[str, Any]:
        """
        Step 3: Process user clarification and generate final nutritional analysis
        """
        try:
            # Retrieve preliminary analysis data
            preliminary_data = FoodAnalysisCache.get(session_key)
            if not preliminary_data:
                return {
                    'error': 'session_expired',
                    'message': '❌ Session expired. Please send your photo again.'
                }
            
            analysis_result = preliminary_data['analysis_result']
            user_id = preliminary_data['user_id']
            
            # Apply user clarifications if provided
            if user_input:
                analysis_result = self._apply_user_clarifications(analysis_result, user_input)
            
            # Generate comprehensive nutritional analysis
            comprehensive_analysis = self._generate_comprehensive_analysis(analysis_result)
            
            # Create food log entry
            user = self.User.query.get(user_id)
            food_log = self._create_enhanced_food_log(user, comprehensive_analysis, preliminary_data['image_url'], user_input)
            
            # Update daily stats
            self._update_user_daily_stats(user, date.today())
            
            # Generate multi-part response
            response = self._format_multi_part_analysis_response(comprehensive_analysis, food_log, user)
            
            # Clean up session data
            FoodAnalysisCache.delete(session_key)
            
            return response
            
        except Exception as e:
            self.logger.error(f"Clarification processing failed for {subscriber_id}", e)
            return {
                'error': 'clarification_failed',
                'message': '❌ Sorry, something went wrong. Please try again.'
            }
    
    def _analyze_with_gemini_vision(self, image_data: bytes) -> Dict[str, Any]:
        """Enhanced Gemini Vision AI analysis with detailed food identification"""
        
        if not self.gemini_available:
            return self._fallback_detailed_analysis(image_data)
        
        try:
            with LogTimer("gemini_vision_enhanced_analysis"):
                # Create image part for Gemini
                image_part = Part.from_data(image_data, mime_type="image/jpeg")
                
                # Enhanced prompt for detailed food analysis
                prompt = """
                You are a professional nutritionist analyzing a food photo. Provide a detailed, accurate description following this exact format:

                FOOD_DESCRIPTION: [Detailed description with cooking method, estimated weights in grams, and specific food items]

                FOOD_ITEMS: [JSON array of individual food items with estimated weights]
                Example: [{"item": "baked whole fish", "weight_grams": 500, "cooking_method": "baked"}, {"item": "broccoli", "weight_grams": 100, "preparation": "steamed"}]

                CONFIDENCE: [Number from 0.0 to 1.0 indicating confidence in the analysis]

                CLARIFICATION_NEEDED: [JSON array of specific questions about preparation methods, ingredients, or cooking details that would improve nutritional accuracy]

                COOKING_CONTEXT: [Any visible cooking methods, seasonings, oils, or preparation details you can observe]

                Please be specific about weights (estimate carefully based on visual portion sizes), cooking methods (baked, fried, grilled, etc.), and identify all visible food components. Focus on accuracy for nutritional calculation.
                """
                
                # Generate response
                response = self.gemini_model.generate_content([prompt, image_part])
                
                # Parse Gemini response
                analysis_result = self._parse_gemini_response(response.text)
                analysis_result['analysis_method'] = 'gemini_vision_enhanced'
                analysis_result['raw_response'] = response.text
                
                self.logger.info("✅ Gemini Vision enhanced analysis completed")
                return analysis_result
                
        except Exception as e:
            self.logger.error(f"Gemini Vision enhanced analysis failed: {str(e)}")
            return self._fallback_detailed_analysis(image_data)
    
    def _parse_gemini_response(self, response_text: str) -> Dict[str, Any]:
        """Parse structured Gemini response into analysis result"""
        result = {
            'food_description': '',
            'food_items': [],
            'confidence_score': 0.7,
            'clarification_needed': [],
            'cooking_context': ''
        }
        
        try:
            lines = response_text.split('\n')
            current_section = None
            
            for line in lines:
                line = line.strip()
                if line.startswith('FOOD_DESCRIPTION:'):
                    result['food_description'] = line.replace('FOOD_DESCRIPTION:', '').strip()
                elif line.startswith('FOOD_ITEMS:'):
                    try:
                        items_json = line.replace('FOOD_ITEMS:', '').strip()
                        result['food_items'] = json.loads(items_json)
                    except json.JSONDecodeError:
                        result['food_items'] = []
                elif line.startswith('CONFIDENCE:'):
                    try:
                        result['confidence_score'] = float(line.replace('CONFIDENCE:', '').strip())
                    except ValueError:
                        result['confidence_score'] = 0.7
                elif line.startswith('CLARIFICATION_NEEDED:'):
                    try:
                        clarification_json = line.replace('CLARIFICATION_NEEDED:', '').strip()
                        result['clarification_needed'] = json.loads(clarification_json)
                    except json.JSONDecodeError:
                        result['clarification_needed'] = []
                elif line.startswith('COOKING_CONTEXT:'):
                    result['cooking_context'] = line.replace('COOKING_CONTEXT:', '').strip()
            
            # Fallback if parsing failed
            if not result['food_description']:
                result['food_description'] = response_text[:200] + "..."
                
        except Exception as e:
            self.logger.error(f"Error parsing Gemini response: {str(e)}")
            result['food_description'] = "Mixed food items"
            result['confidence_score'] = 0.5
        
        return result
    
    def _generate_clarification_questions(self, analysis_result: Dict[str, Any]) -> List[str]:
        """Generate contextual clarification questions based on analysis"""
        questions = []
        
        # Use Gemini-provided clarification questions if available
        if analysis_result.get('clarification_needed'):
            questions.extend(analysis_result['clarification_needed'])
        
        # Add generic questions based on food items
        food_items = analysis_result.get('food_items', [])
        
        for item in food_items:
            item_name = item.get('item', '').lower()
            
            # Cheese-specific questions
            if 'cheese' in item_name:
                questions.append("What type of cheese are the cubes made from?")
            
            # Fish/meat preparation questions
            elif any(protein in item_name for protein in ['fish', 'chicken', 'beef', 'pork']):
                questions.append(f"How was the {item_name} prepared (e.g., any added oils, seasonings, or sauces)?")
            
            # Cooking method questions
            elif item.get('cooking_method') == 'unknown':
                questions.append(f"How was the {item_name} cooked?")
        
        # Limit to most relevant questions
        return questions[:3]
    
    def _format_clarification_response(self, analysis_result: Dict[str, Any], questions: List[str], session_key: str) -> Dict[str, Any]:
        """Format the initial response with clarification questions and buttons"""
        
        description = analysis_result.get('food_description', 'Food items detected')
        
        message = f"{description}\n\n"
        
        if questions:
            message += "Could you clarify a few details about your meal? (You can skip any question and simply press \"Analyze\" when you're ready.)\n"
            for question in questions:
                message += f"• {question}\n"
        else:
            message += "Ready to analyze your meal?"
        
        # ManyChat quick replies/buttons
        quick_replies = [
            {
                "title": "Analyze",
                "payload": f"analyze_food:{session_key}"
            },
            {
                "title": "New Log",
                "payload": "new_food_log"
            }
        ]
        
        return {
            'version': 'v2',
            'content': {
                'messages': [{
                    'type': 'text',
                    'text': message,
                    'quick_replies': quick_replies
                }]
            },
            'session_key': session_key,
            'requires_clarification': True
        }
    
    def _generate_comprehensive_analysis(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive nutritional analysis with detailed breakdowns"""
        
        food_items = analysis_result.get('food_items', [])
        total_nutrition = {
            'calories': 0, 'protein': 0, 'carbs': 0, 'fat': 0, 'fiber': 0, 'sodium': 0,
            'saturated_fat': 0, 'sugar': 0, 'omega3': 0, 'omega6': 0
        }
        
        detailed_items = []
        
        # Calculate nutrition for each food item
        for item in food_items:
            item_nutrition = self._calculate_item_nutrition(item)
            detailed_items.append({
                'name': item.get('item', 'Unknown'),
                'weight': item.get('weight_grams', 100),
                'nutrition': item_nutrition
            })
            
            # Add to totals
            for key in total_nutrition:
                total_nutrition[key] += item_nutrition.get(key, 0)
        
        # Calculate derived metrics
        comprehensive_analysis = {
            **analysis_result,
            'detailed_items': detailed_items,
            'total_nutrition': total_nutrition,
            'glycemic_load': self._calculate_glycemic_load(total_nutrition),
            'portion_size_category': self._categorize_portion_size(total_nutrition['calories']),
            'macronutrient_balance': self._analyze_macronutrient_balance(total_nutrition),
            'food_score': self._calculate_enhanced_food_score(total_nutrition, detailed_items),
            'health_recommendations': self._generate_health_recommendations(total_nutrition, detailed_items)
        }
        
        return comprehensive_analysis
    
    def _calculate_item_nutrition(self, item: Dict[str, Any]) -> Dict[str, float]:
        """Calculate nutrition for individual food item based on type and weight"""
        item_name = item.get('item', '').lower()
        weight_grams = item.get('weight_grams', 100)
        
        # Enhanced nutrition database with detailed micronutrients
        nutrition_db = {
            'fish': {'calories': 1.9, 'protein': 0.25, 'carbs': 0, 'fat': 0.08, 'fiber': 0, 'sodium': 0.5, 'saturated_fat': 0.02, 'omega3': 0.015},
            'baked fish': {'calories': 1.95, 'protein': 0.26, 'carbs': 0, 'fat': 0.085, 'fiber': 0, 'sodium': 0.55, 'saturated_fat': 0.02, 'omega3': 0.016},
            'broccoli': {'calories': 0.34, 'protein': 0.028, 'carbs': 0.07, 'fat': 0.004, 'fiber': 0.026, 'sodium': 0.00033, 'saturated_fat': 0.001},
            'potato': {'calories': 0.77, 'protein': 0.02, 'carbs': 0.17, 'fat': 0.001, 'fiber': 0.022, 'sodium': 0.00006, 'saturated_fat': 0.0003},
            'tomato': {'calories': 0.18, 'protein': 0.009, 'carbs': 0.039, 'fat': 0.002, 'fiber': 0.012, 'sodium': 0.00005, 'saturated_fat': 0.0003},
            'cheese': {'calories': 4.0, 'protein': 0.25, 'carbs': 0.013, 'fat': 0.33, 'fiber': 0, 'sodium': 0.0062, 'saturated_fat': 0.21},
            'olive oil': {'calories': 8.84, 'protein': 0, 'carbs': 0, 'fat': 1.0, 'fiber': 0, 'sodium': 0.000002, 'saturated_fat': 0.138}
        }
        
        # Find best match in nutrition database
        nutrition_per_gram = None
        for food_key in nutrition_db:
            if food_key in item_name:
                nutrition_per_gram = nutrition_db[food_key]
                break
        
        # Default values if no match found
        if not nutrition_per_gram:
            nutrition_per_gram = {'calories': 1.5, 'protein': 0.05, 'carbs': 0.15, 'fat': 0.05, 'fiber': 0.02, 'sodium': 0.001, 'saturated_fat': 0.02}
        
        # Calculate absolute values based on weight
        result = {}
        for nutrient, per_gram in nutrition_per_gram.items():
            result[nutrient] = per_gram * weight_grams
        
        # Add missing nutrients with defaults
        for nutrient in ['sugar', 'omega3', 'omega6']:
            if nutrient not in result:
                result[nutrient] = 0
        
        return result
    
    def _calculate_glycemic_load(self, nutrition: Dict[str, float]) -> str:
        """Calculate glycemic load category"""
        carbs = nutrition.get('carbs', 0)
        if carbs < 10:
            return "📉 Low"
        elif carbs < 20:
            return "📊 Moderate"
        else:
            return "📈 High"
    
    def _categorize_portion_size(self, calories: float) -> str:
        """Categorize portion size based on calories"""
        if calories < 200:
            return "🍽️ Small"
        elif calories < 400:
            return "🍽️ Medium"
        elif calories < 600:
            return "🍽️ Large"
        else:
            return "🍽️ Extra Large"
    
    def _analyze_macronutrient_balance(self, nutrition: Dict[str, float]) -> str:
        """Analyze macronutrient balance"""
        total_calories = nutrition.get('calories', 0)
        if total_calories == 0:
            return "⚖️ Unable to determine"
        
        protein_pct = (nutrition.get('protein', 0) * 4) / total_calories * 100
        carb_pct = (nutrition.get('carbs', 0) * 4) / total_calories * 100
        fat_pct = (nutrition.get('fat', 0) * 9) / total_calories * 100
        
        balance_parts = []
        if protein_pct > 30:
            balance_parts.append("🐟 High protein")
        elif protein_pct > 15:
            balance_parts.append("🐟 Moderate protein")
        
        if carb_pct > 50:
            balance_parts.append("🥖 High carbs")
        elif carb_pct > 25:
            balance_parts.append("🥖 Moderate carbs")
        
        if fat_pct > 35:
            balance_parts.append("🥑 High fat")
        elif fat_pct > 20:
            balance_parts.append("🥑 Moderate fat")
        
        return ", ".join(balance_parts) if balance_parts else "⚖️ Balanced"
    
    def _calculate_enhanced_food_score(self, nutrition: Dict[str, float], items: List[Dict]) -> Dict[str, Any]:
        """Calculate enhanced food score with detailed reasoning"""
        score = 3.0  # Base score
        reasons = []
        
        # Positive factors
        protein = nutrition.get('protein', 0)
        fiber = nutrition.get('fiber', 0)
        vegetables = len([item for item in items if any(veg in item['name'].lower() for veg in ['broccoli', 'spinach', 'kale', 'tomato'])])
        
        if protein > 25:
            score += 0.5
            reasons.append("high protein content")
        
        if fiber > 5:
            score += 0.3
            reasons.append("good fiber content")
        
        if vegetables >= 2:
            score += 0.4
            reasons.append("multiple vegetables")
        
        # Negative factors
        saturated_fat = nutrition.get('saturated_fat', 0)
        sodium = nutrition.get('sodium', 0)
        
        if saturated_fat > 10:
            score -= 0.3
            reasons.append("high saturated fat")
        
        if sodium > 1000:
            score -= 0.2
            reasons.append("high sodium")
        
        # Cap score between 1 and 5
        final_score = max(1, min(5, score))
        
        return {
            'score': round(final_score, 1),
            'reasons': reasons,
            'recommendation': self._get_frequency_recommendation(final_score)
        }
    
    def _get_frequency_recommendation(self, score: float) -> str:
        """Get eating frequency recommendation based on score"""
        if score >= 4.5:
            return "Often ✔️"
        elif score >= 3.5:
            return "Regularly ✔️"
        elif score >= 2.5:
            return "Sometimes ⚠️"
        else:
            return "Occasionally ⚠️"
    
    def _generate_health_recommendations(self, nutrition: Dict[str, float], items: List[Dict]) -> Dict[str, List[str]]:
        """Generate personalized health recommendations"""
        recommendations = {
            'additions': [],
            'replacements': []
        }
        
        # Analyze nutritional gaps
        fiber = nutrition.get('fiber', 0)
        omega3 = nutrition.get('omega3', 0)
        vegetables = len([item for item in items if any(veg in item['name'].lower() for veg in ['broccoli', 'spinach', 'kale', 'tomato', 'carrot'])])
        
        # Addition recommendations
        if fiber < 5:
            recommendations['additions'].append("🥗 Add leafy greens like spinach or kale for extra fiber and micronutrients")
        
        if omega3 < 1:
            recommendations['additions'].append("🥑 Include a serving of healthy fats, such as avocado or chia seeds")
        
        if vegetables < 2:
            recommendations['additions'].append("🌽 Add more colorful vegetables for vitamins and antioxidants")
        
        # Replacement recommendations
        saturated_fat = nutrition.get('saturated_fat', 0)
        if saturated_fat > 15:
            recommendations['replacements'].append("🧀 Consider reducing cheese portion or using lower-fat cheese alternatives")
        
        sodium = nutrition.get('sodium', 0)
        if sodium > 1200:
            recommendations['replacements'].append("🧂 Use herbs and spices instead of salt for flavoring")
        
        return recommendations
    
    def _format_multi_part_analysis_response(self, analysis: Dict[str, Any], food_log, user) -> Dict[str, Any]:
        """Format the comprehensive multi-part analysis response"""
        
        nutrition = analysis['total_nutrition']
        food_score_data = analysis['food_score']
        recommendations = analysis['health_recommendations']
        
        # Message parts (separated by ---)
        messages = []
        
        # Part 1: Initial message
        messages.append({
            'type': 'text',
            'text': 'Analyzing, give me a sec...'
        })
        
        # Part 2: Header
        messages.append({
            'type': 'text', 
            'text': '📊 Here\'s your detailed nutritional analysis:'
        })
        
        # Part 3: Meal Description
        meal_description = f"*Meal Description*:\n🍽️ {analysis.get('food_description', 'Mixed food items')}"
        messages.append({
            'type': 'text',
            'text': meal_description
        })
        
        # Part 4: Food Parameters
        parameters_text = f"""*Food Parameters*:
*Glycemic Load*: {analysis.get('glycemic_load', '📊 Moderate')}
*Portion Size*: {analysis.get('portion_size_category', '🍽️ Medium')}
*Macronutrient Balance*: {analysis.get('macronutrient_balance', '⚖️ Balanced')}"""
        
        messages.append({
            'type': 'text',
            'text': parameters_text
        })
        
        # Part 5: Detailed Nutrients
        nutrients_text = f"""*Nutrients*:
*Energy*: 🔥 {nutrition['calories']:.1f} kcal
*Protein*: 💪 {nutrition['protein']:.1f}g
*Carbohydrates*: 🍞 {nutrition['carbs']:.1f}g
*Total Fiber*: 🌱 {nutrition['fiber']:.1f}g
*Total Sugar*: 🍯 {nutrition.get('sugar', 0):.1f}g
*Total Fat*: 🥑 {nutrition['fat']:.1f}g
*Saturated Fat*: 🧈 {nutrition.get('saturated_fat', 0):.1f}g
*Trans Fat*: 🚫 0 g
*Omega-3 Fatty Acids*: 🐟 {nutrition.get('omega3', 0):.4f}g
*Omega-6 Fatty Acids*: 🌻 {nutrition.get('omega6', 0):.3f}g
*Sodium*: 🧂 {nutrition['sodium']:.1f}mg
*Alcohol*: 🚫 0 g"""
        
        messages.append({
            'type': 'text',
            'text': nutrients_text
        })
        
        # Part 6: Food Scores
        score_reasons = ", ".join(food_score_data['reasons']) if food_score_data['reasons'] else "balanced nutritional profile"
        scores_text = f"""*Food Scores*:
*Overall Rating*: 💫 — {food_score_data['score']}/5 — {'Great Choice' if food_score_data['score'] >= 4 else 'Good Choice' if food_score_data['score'] >= 3 else 'Fair Choice'}
*Should you eat this?*: {food_score_data['recommendation']}
*Food Score Reason*: {score_reasons.capitalize()}"""
        
        messages.append({
            'type': 'text',
            'text': scores_text
        })
        
        # Part 7: Additions for Sugar Spikes
        if recommendations['additions']:
            additions_text = "*What to Add to Decrease Sugar Spikes*:\n" + "\n".join(f" - {rec}" for rec in recommendations['additions'])
            messages.append({
                'type': 'text',
                'text': additions_text
            })
        
        # Part 8: Replacements and Exclusions
        if recommendations['replacements']:
            replacements_text = "*Replacements and Exclusions*:\n" + "\n".join(f" - {rec}" for rec in recommendations['replacements'])
            messages.append({
                'type': 'text',
                'text': replacements_text
            })
        
        return {
            'version': 'v2',
            'content': {
                'messages': messages
            },
            'analysis_complete': True,
            'food_log_id': food_log.id if food_log else None
        }
    
    def _fallback_detailed_analysis(self, image_data: bytes) -> Dict[str, Any]:
        """Fallback analysis when Gemini Vision is not available"""
        return {
            'food_description': 'Mixed food items (detailed analysis unavailable)',
            'food_items': [{'item': 'unknown food', 'weight_grams': 200}],
            'confidence_score': 0.5,
            'clarification_needed': ['What type of food is shown in the image?', 'How was it prepared?'],
            'cooking_context': 'Unable to determine cooking method'
        }
    
    # Helper methods (implement remaining helper methods from original handler)
    def _get_or_create_user(self, subscriber_id: str):
        """Get or create user from subscriber ID"""
        user = self.User.query.filter_by(whatsapp_id=subscriber_id).first()
        if not user:
            user = self.User(whatsapp_id=subscriber_id)
            self.db.session.add(user)
            self.db.session.commit()
        return user
    
    def _download_and_validate_image(self, image_url: str) -> bytes:
        """Download and validate image from URL"""
        try:
            response = requests.get(image_url, timeout=AppConstants.DOWNLOAD_TIMEOUT)
            response.raise_for_status()
            
            if len(response.content) > AppConstants.MAX_FILE_SIZE:
                raise FileProcessingException("Image file too large", file_type='image')
            
            return response.content
            
        except Exception as e:
            raise FileProcessingException(f"Failed to download image: {str(e)}", file_type='image')
    
    def _create_enhanced_food_log(self, user, analysis: Dict[str, Any], image_url: str, user_clarifications: str = None):
        """Create enhanced food log entry with detailed analysis"""
        nutrition = analysis['total_nutrition']
        food_score_data = analysis['food_score']
        
        food_log = self.FoodLog(
            user_id=user.id,
            food_name=analysis.get('food_description', 'Unknown food'),
            calories=nutrition['calories'],
            protein=nutrition['protein'],
            carbs=nutrition['carbs'],
            fat=nutrition['fat'],
            fiber=nutrition['fiber'],
            sodium=nutrition['sodium'],
            portion_size=f"~{nutrition['calories']:.0f} kcal",
            food_score=food_score_data['score'],
            analysis_method=analysis.get('analysis_method', 'enhanced_gemini'),
            raw_input=image_url,
            image_path=image_url,
            confidence_score=analysis.get('confidence_score', 0.7)
        )
        
        # Add user clarifications as metadata if provided
        if user_clarifications:
            food_log.raw_input += f" | Clarifications: {user_clarifications}"
        
        self.db.session.add(food_log)
        self.db.session.commit()
        
        return food_log
    
    def _update_user_daily_stats(self, user, date_today):
        """Update user's daily statistics"""
        # Implementation would be similar to the original handler
        pass
    
    def _apply_user_clarifications(self, analysis_result: Dict[str, Any], user_input: str) -> Dict[str, Any]:
        """Apply user clarifications to improve analysis accuracy"""
        # This could use Gemini to reanalyze with additional context
        # For now, just store the clarifications
        analysis_result['user_clarifications'] = user_input
        
        # Could implement more sophisticated clarification processing here
        # such as adjusting nutrition values based on cooking methods mentioned
        
        return analysis_result 