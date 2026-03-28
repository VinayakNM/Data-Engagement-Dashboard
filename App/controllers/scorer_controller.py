from flask import Blueprint, render_template, request, flash, redirect, url_for
from App.models.user import Registration
from flask_login import login_required, current_user
from App.models import db, Participant, Result

scorer_bp = Blueprint('scorer', __name__)

@scorer_bp.route('/enter-results', methods=['GET', 'POST'])
@login_required
def enter_results():
    if request.method == 'POST':
        participant_id = request.form.get('participant_id')
        event_time = request.form.get('finish_time')

        new_result = Result(participant_id=participant_id, finish_time=event_time)

        db.session.add(new_result)
        db.session.commit()

        flash(f"Result recorderd for Participant ID: {participant_id}")
        return redirect(url_for('scorer.enter_results'))

    participants = Participant.query.filter_by(institution_id=current_user.institution_id).all()
    return render_template('enter_results.html', participants=participants)

def get_recent_results(limit=10):
    return Result.query.order_by(Result.id.desc()).limit(limit).all()

@scorer_bp.route('/dashboard')
@login_required
def dashboard():
    results = db.session.query(Result)\
        .join(Registration)\
        .join(Participation)\
        .filter(Registration.institution_id == current_user.institution_id)\
        .order_by(Result.id.desc())\
        .all()
    return render_template('scorer_dashboard.html', results=results)

@scorer_bp.route('/flag-error/<int:result_id>', methods=['POST'])
@login_required
def flag_error(result_id):
    result=Result.query.get_or_404(result_id)

    result.is_error = not getattr(result, 'is_error', False)
    db.session.commit()

    status = "flagged" if result.is_error else "unflagged"
    flash(f"Result {result_id} has been {status}.")
    return redirect(url_for('scorer.dashboard'))

        
