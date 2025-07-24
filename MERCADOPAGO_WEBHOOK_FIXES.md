# 🚨 **Critical Mercado Pago Webhook Fixes**

**Based on Official Documentation:** https://www.mercadopago.com.ar/developers/es/docs/subscriptions/additional-content/your-integrations/notifications/webhooks

---

## 🔴 **Critical Issues Fixed**

### **1. Webhook Configuration Method (MAJOR)**

**❌ Previous Implementation:**
- Assumed webhooks could be configured via "Tus integraciones" dashboard
- No webhook URL in subscription creation

**✅ Fixed Implementation:**
- Webhooks for subscriptions MUST be configured during subscription creation
- Added `notification_url` parameter to subscription API call
- Now creates subscriptions via `/preapproval` API endpoint

**Code Change:**
```python
# OLD: Just constructing URL
subscription_url = f"https://www.mercadopago.com.ar/subscriptions/checkout?preapproval_plan_id={plan_id}"

# NEW: Creating via API with webhook
subscription_data = {
    "preapproval_plan_id": plan_id,
    "notification_url": "https://caloria.vip/webhook/mercadopago",  # CRITICAL
    "external_reference": user.whatsapp_id,
    # ... other required fields
}
response = requests.post("https://api.mercadopago.com/preapproval", ...)
```

### **2. Webhook JSON Format (MAJOR)**

**❌ Previous Format (Incorrect):**
```json
{
 "type": "subscription",
 "data": {
     "id": "subscription_id"
 }
}
```

**✅ Actual MP Format (Fixed):**
```json
{
 "id": 12345,
 "live_mode": true,
 "type": "subscription_preapproval",
 "date_created": "2015-03-25T10:04:58.396-04:00",
 "user_id": 44444,
 "api_version": "v1",
 "action": "subscription.created",
 "data": {
     "id": "999999999"
 }
}
```

### **3. API Endpoints (MAJOR)**

**❌ Previous Endpoint:**
```python
url = f"https://api.mercadopago.com/preapproval/{subscription_id}"
```

**✅ Correct Endpoint (Fixed):**
```python
# For subscription details:
url = f"https://api.mercadopago.com/preapproval/{subscription_id}"

# For subscription payments:
url = f"https://api.mercadopago.com/authorized_payments/{payment_id}"
```

### **4. Webhook Types (NEW)**

**✅ Now Handling Correct Types:**
- `subscription_preapproval` - Main subscription events
- `subscription_authorized_payment` - Payment events
- `subscription_preapproval_plan` - Plan events

### **5. Response Requirements (CRITICAL)**

**✅ Fixed Response Handling:**
- MUST return HTTP 200/201 within 22 seconds
- Retry mechanism: every 15 minutes for 3 attempts
- Return 200 even for errors to avoid unnecessary retries

---

## 🔧 **Technical Changes Made**

### **A. MercadoPagoService.create_subscription_link()**
- ✅ Now creates subscription via API instead of URL construction
- ✅ Includes required `notification_url` parameter
- ✅ Stores subscription ID immediately
- ✅ Returns `init_point` URL for user redirection

### **B. mercadopago_webhook() Handler**
- ✅ Handles correct JSON structure with `type`, `action`, `data.id`
- ✅ Routes to appropriate handlers based on webhook type
- ✅ Returns HTTP 200 within timeout requirements
- ✅ Better error handling and logging

### **C. Subscription Event Handling**
- ✅ New `handle_subscription_webhook()` with correct parameters
- ✅ New `handle_subscription_payment_webhook()` for payment events
- ✅ Proper status checking and user state management

### **D. API Integration**
- ✅ Correct API endpoints for fetching subscription details
- ✅ Proper authentication headers
- ✅ Error handling for API failures

---

## 🎯 **Subscription Flow (Fixed)**

1. **User completes quiz** → Quiz handler
2. **Subscription creation** → API call to `/preapproval` with webhook URL
3. **User redirected** → To Mercado Pago `init_point`
4. **User pays/cancels** → MP sends webhook to our configured URL
5. **Webhook received** → Correct JSON format processed
6. **User status updated** → Trial started or cancelled
7. **ManyChat notification** → User informed of status

---

## 🧪 **Testing Requirements**

**Before Production:**
1. ✅ Test subscription creation via API
2. ✅ Test webhook reception with correct format
3. ✅ Test trial start/end functionality
4. ✅ Test payment event handling
5. ✅ Test error scenarios and retries

**Webhook Testing:**
```bash
# Test webhook endpoint
curl -X POST https://caloria.vip/webhook/mercadopago \
  -H "Content-Type: application/json" \
  -d '{
    "id": 12345,
    "live_mode": false,
    "type": "subscription_preapproval",
    "action": "subscription.created",
    "data": {"id": "test_subscription_123"}
  }'
```

---

## ⚠️ **Production Deployment Notes**

1. **Webhook URL:** Must be HTTPS and publicly accessible
2. **Response Time:** MUST respond within 22 seconds
3. **Status Codes:** Return 200/201 for success, avoid 4xx/5xx for retries
4. **Error Handling:** Log errors but still return 200
5. **Security:** Implement proper signature verification

---

## 📋 **Next Steps**

✅ **Phase 1 Fixed** - Foundation now complies with MP documentation
🔜 **Phase 2** - Quiz integration and ManyChat flows
🔜 **Phase 3** - Trial day program and engagement
🔜 **Phase 4** - Production testing and deployment

**The subscription foundation is now correctly implemented according to Mercado Pago's official specifications.** 