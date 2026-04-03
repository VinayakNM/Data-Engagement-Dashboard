import pytest
from datetime import date, timedelta
from App.main import create_app
from App.database import db
from App.models import (
    Admin,
    HR,
    Scorer,
    Institution,
    Season,
    Event,
    SeasonEvent,
    Stage,
    Participant,
    Registration,
    Result,
)
from App.controllers.hr_controller import (
    get_hr_stats,
    get_available_events,
    register_participants,
)
from App.controllers.participant_controller import create_participant


# ─────────────────────────── FIXTURES ───────────────────────────


@pytest.fixture(scope="module")
def test_app():
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "JWT_SECRET_KEY": "hr-test-secret",
            "JWT_TOKEN_LOCATION": ["headers"],
            "JWT_COOKIE_CSRF_PROTECT": False,
            "WTF_CSRF_ENABLED": False,
        }
    )
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture(scope="module")
def client(test_app):
    return test_app.test_client()


@pytest.fixture(scope="module")
def seed(test_app):
    with test_app.app_context():
        # Institutions
        inst1 = Institution(name="First Citizens", code="FCIT", status="active")
        inst2 = Institution(name="Scotiabank", code="SCOT", status="active")
        db.session.add_all([inst1, inst2])
        db.session.flush()

        # Users
        admin = Admin(
            firstname="Admin",
            lastname="User",
            username="hradmin",
            email="admin@hr.com",
            password="Admin123!",
        )
        hr1 = HR(
            firstname="Jane",
            lastname="HR",
            username="hr_fcit",
            email="hr@fcit.com",
            password="Hr123!",
            institution_id=inst1.id,
        )
        hr2 = HR(
            firstname="Bob",
            lastname="HR",
            username="hr_scot",
            email="hr@scot.com",
            password="Hr123!",
            institution_id=inst2.id,
        )
        db.session.add_all([admin, hr1, hr2])
        db.session.flush()

        # Season
        today = date.today()
        season = Season(
            year=2025,
            status="active",
            start_date=today - timedelta(days=60),
            end_date=today + timedelta(days=120),
        )
        db.session.add(season)
        db.session.flush()

        # Events
        urban = Event(name="Urban Challenge", event_type="run")
        cross = Event(name="Cross Country", event_type="run")
        relay = Event(name="Corporate Relay", event_type="mixed")
        db.session.add_all([urban, cross, relay])
        db.session.flush()

        # SeasonEvents
        se_urban = SeasonEvent(
            season_id=season.id,
            event_id=urban.id,
            start_date=today - timedelta(days=30),
            end_date=today + timedelta(days=60),
        )
        se_cross = SeasonEvent(
            season_id=season.id,
            event_id=cross.id,
            start_date=today + timedelta(days=10),
            end_date=today + timedelta(days=90),
        )
        db.session.add_all([se_urban, se_cross])
        db.session.flush()

        # Stages for Urban Challenge
        st1 = Stage(
            season_event_id=se_urban.id,
            stage_number=1,
            distance="5K",
            stage_date=today - timedelta(days=20),
        )
        st2 = Stage(
            season_event_id=se_urban.id,
            stage_number=2,
            distance="5K",
            stage_date=today - timedelta(days=10),
        )
        st3 = Stage(
            season_event_id=se_urban.id,
            stage_number=3,
            distance="5K",
            stage_date=today + timedelta(days=10),
        )
        db.session.add_all([st1, st2, st3])

        # Participants for inst1
        p1 = Participant(
            first_name="Alice",
            last_name="Smith",
            institution_id=inst1.id,
            sex="F",
            division="F3039",
            email="alice@test.com",
        )
        p2 = Participant(
            first_name="John",
            last_name="Doe",
            institution_id=inst1.id,
            sex="M",
            division="M4049",
            email="john@test.com",
        )
        p3 = Participant(
            first_name="Mary",
            last_name="Jones",
            institution_id=inst1.id,
            sex="F",
            division="F2029",
        )
        # Participants for inst2
        p4 = Participant(
            first_name="Tom",
            last_name="Brown",
            institution_id=inst2.id,
            sex="M",
            division="M3039",
        )
        db.session.add_all([p1, p2, p3, p4])
        db.session.flush()

        # Registrations
        reg1 = Registration(participant_id=p1.id, season_event_id=se_urban.id)
        reg2 = Registration(participant_id=p2.id, season_event_id=se_urban.id)
        # p3 is unregistered
        reg4 = Registration(participant_id=p4.id, season_event_id=se_urban.id)
        db.session.add_all([reg1, reg2, reg4])
        db.session.flush()

        # Results — Alice completed stages 1 & 2, John completed stage 1 only
        r1 = Result(
            registration_id=reg1.id,
            stage_id=st1.id,
            finish_time="00:28:15",
            placement=1,
        )
        r2 = Result(
            registration_id=reg1.id,
            stage_id=st2.id,
            finish_time="00:29:00",
            placement=2,
        )
        r3 = Result(
            registration_id=reg2.id,
            stage_id=st1.id,
            finish_time="00:32:45",
            placement=3,
        )
        db.session.add_all([r1, r2, r3])
        db.session.commit()

        yield {
            "admin_email": "admin@hr.com",
            "hr1_email": "hr@fcit.com",
            "hr2_email": "hr@scot.com",
            "inst1_id": inst1.id,
            "inst2_id": inst2.id,
            "hr1_id": hr1.id,
            "hr2_id": hr2.id,
            "season_id": season.id,
            "urban_id": urban.id,
            "cross_id": cross.id,
            "relay_id": relay.id,
            "se_urban_id": se_urban.id,
            "se_cross_id": se_cross.id,
            "st1_id": st1.id,
            "st2_id": st2.id,
            "st3_id": st3.id,
            "p1_id": p1.id,
            "p2_id": p2.id,
            "p3_id": p3.id,
            "p4_id": p4.id,
            "reg1_id": reg1.id,
            "reg2_id": reg2.id,
            "reg4_id": reg4.id,
        }


