from App.models import *
from flask import Blueprint, request, flash, redirect, url_for, render_template
from flask_jwt_extended import jwt_required, current_user
from App.controllers.admin_controller import create_user_by_admin, generate_temp_password
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


from App.controllers.admin_controller import create_user_by_admin, generate_temp_password

@admin_views.route('/admin/users/create', methods=['POST'])
@jwt_required()
def create_user():
    if current_user.role != 'admin':
        return "Access Denied", 403
    
    # Get form data
    firstname = request.form.get('firstname')
    lastname = request.form.get('lastname')
    email = request.form.get('email')
    role = request.form.get('role')
    institution_id = request.form.get('institution_id')
    
    # Generate username
    from App.controllers.user_controller import generate_username
    from App.models import Institution
    
    if role == 'hr':
        inst = Institution.query.get(institution_id)
        if not inst:
            flash('Institution not found', 'danger')
            return redirect(url_for('admin_views.dashboard'))
        username = generate_username(firstname, lastname, inst.code)
    else:
        # For admin/scorer, use role-based username
        base = f"{role}_{firstname[0].upper()}{lastname}".lower()
        username = base
    
    # Generate temporary password
    temp_password = generate_temp_password()
    
    # Create user
    user, error = create_user_by_admin(
        firstname=firstname,
        lastname=lastname,
        username=username,
        email=email,
        password=temp_password,
        role=role,
        institution_id=institution_id if role == 'hr' else None
    )
    
    if error:
        flash(error, 'danger')
    else:
        flash(f'{role.capitalize()} user created! Username: {username}, Temporary password: {temp_password}', 'success')
        # In production, email this instead of displaying
    
    return redirect(url_for('admin_views.dashboard'))

    
@admin_views.route('/admin/users')
@jwt_required()
def list_users():
    if current_user.role != 'admin':
        return "Access Denied", 403
    
    from App.controllers.admin_controller import get_all_users
    users = get_all_users()
    return render_template('admin/users.html', users=users)


@admin_views.route('/admin/institutions')
@jwt_required()
def institutions():
    if current_user.role != 'admin':
        return "Access Denied", 403
    return render_template('admin/institutions.html', title="Institution Management")

@admin_views.route('/admin/events')
@jwt_required()
def events():
    if current_user.role != 'admin':
        return "Access Denied", 403
    return render_template('admin/Forms/EventForm.html', title="Event Management")

@admin_views.route('/admin/seasons')
@jwt_required()
def seasons():
    if current_user.role != 'admin':
        return "Access Denied", 403
    return render_template('admin/Forms/SeasonForm.html', title="Season Management")

@admin_views.route('/admin/bibs')
@jwt_required()
def bibs():
    if current_user.role != 'admin':
        return "Access Denied", 403
    return render_template('admin/bibs.html', title="Bib Management")
