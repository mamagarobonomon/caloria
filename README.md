# Caloria - WhatsApp Calorie Tracker

A comprehensive WhatsApp chatbot that helps users track their calorie intake and achieve their health goals through AI-powered food analysis.

## 🚀 Features

### Core Functionality
- **Multi-Modal Food Analysis**: Process photos, text descriptions, and voice messages
- **AI-Powered Recognition**: Google Cloud Vision & Speech APIs for accurate food and voice recognition
- **Nutritional Analysis**: Spoonacular API integration for detailed nutritional data
- **Personalized Goals**: BMR calculation using Harris-Benedict formula
- **Daily Summaries**: Automated daily statistics and recommendations
- **ManyChat Integration**: Seamless WhatsApp conversation management

### Admin Panel
- **User Management**: View and manage all users
- **Real-time Analytics**: Dashboard with statistics and charts
- **Food Log Monitoring**: Track user activity and food entries
- **Data Export**: Export user data for analysis

### Technical Features
- **Modern UI**: Beautiful, responsive admin interface with Bootstrap 5
- **RESTful APIs**: Well-structured API endpoints for external integrations
- **Database Management**: Comprehensive data models with relationships
- **Scheduled Tasks**: Automated daily updates and recommendations
- **Error Handling**: Robust fallback systems for API failures

## 🏗️ Architecture

### System Components
1. **ManyChat**: WhatsApp integration and conversation flows
2. **Flask Backend**: API endpoints and business logic
3. **PostgreSQL Database**: User data and food logs storage
4. **Admin Panel**: Web-based management interface

### Database Schema
- **Users**: Profile information, goals, and calculated values
- **Food Logs**: Individual meal entries with nutritional data
- **Daily Stats**: Aggregated daily statistics and recommendations
- **Admin Users**: Administrative access management

## 📚 Documentation

### **🔗 Quick Access to Documentation**
- **[📚 Documentation Index](./DOCUMENTATION_INDEX.md)** - Complete reference to all guides
- **[📘 Mercado Pago Integration Guide](./MERCADOPAGO_INTEGRATION_GUIDE.md)** - **MAIN REFERENCE** for payment integration
- **[🚨 Mercado Pago Webhook Fixes](./MERCADOPAGO_WEBHOOK_FIXES.md)** - Critical fixes and corrections
- **[🚀 Deployment Guide](./DEPLOYMENT_CONSOLIDATED.md)** - Production deployment instructions

### **💳 Subscription Features (NEW)**
Caloria now includes a premium subscription system powered by Mercado Pago:
- **1-day free trial** with full premium access
- **Monthly subscription** at $4999.00 ARS (~$5.00 USD)
- **Argentina-focused** payment integration
- **Real-time webhook processing** for subscription status
- **Comprehensive trial management** and re-engagement flows

**For all subscription integration details, see the [Mercado Pago Integration Guide](./MERCADOPAGO_INTEGRATION_GUIDE.md).**

## 🛠️ Installation

### Prerequisites
- Python 3.8+
- PostgreSQL (optional, defaults to SQLite)
- Google Cloud account with Vision & Speech APIs enabled
- ManyChat account
- Spoonacular API key

### Local Setup

1. **Clone the repository**
```bash
git clone <repository-url>
cd Caloria
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Set environment variables**
```bash
export SECRET_KEY="your-secret-key-here"
export SPOONACULAR_API_KEY="your-spoonacular-api-key"
export MANYCHAT_API_TOKEN="your-manychat-api-token"
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/google-cloud-service-account.json"
export DATABASE_URL="postgresql://user:password@localhost/caloria"  # Optional
```

4. **Initialize the database**
```bash
python app.py
```

5. **Access the application**
- Main page: http://localhost:5000
- Admin panel: http://localhost:5000/admin
- Default admin credentials: `admin` / `admin123`

## 🔧 Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `SECRET_KEY` | Flask session security key | Yes |
| `SPOONACULAR_API_KEY` | Nutritional data API key | Yes |
| `MANYCHAT_API_TOKEN` | WhatsApp integration token | Yes |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to Google Cloud service account JSON | Yes |
| `GOOGLE_CLOUD_KEY_JSON` | Google Cloud service account JSON (alternative) | Yes* |
| `DATABASE_URL` | PostgreSQL connection string | No |
| `OPENAI_API_KEY` | OpenAI API for enhanced analysis | No |

*Either `GOOGLE_APPLICATION_CREDENTIALS` or `GOOGLE_CLOUD_KEY_JSON` is required for Google Cloud APIs.

### ManyChat Setup

1. **Create ManyChat Account**: Sign up at manychat.com
2. **Configure Webhook**: Set webhook URL to `your-domain.com/webhook/manychat`
3. **Design Conversation Flows**:
   - Initial quiz flow for user onboarding
   - Food logging flow with follow-up questions
   - Daily summary message flow

### Google Cloud API Setup (Primary)

1. **Create Google Cloud Project**: Visit console.cloud.google.com
2. **Enable APIs**:
   - Vision API (for food image recognition)
   - Speech-to-Text API (for voice processing)
3. **Create Service Account**:
   - Go to IAM & Admin → Service Accounts
   - Create new service account with Vision and Speech permissions
   - Generate and download JSON key file
4. **Configure Credentials**:
   ```bash
   # Option 1: Set path to JSON file
   export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json"
   
   # Option 2: Set JSON content directly
   export GOOGLE_CLOUD_KEY_JSON='{"type":"service_account","project_id":"..."}'
   ```

### Spoonacular API Setup (Nutritional Data)

1. **Get API Key**: Register at spoonacular.com/food-api
2. **Configure Endpoints**: The system uses:
   - Ingredient parsing endpoint for nutritional data
   - Recipe parsing for nutrition lookup

## 📱 WhatsApp Integration

### Conversation Flows

#### Initial Quiz Flow
- Collect user's name, weight, height, age
- Determine activity level and health goals
- Calculate BMR and daily calorie targets

#### Food Logging Flow
- Accept photos, text, or voice messages
- Ask clarifying questions when needed
- Provide detailed nutritional analysis
- Update daily statistics in real-time

#### Daily Summary Flow
- Send automated evening summaries
- Provide personalized recommendations
- Track progress toward goals

### Sample Conversation
```
User: [Sends photo of soup]
Bot: Could you clarify a few details? What type of meat is used?
User: Beef, no oil added
Bot: 📊 Nutritional Analysis:
     🍽️ Beef soup (1000ml)
     🔥 Energy: 973.7 kcal
     💪 Protein: 115.8g
     ⭐ Overall Rating: 4/5 – Great Choice!