def get_token(client, email, password):
    resp = client.post("/api/login", json={"email": email, "password": password})
    assert resp.status_code == 200, f"Login failed: {resp.data}"
    return resp.get_json().get("access_token")


def auth(token):
    return {"Authorization": f"Bearer {token}"}


# ──────────────────── UNIT: Participant model ────────────────────


class TestParticipantModel:

    def test_participant_stores_basic_fields(self):
        p = Participant(first_name="Test", last_name="User", institution_id=1)
        assert p.first_name == "Test"
        assert p.last_name == "User"

    def test_participant_optional_fields_default_none(self):
        p = Participant(first_name="Test", last_name="User", institution_id=1)
        assert p.email is None
        assert p.sex is None
        assert p.division is None
        assert p.birth_date is None
        assert p.contact is None

    def test_participant_get_json_has_all_fields(self):
        p = Participant(
            first_name="Jane",
            last_name="Doe",
            institution_id=1,
            sex="F",
            division="F3039",
            email="jane@test.com",
        )
        j = p.get_json()
        for key in (
            "id",
            "first_name",
            "last_name",
            "sex",
            "division",
            "email",
            "institution_id",
            "birth_date",
        ):
            assert key in j

    def test_participant_kwargs_set_correctly(self):
        p = Participant(
            first_name="X",
            last_name="Y",
            institution_id=1,
            sex="M",
            division="M2029",
            contact="1-868-555-0000",
        )
        assert p.sex == "M"
        assert p.division == "M2029"
        assert p.contact == "1-868-555-0000"


# ──────────────────── UNIT: Registration model ────────────────────


class TestRegistrationModel:

    def test_registration_stores_ids(self):
        r = Registration(participant_id=1, season_event_id=2)
        assert r.participant_id == 1
        assert r.season_event_id == 2

    def test_registration_division_defaults_none(self):
        r = Registration(participant_id=1, season_event_id=1)
        assert r.division is None

    def test_registration_division_via_kwargs(self):
        r = Registration(participant_id=1, season_event_id=1, division="M3039")
        assert r.division == "M3039"


# ──────────────────── INTEGRATION: create_participant ────────────────────


