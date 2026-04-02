from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, current_user
from App.database import db
from App.models import (
    User, Institution, Season, Event, SeasonEvent, Stage, Registration, Result
)
from datetime import datetime

forms_api = Blueprint('forms_api', __name__, url_prefix='/api/forms')


def _admin():
    if not current_user or current_user.role != 'admin':
        return jsonify(error='Admin access required'), 403
    return None


def _parse_date(val):
    if not val:
        return None
    try:
        return datetime.strptime(val, '%Y-%m-%d').date()
    except Exception:
        return None


#  EVENT FORM  —  /api/forms/events

@forms_api.route('/events', methods=['GET'])
@jwt_required()
def form_get_events():
    """
    GET /api/forms/events?season_id=<id>
    Always returns ALL events including unassigned ones.
    When season_id provided, marks which events are in that season and includes stage data.
    """
    season_id = request.args.get('season_id', type=int)

    # Build lookup: event_id -> SeasonEvent for selected season
    se_map = {}
    if season_id:
        for se in SeasonEvent.query.filter_by(season_id=season_id).all():
            se_map[se.event_id] = se

    events = Event.query.order_by(Event.name).all()
    result = []
    for e in events:
        se = se_map.get(e.id)
        stages = []
        if se:
            stages = [{
                'id':           st.id,
                'stage_number': st.stage_number,
                'distance':     st.distance  or '',
                'location':     st.location  or '',
                'stage_date':   st.stage_date.isoformat() if st.stage_date else '',
            } for st in Stage.query.filter_by(season_event_id=se.id)
                                   .order_by(Stage.stage_number).all()]

        assigned_seasons = [
            {'id': x.season_id, 'year': x.season.year if x.season else '?'}
            for x in e.season_events if x.season
        ]
        total_stages = len(stages) or sum(
            Stage.query.filter_by(season_event_id=x.id).count()
            for x in e.season_events
        )

        result.append({
            'id':                 e.id,
            'season_event_id':    se.id if se else None,
            'name':               e.name,
            'event_type':         e.event_type or 'run',
            'description':        e.description or '',
            'status':             se.status if se else 'unassigned',
            'start_date':         se.start_date.isoformat() if se and se.start_date else None,
            'end_date':           se.end_date.isoformat()   if se and se.end_date   else None,
            'stage_count':        total_stages,
            'assigned_seasons':   assigned_seasons,
            'in_selected_season': se is not None,
            'stages':             stages,
        })
    return jsonify(result)

@forms_api.route('/events', methods=['POST'])
@jwt_required()
def form_create_event():
    """Create a new Event and optionally link it to a season with stages."""
    err = _admin()
    if err: return err
    data = request.get_json(force=True)
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify(error='name is required'), 400

    e = Event.query.filter_by(name=name).first()
    if not e:
        e = Event(name=name,
                  event_type=data.get('event_type', 'run'),
                  description=data.get('description', ''))
        db.session.add(e)
        db.session.flush()
    else:
        e.event_type  = data.get('event_type', e.event_type)
        e.description = data.get('description', e.description)

    season_id = data.get('season_id')
    se = None
    if season_id:
        se = SeasonEvent.query.filter_by(season_id=int(season_id), event_id=e.id).first()
        if not se:
            se = SeasonEvent(season_id=int(season_id), event_id=e.id, status='active')
            db.session.add(se)
            db.session.flush()
        _replace_stages(se.id, data.get('stages', []))

    db.session.commit()
    return jsonify({'id': e.id, 'name': e.name,
                    'season_event_id': se.id if se else None}), 201


@forms_api.route('/events/<int:eid>', methods=['PUT'])
@jwt_required()
def form_update_event(eid):
    """Update event name/type/description and replace its stages for a given season."""
    err = _admin()
    if err: return err
    e = Event.query.get_or_404(eid)
    data = request.get_json(force=True)

    if 'name'        in data: e.name        = data['name']
    if 'event_type'  in data: e.event_type  = data['event_type']
    if 'description' in data: e.description = data['description']

    season_id = data.get('season_id')
    if season_id:
        se = SeasonEvent.query.filter_by(season_id=int(season_id), event_id=e.id).first()
        if not se:
            se = SeasonEvent(season_id=int(season_id), event_id=e.id, status='active')
            db.session.add(se)
            db.session.flush()
        if 'status' in data:
            se.status = data['status']
        _replace_stages(se.id, data.get('stages', []))

    db.session.commit()
    return jsonify({'id': e.id, 'name': e.name, 'event_type': e.event_type})


