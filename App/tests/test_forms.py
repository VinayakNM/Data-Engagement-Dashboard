import pytest
from datetime import date
from App.main import create_app
from App.database import db
from App.models import (
    Admin,
    HR,
    Institution,
    Season,
    Event,
    SeasonEvent,
    Stage,
    Participant,
    Registration,
)


@pytest.fixture(scope="module")
def test_app():
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "JWT_SECRET_KEY": "forms-test-secret",
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
        inst1 = Institution(
            name="Central Bank of TT",
            code="CBTT",
            contact_person="John Doe",
            contact_email="hr@cbtt.com",
            phone="1-868-625-4835",
            status="active",
        )
        inst2 = Institution(name="Sagicor", code="SAGC", status="active")
        db.session.add_all([inst1, inst2])
        db.session.flush()

        admin = Admin(
            firstname="Admin",
            lastname="User",
            username="formadmin",
            email="admin@forms.com",
            password="Admin123!",
        )
        hr = HR(
            firstname="HR",
            lastname="CBTT",
            username="hr_cbtt",
            email="hr@forms.com",
            password="Hr123!",
            institution_id=inst1.id,
        )
        db.session.add_all([admin, hr])
        db.session.flush()

        season = Season(
            year=2025,
            status="planning",
            reg_open=date(2025, 1, 1),
            reg_close=date(2025, 2, 28),
            start_date=date(2025, 3, 1),
            end_date=date(2025, 12, 31),
        )
        db.session.add(season)
        db.session.flush()

        event1 = Event(name="Urban Challenge", event_type="run")
        event2 = Event(name="Cross Country", event_type="run")
        db.session.add_all([event1, event2])
        db.session.flush()

        se = SeasonEvent(
            season_id=season.id,
            event_id=event1.id,
            status="active",
            start_date=date(2025, 3, 1),
            end_date=date(2025, 4, 30),
        )
        db.session.add(se)
        db.session.flush()

        st1 = Stage(
            season_event_id=se.id,
            stage_number=1,
            distance="5K",
            location="Queen's Park",
            stage_date=date(2025, 3, 15),
        )
        st2 = Stage(
            season_event_id=se.id,
            stage_number=2,
            distance="5K",
            location="Brian Lara",
            stage_date=date(2025, 4, 5),
        )
        db.session.add_all([st1, st2])

        part = Participant(first_name="Jane", last_name="Doe", institution_id=inst1.id)
        db.session.add(part)
        db.session.flush()

        reg = Registration(participant_id=part.id, season_event_id=se.id)
        db.session.add(reg)
        db.session.commit()

        yield {
            "admin_email": "admin@forms.com",
            "hr_email": "hr@forms.com",
            "inst1_id": inst1.id,
            "inst2_id": inst2.id,
            "hr_id": hr.id,
            "season_id": season.id,
            "event1_id": event1.id,
            "event2_id": event2.id,
            "se_id": se.id,
        }


def get_token(client, email, password):
    resp = client.post("/api/login", json={"email": email, "password": password})
    assert resp.status_code == 200, f"Login failed for {email}: {resp.data}"
    return resp.get_json().get("access_token")


def auth(token):
    return {"Authorization": f"Bearer {token}"}


#  UNIT TESTS — model fields only


class TestInstitutionModel:

    def test_defaults_to_active(self):
        i = Institution(name="Test", code="T001")
        assert i.status == "active"

    def test_stores_contact_fields(self):
        i = Institution(
            name="Test",
            code="T002",
            contact_person="Alice",
            contact_email="a@t.com",
            phone="1-868-000-0000",
        )
        assert i.contact_person == "Alice"
        assert i.contact_email == "a@t.com"
        assert i.phone == "1-868-000-0000"

    def test_get_json_has_all_fields(self):
        i = Institution(
            name="Test",
            code="T003",
            contact_person="Bob",
            contact_email="b@t.com",
            phone="123",
            status="inactive",
        )
        j = i.get_json()
        for key in (
            "id",
            "name",
            "code",
            "contact_person",
            "contact_email",
            "phone",
            "status",
        ):
            assert key in j