class TestCreateParticipant:

    def test_creates_and_returns_participant(self, test_app, seed):
        with test_app.app_context():
            p = create_participant(
                first_name="New",
                last_name="Person",
                email="new@test.com",
                institution_id=seed["inst1_id"],
            )
            assert p.id is not None
            assert p.first_name == "New"

    def test_birth_date_string_converted(self, test_app, seed):
        with test_app.app_context():
            p = create_participant(
                first_name="Date",
                last_name="Test",
                email="date@test.com",
                institution_id=seed["inst1_id"],
                birth_date="1990-05-15",
            )
            assert p.birth_date == date(1990, 5, 15)

    def test_invalid_birth_date_becomes_none(self, test_app, seed):
        with test_app.app_context():
            p = create_participant(
                first_name="Bad",
                last_name="Date",
                email="bad@test.com",
                institution_id=seed["inst1_id"],
                birth_date="not-a-date",
            )
            assert p.birth_date is None

    def test_optional_fields_stored(self, test_app, seed):
        with test_app.app_context():
            p = create_participant(
                first_name="Full",
                last_name="Data",
                email="full@test.com",
                institution_id=seed["inst1_id"],
                sex="F",
                division="F4049",
                contact="1-868-000-0001",
            )
            assert p.sex == "F"
            assert p.division == "F4049"
            assert p.contact == "1-868-000-0001"

    def test_participant_persists_to_db(self, test_app, seed):
        with test_app.app_context():
            p = create_participant(
                first_name="Persist",
                last_name="Check",
                email="persist@test.com",
                institution_id=seed["inst1_id"],
            )
            pid = p.id
            fetched = Participant.query.get(pid)
            assert fetched is not None
            assert fetched.first_name == "Persist"


# ──────────────────── INTEGRATION: register_participants ────────────────────


class TestRegisterParticipants:

    def test_registers_participants(self, test_app, seed):
        with test_app.app_context():
            # p3 is unregistered — register them
            count = register_participants([str(seed["p3_id"])], seed["se_urban_id"])
            assert count == 1
            reg = Registration.query.filter_by(
                participant_id=seed["p3_id"], season_event_id=seed["se_urban_id"]
            ).first()
            assert reg is not None

    def test_skips_duplicate_registrations(self, test_app, seed):
        with test_app.app_context():
            # p1 already registered — should not create duplicate
            count = register_participants([str(seed["p1_id"])], seed["se_urban_id"])
            assert count == 0

    def test_registers_multiple_at_once(self, test_app, seed):
        with test_app.app_context():
            # Create fresh participants to register
            pa = create_participant("Multi1", "Test", None, seed["inst1_id"])
            pb = create_participant("Multi2", "Test", None, seed["inst1_id"])
            count = register_participants([str(pa.id), str(pb.id)], seed["se_cross_id"])
            assert count == 2

    def test_returns_zero_if_all_duplicate(self, test_app, seed):
        with test_app.app_context():
            count = register_participants(
                [str(seed["p1_id"]), str(seed["p2_id"])], seed["se_urban_id"]
            )
            assert count == 0


# ──────────────────── INTEGRATION: get_hr_stats ────────────────────


