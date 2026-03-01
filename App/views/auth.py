from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
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
        db.session.add(user)
        db.session.commit()

        # Create JWT token
        token = create_access_token(identity=user.id)

        #Redirect based on role
        if user.role == 'admin':
            response = redirect(url_for('dashboard_views.admin_page'))
        elif user.role == 'hr':
            response = redirect(url_for('dashboard_views.hr_page'))
        elif user.role == 'scorer':
            response = redirect(url_for('dashboard_views.scorer_page'))
        else:
            response = redirect(url_for('index_views.index_page'))

        # Set cookie
        set_access_cookies(response, token)
        flash('Login successful!', 'success')
        return response

    # GET request – show login form
    return render_template('login.html')

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

    token = create_access_token(identity=user.id)
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