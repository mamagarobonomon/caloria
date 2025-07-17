# 🛡️ Safe Caloria Deployment for King Servers VPS

**Multi-project server compatible - won't interfere with existing projects**

## 📋 King Servers Connection Info

King Servers typically provides:
- **Server IP**: 162.248.225.106
- **Username**: Your chosen username (e.g., `username`, `admin`, `user`, etc.)
- **Password**: Provided in King Servers email/control panel
- **SSH Port**: 22 (default)

## 🔗 **Step 1: Connect with Your King Servers Username**

### **Find Your Username:**
Check your King Servers email or control panel for:
- Username (NOT root)
- Password
- Server IP: 162.248.225.106

### **Connect via SSH:**
```bash
# Replace 'your-username' with your actual King Servers username
ssh your-username@162.248.225.106

# Examples of common usernames:
# ssh admin@162.248.225.106
# ssh user@162.248.225.106
# ssh ubuntu@162.248.225.106
# ssh sergey@162.248.225.106
```

**Enter your password when prompted**

---

## 🚀 **Step 2: Safe Deployment (Multi-Project Compatible)**

Once connected to your VPS with your username:

### **Download Safe Deployment Script:**
```bash
# Download the isolated deployment script
wget https://raw.githubusercontent.com/mamagarobonomon/caloria/main/safe_deploy_script.sh

# Make it executable
chmod +x safe_deploy_script.sh

# Run with sudo (since you're not root)
sudo ./safe_deploy_script.sh
```

---

## 🔧 **Step 3: Production Configuration**

### **3a. Configure Isolated Environment:**
```bash
# Switch to the isolated caloria user
sudo -u caloria bash
cd /var/www/caloria
source venv/bin/activate

# Generate secure production configuration
python3 -c "
import secrets
import os

# Generate unique passwords for this isolated instance
db_pass = secrets.token_urlsafe(16)
admin_pass = secrets.token_urlsafe(12)

print('🔐 SAVE THESE CREDENTIALS FOR CALORIA:')
print(f'🌐 Website: https://caloria.vip/admin')
print(f'👤 Admin Login: admin')
print(f'🔑 Admin Password: {admin_pass}')
print(f'🗄️ Database User: caloria_vip_user')
print(f'🔒 Database Password: {db_pass}')
print('='*50)

# Create isolated production environment
env_content = f'''SECRET_KEY=7J9b_3OdefZaC10a1B7Zi137WiC5yzc7l_UsBXo7zAI
FLASK_ENV=production
DATABASE_URL=postgresql://caloria_vip_user:{db_pass}@localhost/caloria_vip_db
SPOONACULAR_API_KEY=3e0eac47470049d6845406463f223518
MANYCHAT_API_TOKEN=your-manychat-token-here
DEFAULT_ADMIN_USERNAME=admin
DEFAULT_ADMIN_PASSWORD={admin_pass}
UPLOAD_FOLDER=/var/www/caloria/uploads
MAX_CONTENT_LENGTH=16777216
LOG_LEVEL=INFO
PORT=5001'''

with open('.env', 'w') as f:
    f.write(env_content)

print('✅ Isolated production environment configured!')
print('📝 Environment file created at: /var/www/caloria/.env')
"

# Initialize the isolated database
python -c "from app import app, db; app.app_context().push(); db.create_all(); print('🗄️ Isolated database initialized!')"

# Exit back to your user account
exit
```

### **3b. Update Database & Start Services:**
```bash
# Update PostgreSQL with the generated password
DB_PASS=$(sudo grep DATABASE_URL /var/www/caloria/.env | cut -d: -f3 | cut -d@ -f1)
sudo -u postgres psql -c "ALTER USER caloria_vip_user PASSWORD '$DB_PASS';"

# Start the isolated Caloria services
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start caloria-vip
sudo systemctl reload nginx

# Check the isolated service status
echo "📊 Caloria Service Status (isolated):"
sudo supervisorctl status caloria-vip
```

---

## 🔒 **Step 4: SSL Certificate (Your Domain Only)**

### **Install SSL for caloria.vip:**
```bash
# Replace with your actual email address
sudo certbot --nginx -d caloria.vip -d www.caloria.vip --non-interactive --agree-tos --email your-email@example.com

# Example:
# sudo certbot --nginx -d caloria.vip -d www.caloria.vip --non-interactive --agree-tos --email sergey@example.com
```

---

## 🧪 **Step 5: Test Your Isolated Deployment**

```bash
# Test the isolated Caloria service
curl -I http://127.0.0.1:5001
curl -I https://caloria.vip

# Check isolated services only
sudo supervisorctl status caloria-vip
sudo systemctl status nginx --no-pager -l
```

---

## 🛡️ **Isolation Summary:**

Your Caloria deployment is **completely isolated**:

### **✅ What's Isolated:**
- **Port**: 5001 (internal) - won't conflict with other apps
- **Database**: `caloria_vip_db` & `caloria_vip_user` - unique names
- **User**: `caloria` - dedicated system user
- **Directory**: `/var/www/caloria` - isolated location
- **Nginx Config**: Only affects `caloria.vip` domain
- **Supervisor**: `caloria-vip` process - unique name

### **✅ What's Safe for Other Projects:**
- **Existing ports**: 80, 443, 5000, etc. remain untouched
- **Other databases**: Completely unaffected
- **Other nginx sites**: Continue working normally
- **Other supervisor processes**: Keep running
- **System packages**: Only adds, never removes

---

## 📋 **Quick Connection Reference:**

### **What You Need from King Servers:**
- **Server IP**: 162.248.225.106 ✅
- **Your Username**: `_____________` (from King Servers email)
- **Your Password**: `_____________` (from King Servers)

### **Connection Command:**
```bash
ssh YOUR_USERNAME@162.248.225.106
```

### **One-Line Deployment:**
```bash
wget https://raw.githubusercontent.com/mamagarobonomon/caloria/main/safe_deploy_script.sh && chmod +x safe_deploy_script.sh && sudo ./safe_deploy_script.sh
```

---

## 🎯 **Expected Results:**

After deployment:
- **✅ Website**: https://caloria.vip
- **✅ Admin Panel**: https://caloria.vip/admin
- **✅ Your other projects**: Continue running normally
- **✅ SSL Certificate**: Automatic HTTPS
- **✅ Isolated operation**: No conflicts

---

## 🆘 **If You Need Help:**

### **Check King Servers Username:**
1. **Login to King Servers** control panel
2. **Check VPS details** - username should be listed
3. **Or check the setup email** they sent you

### **Common King Servers Usernames:**
- `admin`
- `user` 
- `ubuntu` (if Ubuntu OS)
- Your chosen username during signup

### **Test Connection:**
```bash
# Try connecting (replace with your actual username)
ssh your-username@162.248.225.106

# If connection works, you'll see a password prompt
# If username is wrong, you'll get "Permission denied"
```

---

**What's your King Servers username?** Check your email or control panel, and I'll give you the exact connection command! 🚀 