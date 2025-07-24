# 📋 **Complete ManyChat Quiz Flow Configuration**
**15-Question Nutrition Quiz with Subscription Integration**

---

## 🎯 **FLOW OVERVIEW**

**Purpose:** Convert users through personalized quiz → subscription offer → trial activation  
**Questions:** 15 total with subscription mentions at Q10-11  
**Result:** Personalized nutrition plan + premium trial offer  

---

## 📝 **COMPLETE QUIZ FLOW CONFIGURATION**

### **QUIZ START**
```
FLOW NAME: "Nutrition Quiz Start"
TRIGGER: Button click "🎯 Comenzar Quiz Nutricional"

MESSAGE:
¡Perfecto! 🎉 

Voy a hacerte 15 preguntas rápidas para crear tu perfil nutricional personalizado.

Al finalizar tendrás:
✅ Tu plan calórico personalizado
✅ Recomendaciones específicas para tu objetivo  
💎 Acceso a funciones PREMIUM por 24h GRATIS

📊 Esto toma solo 3-4 minutos.

¿Listo para empezar?

BUTTONS:
[✅ ¡Sí, empecemos!] → Go to Q1
[📋 ¿Qué preguntas me harás?] → Go to "Quiz Preview"
[🔙 Volver después] → Go to "Main Menu"
```

### **QUIZ PREVIEW**
```
FLOW NAME: "Quiz Preview"

MESSAGE:
📋 TE PREGUNTARÉ SOBRE:

1️⃣-3️⃣ **Información básica:** Nombre, edad, género
4️⃣-5️⃣ **Medidas:** Altura y peso actual
6️⃣-7️⃣ **Objetivos:** Meta y peso ideal
8️⃣-9️⃣ **Estilo de vida:** Actividad física y sueño
🔟-1️⃣1️⃣ **Hábitos:** Estrés y restricciones alimentarias
1️⃣2️⃣-1️⃣3️⃣ **Salud:** Alergias y condiciones médicas
1️⃣4️⃣-1️⃣5️⃣ **Preferencias:** Comidas diarias y confirmación

💎 ¡Incluye información sobre nuestro plan PREMIUM!

BUTTONS:
[🚀 ¡Perfecto, empecemos!] → Go to Q1
[🔙 Volver al menú] → Go to "Main Menu"
```

---

## 🔢 **QUESTION FLOW SEQUENCE**

### **QUESTION 1: NAME**
```
FLOW NAME: "Quiz Q1 - Name"

MESSAGE:
1️⃣ ¡Empecemos! 😊

¿Cuál es tu nombre?
(Solo tu primer nombre está bien)

INPUT TYPE: Text Input
CUSTOM FIELD: first_name
VALIDATION: Required, 2-50 characters

ACTION: Set Custom Field "first_name" = {{user_input}}
NEXT: Go to Q2
```

### **QUESTION 2: AGE**
```
FLOW NAME: "Quiz Q2 - Age"

MESSAGE:
2️⃣ Hola {{first_name}}! 👋

¿Cuántos años tienes?

BUTTONS:
[18-25] → Set age = "18-25"
[26-35] → Set age = "26-35"  
[36-45] → Set age = "36-45"
[46-55] → Set age = "46-55"
[56-65] → Set age = "56-65"
[65+] → Set age = "65+"

CUSTOM FIELD: age
NEXT: Go to Q3
```

### **QUESTION 3: GENDER**
```
FLOW NAME: "Quiz Q3 - Gender"

MESSAGE:
3️⃣ ¿Cuál es tu género?

BUTTONS:
[👨 Masculino] → Set gender = "male"
[👩 Femenino] → Set gender = "female"
[🔀 Prefiero no decir] → Set gender = "other"

CUSTOM FIELD: gender
NEXT: Go to Q4
```

### **QUESTION 4: HEIGHT**
```
FLOW NAME: "Quiz Q4 - Height"

MESSAGE:
4️⃣ ¿Cuánto mides?

Por favor escribe tu altura en centímetros.
Ejemplo: 175

INPUT TYPE: Number Input
CUSTOM FIELD: height_cm
VALIDATION: 140-220 cm
ERROR MESSAGE: "Por favor ingresa una altura válida entre 140 y 220 cm"

ACTION: Set Custom Field "height_cm" = {{user_input}}
NEXT: Go to Q5
```

