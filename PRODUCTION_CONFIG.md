# 🔐 Production Configuration for caloria.vip

**Keep this file secure and don't share it publicly!**

## 🎯 Generated Configuration Values

### **Secret Key (Generated)**
```
SECRET_KEY=7J9b_3OdefZaC10a1B7Zi137WiC5yzc7l_UsBXo7zAI
```

### **API Keys (Your Values)**
```
SPOONACULAR_API_KEY=3e0eac47470049d6845406463f223518
MANYCHAT_API_TOKEN=YOUR_MANYCHAT_TOKEN_HERE
```

### **Database Configuration**
```
DATABASE_USER=caloria_user
DATABASE_NAME=caloria_db
DATABASE_PASSWORD=WILL_BE_GENERATED_ON_SERVER
```

### **Admin Configuration**
```
DEFAULT_ADMIN_USERNAME=admin
DEFAULT_ADMIN_PASSWORD=CHANGE_THIS_ON_FIRST_LOGIN
```

---

## 📋 Configuration Steps Checklist

### **Step 1: GitHub Repository**
- [ ] Created repository at github.com
- [ ] Repository URL: `https://github.com/YOUR-USERNAME/caloria.git`
- [ ] Code pushed to main branch

### **Step 2: King Servers VPS**
- [ ] Ordered VPS with 4GB RAM, Ubuntu 22.04
- [ ] Server IP: `___________________`
- [ ] Root password: `_______________`

### **Step 3: GoDaddy DNS**
- [ ] Added A record: @ → SERVER_IP
- [ ] Added A record: www → SERVER_IP
- [ ] DNS propagation started

### **Step 4: Production Environment**
```bash
# Complete .env file for production:
SECRET_KEY=7J9b_3OdefZaC10a1B7Zi137WiC5yzc7l_UsBXo7zAI
FLASK_ENV=production
DATABASE_URL=postgresql://caloria_user:SECURE_PASSWORD@localhost/caloria_db
SPOONACULAR_API_KEY=3e0eac47470049d6845406463f223518
MANYCHAT_API_TOKEN=your-manychat-token-here
DEFAULT_ADMIN_USERNAME=admin
DEFAULT_ADMIN_PASSWORD=your-secure-admin-password
UPLOAD_FOLDER=/var/www/caloria/uploads
MAX_CONTENT_LENGTH=16777216
LOG_LEVEL=INFO
```

### **Step 5: Deployment Commands**
```bash
# On your King Servers VPS:
ssh root@YOUR_SERVER_IP
wget https://raw.githubusercontent.com/YOUR-USERNAME/caloria/main/deploy_script.sh
chmod +x deploy_script.sh
sudo ./deploy_script.sh
```

---

## 🔗 Quick Links

- **Website**: https://caloria.vip
- **Admin Panel**: https://caloria.vip/admin  
- **King Servers**: https://kingservers.com/
- **GoDaddy DNS**: https://dcc.godaddy.com/

---

## 📞 Important Contacts

- **King Servers Support**: sales@kingservers.com, 8 (800) 222 32 56
- **GitHub Repository**: https://github.com/YOUR-USERNAME/caloria

**Status**: 📝 Configuration prepared, ready for deployment! 