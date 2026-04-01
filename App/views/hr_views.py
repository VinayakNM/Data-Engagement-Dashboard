from App.models import Participant
from flask import Blueprint, request, flash, redirect, url_for, render_template
from flask_jwt_extended import jwt_required, current_user
from App.controllers.hr_controller import get_hr_stats, get_available_events, register_participants
from datetime import datetime
import csv
import io


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


@hr_views.route('/hr/register', methods=['GET', 'POST'])
@jwt_required()
def register():
    if current_user.role != 'hr':
        return "Access Denied", 403
    
    if request.method == 'POST':
        season_event_id = request.form.get('season_event_id')
        participant_ids = request.form.getlist('participant_ids')
        
        if not season_event_id or not participant_ids:
            flash('Please select an event and at least one participant', 'danger')
            return redirect(url_for('hr_views.register'))
        
        count = register_participants(participant_ids, season_event_id)
        flash(f'{count} participants registered successfully!', 'success')
        return redirect(url_for('hr_views.dashboard'))
    
    # GET request - show form
    participants = Participant.query.filter_by(institution_id=current_user.institution_id).all()
    events = get_available_events(current_user.institution_id)
    
    return render_template('hr/register.html', 
                         participants=participants, 
                         events=events)


@hr_views.route('/hr/import-participants', methods=['GET', 'POST'])
@jwt_required()
def import_participants():
    if current_user.role != 'hr':
        return "Access Denied", 403
    
    if request.method == 'POST':
        file = request.files.get('csv_file')
        season_event_id = request.form.get('season_event_id')
        if not file or not file.filename.endswith('.csv'):
            flash('Please upload a valid CSV file.', 'danger')
            return redirect(request.url)
        # process CSV
        import csv, io
        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        csv_input = csv.DictReader(stream)
        new_participant_ids = []
        for row in csv_input:
            # expecting headers: first_name, last_name, email
            participant = Participant.query.filter_by(email=row['email']).first()
            if not participant:
                participant = Participant(
                    first_name=row['first_name'],
                    last_name=row['last_name'],
                    email=row['email'],
                    institution_id=current_user.institution_id
                )
                db.session.add(participant)
                db.session.flush()
            new_participant_ids.append(participant.id)
        reg_count = register_participants(new_participant_ids, season_event_id)
        db.session.commit()
        flash(f'Imported participants and created {reg_count} new registrations!', 'success')
        return redirect(url_for('hr_views.dashboard'))
    
    # GET request: show form
    events = get_available_events(current_user.institution_id)
    return render_template('hr/import_participants.html', events=events)