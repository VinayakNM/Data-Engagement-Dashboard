import pytest
from datetime import date, timedelta
from App.main import create_app
from App.database import db
from App.models import (
    Admin, HR, Institution, Season, Event,
    SeasonEvent, Stage, Participant, Registration, Result
)
from App.controllers.admin_controller import (
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


# ─────────────────────────── FIXTURES ───────────────────────────

@pytest.fixture(scope='module')
def test_app():
    app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'JWT_SECRET_KEY': 'admin-metrics-secret',
        'JWT_TOKEN_LOCATION': ['headers'],
        'JWT_COOKIE_CSRF_PROTECT': False,
        'WTF_CSRF_ENABLED': False,
    })
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture(scope='module')
def client(test_app):
    return test_app.test_client()


@pytest.fixture(scope='module')
def seed(test_app):
    with test_app.app_context():
        today = date.today()

        # Institutions
        inst1 = Institution(name='CBTT',         code='CBTT', status='active')
        inst2 = Institution(name='Sagicor',       code='SAGC', status='active')
        inst3 = Institution(name='Empty Corp',    code='EMPT', status='inactive')
        db.session.add_all([inst1, inst2, inst3])
        db.session.flush()

        # Users
        admin = Admin(firstname='Super', lastname='Admin',
                      username='superadmin', email='super@admin.com',
                      password='Admin123!')
        hr1 = HR(firstname='HR', lastname='CBTT',
                 username='hr_cbtt2', email='hr@cbtt2.com',
                 password='Hr123!', institution_id=inst1.id)
        db.session.add_all([admin, hr1])
        db.session.flush()

        # Seasons
        active_season = Season(year=2025, status='active',
                               start_date=today - timedelta(days=90),
                               end_date=today + timedelta(days=90))
        old_season = Season(year=2024, status='closed',
                            start_date=date(2024, 1, 1),
                            end_date=date(2024, 12, 31))
        db.session.add_all([active_season, old_season])
        db.session.flush()

        # Events
        urban = Event(name='Urban Challenge', event_type='run')
        cross = Event(name='Cross Country',   event_type='run')
        relay = Event(name='Corporate Relay', event_type='mixed')
        db.session.add_all([urban, cross, relay])
        db.session.flush()

        # SeasonEvents — active season
        se_urban = SeasonEvent(season_id=active_season.id, event_id=urban.id,
                               start_date=today - timedelta(days=60),
                               end_date=today + timedelta(days=30))
        se_cross = SeasonEvent(season_id=active_season.id, event_id=cross.id,
                               start_date=today + timedelta(days=10),
                               end_date=today + timedelta(days=60))
        # Old season urban
        se_old = SeasonEvent(season_id=old_season.id, event_id=urban.id,
                             start_date=date(2024, 3, 1),
                             end_date=date(2024, 6, 30))
        db.session.add_all([se_urban, se_cross, se_old])
        db.session.flush()

        # Stages — 3 stages for Urban Challenge current season
        st1 = Stage(season_event_id=se_urban.id, stage_number=1,
                    distance='5K', stage_date=today - timedelta(days=50))
        st2 = Stage(season_event_id=se_urban.id, stage_number=2,
                    distance='5K', stage_date=today - timedelta(days=30))
        st3 = Stage(season_event_id=se_urban.id, stage_number=3,
                    distance='5K', stage_date=today + timedelta(days=10))
        db.session.add_all([st1, st2, st3])

        # Participants — mixed genders and divisions
        # inst1: 4 participants
        p1 = Participant(first_name='Alice', last_name='A',
                         institution_id=inst1.id, sex='F', division='F3039')
        p2 = Participant(first_name='Bob',   last_name='B',
                         institution_id=inst1.id, sex='M', division='M3039')
        p3 = Participant(first_name='Carol', last_name='C',
                         institution_id=inst1.id, sex='F', division='F4049')
        p4 = Participant(first_name='Dave',  last_name='D',
                         institution_id=inst1.id, sex='M', division='M2029')
        # inst2: 2 participants
        p5 = Participant(first_name='Eve',   last_name='E',
                         institution_id=inst2.id, sex='F', division='F2029')
        p6 = Participant(first_name='Frank', last_name='F',
                         institution_id=inst2.id, sex='M', division='M5059')
        db.session.add_all([p1, p2, p3, p4, p5, p6])
        db.session.flush()

        # Registrations — all inst1 + inst2 registered for Urban
        reg1 = Registration(participant_id=p1.id, season_event_id=se_urban.id)
        reg2 = Registration(participant_id=p2.id, season_event_id=se_urban.id)
        reg3 = Registration(participant_id=p3.id, season_event_id=se_urban.id)
        reg4 = Registration(participant_id=p4.id, season_event_id=se_urban.id)
        reg5 = Registration(participant_id=p5.id, season_event_id=se_urban.id)
        reg6 = Registration(participant_id=p6.id, season_event_id=se_urban.id)
        db.session.add_all([reg1, reg2, reg3, reg4, reg5, reg6])
        db.session.flush()

        # Results — p1 completed all 3 stages, p2 completed 2, p3 completed 1
        # p4, p5, p6 = no results (no-shows since event dates are past)
        r1a = Result(registration_id=reg1.id, stage_id=st1.id, finish_time='00:25:00', placement=1)
        r1b = Result(registration_id=reg1.id, stage_id=st2.id, finish_time='00:26:00', placement=1)
        r1c = Result(registration_id=reg1.id, stage_id=st3.id, finish_time='00:27:00', placement=1)
        r2a = Result(registration_id=reg2.id, stage_id=st1.id, finish_time='00:30:00', placement=2)
        r2b = Result(registration_id=reg2.id, stage_id=st2.id, finish_time='00:31:00', placement=2)
        r3a = Result(registration_id=reg3.id, stage_id=st1.id, finish_time='00:35:00', placement=3)
        db.session.add_all([r1a, r1b, r1c, r2a, r2b, r3a])
        db.session.commit()

        yield {
            'admin_email':      'super@admin.com',
            'hr_email':         'hr@cbtt2.com',
            'active_season_id': active_season.id,
            'old_season_id':    old_season.id,
            'inst1_id':         inst1.id,
            'inst2_id':         inst2.id,
            'inst3_id':         inst3.id,
            'urban_id':         urban.id,
            'cross_id':         cross.id,
            'relay_id':         relay.id,
            'se_urban_id':      se_urban.id,
            'se_cross_id':      se_cross.id,
            'st1_id':           st1.id,
            'st2_id':           st2.id,
            'st3_id':           st3.id,
            'p1_id': p1.id, 'p2_id': p2.id, 'p3_id': p3.id,
            'p4_id': p4.id, 'p5_id': p5.id, 'p6_id': p6.id,
            'reg1_id': reg1.id, 'reg2_id': reg2.id, 'reg3_id': reg3.id,
        }