class TestSeasonModel:

    def test_default_status_is_planning(self):
        assert Season(year=2030).status == "planning"

    def test_stores_all_date_fields(self):
        s = Season(
            year=2030,
            reg_open=date(2030, 1, 1),
            reg_close=date(2030, 2, 28),
            start_date=date(2030, 3, 1),
            end_date=date(2030, 12, 31),
        )
        assert s.reg_open == date(2030, 1, 1)
        assert s.reg_close == date(2030, 2, 28)
        assert s.start_date == date(2030, 3, 1)
        assert s.end_date == date(2030, 12, 31)

    def test_dates_default_to_none(self):
        s = Season(year=2031)
        assert s.reg_open is None and s.start_date is None


class TestEventModel:

    def test_stores_event_type(self):
        for t in ("run", "walk", "mixed", "other"):
            assert Event(name="E", event_type=t).event_type == t

    def test_season_event_default_status(self):
        assert SeasonEvent(season_id=1, event_id=1).status == "active"

    def test_stage_stores_distance(self):
        st = Stage(season_event_id=1, stage_number=1, distance="5K")
        assert st.distance == "5K"


#  INTEGRATION TESTS — direct DB


class TestInstitutionIntegration:

    def test_contact_fields_persist(self, test_app, seed):
        with test_app.app_context():
            i = Institution.query.get(seed["inst1_id"])
            assert i.contact_person == "John Doe"
            assert i.contact_email == "hr@cbtt.com"
            assert i.phone == "1-868-625-4835"

    def test_status_update_persists(self, test_app, seed):
        with test_app.app_context():
            i = Institution.query.get(seed["inst2_id"])
            i.status = "inactive"
            db.session.commit()
            assert Institution.query.get(seed["inst2_id"]).status == "inactive"
            i.status = "active"
            db.session.commit()

    def test_duplicate_code_raises(self, test_app):
        with test_app.app_context():
            db.session.add(Institution(name="Dup", code="CBTT"))
            with pytest.raises(Exception):
                db.session.flush()
            db.session.rollback()

    def test_hr_assigned_to_institution(self, test_app, seed):
        with test_app.app_context():
            hr = HR.query.get(seed["hr_id"])
            assert hr.institution_id == seed["inst1_id"]

    def test_hr_without_institution_raises(self, test_app):
        with test_app.app_context():
            with pytest.raises(ValueError):
                HR(
                    firstname="X",
                    lastname="Y",
                    username="xy99",
                    email="xy@test.com",
                    password="pass",
                    institution_id=None,
                )


class TestSeasonIntegration:

    def test_all_dates_persist(self, test_app, seed):
        with test_app.app_context():
            s = Season.query.get(seed["season_id"])
            assert s.reg_open == date(2025, 1, 1)
            assert s.start_date == date(2025, 3, 1)
            assert s.end_date == date(2025, 12, 31)

    def test_duplicate_year_raises(self, test_app):
        with test_app.app_context():
            db.session.add(Season(year=2025))
            with pytest.raises(Exception):
                db.session.flush()
            db.session.rollback()

    def test_has_linked_events(self, test_app, seed):
        with test_app.app_context():
            s = Season.query.get(seed["season_id"])
            assert len(s.season_events) >= 1


