from App.models import *
from flask import Blueprint, request, flash, redirect, url_for, render_template
from flask_jwt_extended import jwt_required, current_user
from App.controllers.admin_controller import (
    create_user_by_admin,
    generate_temp_password,
)
from App.controllers.user_controller import generate_username
from App.controllers.admin_controller import (
    get_admin_data,
    get_total_participants,
    get_active_participants,
    get_participation_rate,
    get_institution_stats,
    get_stage_completion,
    get_participation_by_institution,
    get_participation_status_breakdown,
    get_stage_funnel,
    get_gender_split,
    get_age_group_distribution,
)
from App.database import db

admin_views = Blueprint("admin_views", __name__, template_folder="../templates")


@admin_views.route("/test")
def test():
    return "Admin blueprint works!"


@admin_views.route("/admin/dashboard")
@jwt_required()
def dashboard():
    if current_user.role != "admin":
        return "Access Denied", 403
    # Get institutions for dropdown and table
    institutions = get_admin_data()

    # Get metrics
    # Support filter params from URL query string
    filter_year = request.args.get("season", type=int)
    filter_inst = request.args.get("institution")
    filter_event = request.args.get("event", type=int)
    filter_division = request.args.get("division")

    # Resolve season — use filter year if provided, else active season, else most recent
    if filter_year:
        current_season = Season.query.filter_by(year=filter_year).first()
    else:
        current_season = (
            Season.query.filter_by(status="active").order_by(Season.year.desc()).first()
        )
        if not current_season:
            current_season = Season.query.order_by(Season.year.desc()).first()
    season_id = current_season.id if current_season else None

    # All seasons for the filter dropdown
    all_seasons = Season.query.order_by(Season.year.desc()).all()

    # Events for the event filter dropdown
    events = Event.query.order_by(Event.name).all()

    # Distinct divisions from Participant and Registration tables
    div_rows = (
        db.session.query(Participant.division)
        .filter(Participant.division.isnot(None), Participant.division != "")
        .distinct()
        .all()
    )
    divisions = sorted(set(r[0] for r in div_rows if r[0]))

    total_participants = get_total_participants(
        season_id, filter_event, filter_division, filter_inst
    )
    active_participants = get_active_participants(
        season_id, filter_event, filter_division, filter_inst
    )
    participation_rate = get_participation_rate(
        season_id, filter_event, filter_division, filter_inst
    )
    institution_stats = get_institution_stats(
        season_id, filter_event, filter_division, filter_inst
    )
    stage_completion = get_stage_completion(season_id, filter_event, filter_inst) or []
    participation_by_inst = (
        get_participation_by_institution(
            season_id, filter_event, filter_division, filter_inst
        )
        or []
    )
    status_breakdown = get_participation_status_breakdown(
        season_id, filter_event, filter_division, filter_inst
    ) or {"participated": 0, "no_show": 0, "pending": 0}

    participated_count = status_breakdown.get("participated", 0)
    no_show_count = status_breakdown.get("no_show", 0) + status_breakdown.get(
        "pending", 0
    )
    total_reg = participated_count + no_show_count
    active_pct = (
        round((participated_count / total_reg * 100), 1) if total_reg > 0 else 0
    )
    no_show_pct = round((no_show_count / total_reg * 100), 1) if total_reg > 0 else 0

    # FIX: bar chart max for proportional heights
    max_count = max((i["count"] for i in participation_by_inst), default=1)

    # ── Analytics panels ──────────────────────────────────────────────────────
    stage_funnel = get_stage_funnel(season_id, filter_event, filter_inst)
    gender_split = get_gender_split(season_id, filter_event, filter_inst)
    age_groups = get_age_group_distribution(season_id, filter_event, filter_inst)

    return render_template(
        "admin/admin.html",
        institutions=institutions,
        institution_stats=institution_stats,
        total_participants=total_participants,
        active_participants=active_participants,
        participation_rate=participation_rate,
        stage_completion=stage_completion,
        participation_by_inst=participation_by_inst,
        current_season=current_season,
        all_seasons=all_seasons,
        events=events,
        divisions=divisions,
        filter_year=filter_year or (current_season.year if current_season else None),
        max_count=max_count,
        active_pct=active_pct,
        no_show_pct=no_show_pct,
        stage_funnel=stage_funnel,
        gender_split=gender_split,
        age_groups=age_groups,
    )


