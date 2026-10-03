from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager

from config import Config


db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    login_manager.login_view = "auth.login"

    from app import models
    from app.auth import auth_bp
    from app.today import today_bp
    from app.goals import goals_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(today_bp)
    app.register_blueprint(goals_bp)

    return app