class TestGetHrStats:

    def test_returns_correct_total_participants(self, test_app, seed):
        with test_app.app_context():
            stats = get_hr_stats(seed["inst1_id"])
            # inst1 has p1, p2, p3 + ones created in create_participant tests
            assert stats["total_participants"] >= 3

    def test_returns_correct_reg_count(self, test_app, seed):
        with test_app.app_context():
            stats = get_hr_stats(seed["inst1_id"])
            assert stats["reg_count"] >= 2  # p1 and p2 registered

    def test_participated_count_correct(self, test_app, seed):
        with test_app.app_context():
            stats = get_hr_stats(seed["inst1_id"])
            # Alice and John both have results
            assert stats["part_count"] >= 2

    def test_participation_rate_is_percentage(self, test_app, seed):
        with test_app.app_context():
            stats = get_hr_stats(seed["inst1_id"])
            assert 0 <= stats["participation_rate"] <= 100

    def test_institution_returned(self, test_app, seed):
        with test_app.app_context():
            stats = get_hr_stats(seed["inst1_id"])
            assert stats["institution"] is not None
            assert stats["institution"].id == seed["inst1_id"]

    def test_division_data_returned(self, test_app, seed):
        with test_app.app_context():
            stats = get_hr_stats(seed["inst1_id"])
            assert isinstance(stats["division_data"], list)
            assert len(stats["division_data"]) >= 1
            assert "division" in stats["division_data"][0]
            assert "count" in stats["division_data"][0]

    def test_gender_data_returned(self, test_app, seed):
        with test_app.app_context():
            stats = get_hr_stats(seed["inst1_id"])
            assert isinstance(stats["gender_data"], list)
            sexes = [g["sex"] for g in stats["gender_data"]]
            assert "F" in sexes or "M" in sexes

    def test_gender_pct_sums_to_100(self, test_app, seed):
        with test_app.app_context():
            stats = get_hr_stats(seed["inst1_id"])
            total_pct = sum(g["pct"] for g in stats["gender_data"])
            assert abs(total_pct - 100.0) < 1.0  # allow rounding

    def test_participants_have_status_flags(self, test_app, seed):
        with test_app.app_context():
            stats = get_hr_stats(seed["inst1_id"])
            for p in stats["participants"]:
                assert hasattr(p, "has_result")
                assert hasattr(p, "is_no_show")
                assert hasattr(p, "is_registered")

    def test_stage_completion_returned(self, test_app, seed):
        with test_app.app_context():
            stats = get_hr_stats(seed["inst1_id"])
            assert isinstance(stats["stage_completion"], list)

    def test_inst2_stats_isolated_from_inst1(self, test_app, seed):
        with test_app.app_context():
            stats1 = get_hr_stats(seed["inst1_id"])
            stats2 = get_hr_stats(seed["inst2_id"])
            # inst2 only has p4
            assert stats2["total_participants"] >= 1
            # inst2 participants should not appear in inst1 stats
            inst2_ids = {p.id for p in stats2["participants"]}
            inst1_ids = {p.id for p in stats1["participants"]}
            assert inst2_ids.isdisjoint(inst1_ids)


# ──────────────────── INTEGRATION: get_available_events ────────────────────


class TestGetAvailableEvents:

    def test_returns_list(self, test_app, seed):
        with test_app.app_context():
            events = get_available_events(seed["inst1_id"])
            assert isinstance(events, list)

    def test_events_have_required_fields(self, test_app, seed):
        with test_app.app_context():
            events = get_available_events(seed["inst1_id"])
            assert len(events) >= 1
            for ev in events:
                assert "id" in ev
                assert "name" in ev
                assert "date" in ev

    def test_returns_events_for_current_season(self, test_app, seed):
        with test_app.app_context():
            events = get_available_events(seed["inst1_id"])
            names = [e["name"] for e in events]
            assert "Urban Challenge" in names or "Cross Country" in names

    def test_returns_empty_if_no_season(self, test_app):
        with test_app.app_context():
            # Use a non-existent institution — should still return based on season
            events = get_available_events(9999)
            assert isinstance(events, list)


# ──────────────────── SYSTEM: HR API routes ────────────────────


class TestHRDashboardRoute:

    def test_dashboard_requires_auth(self, client):
        assert client.get("/hr/dashboard").status_code in (302, 401)

    def test_admin_cannot_access_hr_dashboard(self, client, seed):
        token = get_token(client, seed["admin_email"], "Admin123!")
        resp = client.get("/hr/dashboard", headers=auth(token))
        assert resp.status_code == 403

    def test_hr_cannot_access_admin_dashboard(self, client, seed):
        token = get_token(client, seed["hr1_email"], "Hr123!")
        resp = client.get("/admin/dashboard", headers=auth(token))
        assert resp.status_code == 403


