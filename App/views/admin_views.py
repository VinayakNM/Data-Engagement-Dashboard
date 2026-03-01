from flask import Blueprint, request, flash, redirect, url_for, render_template
from flask_jwt_extended import jwt_required, current_user
from App.controllers.admin_controller import create_hr_user

admin_views = Blueprint('admin_views', __name__, template_folder='../templates')

@admin_views.route('/test')
def test():
    return "Admin blueprint works!"

@admin_views.route('/dashboard')
@jwt_required()
def dashboard():
    if current_user.role != 'admin':
        return "Access Denied", 403
    from App.controllers.dashboards import get_admin_data
    institutions = get_admin_data()
    return render_template('admin/admin.html', institutions=institutions)


@admin_views.route('/admin/users/create', methods=['POST'])
@jwt_required
def create_hr():
    if current_user.role != 'admin':
        return "Access Denied", 403


    # Get form data (Andrea's form in admin.html)
    firstname = request.form.get('firstname')
    lastname = request.form.get('lastname')
    username = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password')
    institution_id = request.form.get('institution_id')

    if not all([firstname, lastname, username, email, password, institution_id]):
        flash('All fields are required', 'danger')
        return redirect(url_for('admin_views.dashboard'))
    
    hr, error = create_hr_user(firstname, lastname, username, email, password, institution_id)
    if error:
        flash(error, 'danger')
    else:
        flash(f'HR user {username} created successfully', 'success')

    return redirect(url_for('admin_views.dashboard'))
