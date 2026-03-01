# seed.py
from App import create_app
from App.database import db
from App.models import Institution, Admin, HR, Scorer, PulseLeader
from datetime import datetime

def seed():
    app = create_app()
    with app.app_context():
        print("Seeding database...")

        # ---------- INSTITUTIONS ----------
        institutions = [
            ('Central Bank of Trinidad and Tobago', 'CBTT'),
            ('First Citizens Bank', 'FCIT'),
            ('Sagicor', 'SAGC'),
            ('Scotiabank', 'SCOT'),
            ('TT Mortgage Bank', 'TTMB'),
            ('TTUTC', 'TTUT'),
            ('Ministry of Finance', 'MOF'),
        ]
        for name, code in institutions:
            inst = Institution.query.filter_by(code=code).first()
            if not inst:
                inst = Institution(name=name, code=code)
                
                db.session.add(inst)
                print(f"  + Institution: {name} ({code})")
        db.session.commit()

        # Get institution IDs for later
        cbtt = Institution.query.filter_by(code='CBTT').first()
        fcit = Institution.query.filter_by(code='FCIT').first()

        # ---------- ADMIN ----------
        if not Admin.query.filter_by(email='admin@carifin.com').first():
            admin = Admin(
                firstname='Admin',
                lastname='User',
                username='admin',
                email='admin@carifin.com',
                password='Admin123!'
            )
            db.session.add(admin)
            print("  + Admin: admin@carifin.com / Admin123!")
        else:
            print("  - Admin already exists")

        # ---------- HR ----------
        if not HR.query.filter_by(email='hr@cbtt.com').first():
            hr = HR(
                firstname='HR',
                lastname='CBTT',
                username='hr_cbtt',
                email='hr@cbtt.com',
                password='Hr123!',
                institution_id=cbtt.id
            )
            db.session.add(hr)
            print("  + HR: hr@cbtt.com / Hr123! (CBTT)")
        else:
            print("  - HR already exists")

        # ---------- SCORER ----------
        if not Scorer.query.filter_by(email='scorer@carifin.com').first():
            scorer = Scorer(
                firstname='Scorer',
                lastname='User',
                username='scorer',
                email='scorer@carifin.com',
                password='Scorer123!'
            )
            db.session.add(scorer)
            print("  + Scorer: scorer@carifin.com / Scorer123!")
        else:
            print("  - Scorer already exists")

        # ---------- PULSE LEADER ----------
        if not PulseLeader.query.filter_by(email='pulse@cbtt.com').first():
            pulse = PulseLeader(
                firstname='Pulse',
                lastname='Leader',
                username='pulse_cbtt',
                email='pulse@cbtt.com',
                password='Pulse123!',
                institution_id=cbtt.id
            )
            pulse.social_media_handle = '@CBTT_Pulse'  # optional field
            db.session.add(pulse)
            print("  + PulseLeader: pulse@cbtt.com / Pulse123! (CBTT)")
        else:
            print("  - PulseLeader already exists")

        # (Optional) Create a second HR for another institution
        if not HR.query.filter_by(email='hr@fcit.com').first():
            hr2 = HR(
                firstname='HR2',
                lastname='FCIT',
                username='hr_fcit',
                email='hr@fcit.com',
                password='Hr123!',
                institution_id=fcit.id
            )
            db.session.add(hr2)
            print("  + HR: hr@fcit.com / Hr123! (FCIT)")

        db.session.commit()
        print("Seeding complete!")

if __name__ == '__main__':
    seed()