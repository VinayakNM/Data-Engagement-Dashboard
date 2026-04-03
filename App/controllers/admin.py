"""
App/controllers/admin.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Admin blueprint — page routes + JSON API endpoints.

Page routes:
  GET  /admin/dashboard                → dashboard.html
  GET  /admin/event-management         → event_management.html
  GET  /admin/season-management        → season_management.html  (stub)
  GET  /admin/bib-no-management        → bib_no_management.html  (stub)
  GET  /admin/bib-tag-management       → bib_tag_management.html (stub)
  GET  /admin/institution-management   → institution_management.html (stub)
  GET  /admin/user-management          → user_management.html    (stub)
  GET  /admin/forms                    → forms.html              (stub)

API endpoints (JSON):
  ── Seasons ──
  GET  /api/seasons                    → list all seasons
  POST /api/seasons                    → create season

  ── Events (per season) ──
  GET  /api/seasons/<id>/events        → list SeasonEvents for a season
  POST /api/events                     → create Event + SeasonEvent + Stages

  ── SeasonEvent ──
  PUT    /api/season-events/<id>       → update event fields + replace stages
  PATCH  /api/season-events/<id>/status → set status active/inactive
  DELETE /api/season-events/<id>       → remove from season (+ stages)

  ── Dashboard stats ──
  GET  /api/stats                      → total_users, active_events, current_season
  GET  /api/metrics                    → registered, participated, no_shows, completed
  GET  /api/top-institutions           → top 4 institutions by participant count
  GET  /api/participation-by-year      → year-over-year participation counts
  GET  /api/funnel                     → drop-off funnel for a season/event

  ── Supporting lists ──
  GET  /api/institutions               → list all institutions
"""

from flask import Blueprint, render_template, jsonify, request, abort
from flask_login import login_required, current_user
from functools import wraps

from App.database import db
from App.models import (
    User, Admin, Season, Event, SeasonEvent, Stage,
    Institution, Participant, Registration, Result
)

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


# ─────────────────────────────────────────
# DECORATORS
# ─────────────────────────────────────────
def admin_required(f):
    """Restrict endpoint to users with role == 'admin'."""
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if current_user.role != 'admin':
            abort(403)
        return f(*args, **kwargs)
    return decorated


# ─────────────────────────────────────────
# PAGE ROUTES
# ─────────────────────────────────────────
@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    return render_template('admin/dashboard.html')


@admin_bp.route('/event-management')
@admin_required
def event_management():
    return render_template('admin/event_management.html')


@admin_bp.route('/season-management')
@admin_required
def season_management():
    return render_template('admin/season_management.html')


@admin_bp.route('/bib-no-management')
@admin_required
def bib_no_management():
    return render_template('admin/bib_no_management.html')


@admin_bp.route('/bib-tag-management')
@admin_required
def bib_tag_management():
    return render_template('admin/bib_tag_management.html')


@admin_bp.route('/institution-management')
@admin_required
def institution_management():
    return render_template('admin/institution_management.html')


@admin_bp.route('/user-management')
@admin_required
def user_management():
    return render_template('admin/user_management.html')


@admin_bp.route('/forms')
@admin_required
def forms():
    return render_template('admin/forms.html')


# ─────────────────────────────────────────
# API — SEASONS
# ─────────────────────────────────────────
@admin_bp.route('/api/seasons', endpoint='api_get_seasons')
@login_required
def api_get_seasons():
    """GET /api/seasons — list all seasons ordered by year."""
    seasons = Season.query.order_by(Season.year).all()
    return jsonify([
        {'id': s.id, 'year': s.year, 'description': s.description}
        for s in seasons
    ])


@admin_bp.route('/api/seasons', methods=['POST'], endpoint='api_create_season')
@admin_required
def api_create_season():
    """POST /api/seasons — create a new season. Body: {year, description}"""
    data = request.get_json(force=True)
    year = data.get('year')
    if not year:
        return jsonify({'error': 'year is required'}), 400
    if Season.query.filter_by(year=year).first():
        return jsonify({'error': f'Season {year} already exists'}), 409
    season = Season(year=int(year), description=data.get('description', ''))
    db.session.add(season)
    db.session.commit()
    return jsonify({'id': season.id, 'year': season.year}), 201