@admin_views.route("/admin/users/create", methods=["POST"])
@jwt_required()
def create_user():
    if current_user.role != "admin":
        return "Access Denied", 403

    # Get form data
    firstname = request.form.get("firstname")
    lastname = request.form.get("lastname")
    email = request.form.get("email")
    role = request.form.get("role")
    institution_id = request.form.get("institution_id")

    # Generate username
    from App.controllers.user_controller import generate_username
    from App.models import Institution

    if role == "hr":
        inst = Institution.query.get(institution_id)
        if not inst:
            flash("Institution not found", "danger")
            return redirect(url_for("admin_views.dashboard"))
        username = generate_username(firstname, lastname, inst.code)
    else:
        # For admin/scorer, use role-based username
        base = f"{role}_{firstname[0].upper()}{lastname}".lower()
        username = base

    # Generate temporary password
    temp_password = generate_temp_password()

    # Create user
    user, error = create_user_by_admin(
        firstname=firstname,
        lastname=lastname,
        username=username,
        email=email,
        password=temp_password,
        role=role,
        institution_id=institution_id if role == "hr" else None,
    )

    if error:
        flash(error, "danger")
    else:
        flash(
            f"{role.capitalize()} user created! Username: {username}, Temporary password: {temp_password}",
            "success",
        )
        # Email the temp_password
        print(f"Temporary password for {username}: {temp_password}")

    return redirect(url_for("admin_views.dashboard"))


