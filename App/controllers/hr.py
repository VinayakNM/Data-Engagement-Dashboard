"""
App/controllers/hr.py
All API logic for the HR dashboard and participant management.
"""
from datetime import date, datetime
from App.database import db
from App.models import (
    Institution, Participant, Season, Event, SeasonEvent,
    Stage, Registration, Result, BibNo, BibTag,
    BibNoAssignment, BibTagAssignment
)
from sqlalchemy import func


# ── Dashboard stats ────────────────────────────────────────

def get_hr_dashboard_data(institution_id, season_ids=None, event_types=None, divisions=None):
    """
    Returns per-season stats for the HR dashboard charts.
    season_ids: list of season IDs to include (None = all)
    """
    seasons = Season.query.order_by(Season.year).all()
    if season_ids:
        seasons = [s for s in seasons if s.id in season_ids]

    result = []
    for season in seasons:
        # Base query: participants from this institution registered in this season
        reg_q = (
            db.session.query(Registration)
            .join(SeasonEvent, Registration.season_event_id == SeasonEvent.id)
            .join(Participant, Registration.participant_id == Participant.id)
            .filter(SeasonEvent.season_id == season.id)
            .filter(Participant.institution_id == institution_id)
        )
        if event_types:
            reg_q = reg_q.join(Event, SeasonEvent.event_id == Event.id).filter(Event.event_type.in_(event_types))
        if divisions:
            reg_q = reg_q.filter(Participant.division.in_(divisions))

        registered = reg_q.count()

        # Participated = has at least one Result
        participated = (
            db.session.query(func.count(func.distinct(Registration.id)))
            .join(SeasonEvent, Registration.season_event_id == SeasonEvent.id)
            .join(Participant, Registration.participant_id == Participant.id)
            .join(Result, Result.registration_id == Registration.id)
            .filter(SeasonEvent.season_id == season.id)
            .filter(Participant.institution_id == institution_id)
            .scalar() or 0
        )

        no_shows = registered - participated

        # Division breakdown for chart
        div_q = (
            db.session.query(Participant.division, func.count(Registration.id).label('cnt'))
            .join(Registration, Participant.id == Registration.participant_id)
            .join(SeasonEvent, Registration.season_event_id == SeasonEvent.id)
            .filter(SeasonEvent.season_id == season.id)
            .filter(Participant.institution_id == institution_id)
            .filter(Participant.division.isnot(None))
            .group_by(Participant.division)
            .all()
        )

        # Stage progression for line chart (Urban Challenge stages)
        stage_q = (
            db.session.query(Stage.stage_number, func.count(Result.id).label('finishers'))
            .join(Result, Stage.id == Result.stage_id)
            .join(Registration, Result.registration_id == Registration.id)
            .join(Participant, Registration.participant_id == Participant.id)
            .join(SeasonEvent, Stage.season_event_id == SeasonEvent.id)
            .filter(SeasonEvent.season_id == season.id)
            .filter(Participant.institution_id == institution_id)
            .group_by(Stage.stage_number)
            .order_by(Stage.stage_number)
            .all()
        )

        result.append({
            'season_id':   season.id,
            'year':        season.year,
            'registered':  registered,
            'participated': participated,
            'no_shows':    no_shows,
            'part_rate':   round(participated / registered * 100, 1) if registered else 0,
            'division_breakdown': [{'division': d, 'count': c} for d, c in div_q],
            'stage_progression':  [{'stage': s, 'finishers': f} for s, f in stage_q],
        })

    return result


def get_hr_filter_options(institution_id):
    """Returns available seasons, events, divisions for the filter panel."""
    seasons = Season.query.order_by(Season.year).all()
    events  = Event.query.order_by(Event.name).all()
    divs    = (
        db.session.query(Participant.division)
        .filter(Participant.institution_id == institution_id)
        .filter(Participant.division.isnot(None))
        .distinct()
        .order_by(Participant.division)
        .all()
    )
    return {
        'seasons':   [{'id': s.id, 'year': s.year} for s in seasons],
        'events':    [{'id': e.id, 'name': e.name, 'type': e.event_type} for e in events],
        'divisions': [d[0] for d in divs],
    }


# ── Participant CRUD ───────────────────────────────────────

def _calc_division(sex, birth_date):
    """Auto-calculate division code from sex and birth year."""
    if not sex or not birth_date:
        return None
    try:
        if isinstance(birth_date, str):
            birth_date = datetime.strptime(birth_date, '%Y-%m-%d').date()
        age  = (date.today() - birth_date).days // 365
        prefix = sex[0].upper()
        if   age < 20: suffix = '2029'
        elif age < 30: suffix = '3039'
        elif age < 40: suffix = '4049'
        elif age < 50: suffix = '5059'
        else:          suffix = '60+'
        return f"{prefix}{suffix}"
    except Exception:
        return None


