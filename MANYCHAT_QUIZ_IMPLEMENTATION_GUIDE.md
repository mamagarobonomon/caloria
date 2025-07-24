# 🚀 **ManyChat Implementation Guide: Bilingual Nutrition Quiz**

**Complete Step-by-Step Implementation for WhatsApp-Native Nutrition Quiz (15 Questions)**  
**Languages: Spanish & English**

---

## 📋 **Complete Step-by-Step Implementation**

---

## **Step 1: ManyChat Account Setup & Preparation**

### **1.1 Account Configuration**
```
1. Sign up for ManyChat Pro account (required for advanced features)
2. Connect your WhatsApp Business account
3. Verify your WhatsApp Business API access
4. Set up your business profile:
   - Business name: "Caloria - Asistente de Nutrición"
   - Description: "Tu asistente personal de nutrición con IA"
   - Profile photo: Caloria logo
```

### **1.2 Language Strategy Setup**
```
Language Detection Method:
Option A: Ask user preference at start
Option B: Detect from phone number region
Option C: Let users switch anytime

Recommended: Option A (user choice)
```

---

## **Step 2: Custom Fields Creation**

### **2.1 Create All Custom Fields**
```
Go to: Settings → Custom Fields → Create New

Required Fields:
1. language (text) - "es" or "en"
2. user_name (text)
3. age (number)
4. gender (text) - "male", "female", "other"
5. height_cm (number)
6. weight_kg (number)
7. goal (text) - "lose", "gain", "maintain", "performance"
8. target_weight_kg (number)
9. timeline (text) - "1-3m", "3-6m", "6-12m", "12m+"
10. activity_level (text) - "sedentary", "light", "moderate", "active", "extreme"
11. sleep_hours (number)
12. stress_level (text) - "low", "moderate", "high"
13. diet_restrictions (text)
14. allergies (text)
15. meals_per_day (number)
16. quiz_completed (text) - "yes", "no"
17. payment_status (text) - "free", "paid"
18. calculated_bmr (number)
19. calculated_tdee (number)
20. daily_calories (number)
21. protein_g (number)
22. carbs_g (number)
23. fat_g (number)
```

---

## **Step 3: Main Flow Structure**

### **3.1 Flow Architecture**
```
Main Menu Flow
├── Language Selection
├── Welcome & Introduction
├── Quiz Flow (15 questions)
├── Calculation Processing
├── Results Preview
├── Payment Flow
└── Premium Content Delivery
```

### **3.2 Create Flow Hierarchy**
```
1. Create "Main Menu" flow
2. Create "Language Selection" flow
3. Create "Quiz Flow" flow
4. Create "Calculation" flow
5. Create "Payment" flow
6. Create "Premium Content" flow
```

---

## **Step 4: Language Selection Flow**

### **4.1 Welcome Message (Language Selection)**
```
Flow Name: "Language Selection"
Trigger: Default Reply (when user first messages)

Message Content:
🌟 ¡Bienvenido a Caloria! | Welcome to Caloria! 🌟

Tu asistente personal de nutrición con IA
Your personal AI nutrition assistant

Por favor selecciona tu idioma preferido:
Please select your preferred language:

Buttons:
🇪🇸 Español
🇺🇸 English
```

### **4.2 Language Setting Actions**
```
Spanish Button Action:
1. Set Custom Field: language = "es"
2. Go to Flow: "Welcome Spanish"

English Button Action:
1. Set Custom Field: language = "en"  
2. Go to Flow: "Welcome English"
```

---

## **Step 5: Welcome & Introduction Flows**

### **5.1 Spanish Welcome Flow**
```
Flow Name: "Welcome Spanish"

Message 1:
¡Perfecto! 🇪🇸

Soy tu asistente personal de nutrición. Te ayudaré a crear un plan nutricional personalizado basado en tus objetivos y estilo de vida.

📋 Te haré 15 preguntas rápidas (toma solo 3-5 minutos)
🧮 Calcularé tus necesidades nutricionales exactas
🎯 Recibirás recomendaciones personalizadas

¿Listo para comenzar?

Buttons:
✅ ¡Sí, empecemos!
❓ Tengo una pregunta
```

