# ManyChat Enhanced Food Logging Setup Guide

**⚠️ REQUIRED STEP AFTER WHATSAPP BUSINESS ACCOUNT VERIFICATION ⚠️**

This document provides step-by-step instructions for configuring ManyChat to support the enhanced food logging system with Gemini Vision AI, clarification questions, and multi-part responses.

---

## 📋 **PREREQUISITES**

- ✅ WhatsApp Business Account verified and approved
- ✅ ManyChat account connected to WhatsApp Business
- ✅ Caloria server deployed and running at https://caloria.vip
- ✅ Enhanced food logging system deployed (completed)

---

## 🔧 **STEP 1: WEBHOOK CONFIGURATION**

### **1.1 Basic Webhook Setup**

Navigate to: **ManyChat → Settings → Integrations → Webhooks**

**Configure Main Webhook:**
```
Webhook Name: Caloria Enhanced Food Analysis
URL: https://caloria.vip/webhook/manychat
Method: POST
Content-Type: application/json
```

**Enable Triggers:**
- ✅ Message Received
- ✅ Quick Reply Selected
- ✅ Attachment Received
- ✅ User Input

### **1.2 Webhook Data Payload**

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
  "timestamp": "{{current_timestamp}}"
}
```

---

## 🎯 **STEP 2: FLOW SETUP FOR ENHANCED FOOD ANALYSIS**

### **2.1 Create Main Food Logging Flow**

**Flow Details:**
```
Flow Name: "Enhanced Food Analysis"
Description: "Comprehensive food logging with Gemini Vision AI"
Status: Active
```

**Flow Triggers:**
- Keywords: ["food", "meal", "analyze", "nutrition", "calories"]
- Image Upload (any image attachment)
- Default reply for unrecognized content

### **2.2 Flow Structure**

```
Flow Sequence:
1. User Input (Image/Text) → 
2. Send to Webhook → 
3. Dynamic Response → 
4. Handle User Interaction → 
5. Final Analysis/New Log
```

**Node 1: Input Detection**
```
Condition: Check message type
- If Image: Go to Image Analysis
- If Text: Go to Text Processing
- If Quick Reply: Go to Button Handler
```

**Node 2: Image Analysis Webhook**
```
Action Type: External Request
URL: https://caloria.vip/webhook/manychat
Method: POST
Variables to Send:
- subscriber_id: {{user_id}}
- type: "image"
- image_url: {{attachment_url}}
- attachments: {{attachments}}
```

**Node 3: Dynamic Response Handler**
```
Response Processing:
- Parse webhook response JSON
- Display message content
- Show quick reply buttons if present
- Store session_key for clarification flow
```

---

## 🔘 **STEP 3: QUICK REPLY BUTTON CONFIGURATION**

### **3.1 Analyze Button Setup**

**Button Configuration:**
```
Button Title: "Analyze"
Button Type: Quick Reply
Payload Format: "analyze_food:{{session_key}}"
Action: Send to External Webhook
```

**Webhook Action for Analyze:**
```
URL: https://caloria.vip/webhook/manychat
Method: POST
Data:
{
  "subscriber_id": "{{user_id}}",
  "type": "quick_reply",
  "quick_reply": {
    "payload": "{{payload}}"
  }
}
```

### **3.2 New Log Button Setup**

**Button Configuration:**
```
Button Title: "New Log"
Button Type: Quick Reply
Payload: "new_food_log"
Action: Send to External Webhook
```

**Webhook Action for New Log:**
```
URL: https://caloria.vip/webhook/manychat
Method: POST
Data:
{
  "subscriber_id": "{{user_id}}",
  "type": "quick_reply",
  "quick_reply": {
    "payload": "new_food_log"
  }
}
```

---

## 📱 **STEP 4: MESSAGE TYPE ROUTING**

### **4.1 Image Message Handler**

**Trigger Configuration:**
```
Trigger: User uploads image/photo
Condition: Attachment type = image
Actions:
1. Extract image URL
2. Send to webhook with image data
3. Display response with clarification questions
4. Show quick reply buttons
```

**Implementation:**
```
Step 1: Detect Image Upload
- Condition: {{attachment_type}} = "image"

