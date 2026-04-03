# seed.py
import os
import re
from App import create_app
from App.database import db
from App.models import (
    Institution, Admin, HR, Scorer, PulseLeader,
    Season, Event, SeasonEvent, Stage,
    Participant, Registration, Result,
)
from datetime import datetime, date

# ── Path to the secret Excel file mounted by Render ──────────────────────────
# Upload via: Render Dashboard → carifin-dashboard → Environment → Secret Files
# Filename: urban_challenge_master.xlsx
EXCEL_SEED_PATH = '/etc/secrets/urban_challenge_master.xlsx'


def seed():
    app = create_app()
    with app.app_context():
        print("Seeding database...")

        db.create_all()
        print(" + Tables created!")

        # ── INSTITUTIONS ──────────────────────────────────────────────────────
        institutions = [
            ('Central Bank of Trinidad and Tobago', 'CBTT'),
            ('First Citizens Bank',                 'FCIT'),
            ('Sagicor',                             'SAGC'),
            ('Scotiabank',                          'SCOT'),
            ('TT Mortgage Bank',                    'TTMB'),
            ('TTUTC',                               'TTUT'),
            ('Ministry of Finance',                 'MOF'),
        ]
        for name, code in institutions:
            if not Institution.query.filter_by(code=code).first():
                db.session.add(Institution(name=name, code=code))
                print(f"  + Institution: {name} ({code})")
        db.session.commit()

        cbtt = Institution.query.filter_by(code='CBTT').first()
        fcit = Institution.query.filter_by(code='FCIT').first()

        # ── SEASONS ───────────────────────────────────────────────────────────
        seasons = [
            (2025, 'CariFin Games 2025',                    'active'),
            (2024, 'CariFin Games 2024',                    'closed'),
            (2026, 'CariFin Games 2026 - 35th Anniversary', 'planning'),
        ]
        for year, desc, status in seasons:
            if not Season.query.filter_by(year=year).first():
                db.session.add(Season(year=year, description=desc, status=status))
                print(f"  + Season: {year} ({status})")
        db.session.commit()

        current_season = Season.query.filter_by(year=2025).first()

        # ── EVENTS ────────────────────────────────────────────────────────────
        events = [
            ('Urban Challenge', 'Multi-stage running event across 5 locations', 'run'),
            ('Cross Country',   'Single day cross country race',                'run'),
            ('Corporate Relay', 'Team relay event',                             'run'),
        ]
        for name, desc, etype in events:
            if not Event.query.filter_by(name=name).first():
                db.session.add(Event(name=name, description=desc, event_type=etype))
                print(f"  + Event: {name}")
        db.session.commit()

        urban = Event.query.filter_by(name='Urban Challenge').first()
        cross = Event.query.filter_by(name='Cross Country').first()
        relay = Event.query.filter_by(name='Corporate Relay').first()

        # ── SEASON-EVENT BRIDGE ───────────────────────────────────────────────
        if current_season:
            if not SeasonEvent.query.filter_by(season_id=current_season.id, event_id=urban.id).first():
                db.session.add(SeasonEvent(
                    season_id=current_season.id, event_id=urban.id, status='active',
                    start_date=date(2025, 3, 1), end_date=date(2025, 11, 30)))
                print("  + Linked Urban Challenge to 2025 season")

            if not SeasonEvent.query.filter_by(season_id=current_season.id, event_id=cross.id).first():
                db.session.add(SeasonEvent(
                    season_id=current_season.id, event_id=cross.id, status='active',
                    start_date=date(2025, 10, 15), end_date=date(2025, 10, 15)))
                print("  + Linked Cross Country to 2025 season")

            if relay and not SeasonEvent.query.filter_by(season_id=current_season.id, event_id=relay.id).first():
                db.session.add(SeasonEvent(
                    season_id=current_season.id, event_id=relay.id,
                    start_date=date(2025, 5, 20), end_date=date(2025, 5, 20)))
                print("  + Linked Corporate Relay to 2025 season")

        db.session.commit()

        # ── STAGES for Urban Challenge ────────────────────────────────────────
        if current_season and urban:
            se_urban = SeasonEvent.query.filter_by(
                season_id=current_season.id, event_id=urban.id).first()
            if se_urban:
                stages = [
                    (1, '5K', "Queen's Park Savannah",  date(2025, 3, 1)),
                    (2, '5K', 'Brian Lara Promenade',   date(2025, 3, 8)),
                    (3, '3K', 'Hasely Crawford Stadium', date(2025, 3, 15)),
                    (4, '5K', 'Mucurapo',               date(2025, 3, 22)),
                    (5, '3K', 'Chaguanas',              date(2025, 3, 29)),
                ]
                for stage_num, distance, location, stage_date in stages:
                    if not Stage.query.filter_by(season_event_id=se_urban.id, stage_number=stage_num).first():
                        db.session.add(Stage(
                            season_event_id=se_urban.id, stage_number=stage_num,
                            distance=distance, location=location, stage_date=stage_date))
                        print(f"  + Stage {stage_num}: {location}")
        db.session.commit()

        # ── USERS ─────────────────────────────────────────────────────────────
        if not Admin.query.filter_by(email='admin@carifin.com').first():
            db.session.add(Admin(
                firstname='Admin', lastname='User', username='admin',
                email='admin@carifin.com', password='Admin123!'))
            print("  + Admin: admin@carifin.com / Admin123!")
        else:
            print("  - Admin already exists")

        if cbtt and not HR.query.filter_by(email='hr@cbtt.com').first():
            db.session.add(HR(
                firstname='HR', lastname='CBTT', username='hr_cbtt',
                email='hr@cbtt.com', password='Hr123!', institution_id=cbtt.id))
            print("  + HR: hr@cbtt.com (CBTT)")

        if fcit and not HR.query.filter_by(email='hr@fcit.com').first():
            db.session.add(HR(
                firstname='HR2', lastname='FCIT', username='hr_fcit',
                email='hr@fcit.com', password='Hr123!', institution_id=fcit.id))
            print("  + HR: hr@fcit.com (FCIT)")

        if not Scorer.query.filter_by(email='scorer@carifin.com').first():
            db.session.add(Scorer(
                firstname='Scorer', lastname='User', username='scorer',
                email='scorer@carifin.com', password='Scorer123!'))
            print("  + Scorer: scorer@carifin.com")

        if cbtt and not PulseLeader.query.filter_by(email='pulse@cbtt.com').first():
            pulse = PulseLeader(
                firstname='Pulse', lastname='Leader', username='pulse_cbtt',
                email='pulse@cbtt.com', password='Pulse123!', institution_id=cbtt.id)
            pulse.social_media_handle = '@CBTT_Pulse'
            db.session.add(pulse)
            print("  + PulseLeader: pulse@cbtt.com (CBTT)")

        db.session.commit()

        # ── EXCEL SEED (from Render secret file) ─────────────────────────────
        if os.path.exists(EXCEL_SEED_PATH):
            print(f"\n  Found seed Excel at {EXCEL_SEED_PATH}, importing...")
            try:
                result = import_excel_seed(EXCEL_SEED_PATH, season_year=2025)
                print(f"  ✓ Excel import: {result['created']} participants, "
                      f"{result['registered']} registered, "
                      f"{result['results']} results, "
                      f"{result['skipped']} skipped.")
                if result['unmatched']:
                    print(f"  ⚠ Unmatched institutions: {', '.join(result['unmatched'])}")
            except Exception as e:
                print(f"  ✗ Excel import failed: {e}")
        else:
            print(f"\n  No seed Excel found at {EXCEL_SEED_PATH} — skipping participant import.")
            print("    To seed participants: upload 'urban_challenge_master.xlsx' as a")
            print("    Render Secret File, then redeploy.")

        print("\nSeeding complete!")