### **5.2 English Welcome Flow**
```
Flow Name: "Welcome English"

Message 1:
Perfect! 🇺🇸

I'm your personal nutrition assistant. I'll help you create a personalized nutrition plan based on your goals and lifestyle.

📋 I'll ask you 15 quick questions (takes only 3-5 minutes)
🧮 I'll calculate your exact nutritional needs
🎯 You'll receive personalized recommendations

Ready to start?

Buttons:
✅ Yes, let's begin!
❓ I have a question
```

---

## **Step 6: Quiz Flow Implementation**

### **6.1 Question 1: Name**
```
Flow Name: "Quiz Question 1"

Spanish Message:
¡Empecemos! 😊

1️⃣ ¿Cuál es tu nombre?
(Solo tu primer nombre está bien)

Input Type: Text Input
Custom Field: user_name

English Message:
Let's begin! 😊

1️⃣ What's your name?
(Just your first name is fine)

Next Action: Go to "Quiz Question 2"
```

### **6.2 Question 2: Age**
```
Flow Name: "Quiz Question 2"

Spanish Message:
Hola {{user_name}}! 👋

2️⃣ ¿Cuántos años tienes?

Quick Replies:
18-25 | 26-35 | 36-45 | 46-55 | 56-65 | 65+

English Message:
Hi {{user_name}}! 👋

2️⃣ How old are you?

Action: Set Custom Field: age
Next: Go to "Quiz Question 3"
```

### **6.3 Question 3: Gender**
```
Flow Name: "Quiz Question 3"

Spanish Message:
3️⃣ ¿Cuál es tu género?

Buttons:
👨 Masculino
👩 Femenino  
🔀 Prefiero no decir

English Message:
3️⃣ What's your gender?

Buttons:
👨 Male
👩 Female
🔀 Prefer not to say

Custom Field: gender
Values: "male", "female", "other"
```

### **6.4 Question 4: Height**
```
Flow Name: "Quiz Question 4"

Spanish Message:
4️⃣ ¿Cuánto mides?

Por favor escribe tu altura en centímetros
Ejemplo: 175

Input Type: Text Input
Custom Field: height_cm

English Message:
4️⃣ What's your height?

Please write your height in centimeters
Example: 175

Validation: Must be number between 140-220
```

### **6.5 Question 5: Current Weight**
```
Flow Name: "Quiz Question 5"

Spanish Message:
5️⃣ ¿Cuánto pesas actualmente?

Por favor escribe tu peso en kilogramos
Ejemplo: 70

Input Type: Text Input
Custom Field: weight_kg

English Message:
5️⃣ What's your current weight?

Please write your weight in kilograms
Example: 70

Validation: Must be number between 40-200
```

### **6.6 Question 6: Primary Goal**
```
Flow Name: "Quiz Question 6"

Spanish Message:
6️⃣ ¿Cuál es tu objetivo principal?

Buttons:
🔥 Perder peso
💪 Ganar músculo
⚖️ Mantener peso
🏃 Mejorar rendimiento

English Message:
6️⃣ What's your primary goal?

Buttons:
🔥 Lose weight
💪 Gain muscle
⚖️ Maintain weight
🏃 Improve performance

Custom Field: goal
Values: "lose", "gain", "maintain", "performance"
```

### **6.7 Question 7: Target Weight (Conditional)**
```
Flow Name: "Quiz Question 7"

Condition: IF goal = "lose" OR goal = "gain"

Spanish Message:
7️⃣ ¿Cuál es tu peso objetivo?

Escribe tu peso meta en kilogramos
Ejemplo: 65

English Message:
7️⃣ What's your target weight?

Write your goal weight in kilograms
Example: 65

Custom Field: target_weight_kg

If goal = "maintain" or "performance": Skip to Question 8
```

