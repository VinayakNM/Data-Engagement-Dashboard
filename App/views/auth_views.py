from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from App.database import db
from App.models import User

auth_blueprint = Blueprint('auth', __name__)

@auth_blueprint.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()
        if not user:
            flash('User not found', 'danger')
            return redirect(url_for('auth.login'))

        if not user.check_password(password):
            flash('Invalid password', 'danger')
            return redirect(url_for('auth.login'))

        if not user.is_active:
            flash('Account deactivated', 'danger')
            return redirect(url_for('auth.login'))

        # Update last login
        from datetime import datetime
        user.last_login = datetime.utcnow()
        db.session.add(user)
        db.session.commit()

        session['user_id'] = user.id
        session['user_role'] = user.role
        session['institution_id'] = user.institution_id

        flash('Login successful!', 'success')

        # Redirect based on role
        if user.role == 'admin':
            return redirect(url_for('admin_views.dashboard'))
        elif user.role == 'hr':
            return redirect(url_for('hr.dashboard'))
        elif user.role == 'scorer':
            return redirect(url_for('scorer.dashboard'))
        elif user.role == 'pulse_leader':
            return redirect(url_for('pulse.dashboard'))
        else:
            return redirect(url_for('index_views.index_page'))

    return render_template('login.html')