### **QUESTION 5: CURRENT WEIGHT**
```
FLOW NAME: "Quiz Q5 - Weight"

MESSAGE:
5️⃣ ¿Cuánto pesas actualmente?

Por favor escribe tu peso en kilogramos.
Ejemplo: 70

INPUT TYPE: Number Input
CUSTOM FIELD: weight_kg
VALIDATION: 40-200 kg
ERROR MESSAGE: "Por favor ingresa un peso válido entre 40 y 200 kg"

ACTION: Set Custom Field "weight_kg" = {{user_input}}
NEXT: Go to Q6
```

### **QUESTION 6: PRIMARY GOAL**
```
FLOW NAME: "Quiz Q6 - Goal"

MESSAGE:
6️⃣ ¿Cuál es tu objetivo principal?

BUTTONS:
[🔥 Perder peso] → Set goal = "lose_weight"
[💪 Ganar masa muscular] → Set goal = "build_muscle"
[⚖️ Mantener peso] → Set goal = "maintain_weight"
[📈 Ganar peso] → Set goal = "gain_weight"

CUSTOM FIELD: goal
NEXT: Go to Q7
```

### **QUESTION 7: TARGET WEIGHT**
```
FLOW NAME: "Quiz Q7 - Target Weight"

MESSAGE:
7️⃣ ¿Cuál es tu peso ideal/objetivo?

Escribe el peso que quieres alcanzar (en kg).
Ejemplo: 65

INPUT TYPE: Number Input
CUSTOM FIELD: target_weight_kg
VALIDATION: 40-200 kg

ACTION: Set Custom Field "target_weight_kg" = {{user_input}}
NEXT: Go to Q8
```

### **QUESTION 8: ACTIVITY LEVEL**
```
FLOW NAME: "Quiz Q8 - Activity"

MESSAGE:
8️⃣ ¿Qué tan activo/a eres físicamente?

BUTTONS:
[🛋️ Sedentario] → Set activity = "sedentary"
[🚶 Ligeramente activo] → Set activity = "light"
[🏃 Moderadamente activo] → Set activity = "moderate"
[🏋️ Muy activo] → Set activity = "very_active"
[🤸 Extremadamente activo] → Set activity = "extra_active"

CUSTOM FIELD: activity_level
NEXT: Go to Q9
```

### **QUESTION 9: SLEEP**
```
FLOW NAME: "Quiz Q9 - Sleep"

MESSAGE:
9️⃣ ¿Cuántas horas duermes por noche?

BUTTONS:
[😴 Menos de 6h] → Set sleep = "less_6"
[💤 6-7 horas] → Set sleep = "6_7"
[😊 7-8 horas] → Set sleep = "7_8"
[🌙 8-9 horas] → Set sleep = "8_9"
[😴 Más de 9h] → Set sleep = "more_9"

CUSTOM FIELD: sleep_hours
NEXT: Go to Q10
```

### **QUESTION 10: STRESS (WITH PREMIUM MENTION)**
```
FLOW NAME: "Quiz Q10 - Stress + Premium Mention"

MESSAGE:
🔟 ¿Cómo es tu nivel de estrés habitualmente?

BUTTONS:
[😌 Bajo] → Set stress = "low"
[😐 Moderado] → Set stress = "moderate"
[😰 Alto] → Set stress = "high"
[🤯 Muy alto] → Set stress = "very_high"

💎 ¡Por cierto, {{first_name}}!
Al finalizar este quiz tendrás acceso a nuestro plan PREMIUM:
✨ Análisis ilimitado de comidas
🎯 Recomendaciones personalizadas avanzadas  
📊 Seguimiento detallado de micronutrientes
⚡ ¡Prueba GRATIS por 24 horas completas!

🎉 ¡Solo quedan 5 preguntas más!

CUSTOM FIELD: stress_level
NEXT: Go to Q11
```