Step 2: Send to Webhook
- URL: https://caloria.vip/webhook/manychat
- Include image URL and user data

Step 3: Display Response
- Show webhook response message
- Display quick reply buttons
- Store session information
```

### **4.2 Text Message Handler**

**Trigger Configuration:**
```
Trigger: User sends text message
Condition: No quick reply payload present
Purpose: Handle clarification responses
```

**Implementation:**
```
Step 1: Check for Active Session
- Look for pending food analysis

Step 2: Send as Clarification
- URL: https://caloria.vip/webhook/manychat
- Include text as clarification input

Step 3: Process Response
- Display comprehensive analysis
- Complete food logging session
```

### **4.3 Quick Reply Handler**

**Trigger Configuration:**
```
Trigger: User clicks quick reply button
Condition: Payload present
Actions:
1. Extract payload data
2. Send to appropriate webhook endpoint
3. Process response
```

---

## 🔄 **STEP 5: RESPONSE HANDLING CONFIGURATION**

### **5.1 Dynamic Response Processing**

**Response Format Support:**
```javascript
Expected Webhook Response:
{
  "version": "v2",
  "content": {
    "messages": [
      {
        "type": "text",
        "text": "Response message",
        "quick_replies": [
          {"title": "Analyze", "payload": "analyze_food:session_key"},
          {"title": "New Log", "payload": "new_food_log"}
        ]
      }
    ]
  },
  "session_key": "food_analysis_user_timestamp",
  "requires_clarification": true
}
```

### **5.2 Multi-Message Response Handler**

**For Comprehensive Analysis:**
```
Response Type: Multiple sequential messages
Separator: "---"
Format: Individual message cards
Actions:
1. Parse messages array
2. Send each message sequentially
3. Add delays between messages (2-3 seconds)
4. Complete analysis flow
```

### **5.3 Error Handling**

**Fallback Responses:**
```
Webhook Error: "❌ Sorry, I couldn't analyze your food. Please try again."
Image Error: "❌ Unable to process image. Please send a clearer photo."
Session Expired: "❌ Session expired. Please send your photo again."
Unknown Error: "❌ Something went wrong. Please try again."
```

---

## ⚙️ **STEP 6: CUSTOM FIELDS AND VARIABLES**

### **6.1 Required Custom Fields**

**Create Custom Fields:**
```
1. Food Analysis Session
   - Field Name: food_session_key
   - Type: Text
   - Purpose: Store active analysis session

2. Last Analysis Timestamp  
   - Field Name: last_food_analysis
   - Type: DateTime
   - Purpose: Track analysis frequency

3. Pending Clarification
   - Field Name: pending_clarification
   - Type: Boolean
   - Purpose: Track clarification state

4. Analysis Count
   - Field Name: total_food_analyses
   - Type: Number
   - Purpose: Track user engagement
```

### **6.2 Session Management**

**Session Storage:**
```
On Image Analysis:
- Store session_key in custom field
- Set pending_clarification = true
- Record timestamp

