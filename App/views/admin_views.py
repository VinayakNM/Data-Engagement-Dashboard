from App.models import *
from flask import Blueprint, request, flash, redirect, url_for, render_template
from flask_jwt_extended import jwt_required, current_user
from App.controllers.admin_controller import create_hr_user
from App.controllers.user_controller import generate_username
from App.controllers.admin_controller import (
    get_admin_data,
    get_total_participants,
    get_active_participants,
    get_participation_rate,
    get_institution_stats,
    get_stage_completion,
    get_participation_by_institution,
    get_participation_status_breakdown,
    get_stage_funnel,
    get_gender_split,
    get_age_group_distribution,
)


admin_views = Blueprint('admin_views', __name__, template_folder='../templates')

@admin_views.route('/test')
def test():
    return "Admin blueprint works!"

@admin_views.route('/admin/dashboard')
@jwt_required()
def dashboard():
    if current_user.role != 'admin':
        return "Access Denied", 403
    # Get institutions for dropdown and table
    institutions = get_admin_data()
    
    # Get metrics
    # Support filter params from URL query string
    filter_year = request.args.get('season', type=int)
    filter_inst = request.args.get('institution')
    filter_event = request.args.get('event', type=int)
    filter_division = request.args.get('division')

    # Resolve season — use filter year if provided, else active season, else most recent
    if filter_year:
        current_season = Season.query.filter_by(year=filter_year).first()
    else:
        current_season = Season.query.filter_by(status='active').order_by(Season.year.desc()).first()
        if not current_season:
            current_season = Season.query.order_by(Season.year.desc()).first()
    season_id = current_season.id if current_season else None

    # All seasons for the filter dropdown
    all_seasons = Season.query.order_by(Season.year.desc()).all()

    # Events for the event filter dropdown
    events = Event.query.order_by(Event.name).all()

    # Distinct divisions from Participant and Registration tables
    div_rows = db.session.query(Participant.division).filter(
        Participant.division.isnot(None),
        Participant.division != ''
    ).distinct().all()
    divisions = sorted(set(r[0] for r in div_rows if r[0]))

    total_participants  = get_total_participants(season_id, filter_event, filter_division, filter_inst)
    active_participants = get_active_participants(season_id, filter_event, filter_division, filter_inst)
    participation_rate  = get_participation_rate(season_id, filter_event, filter_division, filter_inst)
    institution_stats   = get_institution_stats(season_id, filter_event, filter_division, filter_inst)
    stage_completion    = get_stage_completion(season_id, filter_event, filter_inst) or []
    participation_by_inst  = get_participation_by_institution(season_id, filter_event, filter_division, filter_inst) or []
    status_breakdown = get_participation_status_breakdown(season_id, filter_event, filter_division, filter_inst) or {'participated': 0, 'no_show': 0, 'pending': 0}

    participated_count = status_breakdown.get('participated', 0)
    no_show_count      = status_breakdown.get('no_show', 0) + status_breakdown.get('pending', 0)
    total_reg   = participated_count + no_show_count
    active_pct  = round((participated_count / total_reg * 100), 1) if total_reg > 0 else 0
    no_show_pct = round((no_show_count      / total_reg * 100), 1) if total_reg > 0 else 0

    # FIX: bar chart max for proportional heights
    max_count = max((i['count'] for i in participation_by_inst), default=1)

    # ── Analytics panels ──────────────────────────────────────────────────────
    stage_funnel     = get_stage_funnel(season_id, filter_event, filter_inst)
    gender_split     = get_gender_split(season_id, filter_event, filter_inst)
    age_groups       = get_age_group_distribution(season_id, filter_event, filter_inst)

    return render_template('admin/admin.html',
                         institutions=institutions,
                         institution_stats=institution_stats,
                         total_participants=total_participants,
                         active_participants=active_participants,
                         participation_rate=participation_rate,
                         stage_completion=stage_completion,
                         participation_by_inst=participation_by_inst,
                         current_season=current_season,
                         all_seasons=all_seasons,
                         events=events,
                         divisions=divisions,
                         filter_year=filter_year or (current_season.year if current_season else None),
                         max_count=max_count,
                         active_pct=active_pct,
                         no_show_pct=no_show_pct,
                         stage_funnel=stage_funnel,
                         gender_split=gender_split,
                         age_groups=age_groups)


