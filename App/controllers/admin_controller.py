from App.models import *
from App.database import db
from sqlalchemy import func
from datetime import date


def _base_reg_query(season_id, event_id=None, division=None, institution_code=None):
    """
    Returns a base Registration query pre-filtered by season, and optionally
    by event, division, and institution. Used by all metric functions so that
    every chart/counter respects the same active filters.
    """
    q = db.session.query(Registration)\
        .join(SeasonEvent)\
        .filter(SeasonEvent.season_id == season_id)

    if event_id:
        q = q.filter(SeasonEvent.event_id == event_id)

    if division:
        # division is stored on both Participant and Registration
        q = q.join(Participant, Registration.participant_id == Participant.id)\
             .filter(
                 db.or_(
                     Registration.division == division,
                     Participant.division == division
                 )
             )
    elif institution_code:
        # only join Participant if we didn't already for division
        q = q.join(Participant, Registration.participant_id == Participant.id)

    if institution_code:
        inst = Institution.query.filter_by(code=institution_code).first()
        if inst:
            q = q.filter(Participant.institution_id == inst.id)

    return q


def get_total_participants(season_id=None, event_id=None, division=None, institution_code=None):
    """Get total participants registered, respecting all active filters."""
    if not season_id:
        current_season = Season.query.filter_by(status='active').order_by(Season.year.desc()).first()
        if not current_season:
            return 0
        season_id = current_season.id

    return _base_reg_query(season_id, event_id, division, institution_code)\
        .with_entities(Registration.participant_id).distinct().count()


def get_active_participants(season_id=None, event_id=None, division=None, institution_code=None):
    """Get participants who have at least one result (participated)."""
    if not season_id:
        current_season = Season.query.order_by(Season.year.desc()).first()
        if not current_season:
            return 0
        season_id = current_season.id

    return _base_reg_query(season_id, event_id, division, institution_code)\
        .join(Result, Registration.id == Result.registration_id)\
        .with_entities(Registration.participant_id).distinct().count()


def get_participation_rate(season_id=None, event_id=None, division=None, institution_code=None):
    """Calculate participation rate (participants with results vs registered)."""
    if not season_id:
        current_season = Season.query.order_by(Season.year.desc()).first()
        if not current_season:
            return 0
        season_id = current_season.id

    total_reg = _base_reg_query(season_id, event_id, division, institution_code).count()
    if total_reg == 0:
        return 0

    total_participated = _base_reg_query(season_id, event_id, division, institution_code)\
        .join(Result, Registration.id == Result.registration_id)\
        .with_entities(Registration.id).distinct().count()

    return round((total_participated / total_reg) * 100, 1)


def get_institution_stats(season_id=None, event_id=None, division=None, institution_code=None):
    """Get participation stats by institution, respecting all active filters."""
    if not season_id:
        current_season = Season.query.order_by(Season.year.desc()).first()
        if not current_season:
            return []
        season_id = current_season.id

    institutions = Institution.query.all()
    stats = []

    for inst in institutions:
        # Skip institutions that don't match the institution filter
        if institution_code and inst.code != institution_code:
            continue

        participant_count = Participant.query.filter_by(institution_id=inst.id).count()

        base = db.session.query(Registration)\
            .join(SeasonEvent)\
            .filter(SeasonEvent.season_id == season_id)\
            .join(Participant, Registration.participant_id == Participant.id)\
            .filter(Participant.institution_id == inst.id)

        if event_id:
            base = base.filter(SeasonEvent.event_id == event_id)
        if division:
            base = base.filter(
                db.or_(
                    Registration.division == division,
                    Participant.division == division
                )
            )

        reg_count  = base.count()
        part_count = base.join(Result, Registration.id == Result.registration_id)\
                         .with_entities(Registration.participant_id).distinct().count()

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