# ─────────────────────────────────────────
# API — EVENTS (per season)
# ─────────────────────────────────────────
def _season_event_to_dict(se):
    """Serialize a SeasonEvent with nested event info and stages."""
    return {
        'id':           se.id,                         # SeasonEvent.id
        'event_id':     se.event.id,
        'event_name':   se.event.name,
        'event_type':   se.event.event_type or '',
        'description':  se.event.description or '',
        'status':       se.status,
        'start_date':   se.start_date.isoformat() if se.start_date else None,
        'end_date':     se.end_date.isoformat()   if se.end_date   else None,
        'stages': [
            {
                'id':           st.id,
                'stage_number': st.stage_number,
                'distance':     st.distance or '',
                'location':     st.location or '',
                'stage_date':   st.stage_date.isoformat() if st.stage_date else None,
            }
            for st in sorted(se.stages, key=lambda x: x.stage_number or 0)
        ]
    }


@admin_bp.route('/api/seasons/<int:season_id>/events', endpoint='api_list_season_events')
@login_required
def api_list_season_events(season_id):
    """GET /api/seasons/<id>/events — all SeasonEvents for a season."""
    season = Season.query.get_or_404(season_id)
    return jsonify([_season_event_to_dict(se) for se in season.season_events])


@admin_bp.route('/api/events', methods=['POST'], endpoint='api_create_event')
@admin_required
def api_create_event():
    """
    POST /api/events
    Body: { name, event_type, description, season_id, stages: [{stage_number, distance, location, stage_date}] }
    Creates Event + SeasonEvent + Stages atomically.
    If an Event with the same name already exists, reuses it (just creates a new SeasonEvent).
    """
    data       = request.get_json(force=True)
    name       = (data.get('name') or '').strip()
    season_id  = data.get('season_id')
    event_type = data.get('event_type', 'Walk')
    description = data.get('description', '')
    stages_data = data.get('stages', [])

    if not name:
        return jsonify({'error': 'name is required'}), 400
    if not season_id:
        return jsonify({'error': 'season_id is required'}), 400

    season = Season.query.get_or_404(season_id)

    # Reuse existing Event by name, or create new
    event = Event.query.filter(db.func.lower(Event.name) == name.lower()).first()
    if not event:
        event = Event(name=name, event_type=event_type, description=description)
        db.session.add(event)
        db.session.flush()  # get event.id before commit
    else:
        # Update type/description if provided
        event.event_type  = event_type
        event.description = description

    # Check this event isn't already in this season
    existing_se = SeasonEvent.query.filter_by(season_id=season.id, event_id=event.id).first()
    if existing_se:
        return jsonify({'error': f'"{name}" is already in season {season.year}'}), 409

    se = SeasonEvent(season_id=season.id, event_id=event.id)
    se.status = 'active'
    db.session.add(se)
    db.session.flush()

    # Create stages
    for s in stages_data:
        stage = Stage(
            season_event_id = se.id,
            stage_number    = s.get('stage_number', 1),
            location        = s.get('location') or None,
            stage_date      = _parse_date(s.get('stage_date')),
        )
        # Stage doesn't have a distance column in the model —
        # add one if needed, or store in location string.
        # If you add `distance = db.Column(db.String(20))` to Stage, uncomment:
        # stage.distance = s.get('distance') or None
        db.session.add(stage)

    db.session.commit()
    return jsonify(_season_event_to_dict(se)), 201


# ─────────────────────────────────────────
# API — SEASON-EVENT (update / status / delete)
# ─────────────────────────────────────────
@admin_bp.route('/api/season-events/<int:se_id>', methods=['PUT'], endpoint='api_update_season_event')
@admin_required
def api_update_season_event(se_id):
    """
    PUT /api/season-events/<id>
    Body: { name, event_type, description, stages: [...] }
    Updates the Event record and REPLACES all stages.
    """
    se   = SeasonEvent.query.get_or_404(se_id)
    data = request.get_json(force=True)

    # Update Event fields
    event = se.event
    if 'name'        in data: event.name        = data['name'].strip()
    if 'event_type'  in data: event.event_type  = data['event_type']
    if 'description' in data: event.description = data['description']

    # Replace stages: delete old, insert new
    Stage.query.filter_by(season_event_id=se.id).delete()
    for s in data.get('stages', []):
        stage = Stage(
            season_event_id = se.id,
            stage_number    = s.get('stage_number', 1),
            location        = s.get('location') or None,
            stage_date      = _parse_date(s.get('stage_date')),
        )
        db.session.add(stage)

    db.session.commit()
    return jsonify(_season_event_to_dict(se))


