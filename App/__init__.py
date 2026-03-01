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

    @jwt.user_lookup_loader
    def user_lookup_callback(_jwt_header, jwt_data):
        identity = jwt_data["sub"]
        return User.query.get(identity)

    # Register blueprints
    from App.views.auth_views import auth_blueprint
    app.register_blueprint(auth_blueprint)

    from App.views.dashboards import dashboard_views
    app.register_blueprint(dashboard_views)


    return app