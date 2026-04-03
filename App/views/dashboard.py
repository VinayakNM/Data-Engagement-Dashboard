from flask import Blueprint, render_template
from flask_jwt_extended import jwt_required, current_user

dashboard_views = Blueprint('dashboard_views', __name__, template_folder='../templates')

@dashboard_views.route('/admin/dashboard')
@jwt_required()
def admin_dashboard():
    if current_user.role != 'admin':
        return "Access Denied", 403
    return render_template('admin/dashboard.html')

@dashboard_views.route('/admin/event-management')
@jwt_required()
def event_management():
    if current_user.role != 'admin':
        return "Access Denied", 403
    return render_template('admin/event_management.html')