def get_stage_completion(season_id=None, event_id=None, institution_code=None):
    """Get completion rates for each stage of an event, respecting active filters."""
    # Resolve season
    if not season_id:
        current_season = Season.query.filter_by(status='active').order_by(Season.year.desc()).first()
        if not current_season:
            current_season = Season.query.order_by(Season.year.desc()).first()
        if not current_season:
            return []
        season_id = current_season.id

    # Resolve event — use filter or fall back to Urban Challenge then first available
    if not event_id:
        urban = Event.query.filter_by(name='Urban Challenge').first()
        if urban:
            event_id = urban.id
        else:
            # Find first event linked to this season
            se_any = SeasonEvent.query.filter_by(season_id=season_id).first()
            if se_any:
                event_id = se_any.event_id
            else:
                return []

    season_event = SeasonEvent.query.filter_by(
        season_id=season_id, event_id=event_id
    ).first()
    if not season_event:
        return []

    stages = Stage.query.filter_by(
        season_event_id=season_event.id
    ).order_by(Stage.stage_number).all()
    if not stages:
        return []

    # Base registrations — optionally filtered by institution
    base_q = db.session.query(Registration.id).filter(
        Registration.season_event_id == season_event.id
    )
    if institution_code:
        inst = Institution.query.filter_by(code=institution_code).first()
        if inst:
            base_q = base_q.join(
                Participant, Registration.participant_id == Participant.id
            ).filter(Participant.institution_id == inst.id)

    total_reg = base_q.count()
    if total_reg == 0:
        return [{'stage': s.stage_number, 'completion': 0, 'completed': 0, 'total': 0} for s in stages]

    reg_ids = [r[0] for r in base_q.all()]
    completion_data = []
    for stage in stages:
        completed = db.session.query(func.count(func.distinct(Result.registration_id)))            .filter(
                Result.stage_id == stage.id,
                Result.registration_id.in_(reg_ids)
            ).scalar() or 0

        completion_rate = round((completed / total_reg) * 100, 1) if total_reg > 0 else 0
        completion_data.append({
            'stage': stage.stage_number,
            'completion': completion_rate,
            'completed': completed,
            'total': total_reg,
        })

    return completion_data


def get_participation_by_institution(season_id=None, event_id=None, division=None, institution_code=None):
    """Get participation counts by institution for the bar chart."""
    if not season_id:
        current_season = Season.query.order_by(Season.year.desc()).first()
        if not current_season:
            return []
        season_id = current_season.id

    q = db.session.query(
        Institution.code,
        func.count(func.distinct(Registration.participant_id)).label('count')
    ).join(Participant, Institution.id == Participant.institution_id)\
     .join(Registration, Participant.id == Registration.participant_id)\
     .join(SeasonEvent, Registration.season_event_id == SeasonEvent.id)\
     .filter(SeasonEvent.season_id == season_id)

    if event_id:
        q = q.filter(SeasonEvent.event_id == event_id)
    if division:
        q = q.filter(
            db.or_(
                Registration.division == division,
                Participant.division == division
            )
        )
    if institution_code:
        inst = Institution.query.filter_by(code=institution_code).first()
        if inst:
            q = q.filter(Institution.id == inst.id)

    results = q.group_by(Institution.code).all()
    return [{'code': r[0], 'count': r[1]} for r in results]


def get_participation_status_breakdown(season_id=None, event_id=None, division=None, institution_code=None):
    """Get counts for participated, no-show, pending for pie chart."""
    if not season_id:
        current_season = Season.query.order_by(Season.year.desc()).first()
        if not current_season:
            return {'participated': 0, 'no_show': 0, 'pending': 0}
        season_id = current_season.id

    today = date.today()

    registrations = _base_reg_query(season_id, event_id, division, institution_code).all()

    participated = 0
    no_show = 0
    pending = 0

    for reg in registrations:
        has_result = len(reg.results) > 0

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


def get_all_users():
    """Return all users with their details."""
    return User.query.all()