def get_token(client, email, password):
    resp = client.post('/api/login', json={'email': email, 'password': password})
    assert resp.status_code == 200
    return resp.get_json().get('access_token')


def auth(token):
    return {'Authorization': f'Bearer {token}'}


# ──────────────────── get_total_participants ────────────────────

class TestGetTotalParticipants:

    def test_counts_all_registered(self, test_app, seed):
        with test_app.app_context():
            total = get_total_participants(seed['active_season_id'])
            assert total == 6  # all 6 registered for urban

    def test_filters_by_event(self, test_app, seed):
        with test_app.app_context():
            # No one registered for Cross Country
            total = get_total_participants(seed['active_season_id'],
                                          event_id=seed['cross_id'])
            assert total == 0

    def test_filters_by_institution(self, test_app, seed):
        with test_app.app_context():
            total = get_total_participants(seed['active_season_id'],
                                          institution_code='CBTT')
            assert total == 4

    def test_filters_by_division(self, test_app, seed):
        with test_app.app_context():
            total = get_total_participants(seed['active_season_id'],
                                          division='F3039')
            assert total == 1  # only Alice

    def test_returns_zero_for_empty_season(self, test_app, seed):
        with test_app.app_context():
            total = get_total_participants(seed['old_season_id'])
            assert total == 0

    def test_returns_zero_if_no_active_season(self, test_app):
        with test_app.app_context():
            # Pass a non-existent season_id
            total = get_total_participants(99999)
            assert total == 0


# ──────────────────── get_active_participants ────────────────────

class TestGetActiveParticipants:

    def test_counts_only_participants_with_results(self, test_app, seed):
        with test_app.app_context():
            active = get_active_participants(seed['active_season_id'])
            assert active == 3  # p1, p2, p3 have results

    def test_filters_by_institution(self, test_app, seed):
        with test_app.app_context():
            active = get_active_participants(seed['active_season_id'],
                                            institution_code='CBTT')
            assert active == 3  # all 3 active are in inst1

    def test_inst2_active_count(self, test_app, seed):
        with test_app.app_context():
            active = get_active_participants(seed['active_season_id'],
                                            institution_code='SAGC')
            assert active == 0  # inst2 has no results


# ──────────────────── get_participation_rate ────────────────────