### **6.8 Question 8: Timeline**
```
Flow Name: "Quiz Question 8"

Spanish Message:
8️⃣ ¿En cuánto tiempo quieres lograr tu objetivo?

Quick Replies:
1-3 meses | 3-6 meses | 6-12 meses | Más de 1 año

English Message:
8️⃣ In how much time do you want to achieve your goal?

Quick Replies:
1-3 months | 3-6 months | 6-12 months | More than 1 year

Custom Field: timeline
Values: "1-3m", "3-6m", "6-12m", "12m+"
```

### **6.9 Question 9: Activity Level**
```
Flow Name: "Quiz Question 9"

Spanish Message:
9️⃣ ¿Qué tan activo eres?

Buttons:
😴 Sedentario (oficina, poco ejercicio)
🚶 Ligeramente activo (ejercicio 1-3 días)
🏃 Moderadamente activo (ejercicio 3-5 días)
💪 Muy activo (ejercicio 6-7 días)
🏋️ Extremadamente activo (atleta)

English Message:
9️⃣ How active are you?

Buttons:
😴 Sedentary (office, little exercise)
🚶 Lightly active (exercise 1-3 days)
🏃 Moderately active (exercise 3-5 days)
💪 Very active (exercise 6-7 days)
🏋️ Extremely active (athlete)

Custom Field: activity_level
Values: "sedentary", "light", "moderate", "active", "extreme"
```

### **6.10 Question 10: Sleep Hours**
```
Flow Name: "Quiz Question 10"

Spanish Message:
🔟 ¿Cuántas horas duermes por noche?

Quick Replies:
4-5 horas | 6-7 horas | 8-9 horas | Más de 9

English Message:
🔟 How many hours do you sleep per night?

Quick Replies:
4-5 hours | 6-7 hours | 8-9 hours | More than 9

Custom Field: sleep_hours
Values: 4, 6, 8, 10
```

### **6.11 Question 11: Stress Level**
```
Flow Name: "Quiz Question 11"

Spanish Message:
1️⃣1️⃣ ¿Cuál es tu nivel de estrés diario?

Buttons:
😌 Bajo
😐 Moderado
😰 Alto

English Message:
1️⃣1️⃣ What's your daily stress level?

Buttons:
😌 Low
😐 Moderate
😰 High

Custom Field: stress_level
Values: "low", "moderate", "high"
```

### **6.12 Question 12: Dietary Restrictions**
```
Flow Name: "Quiz Question 12"

Spanish Message:
1️⃣2️⃣ ¿Tienes alguna restricción alimentaria?

Buttons:
✅ Sin restricciones
🥗 Vegetariano
🌱 Vegano
🚫🍞 Sin gluten
🚫🥛 Sin lactosa
🕌 Halal
✡️ Kosher
📝 Otra

English Message:
1️⃣2️⃣ Do you have any dietary restrictions?

Buttons:
✅ No restrictions
🥗 Vegetarian
🌱 Vegan
🚫🍞 Gluten-free
🚫🥛 Lactose-free
🕌 Halal
✡️ Kosher
📝 Other

Custom Field: diet_restrictions
```

### **6.13 Question 13: Food Allergies**
```
Flow Name: "Quiz Question 13"

Spanish Message:
1️⃣3️⃣ ¿Tienes alergias alimentarias?

Si tienes varias, escríbelas separadas por comas
Ejemplo: nueces, mariscos

Si no tienes, escribe "ninguna"

Input Type: Text Input
Custom Field: allergies

English Message:
1️⃣3️⃣ Do you have any food allergies?

If you have several, write them separated by commas
Example: nuts, shellfish

If you don't have any, write "none"
```

### **6.14 Question 14: Meals Per Day**
```
Flow Name: "Quiz Question 14"

Spanish Message:
1️⃣4️⃣ ¿Cuántas comidas haces al día?

Quick Replies:
2 comidas | 3 comidas | 4-5 comidas | Ayuno intermitente

English Message:
1️⃣4️⃣ How many meals do you eat per day?

Quick Replies:
2 meals | 3 meals | 4-5 meals | Intermittent fasting

Custom Field: meals_per_day
Values: 2, 3, 5, 0 (for IF)
```

