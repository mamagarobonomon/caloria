#!/bin/bash

# Caloria Deployment Script for King Servers VPS
# Run this script on your Ubuntu/Debian VPS

echo "🚀 Starting Caloria deployment on King Servers VPS..."

# Update system
echo "📦 Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install required packages
echo "🔧 Installing required packages..."
sudo apt install -y python3 python3-pip python3-venv git nginx certbot python3-certbot-nginx postgresql postgresql-contrib supervisor ufw

# Create application user
echo "👤 Creating application user..."
sudo useradd -m -s /bin/bash caloria
sudo usermod -aG sudo caloria

# Create application directory
echo "📁 Setting up application directory..."
sudo mkdir -p /var/www/caloria
sudo chown caloria:caloria /var/www/caloria

# Switch to application user
echo "🔄 Setting up as caloria user..."
sudo -u caloria bash << 'EOF'
cd /var/www/caloria

# Clone your repository (you'll need to update this URL)
git clone https://github.com/YOUR-USERNAME/caloria.git .

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Create production environment file
cat > .env << 'ENVEOF'
# Production Environment Variables
SECRET_KEY=CHANGE-THIS-TO-SECURE-RANDOM-KEY
FLASK_ENV=production
DATABASE_URL=postgresql://caloria_user:SECURE_PASSWORD@localhost/caloria_db
SPOONACULAR_API_KEY=3e0eac47470049d6845406463f223518
MANYCHAT_API_TOKEN=your-manychat-token-here
OPENAI_API_KEY=
GOOGLE_CLOUD_API_KEY=
DEFAULT_ADMIN_USERNAME=admin
DEFAULT_ADMIN_PASSWORD=CHANGE-THIS-PASSWORD
UPLOAD_FOLDER=/var/www/caloria/uploads
MAX_CONTENT_LENGTH=16777216
LOG_LEVEL=INFO
DAILY_UPDATE_HOUR=20
DAILY_UPDATE_MINUTE=0
ENVEOF

# Create necessary directories
mkdir -p uploads logs
chmod 755 uploads logs

EOF

echo "✅ Application setup completed!"

# Setup PostgreSQL database
echo "🗄️ Setting up PostgreSQL database..."
sudo -u postgres psql << 'SQLEOF'
CREATE USER caloria_user WITH PASSWORD 'SECURE_PASSWORD_CHANGE_THIS';
CREATE DATABASE caloria_db OWNER caloria_user;
GRANT ALL PRIVILEGES ON DATABASE caloria_db TO caloria_user;
\q
SQLEOF

# Setup Nginx configuration
echo "🌐 Configuring Nginx..."
sudo tee /etc/nginx/sites-available/caloria << 'NGINXEOF'
server {
    listen 80;
    server_name caloria.vip www.caloria.vip;
    
    client_max_body_size 16M;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 300;
        proxy_send_timeout 300;
        proxy_read_timeout 300;
    }
    
    location /static {
        alias /var/www/caloria/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
    
    location /uploads {
        alias /var/www/caloria/uploads;
        expires 7d;
    }
}
NGINXEOF

# Enable the site
sudo ln -sf /etc/nginx/sites-available/caloria /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx

# Setup Supervisor for application management
echo "⚙️ Setting up Supervisor..."
sudo tee /etc/supervisor/conf.d/caloria.conf << 'SUPEOF'
[program:caloria]
command=/var/www/caloria/venv/bin/gunicorn --config /var/www/caloria/gunicorn.conf.py app:app
directory=/var/www/caloria
user=caloria
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/supervisor/caloria.log
environment=PATH="/var/www/caloria/venv/bin"
SUPEOF

# Setup firewall
echo "🔒 Configuring firewall..."
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw --force enable

echo "🎉 Basic deployment setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Update the GitHub repository URL in this script"
echo "2. Change database password in PostgreSQL and .env file"
echo "3. Generate secure SECRET_KEY"
echo "4. Update your domain DNS settings"
echo "5. Run SSL certificate setup"
echo ""
echo "🔧 Manual steps needed:"
echo "sudo -u caloria bash"
echo "cd /var/www/caloria"
echo "source venv/bin/activate"
echo "python -c 'from app import app, db; app.app_context().push(); db.create_all()'"
echo ""
echo "🔒 SSL Certificate:"
echo "sudo certbot --nginx -d caloria.vip -d www.caloria.vip" 