class TestGetParticipationRate:

    def test_rate_is_correct_percentage(self, test_app, seed):
        with test_app.app_context():
            rate = get_participation_rate(seed['active_season_id'])
            # 3 participated out of 6 registered = 50%
            assert rate == 50.0

    def test_rate_filtered_by_institution(self, test_app, seed):
        with test_app.app_context():
            rate = get_participation_rate(seed['active_season_id'],
                                         institution_code='CBTT')
            # 3 out of 4 inst1 participants = 75%
            assert rate == 75.0

    def test_rate_returns_zero_for_no_registrations(self, test_app, seed):
        with test_app.app_context():
            rate = get_participation_rate(seed['old_season_id'])
            assert rate == 0

    def test_rate_between_0_and_100(self, test_app, seed):
        with test_app.app_context():
            rate = get_participation_rate(seed['active_season_id'])
            assert 0 <= rate <= 100


# ──────────────────── get_institution_stats ────────────────────

class TestGetInstitutionStats:

    def test_returns_list_of_dicts(self, test_app, seed):
        with test_app.app_context():
            stats = get_institution_stats(seed['active_season_id'])
            assert isinstance(stats, list)
            assert len(stats) >= 2

    def test_each_stat_has_required_keys(self, test_app, seed):
        with test_app.app_context():
            stats = get_institution_stats(seed['active_season_id'])
            for s in stats:
                for key in ('id', 'code', 'name', 'participants',
                            'registrations', 'participated', 'participation_rate'):
                    assert key in s

    def test_inst1_registrations_correct(self, test_app, seed):
        with test_app.app_context():
            stats = get_institution_stats(seed['active_season_id'])
            cbtt  = next(s for s in stats if s['code'] == 'CBTT')
            assert cbtt['registrations'] == 4

    def test_inst1_participated_correct(self, test_app, seed):
        with test_app.app_context():
            stats = get_institution_stats(seed['active_season_id'])
            cbtt  = next(s for s in stats if s['code'] == 'CBTT')
            assert cbtt['participated'] == 3

    def test_inst1_rate_correct(self, test_app, seed):
        with test_app.app_context():
            stats = get_institution_stats(seed['active_season_id'])
            cbtt  = next(s for s in stats if s['code'] == 'CBTT')
            assert cbtt['participation_rate'] == 75.0

    def test_filter_by_institution_code(self, test_app, seed):
        with test_app.app_context():
            stats = get_institution_stats(seed['active_season_id'],
                                          institution_code='CBTT')
            assert len(stats) == 1
            assert stats[0]['code'] == 'CBTT'


# ──────────────────── get_stage_completion ────────────────────

class TestGetStageCompletion:

    def test_returns_list_of_stages(self, test_app, seed):
        with test_app.app_context():
            completion = get_stage_completion(seed['active_season_id'],
                                              event_id=seed['urban_id'])
            assert isinstance(completion, list)
            assert len(completion) == 3

    def test_stage_has_required_fields(self, test_app, seed):
        with test_app.app_context():
            completion = get_stage_completion(seed['active_season_id'],
                                              event_id=seed['urban_id'])
            for s in completion:
                assert 'stage'      in s
                assert 'completion' in s
                assert 'completed'  in s
                assert 'total'      in s

    def test_stage1_completion_correct(self, test_app, seed):
        with test_app.app_context():
            completion = get_stage_completion(seed['active_season_id'],
                                              event_id=seed['urban_id'])
            s1 = next(s for s in completion if s['stage'] == 1)
            # 3 out of 6 completed stage 1 = 50%
            assert s1['completed'] == 3
            assert s1['completion'] == 50.0

    def test_stage2_completion_correct(self, test_app, seed):
        with test_app.app_context():
            completion = get_stage_completion(seed['active_season_id'],
                                              event_id=seed['urban_id'])
            s2 = next(s for s in completion if s['stage'] == 2)
            # 2 out of 6 completed stage 2
            assert s2['completed'] == 2

    def test_stage3_completion_correct(self, test_app, seed):
        with test_app.app_context():
            completion = get_stage_completion(seed['active_season_id'],
                                              event_id=seed['urban_id'])
            s3 = next(s for s in completion if s['stage'] == 3)
            # 1 out of 6 completed stage 3
            assert s3['completed'] == 1

    def test_returns_empty_for_event_with_no_stages(self, test_app, seed):
        with test_app.app_context():
            completion = get_stage_completion(seed['active_season_id'],
                                              event_id=seed['cross_id'])
            assert completion == []

    def test_completion_percentages_decrease_across_stages(self, test_app, seed):
        with test_app.app_context():
            completion = get_stage_completion(seed['active_season_id'],
                                              event_id=seed['urban_id'])
            pcts = [s['completion'] for s in completion]
            # Each stage should have <= completion of previous
            assert pcts[0] >= pcts[1] >= pcts[2]

    def test_filters_by_institution(self, test_app, seed):
        with test_app.app_context():
            completion = get_stage_completion(seed['active_season_id'],
                                              event_id=seed['urban_id'],
                                              institution_code='CBTT')
            s1 = next(s for s in completion if s['stage'] == 1)
            # inst1 has 4 registered, 3 completed stage 1
            assert s1['total'] == 4
            assert s1['completed'] == 3