### **QUESTION 11: DIET RESTRICTIONS (WITH PREMIUM MENTION)**
```
FLOW NAME: "Quiz Q11 - Diet + Premium Mention"

MESSAGE:
1️⃣1️⃣ ¿Sigues alguna dieta especial o tienes restricciones alimentarias?

BUTTONS:
[🍽️ Ninguna] → Set diet = "none"
[🥬 Vegetariana] → Set diet = "vegetarian"
[🌱 Vegana] → Set diet = "vegan"
[🥩 Keto/Low-carb] → Set diet = "keto"
[🚫 Otras restricciones] → Set diet = "other"

💎 ¡Increíble progreso, {{first_name}}!
Con CALORIA PREMIUM podrás:
🧬 Ver micronutrientes específicos para tu dieta
⏰ Saber el timing perfecto para cada comida
🎯 Recibir consejos personalizados para {{goal}}

🎉 ¡Solo quedan 4 preguntas más!

CUSTOM FIELD: diet_restrictions
NEXT: Go to Q12
```

### **QUESTION 12: ALLERGIES**
```
FLOW NAME: "Quiz Q12 - Allergies"

MESSAGE:
1️⃣2️⃣ ¿Tienes alguna alergia alimentaria?

BUTTONS:
[✅ No tengo alergias] → Set allergies = "none"
[🥜 Frutos secos] → Set allergies = "nuts"
[🥛 Lácteos] → Set allergies = "dairy"
[🌾 Gluten] → Set allergies = "gluten"
[🦐 Mariscos] → Set allergies = "seafood"
[📝 Otras] → Set allergies = "other"

CUSTOM FIELD: allergies
NEXT: Go to Q13
```

### **QUESTION 13: MEDICAL CONDITIONS**
```
FLOW NAME: "Quiz Q13 - Medical"

MESSAGE:
1️⃣3️⃣ ¿Tienes alguna condición médica que afecte tu alimentación?

BUTTONS:
[✅ Ninguna] → Set medical = "none"
[🩺 Diabetes] → Set medical = "diabetes"
[❤️ Hipertensión] → Set medical = "hypertension"
[🔄 Problemas tiroideos] → Set medical = "thyroid"
[💊 Otras] → Set medical = "other"

CUSTOM FIELD: medical_conditions
NEXT: Go to Q14
```

### **QUESTION 14: MEALS PER DAY**
```
FLOW NAME: "Quiz Q14 - Meals"

MESSAGE:
1️⃣4️⃣ ¿Cuántas comidas prefieres hacer al día?

BUTTONS:
[🍽️ 2 comidas] → Set meals = "2"
[🍽️🍽️ 3 comidas] → Set meals = "3"
[🍽️🍽️🍽️+ 4-5 comidas] → Set meals = "5"
[⏰ Ayuno intermitente] → Set meals = "0"

CUSTOM FIELD: meals_per_day
NEXT: Go to Q15
```

### **QUESTION 15: FINAL CONFIRMATION**
```
FLOW NAME: "Quiz Q15 - Final"

MESSAGE:
1️⃣5️⃣ ¡Última pregunta! 🎉

¿Estás listo/a para recibir tu plan nutricional personalizado?

BUTTONS:
[✅ ¡Sí, calcular mi plan!] → Go to "Quiz Completion"
[🔄 Revisar mis respuestas] → Go to "Review Answers"

CUSTOM FIELD: quiz_completed = "yes"
```

---

## 🎉 **QUIZ COMPLETION & SUBSCRIPTION OFFER**

### **QUIZ COMPLETION FLOW**
```
FLOW NAME: "Quiz Completion & Subscription Offer"

EXTERNAL REQUEST:
URL: https://caloria.vip/webhook/manychat
METHOD: POST
HEADERS: Content-Type: application/json
BODY:
{
  "subscriber_id": "{{subscriber_id}}",
  "message_text": "{\"question_number\": 15, \"quiz_completed\": true, \"quiz_data\": {\"first_name\": \"{{first_name}}\", \"age\": \"{{age}}\", \"gender\": \"{{gender}}\", \"height_cm\": \"{{height_cm}}\", \"weight_kg\": \"{{weight_kg}}\", \"goal\": \"{{goal}}\", \"target_weight_kg\": \"{{target_weight_kg}}\", \"activity_level\": \"{{activity_level}}\", \"sleep_hours\": \"{{sleep_hours}}\", \"stress_level\": \"{{stress_level}}\", \"diet_restrictions\": \"{{diet_restrictions}}\", \"allergies\": \"{{allergies}}\", \"medical_conditions\": \"{{medical_conditions}}\", \"meals_per_day\": \"{{meals_per_day}}\"}}",
  "message_type": "quiz_response"
}

SUCCESS RESPONSE: Display external request response
ERROR RESPONSE: Go to "Quiz Completion Fallback"
```