@forms_api.route('/events/<int:eid>/status', methods=['PATCH'])
@jwt_required()
def form_patch_event_status(eid):
    """Toggle Active / Inactive for a SeasonEvent (requires season_id in body)."""
    err = _admin()
    if err: return err
    data      = request.get_json(force=True)
    season_id = data.get('season_id')
    if not season_id:
        return jsonify(error='season_id required'), 400
    se = SeasonEvent.query.filter_by(season_id=int(season_id), event_id=eid).first()
    if not se:
        return jsonify(error='Event not linked to this season'), 404
    se.status = data.get('status', 'active')
    db.session.commit()
    return jsonify({'id': se.id, 'status': se.status})


@forms_api.route('/events/<int:eid>', methods=['DELETE'])
@jwt_required()
def form_delete_event(eid):
    """Delete an event and all its season links / stages / registrations."""
    err = _admin()
    if err: return err
    e = Event.query.get_or_404(eid)
    for se in e.season_events:
        Stage.query.filter_by(season_event_id=se.id).delete()
        for reg in Registration.query.filter_by(season_event_id=se.id).all():
            Result.query.filter_by(registration_id=reg.id).delete()
            db.session.delete(reg)
        db.session.delete(se)
    db.session.delete(e)
    db.session.commit()
    return jsonify(deleted=eid)


def _replace_stages(season_event_id, stages_data):
    """Delete all stages for a SeasonEvent then re-insert. Flush between to
    avoid the unique constraint on (season_event_id, stage_number) firing."""
    Stage.query.filter_by(season_event_id=season_event_id)\
               .delete(synchronize_session='fetch')
    db.session.flush()
    for i, st in enumerate(stages_data):
        s = Stage(season_event_id=season_event_id, stage_number=i + 1,
                  distance=(st.get('distance') or '').strip(),
                  location=(st.get('location') or '').strip())
        raw = st.get('stage_date')
        if raw:
            try:
                s.stage_date = datetime.strptime(raw, '%Y-%m-%d').date()
            except Exception:
                pass
        db.session.add(s)


#  SEASON FORM  —  /api/forms/seasons

@forms_api.route('/seasons', methods=['GET'])
@jwt_required()
def form_get_seasons():
    """Return all seasons with their linked events (for the seasons list + view panel)."""
    seasons = Season.query.order_by(Season.year.desc()).all()
    result  = []
    for s in seasons:
        ses = SeasonEvent.query.filter_by(season_id=s.id).all()
        events = []
        for se in ses:
            if not se.event:
                continue
            events.append({
                'id':         se.event.id,
                'name':       se.event.name,
                'included':   True,
                'start_date': se.start_date.isoformat() if se.start_date else None,
                'end_date':   se.end_date.isoformat()   if se.end_date   else None,
            })
        result.append({
            'id':          s.id,
            'year':        s.year,
            'description': s.description or '',
            'status':      s.status or 'planning',
            'reg_open':    s.reg_open.isoformat()    if s.reg_open    else None,
            'reg_close':   s.reg_close.isoformat()   if s.reg_close   else None,
            'start_date':  s.start_date.isoformat()  if s.start_date  else None,
            'end_date':    s.end_date.isoformat()     if s.end_date    else None,
            'events':      events,
        })
    return jsonify(result)


@forms_api.route('/seasons', methods=['POST'])
@jwt_required()
def form_create_season():
    """Create a season with optional dates, status, and event links."""
    err = _admin()
    if err: return err
    data = request.get_json(force=True)
    year = data.get('year')
    if not year:
        return jsonify(error='year is required'), 400
    if Season.query.filter_by(year=int(year)).first():
        return jsonify(error=f'Season {year} already exists'), 400

    s = Season(
        year        = int(year),
        description = data.get('description', ''),
        status      = data.get('status', 'planning'),
        reg_open    = _parse_date(data.get('reg_open')),
        reg_close   = _parse_date(data.get('reg_close')),
        start_date  = _parse_date(data.get('start_date')),
        end_date    = _parse_date(data.get('end_date')),
    )
    db.session.add(s)
    db.session.flush()
    _sync_season_events(s.id, data.get('events', []))
    db.session.commit()
    return jsonify({'id': s.id, 'year': s.year}), 201