@admin_views.route('/admin/users/create', methods=['POST'])
@jwt_required()
def create_hr():
    if current_user.role != 'admin':
        return "Access Denied", 403


    # Get form data (form in admin.html)
    firstname = request.form.get('firstname')
    lastname = request.form.get('lastname')
    # username = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password')
    institution_id = request.form.get('institution_id')

    # Get institution code for username
    from App.models import Institution
    inst = Institution.query.get(institution_id)
    if not inst:
        flash('Institution not found', 'danger')
        return redirect(url_for('admin_views.dashboard'))
    
    username = generate_username(firstname, lastname, inst.code)

    # if not all([firstname, lastname, username, email, password, institution_id]):
    #    flash('All fields are required', 'danger')
    #    return redirect(url_for('admin_views.dashboard'))
    
    hr, error = create_hr_user(firstname, lastname, username, email, password, institution_id)
    if error:
        flash(error, 'danger')
    else:
        flash(f'HR user {username} created successfully', 'success')

    return redirect(url_for('admin_views.dashboard'))

    


@admin_views.route('/admin/import-season', methods=['POST'])
@jwt_required()
def import_season_excel():
    """Upload an Excel registration file and seed it into a chosen season."""
    if current_user.role != 'admin':
        return "Access Denied", 403

    from datetime import date
    import io

    try:
        import pandas as pd
    except ImportError:
        flash('pandas not installed on this server.', 'danger')
        return redirect(url_for('admin_views.dashboard'))

    season_year = request.form.get('season_year', type=int)
    file = request.files.get('excel_file')

    if not season_year:
        flash('Please select a season.', 'danger')
        return redirect(url_for('admin_views.dashboard'))
    if not file or not file.filename:
        flash('Please choose an Excel file to upload.', 'danger')
        return redirect(url_for('admin_views.dashboard'))
    if not file.filename.lower().endswith(('.xlsx', '.xls')):
        flash('Only .xlsx / .xls files are supported.', 'danger')
        return redirect(url_for('admin_views.dashboard'))

    # ── Resolve season ────────────────────────────────────────────────────
    season = Season.query.filter_by(year=season_year).first()
    if not season:
        flash(f'Season {season_year} not found. Create it first.', 'danger')
        return redirect(url_for('admin_views.dashboard'))

    # ── Read file ─────────────────────────────────────────────────────────
    try:
        df = pd.read_excel(io.BytesIO(file.read()))
    except Exception as e:
        flash(f'Could not read file: {e}', 'danger')
        return redirect(url_for('admin_views.dashboard'))

    # ── Column detection helpers ──────────────────────────────────────────
    col_map = {c.strip().upper(): c for c in df.columns}

    def find_col(*candidates):
        for c in candidates:
            if c.upper() in col_map:
                return col_map[c.upper()]
        return None

    def parse_date(val):
        from datetime import datetime, date as date_
        if val is None: return None
        if isinstance(val, datetime): return val.date()
        if isinstance(val, date_): return val
        s = str(val).strip()
        if s in ('', 'nan', 'NaT', 'None'): return None
        for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y'):
            try: return datetime.strptime(s.split(' ')[0], fmt).date()
            except ValueError: continue
        return None

    TEAM_MAP = {
        'cbtt': 'CBTT', 'first citizens': 'FCIT', 'fcb': 'FCIT',
        'sagicor': 'SAGC', 'scotiabank': 'SCOT', 'scotia': 'SCOT',
        'ttmb': 'TTMB', 'ttutc': 'TTUT', 'utc': 'TTUT',
        'min. of finance': 'MOF', 'ministry of finance': 'MOF',
    }

    col_first = find_col('FIRST NAME', 'FIRSTNAME', 'FIRST')
    col_last  = find_col('LAST NAME',  'LASTNAME',  'LAST')
    col_team  = find_col('TEAM NAME',  'TEAM',      'INSTITUTION', 'CLUB')
    col_email = find_col('EMAIL', 'E-MAIL')
    col_sex   = find_col('SEX', 'GENDER')
    col_div   = find_col('DIV', 'DIVISION', 'AGE GROUP')
    col_bdate = find_col('BIRTHDATE', 'BIRTH DATE', 'DOB', 'DATE OF BIRTH')

    if not all([col_first, col_last, col_team]):
        flash('File missing required columns (FIRST NAME, LAST NAME, TEAM NAME).', 'danger')
        return redirect(url_for('admin_views.dashboard'))

    df = df[df[col_team].notna() & df[col_first].notna() & df[col_last].notna()]

    # Detect stage TIME columns
    stage_nums = [n for n in range(1, 10)
                  if col_map.get(f'TIME{n}') and df[col_map[f'TIME{n}']].notna().any()]
    if not stage_nums:
        stage_nums = []

    # ── Resolve event & season-event ─────────────────────────────────────
    event = Event.query.filter_by(name='Urban Challenge').first()
    if not event:
        event = Event.query.first()
    if not event:
        flash('No events found. Create an event first.', 'danger')
        return redirect(url_for('admin_views.dashboard'))

    se = SeasonEvent.query.filter_by(season_id=season.id, event_id=event.id).first()
    if not se:
        se = SeasonEvent(season_id=season.id, event_id=event.id, status='active',
                         start_date=date(season.year, 3, 1),
                         end_date=date(season.year, 11, 30))
        db.session.add(se)
        db.session.flush()

    # Ensure stages exist
    month_map = {1: 2, 2: 5, 3: 9, 4: 10, 5: 11}
    for snum in stage_nums:
        if not Stage.query.filter_by(season_event_id=se.id, stage_number=snum).first():
            db.session.add(Stage(
                season_event_id=se.id, stage_number=snum,
                distance='5K', location="Queen's Park Savannah",
                stage_date=date(season.year, month_map.get(snum, 3), 15)))
    db.session.commit()
    stage_by_num = {s.stage_number: s for s in
                    Stage.query.filter_by(season_event_id=se.id).all()}

    # ── Institution cache ─────────────────────────────────────────────────
    inst_cache = {}
    for raw in df[col_team].dropna().unique():
        code = TEAM_MAP.get(str(raw).strip().lower())
        if code and code not in inst_cache:
            inst = Institution.query.filter_by(code=code).first()
            if inst:
                inst_cache[code] = inst

    # ── Import rows ───────────────────────────────────────────────────────
    created = registered = results_added = skipped = 0

    for _, row in df.iterrows():
        code = TEAM_MAP.get(str(row[col_team]).strip().lower())
        if not code or code not in inst_cache:
            skipped += 1
            continue

        first = str(row[col_first]).strip()
        last  = str(row[col_last]).strip()
        if not first or not last or first == 'nan' or last == 'nan':
            skipped += 1
            continue

        inst  = inst_cache[code]
        email = (str(row[col_email]).strip()
                 if col_email and pd.notna(row.get(col_email)) else None)
        bdate = parse_date(row.get(col_bdate)) if col_bdate else None
        sex   = (str(row[col_sex]).strip()
                 if col_sex and pd.notna(row.get(col_sex)) else None)
        div   = (str(row[col_div]).strip()
                 if col_div and pd.notna(row.get(col_div)) else None)
        if email == 'nan': email = None
        if sex   == 'nan': sex   = None
        if div   == 'nan': div   = None

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

        for snum in stage_nums:
            time_col = col_map.get(f'TIME{snum}')
            if not time_col: continue
            time_val = row.get(time_col)
            if pd.isna(time_val) or str(time_val).strip() in ('', 'nan'): continue
            stage = stage_by_num.get(snum)
            if not stage: continue
            if not Result.query.filter_by(
                    registration_id=reg.id, stage_id=stage.id).first():
                db.session.add(Result(registration_id=reg.id,
                                      stage_id=stage.id,
                                      finish_time=str(time_val).strip()))
                results_added += 1

    db.session.commit()

    flash(
        f'✓ Season {season_year} import complete — '
        f'{created} participants added, {registered} registered, '
        f'{results_added} results recorded, {skipped} rows skipped.',
        'success'
    )
    return redirect(url_for('admin_views.dashboard'))
@admin_views.route('/admin/system/institutions')
@jwt_required()
def institution_form():
    if current_user.role != 'admin':
        return "Access Denied", 403
    return render_template('admin/Forms/InstitutionForm.html')


@admin_views.route('/admin/system/events')
@jwt_required()
def event_form():
    if current_user.role != 'admin':
        return "Access Denied", 403
    return render_template('admin/Forms/EventForm.html')


@admin_views.route('/admin/system/seasons')
@jwt_required()
def season_form():
    if current_user.role != 'admin':
        return "Access Denied", 403
    return render_template('admin/Forms/SeasonForm.html')


@admin_views.route('/admin/users')
@jwt_required()
def list_users():
    if current_user.role != 'admin':
        return "Access Denied", 403
    
    from App.controllers.admin_controller import get_all_users
    users = get_all_users()
    return render_template('admin/users.html', users=users)