@admin_bp.route('/api/season-events/<int:se_id>/status', methods=['PATCH'], endpoint='api_set_season_event_status')
@admin_required
def api_set_season_event_status(se_id):
    """
    PATCH /api/season-events/<id>/status
    Body: { status: 'active' | 'inactive' }
    """
    se     = SeasonEvent.query.get_or_404(se_id)
    data   = request.get_json(force=True)
    status = data.get('status')
    if status not in ('active', 'inactive'):
        return jsonify({'error': 'status must be active or inactive'}), 400
    se.status = status
    db.session.commit()
    return jsonify({'id': se.id, 'status': se.status})


@admin_bp.route('/api/season-events/<int:se_id>', methods=['DELETE'], endpoint='api_delete_season_event')
@admin_required
def api_delete_season_event(se_id):
    """
    DELETE /api/season-events/<id>
    Removes the SeasonEvent and its Stages.
    Does NOT delete the Event itself (it may exist in other seasons).
    """
    se = SeasonEvent.query.get_or_404(se_id)

    # Delete child stages first (cascade safety)
    Stage.query.filter_by(season_event_id=se.id).delete()

    # Optionally: also delete registrations + results for this season_event
    # (uncomment if you want hard delete)
    # for reg in se.registrations:
    #     Result.query.filter_by(registration_id=reg.id).delete()
    # Registration.query.filter_by(season_event_id=se.id).delete()

    db.session.delete(se)
    db.session.commit()
    return jsonify({'deleted': se_id}), 200


# ─────────────────────────────────────────
# API — DASHBOARD STATS
# ─────────────────────────────────────────
@admin_bp.route('/api/stats', endpoint='api_stats')
@login_required
def api_stats():
    """
    GET /api/stats
    Returns counts for the dashboard System Stats strip.
    """
    total_users   = User.query.count()
    active_events = SeasonEvent.query.filter_by(status='active').count()
    latest_season = Season.query.order_by(Season.year.desc()).first()
    current_season = latest_season.year if latest_season else '—'

    return jsonify({
        'total_users':    total_users,
        'active_events':  active_events,
        'current_season': current_season,
    })


@admin_bp.route('/api/metrics', endpoint='api_metrics')
@login_required
def api_metrics():
    """
    GET /api/metrics?season_id=&event_id=
    Returns Key Metrics for the dashboard.
    Pass season_id (and optionally event_id) to filter.
    """
    season_id = request.args.get('season_id', type=int)
    event_id  = request.args.get('event_id',  type=int)

    reg_q = Registration.query
    if season_id:
        reg_q = reg_q.join(SeasonEvent).filter(SeasonEvent.season_id == season_id)
        if event_id:
            reg_q = reg_q.filter(SeasonEvent.event_id == event_id)

    registered = reg_q.count()

    # "Participated" = has at least one Result record
    participated_ids = (
        db.session.query(Result.registration_id)
        .join(Registration)
        .distinct()
    )
    if season_id:
        participated_ids = (
            participated_ids
            .join(SeasonEvent, Registration.season_event_id == SeasonEvent.id)
            .filter(SeasonEvent.season_id == season_id)
        )
        if event_id:
            participated_ids = participated_ids.filter(SeasonEvent.event_id == event_id)

    participated = participated_ids.count()
    no_shows     = registered - participated

    # "Completed" = has a Result with a placement value set
    completed = (
        Result.query.join(Registration)
        .filter(Result.placement.isnot(None))
    )
    if season_id:
        completed = (
            completed
            .join(SeasonEvent, Registration.season_event_id == SeasonEvent.id)
            .filter(SeasonEvent.season_id == season_id)
        )
    completed = completed.count()

    def pct(n, total):
        return f'{round(n / total * 100, 1)}%' if total else '0%'

    return jsonify({
        'registered':         registered,
        'participated':       participated,
        'participated_pct':   pct(participated, registered),
        'no_shows':           no_shows,
        'no_shows_pct':       pct(no_shows, registered),
        'completed':          completed,
        'completed_pct':      pct(completed, registered),
    })


