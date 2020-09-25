import datetime
from app import db, admin
from flask import session, current_app
from flask_admin.contrib.sqla import ModelView
from flask_login import current_user
from cryptography.fernet import Fernet


class Session(db.Model):
    session_id = db.Column(db.String(), primary_key=True)
    user = db.Column(db.String(), nullable=True)
    token = db.Column(db.LargeBinary(), nullable=True)
    refresh_token = db.Column(db.LargeBinary(), nullable=True)
    expiry = db.Column(db.DateTime, nullable=True)
    state = db.Column(db.String(), nullable=True)
    verifier = db.Column(db.String(), nullable=True)

    def __repr__(self):
        return f'Session({self.user}, {self.session_id}, {self.expiry})'

    @classmethod
    def clean(cls):
        # https://silvaneves.org/deleting-old-items-in-sqlalchemy.html
        # https://stackoverflow.com/questions/5602918/select-null-values-in-sqlalchemy
        expiration_time = 180
        limit = datetime.datetime.now() - datetime.timedelta(days=expiration_time)
        cls.query.filter(cls.expiry < limit).delete()
        cls.query.filter(cls.expiry.is_(None)).delete()
        db.session.commit()
        pass

    is_authenticated = is_active = user is not None

    is_anonymous = not is_authenticated

    def get_id(self):
        return self.session_id


class Master(db.Model):
    session_id = db.Column(db.String(), primary_key=True)
    user = db.Column(db.String(), nullable=True)
    token = db.Column(db.String(), nullable=True)
    refresh_token = db.Column(db.String(), nullable=True)
    expiry = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return f'Master ({self.token}, {self.refresh_token})'


class Adds(db.Model):
    user = db.Column(db.String(), primary_key=True)
    last_add = db.Column(db.DateTime)

    def __repr__(self):
        return f'Add({self.user}, {self.last_add})'


class AdminViewBase(ModelView):
    column_display_pk = True
    column_exclude_list = ['token', 'refresh_token', 'state', 'verifier']
    can_edit = False
    can_create = False
    can_export = True
    page_size = 100

    def is_accessible(self):
        return current_user.is_authenticated and \
               current_user.user in [current_app.config['ADMIN_ACCOUNT_ID'], current_app.config['MASTER_ACCOUNT_ID']]


class AdminViewMaster(ModelView):
    column_display_pk = True
    form_columns = ['session_id', 'user', 'token', 'refresh_token', 'expiry']
    can_delete = False

    def is_accessible(self):
        return current_user.is_authenticated and \
               current_user.user in [current_app.config['ADMIN_ACCOUNT_ID'], current_app.config['MASTER_ACCOUNT_ID']]

    # https://flask-admin.readthedocs.io/en/latest/api/mod_model/#flask_admin.model.BaseModelView.on_model_change
    def on_model_change(self, form, model, is_created):
        # if not type(model.token) == str and not type(model.refresh_token) == str:
        if form.token and form.refresh_token:
            f = Fernet(session['key'])
            model.token = f.decrypt(form.token.data[2:-1].encode()).decode("utf-8")
            model.refresh_token = f.decrypt(form.refresh_token.data[2:-1].encode()).decode("utf-8")


admin.add_view(AdminViewBase(Session, db.session))
admin.add_view(AdminViewBase(Adds, db.session))
admin.add_view(AdminViewMaster(Master, db.session))