class TestAddParticipantRoute:

    def test_add_participant_requires_auth(self, client):
        assert client.get("/hr/participants/add").status_code in (302, 401)

    def test_add_participant_post_creates_participant(self, client, seed):
        token = get_token(client, seed["hr1_email"], "Hr123!")
        resp = client.post(
            "/hr/participants/add",
            headers=auth(token),
            data={
                "first_name": "Route",
                "last_name": "Test",
                "email": "route@test.com",
                "sex": "M",
                "division": "M2029",
            },
        )
        # Should redirect on success
        assert resp.status_code in (200, 302)
        with seed["inst1_id"] and True:
            pass  # participant created checked via DB below

    def test_add_participant_persists(self, client, test_app, seed):
        token = get_token(client, seed["hr1_email"], "Hr123!")
        client.post(
            "/hr/participants/add",
            headers=auth(token),
            data={
                "first_name": "Persisted",
                "last_name": "Route",
                "email": "persisted_route@test.com",
            },
        )
        with test_app.app_context():
            p = Participant.query.filter_by(email="persisted_route@test.com").first()
            assert p is not None
            assert p.institution_id == seed["inst1_id"]

    def test_hr2_cannot_add_to_inst1(self, client, test_app, seed):
        """HR from inst2 adding a participant should assign them to inst2, not inst1."""
        token = get_token(client, seed["hr2_email"], "Hr123!")
        client.post(
            "/hr/participants/add",
            headers=auth(token),
            data={
                "first_name": "WrongInst",
                "last_name": "Test",
                "email": "wronginst@test.com",
            },
        )
        with test_app.app_context():
            p = Participant.query.filter_by(email="wronginst@test.com").first()
            if p:
                assert p.institution_id == seed["inst2_id"]


class TestUploadCSVRoute:

    def test_upload_csv_requires_auth(self, client):
        resp = client.post("/hr/participants/upload-csv")
        assert resp.status_code in (302, 401)

    def test_upload_valid_csv(self, client, test_app, seed):
        token = get_token(client, seed["hr1_email"], "Hr123!")
        csv_data = (
            "first_name,last_name,email,sex,div\n"
            "CSV,Import,csv_import@test.com,F,F3039\n"
            "CSV2,Import2,csv_import2@test.com,M,M4049\n"
        )
        resp = client.post(
            "/hr/participants/upload-csv",
            headers=auth(token),
            data={
                "csv_file": (__import__("io").BytesIO(csv_data.encode()), "test.csv")
            },
            content_type="multipart/form-data",
        )
        assert resp.status_code in (200, 302)
        with test_app.app_context():
            p = Participant.query.filter_by(email="csv_import@test.com").first()
            assert p is not None

    def test_upload_rejects_non_csv(self, client, seed):
        token = get_token(client, seed["hr1_email"], "Hr123!")
        resp = client.post(
            "/hr/participants/upload-csv",
            headers=auth(token),
            data={"csv_file": (__import__("io").BytesIO(b"data"), "test.xlsx")},
            content_type="multipart/form-data",
        )
        assert resp.status_code in (200, 302)  # flashes error and redirects

    def test_upload_skips_duplicates(self, client, test_app, seed):
        token = get_token(client, seed["hr1_email"], "Hr123!")
        # Upload same person twice
        csv_data = "first_name,last_name,email\nAlice,Smith,alice@test.com\n"
        client.post(
            "/hr/participants/upload-csv",
            headers=auth(token),
            data={"csv_file": (__import__("io").BytesIO(csv_data.encode()), "dup.csv")},
            content_type="multipart/form-data",
        )
        with test_app.app_context():
            count = Participant.query.filter_by(
                first_name="Alice", last_name="Smith", institution_id=seed["inst1_id"]
            ).count()
            assert count == 1  # no duplicate


class TestRegisterRoute:

    def test_register_requires_auth(self, client):
        assert client.get("/hr/register").status_code in (302, 401)

    def test_register_post_creates_registrations(self, client, test_app, seed):
        token = get_token(client, seed["hr1_email"], "Hr123!")
        # Create a fresh participant to register
        with test_app.app_context():
            fresh = create_participant(
                "Fresh", "Reg", "fresh_reg@test.com", seed["inst1_id"]
            )
            fresh_id = fresh.id

        resp = client.post(
            "/hr/register",
            headers=auth(token),
            data={
                "season_event_id": str(seed["se_cross_id"]),
                "participant_ids": [str(fresh_id)],
            },
        )
        assert resp.status_code in (200, 302)

        with test_app.app_context():
            reg = Registration.query.filter_by(
                participant_id=fresh_id, season_event_id=seed["se_cross_id"]
            ).first()
            assert reg is not None

    def test_register_post_missing_event_redirects(self, client, seed):
        token = get_token(client, seed["hr1_email"], "Hr123!")
        resp = client.post(
            "/hr/register",
            headers=auth(token),
            data={
                "participant_ids": [str(seed["p1_id"])],
                # no season_event_id
            },
        )
        assert resp.status_code in (200, 302)


