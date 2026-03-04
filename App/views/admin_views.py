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
    get_participation_status_breakdown
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
    current_season = Season.query.order_by(Season.year.desc()).first()
    season_id = current_season.id if current_season else None
    
    total_participants = get_total_participants()
    active_participants = get_active_participants(season_id)
    participation_rate = get_participation_rate(season_id)
    institution_stats = get_institution_stats(season_id)
    stage_completion = get_stage_completion() or []  # Default to empty list
    participation_by_inst = get_participation_by_institution(season_id) or []  # Default to empty list
    status_breakdown = get_participation_status_breakdown(season_id) or {'active': 0, 'no_show': 0, 'dnf': 0}
    
    # Safely access keys with defaults
    total_reg = status_breakdown.get('active', 0) + status_breakdown.get('no_show', 0) + status_breakdown.get('dnf', 0)
    
    # Calculate percentages for pie chart (avoid division by zero)
    active_pct = round((status_breakdown.get('active', 0) / total_reg * 100), 1) if total_reg > 0 else 0
    no_show_pct = round((status_breakdown.get('no_show', 0) / total_reg * 100), 1) if total_reg > 0 else 0
    dnf_pct = round((status_breakdown.get('dnf', 0) / total_reg * 100), 1) if total_reg > 0 else 0
    
    return render_template('admin/admin.html',
                         institutions=institutions,
                         institution_stats=institution_stats,
                         total_participants=total_participants,
                         active_participants=active_participants,
                         participation_rate=participation_rate,
                         stage_completion=stage_completion,
                         participation_by_inst=participation_by_inst,
                         current_season=current_season,
                         active_pct=active_pct,
                         no_show_pct=no_show_pct,
                         dnf_pct=dnf_pct)


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