# ──────────────────── get_stage_funnel ────────────────────

class TestGetStageFunnel:

    def test_returns_dict_with_event_name(self, test_app, seed):
        with test_app.app_context():
            funnel = get_stage_funnel(seed['active_season_id'],
                                      event_id=seed['urban_id'])
            assert 'event_name' in funnel
            assert funnel['event_name'] == 'Urban Challenge'

    def test_returns_stages_list(self, test_app, seed):
        with test_app.app_context():
            funnel = get_stage_funnel(seed['active_season_id'],
                                      event_id=seed['urban_id'])
            assert 'stages' in funnel
            assert len(funnel['stages']) == 3

    def test_each_stage_has_required_fields(self, test_app, seed):
        with test_app.app_context():
            funnel = get_stage_funnel(seed['active_season_id'],
                                      event_id=seed['urban_id'])
            for s in funnel['stages']:
                assert 'stage'         in s
                assert 'label'         in s
                assert 'count'         in s
                assert 'pct_of_stage1' in s

    def test_pct_based_on_total_registered(self, test_app, seed):
        with test_app.app_context():
            funnel = get_stage_funnel(seed['active_season_id'],
                                      event_id=seed['urban_id'])
            s1 = funnel['stages'][0]
            # 3 completed out of 6 registered = 50%
            assert s1['pct_of_stage1'] == 50.0

    def test_total_registered_correct(self, test_app, seed):
        with test_app.app_context():
            funnel = get_stage_funnel(seed['active_season_id'],
                                      event_id=seed['urban_id'])
            assert funnel['total_registered'] == 6

    def test_returns_empty_for_nonexistent_season(self, test_app):
        with test_app.app_context():
            funnel = get_stage_funnel(99999)
            assert funnel == {}

    def test_falls_back_to_first_event_if_no_event_id(self, test_app, seed):
        with test_app.app_context():
            funnel = get_stage_funnel(seed['active_season_id'])
            assert funnel != {}
            assert 'event_name' in funnel


# ──────────────────── get_gender_split ────────────────────

class TestGetGenderSplit:

    def test_returns_list(self, test_app, seed):
        with test_app.app_context():
            split = get_gender_split(seed['active_season_id'])
            assert isinstance(split, list)

    def test_contains_male_and_female(self, test_app, seed):
        with test_app.app_context():
            split = get_gender_split(seed['active_season_id'])
            sexes = {s['sex'] for s in split}
            assert 'M' in sexes
            assert 'F' in sexes

    def test_counts_correct(self, test_app, seed):
        with test_app.app_context():
            split = get_gender_split(seed['active_season_id'],
                                     event_id=seed['urban_id'])
            m = next((s for s in split if s['sex'] == 'M'), None)
            f = next((s for s in split if s['sex'] == 'F'), None)
            assert m is not None and m['count'] == 3  # Bob, Dave, Frank
            assert f is not None and f['count'] == 3  # Alice, Carol, Eve

    def test_filters_by_institution(self, test_app, seed):
        with test_app.app_context():
            split = get_gender_split(seed['active_season_id'],
                                     institution_code='CBTT')
            total = sum(s['count'] for s in split)
            assert total == 4  # inst1 has 4 participants

    def test_sex_values_are_uppercase(self, test_app, seed):
        with test_app.app_context():
            split = get_gender_split(seed['active_season_id'])
            for s in split:
                assert s['sex'] == s['sex'].upper()


# ──────────────────── get_age_group_distribution ────────────────────

