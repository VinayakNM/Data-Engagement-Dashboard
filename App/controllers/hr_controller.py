from App.models import Participant, Registration, Result, Institution
from App.database import db



def get_hr_stats(institution_id):
    total_participants=Participant.query.filter_by(institution_id=institution_id).count()
    participated = db.session.query(Participant)\
        .join(Registration)\
        .join(Result)\
        .filter(Participant.institution_id == institution_id)\
        .distinct(Registration.participant_id).count()
    
    participants=Participant.query.filter_by(institution_id=institution_id).all()

    for p in participants:
        p.has_result = any(r.results for r in p.registrations)

    return {
        "reg_count": total_participants,
        "part_count": participated,
        "no_show_count": total_participants - participated,
        "participants": participants,
        "institution": Institution.query.get(institution_id)
    }