def calc_age(birth_date):
    if not birth_date:
        return None
    try:
        if isinstance(birth_date, str):
            birth_date = datetime.strptime(birth_date, '%Y-%m-%d').date()
        return (date.today() - birth_date).days // 365
    except Exception:
        return None


def list_participants(institution_id, season_id=None):
    """All participants for this institution with their registration summary."""
    parts = Participant.query.filter_by(institution_id=institution_id).order_by(
        Participant.last_name, Participant.first_name).all()

    result = []
    for p in parts:
        # Which events are they registered for?
        regs = Registration.query.filter_by(participant_id=p.id).all()
        event_names = []
        statuses    = []
        for r in regs:
            se = SeasonEvent.query.get(r.season_event_id)
            if se:
                if season_id and se.season_id != season_id:
                    continue
                event_names.append(se.event.name)
                # Has result = Completed, else Active
                has_result = Result.query.filter_by(registration_id=r.id).first()
                statuses.append('Completed' if has_result else 'Active')

        result.append({
            'id':         p.id,
            'first_name': p.first_name,
            'last_name':  p.last_name,
            'full_name':  f"{p.first_name} {p.last_name}",
            'division':   p.division or '—',
            'sex':        p.sex or '',
            'birth_date': p.birth_date.isoformat() if p.birth_date else None,
            'age':        calc_age(p.birth_date),
            'email':      p.email or '',
            'contact':    p.contact or '',
            'events':     ', '.join(event_names) if event_names else 'Not Registered',
            'status':     statuses[0] if statuses else 'Not Registered',
            'institution_id': p.institution_id,
        })
    return result


def get_participant(participant_id):
    p = Participant.query.get(participant_id)
    if not p:
        return None
    regs = Registration.query.filter_by(participant_id=p.id).all()
    reg_list = []
    for r in regs:
        se  = SeasonEvent.query.get(r.season_event_id)
        bib = BibNoAssignment.query.filter_by(registration_id=r.id).first()
        reg_list.append({
            'registration_id': r.id,
            'season_event_id': se.id,
            'season_year':     se.season.year if se else None,
            'event_name':      se.event.name if se else None,
            'bib_no':          bib.bib_no.bib_value if bib else None,
        })
    return {
        'id': p.id, 'first_name': p.first_name, 'last_name': p.last_name,
        'birth_date': p.birth_date.isoformat() if p.birth_date else None,
        'age': calc_age(p.birth_date),
        'sex': p.sex or '',
        'division': p.division or '',
        'email': p.email or '', 'contact': p.contact or '',
        'institution_id': p.institution_id,
        'registrations': reg_list,
    }


def create_participant(data, institution_id):
    """Create a single participant. Returns (participant, error_string)."""
    fn = (data.get('first_name') or '').strip()
    ln = (data.get('last_name')  or '').strip()
    if not fn or not ln:
        return None, 'first_name and last_name are required'

    bd_str = data.get('birth_date') or None
    bd = None
    if bd_str:
        try:
            bd = datetime.strptime(bd_str, '%Y-%m-%d').date()
        except ValueError:
            return None, f'Invalid birth_date format: {bd_str}'

    sex = (data.get('sex') or '').strip().upper()[:1] or None
    div = _calc_division(sex, bd) if sex and bd else data.get('division') or None

    p = Participant(
        first_name=fn, last_name=ln,
        institution_id=institution_id,
        birth_date=bd, sex=sex, division=div,
        email=(data.get('email') or '').strip() or None,
        contact=(data.get('contact') or '').strip() or None,
    )
    db.session.add(p)
    db.session.flush()
    return p, None


def update_participant(participant_id, data, institution_id):
    p = Participant.query.filter_by(id=participant_id, institution_id=institution_id).first()
    if not p:
        return None, 'Participant not found'
    if 'first_name' in data: p.first_name = data['first_name'].strip()
    if 'last_name'  in data: p.last_name  = data['last_name'].strip()
    if 'email'      in data: p.email      = data['email'].strip() or None
    if 'contact'    in data: p.contact    = data['contact'].strip() or None
    if 'sex'        in data:
        p.sex = (data['sex'] or '').upper()[:1] or None
    if 'birth_date' in data and data['birth_date']:
        try:
            p.birth_date = datetime.strptime(data['birth_date'], '%Y-%m-%d').date()
        except ValueError:
            return None, 'Invalid birth_date'
    # Recalculate division
    p.division = _calc_division(p.sex, p.birth_date) or p.division
    db.session.commit()
    return p, None


