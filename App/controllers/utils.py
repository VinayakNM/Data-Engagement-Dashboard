import csv
from io import TextIOWrapper
from .models import Participant, db 

def process_participants_csv(file, institution_id):
    csv_file = TextIOWrapper(file, encoding='utf-8')
    reader = csv.DictReader(csv_file)
    added_count = 0

    for row in reader:
        if not Participant.query.filter_by(email=row['email']).first():
            new_p = Participant(
                firstname=row['firstname'],
                lastname=row['lastname'],
                email=row['email'],
                institution_id=institution_id
            )

            db.session.add(new_p)
            added_count += 1

    db.session.commit()
    return added_count
