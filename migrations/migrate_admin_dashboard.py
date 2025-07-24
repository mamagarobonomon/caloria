#!/usr/bin/env python3
"""
Database Migration: Admin Dashboard Updates
- Add SystemActivityLog table
- Migrate existing quiz/registration events if possible
- Test subscription analytics queries

This migration ensures the admin dashboard has all necessary tables and data
for displaying subscription analytics and separate system activity logs.
"""

import os
import sys
import sqlite3
import json
from datetime import datetime

def setup_app():
    """Setup Flask app for migration"""
    try:
        # Add the project root to Python path
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        
        # Import Flask app
        from app import app, db
        
        return app, db
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure you're running this from the project root directory")
        return None, None

def test_database_connection():
    """Test database connection"""
    try:
        app, db = setup_app()
        if not app:
            return False
            
        with app.app_context():
            # Test connection with raw SQL to avoid model issues
            with db.engine.connect() as connection:
                result = connection.execute(db.text("SELECT COUNT(*) FROM user"))
                user_count = result.scalar()
                print(f"✅ Database connection successful - {user_count} users found")
                return True
                
    except Exception as e:
        print(f"❌ Database connection failed: {str(e)}")
        return False

def backup_database():
    """Create backup of current database"""
    try:
        # Determine database file path
        db_path = 'instance/caloria.db'
        if not os.path.exists(db_path):
            db_path = 'caloria.db'
            if not os.path.exists(db_path):
                print("⚠️ Database file not found, assuming fresh installation")
                return True
        
        backup_path = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Copy database file
        import shutil
        shutil.copy2(db_path, backup_path)
        print(f"✅ Database backed up to: {backup_path}")
        return True
        
    except Exception as e:
        print(f"❌ Backup failed: {str(e)}")
        return False

def run_migration():
    """Run the database migration"""
    try:
        app, db = setup_app()
        if not app:
            return False
            
        with app.app_context():
            print("🔄 Creating SystemActivityLog table...")
            
            # Create all tables (will only create missing ones)
            db.create_all()
            
            print("✅ SystemActivityLog table created successfully!")
            
            # Test the new table
            with db.engine.connect() as connection:
                result = connection.execute(db.text("SELECT COUNT(*) FROM system_activity_log"))
                activity_count = result.scalar()
                print(f"✅ SystemActivityLog table accessible - {activity_count} activities found")
            
            return True
            
    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        return False

def migrate_existing_data():
    """Migrate existing quiz/registration data to SystemActivityLog if possible"""
    try:
        app, db = setup_app()
        if not app:
            return False
            
        with app.app_context():
            from app import User, SystemActivityLog
            
            print("🔄 Migrating existing user data to system activity log...")
            
            users_with_completed_quiz = User.query.filter_by(quiz_completed=True).all()
            migration_count = 0
            
            for user in users_with_completed_quiz:
                # Check if we already have a quiz_completed activity for this user
                existing_activity = SystemActivityLog.query.filter_by(
                    user_id=user.id,
                    activity_type='quiz_completed'
                ).first()
                
                if not existing_activity:
                    # Create quiz completion activity
                    SystemActivityLog.log_activity(
                        user_id=user.id,
                        activity_type='quiz_completed',
                        activity_data={
                            'goal': user.goal,
                            'bmr': user.bmr,
                            'daily_calorie_goal': user.daily_calorie_goal,
                            'migrated': True,
                            'completion_time': user.created_at.isoformat() if user.created_at else datetime.utcnow().isoformat()
                        }
                    )
                    migration_count += 1
            
            print(f"✅ Migrated {migration_count} quiz completion activities")
            
            # Migrate registration activities for all users
            all_users = User.query.all()
            registration_count = 0
            
            for user in all_users:
                # Check if we already have a registration activity for this user
                existing_registration = SystemActivityLog.query.filter_by(
                    user_id=user.id,
                    activity_type='registration'
                ).first()
                
                if not existing_registration:
                    # Create registration activity
                    SystemActivityLog.log_activity(
                        user_id=user.id,
                        activity_type='registration',
                        activity_data={
                            'source': 'migration',
                            'platform': 'telegram',
                            'migrated': True,
                            'registration_time': user.created_at.isoformat() if user.created_at else datetime.utcnow().isoformat()
                        }
                    )
                    registration_count += 1
            
            print(f"✅ Migrated {registration_count} registration activities")
            return True
            
    except Exception as e:
        print(f"❌ Data migration failed: {str(e)}")
        return False

