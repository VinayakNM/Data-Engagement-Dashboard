from App.models import *
from App.database import db
from sqlalchemy import func
from datetime import date
import secrets
import string



def get_total_participants():
    """Get total number of participants across all institutions."""
    return Participant.query.count()

def get_active_participants(season_id=None):
    """Get participants registered in current season."""
    if not season_id:
        # Get current season (most recent)
        current_season = Season.query.order_by(Season.year.desc()).first()
        if not current_season:
            return 0
        season_id = current_season.id
    
    # Count participants with registrations in this season
    return db.session.query(Participant.id)\
        .join(Registration)\
        .join(SeasonEvent)\
        .filter(SeasonEvent.season_id == season_id)\
        .distinct().count()

def get_participation_rate(season_id=None):
    """Calculate participation rate (participants with results vs registered)."""
    if not season_id:
        current_season = Season.query.order_by(Season.year.desc()).first()
        if not current_season:
            return 0
        season_id = current_season.id
    
    # Total registered in season
    total_reg = db.session.query(Registration.id)\
        .join(SeasonEvent)\
        .filter(SeasonEvent.season_id == season_id)\
        .count()
    
    if total_reg == 0:
        return 0
    
    # Total with results
    total_participated = db.session.query(Registration.id)\
        .join(SeasonEvent)\
        .filter(SeasonEvent.season_id == season_id)\
        .join(Result)\
        .distinct().count()
    
    return round((total_participated / total_reg) * 100, 1)

def get_institution_stats(season_id=None):
    """Get participation stats by institution."""
    if not season_id:
        current_season = Season.query.order_by(Season.year.desc()).first()
        if not current_season:
            return []
        season_id = current_season.id
    
    institutions = Institution.query.all()
    stats = []
    
    for inst in institutions:
        # Count participants for this institution
        participant_count = Participant.query.filter_by(institution_id=inst.id).count()
        
        # Count registrations in current season
        reg_count = db.session.query(Registration.id)\
            .join(Participant)\
            .filter(Participant.institution_id == inst.id)\
            .join(SeasonEvent)\
            .filter(SeasonEvent.season_id == season_id)\
            .count()
        
        # Count participants with results
        part_count = db.session.query(Registration.participant_id)\
            .join(Participant)\
            .filter(Participant.institution_id == inst.id)\
            .join(SeasonEvent)\
            .filter(SeasonEvent.season_id == season_id)\
            .join(Result)\
            .distinct().count()
        
        part_rate = round((part_count / reg_count * 100), 1) if reg_count > 0 else 0
        
        stats.append({
            'id': inst.id,
            'code': inst.code,
            'name': inst.name,
            'participants': participant_count,
            'registrations': reg_count,
            'participated': part_count,
            'participation_rate': part_rate,
            'user_count': len(inst.users)
        })
    
    return stats

def get_stage_completion(event_id=None):
    """Get completion rates for each stage of an event."""
    if not event_id:
        # Get Urban Challenge event
        urban = Event.query.filter_by(name='Urban Challenge').first()
        if not urban:
            return []
        event_id = urban.id
    
    # Get current season
    current_season = Season.query.order_by(Season.year.desc()).first()
    if not current_season:
        return []
    
    # Get season_event
    season_event = SeasonEvent.query.filter_by(
        season_id=current_season.id,
        event_id=event_id
    ).first()
    
    if not season_event:
        return []
    
    # Get stages for this event
    stages = Stage.query.filter_by(season_event_id=season_event.id).order_by(Stage.stage_number).all()
    
    # Get total registrations for this event
    total_reg = Registration.query.filter_by(season_event_id=season_event.id).count()
    
    if total_reg == 0:
        return [{'stage': s.stage_number, 'completion': 0} for s in stages]
    
    completion_data = []
    for stage in stages:
        # Count participants who have results for this stage
        completed = db.session.query(Result.registration_id)\
            .join(Registration)\
            .filter(Registration.season_event_id == season_event.id)\
            .filter(Result.stage_id == stage.id)\
            .distinct().count()

        completion_rate = round((completed / total_reg) * 100, 1) if total_reg > 0 else 0
        completion_data.append({
            'stage': stage.stage_number,
            'completion': completion_rate,
            'completed': completed,
            'total': total_reg
        })
    

    return completion_data


def get_participation_by_institution(season_id=None):
    """Get participation counts by institution for charts."""
    if not season_id:
        current_season = Season.query.order_by(Season.year.desc()).first()
        if not current_season:
            return []
        season_id = current_season.id
    
    results = db.session.query(
        Institution.code,
        func.count(Participant.id).label('count')
    ).join(Participant)\
     .join(Registration)\
     .join(SeasonEvent)\
     .filter(SeasonEvent.season_id == season_id)\
     .group_by(Institution.code)\
     .all()
    
    return [{'code': r[0], 'count': r[1]} for r in results]

def get_participation_status_breakdown(season_id=None):
    """Get counts for participated, no-show, pending for pie chart."""
    if not season_id:
        current_season = Season.query.order_by(Season.year.desc()).first()
        if not current_season:
            return {'participated': 0, 'no_show': 0, 'pending': 0}
        season_id = current_season.id
    
    today = date.today()
    
    # Get all registrations for the season
    registrations = db.session.query(Registration)\
        .join(SeasonEvent)\
        .filter(SeasonEvent.season_id == season_id)\
        .all()
    
    participated = 0
    no_show = 0
    pending = 0
    
    for reg in registrations:
        has_result = len(reg.results) > 0
        
        # Get event date
        event_date = None
        if reg.season_event and reg.season_event.end_date:
            event_date = reg.season_event.end_date
        elif reg.season_event and reg.season_event.start_date:
            event_date = reg.season_event.start_date
        
        if has_result:
            participated += 1
        elif event_date and event_date < today:
            no_show += 1
        else:
            pending += 1
    
    return {
        'participated': participated,
        'no_show': no_show,
        'pending': pending
    }

def get_admin_data():
    return Institution.query.all()


def generate_temp_password(length=10):
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def create_user_by_admin(firstname, lastname, username, email, password, role, institution_id=None):
    """Create a user of any role (admin, hr, scorer)"""
    
    # Map role to model class
    role_map = {
        'admin': Admin,
        'hr': HR,
        'scorer': Scorer
    }
    
    if role not in role_map:
        return None, f"Invalid role: {role}"
    
    UserClass = role_map[role]
    
    # Check if email already exists
    if User.query.filter_by(email=email).first():
        return None, "Email already registered"
    
    # For admin and scorer, institution_id should be None
    if role in ['admin', 'scorer']:
        institution_id = None
    
    # For HR, institution_id is required
    if role == 'hr' and not institution_id:
        return None, "Institution required for HR users"
    
    # Create the user
    if role == 'hr':
        user = UserClass(
            firstname=firstname,
            lastname=lastname,
            username=username,
            email=email,
            password=password,
            institution_id=institution_id
        )
    else:
        user = UserClass(
            firstname=firstname,
            lastname=lastname,
            username=username,
            email=email,
            password=password
        )
    
    # Set must_change_password flag
    user.must_change_password = True
    
    db.session.add(user)
    db.session.commit()
    
    return user, None


def get_all_users():
    """Return all users with their details."""
    return User.query.all()