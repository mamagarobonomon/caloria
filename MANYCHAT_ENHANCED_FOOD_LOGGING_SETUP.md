# ManyChat Enhanced Food Logging Setup Guide

**⚠️ REQUIRED STEP AFTER WHATSAPP BUSINESS ACCOUNT VERIFICATION ⚠️**

This document provides step-by-step instructions for configuring ManyChat to support the enhanced food logging system with Gemini Vision AI, clarification questions, and multi-part responses.

**🌍 BILINGUAL SUPPORT: Spanish (default) & English**

---

## 📋 **PREREQUISITES**

- ✅ WhatsApp Business Account verified and approved
- ✅ ManyChat account connected to WhatsApp Business
- ✅ Caloria server deployed and running at https://caloria.vip
- ✅ Enhanced bilingual food logging system deployed (completed)

---

## 🌍 **STEP 1: LANGUAGE DETECTION & SETUP**

### **1.1 Language Strategy Configuration**

**Default Language Behavior:**
```
Default: Spanish (es) 
Alternative: English (en)
Detection: Automatic based on user input
Storage: User.language field in database
```

**Language Detection Methods:**
```
Method 1: Automatic detection from first message
Method 2: Language selection buttons
Method 3: Command-based switching (/lang en, /lang es)
Recommended: Combination of all methods
```

### **1.2 Language Switching Flow**

**Create Language Selection Flow:**
```
Flow Name: "Language Selection"
Trigger: Keywords ["language", "idioma", "lang", "english", "español"]

Message (Bilingual):
🌍 Language / Idioma

Choose your preferred language:
Elige tu idioma preferido:

Buttons:
🇪🇸 Español
🇺🇸 English
```

**Button Actions:**
```
Spanish Button:
- Payload: "set_language:es"
- Action: Send to webhook
- Response: "🇪🇸 Idioma cambiado a español..."

English Button:
- Payload: "set_language:en" 
- Action: Send to webhook
- Response: "🇺🇸 Language switched to English..."
```

---

## 🔧 **STEP 2: WEBHOOK CONFIGURATION**

### **2.1 Enhanced Webhook Setup**

Navigate to: **ManyChat → Settings → Integrations → Webhooks**

**Configure Main Webhook:**
```
Webhook Name: Caloria Enhanced Food Analysis (Bilingual)
URL: https://caloria.vip/webhook/manychat
Method: POST
Content-Type: application/json
```

**Enable Triggers:**
- ✅ Message Received
- ✅ Quick Reply Selected
- ✅ Attachment Received
- ✅ User Input
- ✅ Language Detection

### **2.2 Bilingual Webhook Data Payload**

**Configure Webhook to Send:**
```json
{
  "subscriber_id": "{{user_id}}",
  "type": "{{message_type}}",
  "text": "{{text}}",
  "attachments": "{{attachments}}",
  "quick_reply": {
    "payload": "{{payload}}",
    "title": "{{quick_reply_title}}"
  },
  "first_name": "{{first_name}}",
  "last_name": "{{last_name}}",
  "timestamp": "{{current_timestamp}}",
  "user_language": "{{language}}",
  "locale": "{{locale}}"
}
```

---

## 🎯 **STEP 3: BILINGUAL FLOW SETUP**

### **3.1 Create Enhanced Food Analysis Flow**

**Flow Details:**
```
Flow Name: "Enhanced Food Analysis (Bilingual)"
Description: "Comprehensive food logging with Gemini Vision AI in Spanish/English"
Status: Active
Default Language: Spanish
```

**Flow Triggers:**
- Keywords: ["food", "meal", "analyze", "nutrition", "calories", "comida", "analizar", "nutrición", "calorías"]
- Image Upload (any image attachment)
- Default reply for unrecognized content

### **3.2 Language-Aware Flow Structure**

```
Bilingual Flow Sequence:
1. Language Detection → 
2. User Input (Image/Text) → 
3. Send to Webhook (with language) → 
4. Dynamic Response (language-specific) → 
5. Handle User Interaction → 
6. Final Analysis/New Log (localized)
```

**Node 1: Language Detection**
```
Condition: Check user language preference
- If language not set: Show language selection
- If Spanish: Use Spanish flow
- If English: Use English flow
- Store language preference in custom field
```

