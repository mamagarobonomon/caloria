# 🌐 Google Cloud Setup Guide for Caloria

This guide will help you set up Google Cloud Vision API and Speech-to-Text API as the primary food recognition tools for Caloria.

---

## 🎯 **Why Google Cloud APIs?**

- ✅ **Superior accuracy** - Industry-leading image and speech recognition
- ✅ **Multi-language support** - Supports multiple languages for voice commands
- ✅ **Real-time processing** - Fast API response times
- ✅ **Scalable** - Handles high volume with Google's infrastructure
- ✅ **Food-specific** - Excellent at detecting food items in images

---

## 🚀 **Step 1: Create Google Cloud Project**

### **1a. Visit Google Cloud Console**
```
https://console.cloud.google.com
```

### **1b. Create New Project**
1. Click **"New Project"**
2. Enter project name: `caloria-food-recognition`
3. Note your **Project ID** (you'll need this later)
4. Click **"Create"**

---

## 🔧 **Step 2: Enable Required APIs**

### **2a. Enable Vision API**
```bash
# In Google Cloud Console:
Navigation Menu → APIs & Services → Library
Search: "Cloud Vision API"
Click → Enable
```

### **2b. Enable Speech-to-Text API**
```bash
# In Google Cloud Console:
Navigation Menu → APIs & Services → Library  
Search: "Cloud Speech-to-Text API"
Click → Enable
```

### **2c. Verify APIs are Enabled**
```bash
# Check in: APIs & Services → Dashboard
# You should see:
# ✅ Cloud Vision API
# ✅ Cloud Speech-to-Text API
```

---

## 🔑 **Step 3: Create Service Account**

### **3a. Create Service Account**
```bash
# Navigation Menu → IAM & Admin → Service Accounts
Click "Create Service Account"

Service account name: caloria-service-account
Service account ID: caloria-service-account
Description: Service account for Caloria food recognition
```

### **3b. Grant Permissions**
```bash
# Click "Continue" → Grant roles:
1. Add Role: "Cloud Vision → Vision AI Service Agent"
2. Add Role: "Cloud Speech → Speech Service Agent"
3. Click "Continue" → "Done"
```

### **3c. Generate JSON Key**
```bash
# In Service Accounts list:
1. Click on "caloria-service-account"
2. Go to "Keys" tab
3. Click "Add Key" → "Create new key"
4. Select "JSON" format
5. Click "Create"
6. Download the JSON file (keep it secure!)
```

---

## ⚙️ **Step 4: Configure Caloria Application**

### **Option A: Set File Path (Recommended)**
```bash
# Move your JSON file to a secure location
mv ~/Downloads/caloria-service-account-*.json /etc/google-cloud/caloria-credentials.json

# Set environment variable
export GOOGLE_APPLICATION_CREDENTIALS="/etc/google-cloud/caloria-credentials.json"

# Add to your .bashrc or .zshrc for persistence
echo 'export GOOGLE_APPLICATION_CREDENTIALS="/etc/google-cloud/caloria-credentials.json"' >> ~/.bashrc
```

### **Option B: Set JSON Content Directly**
```bash
# Read the JSON file content
export GOOGLE_CLOUD_KEY_JSON='{"type":"service_account","project_id":"your-project-id",...}'

# Or use file content directly
export GOOGLE_CLOUD_KEY_JSON=$(cat /path/to/your-service-account.json)
```

### **Option C: For Production/Docker**
```bash
# In your production environment variables:
GOOGLE_CLOUD_KEY_JSON={"type":"service_account","project_id":"caloria-food-recognition-123","private_key_id":"..."}

# Or mount the JSON file
GOOGLE_APPLICATION_CREDENTIALS=/app/credentials/google-cloud-service-account.json
```

---

## 🧪 **Step 5: Test Configuration**

### **5a. Test Credentials**
```bash
# Install Google Cloud CLI (optional)
curl https://sdk.cloud.google.com | bash
gcloud auth activate-service-account --key-file=/path/to/your-service-account.json

# Test authentication
gcloud auth list
```

### **5b. Test with Caloria**
```bash
# Start your Caloria application
python app.py

# Check logs for:
# ✅ "Google Cloud libraries available"
# ✅ "Google Cloud Vision API food analysis"
# ✅ "Google Cloud Speech-to-Text analysis"
```

---

## 💰 **Step 6: Understanding Costs & Limits**

### **Vision API Pricing (2024)**
- **Free tier**: 1,000 images/month
- **Label detection**: $1.50 per 1,000 images
- **Object localization**: $1.50 per 1,000 images

### **Speech-to-Text Pricing**
- **Free tier**: 60 minutes/month
- **Standard model**: $0.006 per 15 seconds
- **Enhanced model**: $0.009 per 15 seconds

### **Cost Optimization Tips**
```bash
# 1. Enable quotas to prevent overage
# APIs & Services → Quotas → Set daily limits

# 2. Monitor usage
# APIs & Services → Dashboard → View usage

# 3. Use caching in production
# Cache results to avoid repeat API calls
```

---

## 🔒 **Step 7: Security Best Practices**

### **7a. Secure Your Credentials**
```bash
# ❌ Never commit JSON keys to Git
echo "*.json" >> .gitignore
echo "google-cloud-*.json" >> .gitignore

# ✅ Use environment variables
# ✅ Restrict service account permissions
# ✅ Rotate keys regularly (every 90 days)
```

### **7b. Production Security**
```bash
# Create separate service accounts for:
# - Development environment
# - Staging environment  
# - Production environment

# Set up key rotation policy
# IAM & Admin → Service Accounts → Key rotation
```

---

## 🚨 **Troubleshooting**

### **Common Issues**

#### **"Google Cloud libraries not available"**
```bash
# Solution: Install required packages
pip install google-cloud-vision google-cloud-speech
```

#### **"No Google Cloud credentials available"**
```bash
# Check environment variables
echo $GOOGLE_APPLICATION_CREDENTIALS
echo $GOOGLE_CLOUD_KEY_JSON

# Verify file exists and is readable
ls -la $GOOGLE_APPLICATION_CREDENTIALS
cat $GOOGLE_APPLICATION_CREDENTIALS | jq .project_id
```

#### **"Permission denied" errors**
```bash
# Verify service account has correct roles:
# 1. Cloud Vision → Vision AI Service Agent
# 2. Cloud Speech → Speech Service Agent

# Check in IAM & Admin → IAM
```

#### **"API not enabled" errors**
```bash
# Enable APIs in Console:
# APIs & Services → Library → Search & Enable:
# - Cloud Vision API
# - Cloud Speech-to-Text API
```

#### **"Quota exceeded" errors**
```bash
# Check usage and quotas:
# APIs & Services → Quotas
# Increase quotas or implement caching
```

---

## 🎯 **Step 8: Verify Integration**

### **Test Image Recognition**
1. Send a food photo to your Caloria WhatsApp bot
2. Check logs for: `🔍 Starting Google Cloud Vision API food analysis`
3. Should see: `📍 Object detected: food` or `🏷️ Label detected: fruit`

### **Test Voice Recognition**
1. Send a voice message saying "I ate an apple"
2. Check logs for: `🎤 Starting Google Cloud Speech-to-Text analysis`
3. Should see: `🎯 Speech recognition: 'I ate an apple'`

### **Success Indicators**
```bash
# In your application logs:
✅ Google Cloud Vision analysis successful
✅ Google Speech transcription: 'chicken breast'
✅ Best food detection: fruit -> using: apple
```

---

## 📈 **Step 9: Monitoring & Optimization**

### **Set Up Monitoring**
```bash
# Google Cloud Console → Monitoring
# Create alerts for:
# - API quota approaching limits
# - High error rates
# - Response time degradation
```

### **Performance Optimization**
```bash
# In production:
# 1. Implement result caching
# 2. Resize images before API calls
# 3. Use batch processing for multiple requests
# 4. Set appropriate timeouts
```

---

## 🎉 **Congratulations!**

Your Caloria application now uses Google Cloud as the primary engine for:
- 📸 **Food image recognition** (Google Cloud Vision)
- 🎤 **Voice-to-text conversion** (Google Cloud Speech)
- 📊 **Nutritional analysis** (Spoonacular as fallback)

The system will automatically fall back to Spoonacular and local analysis if Google Cloud APIs are unavailable, ensuring reliability! 🚀 