@admin_bp.route('/api/top-institutions', endpoint='api_top_institutions')
@login_required
def api_top_institutions():
    """
    GET /api/top-institutions?season_id=&limit=4
    Returns institutions ranked by number of registered participants.
    """
    season_id = request.args.get('season_id', type=int)
    limit     = request.args.get('limit', 4, type=int)

    q = (
        db.session.query(
            Institution.name,
            Institution.code,
            db.func.count(Registration.id).label('count')
        )
        .join(Participant,   Institution.id == Participant.institution_id)
        .join(Registration,  Participant.id == Registration.participant_id)
    )
    if season_id:
        q = q.join(SeasonEvent, Registration.season_event_id == SeasonEvent.id) \
             .filter(SeasonEvent.season_id == season_id)

    results = (
        q.group_by(Institution.id)
         .order_by(db.func.count(Registration.id).desc())
         .limit(limit)
         .all()
    )
    return jsonify([
        {'name': r.name, 'code': r.code, 'count': r.count}
        for r in results
    ])


@admin_bp.route('/api/participation-by-year', endpoint='api_participation_by_year')
@login_required
def api_participation_by_year():
    """
    GET /api/participation-by-year
    Returns total registrations grouped by season year for the bar chart.
    """
    rows = (
        db.session.query(
            Season.year,
            db.func.count(Registration.id).label('count')
        )
        .join(SeasonEvent, Season.id == SeasonEvent.season_id)
        .join(Registration, SeasonEvent.id == Registration.season_event_id)
        .group_by(Season.year)
        .order_by(Season.year)
        .all()
    )
    years  = [r.year  for r in rows]
    counts = [r.count for r in rows]
    max_c  = max(counts) if counts else 1

    return jsonify([
        {'year': r.year, 'count': r.count, 'pct': round(r.count / max_c * 100)}
        for r in rows
    ])


@admin_bp.route('/api/funnel', endpoint='api_funnel')
@login_required
def api_funnel():
    """
    GET /api/funnel?season_id=&event_id=
    Returns stage-by-stage drop-off for one SeasonEvent.
    """
    season_id = request.args.get('season_id', type=int)
    event_id  = request.args.get('event_id',  type=int)

    if not (season_id and event_id):
        return jsonify({'error': 'season_id and event_id are required'}), 400

    se = SeasonEvent.query.filter_by(season_id=season_id, event_id=event_id).first()
    if not se:
        return jsonify({'error': 'Event not found in season'}), 404

    registered = Registration.query.filter_by(season_event_id=se.id).count()
    stages = sorted(se.stages, key=lambda s: s.stage_number or 0)

    funnel = []
    for stage in stages:
        finishers = Result.query.filter_by(stage_id=stage.id).count()
        funnel.append({
            'stage_number': stage.stage_number,
            'location':     stage.location,
            'finishers':    finishers,
            'drop_pct':     round((1 - finishers / registered) * 100, 1) if registered else 0,
        })

    return jsonify({
        'event_name': se.event.name,
        'season_year': se.season.year,
        'registered': registered,
        'funnel': funnel,
    })


# ─────────────────────────────────────────
# API — SUPPORTING LISTS
# ─────────────────────────────────────────
@admin_bp.route('/api/institutions', endpoint='api_list_institutions')
@login_required
def api_list_institutions():
    """GET /api/institutions — list all institutions for filter dropdowns."""
    institutions = Institution.query.order_by(Institution.name).all()
    return jsonify([i.get_json() for i in institutions])


# ─────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────
def _parse_date(value):
    """Safely parse a YYYY-MM-DD string to a date object, or return None."""
    if not value:
        return None
    try:
        from datetime import date
        return date.fromisoformat(str(value))
    except ValueError:
        return None