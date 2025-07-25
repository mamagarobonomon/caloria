#!/bin/bash

# Production Environment Setup for Caloria
# Run this script on the server after the safe deployment

echo "🔧 Setting up production environment for Caloria..."

# Generate secure SECRET_KEY
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")

# Generate secure database password
DB_PASSWORD=$(python3 -c "import secrets; print(secrets.token_urlsafe(16))")

# Create production .env file
cat > /var/www/caloria/.env << EOF
# Production Environment Variables for Caloria
SECRET_KEY=${SECRET_KEY}
FLASK_ENV=production
DEBUG=False

# Database Configuration (PostgreSQL)
DATABASE_URL=postgresql://caloria_vip_user:${DB_PASSWORD}@localhost/caloria_vip_db

# External API Keys
SPOONACULAR_API_KEY=3e0eac47470049d6845406463f223518
MANYCHAT_API_TOKEN=your-manychat-token-here
OPENAI_API_KEY=your-openai-api-key-here

# Google Cloud Authentication (Service Account JSON)
# Choose ONE of the following methods:
# Method 1: File path (recommended for production)
# GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
# Method 2: JSON content directly (for containerized deployments)
# GOOGLE_CLOUD_KEY_JSON={"type":"service_account","project_id":"your-project",...}

# Google Cloud Project Configuration
GOOGLE_CLOUD_PROJECT_ID=your-google-cloud-project-id
GOOGLE_CLOUD_LOCATION=us-central1

# Admin Configuration
DEFAULT_ADMIN_USERNAME=admin
DEFAULT_ADMIN_PASSWORD=CaloriaAdmin2025!

# File Upload Settings
UPLOAD_FOLDER=/var/www/caloria/uploads
MAX_CONTENT_LENGTH=16777216

# Logging
LOG_LEVEL=INFO

# Scheduled Tasks
DAILY_UPDATE_HOUR=20
DAILY_UPDATE_MINUTE=0

# Server Configuration
HOST=0.0.0.0
PORT=5001

# Security Settings
SESSION_COOKIE_SECURE=True
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE=Lax
EOF

echo "✅ Production environment file created!"
echo ""
echo "🔑 Generated Credentials:"
echo "Database Password: ${DB_PASSWORD}"
echo "SECRET_KEY: ${SECRET_KEY}"
echo "Admin Password: CaloriaAdmin2025!"
echo ""
echo "⚠️  Please save these credentials securely!"

# Update PostgreSQL with the generated password
echo "🗄️ Updating PostgreSQL password..."
sudo -u postgres psql -c "ALTER USER caloria_vip_user PASSWORD '${DB_PASSWORD}';"

echo ""
echo "🎯 Next steps:"
echo "1. Initialize database: python -c 'from app import app, db; app.app_context().push(); db.create_all()'"
echo "2. Start services: sudo supervisorctl reread && sudo supervisorctl update && sudo supervisorctl start caloria-vip"
echo "3. Setup SSL: sudo certbot --nginx -d caloria.vip -d www.caloria.vip" 