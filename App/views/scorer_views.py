from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_jwt_extended import jwt_required, current_user
from App.controllers.scorer_controller import get_recent_results
from App.controllers.hr_controller import get_available_events
from App.models import Registration, Result, Stage, Participant
from App.database import db
import csv
import io


scorer_views = Blueprint('scorer_views', __name__, template_folder='../templates')

@scorer_views.route('/scorer/dashboard')
@jwt_required()
def dashboard():
    if current_user.role not in ['admin', 'scorer']:
        return "Access Denied", 403
    results = get_recent_results()
    return render_template('scorer/scorer.html', results=results)


@scorer_views.route('/scorer/enter-results', methods=['GET', 'POST'])
@jwt_required()
def enter_results():
    if current_user.role not in ['admin', 'scorer']:
        return "Access Denied", 403

    if request.method == 'POST':
        season_event_id = request.form.get('season_event_id')
        if not season_event_id:
            flash('Please select an event.', 'danger')
            return redirect(url_for('scorer_views.enter_results'))

        registrations = Registration.query.filter_by(season_event_id=season_event_id).all()
        stage = Stage.query.filter_by(season_event_id=season_event_id).first()
        if not stage:
            flash('No stage found for this event.', 'danger')
            return redirect(url_for('scorer_views.enter_results'))

        for reg in registrations:
            pid = reg.participant_id
            time_key = f'time_{pid}'
            place_key = f'placement_{pid}'
            if time_key in request.form and request.form[time_key]:
                finish_time = request.form[time_key]
                placement = request.form.get(place_key) or None
                existing = Result.query.filter_by(registration_id=reg.id).first()
                if existing:
                    existing.finish_time = finish_time
                    existing.placement = placement
                else:
                    result = Result(
                        registration_id=reg.id,
                        stage_id=stage.id,
                        finish_time=finish_time,
                        placement=placement
                    )
                    db.session.add(result)
        db.session.commit()
        flash('Results saved successfully!', 'success')
        return redirect(url_for('scorer_views.dashboard'))

    # GET request – show event selection form
    events = get_available_events(current_user.institution_id)   # scorers have no institution, but the function works
    return render_template('scorer/select_event.html', events=events)


@scorer_views.route('/scorer/enter-results/event/<int:season_event_id>')
@jwt_required()
def show_participants_for_event(season_event_id):
    if current_user.role not in ['admin', 'scorer']:
        return "Access Denied", 403
    registrations = Registration.query.filter_by(season_event_id=season_event_id).all()
    participants = [reg.participant for reg in registrations]
    return render_template('scorer/enter_results_form.html',
                           participants=participants,
                           season_event_id=season_event_id)

@scorer_views.route('/scorer/upload-results', methods=['GET', 'POST'])
@jwt_required()
def upload_results():
    if current_user.role not in ['admin', 'scorer']:
        return "Access Denied", 403

    if request.method == 'POST':
        file = request.files.get('csv_file')
        season_event_id = request.form.get('season_event_id')
        
        if not file or not file.filename.endswith('.csv'):
            flash('Please upload a valid CSV file.', 'danger')
            return redirect(request.url)
        
        # Get the stage for this event (assuming one stage per event)
        stage = Stage.query.filter_by(season_event_id=season_event_id).first()
        if not stage:
            flash('No stage found for this event.', 'danger')
            return redirect(request.url)
        
        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        csv_input = csv.DictReader(stream)
        
        # Expected columns: participant_id, finish_time, placement (optional)
        count = 0
        for row in csv_input:
            pid = row.get('participant_id')
            finish_time = row.get('finish_time')
            placement = row.get('placement')
            if not pid or not finish_time:
                continue
            
            # Find registration for this participant in the event
            reg = Registration.query.filter_by(
                participant_id=pid,
                season_event_id=season_event_id
            ).first()
            if not reg:
                continue
            
            # Create or update result
            result = Result.query.filter_by(registration_id=reg.id, stage_id=stage.id).first()
            if not result:
                result = Result(registration_id=reg.id, stage_id=stage.id)
            result.finish_time = finish_time
            result.placement = placement
            db.session.add(result)
            count += 1
        
        db.session.commit()
        flash(f'Successfully imported {count} results!', 'success')
        return redirect(url_for('scorer_views.dashboard'))
    
    # GET request – show form
    from App.controllers.hr_controller import get_available_events
    events = get_available_events(current_user.institution_id)   # scorers have no institution, but the function works
    return render_template('scorer/upload_results.html', events=events)