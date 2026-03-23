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