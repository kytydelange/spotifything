from flask import current_app
from flask_sqlalchemy import SQLAlchemy
from flask_admin import Admin, AdminIndexView, expose
from flask_login import LoginManager, current_user


class SecuredAdminView(AdminIndexView):

    @expose('/')
    def index(self):
        return self.render('/admin/index.html')

    def is_accessible(self):
        return current_user.is_authenticated and \
               current_user.user in [current_app.config['ADMIN_ACCOUNT_ID'], current_app.config['MASTER_ACCOUNT_ID']]


db = SQLAlchemy()
admin = Admin(template_mode='bootstrap3', index_view=SecuredAdminView(url='/admin'))
login_manager = LoginManager()
login_manager.login_view = "main.connect"
login_manager.login_message = None