def delete_participant(participant_id, institution_id):
    p = Participant.query.filter_by(id=participant_id, institution_id=institution_id).first()
    if not p:
        return False, 'Not found'
    # Remove registrations + results
    for reg in p.registrations:
        Result.query.filter_by(registration_id=reg.id).delete()
        BibNoAssignment.query.filter_by(registration_id=reg.id).delete()
        BibTagAssignment.query.filter_by(registration_id=reg.id).delete()
    Registration.query.filter_by(participant_id=p.id).delete()
    db.session.delete(p)
    db.session.commit()
    return True, None


def check_duplicate(first_name, last_name, institution_id):
    """Check if a participant with same name exists at this institution."""
    existing = Participant.query.filter(
        Participant.institution_id == institution_id,
        func.lower(Participant.first_name) == first_name.lower(),
        func.lower(Participant.last_name)  == last_name.lower(),
    ).first()
    return existing is not None


def bulk_create_participants(rows, institution_id):
    """
    Import a list of dicts from CSV/Excel.
    Returns (added_count, skipped_count, errors[]).
    """
    added, skipped, errors = 0, 0, []
    for i, row in enumerate(rows, 1):
        fn = str(row.get('first_name') or row.get('First Name') or '').strip()
        ln = str(row.get('last_name')  or row.get('Last Name')  or '').strip()
        if not fn or not ln:
            skipped += 1
            continue
        if check_duplicate(fn, ln, institution_id):
            errors.append(f"Row {i}: {fn} {ln} already exists — skipped")
            skipped += 1
            continue
        p, err = create_participant({
            'first_name': fn,
            'last_name':  ln,
            'birth_date': str(row.get('birth_date') or row.get('Birth Date') or '').strip() or None,
            'sex':        str(row.get('sex')         or row.get('Sex')        or '').strip() or None,
            'email':      str(row.get('email')       or row.get('Email')      or '').strip() or None,
            'contact':    str(row.get('contact')     or row.get('Phone')      or '').strip() or None,
        }, institution_id)
        if err:
            errors.append(f"Row {i}: {err}")
            skipped += 1
        else:
            added += 1
    db.session.commit()
    return added, skipped, errors


# ── Event Registration ─────────────────────────────────────

def get_available_events(institution_id):
    """Current season's events available for registration."""
    latest_season = Season.query.order_by(Season.year.desc()).first()
    if not latest_season:
        return []
    ses = SeasonEvent.query.filter_by(season_id=latest_season.id, status='active').all()
    return [{'id': se.id, 'event_name': se.event.name,
             'event_type': se.event.event_type,
             'start_date': se.start_date.isoformat() if se.start_date else None,
             'season_year': latest_season.year} for se in ses]


def _next_bib(season_id, institution_id):
    """Auto-generate next bib number for this institution/season."""
    existing = (BibNo.query
                .filter_by(season_id=season_id, institution_id=institution_id)
                .order_by(BibNo.id.desc()).first())
    if existing:
        try:
            return str(int(existing.bib_value) + 1)
        except ValueError:
            pass
    # Start from 1001
    count = BibNo.query.filter_by(season_id=season_id, institution_id=institution_id).count()
    return str(1001 + count)


def register_participant_for_events(participant_id, season_event_ids, institution_id):
    """
    Register participant for one or more SeasonEvents.
    Auto-assigns a BibNo for each registration.
    Returns (registrations_created, error).
    """
    p = Participant.query.filter_by(id=participant_id, institution_id=institution_id).first()
    if not p:
        return [], 'Participant not found'

    created = []
    for se_id in season_event_ids:
        se = SeasonEvent.query.get(se_id)
        if not se:
            continue
        # Check not already registered
        existing = Registration.query.filter_by(
            participant_id=p.id, season_event_id=se_id).first()
        if existing:
            continue

        reg = Registration(participant_id=p.id, season_event_id=se_id)
        db.session.add(reg)
        db.session.flush()

        # Auto-assign Bib No
        bib_val = _next_bib(se.season_id, institution_id)
        bib = BibNo(bib_value=bib_val, season_id=se.season_id, institution_id=institution_id)
        db.session.add(bib)
        db.session.flush()

        assignment = BibNoAssignment(registration_id=reg.id, bib_no_id=bib.id)
        db.session.add(assignment)

        created.append({
            'registration_id': reg.id,
            'event_name': se.event.name,
            'bib_no': bib_val,
        })

    db.session.commit()
    return created, None
