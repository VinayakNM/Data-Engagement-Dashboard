from App import create_app
from App.database import db

app = create_app()

with app.app_context():
    db.create_all()
    print("Database created successfully!")
