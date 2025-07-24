from app import app, db

with app.app_context():
    print("Adding all missing subscription columns...")
    
    columns = [
        ("trial_start_time", "DATETIME"),
        ("trial_end_time", "DATETIME"),
        ("mercadopago_subscription_id", "VARCHAR(100)"),
        ("cancellation_reason", "VARCHAR(200)"),
        ("reengagement_scheduled", "DATETIME"),
        ("last_payment_date", "DATETIME")
    ]
    
    with db.engine.connect() as conn:
        for col_name, col_def in columns:
            try:
                conn.execute(db.text(f"ALTER TABLE user ADD COLUMN {col_name} {col_def}"))
                conn.commit()
                print(f"✅ Added {col_name}")
            except Exception as e:
                if "duplicate" in str(e).lower():
                    print(f"⚠️ {col_name} already exists")
                else:
                    print(f"❌ {col_name}: {e}")
    
    print("Complete migration done!")
