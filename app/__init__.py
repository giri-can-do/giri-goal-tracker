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
    app.jinja_env.filters["number"] = format_number

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    login_manager.login_view = "auth.login"

    from app import models
    from app.auth import auth_bp
    from app.today import today_bp
    from app.goals import goals_bp
    from app.history import history_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(today_bp)
    app.register_blueprint(goals_bp)
    app.register_blueprint(history_bp)

    return app

def format_number(value):
    if value is None:
        return ""

    try:
        number = float(value)
    except (TypeError, ValueError):
        return value

    # Whole number
    if number.is_integer():
        return f"{int(number):,}"

    # Decimal number
    return f"{number:,.2f}".rstrip("0").rstrip(".")