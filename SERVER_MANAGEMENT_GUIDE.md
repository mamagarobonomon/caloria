# 🖥️ Server Management Guide: Preventing Domain Conflicts

**How to prevent other applications from hijacking caloria.vip**

---

## 🚨 **What Happened?**

The issue occurred because:
1. **Port 5001 was occupied** by another application
2. **SSL configuration was incomplete** for caloria.vip
3. **Nginx fell back to a default server** (Express.js app) when HTTPS requests came in

---

## 🛡️ **Prevention Strategies**

### **1. Port Allocation Management**

**Current Port Allocations on VPS:**
```bash
Port 3011: checkiton.net (Node.js/Express)
Port 5001: caloria.vip (Flask/Python) 
Port 8000: memebox.app (Frontend)
```

**Before deploying any new application:**
```bash
# Check if port is free
sudo lsof -i :5001
# If occupied, choose a different port!
```

### **2. Mandatory SSL Configuration**

**Every domain MUST have both HTTP and HTTPS configured:**
```bash
# Updated deployment script automatically runs:
sudo certbot --nginx -d caloria.vip -d www.caloria.vip --redirect
```

**This ensures:**
- ✅ Proper SSL certificates
- ✅ HTTPS redirects
- ✅ No fallback to wrong applications

### **3. Nginx Server Block Isolation**

**Each application has isolated nginx config:**
```nginx
# /etc/nginx/sites-available/caloria-vip
server {
    listen 80;
    listen 443 ssl; # BOTH protocols configured
    server_name caloria.vip www.caloria.vip;
    
    # SSL certificate paths
    ssl_certificate /etc/letsencrypt/live/caloria.vip/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/caloria.vip/privkey.pem;
    
    # Proxy to correct port
    location / {
        proxy_pass http://127.0.0.1:5001;  # Caloria-specific port
        # ... proxy headers
    }
}
```

### **4. Application User Isolation**

**Each application runs under its own user:**
```bash
User: caloria    -> /var/www/caloria    (Port 5001)
User: checkiton  -> /var/www/checkiton  (Port 3011)
User: memebox    -> /var/www/memebox    (Port 8000)
```

---

## 🔍 **Monitoring & Detection**

### **Daily Health Check**
```bash
# Run monitoring script
./monitor_caloria.sh

# Expected output:
# ✅ ALL CHECKS PASSED: Caloria deployment is healthy!
```

### **Manual Verification Commands**
```bash
# 1. Check port ownership
sudo lsof -i :5001
# Should show: gunicorn processes owned by 'caloria' user

# 2. Test domain content
curl -s https://caloria.vip | grep -i "caloria.*nutrición"
# Should return: matching lines

# 3. Check HTTP headers
curl -sI https://caloria.vip
# Should NOT contain: X-Powered-By: Express
# Should contain: X-Frame-Options: DENY (Flask indicators)

# 4. Verify SSL certificate
sudo certbot certificates | grep caloria.vip
# Should show: valid certificate
```

---

## 🔧 **Quick Fix Commands**

If domain hijacking is detected:

```bash
# 1. Kill conflicting processes on port 5001
sudo pkill -f "port.*5001"

# 2. Restart Caloria application
sudo supervisorctl restart caloria-vip

# 3. Fix SSL configuration
sudo certbot --nginx -d caloria.vip -d www.caloria.vip --redirect

# 4. Reload nginx
sudo nginx -t && sudo systemctl reload nginx

# 5. Verify fix
curl -sI https://caloria.vip
```

---

## 📋 **Deployment Checklist**

Before deploying ANY application on the server:

- [ ] **Check port availability**: `sudo lsof -i :PORT`
- [ ] **Use unique port number**: Don't reuse existing ports
- [ ] **Create dedicated user**: `sudo useradd -m APP_NAME`
- [ ] **Configure both HTTP & HTTPS**: Use certbot for SSL
- [ ] **Test nginx config**: `sudo nginx -t`
- [ ] **Verify no conflicts**: Run domain content checks

---

## 🚨 **Emergency Contacts & Commands**

**If caloria.vip shows wrong content:**

1. **Immediate fix**: `sudo supervisorctl restart caloria-vip`
2. **Check logs**: `sudo tail -f /var/log/supervisor/caloria-vip.log`
3. **Full monitoring**: `./monitor_caloria.sh`

**Server admin contacts:**
- VPS Provider: King Servers (162.248.225.106)
- SSL Certificate: Let's Encrypt (auto-renewal enabled)
- Domain Registrar: GoDaddy (caloria.vip)

---

## 📈 **Automation Setup**

**Set up daily monitoring via cron:**
```bash
# Add to server crontab
0 9 * * * /path/to/monitor_caloria.sh | mail -s "Caloria Health Check" admin@caloria.vip
```

This ensures automatic detection of any domain hijacking attempts! 