@forms_api.route('/seasons/<int:sid>', methods=['PUT'])
@jwt_required()
def form_update_season(sid):
    """Update season fields and sync event links."""
    err = _admin()
    if err: return err
    s = Season.query.get_or_404(sid)
    data = request.get_json(force=True)

    if 'year'        in data: s.year        = int(data['year'])
    if 'description' in data: s.description = data['description']
    if 'status'      in data: s.status      = data['status']
    if 'reg_open'    in data: s.reg_open    = _parse_date(data['reg_open'])
    if 'reg_close'   in data: s.reg_close   = _parse_date(data['reg_close'])
    if 'start_date'  in data: s.start_date  = _parse_date(data['start_date'])
    if 'end_date'    in data: s.end_date    = _parse_date(data['end_date'])

    if 'events' in data:
        _sync_season_events(s.id, data['events'])

    db.session.commit()
    return jsonify({'id': s.id, 'year': s.year})


@forms_api.route('/seasons/<int:sid>', methods=['DELETE'])
@jwt_required()
def form_delete_season(sid):
    """Delete a season and all child records."""
    err = _admin()
    if err: return err
    s = Season.query.get_or_404(sid)
    for se in SeasonEvent.query.filter_by(season_id=sid).all():
        Stage.query.filter_by(season_event_id=se.id).delete()
        for reg in Registration.query.filter_by(season_event_id=se.id).all():
            Result.query.filter_by(registration_id=reg.id).delete()
            db.session.delete(reg)
        db.session.delete(se)
    db.session.delete(s)
    db.session.commit()
    return jsonify(deleted=sid)


def _sync_season_events(season_id, events_data):

    for ev in events_data:
        eid      = ev.get('event_id') or ev.get('id')
        included = ev.get('included', True)
        if not eid:
            continue
        se = SeasonEvent.query.filter_by(season_id=season_id, event_id=eid).first()
        if included:
            if not se:
                se = SeasonEvent(season_id=season_id, event_id=eid, status='active')
                db.session.add(se)
                db.session.flush()
            se.start_date = _parse_date(ev.get('start_date'))
            se.end_date   = _parse_date(ev.get('end_date'))
        else:
            if se:
                Stage.query.filter_by(season_event_id=se.id).delete()
                db.session.delete(se)


#  INSTITUTION FORM  —  /api/forms/institutions

@forms_api.route('/institutions', methods=['GET'])
@jwt_required()
def form_get_institutions():
    """Return all institutions with user counts, participant counts, and participation history."""
    insts = Institution.query.order_by(Institution.name).all()
    result = []
    for i in insts:
        # Participation history: registered count per season
        from App.models import Participant as P, Registration as R, SeasonEvent as SE, Season as S
        from sqlalchemy import func
        history = db.session.query(
            S.year,
            func.count(R.id).label('registered')
        ).join(SE, S.id == SE.season_id)\
         .join(R,  SE.id == R.season_event_id)\
         .join(P,  R.participant_id == P.id)\
         .filter(P.institution_id == i.id)\
         .group_by(S.year)\
         .order_by(S.year.desc())\
         .limit(5).all()

        # HR users assigned to this institution
        hr_users = [u for u in i.users if u.role == 'hr']

        # Participant count for the active season only
        # Prefer 'active', then 'closed' — never use a planning season (no data)
        current_season = Season.query.filter_by(status='active').order_by(Season.year.desc()).first()
        if not current_season:
            current_season = Season.query.filter_by(status='closed').order_by(Season.year.desc()).first()
        if not current_season:
            current_season = Season.query.filter(Season.status.notin_(['planning'])).order_by(Season.year.desc()).first()
        season_participant_count = 0
        if current_season:
            season_participant_count = db.session.query(
                func.count(func.distinct(P.id))
            ).join(R, P.id == R.participant_id)             .join(SE, R.season_event_id == SE.id)             .filter(SE.season_id == current_season.id,
                     P.institution_id == i.id)             .scalar() or 0

        result.append({
            **i.get_json(),
            'participant_count': season_participant_count,
            'user_count':        len(i.users),
            'hr_users': [{'id': u.id, 'username': u.username, 'email': u.email}
                         for u in hr_users],
            'participation_history': [
                {'year': row.year, 'registered': row.registered}
                for row in history
            ],
        })
    return jsonify(result)


