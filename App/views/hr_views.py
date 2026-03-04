from flask import Blueprint, request, flash, redirect, url_for, render_template
from flask_jwt_extended import jwt_required, current_user
from App.controllers.hr_controller import get_hr_stats
from datetime import datetime


hr_views = Blueprint('hr_views', __name__, template_folder='../templates')

@hr_views.route('/hr/dashboard')
@jwt_required()
def dashboard():
    if current_user.role != 'hr':
        return "Access Denied", 403
    stats = get_hr_stats(current_user.institution_id)
    return render_template('hr/hr.html', **stats)



from App.controllers.participant_controller import create_participant

@hr_views.route('/hr/participants/add', methods=['GET', 'POST'])
@jwt_required()
def add_participant():
    if current_user.role != 'hr':
        return "Access Denied", 403
    
    if request.method == 'POST':
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        email = request.form.get('email')
        birth_date = request.form.get('birth_date')
        sex = request.form.get('sex')
        division = request.form.get('division')
        
        create_participant(
            first_name=first_name,
            last_name=last_name,
            email=email,
            birth_date=birth_date if birth_date else None,
            sex=sex,
            division=division,
            institution_id=current_user.institution_id
        )
        flash('Participant added successfully!', 'success')
        return redirect(url_for('hr_views.dashboard'))
    
    return render_template('hr/add_participant.html')