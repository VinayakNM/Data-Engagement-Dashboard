from flask import Blueprint, request, flash, redirect, url_for, render_template, jsonify
from flask_jwt_extended import jwt_required, current_user
from App.controllers.hr_controller import (
    get_hr_stats,
    get_available_events,
    register_participants,
)
from App.controllers.participant_controller import create_participant
from App.models import Participant
from App.database import db
from datetime import datetime
import csv
import io

hr_views = Blueprint("hr_views", __name__, template_folder="../templates")


@hr_views.route("/hr/dashboard")
@jwt_required()
def dashboard():
    if current_user.role != "hr":
        return "Access Denied", 403
    stats = get_hr_stats(current_user.institution_id)
    events = get_available_events(current_user.institution_id)
    return render_template("hr/hr.html", **stats, events=events)


@hr_views.route("/hr/participants")
@jwt_required()
def participant_roster():
    if current_user.role != "hr":
        return "Access Denied", 403
    participants = Participant.query.filter_by(
        institution_id=current_user.institution_id
    ).all()
    return render_template("hr/participants.html", participants=participants)


@hr_views.route("/hr/participants/add", methods=["GET", "POST"])
@jwt_required()
def add_participant():
    if current_user.role != "hr":
        return "Access Denied", 403

    if request.method == "POST":
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        email = request.form.get("email")
        birth_date = request.form.get("birth_date")
        sex = request.form.get("sex")
        division = request.form.get("division")

        create_participant(
            first_name=first_name,
            last_name=last_name,
            email=email,
            birth_date=birth_date if birth_date else None,
            sex=sex,
            division=division,
            institution_id=current_user.institution_id,
        )
        flash("Participant added successfully!", "success")
        return redirect(url_for("hr_views.dashboard") + "#roster")

    return render_template("hr/add_participant.html")


@hr_views.route("/hr/participants/upload-csv", methods=["POST"])
@jwt_required()
def upload_csv():
    """Batch import participants from a CSV file."""
    if current_user.role != "hr":
        return "Access Denied", 403

    file = request.files.get("csv_file")
    if not file or not file.filename.endswith(".csv"):
        flash("Please upload a valid .csv file.", "danger")
        return redirect(url_for("hr_views.dashboard"))

    stream = io.StringIO(file.stream.read().decode("utf-8-sig"))
    reader = csv.DictReader(stream)
    created = 0
    skipped = 0
    errors = []

    # Normalise header names to lowercase stripped
    for row in reader:
        row = {k.strip().lower(): (v.strip() if v else "") for k, v in row.items()}

        first = (
            row.get("first_name") or row.get("first name") or row.get("firstname", "")
        )
        last = row.get("last_name") or row.get("last name") or row.get("lastname", "")
        if not first or not last:
            skipped += 1
            continue

        email = row.get("email") or None
        sex = row.get("sex") or None
        division = row.get("div") or row.get("division") or None
        birth_raw = (
            row.get("birth_date") or row.get("birthdate") or row.get("dob") or None
        )
        birth_date = None
        if birth_raw:
            for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"):
                try:
                    birth_date = datetime.strptime(birth_raw, fmt).date()
                    break
                except ValueError:
                    continue

        # Skip duplicate (same name + institution)
        existing = Participant.query.filter_by(
            first_name=first, last_name=last, institution_id=current_user.institution_id
        ).first()
        if existing:
            skipped += 1
            continue

        try:
            create_participant(
                first_name=first,
                last_name=last,
                email=email,
                birth_date=birth_date,
                sex=sex,
                division=division,
                institution_id=current_user.institution_id,
            )
            created += 1
        except Exception as e:
            errors.append(f"{first} {last}: {str(e)}")
            db.session.rollback()

    if errors:
        flash(
            f'Imported {created}, skipped {skipped}. Errors: {"; ".join(errors[:3])}',
            "danger",
        )
    else:
        flash(
            f"✓ {created} participants imported, {skipped} skipped (duplicates or missing name).",
            "success",
        )

    return redirect(url_for("hr_views.dashboard"))


@hr_views.route("/hr/register", methods=["GET", "POST"])
@jwt_required()
def register():
    if current_user.role != "hr":
        return "Access Denied", 403

    if request.method == "POST":
        season_event_id = request.form.get("season_event_id")
        participant_ids = request.form.getlist("participant_ids")

        if not season_event_id or not participant_ids:
            flash("Please select an event and at least one participant", "danger")
            return redirect(url_for("hr_views.register"))

        count = register_participants(participant_ids, season_event_id)
        flash(f"{count} participants registered successfully!", "success")
        return redirect(url_for("hr_views.dashboard"))

    participants = Participant.query.filter_by(
        institution_id=current_user.institution_id
    ).all()
    events = get_available_events(current_user.institution_id)
    return render_template("hr/register.html", participants=participants, events=events)


# ── EXPORTS ──────────────────────────────────────────────────────────────────


@hr_views.route("/hr/export/roster")
@jwt_required()
def export_roster():
    """Export institution participant roster as CSV."""
    if current_user.role != "hr":
        return "Access Denied", 403
    from flask import Response
    from App.models import Participant
    from App.controllers.hr_controller import get_hr_stats

    stats = get_hr_stats(current_user.institution_id)
    inst = stats["institution"]

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        ["First Name", "Last Name", "Email", "Sex", "Division", "Birth Date", "Status"]
    )
    for p in stats["participants"]:
        if p.has_result:
            status = "Participated"
        elif p.is_no_show:
            status = "No-Show"
        elif p.is_registered:
            status = "Registered"
        else:
            status = "Unregistered"
        writer.writerow(
            [
                p.first_name,
                p.last_name,
                p.email or "",
                p.sex or "",
                p.division or "",
                p.birth_date.isoformat() if p.birth_date else "",
                status,
            ]
        )

    output.seek(0)
    filename = f"{inst.code}_roster_{stats['current_season'].year if stats['current_season'] else 'all'}.csv"
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@hr_views.route("/hr/export/results")
@jwt_required()
def export_results():
    """Export stage results for this institution as CSV."""
    if current_user.role != "hr":
        return "Access Denied", 403
    from flask import Response
    from App.models import (
        Participant,
        Registration,
        Result,
        Stage,
        SeasonEvent,
        Season,
        Event,
    )

    inst_id = current_user.institution_id
    inst = db.session.query(
        __import__("App.models", fromlist=["Institution"]).Institution
    ).get(inst_id)

    current_season = (
        Season.query.filter_by(status="active").order_by(Season.year.desc()).first()
        or Season.query.order_by(Season.year.desc()).first()
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "First Name",
            "Last Name",
            "Division",
            "Event",
            "Stage",
            "Finish Time",
            "Placement",
        ]
    )

    if current_season:
        rows = (
            db.session.query(
                Participant.first_name,
                Participant.last_name,
                Participant.division,
                Event.name,
                Stage.stage_number,
                Result.finish_time,
                Result.placement,
            )
            .join(Registration, Participant.id == Registration.participant_id)
            .join(SeasonEvent, Registration.season_event_id == SeasonEvent.id)
            .join(Event, SeasonEvent.event_id == Event.id)
            .join(Result, Registration.id == Result.registration_id)
            .join(Stage, Result.stage_id == Stage.id)
            .filter(
                Participant.institution_id == inst_id,
                SeasonEvent.season_id == current_season.id,
            )
            .order_by(Participant.last_name, Stage.stage_number)
            .all()
        )

        for r in rows:
            writer.writerow(list(r))

    output.seek(0)
    season_year = current_season.year if current_season else "all"
    filename = f"{inst.code if inst else 'export'}_results_{season_year}.csv"
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
