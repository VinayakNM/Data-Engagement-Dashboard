from flask import Flask
from .models import *
from .views import *
from .controllers import *
from .main import *
from App.views import auth_views
from flask_jwt_extended import JWTManager
from App.database import db
from App.config import load_config


def create_app(overrides={}):
    app = Flask(__name__)

    # ... config ...
    load_config(app, overrides)

    db.init_app(app)
    jwt = JWTManager(app)

    @app.context_processor
    def inject_user():
        """Make current_user available in all templates."""
        from flask_jwt_extended import current_user
        try:
            # If we're in a JWT-protected route, current_user will be set
            return dict(current_user=current_user)
        except RuntimeError:
            # Outside of JWT context, current_user is not available
            return dict(current_user=None)

    @jwt.user_lookup_loader
    def user_lookup_callback(_jwt_header, jwt_data):
        identity = jwt_data["sub"]
        return User.query.get(identity)
    

    # Register blueprints

    from App.views.index import index_views
    app.register_blueprint(index_views)

    from App.views.auth_views import auth_views
    app.register_blueprint(auth_views)

    #from App.views.dashboards import dashboard_views
    #app.register_blueprint(dashboard_views)

    from App.views.admin_views import admin_views
    app.register_blueprint(admin_views)

    from App.views.hr_views import hr_views
    app.register_blueprint(hr_views)

    from App.views.scorer_views import scorer_views
    app.register_blueprint(scorer_views)

    return app