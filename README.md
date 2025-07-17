# Caloria - WhatsApp Calorie Tracker

A comprehensive WhatsApp chatbot that helps users track their calorie intake and achieve their health goals through AI-powered food analysis.

## 🚀 Features

### Core Functionality
- **Multi-Modal Food Analysis**: Process photos, text descriptions, and voice messages
- **AI-Powered Recognition**: Spoonacular API integration for accurate nutritional analysis
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

## 🛠️ Installation

### Prerequisites
- Python 3.8+
- PostgreSQL (optional, defaults to SQLite)
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
| `SPOONACULAR_API_KEY` | Food analysis API key | Yes |
| `MANYCHAT_API_TOKEN` | WhatsApp integration token | Yes |
| `DATABASE_URL` | PostgreSQL connection string | No |
| `OPENAI_API_KEY` | OpenAI API for enhanced analysis | No |
| `GOOGLE_CLOUD_API_KEY` | Speech-to-text API key | No |

### ManyChat Setup

1. **Create ManyChat Account**: Sign up at manychat.com
2. **Configure Webhook**: Set webhook URL to `your-domain.com/webhook/manychat`
3. **Design Conversation Flows**:
   - Initial quiz flow for user onboarding
   - Food logging flow with follow-up questions
   - Daily summary message flow

### Spoonacular API Setup

1. **Get API Key**: Register at spoonacular.com/food-api
2. **Configure Endpoints**: The system uses:
   - Image analysis endpoint
   - Ingredient parsing endpoint
   - Nutrition data endpoint

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

### Production Deployment

1. **Set up hosting** (AWS, Heroku, DigitalOcean)
2. **Configure environment variables**
3. **Set up PostgreSQL database**
4. **Configure domain and SSL**
5. **Set up ManyChat webhook**

### Docker Deployment (Optional)
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["python", "app.py"]
```

### Environment Configuration
```bash
# Production settings
export FLASK_ENV=production
export SECRET_KEY="complex-production-secret"
export DATABASE_URL="postgresql://..."
```

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