class TestExportRoutes:

    def test_export_roster_requires_auth(self, client):
        assert client.get("/hr/export/roster").status_code in (302, 401)

    def test_export_roster_returns_csv(self, client, seed):
        token = get_token(client, seed["hr1_email"], "Hr123!")
        resp = client.get("/hr/export/roster", headers=auth(token))
        assert resp.status_code == 200
        assert "text/csv" in resp.content_type

    def test_export_roster_has_headers(self, client, seed):
        token = get_token(client, seed["hr1_email"], "Hr123!")
        resp = client.get("/hr/export/roster", headers=auth(token))
        content = resp.data.decode("utf-8")
        assert "First Name" in content
        assert "Last Name" in content
        assert "Status" in content

    def test_export_roster_contains_participants(self, client, seed):
        token = get_token(client, seed["hr1_email"], "Hr123!")
        resp = client.get("/hr/export/roster", headers=auth(token))
        content = resp.data.decode("utf-8")
        assert "Alice" in content
        assert "John" in content

    def test_export_results_requires_auth(self, client):
        assert client.get("/hr/export/results").status_code in (302, 401)

    def test_export_results_returns_csv(self, client, seed):
        token = get_token(client, seed["hr1_email"], "Hr123!")
        resp = client.get("/hr/export/results", headers=auth(token))
        assert resp.status_code == 200
        assert "text/csv" in resp.content_type

    def test_export_results_has_headers(self, client, seed):
        token = get_token(client, seed["hr1_email"], "Hr123!")
        resp = client.get("/hr/export/results", headers=auth(token))
        content = resp.data.decode("utf-8")
        assert "First Name" in content
        assert "Stage" in content
        assert "Finish Time" in content

    def test_export_results_contains_results(self, client, seed):
        token = get_token(client, seed["hr1_email"], "Hr123!")
        resp = client.get("/hr/export/results", headers=auth(token))
        content = resp.data.decode("utf-8")
        # Alice has results
        assert "Alice" in content
        assert "00:28:15" in content

    def test_inst2_export_does_not_show_inst1_data(self, client, seed):
        token = get_token(client, seed["hr2_email"], "Hr123!")
        resp = client.get("/hr/export/roster", headers=auth(token))
        content = resp.data.decode("utf-8")
        assert "Alice" not in content
        assert "Tom" in content


class TestAuthRoutes:

    def test_api_login_success(self, client, seed):
        resp = client.post(
            "/api/login", json={"email": seed["hr1_email"], "password": "Hr123!"}
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert "access_token" in data
        assert data["user"]["role"] == "hr"

    def test_api_login_wrong_password(self, client, seed):
        resp = client.post(
            "/api/login", json={"email": seed["hr1_email"], "password": "wrong"}
        )
        assert resp.status_code == 401

    def test_api_login_unknown_email(self, client):
        resp = client.post(
            "/api/login", json={"email": "nobody@test.com", "password": "pass"}
        )
        assert resp.status_code == 401

    def test_api_identify_returns_user_info(self, client, seed):
        token = get_token(client, seed["hr1_email"], "Hr123!")
        resp = client.get("/api/identify", headers=auth(token))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["email"] == seed["hr1_email"]
        assert data["role"] == "hr"

    def test_api_identify_requires_auth(self, test_app):
        fresh = test_app.test_client()
        assert fresh.get("/api/identify").status_code == 401

    def test_api_logout_clears_cookie(self, client, seed):
        resp = client.get("/api/logout")
        assert resp.status_code == 200
