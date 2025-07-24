#!/usr/bin/env python3
"""
Database Migration Script for Caloria Subscription Functionality
Run this script to add subscription tables and fields to existing database.

Usage:
    python migrate_subscription_db.py
"""

import os
import sys
from datetime import datetime

# Add the current directory to Python path to import app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, User, Subscription, PaymentTransaction, TrialActivity, ReengagementSchedule

def backup_database():
    """Create a backup of the current database"""
    try:
        if 'sqlite' in app.config['SQLALCHEMY_DATABASE_URI']:
            # SQLite backup
            import shutil
            db_uri = app.config['SQLALCHEMY_DATABASE_URI']
            
            # Handle different SQLite URI formats
            if db_uri.startswith('sqlite:///'):
                db_path = db_uri.replace('sqlite:///', '')
            elif db_uri.startswith('sqlite://'):
                db_path = db_uri.replace('sqlite://', '')
            else:
                db_path = 'caloria.db'  # fallback
            
            # If path is relative, it might be in instance directory
            if not os.path.isabs(db_path) and not os.path.exists(db_path):
                # Check if it's in instance directory
                instance_path = os.path.join('instance', db_path)
                if os.path.exists(instance_path):
                    db_path = instance_path
            
            if not os.path.exists(db_path):
                print(f"⚠️ Database file not found at: {db_path}")
                print("⚠️ Continuing without backup (new database will be created)")
                return True
            
            backup_path = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            shutil.copy2(db_path, backup_path)
            print(f"✅ Database backed up to: {backup_path}")
        else:
            print("⚠️ PostgreSQL detected - please create manual backup before proceeding")
            response = input("Have you created a backup? (y/N): ")
            if response.lower() != 'y':
                print("❌ Migration cancelled. Please create a backup first.")
                return False
        return True
    except Exception as e:
        print(f"❌ Error creating backup: {str(e)}")
        return False

def test_database_connection():
    """Test database connection using raw SQL to avoid model column issues"""
    try:
        with app.app_context():
            # Use raw SQL to avoid model issues during migration
            with db.engine.connect() as connection:
                result = connection.execute(db.text("SELECT COUNT(*) FROM user"))
                user_count = result.fetchone()[0]
                print(f"✅ Database connection OK. Found {user_count} existing users.")
            return True
    except Exception as e:
        print(f"❌ Database connection failed: {str(e)}")
        return False

def run_migration():
    """Run the database migration"""
    try:
        with app.app_context():
            print("🔄 Creating new tables...")
            
            # Create all tables (will only create missing ones)
            db.create_all()
            
            print("✅ All subscription tables created successfully!")
            
            # Add new columns to existing User table
            print("🔄 Adding subscription columns to User table...")
            
            with db.engine.connect() as connection:
                # List of new columns to add to User table
                user_columns = [
                    ("subscription_tier", "VARCHAR(20) DEFAULT 'trial_pending'"),
                    ("subscription_status", "VARCHAR(20) DEFAULT 'inactive'"),
                    ("trial_start_time", "DATETIME"),
                    ("trial_end_time", "DATETIME"),
                    ("mercadopago_subscription_id", "VARCHAR(100)"),
                    ("cancellation_reason", "VARCHAR(200)"),
                    ("reengagement_scheduled", "DATETIME"),
                    ("last_payment_date", "DATETIME")
                ]
                
                for column_name, column_def in user_columns:
                    try:
                        # Try to add the column
                        alter_sql = db.text(f"ALTER TABLE user ADD COLUMN {column_name} {column_def}")
                        connection.execute(alter_sql)
                        print(f"  ✅ Added column: {column_name}")
                    except Exception as e:
                        if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                            print(f"  ⚠️ Column {column_name} already exists, skipping")
                        else:
                            print(f"  ❌ Error adding column {column_name}: {str(e)}")
                            return False
            
            print("✅ User table updated successfully!")
            
            # Test the new tables
            print("🔍 Testing new tables...")
            
            # Test new tables using raw SQL to avoid model issues
            with db.engine.connect() as connection:
                # Test Subscription table
                result = connection.execute(db.text("SELECT COUNT(*) FROM subscription"))
                subscription_count = result.fetchone()[0]
                print(f"  📋 Subscription table: {subscription_count} records")
                
                # Test PaymentTransaction table  
                result = connection.execute(db.text("SELECT COUNT(*) FROM payment_transaction"))
                transaction_count = result.fetchone()[0]
                print(f"  💳 PaymentTransaction table: {transaction_count} records")
                
                # Test TrialActivity table
                result = connection.execute(db.text("SELECT COUNT(*) FROM trial_activity"))
                activity_count = result.fetchone()[0]
                print(f"  📊 TrialActivity table: {activity_count} records")
                
                # Test ReengagementSchedule table
                result = connection.execute(db.text("SELECT COUNT(*) FROM reengagement_schedule"))
                reengagement_count = result.fetchone()[0]
                print(f"  🔔 ReengagementSchedule table: {reengagement_count} records")
                
                # Test new User columns
                result = connection.execute(db.text("SELECT subscription_tier, subscription_status FROM user LIMIT 1"))
                user_row = result.fetchone()
                if user_row:
                    print(f"  👤 User columns working: tier={user_row[0]}, status={user_row[1]}")
            
            print("✅ Migration completed successfully!")
            return True
            
    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        return False