@admin_views.route("/admin/import-season", methods=["POST"])
@jwt_required()
def import_season_excel():
    """Upload an Excel registration file and seed it into a chosen season.
    Fully dynamic — institutions and events are matched from the database,
    not from a hardcoded map. New institutions and events are auto-created.
    """
    if current_user.role != "admin":
        return "Access Denied", 403

    from datetime import date, datetime
    import io

    try:
        import pandas as pd
    except ImportError:
        flash("pandas not installed on this server.", "danger")
        return redirect(url_for("admin_views.dashboard"))

    try:
        season_year = request.form.get("season_year", type=int)
        file = request.files.get("excel_file")

        if not season_year:
            flash("Please select a season.", "danger")
            return redirect(url_for("admin_views.dashboard"))
        if not file or not file.filename:
            flash("Please choose an Excel file to upload.", "danger")
            return redirect(url_for("admin_views.dashboard"))
        if not file.filename.lower().endswith((".xlsx", ".xls")):
            flash("Only .xlsx / .xls files are supported.", "danger")
            return redirect(url_for("admin_views.dashboard"))

        # ── Resolve season ────────────────────────────────────────────────────
        season = Season.query.filter_by(year=season_year).first()
        if not season:
            flash(f"Season {season_year} not found. Create it first.", "danger")
            return redirect(url_for("admin_views.dashboard"))

        # ── Read file ─────────────────────────────────────────────────────────
        try:
            df = pd.read_excel(io.BytesIO(file.read()))
        except Exception as e:
            flash(f"Could not read file: {e}", "danger")
            return redirect(url_for("admin_views.dashboard"))

        # Strip whitespace from all column names
        df.columns = [str(c).strip() for c in df.columns]
        col_map = {c.upper(): c for c in df.columns}

        def find_col(*candidates):
            for c in candidates:
                if c.upper() in col_map:
                    return col_map[c.upper()]
            return None

        def clean(val):
            if val is None:
                return None
            s = str(val).strip()
            return None if s in ("", "nan", "NaT", "None") else s

        def parse_date(val):
            if val is None:
                return None
            if isinstance(val, datetime):
                return val.date()
            if isinstance(val, date):
                return val
            s = str(val).strip()
            if s in ("", "nan", "NaT", "None"):
                return None
            for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y"):
                try:
                    return datetime.strptime(s.split(" ")[0], fmt).date()
                except ValueError:
                    continue
            return None

        # ── Detect columns ────────────────────────────────────────────────────
        col_first = find_col("FIRST NAME", "FIRSTNAME", "FIRST")
        col_last = find_col("LAST NAME", "LASTNAME", "LAST")
        col_team = find_col("TEAM NAME", "TEAM", "INSTITUTION", "CLUB", "COMPANY")
        col_event = find_col("EVENT NAME", "EVENT", "RACE")
        col_email = find_col("EMAIL", "E-MAIL", "EMAIL ADDRESS")
        col_sex = find_col("SEX", "GENDER")
        col_div = find_col("DIV", "DIVISION", "AGE GROUP", "CATEGORY")
        col_bdate = find_col("BIRTHDATE", "BIRTH DATE", "DOB", "DATE OF BIRTH")

        if not all([col_first, col_last, col_team]):
            flash(
                "File missing required columns (FIRST NAME, LAST NAME, TEAM/INSTITUTION).",
                "danger",
            )
            return redirect(url_for("admin_views.dashboard"))

        df = df[
            df[col_team].notna() & df[col_first].notna() & df[col_last].notna()
        ].copy()
        df.reset_index(drop=True, inplace=True)

        # ── Detect TIME columns for stages ────────────────────────────────────
        stage_nums = [
            n
            for n in range(1, 20)
            if col_map.get(f"TIME{n}") and df[col_map[f"TIME{n}"]].notna().any()
        ]

        all_institutions = Institution.query.all()

        # Build lookup: normalised_key -> Institution
        inst_lookup = {}
        for inst in all_institutions:
            inst_lookup[inst.name.strip().lower()] = inst
            inst_lookup[inst.code.strip().lower()] = inst

        def find_institution(raw_name):
            """Match a raw team name string to an Institution in the DB.
            1. Exact name match (case-insensitive)
            2. Exact code match (case-insensitive)
            3. DB name contains the raw value (substring)
            4. Raw value contains DB name (substring)
            Returns the Institution or None.
            """
            key = raw_name.strip().lower()
            if key in inst_lookup:
                return inst_lookup[key]
            # substring search
            for inst in all_institutions:
                iname = inst.name.lower()
                icode = inst.code.lower()
                if iname in key or key in iname or icode == key:
                    return inst
            return None

        # ── Build event lookup per unique event name in the file ──────────────
        # If no EVENT column, treat all rows as a single event (use season's first event)
        def resolve_event(raw_event_name):
            """Find or create an Event and link it to the season."""
            name = (raw_event_name or "").strip()
            if not name:
                return None, None

            # Find existing event (case-insensitive)
            event = Event.query.filter(
                db.func.lower(Event.name) == name.lower()
            ).first()
            if not event:
                # Auto-create event
                event = Event(name=name, event_type="run")
                db.session.add(event)
                db.session.flush()
                print(f"[IMPORT] Auto-created event: {name}")

            # Link to season if not already
            se = SeasonEvent.query.filter_by(
                season_id=season.id, event_id=event.id
            ).first()
            if not se:
                se = SeasonEvent(
                    season_id=season.id,
                    event_id=event.id,
                    status="active",
                    start_date=date(season.year, 3, 1),
                    end_date=date(season.year, 11, 30),
                )
                db.session.add(se)
                db.session.flush()
                print(f"[IMPORT] Linked event '{name}' to season {season.year}")

            return event, se

        # ── Pre-resolve events and stages ─────────────────────────────────────
        se_cache = {}  # event_name_lower -> SeasonEvent
        stage_cache = {}  # se.id -> {stage_number: Stage}

        if col_event:
            unique_event_names = df[col_event].dropna().unique()
            for raw in unique_event_names:
                name_clean = str(raw).strip()
                if not name_clean or name_clean == "nan":
                    continue
                _, se = resolve_event(name_clean)
                if se:
                    se_cache[name_clean.lower()] = se
        else:
            # No event column — use first event linked to this season, or create a default
            se_list = SeasonEvent.query.filter_by(season_id=season.id).all()
            if se_list:
                default_se = se_list[0]
            else:
                # Auto-create a default event for this season
                default_event = Event.query.first()
                if not default_event:
                    default_event = Event(name="Urban Challenge", event_type="run")
                    db.session.add(default_event)
                    db.session.flush()
                default_se = SeasonEvent(
                    season_id=season.id,
                    event_id=default_event.id,
                    status="active",
                    start_date=date(season.year, 3, 1),
                    end_date=date(season.year, 11, 30),
                )
                db.session.add(default_se)
                db.session.flush()
            se_cache["__default__"] = default_se

        # Ensure stages exist for all resolved SeasonEvents
        db.session.flush()
        month_map = {1: 2, 2: 5, 3: 9, 4: 10, 5: 11}
        for se in se_cache.values():
            for snum in stage_nums:
                if not Stage.query.filter_by(
                    season_event_id=se.id, stage_number=snum
                ).first():
                    db.session.add(
                        Stage(
                            season_event_id=se.id,
                            stage_number=snum,
                            distance="5K",
                            location="TBD",
                            stage_date=date(season.year, month_map.get(snum, 3), 15),
                        )
                    )
            db.session.flush()
            stage_cache[se.id] = {
                s.stage_number: s
                for s in Stage.query.filter_by(season_event_id=se.id).all()
            }

        db.session.commit()

        # ── Import rows ───────────────────────────────────────────────────────
        created = registered = results_added = skipped = 0
        unmatched_institutions = set()

        for _, row in df.iterrows():
            try:
                raw_team = clean(row.get(col_team))
                if not raw_team:
                    skipped += 1
                    continue

                inst = find_institution(raw_team)
                if not inst:
                    unmatched_institutions.add(raw_team)
                    skipped += 1
                    continue

                first = clean(row.get(col_first))
                last = clean(row.get(col_last))
                if not first or not last:
                    skipped += 1
                    continue

                # Resolve which SeasonEvent this row belongs to
                if col_event:
                    raw_ev = clean(row.get(col_event)) or ""
                    se = se_cache.get(raw_ev.lower())
                else:
                    se = se_cache.get("__default__")

                if not se:
                    skipped += 1
                    continue

                email = clean(row.get(col_email)) if col_email else None
                bdate = parse_date(row.get(col_bdate)) if col_bdate else None
                sex = clean(row.get(col_sex)) if col_sex else None
                div = clean(row.get(col_div)) if col_div else None

                # Find or create participant
                p = Participant.query.filter_by(
                    first_name=first, last_name=last, institution_id=inst.id
                ).first()
                if not p:
                    p = Participant(
                        first_name=first,
                        last_name=last,
                        institution_id=inst.id,
                        email=email,
                        birth_date=bdate,
                        sex=sex,
                        division=div,
                    )
                    db.session.add(p)
                    db.session.flush()
                    created += 1

                # Find or create registration
                reg = Registration.query.filter_by(
                    participant_id=p.id, season_event_id=se.id
                ).first()
                if not reg:
                    reg = Registration(
                        participant_id=p.id, season_event_id=se.id, division=div
                    )
                    db.session.add(reg)
                    db.session.flush()
                    registered += 1

                # Import stage results
                stages_for_se = stage_cache.get(se.id, {})
                for snum in stage_nums:
                    time_col = col_map.get(f"TIME{snum}")
                    if not time_col:
                        continue
                    time_val = clean(str(row.get(time_col, "")))
                    if not time_val:
                        continue
                    stage = stages_for_se.get(snum)
                    if not stage:
                        continue
                    if not Result.query.filter_by(
                        registration_id=reg.id, stage_id=stage.id
                    ).first():
                        db.session.add(
                            Result(
                                registration_id=reg.id,
                                stage_id=stage.id,
                                finish_time=time_val,
                            )
                        )
                        results_added += 1

            except Exception as row_error:
                db.session.rollback()
                print(f"[IMPORT] Skipped row due to error: {row_error}")
                skipped += 1
                continue

        db.session.commit()

        msg = (
            f"✓ Season {season_year} import complete — "
            f"{created} participants added, {registered} registered, "
            f"{results_added} results recorded, {skipped} rows skipped."
        )
        if unmatched_institutions:
            msg += (
                f" ⚠ Unmatched institutions (add them first): "
                f'{", ".join(sorted(unmatched_institutions))}'
            )
        flash(msg, "success" if not unmatched_institutions else "warning")
        return redirect(url_for("admin_views.dashboard"))

    except Exception as e:
        db.session.rollback()
        print(f"[IMPORT] Fatal error: {e}")
        flash(f"Import failed: {str(e)}", "danger")
        return redirect(url_for("admin_views.dashboard"))


