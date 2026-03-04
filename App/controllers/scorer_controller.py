from App.models import Result


def get_recent_results(limit=10):
    return Result.query.order_by(Result.id.desc()).limit(limit).all()