def update_existing_users():
    """Update existing users with default subscription values"""
    try:
        with app.app_context():
            # Use raw SQL to avoid model issues during migration
            with db.engine.connect() as connection:
                # Update existing users with default subscription values
                update_sql = db.text("""
                UPDATE user SET 
                    subscription_tier = 'trial_pending',
                    subscription_status = 'inactive'
                WHERE subscription_tier IS NULL OR subscription_status IS NULL
                """)
                result = connection.execute(update_sql)
                updated_count = result.rowcount
                print(f"✅ Updated {updated_count} existing users with default subscription values")
            return True
            
    except Exception as e:
        print(f"❌ Error updating existing users: {str(e)}")
        return False

def verify_migration():
    """Verify the migration was successful"""
    try:
        with app.app_context():
            # Check tables exist using raw SQL
            with db.engine.connect() as connection:
                # Check if new tables exist
                tables_to_check = ['subscription', 'payment_transaction', 'trial_activity', 'reengagement_schedule']
                
                for table_name in tables_to_check:
                    try:
                        result = connection.execute(db.text(f"SELECT COUNT(*) FROM {table_name}"))
                        count = result.fetchone()[0]
                        print(f"  ✅ Table '{table_name}' exists with {count} records")
                    except Exception as e:
                        print(f"  ❌ Table '{table_name}' missing or error: {str(e)}")
                        return False
                
                # Check if user table has new columns
                try:
                    result = connection.execute(db.text("SELECT subscription_tier, subscription_status FROM user LIMIT 1"))
                    print("  ✅ User table has new subscription columns")
                except Exception as e:
                    print(f"  ❌ User table missing subscription columns: {str(e)}")
                    return False
                
                print("✅ Migration verification completed successfully!")
                return True
            
    except Exception as e:
        print(f"❌ Migration verification failed: {str(e)}")
        return False

def main():
    """Main migration function"""
    print("🚀 Caloria Subscription Database Migration")
    print("=" * 50)
    
    # Step 1: Test database connection
    print("1. Testing database connection...")
    if not test_database_connection():
        return False
    
    # Step 2: Create backup
    print("\n2. Creating database backup...")
    if not backup_database():
        return False
    
    # Step 3: Run migration
    print("\n3. Running migration...")
    if not run_migration():
        return False
    
    # Step 4: Update existing users
    print("\n4. Updating existing users...")
    if not update_existing_users():
        return False
    
    # Step 5: Verify migration
    print("\n5. Verifying migration...")
    if not verify_migration():
        return False
    
    print("\n" + "=" * 50)
    print("🎉 MIGRATION COMPLETED SUCCESSFULLY!")
    print("\n📋 Next steps:")
    print("1. Set up environment variables for Mercado Pago")
    print("2. Test the subscription API endpoints")
    print("3. Configure ManyChat flows")
    print("4. Test the complete user journey")
    
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        print("\n❌ Migration failed. Please check the errors above.")
        sys.exit(1)
    else:
        print("\n✅ Migration successful!")
        sys.exit(0) 