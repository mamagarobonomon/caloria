from app import app, db, User

with app.app_context():
    # Create test users
    users = [
        User(whatsapp_id='test123', first_name='John', last_name='Doe', subscription_status='trial_active'),
        User(whatsapp_id='test456', first_name='Jane', last_name='Smith', subscription_status='active'),
        User(whatsapp_id='test789', first_name='Bob', last_name='Wilson', subscription_status='cancelled')
    ]
    
    for user in users:
        db.session.add(user)
    
    db.session.commit()
    print(f"Created {len(users)} test users. Total: {User.query.count()}")
