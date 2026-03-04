from App.database import db
from App.models import Admin, Institution


def initialize():
    db.drop_all()
    db.create_all()

    # Default admin account
    admin = Admin(
        firstname='Admin',
        lastname='User',
        username='admin123',
        email='admin@carifin.com',
        password='Admin123!'
    )
    db.session.add(admin)

    # Sample institutions
    for name, code in [('Central Bank', 'CBTT'), ('Sagicor', 'SAGC'), ('First Citizens', 'FCBL')]:
        db.session.add(Institution(name=name, code=code))

    db.session.commit()
    print('Database initialised.')
    print('Admin login: admin@carifin.com / Admin123!')