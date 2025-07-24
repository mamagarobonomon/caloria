# 🚀 Caloria Complete Deployment Guide

**Single source of truth for deploying Caloria WhatsApp nutrition bot**

---

## 📋 **Prerequisites**

- ✅ King Servers VPS account (162.248.225.106)
- ✅ Domain `caloria.vip` registered at GoDaddy
- ✅ GitHub account with repository: `mamagarobonomon/caloria`
- ✅ SSH client (Terminal on Mac/Linux, PuTTY on Windows)

---

## 🎯 **Deployment Overview**

1. **Connect to VPS** (SSH setup)
2. **Deploy application** (safe, multi-project compatible)
3. **Configure production** (secure environment)
4. **Setup SSL certificate** (HTTPS)
5. **Test and verify** (ensure everything works)

---

## 🔐 **Step 1: SSH Connection Setup**

### **Server Details**
```
Server IP: 162.248.225.106
Username: vps
Port: 22 (default)
```

### **Method A: Password Connection (Quick)**
```bash
ssh vps@162.248.225.106
# Enter password when prompted
```

### **Method B: SSH Keys (Recommended for frequent access)**
```bash
# 1. Generate SSH key (on your local machine)
ssh-keygen -t ed25519 -C "caloria-deployment" -f ~/.ssh/caloria_key -N ""

# 2. Copy key to server (enter password one last time)
ssh-copy-id -i ~/.ssh/caloria_key.pub vps@162.248.225.106

# 3. Create SSH config for easy access
cat >> ~/.ssh/config << 'EOF'
Host caloria
    HostName 162.248.225.106
    User vps
    IdentityFile ~/.ssh/caloria_key
    ServerAliveInterval 60
EOF

# 4. Now connect easily with: ssh caloria
```

---

## 🛡️ **Step 2: Safe Application Deployment**

**This deployment is multi-project safe and won't interfere with existing applications.**

### **2a. Download and Run Deployment Script**
```bash
# Connect to server
ssh vps@162.248.225.106

# Download safe deployment script
wget https://raw.githubusercontent.com/mamagarobonomon/caloria/main/safe_deploy_script.sh
chmod +x safe_deploy_script.sh

# Run deployment (creates isolated environment)
sudo ./safe_deploy_script.sh
```