```

## 🔌 API Endpoints

### Webhook Endpoints
- `POST /webhook/manychat` - Handle ManyChat webhooks

### Admin API
- `GET /api/users` - Get all users (admin only)
- `GET /api/users/{id}/stats` - Get user statistics

### Food Analysis API
- Handles image, text, and voice analysis internally
- Integrates with Spoonacular and fallback systems

## 🎨 Admin Panel Features

### Dashboard
- **Statistics Cards**: Total users, active users, completed quizzes, food logs
- **Recent Activity**: Latest users and food logs
- **Charts**: User activity trends over time
- **Quick Actions**: Common administrative tasks

### User Management
- **User List**: Paginated table with filtering and search
- **User Details**: Comprehensive user profiles with food logs
- **Statistics**: Individual user progress charts
- **Actions**: Activate/deactivate users, view detailed logs

### Features
- **Responsive Design**: Works on desktop and mobile
- **Real-time Updates**: Auto-refresh capabilities
- **Export Functions**: Data export for analysis
- **API Documentation**: Built-in API documentation modal

## 🚀 Deployment

### Production Deployment Guide

**📖 Complete deployment instructions**: See [`DEPLOYMENT_CONSOLIDATED.md`](./DEPLOYMENT_CONSOLIDATED.md)

**Quick Overview:**
1. **VPS Setup**: King Servers VPS (162.248.225.106) with Ubuntu 22.04
2. **Domain**: caloria.vip with GoDaddy DNS configuration
3. **SSL**: Let's Encrypt automatic certificates
4. **Deployment**: Safe, multi-project compatible scripts
5. **Language**: Spanish/English bilingual website

**🎯 Features of Current Deployment:**
- ✅ **Live Website**: https://caloria.vip (Spanish default + EN toggle)
- ✅ **Admin Panel**: https://caloria.vip/admin (`admin` / `CaloriaAdmin2025!`)
- ✅ **SSL Security**: HTTPS with auto-renewal
- ✅ **Isolated Setup**: Won't interfere with other projects
- ✅ **WhatsApp Integration**: Ready for ManyChat connection

### Quick Update Commands
```bash
# Update deployed application (after code changes)
ssh vps@162.248.225.106 "cd /var/www/caloria && sudo -u caloria git pull origin main && sudo -u caloria pkill -f gunicorn; sudo -u caloria bash -c 'cd /var/www/caloria && source venv/bin/activate && nohup gunicorn --bind 127.0.0.1:5001 --workers 2 --timeout 300 app:app > logs/gunicorn.log 2>&1 &'"
```

### Alternative Deployment Options
- **Docker**: See `Dockerfile` for containerized deployment
- **Google Cloud**: See `app.yaml` for App Engine deployment
- **Other VPS**: Adapt the safe deployment scripts

## 📊 Monitoring and Analytics

### Built-in Analytics
- User registration trends
- Food logging patterns
- Goal completion rates
- API usage statistics

### Logging
- Comprehensive error logging
- API request/response logging
- User activity tracking

## 🔒 Security Features

- **Admin Authentication**: Secure login system
- **Session Management**: Flask session security
- **Input Validation**: Comprehensive data validation
- **API Security**: Webhook verification and rate limiting
- **Data Privacy**: GDPR compliance considerations

## 🧪 Testing

### Manual Testing
1. **Admin Panel**: Test all CRUD operations
2. **Webhook Endpoints**: Test with ManyChat simulator
3. **Food Analysis**: Test with various food images and descriptions
4. **Database Operations**: Verify data integrity

### Automated Testing (To Implement)
```bash
# Unit tests
python -m pytest tests/

# Integration tests
python -m pytest tests/integration/
```

## 🛠️ Maintenance

### Regular Tasks
- **Database Backup**: Regular PostgreSQL backups
- **Log Rotation**: Manage application logs
- **API Monitoring**: Monitor external API usage
- **Performance Optimization**: Database query optimization

### Updates
- **Dependency Updates**: Regular security updates
- **Feature Additions**: New analysis capabilities
- **UI Improvements**: Enhanced admin interface

## 📈 Scaling Considerations

### Performance Optimization
- **Database Indexing**: Optimize common queries
- **Caching**: Implement Redis for session storage
- **CDN**: Use CDN for static assets
- **Load Balancing**: Multiple application instances

### Advanced Features
- **Machine Learning**: Custom food recognition models
- **Mobile App**: Native mobile applications
- **Multiple Languages**: Internationalization support
- **Advanced Analytics**: Business intelligence dashboards

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

### Troubleshooting
- **Database Issues**: Check connection strings and permissions
- **API Errors**: Verify API keys and network connectivity
- **ManyChat Issues**: Check webhook configuration and bot flows

### Getting Help
- Check the documentation
- Review error logs
- Contact support team

---

**Caloria** - Making healthy eating simple through AI-powered WhatsApp tracking 🥗📱 