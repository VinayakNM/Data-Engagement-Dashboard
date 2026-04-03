import os, sys, argparse
from datetime import datetime, date

# ── CLI ───────────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser(
    description="Seed CariFin DB from Excel registration list"
)
parser.add_argument(
    "--season",
    type=int,
    default=None,
    help="Target season year (default: most recent/active)",
)
parser.add_argument(
    "--file",
    type=str,
    default="registration_list.xlsx",
    help="Path to Excel file (default: registration_list.xlsx)",
)
parser.add_argument(
    "--event",
    type=str,
    default="Urban Challenge",
    help="Event name in DB (default: Urban Challenge)",
)
parser.add_argument(
    "--dry-run", action="store_true", help="Parse and report only — no DB writes"
)
args = parser.parse_args()

sys.path.insert(0, os.path.dirname(__file__))
from App import create_app
from App.database import db

app = create_app()

# ── Institution name → DB code ────────────────────────────────────────────────
TEAM_MAP = {
    "cbtt": "CBTT",
    "first citizens": "FCIT",
    "fcb": "FCIT",
    "sagicor": "SAGC",
    "scotiabank": "SCOT",
    "scotia": "SCOT",
    "ttmb": "TTMB",
    "ttutc": "TTUT",
    "utc": "TTUT",
    "min. of finance": "MOF",
    "ministry of finance": "MOF",
}


def normalise_columns(df):
    return {c.strip().upper(): c for c in df.columns}


def find_col(col_map, *candidates):
    for c in candidates:
        if c.upper() in col_map:
            return col_map[c.upper()]
    return None


def parse_date(val):
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    s = str(val).strip()
    if s in ("", "nan", "NaT", "None"):
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%m-%d-%Y"):
        try:
            return datetime.strptime(s.split(" ")[0], fmt).date()
        except ValueError:
            continue
    return None


def detect_date_columns(df):
    import pandas as pd

    date_cols = []
    for col in df.columns:
        upper = col.strip().upper()
        if "DATE" in upper or "BIRTH" in upper:
            date_cols.append(col)
            continue
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            date_cols.append(col)
            continue
        sample = df[col].dropna().head(20)
        if (
            len(sample)
            and sum(1 for v in sample if parse_date(v) is not None) / len(sample) > 0.3
        ):
            date_cols.append(col)
    return date_cols


def detect_stages(df, col_map):
    return [
        n
        for n in range(1, 10)
        if col_map.get(f"TIME{n}") and df[col_map[f"TIME{n}"]].notna().any()
    ]