### **2b. What This Creates**
- **Directory**: `/var/www/caloria` (isolated)
- **User**: `caloria` (dedicated application user)
- **Database**: `caloria_vip_db` (unique name)
- **Port**: `5001` (internal, won't conflict)
- **Nginx**: `caloria-vip` (domain-specific config)
- **Supervisor**: `caloria-vip` (unique service name)

---

## ⚙️ **Step 3: Production Configuration**

### **3a. Setup Secure Environment**
```bash
# Download and run production setup
wget https://raw.githubusercontent.com/mamagarobonomon/caloria/main/setup_production.sh
chmod +x setup_production.sh
sudo ./setup_production.sh
```

### **3b. Generated Configuration**
The script will generate:
- **Secret Key**: Random 32-character key
- **Database Password**: Secure random password
- **Admin Password**: `CaloriaAdmin2025!`

**⚠️ Save these credentials securely!**

### **3c. Install Missing Dependencies**
```bash
# Install PostgreSQL adapter (required)
sudo -u caloria bash -c 'cd /var/www/caloria && source venv/bin/activate && pip install psycopg2-binary'
```

---

## 🚀 **Step 4: Start Application**

### **4a. Start Gunicorn Server**
```bash
# Start the application
sudo -u caloria bash -c 'cd /var/www/caloria && mkdir -p logs && source venv/bin/activate && nohup gunicorn --bind 127.0.0.1:5001 --workers 2 --timeout 300 app:app > logs/gunicorn.log 2>&1 &'

# Test if running
curl -I http://127.0.0.1:5001
# Should return: HTTP/1.1 200 OK
```

### **4b. Verify Services**
```bash
# Check if application is running
ps aux | grep gunicorn

# Check nginx status
sudo systemctl status nginx

# Test website (HTTP)
curl -I http://caloria.vip
```

---

## 🔒 **Step 5: SSL Certificate Setup**

### **5a. Install Let's Encrypt Certificate**
```bash
# Install SSL certificate for caloria.vip
sudo certbot --nginx -d caloria.vip -d www.caloria.vip --non-interactive --agree-tos --email sergey@caloria.vip
```

### **5b. Verify HTTPS**
```bash
# Test HTTPS connection
curl -I https://caloria.vip
# Should return: HTTP/1.1 200 OK with SSL headers
```

---

## ✅ **Step 6: Final Verification**

### **6a. Test Main Features**
- **Website**: https://caloria.vip
- **Language Switch**: ES/EN toggle in header
- **Admin Panel**: https://caloria.vip/admin
- **Login**: `admin` / `CaloriaAdmin2025!`

### **6b. Verify Spanish Translation**
```bash
# Check for Spanish content
curl -s https://caloria.vip | grep -i "asistente\|nutrición"
# Should show Spanish text
```

---

## 🔄 **Updates and Maintenance**

### **Update Deployed Code**
```bash
# For code updates (after pushing to GitHub)
ssh vps@162.248.225.106 "cd /var/www/caloria && sudo -u caloria git pull origin main && sudo -u caloria bash -c 'source venv/bin/activate && pip install -r requirements.txt' && sudo -u caloria pkill -f gunicorn; sudo -u caloria bash -c 'cd /var/www/caloria && source venv/bin/activate && nohup gunicorn --bind 127.0.0.1:5001 --workers 2 --timeout 300 app:app > logs/gunicorn.log 2>&1 &'"
```

### **Check Logs**
```bash
# Application logs
sudo tail -f /var/www/caloria/logs/gunicorn.log

# Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### **Service Management**
```bash
# Check if app is running
ps aux | grep gunicorn

# Restart nginx (if needed)
sudo systemctl restart nginx

# Check SSL certificate status
sudo certbot certificates
```

---

## 🆘 **Troubleshooting**

### **Application Won't Start**
```bash
# Check for errors
sudo -u caloria bash -c 'cd /var/www/caloria && source venv/bin/activate && python app.py'
# Look for error messages
```

### **Database Connection Issues**
```bash
# Test database connection
sudo -u postgres psql -d caloria_vip_db -c "SELECT 1;"
```

### **SSL Certificate Issues**
```bash
# Check certificate status
sudo certbot certificates

# Renew if needed
sudo certbot renew --dry-run
```

### **Port Already in Use**
```bash
# Kill existing gunicorn processes
sudo pkill -f gunicorn

# Check what's using port 5001
sudo lsof -i :5001
```

---

## 📊 **Technical Specifications**

| Component | Configuration |
|-----------|--------------|
| **Server** | King Servers VPS (162.248.225.106) |
| **OS** | Ubuntu 22.04 LTS |
| **Domain** | caloria.vip (GoDaddy DNS) |
| **SSL** | Let's Encrypt (auto-renewal) |
| **Web Server** | Nginx (reverse proxy) |
| **App Server** | Gunicorn (port 5001) |
| **Database** | PostgreSQL (caloria_vip_db) |
| **Python** | 3.12 with virtual environment |
| **Framework** | Flask with Spanish/English support |

---

## 🎉 **Success! Your Deployment is Complete**

Your bilingual WhatsApp nutrition bot is now live at:
- **🌐 Website**: https://caloria.vip
- **🔧 Admin**: https://caloria.vip/admin (admin/admin123)
- **🗄️ Database**: PostgreSQL with daily backups
- **🔍 Health**: https://caloria.vip/health/database
- **🇪🇸 Default**: Spanish language
- **🇺🇸 Switch**: English toggle available
- **🔒 Secure**: SSL certificate installed
- **📱 Ready**: WhatsApp bot functionality active

---

## 📞 **Support**

- **Repository**: https://github.com/mamagarobonomon/caloria
- **King Servers**: Support via control panel
- **SSL Issues**: Let's Encrypt documentation
- **Domain**: GoDaddy DNS management

**🎯 This single guide replaces all other deployment documents!** 