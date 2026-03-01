from flask import Blueprint, render_template
from flask_jwt_extended import jwt_required, current_user
from App.controllers.dashboards import get_admin_data, get_hr_stats, get_scorer_data

dashboard_views =Blueprint('dashboard_views', __name__, template_folder='../templates')

@dashboard_views.route('/dashboard/admin')
@jwt_required()
def admin_page():
    if current_user.role != 'admin':
        return "Access Denied", 403
    institutions = get_admin_data()
    return render_template('admin.html', institutions=institutions)

@dashboard_views.route('/dashboard/hr')
@jwt_required()
def hr_page():
    if current_user.role != 'hr':
        return "Access Denied", 403
    stats = get_hr_stats(current_user.institution_id)
    return render_template('hr.html', **stats)

@dashboard_views.route('/dashboard/scorer')
@jwt_required()
def scorer_page():
    if current_user.role not in ['admin', 'scorer']:
        return "Access Denied", 403
    recent_results = get_scorer_data()
    return render_template('scorer.html', results=recent_results)
