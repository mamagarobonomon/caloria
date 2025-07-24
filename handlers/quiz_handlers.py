"""
Quiz Handlers for Caloria Application
Modular handlers for user quiz/onboarding process
"""

import json
from datetime import datetime
from typing import Dict, Any, Optional

from config.constants import AppConstants, StatusCodes, Messages
from services.validation_service import ValidationService
from services.logging_service import caloria_logger
from services.metrics_service import SubscriptionMetrics
from services.caching_service import invalidate_user_related_cache
from exceptions import ValidationException

class QuizHandler:
    """Handler for user quiz and onboarding process"""
    
    def __init__(self, db, user_model):
        self.db = db
        self.User = user_model
        self.logger = caloria_logger
        
        # Quiz flow configuration
        self.quiz_steps = [
            'gender',
            'age', 
            'weight',
            'height',
            'activity_level',
            'goal',
            'review'
        ]
    
    def process_quiz_input(self, subscriber_id: str, text: str) -> Dict[str, Any]:
        """Process quiz input from user"""
        try:
            user = self._get_or_create_user(subscriber_id)
            
            # Parse quiz command
            if text.lower().startswith('quiz start') or text.lower() == 'quiz':
                return self._start_quiz(user)
            
            elif text.lower().startswith('quiz reset'):
                return self._reset_quiz(user)
            
            elif user.quiz_completed:
                return {
                    'message': '✅ Ya completaste el quiz. Usa "quiz reset" para empezar de nuevo.',
                    'quiz_status': 'completed'
                }
            
            else:
                # Process current quiz step
                return self._process_quiz_step(user, text)
                
        except Exception as e:
            self.logger.error(f"Quiz processing failed for {subscriber_id}: {text}", e)
            return {
                'error': 'quiz_processing_failed',
                'message': Messages.SYSTEM_ERROR
            }
    
    def _start_quiz(self, user) -> Dict[str, Any]:
        """Start or restart the quiz process"""
        user.current_quiz_step = 0
        user.quiz_completed = False
        user.quiz_data = json.dumps({})
        user.last_interaction = datetime.utcnow()
        self.db.session.commit()
        
        self.logger.log_user_action('quiz_started', user_id=str(user.id))
        
        return {
            'message': self._get_welcome_message(),
            'quiz_status': 'started',
            'next_step': self._get_step_prompt(0)
        }
    
    def _reset_quiz(self, user) -> Dict[str, Any]:
        """Reset quiz progress"""
        user.current_quiz_step = 0
        user.quiz_completed = False
        user.quiz_data = json.dumps({})
        user.last_interaction = datetime.utcnow()
        self.db.session.commit()
        
        # Invalidate user cache
        invalidate_user_related_cache(user.id)
        
        self.logger.log_user_action('quiz_reset', user_id=str(user.id))
        
        return {
            'message': '🔄 Quiz reiniciado. ¡Empecemos de nuevo!',
            'quiz_status': 'reset',
            'next_step': self._get_step_prompt(0)
        }
    
    def _process_quiz_step(self, user, response: str) -> Dict[str, Any]:
        """Process individual quiz step"""
        current_step = user.current_quiz_step
        
        if current_step >= len(self.quiz_steps):
            return {
                'error': 'invalid_quiz_state',
                'message': 'Estado de quiz inválido. Usa "quiz reset" para empezar de nuevo.'
            }
        
        step_name = self.quiz_steps[current_step]
        
        # Validate and process response
        validation_result = self._validate_step_response(step_name, response)
        if not validation_result['valid']:
            return {
                'message': validation_result['error_message'],
                'quiz_status': 'error',
                'current_step': step_name,
                'retry_prompt': self._get_step_prompt(current_step)
            }
        
        # Save validated response
        quiz_data = json.loads(user.quiz_data or '{}')
        quiz_data[step_name] = validation_result['value']
        user.quiz_data = json.dumps(quiz_data)
        
        # Move to next step
        next_step = current_step + 1
        user.current_quiz_step = next_step
        user.last_interaction = datetime.utcnow()
        
        # Check if quiz is complete
        if next_step >= len(self.quiz_steps):
            return self._complete_quiz(user, quiz_data)
        else:
            self.db.session.commit()
            return {
                'message': f'✅ Perfecto! {validation_result.get("confirmation", "")}',
                'quiz_status': 'in_progress',
                'current_step': step_name,
                'next_step': self._get_step_prompt(next_step),
                'progress': f'{next_step}/{len(self.quiz_steps)}'
            }
    
    def _complete_quiz(self, user, quiz_data: Dict[str, Any]) -> Dict[str, Any]:
        """Complete the quiz and calculate user profile"""
        try:
            # Calculate daily calorie goal
            calorie_goal = self._calculate_daily_calories(quiz_data)
            
            # Update user profile
            user.quiz_completed = True
            user.gender = quiz_data.get('gender')
            user.age = quiz_data.get('age')
            user.weight = quiz_data.get('weight')
            user.height = quiz_data.get('height')
            user.activity_level = quiz_data.get('activity_level')
            user.goal = quiz_data.get('goal')
            user.daily_calorie_goal = calorie_goal
            user.last_interaction = datetime.utcnow()
            
            # Set trial status
            user.subscription_status = 'trial_pending'
            user.trial_start_time = datetime.utcnow()
            
            self.db.session.commit()
            
            # Invalidate user cache
            invalidate_user_related_cache(user.id)
            
            # Record metrics
            SubscriptionMetrics.record_subscription_event('quiz_completed', str(user.id))
            
            self.logger.log_user_action(
                'quiz_completed',
                {
                    'calorie_goal': calorie_goal,
                    'goal': quiz_data.get('goal'),
                    'activity_level': quiz_data.get('activity_level')
                },
                str(user.id)
            )
            
            return {
                'message': self._get_completion_message(quiz_data, calorie_goal),
                'quiz_status': 'completed',
                'user_profile': {
                    'daily_calorie_goal': calorie_goal,
                    'goal': quiz_data.get('goal'),
                    'activity_level': quiz_data.get('activity_level')
                },
                'next_action': 'start_trial'
            }
            
        except Exception as e:
            self.db.session.rollback()
            self.logger.error(f"Quiz completion failed for user {user.id}", e)
            return {
                'error': 'quiz_completion_failed',
                'message': Messages.SYSTEM_ERROR
            }
    
    def _validate_step_response(self, step_name: str, response: str) -> Dict[str, Any]:
        """Validate quiz step response"""
        response = response.strip().lower()
        
        if step_name == 'gender':
            if response in ['hombre', 'masculino', 'male', 'm']:
                return {'valid': True, 'value': 'male', 'confirmation': 'Hombre registrado.'}
            elif response in ['mujer', 'femenino', 'female', 'f']:
                return {'valid': True, 'value': 'female', 'confirmation': 'Mujer registrado.'}
            elif response in ['otro', 'other', 'o']:
                return {'valid': True, 'value': 'other', 'confirmation': 'Género registrado.'}
            else:
                return {
                    'valid': False,
                    'error_message': '❌ Respuesta no válida. Responde: "Hombre", "Mujer" o "Otro"'
                }
        
        elif step_name == 'age':
            try:
                age = int(response)
                if AppConstants.MIN_AGE <= age <= AppConstants.MAX_AGE:
                    return {'valid': True, 'value': age, 'confirmation': f'{age} años registrado.'}
                else:
                    return {
                        'valid': False,
                        'error_message': f'❌ Edad debe estar entre {AppConstants.MIN_AGE} y {AppConstants.MAX_AGE} años.'
                    }
            except ValueError:
                return {
                    'valid': False,
                    'error_message': '❌ Por favor ingresa tu edad como un número (ej: 25)'
                }
        
        elif step_name == 'weight':
            try:
                weight = float(response.replace(',', '.'))
                if AppConstants.MIN_WEIGHT <= weight <= AppConstants.MAX_WEIGHT:
                    return {'valid': True, 'value': weight, 'confirmation': f'{weight}kg registrado.'}
                else:
                    return {
                        'valid': False,
                        'error_message': f'❌ Peso debe estar entre {AppConstants.MIN_WEIGHT} y {AppConstants.MAX_WEIGHT}kg.'
                    }
            except ValueError:
                return {
                    'valid': False,
                    'error_message': '❌ Por favor ingresa tu peso como un número (ej: 70.5)'
                }
        
        elif step_name == 'height':
            try:
                height = float(response.replace(',', '.'))
                if AppConstants.MIN_HEIGHT <= height <= AppConstants.MAX_HEIGHT:
                    return {'valid': True, 'value': height, 'confirmation': f'{height}cm registrado.'}
                else:
                    return {
                        'valid': False,
                        'error_message': f'❌ Altura debe estar entre {AppConstants.MIN_HEIGHT} y {AppConstants.MAX_HEIGHT}cm.'
                    }
            except ValueError:
                return {
                    'valid': False,
                    'error_message': '❌ Por favor ingresa tu altura en centímetros (ej: 175)'
                }
        
        elif step_name == 'activity_level':
            activity_mapping = {
                'sedentario': 'sedentary',
                'sedentary': 'sedentary',
                '1': 'sedentary',
                'ligero': 'lightly_active',
                'lightly_active': 'lightly_active',
                'light': 'lightly_active',
                '2': 'lightly_active',
                'moderado': 'moderately_active',
                'moderately_active': 'moderately_active',
                'moderate': 'moderately_active',
                '3': 'moderately_active',
                'activo': 'very_active',
                'very_active': 'very_active',
                'active': 'very_active',
                '4': 'very_active',
                'muy activo': 'extra_active',
                'extra_active': 'extra_active',
                'extra': 'extra_active',
                '5': 'extra_active'
            }
            
            activity_level = activity_mapping.get(response)
            if activity_level:
                activity_names = {
                    'sedentary': 'Sedentario',
                    'lightly_active': 'Ligeramente activo',
                    'moderately_active': 'Moderadamente activo',
                    'very_active': 'Muy activo',
                    'extra_active': 'Extremadamente activo'
                }
                return {
                    'valid': True,
                    'value': activity_level,
                    'confirmation': f'Nivel de actividad: {activity_names[activity_level]}'
                }
            else:
                return {
                    'valid': False,
                    'error_message': '❌ Responde con: "Sedentario", "Ligero", "Moderado", "Activo" o "Muy activo"'
                }
        
        elif step_name == 'goal':
            goal_mapping = {
                'perder peso': 'lose_weight',
                'bajar': 'lose_weight',
                'adelgazar': 'lose_weight',
                'lose_weight': 'lose_weight',
                'lose': 'lose_weight',
                '1': 'lose_weight',
                'mantener': 'maintain',
                'maintain': 'maintain',
                'maintenance': 'maintain',
                'igual': 'maintain',
                '2': 'maintain',
                'ganar peso': 'gain_weight',
                'subir': 'gain_weight',
                'engordar': 'gain_weight',
                'gain_weight': 'gain_weight',
                'gain': 'gain_weight',
                '3': 'gain_weight',
                'musculo': 'build_muscle',
                'músculos': 'build_muscle',
                'build_muscle': 'build_muscle',
                'muscle': 'build_muscle',
                '4': 'build_muscle'
            }
            
            goal = goal_mapping.get(response)
            if goal:
                goal_names = {
                    'lose_weight': 'Perder peso',
                    'maintain': 'Mantener peso',
                    'gain_weight': 'Ganar peso',
                    'build_muscle': 'Ganar músculo'
                }
                return {
                    'valid': True,
                    'value': goal,
                    'confirmation': f'Objetivo: {goal_names[goal]}'
                }
            else:
                return {
                    'valid': False,
                    'error_message': '❌ Responde con: "Perder peso", "Mantener", "Ganar peso" o "Músculo"'
                }
        
        else:
            return {
                'valid': False,
                'error_message': '❌ Paso de quiz no reconocido.'
            }
    
    def _get_step_prompt(self, step_index: int) -> str:
        """Get prompt for quiz step"""
        if step_index >= len(self.quiz_steps):
            return ""
        
        step_name = self.quiz_steps[step_index]
        
        prompts = {
            'gender': '👤 ¿Cuál es tu género?\nResponde: "Hombre", "Mujer" o "Otro"',
            'age': '🎂 ¿Cuántos años tienes?\nEjemplo: 25',
            'weight': '⚖️ ¿Cuál es tu peso actual en kilogramos?\nEjemplo: 70',
            'height': '📏 ¿Cuál es tu altura en centímetros?\nEjemplo: 175',
            'activity_level': '🏃‍♂️ ¿Cuál es tu nivel de actividad física?\n\n1️⃣ Sedentario (poco o nada de ejercicio)\n2️⃣ Ligero (ejercicio ligero 1-3 días/semana)\n3️⃣ Moderado (ejercicio moderado 3-5 días/semana)\n4️⃣ Activo (ejercicio intenso 6-7 días/semana)\n5️⃣ Muy activo (ejercicio muy intenso, trabajo físico)\n\nResponde con el número o nombre.',
            'goal': '🎯 ¿Cuál es tu objetivo principal?\n\n1️⃣ Perder peso\n2️⃣ Mantener peso\n3️⃣ Ganar peso\n4️⃣ Ganar músculo\n\nResponde con el número o nombre.',
        }
        
        return prompts.get(step_name, 'Paso no encontrado.')
    
    def _calculate_daily_calories(self, quiz_data: Dict[str, Any]) -> int:
        """Calculate daily calorie goal using Mifflin-St Jeor equation"""
        try:
            gender = quiz_data.get('gender')
            age = quiz_data.get('age')
            weight = quiz_data.get('weight')  # kg
            height = quiz_data.get('height')  # cm
            activity_level = quiz_data.get('activity_level')
            goal = quiz_data.get('goal')
            
            # Base Metabolic Rate (BMR) calculation
            if gender == 'male':
                bmr = 88.362 + (13.397 * weight) + (4.799 * height) - (5.677 * age)
            else:  # female or other
                bmr = 447.593 + (9.247 * weight) + (3.098 * height) - (4.330 * age)
            
            # Activity level multipliers
            activity_multipliers = {
                'sedentary': 1.2,
                'lightly_active': 1.375,
                'moderately_active': 1.55,
                'very_active': 1.725,
                'extra_active': 1.9
            }
            
            # Calculate Total Daily Energy Expenditure (TDEE)
            tdee = bmr * activity_multipliers.get(activity_level, 1.375)
            
            # Adjust based on goal
            if goal == 'lose_weight':
                calories = tdee - 500  # 500 calorie deficit
            elif goal == 'gain_weight':
                calories = tdee + 300  # 300 calorie surplus
            elif goal == 'build_muscle':
                calories = tdee + 200  # Small surplus for muscle building
            else:  # maintain
                calories = tdee
            
            # Round to nearest 50 and ensure reasonable bounds
            calories = max(1200, min(3500, round(calories / 50) * 50))
            
            return int(calories)
            
        except Exception as e:
            self.logger.error(f"Calorie calculation failed: {str(e)}", e)
            return 2000  # Default fallback
    
    def _get_welcome_message(self) -> str:
        """Get welcome message for quiz start"""
        return """
🎉 ¡Bienvenido a Caloria!

Vamos a crear tu perfil personalizado para calcular tus necesidades calóricas diarias.

El quiz tiene 6 preguntas rápidas y tomará menos de 2 minutos.

¡Empezamos! 👇
"""
    
    def _get_completion_message(self, quiz_data: Dict[str, Any], calorie_goal: int) -> str:
        """Get quiz completion message"""
        goal_messages = {
            'lose_weight': '🔥 Perfecto para perder peso de forma saludable',
            'maintain': '⚖️ Ideal para mantener tu peso actual',
            'gain_weight': '💪 Genial para ganar peso de manera controlada',
            'build_muscle': '🏋️‍♂️ Excelente para desarrollar músculo'
        }
        
        goal = quiz_data.get('goal', 'maintain')
        goal_message = goal_messages.get(goal, '✅ Plan personalizado creado')
        
        return f"""
🎯 {Messages.QUIZ_COMPLETED}

📊 **Tu Plan Personalizado:**
• Objetivo diario: {calorie_goal} calorías
• {goal_message}

🎁 **¡Prueba gratuita activada!**
Tienes {AppConstants.DEFAULT_TRIAL_DAYS} día para probar todas las funciones.

💡 **¿Qué puedes hacer ahora?**
📸 Envía fotos de tus comidas
📝 Describe lo que comes
🎤 Envía mensajes de voz

¡Ya puedes empezar a registrar tus comidas! 🍎
"""
    
    def _get_or_create_user(self, subscriber_id: str):
        """Get existing user or create new one"""
        user = self.User.query.filter_by(whatsapp_id=subscriber_id).first()
        
        if not user:
            user = self.User(
                whatsapp_id=subscriber_id,
                is_active=True,
                created_at=datetime.utcnow(),
                last_interaction=datetime.utcnow(),
                current_quiz_step=0,
                quiz_completed=False
            )
            self.db.session.add(user)
            self.db.session.commit()
            
            self.logger.log_user_action(
                'user_created',
                {'whatsapp_id': subscriber_id},
                str(user.id)
            )
        
        return user 