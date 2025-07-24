# 📘 **Mercado Pago Integration Guide - Caloria Project**

**Complete reference for Mercado Pago subscription integration with WhatsApp chatbot**

---

## 📋 **Table of Contents**

1. [Project Overview](#project-overview)
2. [Account & Credentials](#account--credentials)
3. [Subscription Plan Details](#subscription-plan-details)
4. [API Integration](#api-integration)
5. [Webhook Implementation](#webhook-implementation)
6. [Database Schema](#database-schema)
7. [User Flow](#user-flow)
8. [Configuration](#configuration)
9. [Testing](#testing)
10. [Troubleshooting](#troubleshooting)
11. [Production Deployment](#production-deployment)

---

## 🎯 **Project Overview**

### **Business Logic**
- **Product**: Caloria WhatsApp nutrition tracking chatbot
- **Monetization**: Subscription-based premium features
- **Target Market**: Argentina (Spanish-speaking users)
- **Trial Strategy**: 1-day free trial → Monthly subscription
- **Payment Provider**: Mercado Pago (popular in Argentina)

### **Subscription Strategy**
- **Free Trial**: 24 hours with full premium access
- **Monthly Fee**: $4999.00 ARS (~$5.00 USD)
- **Trial Behavior**: Immediate cancellation = no access
- **Re-engagement**: 7-day follow-up for cancelled users
- **Premium Features**: Unlimited food analysis, meal planning, advanced recommendations

---

## 🔑 **Account & Credentials**

### **Mercado Pago Account Details**
```bash
# Production Credentials (Argentina)
MERCADO_PAGO_ACCESS_TOKEN=APP_USR-1172155843468668-072410-5f2e9d6af1e4d437c2086d88c529259e-1506756785
MERCADO_PAGO_PUBLIC_KEY=APP_USR-983a7fa3-1497-4ed6-9d0b-a6fc35f5b0dc
MERCADO_PAGO_PLAN_ID=2c938084939f84900193a80bf21f01c8
MERCADO_PAGO_WEBHOOK_SECRET=caloria-webhook-secret-2024

# Configuration
SUBSCRIPTION_TRIAL_DAYS=1
SUBSCRIPTION_PRICE_ARS=499900.0  # $4999.00 ARS (~$5 USD)
```

### **Account Information**
- **Country**: Argentina
- **Currency**: ARS (Argentine Peso)
- **Plan Type**: Subscription with 1-day trial
- **Integration Type**: Preapproval (recurring payments)

---

## 📋 **Subscription Plan Details**

### **Plan Configuration**
```json
{
  "id": "2c938084939f84900193a80bf21f01c8",
  "reason": "Caloria Premium - Plan Nutricional Personalizado",
  "frequency": 1,
  "frequency_type": "months",
  "transaction_amount": 4999.00,
  "currency_id": "ARS",
  "trial_period": 1,
  "trial_period_type": "days",
  "auto_recurring": true
}
```

### **Features Included**
- ✅ **Trial**: 24-hour full access
- ✅ **Premium**: Unlimited food analysis
- ✅ **Advanced**: Meal planning and recommendations
- ✅ **Support**: Priority customer support
- ✅ **Analytics**: Detailed progress tracking

---

## 🔌 **API Integration**

### **Base URLs**
```bash
# Production API
API_BASE_URL=https://api.mercadopago.com

# Webhook URL (must be HTTPS)
WEBHOOK_URL=https://caloria.vip/webhook/mercadopago
```

### **Key Endpoints**

#### **1. Create Subscription**
```http
POST https://api.mercadopago.com/preapproval
Authorization: Bearer {ACCESS_TOKEN}
Content-Type: application/json

{
  "preapproval_plan_id": "2c938084939f84900193a80bf21f01c8",
  "payer_email": "{whatsapp_id}@caloria.app",
  "external_reference": "{whatsapp_id}",
  "notification_url": "https://caloria.vip/webhook/mercadopago",
  "back_url": "https://caloria.vip/subscription-success?user={user_id}",
  "auto_recurring": {
    "frequency": 1,
    "frequency_type": "months",
    "transaction_amount": 4999.00,
    "currency_id": "ARS"
  }
}
```

**Response:**
```json
{
  "id": "subscription_id_123",
  "init_point": "https://www.mercadopago.com.ar/subscriptions/checkout?preapproval_id=...",
  "status": "pending"
}
```

#### **2. Get Subscription Details**
```http
GET https://api.mercadopago.com/preapproval/{subscription_id}
Authorization: Bearer {ACCESS_TOKEN}
```

#### **3. Get Payment Details**
```http
GET https://api.mercadopago.com/authorized_payments/{payment_id}
Authorization: Bearer {ACCESS_TOKEN}
```

#### **4. User Info (Test Connection)**
```http
GET https://api.mercadopago.com/users/me
Authorization: Bearer {ACCESS_TOKEN}
```

---

## 🔗 **Webhook Implementation**

### **Critical Requirements** (from MP Documentation)
- ✅ **Configuration**: Must set `notification_url` during subscription creation
- ✅ **Response Time**: Must respond within 22 seconds
- ✅ **Status Code**: Always return HTTP 200/201 (even for errors)
- ✅ **Retry Logic**: MP retries every 15 minutes for failed deliveries

### **Webhook JSON Format**

**Mercado Pago Sends:**
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
    "id": "subscription_id_999999999"
  }
}
```

### **Webhook Types & Actions**

| Type | Action | Description |
|------|--------|-------------|
| `subscription_preapproval` | `subscription.created` | Subscription authorized |
| `subscription_preapproval` | `subscription.cancelled` | Subscription cancelled |
| `subscription_preapproval` | `subscription.updated` | Subscription modified |
| `subscription_authorized_payment` | `payment.created` | Monthly payment processed |
| `subscription_authorized_payment` | `payment.updated` | Payment status changed |

### **Webhook Handler Code**
```python
@app.route('/webhook/mercadopago', methods=['POST'])
def mercadopago_webhook():
    try:
        data = request.get_json()
        
        # Extract webhook information
        webhook_type = data.get('type')
        action = data.get('action', '')
        resource_id = data.get('data', {}).get('id')
        
        # Route to appropriate handler
        if webhook_type == 'subscription_preapproval':
            result = handle_subscription_webhook(resource_id, action)
        elif webhook_type == 'subscription_authorized_payment':
            result = handle_subscription_payment_webhook(resource_id, action)
        
        # CRITICAL: Always return 200 within 22 seconds
        return jsonify({'status': 'ok'}), 200
        
    except Exception as e:
        app.logger.error(f"Webhook error: {str(e)}")
        return jsonify({'error': 'processed'}), 200  # Still return 200
```

---

## 🗄️ **Database Schema**

### **User Model Extensions**
```python
class User(db.Model):
    # ... existing fields ...
    
    # Subscription fields
    subscription_tier = db.Column(db.String(20), default='trial_pending')
    subscription_status = db.Column(db.String(20), default='inactive')
    trial_start_time = db.Column(db.DateTime, nullable=True)
    trial_end_time = db.Column(db.DateTime, nullable=True)
    mercadopago_subscription_id = db.Column(db.String(100), nullable=True)
    cancellation_reason = db.Column(db.String(200), nullable=True)
    reengagement_scheduled = db.Column(db.DateTime, nullable=True)
    last_payment_date = db.Column(db.DateTime, nullable=True)
```

### **Subscription Model**
```python
class Subscription(db.Model):
    id = db.Column(db.String(50), primary_key=True)  # MP subscription ID
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    plan_id = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(3), default='ARS')
    next_payment_date = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    cancelled_at = db.Column(db.DateTime, nullable=True)
```

### **Payment Transaction Model**
```python
class PaymentTransaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    subscription_id = db.Column(db.String(50), nullable=True)
    mp_payment_id = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), nullable=False)
    transaction_type = db.Column(db.String(20), nullable=False)
    payment_date = db.Column(db.DateTime, default=datetime.utcnow)
```

### **Subscription Status Flow**
```
trial_pending → trial_active → active (paid)
              ↘ cancelled
              ↘ expired
```

---

## 👤 **User Flow**

### **Complete User Journey**
```mermaid
graph TD
    A[User starts quiz] --> B[Question 10-11: Subscription mention]
    B --> C[Quiz completion]
    C --> D[Payment page with MP link]
    D --> E{User action}
    E -->|Pays| F[MP processes payment]
    E -->|Cancels| G[Cancellation page]
    F --> H[Webhook: subscription.created]
    H --> I[Trial starts - 24 hours]
    I --> J{Trial ends}
    J -->|Converts| K[Paid subscription]
    J -->|Cancels| L[Trial ends]
    G --> M[No access]
    L --> N[7-day re-engagement]
    M --> N
```

### **User States**
```python
SUBSCRIPTION_STATES = {
    'inactive': 'No subscription',
    'trial_pending': 'Payment initiated, waiting for confirmation',
    'trial_active': 'In 24-hour trial period',
    'active': 'Paid subscription active',
    'cancelled': 'Cancelled during trial',
    'expired': 'Trial expired without payment'
}
```

---

## ⚙️ **Configuration**

### **Environment Variables**
```bash
# Flask Configuration
SECRET_KEY=your-production-secret-key
FLASK_ENV=production

# Database
DATABASE_URL=postgresql://user:password@localhost/caloria_db

# Mercado Pago
MERCADO_PAGO_ACCESS_TOKEN=APP_USR-1172155843468668-072410-5f2e9d6af1e4d437c2086d88c529259e-1506756785
MERCADO_PAGO_PUBLIC_KEY=APP_USR-983a7fa3-1497-4ed6-9d0b-a6fc35f5b0dc
MERCADO_PAGO_PLAN_ID=2c938084939f84900193a80bf21f01c8
MERCADO_PAGO_WEBHOOK_SECRET=caloria-webhook-secret-2024

# Subscription Settings
SUBSCRIPTION_TRIAL_DAYS=1
SUBSCRIPTION_PRICE_ARS=2999.0

# External Services
MANYCHAT_API_TOKEN=your-manychat-token
SPOONACULAR_API_KEY=your-spoonacular-key
```

### **Server Configuration**
```nginx
# Nginx configuration for webhook endpoint
location /webhook/mercadopago {
    proxy_pass http://127.0.0.1:5001;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_read_timeout 25s;  # Slightly more than MP's 22s requirement
    proxy_connect_timeout 5s;
}
```

---

## 🧪 **Testing**

### **Test Webhooks Locally**
```bash
# 1. Start local server
python app.py

# 2. Test webhook endpoint
curl -X POST http://localhost:5000/webhook/mercadopago \
  -H "Content-Type: application/json" \
  -d '{
    "id": 12345,
    "live_mode": false,
    "type": "subscription_preapproval",
    "action": "subscription.created",
    "data": {"id": "test_subscription_123"}
  }'
```

### **Test Subscription Creation**
```bash
# Create test subscription
curl -X POST http://localhost:5000/api/create-subscription \
  -H "Content-Type: application/json" \
  -d '{
    "subscriber_id": "test_user_123",
    "plan_type": "premium"
  }'
```

### **Test Scripts**
```bash
# Environment setup
python setup_mercadopago_env.py

# Database migration
python migrate_subscription_db.py

# Basic functionality test
python test_subscription_flow.py

# Corrected webhook implementation test
python test_corrected_webhook.py
```

### **Production Testing Checklist**
- [ ] Webhook endpoint responds < 22 seconds
- [ ] Subscription creation via API works
- [ ] Trial start/end functionality
- [ ] Payment webhooks processed correctly
- [ ] Cancellation handling
- [ ] Re-engagement scheduling
- [ ] ManyChat message delivery

---

## 🔧 **Troubleshooting**

### **Common Issues**

#### **1. Webhook Not Received**
```bash
# Check webhook URL is accessible
curl -I https://caloria.vip/webhook/mercadopago

# Check server logs
tail -f /var/www/caloria/logs/gunicorn.log

# Verify webhook URL in subscription
curl -H "Authorization: Bearer $TOKEN" \
  https://api.mercadopago.com/preapproval/$SUBSCRIPTION_ID
```

#### **2. Subscription Creation Fails**
```python
# Common errors and solutions
ERRORS = {
    "400": "Invalid request - check required fields",
    "401": "Invalid access token",
    "403": "Insufficient permissions",
    "404": "Plan ID not found",
    "422": "Invalid plan configuration"
}
```

#### **3. Trial Not Starting**
```bash
# Check user status
python -c "
from app import app, User
with app.app_context():
    user = User.query.filter_by(whatsapp_id='USER_ID').first()
    print(f'Status: {user.subscription_status}')
    print(f'Trial active: {user.is_trial_active()}')
"
```

### **Debug Commands**
```bash
# Check MP API connectivity
curl -H "Authorization: Bearer $MERCADO_PAGO_ACCESS_TOKEN" \
  https://api.mercadopago.com/users/me

# Test webhook processing
python test_corrected_webhook.py

# Check database state
python -c "
from app import app, db, User, Subscription
with app.app_context():
    print(f'Users: {User.query.count()}')
    print(f'Subscriptions: {Subscription.query.count()}')
"
```

### **Log Analysis**
```bash
# Filter webhook logs
grep "webhook" /var/www/caloria/logs/gunicorn.log

# Filter MP API calls
grep "mercadopago" /var/www/caloria/logs/gunicorn.log

# Filter subscription events
grep -i "subscription\|trial" /var/www/caloria/logs/gunicorn.log
```

---

## 🚀 **Production Deployment**

### **Deployment Steps**
```bash
# 1. Deploy code
scp -r . vps@162.248.225.106:/var/www/caloria/

# 2. Set up environment
ssh vps@162.248.225.106
cd /var/www/caloria
python setup_mercadopago_env.py

# 3. Run database migration
python migrate_subscription_db.py

# 4. Test implementation
python test_corrected_webhook.py

# 5. Restart application
sudo -u caloria pkill -f gunicorn
sudo -u caloria bash -c 'cd /var/www/caloria && source venv/bin/activate && nohup gunicorn --bind 127.0.0.1:5001 --workers 2 --timeout 300 app:app > logs/gunicorn.log 2>&1 &'
```

### **Production Verification**
```bash
# 1. Test webhook endpoint
curl -I https://caloria.vip/webhook/mercadopago

# 2. Test subscription API
curl -X POST https://caloria.vip/api/create-subscription \
  -H "Content-Type: application/json" \
  -d '{"subscriber_id": "test_prod_user"}'

# 3. Check application status
curl -I https://caloria.vip/admin

# 4. Monitor logs
tail -f /var/www/caloria/logs/gunicorn.log
```

### **Monitoring Setup**
```bash
# Add to crontab for health checks
*/5 * * * * curl -f https://caloria.vip/health || echo "Site down" | mail admin@caloria.vip

# Log rotation
0 0 * * * logrotate /var/www/caloria/logs/gunicorn.log
```

---

## 📚 **References**

### **Official Documentation**
- [MP Subscriptions Webhooks](https://www.mercadopago.com.ar/developers/es/docs/subscriptions/additional-content/your-integrations/notifications/webhooks)
- [MP Preapproval API](https://www.mercadopago.com.ar/developers/es/reference/subscriptions/_preapproval/post)
- [MP Payment Notifications](https://www.mercadopago.com.ar/developers/es/docs/your-integrations/notifications)

### **Project Files**
- `app.py` - Main application with MP integration
- `MERCADOPAGO_WEBHOOK_FIXES.md` - Critical fixes documentation
- `setup_mercadopago_env.py` - Environment configuration script
- `test_corrected_webhook.py` - Testing script
- `migrate_subscription_db.py` - Database migration script

### **Support Contacts**
- **Mercado Pago Support**: [developers.mercadopago.com](https://developers.mercadopago.com)
- **Project Repository**: [GitHub/caloria](https://github.com/mamagarobonomon/caloria)
- **Production Server**: `162.248.225.106` (King Servers VPS)

---

**📝 Last Updated**: December 2024  
**📋 Version**: 1.0 (Phase 1 Complete)  
**🔄 Next Review**: Before Phase 2 implementation

---

## 📊 **Quick Reference Card**

```bash
# Essential Commands
python setup_mercadopago_env.py     # Setup environment
python migrate_subscription_db.py   # Database migration
python test_corrected_webhook.py    # Test webhooks
python app.py                       # Start application

# Key URLs
https://caloria.vip/webhook/mercadopago          # Webhook endpoint
https://caloria.vip/api/create-subscription     # Create subscription
https://caloria.vip/subscription-success        # Success page
https://caloria.vip/subscription-cancel         # Cancel page

# Important Values
Plan ID: 2c938084939f84900193a80bf21f01c8
Price: $29.99 ARS
Trial: 1 day
Currency: ARS
```

**✅ This document contains all critical information for Mercado Pago integration and should be referenced for any future work on the subscription system.** 