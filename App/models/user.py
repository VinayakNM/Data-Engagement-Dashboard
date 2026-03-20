from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime
from App.database import db


# -------------------- User (base) --------------------
class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    firstname = db.Column(db.String(20), nullable=False)
    lastname = db.Column(db.String(50), nullable=False)
    username = db.Column(db.String(20), nullable=False, unique=True)
    email = db.Column(db.String(120), nullable=False, unique=True)
    password = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    is_active = db.Column(db.Boolean, default=True)

    institution_id = db.Column(db.Integer, db.ForeignKey('institution.id'), nullable=True)
    institution = db.relationship('Institution', backref=db.backref('users', lazy=True))

    __mapper_args__ = {
        'polymorphic_identity': 'user',
        'polymorphic_on': role
    }

    def __init__(self, firstname, lastname, username, email, password, institution_id=None):
        self.firstname = firstname
        self.lastname = lastname
        self.username = username
        self.email = email
        self.set_password(password)
        self.is_active = True
        self.institution_id = institution_id

    def get_json(self):
        return {
            'id': self.id,
            'firstname': self.firstname,
            'lastname': self.lastname,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'institution_id': self.institution_id
        }

    def set_password(self, password):
        """Create hashed password."""
        self.password = generate_password_hash(password)
    
    def check_password(self, password):
        """Check hashed password."""
        return check_password_hash(self.password, password)


# -------------------- Admin (User) --------------------
class Admin(User):
    __tablename__ = 'admins'
    __mapper_args__ = {'polymorphic_identity': 'admin'}
    
    id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)

    def __init__(self, firstname, lastname, username, email, password):
        super().__init__(firstname, lastname, username, email, password, institution_id=None)
        self.role = 'admin'


# -------------------- Scorer (User) --------------------
class Scorer(User):
    __tablename__ = 'scorers'
    __mapper_args__ = {'polymorphic_identity': 'scorer'}
    
    id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)

    def __init__(self, firstname, lastname, username, email, password):
        super().__init__(firstname, lastname, username, email, password, institution_id=None)
        self.role = 'scorer'


# -------------------- HR (User) --------------------
class HR(User):
    __tablename__ = 'hr_users'
    __mapper_args__ = {'polymorphic_identity': 'hr'}
    
    id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    
    def __init__(self, firstname, lastname, username, email, password, institution_id):
        super().__init__(firstname, lastname, username, email, password, institution_id)
        self.role = 'hr'
        if not institution_id:
            raise ValueError("HR users must be assigned to an institution")
        

# -------------------- PulseLeader (User) --------------------
class PulseLeader(User):
    __tablename__ = 'pulse_leaders'
    __mapper_args__ = {'polymorphic_identity': 'pulse_leader'}

    id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    social_media_handle = db.Column(db.String(100))

    def __init__(self, firstname, lastname, username, email, password, institution_id):
        super().__init__(firstname, lastname, username, email, password, institution_id)
        self.role = 'pulse_leader'


# -------------------- Institution --------------------
class Institution(db.Model):
    __tablename__ = 'institution'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(20), nullable=False, unique=True)

    def __init__(self, name, code):
        self.name = name
        self.code = code

    def get_json(self):
        return {
            'id': self.id,
            'name': self.name,
            'code': self.code
        }


# -------------------- Participant --------------------
class Participant(db.Model):
    __tablename__ = 'participant'
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    birth_date = db.Column(db.Date, nullable=True)
    sex = db.Column(db.String(1), nullable=True)  # M/F
    division = db.Column(db.String(20), nullable=True)
    contact = db.Column(db.String(50), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    institution_id = db.Column(db.Integer, db.ForeignKey('institution.id'), nullable=False)
    institution = db.relationship('Institution', backref=db.backref('participants', lazy=True))

    def __init__(self, first_name, last_name, institution_id, **kwargs):
        self.first_name = first_name
        self.last_name = last_name
        self.institution_id = institution_id
        for k, v in kwargs.items():
            setattr(self, k, v)

    def get_json(self):
        return {
            'id': self.id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'birth_date': self.birth_date.isoformat() if self.birth_date else None,
            'sex': self.sex,
            'division': self.division,
            'contact': self.contact,
            'email': self.email,
            'institution_id': self.institution_id
        }


# -------------------- Season --------------------
class Season(db.Model):
    __tablename__ = 'season'
    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.Integer, nullable=False, unique=True)
    description = db.Column(db.String(200))

    def __init__(self, year, description=''):
        self.year = year
        self.description = description


# -------------------- Event --------------------
class Event(db.Model):
    __tablename__ = 'event'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(200))
    event_type = db.Column(db.String(20))  # eg, 'run', 'walk'

    def __init__(self, name, **kwargs):
        self.name = name
        for k, v in kwargs.items():
            setattr(self, k, v)


# -------------------- Season-Event Bridge --------------------
class SeasonEvent(db.Model):
    __tablename__ = 'season_event'
    id = db.Column(db.Integer, primary_key=True)
    season_id = db.Column(db.Integer, db.ForeignKey('season.id'), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)

    season = db.relationship('Season', backref=db.backref('season_events', lazy=True))
    event = db.relationship('Event', backref=db.backref('season_events', lazy=True))

    __table_args__ = (db.UniqueConstraint('season_id', 'event_id', name='_season_event_uc'),)

    def __init__(self, season_id, event_id, **kwargs):
        self.season_id = season_id
        self.event_id = event_id
        for k, v in kwargs.items():
            setattr(self, k, v)


