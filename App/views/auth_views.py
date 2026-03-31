from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from flask_jwt_extended import jwt_required, current_user, unset_jwt_cookies, set_access_cookies, create_access_token
from App.database import db
from App.models import User

auth_views = Blueprint('auth_views', __name__, template_folder='../templates')


# -------------------- Page Routes --------------------

@auth_views.route('/identify', methods=['GET'])
@jwt_required()
def identify_page():
    return render_template('message.html', title="Identify",
                           message=f"You are logged in as {current_user.firstname} {current_user.lastname} ({current_user.email}) - Role: {current_user.role}")

@auth_views.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()
        if not user:
            flash('User not found', 'danger')
            return redirect(url_for('auth_views.login'))

        if not user.check_password(password):
            flash('Invalid password', 'danger')
            return redirect(url_for('auth_views.login'))

        if not user.is_active:
            flash('Account deactivated', 'danger')
            return redirect(url_for('auth_views.login'))

        # Update last login
        from datetime import datetime
        user.last_login = datetime.utcnow()
        db.session.add(user)
        db.session.commit()

        # Create JWT token
        token = create_access_token(identity=str(user.id))

        # CHECK PASSWORD RESET FIRST - before creating response
        if user.must_change_password:
            session['reset_user_id'] = user.id
            flash('You must reset your password before continuing', 'warning')
            # Create a response for the reset page
            response = redirect(url_for('auth_views.reset_password'))
            # Set JWT cookie so reset page can use it if needed
            set_access_cookies(response, token)
            return response

        # If no reset needed, proceed to dashboard
        # Redirect based on role
        if user.role == 'admin':
            response = redirect(url_for('admin_views.dashboard'))
        elif user.role == 'hr':
            response = redirect(url_for('hr_views.dashboard'))
        elif user.role == 'scorer':
            response = redirect(url_for('scorer_views.dashboard'))
        elif user.role == 'pulse_leader':
            response = redirect(url_for('pulse.dashboard'))
        else:
            response = redirect(url_for('index_views.index_page'))

        # Set JWT cookie
        set_access_cookies(response, token)
        flash('Login successful!', 'success')
        return response

    return render_template('login.html')


@auth_views.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    if 'reset_user_id' not in session:
        flash('No password reset required', 'danger')
        return redirect(url_for('auth_views.login'))
    
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        if new_password != confirm_password:
            flash('New passwords do not match', 'danger')
            return redirect(url_for('auth_views.reset_password'))
        
        user = User.query.get(session['reset_user_id'])
        
        if not user or not user.check_password(current_password):
            flash('Invalid current password', 'danger')
            return redirect(url_for('auth_views.reset_password'))
        
        # Set new password
        user.set_password(new_password)
        user.must_change_password = False
        db.session.commit()

        # Create JWT token
        token = create_access_token(identity=str(user.id))

        # Clear reset flag
        session.pop('reset_user_id')

        # Set session variables
        session['user_id'] = user.id
        session['user_role'] = user.role
        session['institution_id'] = user.institution_id

        # Create response with redirect
        if user.role == 'admin':
            response = redirect(url_for('admin_views.dashboard'))
        elif user.role == 'hr':
            response = redirect(url_for('hr_views.dashboard'))
        else:  # scorer
            response = redirect(url_for('scorer_views.dashboard'))

        # Set JWT cookie
        set_access_cookies(response, token)

        flash('Password reset successful!', 'success')
        return response
    
    return render_template('reset_password.html')


@auth_views.route('/toggle-sidebar', methods=['POST'])
def toggle_sidebar():
    if 'sidebar_collapsed' in session:
        session.pop('sidebar_collapsed')
    else:
        session['sidebar_collapsed'] = True
    return '', 200

@auth_views.route('/logout', methods=['GET'])
def logout():
    response = redirect(url_for('auth_views.login'))
    unset_jwt_cookies(response)
    flash('Logged out successfully', 'success')
    return response

# -------------------- API Routes --------------------

@auth_views.route('/api/login', methods=['POST'])
def user_login_api():
    data = request.json
    email = data.get('email')
    password = data.get('password')

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password): #or not user.is_active:
        return jsonify(message='Invalid credentials'), 401

    token = create_access_token(identity=str(user.id))
    response = jsonify(access_token=token, user={
        'id': user.id,
        'email': user.email,
        'role': user.role
    })
    set_access_cookies(response, token)
    return response

@auth_views.route('/api/identify', methods=['GET'])
@jwt_required()
def identify_user():
    return jsonify({
        'id': current_user.id,
        'email': current_user.email,
        'role': current_user.role,
        'firstname': current_user.firstname,
        'lastname': current_user.lastname
    })

@auth_views.route('/api/logout', methods=['GET'])
def logout_api():
    response = jsonify(message="Logged out")
    unset_jwt_cookies(response)
    return response