def import_excel_seed(filepath, season_year):
    """
    Import participants from an Excel file into the given season.
    Reuses the same dynamic matching logic as the admin import route.
    Safe to run multiple times — skips existing participants/registrations.
    """
    import pandas as pd

    season = Season.query.filter_by(year=season_year).first()
    if not season:
        raise ValueError(f"Season {season_year} not found. Run seed() first.")

    df = pd.read_excel(filepath)
    df.columns = [str(c).strip() for c in df.columns]
    col_map = {c.upper(): c for c in df.columns}

    def find_col(*candidates):
        for c in candidates:
            if c.upper() in col_map:
                return col_map[c.upper()]
        return None

    def clean(val):
        if val is None: return None
        s = str(val).strip()
        return None if s in ('', 'nan', 'NaT', 'None') else s

    def parse_date(val):
        if val is None: return None
        if isinstance(val, datetime): return val.date()
        if isinstance(val, date): return val
        s = str(val).strip()
        if s in ('', 'nan', 'NaT', 'None'): return None
        for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y'):
            try: return datetime.strptime(s.split(' ')[0], fmt).date()
            except ValueError: continue
        return None

    col_first = find_col('FIRST NAME', 'FIRSTNAME', 'FIRST')
    col_last  = find_col('LAST NAME',  'LASTNAME',  'LAST')
    col_team  = find_col('TEAM NAME',  'TEAM',      'INSTITUTION', 'CLUB', 'COMPANY')
    col_event = find_col('EVENT NAME', 'EVENT',      'RACE')
    col_email = find_col('EMAIL',      'E-MAIL',     'EMAIL ADDRESS')
    col_sex   = find_col('SEX',        'GENDER')
    col_div   = find_col('DIV',        'DIVISION',   'AGE GROUP', 'CATEGORY')
    col_bdate = find_col('BIRTHDATE',  'BIRTH DATE', 'DOB', 'DATE OF BIRTH')

    if not all([col_first, col_last, col_team]):
        raise ValueError("Excel missing required columns: FIRST NAME, LAST NAME, TEAM/INSTITUTION")

    df = df[df[col_team].notna() & df[col_first].notna() & df[col_last].notna()].copy()
    df.reset_index(drop=True, inplace=True)

    stage_nums = [n for n in range(1, 20)
                  if col_map.get(f'TIME{n}') and df[col_map[f'TIME{n}']].notna().any()]

    # ── Institution fuzzy matching ─────────────────────────────────────────
    all_institutions = Institution.query.all()

    def _normalise(s):
        return re.sub(r'[^a-z0-9 ]', '', s.strip().lower()).strip()

    def _tokens(s):
        return set(_normalise(s).split())

    inst_lookup = {}
    for inst in all_institutions:
        inst_lookup[inst.name.strip().lower()] = inst
        inst_lookup[inst.code.strip().lower()] = inst
        inst_lookup[_normalise(inst.name)]     = inst
        inst_lookup[_normalise(inst.code)]     = inst

    def find_institution(raw_name):
        key   = raw_name.strip().lower()
        key_n = _normalise(raw_name)
        if key   in inst_lookup: return inst_lookup[key]
        if key_n in inst_lookup: return inst_lookup[key_n]
        for inst in all_institutions:
            iname_n = _normalise(inst.name)
            icode   = inst.code.lower()
            if icode == key or icode == key_n: return inst
            if inst.name.lower() in key or key in inst.name.lower(): return inst
            if iname_n and key_n and (iname_n in key_n or key_n in iname_n): return inst
            raw_tok  = _tokens(raw_name)
            inst_tok = _tokens(inst.name)
            if raw_tok and inst_tok:
                overlap = raw_tok & inst_tok
                if len(overlap) >= max(1, len(raw_tok) - 1):
                    return inst
        return None

    # ── Event / SeasonEvent resolution ────────────────────────────────────
    def resolve_event(raw_name):
        name = (raw_name or '').strip()
        if not name: return None, None
        event = Event.query.filter(db.func.lower(Event.name) == name.lower()).first()
        if not event:
            event = Event(name=name, event_type='run')
            db.session.add(event)
            db.session.flush()
        se = SeasonEvent.query.filter_by(season_id=season.id, event_id=event.id).first()
        if not se:
            se = SeasonEvent(
                season_id=season.id, event_id=event.id, status='active',
                start_date=date(season.year, 3, 1),
                end_date=date(season.year, 11, 30))
            db.session.add(se)
            db.session.flush()
        return event, se

    se_cache = {}
    if col_event:
        for raw in df[col_event].dropna().unique():
            name_clean = str(raw).strip()
            if name_clean and name_clean != 'nan':
                _, se = resolve_event(name_clean)
                if se: se_cache[name_clean.lower()] = se
    else:
        se_list = SeasonEvent.query.filter_by(season_id=season.id).all()
        default_se = se_list[0] if se_list else None
        if not default_se:
            default_event = Event.query.filter_by(name='Urban Challenge').first() \
                            or Event.query.first()
            if default_event:
                default_se = SeasonEvent(
                    season_id=season.id, event_id=default_event.id, status='active',
                    start_date=date(season.year, 3, 1),
                    end_date=date(season.year, 11, 30))
                db.session.add(default_se)
                db.session.flush()
        if default_se:
            se_cache['__default__'] = default_se

    # ── Ensure stages exist ───────────────────────────────────────────────
    db.session.flush()
    month_map = {1: 2, 2: 5, 3: 9, 4: 10, 5: 11}
    stage_cache = {}
    for se in se_cache.values():
        for snum in stage_nums:
            if not Stage.query.filter_by(season_event_id=se.id, stage_number=snum).first():
                db.session.add(Stage(
                    season_event_id=se.id, stage_number=snum,
                    distance='5K', location='TBD',
                    stage_date=date(season.year, month_map.get(snum, 3), 15)))
        db.session.flush()
        stage_cache[se.id] = {
            s.stage_number: s
            for s in Stage.query.filter_by(season_event_id=se.id).all()
        }
    db.session.commit()

    # ── Import rows ───────────────────────────────────────────────────────
    created = registered = results = skipped = 0
    unmatched = set()

    for _, row in df.iterrows():
        try:
            raw_team = clean(row.get(col_team))
            if not raw_team: skipped += 1; continue

            inst = find_institution(raw_team)
            if not inst:
                unmatched.add(raw_team)
                skipped += 1
                continue

            first = clean(row.get(col_first))
            last  = clean(row.get(col_last))
            if not first or not last: skipped += 1; continue

            se = se_cache.get(
                clean(row.get(col_event, '')).lower() if col_event else '__default__'
            ) if (col_event or '__default__' in se_cache) else None
            if not se: skipped += 1; continue

            email = clean(row.get(col_email)) if col_email else None
            bdate = parse_date(row.get(col_bdate)) if col_bdate else None
            sex   = clean(row.get(col_sex))   if col_sex   else None
            div   = clean(row.get(col_div))   if col_div   else None

            p = Participant.query.filter_by(
                first_name=first, last_name=last, institution_id=inst.id).first()
            if not p:
                p = Participant(first_name=first, last_name=last,
                                institution_id=inst.id,
                                email=email, birth_date=bdate, sex=sex, division=div)
                db.session.add(p)
                db.session.flush()
                created += 1

            reg = Registration.query.filter_by(
                participant_id=p.id, season_event_id=se.id).first()
            if not reg:
                reg = Registration(participant_id=p.id,
                                   season_event_id=se.id, division=div)
                db.session.add(reg)
                db.session.flush()
                registered += 1

            stages_for_se = stage_cache.get(se.id, {})
            for snum in stage_nums:
                time_col = col_map.get(f'TIME{snum}')
                if not time_col: continue
                time_val = clean(str(row.get(time_col, '')))
                if not time_val: continue
                stage = stages_for_se.get(snum)
                if not stage: continue
                if not Result.query.filter_by(
                        registration_id=reg.id, stage_id=stage.id).first():
                    db.session.add(Result(
                        registration_id=reg.id,
                        stage_id=stage.id,
                        finish_time=time_val))
                    results += 1

        except Exception as row_err:
            db.session.rollback()
            print(f"    [SEED] Row error: {row_err}")
            skipped += 1
            continue

    db.session.commit()
    return {'created': created, 'registered': registered,
            'results': results, 'skipped': skipped, 'unmatched': unmatched}


if __name__ == '__main__':
    seed()