### **6.15 Question 15: Final Confirmation**
```
Flow Name: "Quiz Question 15"

Spanish Message:
1️⃣5️⃣ ¡Última pregunta! 🎉

¿Estás listo para recibir tu plan nutricional personalizado?

Buttons:
✅ ¡Sí, calcular mi plan!
🔄 Revisar mis respuestas

English Message:
1️⃣5️⃣ Last question! 🎉

Are you ready to receive your personalized nutrition plan?

Buttons:
✅ Yes, calculate my plan!
🔄 Review my answers

Action: Set quiz_completed = "yes"
Next: Go to "Calculation Flow"
```

---

## **Step 7: Calculation Flow**

### **7.1 Processing Message**
```
Flow Name: "Calculation Flow"

Spanish Message:
🧮 Calculando tu plan personalizado...

Analizando:
✅ Tu metabolismo basal
✅ Tus necesidades calóricas
✅ Distribución de macronutrientes
✅ Recomendaciones específicas

⏱️ Esto tomará unos segundos...

English Message:
🧮 Calculating your personalized plan...

Analyzing:
✅ Your basal metabolism
✅ Your caloric needs
✅ Macronutrient distribution
✅ Specific recommendations

⏱️ This will take a few seconds...

Delay: 3 seconds
Next: External Request Action
```

### **7.2 API Integration**
```
External Request Configuration:
Method: POST
URL: https://caloria.vip/api/calculate-nutrition
Headers: 
  Content-Type: application/json
  Authorization: Bearer YOUR_API_KEY

Body (JSON):
{
  "subscriber_id": "{{subscriber_id}}",
  "language": "{{language}}",
  "age": "{{age}}",
  "gender": "{{gender}}",
  "height_cm": "{{height_cm}}",
  "weight_kg": "{{weight_kg}}",
  "goal": "{{goal}}",
  "target_weight_kg": "{{target_weight_kg}}",
  "activity_level": "{{activity_level}}",
  "sleep_hours": "{{sleep_hours}}",
  "stress_level": "{{stress_level}}",
  "diet_restrictions": "{{diet_restrictions}}",
  "allergies": "{{allergies}}",
  "meals_per_day": "{{meals_per_day}}"
}

Success Action: Parse JSON response and set custom fields
Error Action: Go to "Calculation Error" flow
```

---

## **Step 8: Results Preview Flow**

### **8.1 Free Results Preview**
```
Flow Name: "Results Preview"

Spanish Message:
🎯 ¡TUS RESULTADOS ESTÁN LISTOS! 

Hola {{user_name}}, aquí tienes tu análisis personalizado:

📊 **TU PLAN BÁSICO:**
🔥 Calorías diarias: {{daily_calories}} kcal
💪 Proteína: {{protein_g}}g
🍞 Carbohidratos: {{carbs_g}}g  
🥑 Grasas: {{fat_g}}g

✨ **PARA DESBLOQUEAR TU PLAN COMPLETO:**
• 📱 Menu personalizado de 7 días
• 🛒 Lista de compras optimizada
• 📅 Horarios de comidas ideales
• 🎯 Seguimiento diario detallado
• 💬 Soporte nutricional 24/7
• 📊 Análisis de progreso semanal

💎 **¿Quieres tu plan nutricional completo?**

English Message:
🎯 YOUR RESULTS ARE READY!

Hi {{user_name}}, here's your personalized analysis:

📊 **YOUR BASIC PLAN:**
🔥 Daily calories: {{daily_calories}} kcal
💪 Protein: {{protein_g}}g
🍞 Carbohydrates: {{carbs_g}}g
🥑 Fats: {{fat_g}}g

✨ **TO UNLOCK YOUR COMPLETE PLAN:**
• 📱 Personalized 7-day menu
• 🛒 Optimized shopping list
• 📅 Ideal meal timing
• 🎯 Detailed daily tracking
• 💬 24/7 nutritional support
• 📊 Weekly progress analysis

💎 **Want your complete nutrition plan?**

Buttons:
💳 Obtener Plan Completo ($19.99) | Get Complete Plan ($19.99)
📧 Enviar por email | Send by email
🔄 Hacer quiz otra vez | Retake quiz
```

---

## **Step 9: Payment Flow**

