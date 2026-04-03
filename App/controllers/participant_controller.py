from datetime import datetime
from App.models import Participant
from App.database import db


def create_participant(first_name, last_name, email, institution_id, **kwargs):
    """Create a new participant."""

    # Handle birth_date conversion if it exists
    birth_date = kwargs.get("birth_date")
    if birth_date and isinstance(birth_date, str):
        try:
            # Convert string 'YYYY-MM-DD' to date object
            kwargs["birth_date"] = datetime.strptime(birth_date, "%Y-%m-%d").date()
        except ValueError:
            # If conversion fails, set to None
            kwargs["birth_date"] = None

    participant = Participant(
        first_name=first_name,
        last_name=last_name,
        email=email,
        institution_id=institution_id,
        **kwargs
    )
    db.session.add(participant)
    db.session.commit()
    return participant