**Node 2: Enhanced Image Analysis**
```
Action Type: External Request
URL: https://caloria.vip/webhook/manychat
Method: POST
Variables to Send:
- subscriber_id: {{user_id}}
- type: "image"
- image_url: {{attachment_url}}
- attachments: {{attachments}}
- user_language: {{language}}
```

**Node 3: Language-Specific Response**
```
Response Processing:
- Parse webhook response JSON
- Display message in user's language
- Show quick reply buttons (localized)
- Store session_key for clarification flow
```

---

## 🔘 **STEP 4: BILINGUAL QUICK REPLY CONFIGURATION**

### **4.1 Spanish Button Setup**

**Analyze Button (Spanish):**
```
Button Title: "Analizar"
Button Type: Quick Reply
Payload Format: "analyze_food:{{session_key}}"
Action: Send to External Webhook
Language: Spanish (es)
```

**New Log Button (Spanish):**
```
Button Title: "Nuevo Registro"
Button Type: Quick Reply
Payload: "new_food_log"
Action: Send to External Webhook
Language: Spanish (es)
```

### **4.2 English Button Setup**

**Analyze Button (English):**
```
Button Title: "Analyze"
Button Type: Quick Reply
Payload Format: "analyze_food:{{session_key}}"
Action: Send to External Webhook
Language: English (en)
```

**New Log Button (English):**
```
Button Title: "New Log"
Button Type: Quick Reply
Payload: "new_food_log"
Action: Send to External Webhook
Language: English (en)
```

### **4.3 Language Switch Buttons**

**Language Toggle Buttons:**
```
Spanish Switch:
- Title: "🇪🇸 Español"
- Payload: "set_language:es"
- Always available in menu

English Switch:
- Title: "🇺🇸 English"  
- Payload: "set_language:en"
- Always available in menu
```

---

## 📱 **STEP 5: BILINGUAL MESSAGE ROUTING**

### **5.1 Image Message Handler (Language-Aware)**

**Trigger Configuration:**
```
Trigger: User uploads image/photo
Condition: Attachment type = image
Language Detection: Automatic
Actions:
1. Detect/confirm user language
2. Extract image URL
3. Send to webhook with language data
4. Display response with localized clarification questions
5. Show language-appropriate quick reply buttons
```

**Implementation:**
```
Step 1: Language Check
- Check user language preference
- Default to Spanish if not set

Step 2: Send to Webhook
- URL: https://caloria.vip/webhook/manychat
- Include image URL, user data, and language

Step 3: Display Localized Response
- Show webhook response message in user's language
- Display quick reply buttons (localized)
- Store session information with language context
```

### **5.2 Text Message Handler (Bilingual)**

**Trigger Configuration:**
```
Trigger: User sends text message
Language Detection: Automatic from content
Purpose: Handle clarification responses and general text
```

**Implementation:**
```
Step 1: Language Detection
- Analyze text for language indicators
- Update user language preference if detected
- Default to existing user language

Step 2: Content Routing
- If clarification session active: Send as clarification
- If language command: Handle language switch
- If food description: Process food analysis
- If quiz response: Handle quiz flow

Step 3: Localized Response
- Return response in user's preferred language
- Include appropriate error messages if needed
```

### **5.3 Language Command Handler**

**Commands Setup:**
```
Spanish Commands:
- "/español" or "/es" → Set language to Spanish
- "/idioma" → Show language selection menu

English Commands:
- "/english" or "/en" → Set language to English
- "/language" → Show language selection menu
```

---

## 🔄 **STEP 6: BILINGUAL RESPONSE HANDLING**

### **6.1 Dynamic Response Processing (Language-Aware)**

**Response Format Support:**
```javascript
Expected Webhook Response:
{
  "version": "v2",
  "content": {
    "messages": [
      {
        "type": "text",
        "text": "Response message in user's language",
        "quick_replies": [
          {"title": "Analizar/Analyze", "payload": "analyze_food:session_key"},
          {"title": "Nuevo Registro/New Log", "payload": "new_food_log"}
        ]
      }
    ]
  },
  "session_key": "food_analysis_user_timestamp",
  "requires_clarification": true,
  "language": "es/en"
}
```

### **6.2 Multi-Message Response Handler (Bilingual)**

