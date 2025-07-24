from app import app, db

with app.app_context():
    print("Creating all tables...")
    db.create_all()
    
    print("Adding subscription columns...")
    try:
        with db.engine.connect() as conn:
            conn.execute(db.text("ALTER TABLE user ADD COLUMN subscription_tier VARCHAR(20) DEFAULT 'trial_pending'"))
            conn.commit()
            print("✅ Added subscription_tier")
    except Exception as e:
        print(f"subscription_tier: {e}")
    
    try:
        with db.engine.connect() as conn:
            conn.execute(db.text("ALTER TABLE user ADD COLUMN subscription_status VARCHAR(20) DEFAULT 'inactive'"))
            conn.commit()
            print("✅ Added subscription_status")
    except Exception as e:
        print(f"subscription_status: {e}")
        
    print("Migration done!")
