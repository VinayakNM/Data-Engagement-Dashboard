from App.models import User


def generate_username(firstname, lastname, institution_code):
    """Generate username like FCB_JDoe_1"""
    # Get first initial + lastname
    base = f"{institution_code}_{firstname[0].upper()}{lastname.capitalize()}"
    
    # Check if username exists and add number if needed
    existing = User.query.filter(User.username.like(f"{base}%")).all()
    if not existing:
        return base
    
    # Find highest number suffix
    max_num = 0
    for user in existing:
        try:
            num = int(user.username.split('_')[-1])
            max_num = max(max_num, num)
        except:
            pass
    return f"{base}_{max_num + 1}"


    