**For Comprehensive Analysis:**
```
Response Type: Multiple sequential messages (language-specific)
Separator: "---"
Format: Individual message cards
Language: Based on user preference
Actions:
1. Parse messages array
2. Send each message sequentially in user's language
3. Add delays between messages (2-3 seconds)
4. Complete analysis flow with localized completion message
```

### **6.3 Error Handling (Bilingual)**

**Fallback Responses:**
```
Spanish Errors:
- Webhook Error: "❌ Lo siento, no pude analizar tu comida. Por favor intenta de nuevo."
- Image Error: "❌ No pude procesar la imagen. Por favor envía una foto más clara."
- Session Expired: "❌ Sesión expirada. Por favor envía tu foto de nuevo."
- Unknown Error: "❌ Algo salió mal. Por favor intenta de nuevo."

English Errors:
- Webhook Error: "❌ Sorry, I couldn't analyze your food. Please try again."
- Image Error: "❌ Unable to process image. Please send a clearer photo."
- Session Expired: "❌ Session expired. Please send your photo again."
- Unknown Error: "❌ Something went wrong. Please try again."
```

---

## ⚙️ **STEP 7: BILINGUAL CUSTOM FIELDS**

### **7.1 Required Custom Fields**

**Create Custom Fields:**
```
1. User Language
   - Field Name: user_language
   - Type: Text
   - Default: "es"
   - Purpose: Store user's preferred language

2. Food Analysis Session
   - Field Name: food_session_key
   - Type: Text
   - Purpose: Store active analysis session

3. Language Detection Status
   - Field Name: language_detected
   - Type: Boolean
   - Purpose: Track if language has been auto-detected

4. Last Message Language
   - Field Name: last_message_lang
   - Type: Text
   - Purpose: Track language of last interaction

5. Analysis Count by Language
   - Field Name: analysis_count_es
   - Field Name: analysis_count_en
   - Type: Number
   - Purpose: Track usage by language
```

### **7.2 Language Session Management**

**Session Storage:**
```
On Image Analysis:
- Store session_key with language context
- Set pending_clarification = true
- Record language used for analysis
- Update last_message_lang field

On Analysis Complete:
- Clear session_key
- Set pending_clarification = false
- Increment language-specific analysis count
- Maintain language preference
```

---

## 🧪 **STEP 8: BILINGUAL TESTING CONFIGURATION**

### **8.1 Language-Specific Test Scenarios**

**Spanish Testing:**
```
1. Send "hola" → Verify Spanish language detection
2. Upload food image → Check Spanish clarification questions
3. Click "Analizar" → Verify Spanish comprehensive response
4. Send "nuevo registro" → Check Spanish new log prompt
5. Test language switching to English
```

**English Testing:**
```
1. Send "hello" → Verify English language detection
2. Upload food image → Check English clarification questions
3. Click "Analyze" → Verify English comprehensive response  
4. Send "new log" → Check English new log prompt
5. Test language switching to Spanish
```

**Mixed Language Testing:**
```
1. Start in Spanish, switch to English mid-session
2. Test session persistence across language changes
3. Verify error messages appear in correct language
4. Test clarification responses in both languages
```

### **8.2 Language Detection Debug**

**Enable ManyChat Debug for Languages:**
```
Settings → General → Debug Mode: ON
Language Tracking: Enabled
- Monitor language detection accuracy
- View webhook requests with language data
- Check custom field updates for language
- Validate bilingual flow execution
```

---

## 🚨 **STEP 9: BILINGUAL CONFIGURATION CHECKLIST**

### **9.1 Must-Configure Items (Language-Aware)**

- [ ] **Webhook URL**: https://caloria.vip/webhook/manychat configured with language support
- [ ] **Language detection** automatic and manual methods working
- [ ] **Spanish image uploads** trigger webhook with Spanish clarification
- [ ] **English image uploads** trigger webhook with English clarification
- [ ] **Bilingual quick reply buttons** display correctly after analysis
- [ ] **Language-specific button clicks** send correct payloads
- [ ] **Multi-message responses** display in user's preferred language
- [ ] **Session management** maintains language context
- [ ] **Error handling** provides messages in correct language
- [ ] **Language switching** works via buttons and commands

### **9.2 Language Performance Settings**

**Optimize for Bilingual Experience:**
```
Spanish Response Time: <5 seconds target
English Response Time: <5 seconds target
Language Detection: <1 second
Language Switching: Immediate
Image Processing: Support both language prompts
File Size Limit: 16MB maximum
Response Accuracy: 95%+ in detected language
```