@admin_views.route("/admin/system/institutions")
@jwt_required()
def institution_form():
    if current_user.role != "admin":
        return "Access Denied", 403
    return render_template("admin/Forms/InstitutionForm.html")


@admin_views.route("/admin/system/events")
@jwt_required()
def event_form():
    if current_user.role != "admin":
        return "Access Denied", 403
    return render_template("admin/Forms/EventForm.html")


@admin_views.route("/admin/system/seasons")
@jwt_required()
def season_form():
    if current_user.role != "admin":
        return "Access Denied", 403
    return render_template("admin/Forms/SeasonForm.html")


@admin_views.route("/admin/users")
@jwt_required()
def list_users():
    if current_user.role != "admin":
        return "Access Denied", 403

    from App.controllers.admin_controller import get_all_users

    users = get_all_users()
    return render_template("admin/users.html", users=users)


# ================== INSTITUTION MANAGEMENT ==================
@admin_views.route("/admin/institutions")
@jwt_required()
def institutions():
    if current_user.role != "admin":
        return "Access Denied", 403

    from App.controllers.admin_controller import get_institution_stats

    current_season = Season.query.order_by(Season.year.desc()).first()
    season_id = current_season.id if current_season else None
    institution_stats = get_institution_stats(season_id)

    return render_template(
        "admin/institutions.html", institution_stats=institution_stats
    )