# -------------------- Stage --------------------
class Stage(db.Model):
    __tablename__ = 'stage'
    id = db.Column(db.Integer, primary_key=True)
    season_event_id = db.Column(db.Integer, db.ForeignKey('season_event.id'), nullable=False)
    stage_number = db.Column(db.Integer, nullable=True)
    location = db.Column(db.String(100), nullable=True)
    stage_date = db.Column(db.Date, nullable=True)

    season_event = db.relationship('SeasonEvent', backref=db.backref('stages', lazy=True))

    __table_args__ = (db.UniqueConstraint('season_event_id', 'stage_number', name='_stage_uc'),)

    def __init__(self, season_event_id, stage_number, **kwargs):
        self.season_event_id = season_event_id
        self.stage_number = stage_number
        for k, v in kwargs.items():
            setattr(self, k, v)


# -------------------- Registration --------------------
class Registration(db.Model):
    __tablename__ = 'registration'
    id = db.Column(db.Integer, primary_key=True)
    participant_id = db.Column(db.Integer, db.ForeignKey('participant.id'), nullable=False)
    season_event_id = db.Column(db.Integer, db.ForeignKey('season_event.id'), nullable=False)
    registration_date = db.Column(db.DateTime, default=datetime.utcnow)
    division = db.Column(db.String(20), nullable=True)  # optional override

    participant = db.relationship('Participant', backref=db.backref('registrations', lazy=True))
    season_event = db.relationship('SeasonEvent', backref=db.backref('registrations', lazy=True))

    __table_args__ = (db.UniqueConstraint('participant_id', 'season_event_id', name='_part_seasonevent_uc'),)

    def __init__(self, participant_id, season_event_id, **kwargs):
        self.participant_id = participant_id
        self.season_event_id = season_event_id
        for k, v in kwargs.items():
            setattr(self, k, v)


# -------------------- BibNo --------------------
class BibNo(db.Model):
    __tablename__ = 'bibNo'
    id = db.Column(db.Integer, primary_key=True)
    bib_value = db.Column(db.String(50), nullable=False)
    institution_id = db.Column(db.Integer, db.ForeignKey('institution.id'), nullable=True)
    season_id = db.Column(db.Integer, db.ForeignKey('season.id'), nullable=False)

    institution = db.relationship('Institution')
    season = db.relationship('Season')
    
    __table_args__ = (db.UniqueConstraint('season_id', 'bib_value', name='_bibNo_season_uc'),)

    def __init__(self, bib_value, season_id, institution_id=None):
        self.bib_value = bib_value
        self.season_id = season_id
        self.institution_id = institution_id


# -------------------- BibTag --------------------
class BibTag(db.Model):
    __tablename__ = 'bibTag'
    id = db.Column(db.Integer, primary_key=True)
    bib_value = db.Column(db.String(50), nullable=False)
    institution_id = db.Column(db.Integer, db.ForeignKey('institution.id'), nullable=True)
    season_id = db.Column(db.Integer, db.ForeignKey('season.id'), nullable=False)

    institution = db.relationship('Institution')
    season = db.relationship('Season')
    
    __table_args__ = (db.UniqueConstraint('season_id', 'bib_value', name='_bibTag_season_uc'),)

    def __init__(self, bib_value, season_id, institution_id=None):
        self.bib_value = bib_value
        self.season_id = season_id
        self.institution_id = institution_id


# -------------------- BibNo Assignment --------------------
class BibNoAssignment(db.Model):
    __tablename__ = 'bib_no_assignment'
    registration_id = db.Column(db.Integer, db.ForeignKey('registration.id'), primary_key=True, nullable=False)
    bib_no_id = db.Column(db.Integer, db.ForeignKey('bibNo.id'), primary_key=True, nullable=False)
    assign_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='active')  # 'active', 'lost', 'replaced'

    registration = db.relationship('Registration', backref=db.backref('bib_no_assignments', lazy=True))
    bib_no = db.relationship('BibNo')

    def __init__(self, registration_id, bib_no_id, **kwargs):
        self.registration_id = registration_id
        self.bib_no_id = bib_no_id
        for k, v in kwargs.items():
            setattr(self, k, v)


# -------------------- BibTag Assignment --------------------
class BibTagAssignment(db.Model):
    __tablename__ = 'bib_tag_assignment'
    registration_id = db.Column(db.Integer, db.ForeignKey('registration.id'), primary_key=True, nullable=False)
    bib_tag_id = db.Column(db.Integer, db.ForeignKey('bibTag.id'), primary_key=True, nullable=False)
    assign_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='active')  # 'active', 'lost', 'replaced'

    registration = db.relationship('Registration', backref=db.backref('bib_tag_assignments', lazy=True))
    bib_tag = db.relationship('BibTag')

    def __init__(self, registration_id, bib_tag_id, **kwargs):
        self.registration_id = registration_id
        self.bib_tag_id = bib_tag_id
        for k, v in kwargs.items():
            setattr(self, k, v)


# -------------------- Result --------------------
class Result(db.Model):
    __tablename__ = 'result'
    id = db.Column(db.Integer, primary_key=True)
    registration_id = db.Column(db.Integer, db.ForeignKey('registration.id'), nullable=False)
    stage_id = db.Column(db.Integer, db.ForeignKey('stage.id'), nullable=False)
    finish_time = db.Column(db.String(20), nullable=True)
    placement = db.Column(db.Integer, nullable=True)
    points = db.Column(db.Integer, nullable=True)

    registration = db.relationship('Registration', backref=db.backref('results', lazy=True))
    stage = db.relationship('Stage', backref=db.backref('results', lazy=True))

    __table_args__ = (db.UniqueConstraint('registration_id', 'stage_id', name='_result_reg_stage_uc'),)

    def __init__(self, registration_id, stage_id, **kwargs):
        self.registration_id = registration_id
        self.stage_id = stage_id
        for k, v in kwargs.items():
            setattr(self, k, v)