class TestEventIntegration:

    def test_stage_persists_distance(self, test_app, seed):
        with test_app.app_context():
            stages = Stage.query.filter_by(season_event_id=seed["se_id"]).all()
            assert all(st.distance == "5K" for st in stages)

    def test_season_event_unique_constraint(self, test_app, seed):
        with test_app.app_context():
            db.session.add(
                SeasonEvent(season_id=seed["season_id"], event_id=seed["event1_id"])
            )
            with pytest.raises(Exception):
                db.session.flush()
            db.session.rollback()

    def test_replace_stages_flush_pattern(self, test_app, seed):
        with test_app.app_context():
            e = Event(name="Replace Test", event_type="walk")
            db.session.add(e)
            db.session.flush()
            se = SeasonEvent(season_id=seed["season_id"], event_id=e.id)
            db.session.add(se)
            db.session.flush()
            db.session.add(Stage(season_event_id=se.id, stage_number=1, distance="3K"))
            db.session.add(Stage(season_event_id=se.id, stage_number=2, distance="5K"))
            db.session.commit()

            # Replace with one stage — flush between delete and insert
            Stage.query.filter_by(season_event_id=se.id).delete(
                synchronize_session="fetch"
            )
            db.session.flush()
            db.session.add(Stage(season_event_id=se.id, stage_number=1, distance="10K"))
            db.session.commit()

            stages = Stage.query.filter_by(season_event_id=se.id).all()
            assert len(stages) == 1
            assert stages[0].distance == "10K"

            # cleanup
            Stage.query.filter_by(season_event_id=se.id).delete()
            db.session.delete(se)
            db.session.delete(e)
            db.session.commit()


#  SYSTEM TESTS — HTTP via test client


class TestFormPageRendering:

    def test_event_form_requires_auth(self, client):
        assert client.get("/eventform").status_code in (302, 401)

    def test_season_form_requires_auth(self, client):
        assert client.get("/seasonform").status_code in (302, 401)

    def test_institution_form_requires_auth(self, client):
        assert client.get("/institutionform").status_code in (302, 401)

    def test_event_form_renders_for_admin(self, client, seed):
        token = get_token(client, seed["admin_email"], "Admin123!")
        resp = client.get("/eventform", headers=auth(token))
        assert resp.status_code == 200

    def test_season_form_renders_for_admin(self, client, seed):
        token = get_token(client, seed["admin_email"], "Admin123!")
        resp = client.get("/seasonform", headers=auth(token))
        assert resp.status_code == 200

    def test_institution_form_renders_for_admin(self, client, seed):
        token = get_token(client, seed["admin_email"], "Admin123!")
        resp = client.get("/institutionform", headers=auth(token))
        assert resp.status_code == 200


