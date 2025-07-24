# 🗄️ Database Configuration Guide for Caloria

**Complete guide for database setup, migration, and maintenance**

---

## 📊 **Database Overview**

### **Current Configuration**
- **Development**: SQLite (automatic, no setup required)
- **Production**: PostgreSQL (configured and validated)
- **Migration**: Automated scripts available
- **Backup**: Daily automated backups with 7-day retention

---

## 🏗️ **Database Architecture**

### **Environment-Specific Setup**

| Environment | Database | Configuration | Status |
|-------------|----------|---------------|--------|
| **Local Development** | SQLite | `sqlite:///caloria.db` | ✅ **Automatic** |
| **Production** | PostgreSQL | `postgresql://caloria_vip_user:password@localhost/caloria_vip_db` | ✅ **Configured** |
| **Testing** | SQLite | In-memory or temporary | ✅ **Automatic** |

### **Key Features Implemented**
- ✅ **Environment validation** on startup
- ✅ **Database health monitoring** via `/health/database`
- ✅ **Automated backups** with integrity verification
- ✅ **Migration scripts** for schema updates
- ✅ **Connection stability** improvements

---

## 🔧 **Configuration Instructions**

### **Local Development Setup**

**No configuration needed!** The application automatically uses SQLite for local development.

```bash
# Clone repository
git clone <repository-url>
cd Caloria

# Install dependencies
pip install -r requirements.txt

# Run application (SQLite will be created automatically)
python app.py
```

**Environment Variables (Optional)**:
```bash
# Default configuration (automatic)
DATABASE_URL=sqlite:///caloria.db

# Custom SQLite location
DATABASE_URL=sqlite:///path/to/custom.db
```

### **Production Setup (PostgreSQL)**

**1. PostgreSQL Installation & Setup**
```bash
# Install PostgreSQL
sudo apt update
sudo apt install postgresql postgresql-contrib

# Create database and user
sudo -u postgres psql
CREATE DATABASE caloria_vip_db;
CREATE USER caloria_vip_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE caloria_vip_db TO caloria_vip_user;
\q
```

**2. Environment Configuration**
```bash
# Production .env file
DATABASE_URL=postgresql://caloria_vip_user:your_secure_password@localhost/caloria_vip_db
SECRET_KEY=your_production_secret_key
FLASK_ENV=production
```

**3. Application Deployment**
```bash
# Deploy and start application
python app.py

# Verify database connection
curl https://your-domain.com/health/database
```

---

## 🔄 **Migration & Data Transfer**

### **SQLite to PostgreSQL Migration**

**Automatic Migration Script**: `migrate_to_postgresql_final.py`

```bash
# Run comprehensive migration
python migrate_to_postgresql_final.py
```

**What the script does**:
1. ✅ Tests PostgreSQL connectivity
2. ✅ Creates backup of SQLite data
3. ✅ Creates PostgreSQL schema
4. ✅ Migrates all user data
5. ✅ Verifies data integrity
6. ✅ Updates environment configuration

### **Manual Migration Steps**

**1. Backup Current Data**
```bash
# SQLite backup
cp caloria.db caloria_backup_$(date +%Y%m%d).db

# Export data
sqlite3 caloria.db .dump > caloria_export.sql
```

**2. Prepare PostgreSQL**
```bash
# Create tables
python -c "from app import app, db; app.app_context().push(); db.create_all()"

# Verify tables
python -c "from app import app, db; app.app_context().push(); print(db.engine.table_names())"
```

**3. Data Transfer**
```bash
# Admin user is automatically created when app starts
# No manual action needed

# Verify migration
curl http://localhost:5000/health/database
```

---

## 📋 **Database Schema**

### **Core Tables**

| Table | Purpose | Key Relationships |
|-------|---------|-------------------|
| `user` | User profiles and settings | Core entity |
| `food_log` | Food intake records | `user.id` → `food_log.user_id` |
| `daily_stats` | Daily aggregated statistics | `user.id` → `daily_stats.user_id` |
| `admin_user` | Admin panel access | Independent |
| `subscription` | Subscription management | `user.id` → `subscription.user_id` |
| `payment_transaction` | Payment history | `user.id` → `payment_transaction.user_id` |
| `trial_activity` | Trial period tracking | `user.id` → `trial_activity.user_id` |
| `system_activity_log` | System events | `user.id` → `system_activity_log.user_id` |

### **Database Size Estimates**

| Users | SQLite Size | PostgreSQL Size | Recommended |
|-------|-------------|-----------------|-------------|
| 1-100 | < 10 MB | < 5 MB | SQLite OK |
| 100-1,000 | 10-100 MB | 5-50 MB | PostgreSQL recommended |
| 1,000+ | 100+ MB | 50+ MB | PostgreSQL required |

---

## 🛡️ **Backup & Recovery**

### **Automated Backup System**

**Current Setup**:
- 📅 **Schedule**: Daily at 2:00 AM
- 📁 **Location**: `/var/backups/caloria/`
- ⏰ **Retention**: 7 days
- 🗜️ **Compression**: gzip format
- ✅ **Integrity**: Automatically verified

**Backup Script**: `/var/www/caloria/backup_script.sh`