### **QUIZ COMPLETION FALLBACK**
```
FLOW NAME: "Quiz Completion Fallback"

MESSAGE:
🎉 ¡Felicitaciones {{first_name}}! Tu perfil nutricional está listo.

📊 TU PLAN PERSONALIZADO:
🎯 Objetivo: {{goal}}
⚖️ Peso actual: {{weight_kg}} kg → Objetivo: {{target_weight_kg}} kg
🏃 Nivel de actividad: {{activity_level}}

🌟 ¡AHORA DESBLOQUEA EL PODER COMPLETO!

💎 CALORIA PREMIUM - 24 HORAS GRATIS:
✅ Análisis ILIMITADO de comidas (vs 3 gratis)
✅ Recomendaciones personalizadas avanzadas
✅ Seguimiento de micronutrientes detallado
✅ Planificación de comidas inteligente
✅ Soporte prioritario 24/7

💰 Después de tu prueba: Solo $4999.00 ARS/mes
🚫 Cancela cuando quieras, sin compromisos

🎁 ¡Activa tu prueba GRATUITA ahora!

BUTTONS:
[🚀 ¡Activar Prueba GRATIS!] → Go to "Subscription Creation"
[📋 Ver Todas las Funciones] → Go to "Premium Features Detail"
[⏰ Lo haré después] → Go to "Maybe Later Flow"
```

---

## 🔧 **TECHNICAL CONFIGURATION**

### **CUSTOM FIELDS SETUP**
```
REQUIRED CUSTOM FIELDS:
- first_name (Text)
- age (Text)
- gender (Text)  
- height_cm (Number)
- weight_kg (Number)
- goal (Text)
- target_weight_kg (Number)
- activity_level (Text)
- sleep_hours (Text)
- stress_level (Text)
- diet_restrictions (Text)
- allergies (Text)
- medical_conditions (Text)
- meals_per_day (Text)
- quiz_completed (Text)
```

### **WEBHOOK CONFIGURATION**
```
PRODUCTION WEBHOOK URL: https://caloria.vip/webhook/manychat
BACKUP WEBHOOK URL: https://caloria.vip/webhook/manychat-backup
TIMEOUT: 30 seconds
RETRY ATTEMPTS: 2
```

---

## 📊 **ANALYTICS & TRACKING**

### **CONVERSION TRACKING POINTS**
```
1. Quiz Started (Q1 reached)
2. Quiz Halfway (Q8 reached)  
3. Premium Mention 1 (Q10 reached)
4. Premium Mention 2 (Q11 reached)
5. Quiz Completed (Q15 reached)
6. Subscription Offer Shown
7. Trial Activation Clicked
```

### **CUSTOM EVENTS**
```
- quiz_started
- quiz_q10_reached  
- quiz_q11_reached
- quiz_completed
- subscription_offer_shown
- trial_button_clicked
```

---

## 🚀 **IMPLEMENTATION CHECKLIST**

### **PHASE 1: Basic Setup (2 hours)**
```
□ Create all 15 question flows
□ Set up custom fields
□ Configure basic navigation
□ Test question sequence
```

### **PHASE 2: Premium Integration (2 hours)**
```
□ Add premium mentions to Q10-11
□ Configure subscription offer flow
□ Set up external request to backend
□ Test webhook integration
```

### **PHASE 3: Polish & Testing (1 hour)**
```
□ Add error handling and fallbacks
□ Test complete user journey
□ Verify analytics tracking
□ Check Spanish language formatting
```

---

**📋 TOTAL SETUP TIME: ~5 hours**  
**🎯 RESULT: Complete quiz flow ready for WhatsApp deployment**  
**🚀 NEXT: Configure subscription creation and payment flows** 