@admin_views.route("/admin/institutions/add", methods=["POST"])
@jwt_required()
def add_institution():
    if current_user.role != "admin":
        return "Access Denied", 403

    code = request.form.get("code")
    name = request.form.get("name")
    contact = request.form.get("contact")
    email = request.form.get("email")
    phone = request.form.get("phone")

    if not code or not name:
        flash("Code and name are required", "danger")
        return redirect(url_for("admin_views.institutions"))

    if Institution.query.filter_by(code=code).first():
        flash(f"Institution with code {code} already exists", "danger")
        return redirect(url_for("admin_views.institutions"))

    inst = Institution(
        name=name,
        code=code,
        # contact=contact,
        # email=email,
        # phone=phone,
        # is_active=True
    )
    db.session.add(inst)
    db.session.commit()

    flash(f"Institution {code} added successfully", "success")
    return redirect(url_for("admin_views.institutions"))


# ================== OTHER MANAGEMENT PAGES (placeholders) ==================
@admin_views.route("/admin/events")
@jwt_required()
def events():
    if current_user.role != "admin":
        return "Access Denied", 403
    return render_template("admin/coming_soon.html", title="Event Management")


@admin_views.route("/admin/seasons")
@jwt_required()
def seasons():
    if current_user.role != "admin":
        return "Access Denied", 403
    return render_template("admin/coming_soon.html", title="Season Management")


@admin_views.route("/admin/bibs")
@jwt_required()
def bibs():
    if current_user.role != "admin":
        return "Access Denied", 403
    return render_template("admin/coming_soon.html", title="Bib Management")


@admin_views.route("/admin/notifications")
@jwt_required()
def notifications():
    if current_user.role != "admin":
        return "Access Denied", 403
    return render_template("admin/coming_soon.html", title="Notifications")