class TestGetAgeGroupDistribution:

    def test_returns_list(self, test_app, seed):
        with test_app.app_context():
            groups = get_age_group_distribution(seed['active_season_id'])
            assert isinstance(groups, list)

    def test_each_group_has_required_fields(self, test_app, seed):
        with test_app.app_context():
            groups = get_age_group_distribution(seed['active_season_id'])
            for g in groups:
                assert 'group' in g
                assert 'M'     in g
                assert 'F'     in g
                assert 'total' in g

    def test_only_returns_groups_with_data(self, test_app, seed):
        with test_app.app_context():
            groups = get_age_group_distribution(seed['active_season_id'])
            for g in groups:
                assert g['total'] > 0

    def test_totals_are_correct(self, test_app, seed):
        with test_app.app_context():
            groups = get_age_group_distribution(seed['active_season_id'])
            grand_total = sum(g['total'] for g in groups)
            # 6 participants with valid division codes
            assert grand_total == 6

    def test_gender_breakdown_sums_to_total(self, test_app, seed):
        with test_app.app_context():
            groups = get_age_group_distribution(seed['active_season_id'])
            for g in groups:
                assert g['M'] + g['F'] == g['total']

    def test_known_age_band_present(self, test_app, seed):
        with test_app.app_context():
            groups = get_age_group_distribution(seed['active_season_id'])
            band_names = [g['group'] for g in groups]
            # We have F3039 and M3039
            assert '30-39' in band_names


# ──────────────────── get_participation_status_breakdown ────────────────────

class TestGetParticipationStatusBreakdown:

    def test_returns_dict_with_required_keys(self, test_app, seed):
        with test_app.app_context():
            breakdown = get_participation_status_breakdown(seed['active_season_id'])
            assert 'participated' in breakdown
            assert 'no_show'      in breakdown
            assert 'pending'      in breakdown

    def test_participated_count_correct(self, test_app, seed):
        with test_app.app_context():
            breakdown = get_participation_status_breakdown(seed['active_season_id'])
            assert breakdown['participated'] == 3

    def test_total_equals_registrations(self, test_app, seed):
        with test_app.app_context():
            breakdown = get_participation_status_breakdown(seed['active_season_id'])
            total = breakdown['participated'] + breakdown['no_show'] + breakdown['pending']
            assert total == 6

    def test_filters_by_institution(self, test_app, seed):
        with test_app.app_context():
            breakdown = get_participation_status_breakdown(
                seed['active_season_id'], institution_code='CBTT'
            )
            total = breakdown['participated'] + breakdown['no_show'] + breakdown['pending']
            assert total == 4

    def test_returns_zeros_for_empty_season(self, test_app, seed):
        with test_app.app_context():
            breakdown = get_participation_status_breakdown(seed['old_season_id'])
            assert breakdown['participated'] == 0
            assert breakdown['no_show']      == 0
            assert breakdown['pending']      == 0


# ──────────────────── Admin dashboard route ────────────────────

class TestAdminDashboardRoute:

    def test_dashboard_requires_auth(self, client):
        assert client.get('/admin/dashboard').status_code in (302, 401)

    def test_hr_cannot_access_admin_dashboard(self, client, seed):
        token = get_token(client, seed['hr_email'], 'Hr123!')
        resp  = client.get('/admin/dashboard', headers=auth(token))
        assert resp.status_code == 403

    def test_admin_can_access_dashboard(self, client, seed):
        token = get_token(client, seed['admin_email'], 'Admin123!')
        resp  = client.get('/admin/dashboard', headers=auth(token))
        assert resp.status_code == 200

    def test_dashboard_filter_by_season(self, client, seed):
        token = get_token(client, seed['admin_email'], 'Admin123!')
        resp  = client.get(f'/admin/dashboard?season=2025', headers=auth(token))
        assert resp.status_code == 200

    def test_dashboard_filter_by_event(self, client, seed):
        token = get_token(client, seed['admin_email'], 'Admin123!')
        resp  = client.get(
            f'/admin/dashboard?event={seed["urban_id"]}',
            headers=auth(token)
        )
        assert resp.status_code == 200

    def test_dashboard_filter_by_institution(self, client, seed):
        token = get_token(client, seed['admin_email'], 'Admin123!')
        resp  = client.get('/admin/dashboard?institution=CBTT', headers=auth(token))
        assert resp.status_code == 200

    def test_create_user_route_requires_admin(self, client, seed):
        token = get_token(client, seed['hr_email'], 'Hr123!')
        resp  = client.post('/admin/users/create', headers=auth(token), data={
            'firstname': 'Test', 'lastname': 'User',
            'email': 'test_new@test.com', 'role': 'hr',
        })
        assert resp.status_code == 403

    def test_list_users_requires_admin(self, client, seed):
        token = get_token(client, seed['hr_email'], 'Hr123!')
        resp  = client.get('/admin/users', headers=auth(token))
        assert resp.status_code == 403

    def test_admin_can_list_users(self, client, seed):
        token = get_token(client, seed['admin_email'], 'Admin123!')
        resp  = client.get('/admin/users', headers=auth(token))
        assert resp.status_code == 200