class TestInstitutionAPI:

    def test_get_returns_list(self, client, seed):
        token = get_token(client, seed["admin_email"], "Admin123!")
        resp = client.get("/api/forms/institutions", headers=auth(token))
        assert resp.status_code == 200
        assert isinstance(resp.get_json(), list)

    def test_get_includes_contact_fields(self, client, seed):
        token = get_token(client, seed["admin_email"], "Admin123!")
        data = client.get("/api/forms/institutions", headers=auth(token)).get_json()
        inst = next(i for i in data if i["code"] == "CBTT")
        assert inst["contact_person"] == "John Doe"
        assert inst["contact_email"] == "hr@cbtt.com"
        assert inst["phone"] == "1-868-625-4835"

    def test_get_includes_hr_users_and_history(self, client, seed):
        token = get_token(client, seed["admin_email"], "Admin123!")
        data = client.get("/api/forms/institutions", headers=auth(token)).get_json()
        inst = next(i for i in data if i["id"] == seed["inst1_id"])
        assert "hr_users" in inst
        assert "participation_history" in inst
        assert "participant_count" in inst

    def test_create_success(self, client, seed):
        token = get_token(client, seed["admin_email"], "Admin123!")
        resp = client.post(
            "/api/forms/institutions",
            headers=auth(token),
            json={
                "name": "Republic Bank",
                "code": "REPT",
                "contact_person": "Mary Jones",
                "contact_email": "mary@rept.com",
            },
        )
        assert resp.status_code == 201
        assert resp.get_json()["code"] == "REPT"

    def test_create_missing_fields_fails(self, client, seed):
        token = get_token(client, seed["admin_email"], "Admin123!")
        assert (
            client.post(
                "/api/forms/institutions", headers=auth(token), json={"code": "XX"}
            ).status_code
            == 400
        )
        assert (
            client.post(
                "/api/forms/institutions", headers=auth(token), json={"name": "XX"}
            ).status_code
            == 400
        )

    def test_create_duplicate_code_fails(self, client, seed):
        token = get_token(client, seed["admin_email"], "Admin123!")
        resp = client.post(
            "/api/forms/institutions",
            headers=auth(token),
            json={"name": "Dup", "code": "CBTT"},
        )
        assert resp.status_code == 400

    def test_update_success(self, client, seed):
        token = get_token(client, seed["admin_email"], "Admin123!")
        resp = client.put(
            f'/api/forms/institutions/{seed["inst2_id"]}',
            headers=auth(token),
            json={"contact_person": "Updated", "phone": "999"},
        )
        assert resp.status_code == 200
        assert resp.get_json()["contact_person"] == "Updated"

    def test_patch_status(self, client, seed):
        token = get_token(client, seed["admin_email"], "Admin123!")
        resp = client.patch(
            f'/api/forms/institutions/{seed["inst2_id"]}/status',
            headers=auth(token),
            json={"status": "inactive"},
        )
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "inactive"
        client.patch(
            f'/api/forms/institutions/{seed["inst2_id"]}/status',
            headers=auth(token),
            json={"status": "active"},
        )

    def test_assign_and_remove_hr(self, client, seed):
        token = get_token(client, seed["admin_email"], "Admin123!")
        # remove first
        client.delete(
            f'/api/forms/institutions/{seed["inst1_id"]}/remove-hr/{seed["hr_id"]}',
            headers=auth(token),
        )
        # assign
        resp = client.post(
            f'/api/forms/institutions/{seed["inst1_id"]}/assign-hr',
            headers=auth(token),
            json={"user_id": seed["hr_id"]},
        )
        assert resp.status_code == 200
        # remove
        resp = client.delete(
            f'/api/forms/institutions/{seed["inst1_id"]}/remove-hr/{seed["hr_id"]}',
            headers=auth(token),
        )
        assert resp.status_code == 200
        # restore
        client.post(
            f'/api/forms/institutions/{seed["inst1_id"]}/assign-hr',
            headers=auth(token),
            json={"user_id": seed["hr_id"]},
        )

    def test_delete_with_participants_blocked(self, client, seed):
        token = get_token(client, seed["admin_email"], "Admin123!")
        resp = client.delete(
            f'/api/forms/institutions/{seed["inst1_id"]}', headers=auth(token)
        )
        assert resp.status_code == 409

    def test_delete_empty_institution(self, client, seed):
        token = get_token(client, seed["admin_email"], "Admin123!")
        r = client.post(
            "/api/forms/institutions",
            headers=auth(token),
            json={"name": "Throwaway", "code": "THRW"},
        )
        iid = r.get_json()["id"]
        resp = client.delete(f"/api/forms/institutions/{iid}", headers=auth(token))
        assert resp.status_code == 200

    def test_hr_cannot_write(self, client, seed):
        token = get_token(client, seed["hr_email"], "Hr123!")
        assert (
            client.post(
                "/api/forms/institutions",
                headers=auth(token),
                json={"name": "X", "code": "XX"},
            ).status_code
            == 403
        )

    def test_unauthenticated_blocked(self, test_app):
        fresh = test_app.test_client()
        assert fresh.get("/api/forms/institutions").status_code == 401