def get_stage_funnel(season_id=None, event_id=None, institution_code=None):
    """
    Funnel: for each stage of an event, return how many distinct participants
    completed it. Respects season, event and institution filters.
    Returns: { event_name, stages: [{stage, label, count, pct_of_stage1}] }
    """
    if not season_id:
        current_season = Season.query.order_by(Season.year.desc()).first()
        if not current_season:
            return {}
        season_id = current_season.id

    # Pick event — use filter_event or fall back to Urban Challenge
    if event_id:
        event = Event.query.get(event_id)
    else:
        event = Event.query.filter_by(name='Urban Challenge').first()
        if not event:
            event = Event.query.first()
    if not event:
        return {}

    season_event = SeasonEvent.query.filter_by(
        season_id=season_id, event_id=event.id
    ).first()
    if not season_event:
        return {}

    stages = Stage.query.filter_by(
        season_event_id=season_event.id
    ).order_by(Stage.stage_number).all()
    if not stages:
        return {}

    # Base registrations (optionally filtered by institution)
    base = db.session.query(Registration.id).filter(
        Registration.season_event_id == season_event.id
    )
    if institution_code:
        inst = Institution.query.filter_by(code=institution_code).first()
        if inst:
            base = base.join(Participant, Registration.participant_id == Participant.id)\
                       .filter(Participant.institution_id == inst.id)
    reg_ids = [r[0] for r in base.all()]
    if not reg_ids:
        return {}

    funnel = []
    stage1_count = None
    for s in stages:
        count = db.session.query(func.count(func.distinct(Result.registration_id)))\
            .filter(Result.stage_id == s.id,
                    Result.registration_id.in_(reg_ids)).scalar() or 0
        if stage1_count is None:
            stage1_count = count
        pct = round(count / stage1_count * 100, 1) if stage1_count else 0
        funnel.append({
            'stage':        s.stage_number,
            'label':        f'Stage {s.stage_number}' + (f' ({s.distance})' if s.distance else ''),
            'count':        count,
            'pct_of_stage1': pct,
        })

    return {'event_name': event.name, 'stages': funnel, 'total_registered': len(reg_ids)}


def get_gender_split(season_id=None, event_id=None, institution_code=None):
    """
    Returns: [{'sex': 'M', 'count': n}, {'sex': 'F', 'count': n}]
    Based on participants registered in the filtered season/event/institution.
    """
    if not season_id:
        current_season = Season.query.order_by(Season.year.desc()).first()
        if not current_season:
            return []
        season_id = current_season.id

    q = db.session.query(
        Participant.sex,
        func.count(func.distinct(Participant.id)).label('count')
    ).join(Registration, Participant.id == Registration.participant_id)\
     .join(SeasonEvent, Registration.season_event_id == SeasonEvent.id)\
     .filter(SeasonEvent.season_id == season_id,
             Participant.sex.isnot(None),
             Participant.sex != '')

    if event_id:
        q = q.filter(SeasonEvent.event_id == event_id)
    if institution_code:
        inst = Institution.query.filter_by(code=institution_code).first()
        if inst:
            q = q.filter(Participant.institution_id == inst.id)

    rows = q.group_by(Participant.sex).all()
    return [{'sex': r[0].upper(), 'count': r[1]} for r in rows]


def get_age_group_distribution(season_id=None, event_id=None, institution_code=None):
    """
    Returns age group counts and gender breakdown per group using the DIV field.
    Div codes like M2029, F3039 encode both sex and age band.
    Returns: [{'group': '20-29', 'M': n, 'F': n, 'total': n}, ...]
    """
    if not season_id:
        current_season = Season.query.order_by(Season.year.desc()).first()
        if not current_season:
            return []
        season_id = current_season.id

    q = db.session.query(
        Participant.division,
        func.count(func.distinct(Participant.id)).label('count')
    ).join(Registration, Participant.id == Registration.participant_id)\
     .join(SeasonEvent, Registration.season_event_id == SeasonEvent.id)\
     .filter(SeasonEvent.season_id == season_id,
             Participant.division.isnot(None),
             Participant.division != '')

    if event_id:
        q = q.filter(SeasonEvent.event_id == event_id)
    if institution_code:
        inst = Institution.query.filter_by(code=institution_code).first()
        if inst:
            q = q.filter(Participant.institution_id == inst.id)

    rows = q.group_by(Participant.division).all()

    # Aggregate into age band buckets
    AGE_BANDS = ['20-29', '30-39', '40-49', '50-59', '60+']
    DIV_TO_BAND = {
        '2029': '20-29', '3039': '30-39', '4049': '40-49',
        '5059': '50-59', '60+': '60+', '60P': '60+',
    }
    buckets = {b: {'group': b, 'M': 0, 'F': 0, 'total': 0} for b in AGE_BANDS}

    for div, count in rows:
        div = str(div).strip().upper()
        sex  = div[0] if div and div[0] in ('M', 'F') else None
        band_key = div[1:] if sex else div
        band = DIV_TO_BAND.get(band_key)
        if not band or not sex:
            continue
        buckets[band][sex]     = buckets[band].get(sex, 0) + count
        buckets[band]['total'] += count

    return [b for b in buckets.values() if b['total'] > 0]