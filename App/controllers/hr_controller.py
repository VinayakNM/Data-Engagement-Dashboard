from App.models import Participant, Registration, Result, Institution
from App.database import db
from datetime import date


def get_hr_stats(institution_id):
    # Get current date to check if event has passed
    today = date.today()
    
    # Get all participants for this institution
    participants = Participant.query.filter_by(institution_id=institution_id).all()

    # Get all participants count for institution
    total_participants = len(participants)
    
    # Get all registrations for this institution's participants
    registrations = db.session.query(Registration)\
        .join(Participant)\
        .filter(Participant.institution_id == institution_id)\
        .all()
    
    # Count unique participants with at least one registration
    registered_participant_ids = set()
    for reg in registrations:
        registered_participant_ids.add(reg.participant_id)
    
    registered_count = len(registered_participant_ids)
    
    # Count participants who have participated (have at least one result)
    participated_participant_ids = set()
    no_show_participant_ids = set()
    
    for reg in registrations:
        # Check if this registration has any results
        has_result = len(reg.results) > 0
        
        # Get the event date to check if it has passed
        event_date = None
        if reg.season_event and reg.season_event.end_date:
            event_date = reg.season_event.end_date
        elif reg.season_event and reg.season_event.start_date:
            event_date = reg.season_event.start_date
        
        if has_result:
            participated_participant_ids.add(reg.participant_id)
        elif event_date and event_date < today:
            # Event has passed and no result = no-show
            no_show_participant_ids.add(reg.participant_id)
    
    participated_count = len(participated_participant_ids)
    no_show_count = len(no_show_participant_ids)
    
    # Add flags to participants for template
    for p in participants:
        p.has_result = p.id in participated_participant_ids
        p.is_no_show = p.id in no_show_participant_ids
        p.is_registered = p.id in registered_participant_ids
    
    return {
        'total_participants': total_participants,
        'reg_count': registered_count,
        'part_count': participated_count,
        'no_show_count': no_show_count,
        'participants': participants,
        'institution': Institution.query.get(institution_id)
    }


def get_available_events(institution_id):
    """Get events available for registration."""
    from App.models import SeasonEvent, Event, Season
    
    # Get current season (most recent)
    current_season = Season.query.order_by(Season.year.desc()).first()
    if not current_season:
        return []
    
    # Get all events in current season
    season_events = SeasonEvent.query.filter_by(season_id=current_season.id).all()
    
    events = []
    for se in season_events:
        event = Event.query.get(se.event_id)
        events.append({
            'id': se.id,
            'name': event.name,
            'date': se.start_date or 'TBD'
        })
    
    return events


def register_participants(participant_ids, season_event_id):
    """Register multiple participants for an event."""
    from App.models import Registration
    
    count = 0
    for pid in participant_ids:
        # Check if already registered
        existing = Registration.query.filter_by(
            participant_id=pid,
            season_event_id=season_event_id
        ).first()
        
        if not existing:
            reg = Registration(
                participant_id=pid,
                season_event_id=season_event_id
            )
            db.session.add(reg)
            count += 1
    
    db.session.commit()
    return count