### **9.1 Payment Options**
```
Flow Name: "Payment Flow"

Spanish Message:
💎 **PLAN NUTRICIONAL COMPLETO**

Tu inversión: $19.99 USD (pago único)

**Lo que incluye:**
✅ Plan de comidas personalizado (7 días)
✅ Lista de compras optimizada
✅ Recetas fáciles paso a paso
✅ Horarios ideales de comidas
✅ Seguimiento diario de progreso
✅ Soporte nutricional por WhatsApp
✅ Actualizaciones según tu progreso
✅ Acceso de por vida

**Elige tu método de pago:**

Buttons:
💳 Stripe (Tarjeta)
🔗 PayPal
💰 Transferencia

English Message:
💎 **COMPLETE NUTRITION PLAN**

Your investment: $19.99 USD (one-time payment)

**What's included:**
✅ Personalized meal plan (7 days)
✅ Optimized shopping list
✅ Easy step-by-step recipes
✅ Ideal meal timing
✅ Daily progress tracking
✅ Nutritional support via WhatsApp
✅ Updates based on your progress
✅ Lifetime access

**Choose your payment method:**

Buttons:
💳 Stripe (Card)
🔗 PayPal
💰 Bank Transfer
```

### **9.2 Stripe Integration**
```
Stripe Payment Button Action:
1. External Request to generate payment link
2. Send payment URL to user
3. Set custom field: payment_status = "pending"
4. Start payment verification flow

Payment Link Generation:
POST https://caloria.vip/api/create-payment
{
  "subscriber_id": "{{subscriber_id}}",
  "amount": 1999,
  "currency": "usd",
  "description": "Plan Nutricional Caloria",
  "success_url": "https://caloria.vip/payment-success?subscriber={{subscriber_id}}",
  "cancel_url": "https://caloria.vip/payment-cancel"
}
```

---

## **Step 10: Premium Content Delivery**

### **10.1 Payment Success Flow**
```
Flow Name: "Payment Success"
Trigger: Payment webhook or API confirmation

Spanish Message:
🎉 ¡PAGO CONFIRMADO!

¡Bienvenido al Plan Completo de Caloria, {{user_name}}!

📱 **TU PLAN PERSONALIZADO:**

**SEMANA 1 - PLAN DE COMIDAS**
📅 Lunes:
🌅 Desayuno: Avena con frutas (420 kcal)
🌞 Almuerzo: Pollo a la plancha con quinoa (580 kcal)
🌙 Cena: Salmón con vegetales (650 kcal)
🥜 Snacks: Nueces y fruta (200 kcal)

📅 Martes:
[Continue with full week...]

**LISTA DE COMPRAS:**
🛒 Proteínas: Pollo (1kg), Salmón (500g), Huevos (12 unidades)
🥬 Verduras: Brócoli, Espinacas, Tomates, Cebolla
🍎 Frutas: Manzanas, Plátanos, Fresas
[Continue with full list...]

**HORARIOS RECOMENDADOS:**
⏰ 7:00 AM - Desayuno
⏰ 12:00 PM - Almuerzo  
⏰ 3:00 PM - Snack
⏰ 7:00 PM - Cena

English Message:
🎉 PAYMENT CONFIRMED!

Welcome to Caloria's Complete Plan, {{user_name}}!

📱 **YOUR PERSONALIZED PLAN:**
[English version of the above content]

Action: Set payment_status = "paid"
```

### **10.2 Daily Tracking Setup**
```
Flow Name: "Daily Tracking Setup"

Spanish Message:
📊 **SEGUIMIENTO DIARIO ACTIVADO**

Ahora recibirás:
• 🌅 Recordatorio de desayuno (7:00 AM)
• 🌞 Recordatorio de almuerzo (12:00 PM)
• 🌙 Recordatorio de cena (7:00 PM)
• 📈 Resumen diario (9:00 PM)
• 📊 Análisis semanal (domingos)

Puedes pausar las notificaciones escribiendo "PAUSA"

¿Quieres empezar mañana?

Buttons:
✅ Sí, empezar mañana
📅 Configurar horarios
⚙️ Configuraciones

Actions:
1. Set up automated sequences
2. Schedule daily reminders
3. Create weekly check-ins
```