On Analysis Complete:
- Clear session_key
- Set pending_clarification = false
- Increment analysis_count
```

---

## 🧪 **STEP 7: TESTING CONFIGURATION**

### **7.1 Test Scenarios**

**Image Upload Test:**
```
1. Send test image to bot
2. Verify webhook receives image URL
3. Check response shows description + questions
4. Confirm buttons are clickable
5. Validate session management
```

**Button Click Test:**
```
1. Click "Analyze" button
2. Verify payload sent to webhook
3. Check comprehensive response received
4. Confirm multi-message formatting
5. Validate session cleanup
```

**Text Clarification Test:**
```
1. Send image, get clarification questions
2. Send text response (e.g., "cheddar cheese")
3. Verify text processed as clarification
4. Check enhanced analysis received
5. Confirm flow completion
```

### **7.2 Debug Mode Setup**

**Enable ManyChat Debug:**
```
Settings → General → Debug Mode: ON
- View webhook requests/responses
- Monitor flow execution
- Check variable values
- Validate custom field updates
```

---

## 🚨 **STEP 8: CRITICAL CONFIGURATION CHECKLIST**

### **8.1 Must-Configure Items**

- [ ] **Webhook URL**: https://caloria.vip/webhook/manychat configured
- [ ] **Image uploads** trigger webhook with attachment URL
- [ ] **Quick reply buttons** display correctly after image analysis
- [ ] **Button clicks** send correct payloads to webhook
- [ ] **Multi-message responses** display properly with separators
- [ ] **Session management** works for clarification flow
- [ ] **Error handling** provides meaningful fallback messages
- [ ] **Custom fields** store session and user data

### **8.2 Performance Settings**

**Optimize for Enhanced Experience:**
```
Message Delays: 2-3 seconds between multi-part responses
Webhook Timeout: 30 seconds
Image Processing: Support PNG, JPG, JPEG formats
File Size Limit: 16MB maximum
Response Time: <5 seconds target
```

---

## 📊 **STEP 9: MONITORING AND ANALYTICS**

### **9.1 Track Key Metrics**

**Important Metrics to Monitor:**
```
- Image analyses per day
- Clarification question engagement rate
- Button click rates (Analyze vs New Log)
- Webhook response times
- Error rates and types
- User completion rates
```

### **9.2 Analytics Setup**

**Configure ManyChat Analytics:**
```
Conversion Goals:
- Successful food analysis completion
- User engagement with clarification questions
- Multi-day usage retention

Custom Events:
- image_analysis_started
- clarification_provided
- analysis_completed
- new_log_initiated
```

---

## 🎯 **STEP 10: GO-LIVE PREPARATION**

### **10.1 Final Checklist**

**Before Enabling for Users:**
- [ ] All webhook endpoints tested and responding
- [ ] Image analysis produces expected clarification questions
- [ ] Buttons work and send correct payloads
- [ ] Multi-part responses display correctly
- [ ] Session management functions properly
- [ ] Error handling provides good user experience
- [ ] Performance meets targets (<5 sec response)

### **10.2 User Communication**

**Announcement Message:**
```
🎉 NEW: Enhanced Food Analysis!

Send me a photo of your meal and I'll provide:
✨ Detailed food identification with weights
📋 Clarification questions for accuracy
📊 Comprehensive nutritional analysis
💡 Personalized health recommendations

Try it now - just send a photo! 📸
```

---

## 🚀 **IMPLEMENTATION TIMELINE**

**Estimated Setup Time: 2-4 hours**

```
Phase 1 (30 min): Basic webhook configuration
Phase 2 (60 min): Flow setup and message routing  
Phase 3 (45 min): Button configuration and response handling
Phase 4 (60 min): Testing and debugging
Phase 5 (15 min): Go-live preparation
```

---

## 📞 **SUPPORT AND TROUBLESHOOTING**

### **Common Issues:**

**Webhook Not Responding:**
- Check server status at https://caloria.vip/health
- Verify webhook URL configuration
- Test endpoint manually with Postman

**Buttons Not Working:**
- Verify quick reply payload format
- Check webhook receives button data
- Validate response handling logic

**Images Not Processing:**
- Confirm image URL accessible
- Check file size and format
- Verify Gemini Vision AI availability

**Session Management Issues:**
- Check custom field configuration
- Verify session key generation
- Test session retrieval logic

---

## ✅ **COMPLETION CONFIRMATION**

Once all steps are completed, the enhanced food logging system will provide:

✅ **Detailed food analysis** with Gemini Vision AI
✅ **Interactive clarification questions** 
✅ **Professional multi-part responses**
✅ **Seamless button interactions**
✅ **Comprehensive nutritional insights**

**Your users will experience professional-grade food analysis with personalized recommendations!** 🥗📊✨

---

**Document Version:** 1.0  
**Last Updated:** December 2024  
**Status:** Ready for Implementation  
**Required After:** WhatsApp Business Account Verification 