# seed.py
from App import create_app
from App.database import db
from App.models import Institution, Admin, HR, Scorer, PulseLeader, Season, Event, SeasonEvent, Stage
from datetime import datetime, date

def seed():
    app = create_app()
    with app.app_context():
        print("Seeding database...")

        db.create_all()
        print(" + Tables created!")

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

        # ---------- SEASONS ----------
        seasons = [
            (2026, 'CariFin Games 2026 - 35th Anniversary'),
            (2025, 'CariFin Games 2025'),
            (2024, 'CariFin Games 2024'),
        ]
        for year, desc in seasons:
            season = Season.query.filter_by(year=year).first()
            if not season:
                season = Season(year=year, description=desc)
                db.session.add(season)
                print(f"  + Season: {year}")
        db.session.commit()

        # Get current season (2026)
        current_season = Season.query.filter_by(year=2026).first()

        # ---------- EVENTS ----------
        events = [
            ('Urban Challenge', 'Multi-stage running event across 5 locations', 'run'),
            ('Cross Country', 'Single day cross country race', 'run'),
            ('Corporate Relay', 'Team relay event', 'run'),
        ]
        for name, desc, etype in events:
            event = Event.query.filter_by(name=name).first()
            if not event:
                event = Event(name=name, description=desc, event_type=etype)
                db.session.add(event)
                print(f"  + Event: {name}")
        db.session.commit()

        # Get event IDs
        urban = Event.query.filter_by(name='Urban Challenge').first()
        cross = Event.query.filter_by(name='Cross Country').first()
        relay = Event.query.filter_by(name='Corporate Relay').first()

        # ---------- SEASON-EVENT BRIDGE ----------
        if current_season:
            # Link Urban Challenge to 2026 season
            if not SeasonEvent.query.filter_by(season_id=current_season.id, event_id=urban.id).first():
                se_urban = SeasonEvent(
                    season_id=current_season.id,
                    event_id=urban.id,
                    start_date=date(2026, 3, 1),
                    end_date=date(2026, 4, 30)
                )
                db.session.add(se_urban)
                print(f"  + Linked Urban Challenge to 2026 season")

            # Link Cross Country to 2026 season
            if not SeasonEvent.query.filter_by(season_id=current_season.id, event_id=cross.id).first():
                se_cross = SeasonEvent(
                    season_id=current_season.id,
                    event_id=cross.id,
                    start_date=date(2026, 10, 15),
                    end_date=date(2026, 10, 15)
                )
                db.session.add(se_cross)
                print(f"  + Linked Cross Country to 2026 season")

            # Link Corporate Relay to 2026 season (optional)
            if relay and not SeasonEvent.query.filter_by(season_id=current_season.id, event_id=relay.id).first():
                se_relay = SeasonEvent(
                    season_id=current_season.id,
                    event_id=relay.id,
                    start_date=date(2026, 5, 20),
                    end_date=date(2026, 5, 20)
                )
                db.session.add(se_relay)
                print(f"  + Linked Corporate Relay to 2026 season")
        
        db.session.commit()

        # ---------- STAGES for Urban Challenge ----------
        if current_season and urban:
            se_urban = SeasonEvent.query.filter_by(
                season_id=current_season.id, 
                event_id=urban.id
            ).first()
            
            if se_urban:
                stages = [
                    (1, "5K", "Queen's Park Savannah", date(2026, 3, 1)),
                    (2, "5K", "Brian Lara Promenade", date(2026, 3, 8)),
                    (3, "3K", "Hasely Crawford Stadium", date(2026, 3, 15)),
                    (4, "5K", "Mucurapo", date(2026, 3, 22)),
                    (5, "3K", "Chaguanas", date(2026, 3, 29)),
                ]
                
                for stage_num, distance, location, stage_date in stages:
                    existing = Stage.query.filter_by(
                        season_event_id=se_urban.id,
                        stage_number=stage_num
                    ).first()
                    
                    if not existing:
                        stage = Stage(
                            season_event_id=se_urban.id,
                            stage_number=stage_num,
                            location=location,
                            stage_date=stage_date
                        )
                        db.session.add(stage)
                        print(f"  + Stage {stage_num}: {location}")

        db.session.commit()

        # ---------- USERS ----------
        # ADMIN
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

        # HR for CBTT
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

        # HR for FCIT
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

        # SCORER
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

        # PULSE LEADER
        if not PulseLeader.query.filter_by(email='pulse@cbtt.com').first():
            pulse = PulseLeader(
                firstname='Pulse',
                lastname='Leader',
                username='pulse_cbtt',
                email='pulse@cbtt.com',
                password='Pulse123!',
                institution_id=cbtt.id
            )
            pulse.social_media_handle = '@CBTT_Pulse'
            db.session.add(pulse)
            print("  + PulseLeader: pulse@cbtt.com / Pulse123! (CBTT)")
        else:
            print("  - PulseLeader already exists")

        db.session.commit()
        print("Seeding complete!")

if __name__ == '__main__':
    seed()