```bash
# Manual backup
sudo -u caloria /var/www/caloria/backup_script.sh

# View backup logs
cat /var/www/caloria/logs/backup.log

# List backups
ls -la /var/backups/caloria/
```

### **Recovery Procedures**

**From Automated Backup**:
```bash
# List available backups
ls -la /var/backups/caloria/

# Restore from backup
zcat /var/backups/caloria/caloria_YYYYMMDD_HHMMSS.sql.gz | psql -d caloria_vip_db
```

**From Manual Backup**:
```bash
# SQLite backup
cp caloria_backup_YYYYMMDD.db caloria.db

# PostgreSQL backup
psql -d caloria_vip_db < backup_file.sql
```

---

## 🔍 **Monitoring & Health Checks**

### **Health Endpoints**

**Database Health**: `GET /health/database`
```json
{
    "database": "POSTGRESQL",
    "status": "healthy",
    "timestamp": "2025-07-24T20:35:42.578586",
    "user_count": 3
}
```

**General Health**: `GET /health`
```json
{
    "status": "healthy",
    "application": "Caloria",
    "timestamp": "2025-07-24T20:35:42.578586"
}
```

### **Monitoring Commands**

```bash
# Check database connection
curl https://caloria.vip/health/database

# Monitor logs
tail -f /var/www/caloria/logs/gunicorn.log

# Check backup status
cat /var/www/caloria/logs/backup.log | tail -10

# Database size monitoring
du -h /var/lib/postgresql/data/
```

---

## 🚨 **Troubleshooting**

### **Common Issues**

#### **"Database connection failed" errors**

**Symptoms**: Application startup errors, health check failures

**Solutions**:
```bash
# 1. Verify DATABASE_URL is set
grep DATABASE_URL /var/www/caloria/.env

# 2. Test PostgreSQL connection
sudo -u postgres psql -d caloria_vip_db -c "SELECT 1;"

# 3. Check application logs
tail -20 /var/www/caloria/logs/gunicorn.log

# 4. Restart PostgreSQL
sudo systemctl restart postgresql
```

#### **"SQLite file not found" errors**

**Symptoms**: Local development issues

**Solutions**:
```bash
# 1. Ensure directory exists
mkdir -p instance

# 2. Create database
python -c "from app import app, db; app.app_context().push(); db.create_all()"

# 3. Check file permissions
ls -la caloria.db
```

#### **"Admin user not found" errors**

**Symptoms**: Admin login fails with 500 error

**Solutions**:
```bash
# 1. Admin user is automatically created by app.py
# Check if admin exists:

# 2. Verify admin exists
python -c "from app import AdminUser; print(AdminUser.query.count())"
```

### **Emergency Recovery**

**Database Corruption**:
1. Stop application: `sudo pkill -f gunicorn`
2. Restore from backup: `zcat /var/backups/caloria/latest.sql.gz | psql -d caloria_vip_db`
3. Restart application: `sudo -u caloria ./deploy.sh`

**Complete Reset**:
1. Backup current data: `python migrate_to_postgresql_final.py`
2. Drop database: `sudo -u postgres dropdb caloria_vip_db`
3. Recreate: `sudo -u postgres createdb caloria_vip_db`
4. Restore: Run migration script

---

## 📈 **Performance Optimization**

### **Database Tuning**

**PostgreSQL Configuration**:
```bash
# /etc/postgresql/*/main/postgresql.conf
shared_buffers = 256MB
effective_cache_size = 1GB
maintenance_work_mem = 64MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
```

**Index Optimization**:
```sql
-- Add indexes for frequently queried columns
CREATE INDEX idx_user_whatsapp_id ON user(whatsapp_id);
CREATE INDEX idx_food_log_user_date ON food_log(user_id, created_at);
CREATE INDEX idx_daily_stats_user_date ON daily_stats(user_id, date);
```

### **Connection Management**

**Connection Pooling** (for high traffic):
```python
# app.py configuration
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_size': 20,
    'pool_recycle': 3600,
    'pool_pre_ping': True
}
```

---

## 🔮 **Future Considerations**

### **Scaling Options**

| User Count | Recommendation | Implementation |
|------------|----------------|----------------|
| 1-1,000 | Single PostgreSQL | Current setup |
| 1,000-10,000 | Read replicas | Add replica servers |
| 10,000+ | Sharding/Clustering | Database cluster |

### **Backup Improvements**

- Point-in-time recovery (WAL archiving)
- Offsite backup storage (cloud storage)
- Real-time replication
- Automated recovery testing

---

## 📞 **Support & Resources**

### **Quick Reference**

| Task | Command |
|------|---------|
| **Health Check** | `curl https://caloria.vip/health/database` |
| **Manual Backup** | `sudo -u caloria /var/www/caloria/backup_script.sh` |
| **View Logs** | `tail -f /var/www/caloria/logs/backup.log` |
| **Migration** | `python migrate_to_postgresql_final.py` |
| **Admin User** | Automatically created by app.py |

### **Contact Information**

- **Documentation**: This guide and `DOCUMENTATION_INDEX.md`
- **Health Monitoring**: `/health/database` endpoint
- **Backup Location**: `/var/backups/caloria/`
- **Log Files**: `/var/www/caloria/logs/`

---

**✅ Database configuration is now production-ready with automated backups, health monitoring, and comprehensive documentation.** 