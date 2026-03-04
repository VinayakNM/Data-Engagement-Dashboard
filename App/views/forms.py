from flask import Blueprint, render_template
from flask_jwt_extended import jwt_required

forms_views = Blueprint('forms_views', __name__)

@forms_views.route('/eventform')
@jwt_required()
def event_form():
    return render_template('Forms/EventForm.html')

@forms_views.route('/institutionform')
@jwt_required()
def institution_form():
    return render_template('Forms/InstitutionForm.html')

@forms_views.route('/seasonform')
@jwt_required()
def season_form():
    return render_template('Forms/SeasonForm.html')

@forms_views.route('/hrregistration')
@jwt_required()
def hr_registration():
    return render_template('Forms/RegistrationForm.html')
