from .user import user_views
from .index import index_views
from .auth import auth_views
from .admin import setup_admin
from .admin_views import admin_views
from .hr_views import hr_views
from .scorer_views import scorer_views
from .forms import forms_views as forms
from .forms_api import forms_api
#from .dashboards import dashboard_views


views = [user_views, index_views, auth_views, admin_views, hr_views, scorer_views, forms, forms_api] 
# blueprints must be added to this list