with app.app_context():
    try:
        import pandas as pd
    except ImportError:
        print(
            "pandas not installed. Run: pip install pandas openpyxl --break-system-packages"
        )
        sys.exit(1)

    print(f'\n{"─"*60}')
    print(f"  CariFin Excel Seeder")
    print(f"  File   : {args.file}")
    print(f"  Event  : {args.event}")
    print(f'  Season : {args.season or "auto-detect"}')
    print(f"  Dry run: {args.dry_run}")
    print(f'{"─"*60}\n')

    from App.models import (
        Institution,
        Participant,
        Season,
        Event,
        SeasonEvent,
        Stage,
        Registration,
        Result,
    )

    if not os.path.exists(args.file):
        print(f"ERROR: File not found: {args.file}")
        sys.exit(1)

    print(f"Reading {args.file} ...")
    df = pd.read_excel(args.file)
    print(f"  {len(df)} rows, {len(df.columns)} columns")
    col_map = normalise_columns(df)

    col_first = find_col(col_map, "FIRST NAME", "FIRSTNAME", "FIRST")
    col_last = find_col(col_map, "LAST NAME", "LASTNAME", "LAST")
    col_team = find_col(col_map, "TEAM NAME", "TEAM", "INSTITUTION", "CLUB")
    col_email = find_col(col_map, "EMAIL", "E-MAIL", "EMAIL ADDRESS")
    col_sex = find_col(col_map, "SEX", "GENDER")
    col_div = find_col(col_map, "DIV", "DIVISION", "AGE GROUP", "AGEGROUP")

    for label, col in [
        ("FIRST NAME", col_first),
        ("LAST NAME", col_last),
        ("TEAM NAME", col_team),
    ]:
        if not col:
            print(
                f'ERROR: Could not find required column "{label}"\nAvailable: {list(df.columns)}'
            )
            sys.exit(1)

    date_cols = detect_date_columns(df)
    col_bdate = find_col(col_map, "BIRTHDATE", "BIRTH DATE", "DOB", "DATE OF BIRTH")
    if not col_bdate and date_cols:
        col_bdate = date_cols[0]

    stage_nums = detect_stages(df, col_map) or [1]

    print(f"\n  Column mapping:")
    print(f"    First name     : {col_first}")
    print(f"    Last name      : {col_last}")
    print(f"    Team           : {col_team}")
    print(f'    Email          : {col_email or "—"}')
    print(f'    Sex            : {col_sex or "—"}')
    print(f'    Division       : {col_div or "—"}')
    print(f'    Birthdate      : {col_bdate or "— (not found)"}')
    print(f'    Date cols found: {date_cols or "none"}')
    print(f"    Stages detected: {stage_nums}")

    df = df[df[col_team].notna() & df[col_first].notna() & df[col_last].notna()]
    print(f"\n  Valid rows: {len(df)}")

    if args.dry_run:
        print("\n[DRY RUN] No database writes. Exiting.")
        sys.exit(0)

    print("\nLooking up institutions ...")
    inst_cache, missing_teams = {}, set()
    for raw in df[col_team].dropna().unique():
        key = str(raw).strip().lower()
        code = TEAM_MAP.get(key)
        if not code:
            missing_teams.add(str(raw).strip())
            continue
        if code in inst_cache:
            continue
        inst = Institution.query.filter_by(code=code).first()
        if inst:
            inst_cache[code] = inst
            print(f"  ✓ {code:6} — {inst.name}")
        else:
            print(f"  ✗ {code:6} — not in DB (add via admin form)")

    if missing_teams:
        print(f"\n  ⚠  Teams not in TEAM_MAP (rows skipped):")
        for t in sorted(missing_teams):
            print(f'       "{t}"')

    print("\nLooking up season ...")
    if args.season:
        season = Season.query.filter_by(year=args.season).first()
        if not season:
            print(
                f"  ✗ Season {args.season} not found — create it via the admin form first"
            )
            sys.exit(1)
    else:
        season = (
            Season.query.filter_by(status="active").order_by(Season.year.desc()).first()
            or Season.query.order_by(Season.year.desc()).first()
        )
        if not season:
            print("  ✗ No season found — create one via the admin form first")
            sys.exit(1)
    print(f"  ✓ Season: {season.year} ({season.status})")

    print("\nLooking up event ...")
    event = Event.query.filter(Event.name.ilike(f"%{args.event}%")).first()
    if not event:
        print(f'  ✗ Event matching "{args.event}" not found — create it first')
        sys.exit(1)
    print(f"  ✓ Event: {event.name} (id={event.id})")

    se = SeasonEvent.query.filter_by(season_id=season.id, event_id=event.id).first()
    if not se:
        se = SeasonEvent(
            season_id=season.id,
            event_id=event.id,
            status="active",
            start_date=date(season.year, 3, 1),
            end_date=date(season.year, 11, 30),
        )
        db.session.add(se)
        db.session.flush()
        print(f'  ✓ Linked "{event.name}" → season {season.year}')
    else:
        print(f"  – SeasonEvent already exists (id={se.id})")

    month_for_stage = {1: 2, 2: 5, 3: 9, 4: 10, 5: 11}
    for snum in stage_nums:
        if not Stage.query.filter_by(season_event_id=se.id, stage_number=snum).first():
            db.session.add(
                Stage(
                    season_event_id=se.id,
                    stage_number=snum,
                    distance="5K",
                    location="Queen's Park Savannah",
                    stage_date=date(season.year, month_for_stage.get(snum, 3), 15),
                )
            )
    db.session.commit()

    stages = (
        Stage.query.filter_by(season_event_id=se.id).order_by(Stage.stage_number).all()
    )
    stage_by_num = {s.stage_number: s for s in stages}
    print(f"  ✓ Stages ready: {[s.stage_number for s in stages]}")

    print("\nImporting participants ...")
    created = skipped = registered = results_added = 0

    for _, row in df.iterrows():
        team_raw = str(row[col_team]).strip()
        code = TEAM_MAP.get(team_raw.lower())
        if not code or code not in inst_cache:
            skipped += 1
            continue

        first = str(row[col_first]).strip()
        last = str(row[col_last]).strip()
        if not first or not last or first == "nan" or last == "nan":
            skipped += 1
            continue

        inst = inst_cache[code]
        email = (
            str(row[col_email]).strip()
            if col_email and pd.notna(row.get(col_email))
            else None
        )
        bdate = parse_date(row.get(col_bdate)) if col_bdate else None
        sex = (
            str(row[col_sex]).strip()
            if col_sex and pd.notna(row.get(col_sex))
            else None
        )
        div = (
            str(row[col_div]).strip()
            if col_div and pd.notna(row.get(col_div))
            else None
        )
        if email == "nan":
            email = None
        if sex == "nan":
            sex = None
        if div == "nan":
            div = None

        p = Participant.query.filter_by(
            first_name=first, last_name=last, institution_id=inst.id
        ).first()
        if not p:
            p = Participant(
                first_name=first,
                last_name=last,
                institution_id=inst.id,
                email=email,
                birth_date=bdate,
                sex=sex,
                division=div,
            )
            db.session.add(p)
            db.session.flush()
            created += 1

        reg = Registration.query.filter_by(
            participant_id=p.id, season_event_id=se.id
        ).first()
        if not reg:
            reg = Registration(participant_id=p.id, season_event_id=se.id, division=div)
            db.session.add(reg)
            db.session.flush()
            registered += 1

        for snum in stage_nums:
            time_col = col_map.get(f"TIME{snum}")
            if not time_col:
                continue
            time_val = row.get(time_col)
            if pd.isna(time_val) or str(time_val).strip() in ("", "nan"):
                continue
            stage = stage_by_num.get(snum)
            if not stage:
                continue
            if not Result.query.filter_by(
                registration_id=reg.id, stage_id=stage.id
            ).first():
                db.session.add(
                    Result(
                        registration_id=reg.id,
                        stage_id=stage.id,
                        finish_time=str(time_val).strip(),
                    )
                )
                results_added += 1

    db.session.commit()

    print(f'\n{"─"*60}')
    print(f"  Done — season {season.year}")
    print(f'{"─"*60}')
    print(f"  Participants created  : {created}")
    print(f"  Registrations added   : {registered}")
    print(f"  Results added         : {results_added}")
    print(f"  Rows skipped          : {skipped}")
    print()
    for inst in Institution.query.order_by(Institution.code).all():
        pc = Participant.query.filter_by(institution_id=inst.id).count()
        rc = (
            db.session.query(Registration)
            .join(Participant)
            .filter(
                Participant.institution_id == inst.id,
                Registration.season_event_id == se.id,
            )
            .count()
        )
        if pc or rc:
            print(
                f"  {inst.code:6} — {pc} participants, {rc} registered season {season.year}"
            )
    print(f"\n  Total registrations  : {Registration.query.count()}")
    print(f"  Total results        : {Result.query.count()}")
    print('\nRun "flask run" and check the admin dashboard.')
