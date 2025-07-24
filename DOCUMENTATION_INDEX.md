# 📚 **Caloria Project Documentation Index**

**Complete reference to all documentation and important files**

---

## 🔗 **Quick Navigation**

| Document | Purpose | Status |
|----------|---------|--------|
| [📘 Mercado Pago Integration Guide](./MERCADOPAGO_INTEGRATION_GUIDE.md) | **MAIN REFERENCE** - Complete MP integration details | ✅ Current |
| [🚨 Mercado Pago Webhook Fixes](./MERCADOPAGO_WEBHOOK_FIXES.md) | Critical fixes based on MP documentation | ✅ Applied |
| [🌐 Google Cloud Integration Guide](./GOOGLE_CLOUD_GUIDE.md) | **CONSOLIDATED** - Setup & migration guide | ✅ Current |
| ~~Pre-Phase 2 Checklist~~ | ~~Tasks before Phase 2~~ | ✅ **COMPLETED & REMOVED** |
| [📖 Project README](./README.md) | General project overview and setup | ✅ Current |
| [🚀 Deployment Guide](./DEPLOYMENT_CONSOLIDATED.md) | Production deployment instructions | ✅ Current |

---

## 🛠️ **Setup & Installation Scripts**

| Script | Purpose | Usage |
|--------|---------|-------|
| [`migrations/setup_mercadopago_env.py`](./migrations/setup_mercadopago_env.py) | Configure MP credentials and environment | `cd migrations && python setup_mercadopago_env.py` |
| [`migrations/migrate_subscription_db.py`](./migrations/migrate_subscription_db.py) | Database migration for subscription tables | `cd migrations && python migrate_subscription_db.py` |
| [`migrations/migrate_admin_dashboard.py`](./migrations/migrate_admin_dashboard.py) | Admin dashboard database migration | `cd migrations && python migrate_admin_dashboard.py` |
| [`test_subscription_flow.py`](./test_subscription_flow.py) | Test basic subscription functionality | `python test_subscription_flow.py` |
| [`test_corrected_webhook.py`](./test_corrected_webhook.py) | Test corrected webhook implementation | `python test_corrected_webhook.py` |

---

## 📋 **Core Application Files**

| File | Purpose | Key Features |
|------|---------|--------------|
| [`app.py`](./app.py) | Main Flask application | Webhook handling, subscription API, user management |
| [`requirements.txt`](./requirements.txt) | Python dependencies | All required packages |
| [`templates/`](./templates/) | HTML templates | Success/cancel pages, admin interface |

---

## 🎯 **Mercado Pago Integration Summary**

### **Essential Information**
- **Plan ID**: `2c938084939f84900193a80bf21f01c8`
- **Price**: $4999.00 ARS (~$5.00 USD)
- **Trial**: 1 day free
- **Country**: Argentina
- **Currency**: ARS

### **Key Endpoints**
- **Webhook**: `https://caloria.vip/webhook/mercadopago`
- **Create Subscription**: `https://caloria.vip/api/create-subscription`
- **Success Page**: `https://caloria.vip/subscription-success`
- **Cancel Page**: `https://caloria.vip/subscription-cancel`

### **Credentials** (see .env file)
```bash
MERCADO_PAGO_ACCESS_TOKEN=APP_USR-1172155843468668-072410-5f2e9d6af1e4d437c2086d88c529259e-1506756785
MERCADO_PAGO_PUBLIC_KEY=APP_USR-983a7fa3-1497-4ed6-9d0b-a6fc35f5b0dc
MERCADO_PAGO_PLAN_ID=2c938084939f84900193a80bf21f01c8
```

---

## 🔄 **Implementation Phases**

### **✅ Phase 1: Foundation (COMPLETED)**
- Database models for subscriptions
- Mercado Pago API integration
- Webhook handling (corrected format)
- Basic subscription flow
- Testing scripts

### **✅ Phase 1.5: Foundation Deployment (COMPLETE)**
- Environment setup and configuration ✅
- Database migration application ✅
- Production deployment of Phase 1 ✅
- Basic functionality verification ✅
- ManyChat integration testing ✅

### **🎉 Phase 2A: Quiz & Subscription Integration (COMPLETE)**
- Quiz flow modified with subscription mentions at Q10-11 ✅
- Payment flow integrated with Mercado Pago ✅
- Premium trial user experience implemented ✅
- Complete Telegram testing infrastructure ✅
- Analytics and conversion tracking ✅
- ManyChat flows ready for WhatsApp deployment ✅

