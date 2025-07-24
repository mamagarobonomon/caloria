#!/usr/bin/env python3
"""Create admin user in PostgreSQL database"""

from app import app, db, AdminUser

def create_admin_user():
    with app.app_context():
        # Check if admin user already exists
        existing_admin = AdminUser.query.filter_by(username="admin").first()
        
        if existing_admin:
            print("✅ Admin user already exists")
            print(f"Username: {existing_admin.username}")
            print(f"Email: {existing_admin.email}")
            print(f"Active: {existing_admin.is_active}")
        else:
            print("Creating new admin user...")
            
            # Create new admin user
            admin = AdminUser(
                username="admin",
                email="admin@caloria.com",
                is_active=True
            )
            admin.set_password("admin123")  # Default password
            
            db.session.add(admin)
            db.session.commit()
            
            print("✅ Admin user created successfully!")
            print("Username: admin")
            print("Password: admin123")
            print("Email: admin@caloria.com")

if __name__ == "__main__":
    create_admin_user() 