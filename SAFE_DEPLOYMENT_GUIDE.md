# 🛡️ Safe Caloria Deployment (UPDATED)

**⚠️ This guide has been superseded by the consolidated deployment documentation.**

---

## 📖 **Use the Updated Guide**

**👉 See: [`DEPLOYMENT_CONSOLIDATED.md`](./DEPLOYMENT_CONSOLIDATED.md)**

The new consolidated guide includes:
- ✅ **Safe deployment** (multi-project compatible)
- ✅ **Clear SSH setup** (no conflicting instructions)
- ✅ **Step-by-step process** (tested and validated)
- ✅ **Troubleshooting** (comprehensive error resolution)
- ✅ **Current information** (reflects live deployment)

---

## 🚀 **Quick Reference**

### **Server Details**
- **IP**: 162.248.225.106
- **User**: vps
- **Domain**: caloria.vip

### **Safe Deployment Features**
- **Isolated Environment**: Uses port 5001 (won't conflict)
- **Unique Database**: caloria_vip_db
- **Dedicated User**: caloria application user
- **Domain-Specific Config**: caloria-vip nginx config
- **No Interference**: Safe for multi-project servers

### **Quick Commands**
```bash
# Connect to server
ssh vps@162.248.225.106

# Deploy application (full guide in DEPLOYMENT_CONSOLIDATED.md)
wget https://raw.githubusercontent.com/mamagarobonomon/caloria/main/safe_deploy_script.sh
chmod +x safe_deploy_script.sh
sudo ./safe_deploy_script.sh

# Setup production environment
wget https://raw.githubusercontent.com/mamagarobonomon/caloria/main/setup_production.sh
chmod +x setup_production.sh
sudo ./setup_production.sh
```

---

## ⚠️ **Migration Notice**

This file previously contained detailed deployment instructions that have been:
- ✅ **Consolidated** into a single, comprehensive guide
- ✅ **Updated** with current working configuration
- ✅ **Enhanced** with troubleshooting and maintenance sections
- ✅ **Tested** against the live deployment

**Please use [`DEPLOYMENT_CONSOLIDATED.md`](./DEPLOYMENT_CONSOLIDATED.md) for all deployment needs.**

---

## 🎯 **Current Status**

- **✅ Live Website**: https://caloria.vip
- **✅ Spanish/English**: Bilingual with language switcher
- **✅ SSL Secured**: HTTPS with auto-renewal
- **✅ Admin Panel**: https://caloria.vip/admin
- **✅ Food Images**: Real photos in WhatsApp chat demo

This deployment guide will be maintained for reference but detailed instructions are now in the consolidated guide. 