"""
App/views/hr_api.py
All JSON API endpoints consumed by the HR dashboard frontend.
"""
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, current_user

from App.database import db
from App.controllers.hr import (
    get_hr_dashboard_data, get_hr_filter_options,
    list_participants, get_participant,
    create_participant, update_participant, delete_participant,
    check_duplicate, bulk_create_participants,
    get_available_events, register_participant_for_events,
)

hr_api = Blueprint('hr_api', __name__, url_prefix='/hr/api')


def _hr_required():
    """Returns (current_user, None) or (None, error_response)."""
    if current_user.role not in ('hr', 'admin'):
        return None, (jsonify(error='Access denied'), 403)
    return current_user, None


# ── Dashboard stats ────────────────────────────────────────

@hr_api.route('/dashboard', methods=['GET'])
@jwt_required()
def dashboard_data():
    user, err = _hr_required(); 
    if err: return err
    inst_id    = current_user.institution_id
    season_ids = request.args.getlist('season_id', type=int) or None
    event_types= request.args.getlist('event_type') or None
    divisions  = request.args.getlist('division') or None
    data = get_hr_dashboard_data(inst_id, season_ids, event_types, divisions)
    return jsonify(data)


@hr_api.route('/filters', methods=['GET'])
@jwt_required()
def filter_options():
    user, err = _hr_required();
    if err: return err
    return jsonify(get_hr_filter_options(current_user.institution_id))


# ── Participants ───────────────────────────────────────────

@hr_api.route('/participants', methods=['GET'])
@jwt_required()
def get_participants():
    user, err = _hr_required();
    if err: return err
    season_id = request.args.get('season_id', type=int)
    return jsonify(list_participants(current_user.institution_id, season_id))


@hr_api.route('/participants/<int:pid>', methods=['GET'])
@jwt_required()
def get_one_participant(pid):
    user, err = _hr_required();
    if err: return err
    p = get_participant(pid)
    if not p or p['institution_id'] != current_user.institution_id:
        return jsonify(error='Not found'), 404
    return jsonify(p)


@hr_api.route('/participants', methods=['POST'])
@jwt_required()
def add_participant():
    user, err = _hr_required();
    if err: return err
    data = request.get_json(force=True)
    p, error = create_participant(data, current_user.institution_id)
    if error:
        return jsonify(error=error), 400
    db.session.commit()
    return jsonify(get_participant(p.id)), 201


@hr_api.route('/participants/<int:pid>', methods=['PUT'])
@jwt_required()
def edit_participant(pid):
    user, err = _hr_required();
    if err: return err
    data = request.get_json(force=True)
    p, error = update_participant(pid, data, current_user.institution_id)
    if error:
        return jsonify(error=error), 400
    return jsonify(get_participant(p.id))


@hr_api.route('/participants/<int:pid>', methods=['DELETE'])
@jwt_required()
def remove_participant(pid):
    user, err = _hr_required();
    if err: return err
    ok, error = delete_participant(pid, current_user.institution_id)
    if not ok:
        return jsonify(error=error), 404
    return jsonify(deleted=pid)


@hr_api.route('/participants/check-duplicate', methods=['POST'])
@jwt_required()
def dup_check():
    user, err = _hr_required();
    if err: return err
    data = request.get_json(force=True)
    is_dup = check_duplicate(
        data.get('first_name',''), data.get('last_name',''),
        current_user.institution_id
    )
    return jsonify(duplicate=is_dup)


@hr_api.route('/participants/bulk-import', methods=['POST'])
@jwt_required()
def bulk_import():
    user, err = _hr_required();
    if err: return err
    data = request.get_json(force=True)
    rows = data.get('rows', [])
    if not rows:
        return jsonify(error='No rows provided'), 400
    added, skipped, errors = bulk_create_participants(rows, current_user.institution_id)
    return jsonify(added=added, skipped=skipped, errors=errors), 200


# ── Events & Registration ──────────────────────────────────

@hr_api.route('/available-events', methods=['GET'])
@jwt_required()
def available_events():
    user, err = _hr_required();
    if err: return err
    return jsonify(get_available_events(current_user.institution_id))


@hr_api.route('/participants/<int:pid>/register', methods=['POST'])
@jwt_required()
def register_for_events(pid):
    user, err = _hr_required();
    if err: return err
    data = request.get_json(force=True)
    se_ids = data.get('season_event_ids', [])
    created, error = register_participant_for_events(
        pid, se_ids, current_user.institution_id)
    if error:
        return jsonify(error=error), 400
    return jsonify(registrations=created), 201
