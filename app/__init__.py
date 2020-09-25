from flask import Flask
from app.config import Config
from app.extensions import db, admin, login_manager
from app.main.views import main
from app.features.views import features
from app.errors.error_handlers import errors


def create_app(config_class=Config):
    app = Flask(__name__, template_folder='templates', static_folder='static')
    app.config.from_object(config_class)

    db.init_app(app)
    admin.init_app(app)
    login_manager.init_app(app)

    app.register_blueprint(main)
    app.register_blueprint(features)
    app.register_blueprint(errors)

    return app