### **🔜 Phase 2B: WhatsApp Deployment (WAITING FOR API APPROVAL)**
- **[🚀 WhatsApp Launch Preparation Plan](./WHATSAPP_LAUNCH_PREPARATION.md)** - **COMPLETE**
- **[📋 Complete ManyChat Quiz Flow](./MANYCHAT_QUIZ_FLOW_COMPLETE.md)** - **READY TO DEPLOY**
- **[📢 Marketing Materials & Content](./WHATSAPP_MARKETING_MATERIALS.md)** - **ALL CONTENT READY**
- **[📊 Launch Monitoring & Support](./WHATSAPP_LAUNCH_MONITORING.md)** - **MONITORING READY**
- Enable ManyChat WhatsApp flows (30 minutes when API approved)
- Production user testing and optimization

### **🔜 Phase 3: Trial Day Program**
- 24-hour intensive engagement
- Trial activity tracking
- Conversion optimization
- Progress analytics

### **🔜 Phase 4: Re-engagement**
- Cancellation handling
- 7-day follow-up campaigns
- Long-term nurture sequences
- Conversion analytics

---

## 🧪 **Testing Workflow**

### **Local Testing**
```bash
# 1. Environment setup
cd migrations && python setup_mercadopago_env.py

# 2. Database preparation
cd migrations && python migrate_subscription_db.py

# 3. Basic functionality test
python test_subscription_flow.py

# 4. Webhook implementation test
python test_corrected_webhook.py

# 5. Start application
python app.py
```

### **Production Testing**
```bash
# 1. Deploy to server
scp -r . vps@162.248.225.106:/var/www/caloria/

# 2. Run setup on server
ssh vps@162.248.225.106
cd /var/www/caloria/migrations
python setup_mercadopago_env.py
python migrate_subscription_db.py

# 3. Test and restart
python test_corrected_webhook.py
sudo systemctl restart caloria
```

---

## 🔧 **Troubleshooting Guide**

### **Common Issues**
1. **Webhook not received** → Check HTTPS accessibility
2. **Subscription creation fails** → Verify MP credentials
3. **Trial not starting** → Check database user status
4. **Payment not processing** → Monitor webhook logs

### **Debug Commands**
```bash
# Check webhook endpoint
curl -I https://caloria.vip/webhook/mercadopago

# Test MP API connectivity
curl -H "Authorization: Bearer $TOKEN" https://api.mercadopago.com/users/me

# Check application logs
tail -f /var/www/caloria/logs/gunicorn.log

# Check database state
python -c "from app import app, User; print(User.query.count())"
```

---

## 📊 **Monitoring & Analytics**

### **Key Metrics to Track**
- Quiz completion rate
- Subscription conversion rate
- Trial-to-paid conversion
- Cancellation rate
- Re-engagement success

### **Log Locations**
- **Application**: `/var/www/caloria/logs/gunicorn.log`
- **Webhook**: Filter with `grep "webhook"`
- **Subscriptions**: Filter with `grep -i "subscription"`

---

## 📞 **Support & References**

### **External Documentation**
- [Mercado Pago Webhooks](https://www.mercadopago.com.ar/developers/es/docs/subscriptions/additional-content/your-integrations/notifications/webhooks)
- [MP Preapproval API](https://www.mercadopago.com.ar/developers/es/reference/subscriptions/_preapproval/post)

### **Production Environment**
- **Server**: `162.248.225.106` (King Servers VPS)
- **Domain**: `caloria.vip`
- **Admin Panel**: `https://caloria.vip/admin`

### **Repository**
- **GitHub**: `https://github.com/mamagarobonomon/caloria`
- **Branch**: `main`

---

## 🚀 **Quick Start Commands**

```bash
# Complete setup from scratch
git clone https://github.com/mamagarobonomon/caloria.git
cd caloria
pip install -r requirements.txt
cd migrations && python setup_mercadopago_env.py
cd migrations && python migrate_subscription_db.py
cd .. && python test_corrected_webhook.py
python app.py
```

---

**📝 Last Updated**: December 2024  
**📋 Current Phase**: Phase 1 Complete - Ready for Phase 2  
**🔄 Next Milestone**: Quiz integration with subscription flow

**✅ For any Mercado Pago integration questions, refer to the [📘 Mercado Pago Integration Guide](./MERCADOPAGO_INTEGRATION_GUIDE.md) first.** 