def test_admin_dashboard_queries():
    """Test all queries used by the admin dashboard"""
    try:
        app, db = setup_app()
        if not app:
            return False
            
        with app.app_context():
            from app import User, FoodLog, SystemActivityLog
            
            print("🔄 Testing admin dashboard queries...")
            
            # Test basic statistics
            total_users = User.query.count()
            active_users = User.query.filter_by(is_active=True).count()
            completed_quizzes = User.query.filter_by(quiz_completed=True).count()
            total_food_logs = FoodLog.query.count()
            
            print(f"✅ Basic stats: {total_users} users, {active_users} active, {completed_quizzes} quizzes, {total_food_logs} food logs")
            
            # Test subscription statistics
            trial_pending = User.query.filter_by(subscription_tier='trial_pending').count()
            trial_active = User.query.filter_by(subscription_tier='trial_active').count()
            paid_subscribers = User.query.filter_by(subscription_tier='active').count()
            cancelled_subs = User.query.filter_by(subscription_tier='cancelled').count()
            
            print(f"✅ Subscription stats: {trial_pending} pending, {trial_active} trial, {paid_subscribers} paid, {cancelled_subs} cancelled")
            
            # Test recent data queries
            recent_food_logs = FoodLog.query.join(User).order_by(FoodLog.created_at.desc()).limit(15).all()
            recent_activities = SystemActivityLog.query.join(User).order_by(SystemActivityLog.created_at.desc()).limit(15).all()
            
            print(f"✅ Recent data: {len(recent_food_logs)} food logs, {len(recent_activities)} system activities")
            
            # Test conversion rates
            quiz_completion_rate = (completed_quizzes / total_users * 100) if total_users > 0 else 0
            trial_conversion_rate = (trial_active / completed_quizzes * 100) if completed_quizzes > 0 else 0
            paid_conversion_rate = (paid_subscribers / trial_active * 100) if trial_active > 0 else 0
            
            print(f"✅ Conversion rates: Quiz {quiz_completion_rate:.1f}%, Trial {trial_conversion_rate:.1f}%, Paid {paid_conversion_rate:.1f}%")
            
            return True
            
    except Exception as e:
        print(f"❌ Dashboard query testing failed: {str(e)}")
        return False

def verify_migration():
    """Verify the migration was successful"""
    try:
        app, db = setup_app()
        if not app:
            return False
            
        with app.app_context():
            from app import SystemActivityLog
            
            print("🔄 Verifying migration...")
            
            # Check SystemActivityLog table exists and has data
            activity_count = SystemActivityLog.query.count()
            print(f"✅ SystemActivityLog table has {activity_count} activities")
            
            # Check activity types
            activity_types = db.session.query(SystemActivityLog.activity_type).distinct().all()
            activity_types = [t[0] for t in activity_types]
            print(f"✅ Activity types found: {activity_types}")
            
            # Test recent activities query
            recent = SystemActivityLog.query.order_by(SystemActivityLog.created_at.desc()).limit(5).all()
            print(f"✅ Recent activities query works: {len(recent)} activities")
            
            return True
            
    except Exception as e:
        print(f"❌ Migration verification failed: {str(e)}")
        return False

def main():
    """Main migration function"""
    print("🚀 Starting Admin Dashboard Migration")
    print("=" * 50)
    
    # Step 1: Test database connection
    print("\n📋 Step 1: Testing database connection")
    if not test_database_connection():
        print("❌ Migration aborted due to connection issues")
        return False
    
    # Step 2: Backup database
    print("\n📋 Step 2: Backing up database")
    if not backup_database():
        print("❌ Migration aborted due to backup failure")
        return False
    
    # Step 3: Run migration
    print("\n📋 Step 3: Running database migration")
    if not run_migration():
        print("❌ Migration failed")
        return False
    
    # Step 4: Migrate existing data
    print("\n📋 Step 4: Migrating existing data")
    if not migrate_existing_data():
        print("⚠️ Data migration had issues, but continuing...")
    
    # Step 5: Test dashboard queries
    print("\n📋 Step 5: Testing admin dashboard queries")
    if not test_admin_dashboard_queries():
        print("⚠️ Dashboard query testing had issues, but continuing...")
    
    # Step 6: Verify migration
    print("\n📋 Step 6: Verifying migration")
    if not verify_migration():
        print("❌ Migration verification failed")
        return False
    
    print("\n" + "=" * 50)
    print("✅ Admin Dashboard Migration Complete!")
    print("🎯 SystemActivityLog table created")
    print("📊 Subscription analytics ready")
    print("🔄 System activities separated from food logs")
    print("🚀 Admin dashboard updated with new features")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 