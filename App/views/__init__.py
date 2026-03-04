from .user import user_views
from .index import index_views
from .auth import auth_views
from .admin import setup_admin
from .forms import forms_views
from .dashboards import dashboard_views
from .hr_api import hr_api
from .admin_api import admin_api
from .forms_api import forms_api

views = [
    user_views,
    index_views,
    auth_views,
    forms_views,
    dashboard_views,
    hr_api,
    admin_api,
    forms_api,
]
