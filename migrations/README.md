# 🔄 Caloria Database Migrations

**Database migration scripts for Caloria project setup and updates.**

---

## 📋 **Migration Scripts**

### **🛠️ `setup_mercadopago_env.py`**
**Purpose:** Initial environment setup for Mercado Pago integration  
**When to run:** During initial project setup  
**What it does:**
- Creates `.env` file with Mercado Pago credentials
- Sets up required environment variables
- Validates API connectivity

**Usage:**
```bash
cd migrations/
python setup_mercadopago_env.py
```

**Status:** ✅ **APPLIED** - Run once during project setup

---

### **🗄️ `migrate_subscription_db.py`**
**Purpose:** Add subscription functionality to existing database  
**When to run:** After basic Caloria setup, before enabling subscriptions  
**What it does:**
- Creates subscription tables (Subscription, PaymentTransaction, etc.)
- Adds subscription fields to User table
- Migrates existing user data
- Creates database relationships

**Usage:**
```bash
cd migrations/
python migrate_subscription_db.py
```

**Status:** ✅ **APPLIED** - Database migration completed

---

### **👤 `migrate_admin_dashboard.py`**
**Purpose:** Add admin dashboard functionality  
**When to run:** To enable enhanced admin features  
**What it does:**
- Creates SystemActivityLog table
- Migrates existing quiz/registration events
- Sets up analytics tracking
- Tests subscription analytics queries

**Usage:**
```bash
cd migrations/
python migrate_admin_dashboard.py
```

**Status:** ✅ **APPLIED** - Admin dashboard migration completed

---

## 🔍 **Migration History**

| Date | Script | Applied By | Status |
|------|--------|------------|--------|
| July 2024 | `setup_mercadopago_env.py` | Project Setup | ✅ Complete |
| July 2024 | `migrate_subscription_db.py` | Phase 1.5 | ✅ Complete |
| July 2024 | `migrate_admin_dashboard.py` | Admin Enhancement | ✅ Complete |

---

## ⚠️ **Important Notes**

### **🚨 Before Running Migrations**
1. **Backup your database** - Migrations modify database structure
2. **Test in development** first
3. **Check dependencies** - Ensure all required packages are installed
4. **Verify environment** - Make sure `.env` file exists

### **🔄 Re-running Migrations**
- **Setup scripts**: Can be run multiple times safely
- **Database migrations**: Include checks for existing tables
- **Data migrations**: Include duplicate prevention logic

### **🛡️ Safety Features**
- **Automatic backups** before major changes
- **Rollback information** provided in case of issues
- **Dry-run options** for testing (where available)
- **Error handling** with clear error messages

---

## 🧪 **Testing Migrations**

### **Before Production**
```bash
# Test database connection
python -c "from app import db; print('✅ Database connection works')"

# Test subscription functionality
cd migrations/
python -c "from migrate_subscription_db import test_subscription_models; test_subscription_models()"

# Test admin features
cd migrations/
python -c "from migrate_admin_dashboard import test_database_connection; test_database_connection()"
```

### **Verify Migration Success**
```bash
# Check if tables exist
python -c "from app import db; print([table.name for table in db.metadata.tables.values()])"

# Check subscription data
python -c "from app import User; print(f'Users with subscription fields: {User.query.count()}')"
```

---

## 🔧 **Troubleshooting**

### **Common Issues**

#### **"Table already exists" errors**
```bash
# Solution: Migration includes existence checks
# If error persists, check database manually:
python -c "from app import db; print(db.engine.table_names())"
```

#### **"Import errors" when running migrations**
```bash
# Solution: Run from correct directory
cd /path/to/caloria/migrations/
python migrate_subscription_db.py
```

#### **"Environment variables not found"**
```bash
# Solution: Run setup first
python setup_mercadopago_env.py
# Then run other migrations
```

#### **Database connection issues**
```bash
# Check if app is running
# Stop app, run migration, restart app
```

---

## 📁 **File Organization**

```
migrations/
├── README.md                    # This file
├── setup_mercadopago_env.py     # Environment setup (one-time)
├── migrate_subscription_db.py   # Subscription database migration  
└── migrate_admin_dashboard.py   # Admin dashboard migration
```

---

## 🎯 **Next Steps**

### **For New Installations**
1. Run `setup_mercadopago_env.py` first
2. Run `migrate_subscription_db.py` for subscription features
3. Run `migrate_admin_dashboard.py` for enhanced admin panel

### **For Future Migrations**
- New migration scripts should be added to this folder
- Update this README with new migration information
- Follow the same naming pattern: `migrate_feature_name.py`
- Include safety checks and backup functionality

---

**✅ All current migrations have been successfully applied to the production database.** 