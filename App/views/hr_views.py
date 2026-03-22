from flask import Blueprint, request, flash, redirect, url_for, render_template, jsonify
from flask_jwt_extended import jwt_required, current_user
from App.controllers.hr_controller import get_hr_stats, get_available_events, register_participants
from App.controllers.participant_controller import create_participant
from App.models import Participant
from App.database import db
from datetime import datetime
import csv, io

hr_views = Blueprint('hr_views', __name__, template_folder='../templates')


@hr_views.route('/hr/dashboard')
@jwt_required()
def dashboard():
    if current_user.role != 'hr':
        return "Access Denied", 403
    stats = get_hr_stats(current_user.institution_id)
    return render_template('hr/hr.html', **stats)


@hr_views.route('/hr/participants/add', methods=['GET', 'POST'])
@jwt_required()
def add_participant():
    if current_user.role != 'hr':
        return "Access Denied", 403

    if request.method == 'POST':
        first_name  = request.form.get('first_name')
        last_name   = request.form.get('last_name')
        email       = request.form.get('email')
        birth_date  = request.form.get('birth_date')
        sex         = request.form.get('sex')
        division    = request.form.get('division')

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


@hr_views.route('/hr/participants/upload-csv', methods=['POST'])
@jwt_required()
def upload_csv():
    """Batch import participants from a CSV file."""
    if current_user.role != 'hr':
        return "Access Denied", 403

    file = request.files.get('csv_file')
    if not file or not file.filename.endswith('.csv'):
        flash('Please upload a valid .csv file.', 'danger')
        return redirect(url_for('hr_views.dashboard'))

    stream   = io.StringIO(file.stream.read().decode('utf-8-sig'))
    reader   = csv.DictReader(stream)
    created  = 0
    skipped  = 0
    errors   = []

    # Normalise header names to lowercase stripped
    for row in reader:
        row = {k.strip().lower(): (v.strip() if v else '') for k, v in row.items()}

        first = row.get('first_name') or row.get('first name') or row.get('firstname', '')
        last  = row.get('last_name')  or row.get('last name')  or row.get('lastname', '')
        if not first or not last:
            skipped += 1
            continue

        email     = row.get('email') or None
        sex       = row.get('sex') or None
        division  = row.get('div') or row.get('division') or None
        birth_raw = row.get('birth_date') or row.get('birthdate') or row.get('dob') or None
        birth_date = None
        if birth_raw:
            for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y'):
                try:
                    birth_date = datetime.strptime(birth_raw, fmt).date()
                    break
                except ValueError:
                    continue

        # Skip duplicate (same name + institution)
        existing = Participant.query.filter_by(
            first_name=first, last_name=last,
            institution_id=current_user.institution_id
        ).first()
        if existing:
            skipped += 1
            continue

        try:
            create_participant(
                first_name=first,
                last_name=last,
                email=email,
                birth_date=birth_date,
                sex=sex,
                division=division,
                institution_id=current_user.institution_id
            )
            created += 1
        except Exception as e:
            errors.append(f"{first} {last}: {str(e)}")
            db.session.rollback()

    if errors:
        flash(f'Imported {created}, skipped {skipped}. Errors: {"; ".join(errors[:3])}', 'danger')
    else:
        flash(f'✓ {created} participants imported, {skipped} skipped (duplicates or missing name).', 'success')

    return redirect(url_for('hr_views.dashboard'))


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

    participants = Participant.query.filter_by(institution_id=current_user.institution_id).all()
    events = get_available_events(current_user.institution_id)
    return render_template('hr/register.html', participants=participants, events=events)