---

## **Step 11: Testing Strategy**

### **11.1 Pre-Launch Testing**
```
Testing Checklist:
□ Test Spanish flow completely
□ Test English flow completely
□ Test language switching
□ Test all conditional logic
□ Test payment integration
□ Test API calculations
□ Test error handling
□ Test mobile compatibility
□ Test with different phone numbers
□ Test edge cases (very tall/short, extreme weights)
```

### **11.2 A/B Testing Setup**
```
Test Variables:
- Question order
- Button text and colors
- Payment timing (after Q15 vs after results)
- Pricing display ($19.99 vs $24.99 vs $29.99)
- Results presentation format
- Call-to-action phrases
```

---

## **Step 12: Analytics & Monitoring**

### **12.1 Key Metrics Setup**
```
Track in ManyChat + Custom Analytics:
1. Quiz start rate (how many start after welcome)
2. Question completion rate (Q1→Q2→...→Q15)
3. Drop-off points (which questions lose users)
4. Payment conversion rate (results → payment)
5. Language preference distribution
6. Goal distribution (lose/gain/maintain/performance)
7. Average completion time
8. Most common diet restrictions
9. Payment method preferences
10. Daily active users post-payment
```

### **12.2 Webhook Setup for Analytics**
```
Configure webhooks to send data to your analytics:
POST https://caloria.vip/analytics/manychat-event
{
  "event_type": "question_completed",
  "subscriber_id": "{{subscriber_id}}",
  "question_number": 5,
  "answer": "{{answer}}",
  "timestamp": "{{timestamp}}",
  "language": "{{language}}"
}
```

---

## **Step 13: Launch Preparation**

### **13.1 Content Preparation**
```
Prepare all content in both languages:
□ Welcome messages
□ Question texts
□ Button labels
□ Error messages
□ Success messages
□ Payment confirmations
□ Premium content (meal plans)
□ Shopping lists
□ Recipes
□ Daily reminders
```

### **13.2 Final Checklist**
```
Pre-Launch:
□ All flows tested
□ Payment system working
□ API endpoints responding
□ Analytics tracking
□ Error handling in place
□ Customer support ready
□ Backup plans for failures
□ Marketing materials ready
□ Social proof prepared
□ Legal compliance checked
```

---

## **🎯 Implementation Timeline**

### **Week 1: Setup & Basic Flows**
- ManyChat account setup
- Custom fields creation
- Language selection flow
- Welcome flows (Spanish/English)
- Questions 1-5 implementation

### **Week 2: Complete Quiz & Logic**
- Questions 6-15 implementation
- Conditional logic setup
- API integration for calculations
- Results preview flow
- Testing basic functionality

### **Week 3: Payment & Premium Content**
- Payment flow setup
- Stripe integration
- Premium content creation
- Payment success flow
- Daily tracking setup

### **Week 4: Testing & Launch**
- Complete testing (all scenarios)
- A/B testing setup
- Analytics implementation
- Error handling verification
- Soft launch with limited users

---

## **📊 Success Metrics**

### **Phase 1: Engagement (First Month)**
- Target: 70% quiz completion rate
- Target: 50% language engagement (balanced ES/EN)
- Target: <5% error rate in flows

### **Phase 2: Conversion (Months 2-3)**
- Target: 15% payment conversion rate
- Target: 80% user satisfaction score
- Target: <24h payment processing time

### **Phase 3: Retention (Months 4-6)**
- Target: 60% daily active users (paid)
- Target: 90% weekly retention (paid users)
- Target: 4.5+ star rating average

---

## **🚀 Ready to Implement**

This comprehensive guide provides everything needed to implement a professional, bilingual nutrition quiz in ManyChat that can handle complex logic, calculations, and payments while maintaining a smooth WhatsApp-native experience!

**Estimated Implementation Time:** 1-2 weeks for full setup and testing.

**Next Step:** Start with Step 1 (ManyChat account setup) and follow the guide sequentially. 