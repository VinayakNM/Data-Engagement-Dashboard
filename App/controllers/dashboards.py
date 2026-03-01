from App.models import User, Institution, Participant, Registration, Result, db
from App.database import db

def get_admin_data():
    return Institution.query.all()

def get_hr_stats(institution_id):
    total_reg=Participant.query.filter_by(institution_id=institution_id).count()
    participated = db.session.query(Registration)\
        .join(Participant)\
        .filter(Participant.institution_id == institution_id)\
        .join(Result).distinct(Registration.participant_id).count()
    participants=Participant.query.filter_by(institution_id=institution_id).all()
    return {
        "reg_count": total_reg,
        "part_count": participated,
        "no_show_count": total_reg - participated,
        "participants": participants,
        "institution": Institution.query.get(institution_id)
    }

def get_scorer_data():
    return Result.query.order_by(Result.id.desc()).limit(10).all()