class TestSeasonAPI:

    def test_get_returns_list_with_date_fields(self, client, seed):
        token = get_token(client, seed["admin_email"], "Admin123!")
        data = client.get("/api/forms/seasons", headers=auth(token)).get_json()
        s = next(x for x in data if x["id"] == seed["season_id"])
        for f in (
            "reg_open",
            "reg_close",
            "start_date",
            "end_date",
            "status",
            "events",
        ):
            assert f in s

    def test_get_includes_linked_events(self, client, seed):
        token = get_token(client, seed["admin_email"], "Admin123!")
        data = client.get("/api/forms/seasons", headers=auth(token)).get_json()
        s = next(x for x in data if x["id"] == seed["season_id"])
        assert len(s["events"]) >= 1

    def test_seasons_list_helper(self, client, seed):
        token = get_token(client, seed["admin_email"], "Admin123!")
        data = client.get("/api/forms/seasons-list", headers=auth(token)).get_json()
        assert isinstance(data, list)
        assert all("id" in s and "year" in s and "status" in s for s in data)

    def test_create_success(self, client, seed):
        token = get_token(client, seed["admin_email"], "Admin123!")
        resp = client.post(
            "/api/forms/seasons",
            headers=auth(token),
            json={
                "year": 2026,
                "status": "planning",
                "reg_open": "2026-01-01",
                "start_date": "2026-03-01",
                "end_date": "2026-12-31",
            },
        )
        assert resp.status_code == 201
        assert resp.get_json()["year"] == 2026

    def test_create_missing_year_fails(self, client, seed):
        token = get_token(client, seed["admin_email"], "Admin123!")
        assert (
            client.post(
                "/api/forms/seasons", headers=auth(token), json={"status": "planning"}
            ).status_code
            == 400
        )

    def test_create_duplicate_year_fails(self, client, seed):
        token = get_token(client, seed["admin_email"], "Admin123!")
        assert (
            client.post(
                "/api/forms/seasons", headers=auth(token), json={"year": 2025}
            ).status_code
            == 400
        )

    def test_update_status_and_dates(self, client, seed):
        token = get_token(client, seed["admin_email"], "Admin123!")
        resp = client.put(
            f'/api/forms/seasons/{seed["season_id"]}',
            headers=auth(token),
            json={"status": "active", "start_date": "2025-03-15"},
        )
        assert resp.status_code == 200
        client.put(
            f'/api/forms/seasons/{seed["season_id"]}',
            headers=auth(token),
            json={"status": "planning"},
        )

    def test_update_include_and_exclude_events(self, client, seed):
        token = get_token(client, seed["admin_email"], "Admin123!")
        resp = client.put(
            f'/api/forms/seasons/{seed["season_id"]}',
            headers=auth(token),
            json={
                "events": [
                    {
                        "event_id": seed["event2_id"],
                        "included": True,
                        "start_date": "2025-05-01",
                    }
                ]
            },
        )
        assert resp.status_code == 200
        resp = client.put(
            f'/api/forms/seasons/{seed["season_id"]}',
            headers=auth(token),
            json={"events": [{"event_id": seed["event2_id"], "included": False}]},
        )
        assert resp.status_code == 200

    def test_delete_season(self, client, seed):
        token = get_token(client, seed["admin_email"], "Admin123!")
        r = client.post("/api/forms/seasons", headers=auth(token), json={"year": 2097})
        sid = r.get_json()["id"]
        resp = client.delete(f"/api/forms/seasons/{sid}", headers=auth(token))
        assert resp.status_code == 200

    def test_hr_cannot_write(self, client, seed):
        token = get_token(client, seed["hr_email"], "Hr123!")
        assert (
            client.post(
                "/api/forms/seasons", headers=auth(token), json={"year": 2080}
            ).status_code
            == 403
        )

    def test_unauthenticated_blocked(self, test_app):
        fresh = test_app.test_client()
        assert fresh.get("/api/forms/seasons").status_code == 401