---

## 📊 **STEP 10: BILINGUAL MONITORING & ANALYTICS**

### **10.1 Language-Specific Metrics**

**Track Key Metrics by Language:**
```
Spanish Users:
- Image analyses per day
- Clarification question engagement rate
- Button click rates (Analizar vs Nuevo Registro)
- Error rates and response times

English Users:
- Image analyses per day  
- Clarification question engagement rate
- Button click rates (Analyze vs New Log)
- Error rates and response times

Mixed Language:
- Language switching frequency
- Session completion rates across languages
- User preference changes over time
```

### **10.2 Bilingual Analytics Setup**

**Configure ManyChat Analytics:**
```
Spanish Conversion Goals:
- successful_food_analysis_es
- clarification_engagement_es
- multi_day_usage_retention_es

English Conversion Goals:
- successful_food_analysis_en
- clarification_engagement_en
- multi_day_usage_retention_en

Language Events:
- language_detected_spanish
- language_detected_english
- language_switched_es_to_en
- language_switched_en_to_es
- bilingual_user_identified
```

---

## 🎯 **STEP 11: BILINGUAL GO-LIVE PREPARATION**

### **11.1 Final Bilingual Checklist**

**Before Enabling for Users:**
- [ ] Spanish and English webhook endpoints tested
- [ ] Both language image analyses produce expected results
- [ ] Bilingual buttons work correctly
- [ ] Multi-part responses display in correct language
- [ ] Language detection and switching functions
- [ ] Error handling works in both languages
- [ ] Session management maintains language context
- [ ] Performance meets targets in both languages

### **11.2 Bilingual User Communication**

**Announcement Message (Bilingual):**
```
🎉 NEW: Enhanced Food Analysis! / ¡NUEVO: Análisis Avanzado de Alimentos!

🇪🇸 Envíame una foto de tu comida y te proporcionaré:
✨ Identificación detallada de alimentos con pesos
📋 Preguntas de aclaración para mayor precisión  
📊 Análisis nutricional comprehensivo
💡 Recomendaciones de salud personalizadas

🇺🇸 Send me a photo of your meal and I'll provide:
✨ Detailed food identification with weights
📋 Clarification questions for accuracy
📊 Comprehensive nutritional analysis  
💡 Personalized health recommendations

Try it now - just send a photo! / ¡Pruébalo ahora - solo envía una foto! 📸
```

---

## 🚀 **BILINGUAL IMPLEMENTATION TIMELINE**

**Estimated Setup Time: 3-5 hours**

```
Phase 1 (45 min): Language detection and webhook configuration
Phase 2 (90 min): Bilingual flow setup and message routing  
Phase 3 (60 min): Button configuration and response handling
Phase 4 (90 min): Comprehensive bilingual testing
Phase 5 (15 min): Go-live preparation and user communication
```

---

## 📞 **BILINGUAL SUPPORT & TROUBLESHOOTING**

### **Common Language Issues:**

**Language Detection Not Working:**
- Check webhook receives language data
- Verify language detection logic in webhook handler
- Test with clear Spanish/English phrases

**Wrong Language Responses:**
- Confirm user language field in database
- Check webhook language parameter
- Verify message templates for both languages

**Language Switching Issues:**
- Test language switch payloads
- Check custom field updates
- Verify session maintains language context

**Mixed Language Sessions:**
- Check session management with language context
- Verify clarification questions match user language
- Test session persistence across language changes

---

## ✅ **BILINGUAL COMPLETION CONFIRMATION**

Once all steps are completed, the enhanced bilingual food logging system will provide:

✅ **Detailed food analysis** with Gemini Vision AI in Spanish/English
✅ **Interactive clarification questions** in user's preferred language
✅ **Professional multi-part responses** fully localized
✅ **Seamless bilingual button interactions**
✅ **Comprehensive nutritional insights** with cultural awareness
✅ **Automatic language detection** and manual switching
✅ **Error handling** in appropriate language

**Your users will experience professional-grade food analysis with personalized recommendations in their preferred language!** 🥗📊🌍✨

---

**Document Version:** 2.0 (Bilingual)  
**Last Updated:** December 2024  
**Status:** Ready for Implementation  
**Required After:** WhatsApp Business Account Verification  
**Languages Supported:** Spanish (default) & English 