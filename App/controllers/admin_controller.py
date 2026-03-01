from App.models import HR, Institution
from App.database import db


def create_hr_user(firstname, lastname, username, email, password, institution_id):
    """Create a new HR user"""
    inst = Institution.query.get(institution_id)
    
    if not inst:
        return None, "Institution not found."
    
    #Checking if account already exists
    if HR.query.filter_by(email=email).first():
        return None, "Email already registered."
    
    hr = HR(
        firstname=firstname,
        lastname=lastname,
        username=username,
        email=email,
        password=password,
        institution_id=institution_id
    )
    db.session.add(hr)
    db.session.commit()
    return hr, None