class TestEventAPI:

    def test_get_all_events(self, client, seed):
        token = get_token(client, seed["admin_email"], "Admin123!")
        data = client.get("/api/forms/events", headers=auth(token)).get_json()
        assert isinstance(data, list) and len(data) >= 2

    def test_get_events_for_season_includes_stages(self, client, seed):
        token = get_token(client, seed["admin_email"], "Admin123!")
        data = client.get(
            f'/api/forms/events?season_id={seed["season_id"]}', headers=auth(token)
        ).get_json()
        ev = next(e for e in data if e["id"] == seed["event1_id"])
        assert len(ev["stages"]) == 2
        assert ev["stages"][0]["distance"] == "5K"

    def test_events_list_helper(self, client, seed):
        token = get_token(client, seed["admin_email"], "Admin123!")
        data = client.get("/api/forms/events-list", headers=auth(token)).get_json()
        assert isinstance(data, list)
        assert all("id" in e and "name" in e for e in data)

    def test_create_event_success(self, client, seed):
        token = get_token(client, seed["admin_email"], "Admin123!")
        resp = client.post(
            "/api/forms/events",
            headers=auth(token),
            json={"name": "New Walk", "event_type": "walk"},
        )
        assert resp.status_code == 201
        assert resp.get_json()["event_type"] == "walk"

    def test_create_event_with_stages(self, client, seed):
        token = get_token(client, seed["admin_email"], "Admin123!")
        resp = client.post(
            "/api/forms/events",
            headers=auth(token),
            json={
                "name": "Staged Run",
                "event_type": "run",
                "season_id": seed["season_id"],
                "stages": [
                    {
                        "distance": "5K",
                        "location": "Park A",
                        "stage_date": "2025-03-10",
                    },
                    {
                        "distance": "3K",
                        "location": "Park B",
                        "stage_date": "2025-03-17",
                    },
                ],
            },
        )
        assert resp.status_code == 201
        assert resp.get_json()["season_event_id"] is not None

    def test_create_missing_name_fails(self, client, seed):
        token = get_token(client, seed["admin_email"], "Admin123!")
        assert (
            client.post(
                "/api/forms/events", headers=auth(token), json={"event_type": "run"}
            ).status_code
            == 400
        )

    def test_update_event(self, client, seed):
        token = get_token(client, seed["admin_email"], "Admin123!")
        resp = client.put(
            f'/api/forms/events/{seed["event2_id"]}',
            headers=auth(token),
            json={"name": "Cross Country Updated"},
        )
        assert resp.status_code == 200
        assert resp.get_json()["name"] == "Cross Country Updated"

    def test_update_event_replaces_stages(self, client, seed):
        token = get_token(client, seed["admin_email"], "Admin123!")
        client.put(
            f'/api/forms/events/{seed["event1_id"]}',
            headers=auth(token),
            json={
                "season_id": seed["season_id"],
                "stages": [
                    {
                        "distance": "10K",
                        "location": "Venue X",
                        "stage_date": "2025-04-01",
                    }
                ],
            },
        )
        data = client.get(
            f'/api/forms/events?season_id={seed["season_id"]}', headers=auth(token)
        ).get_json()
        ev = next(e for e in data if e["id"] == seed["event1_id"])
        assert len(ev["stages"]) == 1
        assert ev["stages"][0]["distance"] == "10K"

    def test_patch_status_active_inactive(self, client, seed):
        token = get_token(client, seed["admin_email"], "Admin123!")
        resp = client.patch(
            f'/api/forms/events/{seed["event1_id"]}/status',
            headers=auth(token),
            json={"season_id": seed["season_id"], "status": "inactive"},
        )
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "inactive"
        client.patch(
            f'/api/forms/events/{seed["event1_id"]}/status',
            headers=auth(token),
            json={"season_id": seed["season_id"], "status": "active"},
        )

    def test_patch_status_missing_season_fails(self, client, seed):
        token = get_token(client, seed["admin_email"], "Admin123!")
        assert (
            client.patch(
                f'/api/forms/events/{seed["event1_id"]}/status',
                headers=auth(token),
                json={"status": "inactive"},
            ).status_code
            == 400
        )

    def test_delete_event(self, client, seed):
        token = get_token(client, seed["admin_email"], "Admin123!")
        r = client.post(
            "/api/forms/events",
            headers=auth(token),
            json={"name": "Delete Me", "event_type": "walk"},
        )
        eid = r.get_json()["id"]
        assert (
            client.delete(f"/api/forms/events/{eid}", headers=auth(token)).status_code
            == 200
        )

    def test_hr_cannot_write(self, client, seed):
        token = get_token(client, seed["hr_email"], "Hr123!")
        assert (
            client.post(
                "/api/forms/events",
                headers=auth(token),
                json={"name": "X", "event_type": "run"},
            ).status_code
            == 403
        )

    def test_unauthenticated_blocked(self, test_app):
        fresh = test_app.test_client()
        assert fresh.get("/api/forms/events").status_code == 401