@forms_api.route('/institutions', methods=['POST'])
@jwt_required()
def form_create_institution():
    """Create a new institution."""
    err = _admin()
    if err: return err
    data = request.get_json(force=True)
    name = (data.get('name') or '').strip()
    code = (data.get('code') or '').strip().upper()
    if not name or not code:
        return jsonify(error='name and code are required'), 400
    if Institution.query.filter_by(code=code).first():
        return jsonify(error=f'Code {code} already exists'), 400

    i = Institution(
        name           = name,
        code           = code,
        contact_person = (data.get('contact_person') or '').strip() or None,
        contact_email  = (data.get('contact_email')  or '').strip() or None,
        phone          = (data.get('phone')          or '').strip() or None,
        status         = data.get('status', 'active'),
    )
    db.session.add(i)
    db.session.commit()
    return jsonify(i.get_json()), 201


@forms_api.route('/institutions/<int:iid>', methods=['PUT'])
@jwt_required()
def form_update_institution(iid):
    """Update institution details."""
    err = _admin()
    if err: return err
    i    = Institution.query.get_or_404(iid)
    data = request.get_json(force=True)

    if 'name'           in data: i.name           = data['name']
    if 'code'           in data: i.code           = data['code'].strip().upper()
    if 'contact_person' in data: i.contact_person = data['contact_person']
    if 'contact_email'  in data: i.contact_email  = data['contact_email']
    if 'phone'          in data: i.phone          = data['phone']
    if 'status'         in data: i.status         = data['status']

    db.session.commit()
    return jsonify(i.get_json())


@forms_api.route('/institutions/<int:iid>/status', methods=['PATCH'])
@jwt_required()
def form_patch_institution_status(iid):
    """Toggle active / inactive."""
    err = _admin()
    if err: return err
    i = Institution.query.get_or_404(iid)
    data = request.get_json(force=True)
    i.status = data.get('status', 'active')
    db.session.commit()
    return jsonify({'id': i.id, 'status': i.status})


@forms_api.route('/institutions/<int:iid>', methods=['DELETE'])
@jwt_required()
def form_delete_institution(iid):
    """Delete institution (only if no participants)."""
    err = _admin()
    if err: return err
    i = Institution.query.get_or_404(iid)
    if i.participants:
        return jsonify(error='Cannot delete: institution has participants'), 409
    db.session.delete(i)
    db.session.commit()
    return jsonify(deleted=iid)


@forms_api.route('/institutions/<int:iid>/assign-hr', methods=['POST'])
@jwt_required()
def form_assign_hr(iid):
    """Assign an HR user to an institution by user_id."""
    err = _admin()
    if err: return err
    Institution.query.get_or_404(iid)
    data    = request.get_json(force=True)
    user_id = data.get('user_id')
    user    = User.query.get_or_404(user_id)
    if user.role != 'hr':
        return jsonify(error='User is not an HR user'), 400
    user.institution_id = iid
    db.session.commit()
    return jsonify(ok=True, user_id=user_id)


@forms_api.route('/institutions/<int:iid>/remove-hr/<int:uid>', methods=['DELETE'])
@jwt_required()
def form_remove_hr(iid, uid):
    """Unassign an HR user from an institution."""
    err = _admin()
    if err: return err
    user = User.query.get_or_404(uid)
    if user.institution_id != iid:
        return jsonify(error='User not assigned to this institution'), 400
    user.institution_id = None
    db.session.commit()
    return jsonify(ok=True)


# ── Shared helpers ─────────────────────────────────────────────

@forms_api.route('/events-list', methods=['GET'])
@jwt_required()
def form_events_list():
    """Lightweight list of all events — used by season form event picker."""
    events = Event.query.order_by(Event.name).all()
    return jsonify([{'id': e.id, 'name': e.name, 'event_type': e.event_type}
                    for e in events])


@forms_api.route('/seasons-list', methods=['GET'])
@jwt_required()
def form_seasons_list():
    """Lightweight list of all seasons — used by event form season picker."""
    seasons = Season.query.order_by(Season.year.desc()).all()
    return jsonify([{'id': s.id, 'year': s.year, 'status': s.status or 'planning'}
                    for s in seasons])


@forms_api.route('/hr-users', methods=['GET'])
@jwt_required()
def form_hr_users():
    """List all HR users — used by institution form HR assignment panel."""
    err = _admin()
    if err: return err
    users = User.query.filter_by(role='hr').order_by(User.lastname).all()
    return jsonify([{'id': u.id, 'username': u.username, 'email': u.email,
                     'institution_id': u.institution_id} for u in users])