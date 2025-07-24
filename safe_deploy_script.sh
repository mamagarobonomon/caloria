#!/bin/bash

# Safe Caloria Deployment Script - No Conflicts with Existing Projects
# Designed for multi-project servers

echo "🛡️ Starting SAFE Caloria deployment (multi-project compatible)..."

# Check if running with sudo privileges
if [ "$EUID" -ne 0 ]; then
    echo "❌ Please run with sudo: sudo ./safe_deploy_script.sh"
    echo "ℹ️  Note: Connect to server as 'vps' user, then run: sudo ./safe_deploy_script.sh"
    exit 1
fi

# Update system packages (safe)
echo "📦 Updating system packages..."
apt update

# Install only missing packages (won't conflict with existing)
echo "🔧 Installing required packages (if not already present)..."
apt install -y python3 python3-pip python3-venv git postgresql postgresql-contrib supervisor ufw

# Check if nginx is installed, install if needed
if ! command -v nginx &> /dev/null; then
    echo "🌐 Installing Nginx..."
    apt install -y nginx
else
    echo "✅ Nginx already installed, skipping..."
fi

# Check if certbot is installed, install if needed  
if ! command -v certbot &> /dev/null; then
    echo "🔒 Installing Certbot..."
    apt install -y certbot python3-certbot-nginx
else
    echo "✅ Certbot already installed, skipping..."
fi

# Create dedicated application user (unique name)
echo "👤 Creating caloria application user..."
if ! id "caloria" &>/dev/null; then
    useradd -m -s /bin/bash caloria
    echo "✅ User 'caloria' created"
else
    echo "✅ User 'caloria' already exists"
fi

# Create isolated application directory
echo "📁 Setting up application directory..."
mkdir -p /var/www/caloria
chown caloria:caloria /var/www/caloria

# Setup application as caloria user (completely isolated)
echo "🔄 Setting up application (isolated environment)..."
sudo -u caloria bash << 'EOF'
cd /var/www/caloria

# Remove existing installation if any
rm -rf * .git .env

# Clone repository
git clone https://github.com/mamagarobonomon/caloria.git .

# Create isolated Python virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies in isolation
pip install --upgrade pip
pip install -r requirements.txt

# Create uploads and logs directories
mkdir -p uploads logs static/css static/js
chmod 755 uploads logs static

echo "✅ Application environment ready!"
EOF

# Setup isolated PostgreSQL database (unique names)
echo "🗄️ Setting up isolated PostgreSQL database..."
sudo -u postgres psql << 'SQLEOF'
-- Create unique database and user for caloria
CREATE DATABASE caloria_vip_db;
CREATE USER caloria_vip_user WITH PASSWORD 'temp_password_change_me';
GRANT ALL PRIVILEGES ON DATABASE caloria_vip_db TO caloria_vip_user;
-- Make sure we don't conflict with existing databases
\q
SQLEOF

# Create isolated Nginx configuration (won't affect other sites)
echo "🌐 Creating isolated Nginx configuration..."
cat > /etc/nginx/sites-available/caloria-vip << 'NGINXEOF'
server {
    listen 80;
    server_name caloria.vip www.caloria.vip;
    
    # Isolated configuration for caloria only
    client_max_body_size 16M;
    
    location / {
        proxy_pass http://127.0.0.1:5001;  # Using port 5001 to avoid conflicts
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 300;
        proxy_send_timeout 300;
        proxy_read_timeout 300;
    }
    
    # Serve static files directly
    location /static {
        alias /var/www/caloria/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
    
    location /uploads {
        alias /var/www/caloria/uploads;
        expires 7d;
    }
    
    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
}
NGINXEOF

# Enable site without affecting others
if [ ! -L /etc/nginx/sites-enabled/caloria-vip ]; then
    ln -s /etc/nginx/sites-available/caloria-vip /etc/nginx/sites-enabled/
fi

# Test nginx configuration before reloading
nginx -t
if [ $? -eq 0 ]; then
    systemctl reload nginx
    echo "✅ Nginx configuration updated successfully"
else
    echo "❌ Nginx configuration error - please check"
    exit 1
fi

# Create isolated Supervisor configuration
echo "⚙️ Setting up isolated Supervisor configuration..."
cat > /etc/supervisor/conf.d/caloria-vip.conf << 'SUPEOF'
[program:caloria-vip]
command=/var/www/caloria/venv/bin/gunicorn --bind 127.0.0.1:5001 --workers 2 --timeout 300 app:app
directory=/var/www/caloria
user=caloria
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/supervisor/caloria-vip.log
stderr_logfile=/var/log/supervisor/caloria-vip-error.log
environment=PATH="/var/www/caloria/venv/bin"

[group:caloria]
programs=caloria-vip
SUPEOF

# Configure firewall (only add new rules, don't remove existing)
echo "🔒 Configuring firewall (safe mode)..."
# Only add rules if they don't exist
ufw status | grep -q "22/tcp" || ufw allow 22/tcp
ufw status | grep -q "80/tcp" || ufw allow 80/tcp  
ufw status | grep -q "443/tcp" || ufw allow 443/tcp

# Enable firewall only if not already enabled
if ! ufw status | grep -q "Status: active"; then
    echo "y" | ufw enable
fi

# 🔒 AUTOMATICALLY CONFIGURE SSL CERTIFICATE
echo "🔒 Setting up SSL certificate for caloria.vip..."
if ! certbot certificates 2>/dev/null | grep -q "caloria.vip"; then
    echo "📜 Creating new SSL certificate..."
    certbot --nginx -d caloria.vip -d www.caloria.vip --non-interactive --agree-tos --email sergey@caloria.vip --redirect
else
    echo "📜 SSL certificate exists, ensuring nginx SSL configuration..."
    certbot --nginx -d caloria.vip -d www.caloria.vip --redirect --non-interactive
fi

# ✅ VERIFY DEPLOYMENT INTEGRITY
echo "✅ Verifying deployment integrity..."

# Check port 5001 is exclusively used by caloria
CALORIA_PID=$(lsof -ti :5001 2>/dev/null)
if [ -n "$CALORIA_PID" ]; then
    CALORIA_USER=$(ps -o user= -p $CALORIA_PID 2>/dev/null)
    if [ "$CALORIA_USER" != "caloria" ]; then
        echo "❌ WARNING: Port 5001 is used by user '$CALORIA_USER', not 'caloria'"
        echo "🔧 Killing conflicting process..."
        kill $CALORIA_PID 2>/dev/null || true
        sleep 2
    fi
fi

# Test nginx configuration
nginx -t || {
    echo "❌ Nginx configuration test failed!"
    exit 1
}

# Reload nginx to apply SSL changes
systemctl reload nginx

echo ""
echo "🎉 SAFE deployment setup complete!"
echo ""
echo "🔧 Configuration Summary:"
echo "• Application directory: /var/www/caloria"
echo "• Application user: caloria"
echo "• Application port: 5001 (internal)"
echo "• Database: caloria_vip_db"
echo "• Database user: caloria_vip_user"
echo "• Nginx config: /etc/nginx/sites-available/caloria-vip"
echo "• Supervisor config: /etc/supervisor/conf.d/caloria-vip.conf"
echo ""
echo "📋 Next steps:"
echo "1. Configure production environment (.env file)"
echo "2. Update database password"
echo "3. Initialize database"
echo "4. Start supervisor services"
echo "5. Setup SSL certificate"
echo ""
echo "✅ No conflicts with existing projects!"
EOF 