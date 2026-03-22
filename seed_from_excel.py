import os, sys
from datetime import datetime, date

sys.path.insert(0, os.path.dirname(__file__))
from App import create_app
from App.database import db

app = create_app()

# Excel team name → your exact institution code in the database
TEAM_MAP = {
    'CBTT':            'CBTT',
    'FIRST CITIZENS':  'FCIT',
    'FCB':             'FCIT',
    'SAGICOR':         'SAGC',
    'SCOTIABANK':      'SCOT',
    'SCOTIA':          'SCOT',
    'TTMB':            'TTMB',
    'TTUTC':           'TTUT',
    'UTC':             'TTUT',
    'MIN. OF FINANCE': 'MOF',
}

# Your exact event name in the database
EVENT_NAME = 'Urban Challenge'

def parse_date(val):
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    s = str(val).strip()
    for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y'):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None

with app.app_context():
    try:
        import pandas as pd
    except ImportError:
        print("pandas not installed. Run: pip install pandas openpyxl --break-system-packages")
        sys.exit(1)

    from App.models import (
        Institution, Participant, Season, Event,
        SeasonEvent, Stage, Registration, Result
    )

    print("Reading Excel file...")
    df = pd.read_excel('registration_list.xlsx')
    df = df[df['TEAM NAME'].notna() & df['FIRST NAME'].notna() & df['LAST NAME'].notna()]
    print(f"  {len(df)} rows loaded")

    # ── 1. Look up existing institutions by code ──────────────────────────────
    print("\nLooking up institutions...")
    inst_cache = {}  # code -> Institution object
    for team, code in TEAM_MAP.items():
        if code in inst_cache:
            continue
        inst = Institution.query.filter_by(code=code).first()
        if inst:
            inst_cache[code] = inst
            print(f"  ✓ Found: {code} — {inst.name}")
        else:
            print(f"  ✗ NOT FOUND in DB: {code} — add this institution first via the admin form")

    # ── 2. Look up existing season ────────────────────────────────────────────
    print("\nLooking up season...")
    season = Season.query.filter_by(status='active').order_by(Season.year.desc()).first()
    if not season:
        season = Season.query.order_by(Season.year.desc()).first()
    if not season:
        print("  ✗ No season found — create a season via the admin form first")
        sys.exit(1)
    print(f"  ✓ Using season: {season.year} ({season.status})")

    # ── 3. Look up existing event ─────────────────────────────────────────────
    print("\nLooking up event...")
    event = Event.query.filter_by(name=EVENT_NAME).first()
    if not event:
        print(f"  ✗ Event '{EVENT_NAME}' not found — create it via the admin form first")
        sys.exit(1)
    print(f"  ✓ Found event: {event.name} (id={event.id})")

    # ── 4. Link event to season if not already linked ─────────────────────────
    se = SeasonEvent.query.filter_by(season_id=season.id, event_id=event.id).first()
    if not se:
        se = SeasonEvent(
            season_id=season.id, event_id=event.id, status='active',
            start_date=date(season.year, 3, 1),
            end_date=date(season.year, 11, 30)
        )
        db.session.add(se)
        db.session.flush()
        print(f"  ✓ Linked {event.name} to season {season.year}")
    else:
        print(f"  – SeasonEvent already exists (id={se.id})")

    # ── 5. Create stages (up to 3, matching TIME1/TIME2/TIME3) ────────────────
    for snum in [1, 2, 3]:
        st = Stage.query.filter_by(season_event_id=se.id, stage_number=snum).first()
        if not st:
            st = Stage(
                season_event_id=se.id,
                stage_number=snum,
                distance='5K',
                location="Queen's Park Savannah",
                stage_date=date(season.year, 2 + snum, 15)
            )
            db.session.add(st)
    db.session.commit()
    stages = Stage.query.filter_by(season_event_id=se.id).order_by(Stage.stage_number).all()
    print(f"  ✓ Stages ready: {len(stages)}")

    # ── 6. Import participants, registrations and results ─────────────────────
    print("\nImporting participants...")
    created = skipped = registered = results_added = 0

    for _, row in df.iterrows():
        team = str(row.get('TEAM NAME', '')).strip()
        code = TEAM_MAP.get(team)
        if not code:
            skipped += 1
            continue
        inst = inst_cache.get(code)
        if not inst:
            skipped += 1
            continue

        first = str(row['FIRST NAME']).strip()
        last  = str(row['LAST NAME']).strip()
        email = str(row['EMAIL']).strip() if pd.notna(row.get('EMAIL')) else None
        if email == 'nan':
            email = None
        bdate = parse_date(row.get('BIRTHDATE'))
        sex   = str(row.get('SEX', '')).strip() or None
        div   = str(row.get('DIV', '')).strip() if pd.notna(row.get('DIV')) else None

        # Find or create participant
        p = Participant.query.filter_by(
            first_name=first, last_name=last, institution_id=inst.id
        ).first()
        if not p:
            p = Participant(
                first_name=first, last_name=last,
                institution_id=inst.id,
                email=email, birth_date=bdate,
                sex=sex, division=div
            )
            db.session.add(p)
            db.session.flush()
            created += 1

        # Register to the season event
        reg = Registration.query.filter_by(
            participant_id=p.id, season_event_id=se.id
        ).first()
        if not reg:
            reg = Registration(participant_id=p.id, season_event_id=se.id)
            db.session.add(reg)
            db.session.flush()
            registered += 1

        # Add results for each stage that has a recorded time
        for i, stage in enumerate(stages):
            time_val = row.get(f'TIME{i+1}')
            if pd.notna(time_val) and str(time_val).strip() not in ('', 'nan'):
                existing = Result.query.filter_by(
                    registration_id=reg.id, stage_id=stage.id
                ).first()
                if not existing:
                    res = Result(
                        registration_id=reg.id,
                        stage_id=stage.id,
                        time=str(time_val).strip()
                    )
                    db.session.add(res)
                    results_added += 1

    db.session.commit()

    # ── Summary ───────────────────────────────────────────────────────────────
    print(f"\n── Import complete ──────────────────────────────────────────────")
    print(f"  Participants created:  {created}")
    print(f"  Registered to event:  {registered}")
    print(f"  Results added:        {results_added}")
    print(f"  Rows skipped:         {skipped}")
    print()
    for inst in Institution.query.all():
        pc = Participant.query.filter_by(institution_id=inst.id).count()
        rc = db.session.query(Registration).join(Participant).filter(
            Participant.institution_id == inst.id,
            Registration.season_event_id == se.id
        ).count()
        print(f"  {inst.code:6} — {pc} participants, {rc} registered")
    print(f"\n  Total registrations: {Registration.query.count()}")
    print(f"  Total results:       {Result.query.count()}")
    print("\nDone. Run flask run and check the admin dashboard.")
