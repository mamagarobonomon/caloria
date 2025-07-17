# 🚀 Caloria Deployment Guide for King Servers

Complete step-by-step guide to deploy your Caloria WhatsApp bot on King Servers VPS with domain `caloria.vip`.

## 📋 Prerequisites

- [x] King Servers VPS account
- [x] Domain `caloria.vip` registered at GoDaddy  
- [x] GitHub account
- [x] SSH client (Terminal on Mac/Linux, PuTTY on Windows)

## 🎯 Deployment Overview

1. **Push code to GitHub**
2. **Set up King Servers VPS**
3. **Configure DNS at GoDaddy**
4. **Deploy application**
5. **Set up SSL certificate**

---

## Step 1: Push Code to GitHub 🐙

### Create GitHub Repository

1. Go to [GitHub.com](https://github.com) and create new repository:
   - **Repository name**: `caloria`
   - **Description**: `WhatsApp Calorie Tracker Bot`
   - **Visibility**: Public or Private
   - **Don't** initialize with README (we already have files)

2. Copy the repository URL (example: `https://github.com/YOUR-USERNAME/caloria.git`)

### Push Your Code

```bash
# In your local Caloria directory
git remote add origin https://github.com/YOUR-USERNAME/caloria.git
git branch -M main
git push -u origin main
```

---

## Step 2: Set Up King Servers VPS 🖥️

### Order VPS

1. **Login to King Servers** control panel
2. **Order VPS/VDS** with these **recommended specs**:
   ```
   🔧 Recommended Configuration:
   • CPU: 2 vCores
   • RAM: 4GB
   • Storage: 40GB SSD
   • OS: Ubuntu 22.04 LTS
   • Location: Choose closest to your users
   • Price: ~$10-15/month
   ```

3. **Note down your server details:**
   - IP Address: `XXX.XXX.XXX.XXX`
   - SSH Port: `22` (default)
   - Root Password: `provided by King Servers`

### Initial Connection

```bash
# Connect to your VPS via SSH
ssh root@YOUR_SERVER_IP

# Update the deployment script with your GitHub URL
# Download our deployment script
wget https://raw.githubusercontent.com/YOUR-USERNAME/caloria/main/deploy_script.sh
chmod +x deploy_script.sh
```

---

## Step 3: Configure DNS at GoDaddy 🌐

### Point Domain to King Servers

1. **Login to GoDaddy** → **My Products** → **Domains** → `caloria.vip` → **DNS**

2. **Delete existing A records** for `@` and `www`

3. **Add new A records:**
   ```
   Type: A
   Name: @
   Value: YOUR_KING_SERVERS_IP
   TTL: 1 Hour
   
   Type: A
   Name: www
   Value: YOUR_KING_SERVERS_IP
   TTL: 1 Hour
   ```

4. **Save changes** (DNS propagation takes 1-24 hours, usually within 1 hour)

---

## Step 4: Deploy Application 🚀

### Run Deployment Script

On your King Servers VPS:

```bash
# Edit the deployment script to use your GitHub repository
nano deploy_script.sh

# Change this line:
# git clone https://github.com/YOUR-USERNAME/caloria.git .
# To your actual GitHub URL

# Run the deployment script
sudo ./deploy_script.sh
```

### Manual Configuration Steps

```bash
# 1. Generate secure SECRET_KEY
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# 2. Update database password
sudo -u postgres psql
ALTER USER caloria_user PASSWORD 'YOUR_NEW_SECURE_PASSWORD';
\q

# 3. Update environment file
sudo -u caloria nano /var/www/caloria/.env
# Update these values:
# SECRET_KEY=your-generated-secret-key
# DATABASE_URL=postgresql://caloria_user:YOUR_NEW_SECURE_PASSWORD@localhost/caloria_db
# MANYCHAT_API_TOKEN=your-manychat-token

# 4. Initialize database
sudo -u caloria bash
cd /var/www/caloria
source venv/bin/activate
python -c "from app import app, db; app.app_context().push(); db.create_all()"
exit

# 5. Start services
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start caloria
sudo systemctl restart nginx
```

---

## Step 5: Set Up SSL Certificate 🔒

### Install Let's Encrypt SSL

```bash
# Install SSL certificate for your domain
sudo certbot --nginx -d caloria.vip -d www.caloria.vip

# Follow the prompts:
# 1. Enter your email address
# 2. Agree to terms
# 3. Choose whether to share email with EFF
# 4. Select redirect option (recommended: 2)
```

### Verify SSL

```bash
# Check SSL certificate
curl -I https://caloria.vip

# Should return HTTP/2 200 OK
```

---

## 🎉 Verification & Testing

### Check Your Deployment

1. **Website**: https://caloria.vip
2. **Admin Panel**: https://caloria.vip/admin
3. **Login**: `admin` / `CHANGE-THIS-PASSWORD`

### Test API Endpoints

```bash
# Test webhook endpoint
curl -X POST https://caloria.vip/webhook/manychat \
  -H "Content-Type: application/json" \
  -d '{"subscriber_id": "test123", "page_id": "test", "data": {"text": "apple"}}'
```

### Update ManyChat Webhook

1. Go to **ManyChat** → **Settings** → **API & Webhooks**
2. Set webhook URL: `https://caloria.vip/webhook/manychat`

---

## 🔧 Ongoing Management

### Useful Commands

```bash
# Check application status
sudo supervisorctl status caloria

# View logs
sudo tail -f /var/log/supervisor/caloria.log
sudo tail -f /var/log/nginx/access.log

# Restart application
sudo supervisorctl restart caloria

# Update application (after code changes)
sudo -u caloria bash
cd /var/www/caloria
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
exit
sudo supervisorctl restart caloria
```

### Security Best Practices

```bash
# Regular security updates
sudo apt update && sudo apt upgrade -y

# Check firewall status
sudo ufw status

# Monitor failed login attempts
sudo tail -f /var/log/auth.log
```

---

## 🆘 Troubleshooting

### Common Issues

**1. Application won't start:**
```bash
sudo supervisorctl tail caloria stderr
# Check error logs for issues
```

**2. Database connection errors:**
```bash
sudo -u postgres psql
\l  # List databases
\du # List users
```

**3. Nginx configuration errors:**
```bash
sudo nginx -t
sudo systemctl status nginx
```

**4. SSL certificate issues:**
```bash
sudo certbot certificates
sudo certbot renew --dry-run
```

### Log Locations

- Application logs: `/var/log/supervisor/caloria.log`
- Nginx access logs: `/var/log/nginx/access.log`
- Nginx error logs: `/var/log/nginx/error.log`
- System logs: `/var/log/syslog`

---

## 📊 Expected Timeline

- **VPS Setup**: 5-15 minutes
- **GitHub Setup**: 5 minutes
- **DNS Configuration**: 5 minutes
- **Deployment Script**: 10-15 minutes
- **SSL Setup**: 5 minutes
- **DNS Propagation**: 1-24 hours
- **Testing & Verification**: 10 minutes

**Total**: ~1-2 hours (excluding DNS propagation)

---

## 🎯 Final Result

✅ **https://caloria.vip** - Your production WhatsApp bot  
✅ **https://caloria.vip/admin** - Admin dashboard  
✅ **SSL Certificate** - Automatic HTTPS  
✅ **PostgreSQL Database** - Production database  
✅ **Professional Domain** - Custom branding  
✅ **Automatic Restarts** - High availability  

---

## 📞 Support

**King Servers Support**: Available via their control panel  
**Caloria Issues**: Check logs and troubleshooting section above

Your WhatsApp calorie tracker is now live on caloria.vip! 🎉🥗📱 

Perfect! 🛡️ **SAFE MULTI-PROJECT DEPLOYMENT READY!**

## 🎯 **Conflict-Free Configuration:**

Your new deployment is **100% isolated** and won't interfere with existing projects:

### **✅ What Makes This Safe:**

1. **🔌 Unique Port**: Uses port `5001` internally (not 5000)
2. **🗄️ Isolated Database**: `caloria_vip_db` + `caloria_vip_user` (unique names)
3. **👤 Dedicated User**: `caloria` user (separate from other projects)
4. **📁 Isolated Directory**: `/var/www/caloria` (won't touch other dirs)
5. **⚙️ Unique Services**: `caloria-vip` supervisor process (unique name)
6. **🌐 Domain-Specific Nginx**: Only affects `caloria.vip` domain
7. **🔒 Additive Firewall**: Only adds rules, doesn't remove existing
8. **🐍 Isolated Python**: Separate virtual environment

---

## 🚀 **Safe Deployment Commands:**

### **Step 1: Connect to Your VPS**
```bash
ssh root@162.248.225.106
```

### **Step 2: Download and Run Safe Deployment**
```bash
# Download the safe deployment script
wget https://raw.githubusercontent.com/mamagarobonomon/caloria/main/safe_deploy_script.sh

# Make it executable
chmod +x safe_deploy_script.sh

# Run the safe deployment (won't affect other projects)
sudo ./safe_deploy_script.sh
```

### **Step 3: Configure Production Environment**
```bash
<code_block_to_apply_changes_from>
```

### **Step 4: Update Database Password & Start Services**
```bash
# Update PostgreSQL with the generated password
DB_PASS=$(grep DATABASE_URL /var/www/caloria/.env | cut -d: -f3 | cut -d@ -f1)
sudo -u postgres psql -c "ALTER USER caloria_vip_user PASSWORD '$DB_PASS';"

# Start isolated services
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start caloria-vip
sudo systemctl reload nginx

# Check isolated service status
sudo supervisorctl status caloria-vip
```

### **Step 5: Install SSL Certificate**
```bash
# SSL for your domain only (replace with your email)
sudo certbot --nginx -d caloria.vip -d www.caloria.vip --non-interactive --agree-tos --email your-email@example.com
```

---

## 🔍 **Verification (Won't Affect Other Projects):**

```bash
# Test isolated service
curl -I http://127.0.0.1:5001
curl -I https://caloria.vip

# Check only caloria services
sudo supervisorctl status caloria-vip
```

---

## 🛡️ **Isolation Guarantees:**

- **✅ Other projects keep using**: ports 80, 443, 5000, etc.
- **✅ Existing nginx configs**: Completely untouched
- **✅ Other databases**: Safe and isolated
- **✅ Other supervisor services**: Continue running normally
- **✅ System packages**: Only adds, never removes
- **✅ Firewall rules**: Only adds HTTP/HTTPS if missing

---

## 🎯 **Ready to Deploy Safely?**

**Connect to your VPS:**
```bash
ssh root@162.248.225.106
```

**Then run:**
```bash
wget https://raw.githubusercontent.com/mamagarobonomon/caloria/main/safe_deploy_script.sh && chmod +x safe_deploy_script.sh && sudo ./safe_deploy_script.sh
```

**This deployment is 100% safe for multi-project servers!** 🛡️

**Your existing projects will continue running normally while Caloria gets deployed in complete isolation.** ✅

**Ready when you are!** 🚀

**This deployment is 100% safe for multi-project servers!** 🛡️

**Your existing projects will continue running normally while Caloria gets deployed in complete isolation.** ✅

**Ready when you are!** 🚀 