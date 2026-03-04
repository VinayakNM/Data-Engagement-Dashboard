from flask import Blueprint, render_template
from flask_jwt_extended import jwt_required, current_user
from App.controllers.scorer_controller import get_recent_results

scorer_views = Blueprint('scorer_views', __name__, template_folder='../templates')

@scorer_views.route('/scorer/dashboard')
@jwt_required()
def dashboard():
    if current_user.role not in ['admin', 'scorer']:
        return "Access Denied", 403
    results = get_recent_results()
    return render_template('scorer/scorer.html', results=results)