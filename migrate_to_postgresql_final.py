#!/usr/bin/env python3
"""
Complete migration from SQLite to PostgreSQL for Caloria
This script will:
1. Test PostgreSQL connectivity
2. Create PostgreSQL schema
3. Migrate data from SQLite
4. Verify migration success
"""

import os
import sys
import sqlite3
import subprocess
from datetime import datetime

def run_command(cmd):
    """Run a shell command and return output"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def test_postgresql_connection():
    """Test PostgreSQL connection"""
    print("🔍 Testing PostgreSQL connection...")
    
    # Test with psycopg2
    try:
        import psycopg2
        conn = psycopg2.connect(
            host="localhost",
            database="caloria_vip_db", 
            user="caloria_vip_user",
            password="temp_password_change_me"
        )
        conn.close()
        print("✅ PostgreSQL connection successful")
        return True
    except Exception as e:
        print(f"❌ PostgreSQL connection failed: {e}")
        return False

def backup_sqlite():
    """Create backup of SQLite database"""
    print("💾 Creating SQLite backup...")
    
    if not os.path.exists("instance/caloria.db"):
        print("⚠️ No SQLite database found to backup")
        return True
    
    backup_name = f"instance/caloria_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    success, stdout, stderr = run_command(f"cp instance/caloria.db {backup_name}")
    
    if success:
        print(f"✅ SQLite backup created: {backup_name}")
        return True
    else:
        print(f"❌ Backup failed: {stderr}")
        return False

def create_postgresql_schema():
    """Create PostgreSQL tables"""
    print("🏗️ Creating PostgreSQL schema...")
    
    # Override database URI to use PostgreSQL
    os.environ['DATABASE_URL'] = "postgresql://caloria_vip_user:temp_password_change_me@localhost/caloria_vip_db"
    
    # Import Flask app
    from app import app, db
    
    # Ensure we're using PostgreSQL
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL']
    
    with app.app_context():
        # Drop all tables first (clean slate)
        db.drop_all()
        print("🗑️ Dropped existing PostgreSQL tables")
        
        # Create all tables
        db.create_all()
        print("✅ PostgreSQL tables created")
        
        # Verify tables exist
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        print(f"📋 Created tables: {tables}")
        
        return len(tables) > 0

def migrate_user_data():
    """Migrate user data from SQLite to PostgreSQL"""
    print("🔄 Migrating user data...")
    
    if not os.path.exists("instance/caloria.db"):
        print("⚠️ No SQLite database found, skipping migration")
        return True
    
    # Import models
    from app import app, db, User
    
    with app.app_context():
        # Connect to SQLite
        sqlite_conn = sqlite3.connect("instance/caloria.db")
        cursor = sqlite_conn.cursor()
        
        try:
            # Get users from SQLite
            cursor.execute("SELECT * FROM user")
            sqlite_users = cursor.fetchall()
            
            # Get column names
            cursor.execute("PRAGMA table_info(user)")
            columns = [col[1] for col in cursor.fetchall()]
            
            print(f"📊 Found {len(sqlite_users)} users in SQLite")
            
            migrated = 0
            for row in sqlite_users:
                user_data = dict(zip(columns, row))
                
                # Check if user already exists in PostgreSQL
                existing = User.query.filter_by(whatsapp_id=user_data["whatsapp_id"]).first()
                if existing:
                    print(f"  ⚠️ User {user_data['whatsapp_id']} already exists, skipping")
                    continue
                
                # Create new user
                new_user = User(
                    whatsapp_id=user_data["whatsapp_id"],
                    first_name=user_data.get("first_name"),
                    last_name=user_data.get("last_name"),
                    weight=user_data.get("weight"),
                    height=user_data.get("height"),
                    age=user_data.get("age"),
                    gender=user_data.get("gender"),
                    activity_level=user_data.get("activity_level"),
                    goal=user_data.get("goal"),
                    bmr=user_data.get("bmr"),
                    daily_calorie_goal=user_data.get("daily_calorie_goal"),
                    quiz_completed=bool(user_data.get("quiz_completed", False)),
                    is_active=bool(user_data.get("is_active", True)),
                    subscription_status=user_data.get("subscription_status", "inactive"),
                    subscription_tier=user_data.get("subscription_tier", "trial_pending")
                )
                
                db.session.add(new_user)
                migrated += 1
                print(f"  ➕ Migrated user: {user_data['whatsapp_id']}")
            
            db.session.commit()
            print(f"✅ Migrated {migrated} users to PostgreSQL")
            
            return True
            
        except Exception as e:
            print(f"❌ Migration failed: {e}")
            db.session.rollback()
            return False
        finally:
            sqlite_conn.close()

def verify_migration():
    """Verify migration was successful"""
    print("🔍 Verifying migration...")
    
    from app import app, db, User
    
    with app.app_context():
        # Count users in PostgreSQL
        pg_users = User.query.count()
        print(f"📊 PostgreSQL users: {pg_users}")
        
        # Test a query
        try:
            first_user = User.query.first()
            if first_user:
                print(f"✅ Sample user: {first_user.whatsapp_id} - {first_user.first_name}")
            else:
                print("⚠️ No users found in PostgreSQL")
        except Exception as e:
            print(f"❌ Query failed: {e}")
            return False
        
        return True

def update_environment():
    """Ensure environment is properly configured"""
    print("⚙️ Checking environment configuration...")
    
    if os.path.exists(".env"):
        with open(".env", "r") as f:
            content = f.read()
            if "postgresql://" in content:
                print("✅ .env file configured for PostgreSQL")
                return True
            else:
                print("⚠️ .env file not configured for PostgreSQL")
                return False
    else:
        print("❌ .env file not found")
        return False

def main():
    """Main migration process"""
    print("🚀 Starting PostgreSQL Migration")
    print("=" * 50)
    
    # Step 1: Test PostgreSQL connection
    if not test_postgresql_connection():
        print("❌ Migration aborted: PostgreSQL connection failed")
        return False
    
    # Step 2: Backup SQLite
    if not backup_sqlite():
        print("❌ Migration aborted: Backup failed")
        return False
    
    # Step 3: Create PostgreSQL schema
    if not create_postgresql_schema():
        print("❌ Migration aborted: Schema creation failed")
        return False
    
    # Step 4: Migrate data
    if not migrate_user_data():
        print("❌ Migration failed: Data migration failed")
        return False
    
    # Step 5: Verify migration
    if not verify_migration():
        print("❌ Migration verification failed")
        return False
    
    # Step 6: Check environment
    if not update_environment():
        print("⚠️ Environment configuration needs attention")
    
    print("\n" + "=" * 50)
    print("🎉 PostgreSQL Migration Complete!")
    print("📊 Data successfully migrated")
    print("🔄 Application ready for PostgreSQL")
    print("\n🚨 IMPORTANT: Restart the application to use PostgreSQL")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 