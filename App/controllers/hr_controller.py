from App.models import (
    Participant,
    Registration,
    Result,
    Institution,
    Stage,
    SeasonEvent,
    Season,
    Event,
)
from App.database import db
from sqlalchemy import func
from datetime import date


def get_hr_stats(institution_id):
    today = date.today()

    # Current / most recent season
    current_season = (
        Season.query.filter_by(status="active").order_by(Season.year.desc()).first()
    )
    if not current_season:
        current_season = Season.query.order_by(Season.year.desc()).first()
    season_id = current_season.id if current_season else None

    participants = Participant.query.filter_by(institution_id=institution_id).all()

    registrations = (
        db.session.query(Registration)
        .join(Participant)
        .filter(Participant.institution_id == institution_id)
        .all()
    )

    registered_ids = set()
    participated_ids = set()
    no_show_ids = set()

    for reg in registrations:
        registered_ids.add(reg.participant_id)
        has_result = len(reg.results) > 0
        event_date = None
        if reg.season_event and reg.season_event.end_date:
            event_date = reg.season_event.end_date
        elif reg.season_event and reg.season_event.start_date:
            event_date = reg.season_event.start_date
        if has_result:
            participated_ids.add(reg.participant_id)
        elif event_date and event_date < today:
            no_show_ids.add(reg.participant_id)

    for p in participants:
        p.has_result = p.id in participated_ids
        p.is_no_show = p.id in no_show_ids
        p.is_registered = p.id in registered_ids

    # ── Division breakdown ────────────────────────────────────────────────
    div_rows = (
        db.session.query(
            Participant.division,
            func.count(Participant.id).label("total"),
        )
        .filter(
            Participant.institution_id == institution_id,
            Participant.division.isnot(None),
            Participant.division != "",
        )
        .group_by(Participant.division)
        .order_by(func.count(Participant.id).desc())
        .all()
    )

    division_data = [{"division": r[0], "count": r[1]} for r in div_rows]

    # ── Gender split ──────────────────────────────────────────────────────
    gender_rows = (
        db.session.query(Participant.sex, func.count(Participant.id).label("count"))
        .filter(
            Participant.institution_id == institution_id,
            Participant.sex.isnot(None),
            Participant.sex != "",
        )
        .group_by(Participant.sex)
        .all()
    )

    g_total = sum(r[1] for r in gender_rows) or 1
    gender_data = [
        {"sex": r[0].upper(), "count": r[1], "pct": round(r[1] / g_total * 100, 1)}
        for r in gender_rows
    ]

    # ── Stage completion for this institution ─────────────────────────────
    stage_completion = []
    if season_id:
        urban = Event.query.filter_by(name="Urban Challenge").first()
        if not urban:
            urban = Event.query.first()
        if urban:
            se = SeasonEvent.query.filter_by(
                season_id=season_id, event_id=urban.id
            ).first()
            if se:
                stages = (
                    Stage.query.filter_by(season_event_id=se.id)
                    .order_by(Stage.stage_number)
                    .all()
                )
                inst_reg_ids = [
                    r.id
                    for r in db.session.query(Registration.id)
                    .join(Participant, Registration.participant_id == Participant.id)
                    .filter(
                        Registration.season_event_id == se.id,
                        Participant.institution_id == institution_id,
                    )
                    .all()
                ]
                total_reg = len(inst_reg_ids)
                for s in stages:
                    if total_reg == 0:
                        stage_completion.append(
                            {
                                "stage": s.stage_number,
                                "completion": 0,
                                "completed": 0,
                                "total": 0,
                            }
                        )
                        continue
                    completed = (
                        db.session.query(
                            func.count(func.distinct(Result.registration_id))
                        )
                        .filter(
                            Result.stage_id == s.id,
                            Result.registration_id.in_(inst_reg_ids),
                        )
                        .scalar()
                        or 0
                    )
                    stage_completion.append(
                        {
                            "stage": s.stage_number,
                            "completion": round(completed / total_reg * 100, 1),
                            "completed": completed,
                            "total": total_reg,
                        }
                    )

    participation_rate = (
        round(len(participated_ids) / len(registered_ids) * 100, 1)
        if registered_ids
        else 0
    )

    return {
        "total_participants": len(participants),
        "reg_count": len(registered_ids),
        "part_count": len(participated_ids),
        "no_show_count": len(no_show_ids),
        "participation_rate": participation_rate,
        "participants": participants,
        "institution": Institution.query.get(institution_id),
        "division_data": division_data,
        "gender_data": gender_data,
        "stage_completion": stage_completion,
        "current_season": current_season,
    }


def get_available_events(institution_id):
    current_season = Season.query.order_by(Season.year.desc()).first()
    if not current_season:
        return []
    season_events = SeasonEvent.query.filter_by(season_id=current_season.id).all()
    events = []
    for se in season_events:
        event = Event.query.get(se.event_id)
        if event:
            events.append(
                {"id": se.id, "name": event.name, "date": se.start_date or "TBD"}
            )
    return events


def register_participants(participant_ids, season_event_id):
    count = 0
    for pid in participant_ids:
        if not Registration.query.filter_by(
            participant_id=pid, season_event_id=season_event_id
        ).first():
            db.session.add(
                Registration(participant_id=pid, season_event_id=season_event_id)
            )
            count += 1
    db.session.commit()
    return count
