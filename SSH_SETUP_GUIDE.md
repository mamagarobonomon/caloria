# 🔑 SSH Key Setup for Caloria VPS

**Secure, passwordless access to your Caloria VPS deployment**

---

## 🎯 **Why Use SSH Keys?**

- ✅ **No more passwords** - instant connection
- ✅ **More secure** - key-based authentication
- ✅ **Faster deployments** - automated access
- ✅ **Industry standard** - professional setup

---

## 🚀 **Quick Setup (5 minutes)**

### **Step 1: Generate SSH Key Pair**
```bash
# On your LOCAL machine (Mac/Linux/WSL)
ssh-keygen -t ed25519 -C "your-email@caloria-vps" -f ~/.ssh/id_ed25519 -N ""
```

### **Step 2: Copy Key to VPS**
```bash
# Enter your VPS password one last time
ssh-copy-id -i ~/.ssh/id_ed25519.pub vps@162.248.225.106
```

### **Step 3: Create SSH Config**
```bash
# Create config file for easy access
cat >> ~/.ssh/config << 'EOF'
# Caloria VPS Configuration
Host caloria-vps
    HostName 162.248.225.106
    User vps
    IdentityFile ~/.ssh/id_ed25519
    PasswordAuthentication no
    ServerAliveInterval 60
    ServerAliveCountMax 3

# Alias for easier access
Host caloria
    HostName 162.248.225.106
    User vps
    IdentityFile ~/.ssh/id_ed25519
    PasswordAuthentication no
    ServerAliveInterval 60
    ServerAliveCountMax 3
EOF

# Set secure permissions
chmod 600 ~/.ssh/config
```

### **Step 4: Test Connection**
```bash
# Should connect without password
ssh caloria "echo 'SSH working!' && whoami"
```

---

## 🛠️ **Easy Commands After Setup**

### **Connect to VPS:**
```bash
ssh caloria                    # Instant connection
```

### **Quick Status Check:**
```bash
ssh caloria "ps aux | grep gunicorn && curl -I http://127.0.0.1:5001"
```

### **Deploy Updates:**
```bash
# Full deployment update
ssh caloria "cd /var/www/caloria && sudo -u caloria bash -c 'git pull origin main && source venv/bin/activate && pip install -r requirements.txt && pkill -f gunicorn && nohup gunicorn --bind 127.0.0.1:5001 --workers 2 --timeout 300 app:app > logs/gunicorn.log 2>&1 &'"

# Quick git pull only
ssh caloria "cd /var/www/caloria && sudo -u caloria git pull origin main"
```

### **Check Application Status:**
```bash
ssh caloria "curl -I https://caloria.vip && echo 'Website is live!'"
```

---

## 🔒 **Security Features**

| Feature | Benefit |
|---------|---------|
| **Ed25519 Keys** | Modern, secure encryption |
| **No Password Auth** | Prevents brute force attacks |
| **Auto-disconnect Protection** | Stable connections |
| **Secure Permissions** | Proper file access controls |

---

## 🆘 **Troubleshooting**

### **Permission Denied:**
```bash
# Fix SSH config permissions
chmod 600 ~/.ssh/config
chmod 600 ~/.ssh/id_ed25519
chmod 644 ~/.ssh/id_ed25519.pub
```

### **Key Not Found:**
```bash
# Verify key exists
ls -la ~/.ssh/id_ed25519*

# Re-copy if needed
ssh-copy-id -i ~/.ssh/id_ed25519.pub vps@162.248.225.106
```

### **Connection Timeout:**
```bash
# Test direct connection
ssh -v vps@162.248.225.106

# Check VPS is running
ping 162.248.225.106
```

---

## 📋 **Alternative Methods**

### **Using Existing SSH Key:**
```bash
# If you already have an SSH key
ssh-copy-id vps@162.248.225.106

# Update SSH config with your existing key
# Replace ~/.ssh/id_ed25519 with your key path
```

### **Multiple Keys:**
```bash
# Add to SSH config with specific identity
Host caloria-work
    HostName 162.248.225.106
    User vps
    IdentityFile ~/.ssh/work_key
```

---

## ✅ **Verification Checklist**

After setup, you should be able to:

- [ ] Connect with `ssh caloria` (no password)
- [ ] Run `ssh caloria whoami` (returns "vps")
- [ ] Deploy updates in one command
- [ ] Access VPS instantly from terminal

---

**🎉 You're all set! SSH keys make deployment much faster and more secure.** 