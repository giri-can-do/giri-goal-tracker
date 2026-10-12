import os

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager

from config import Config
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.middleware.proxy_fix import ProxyFix


db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[]
)

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    # Trust one reverse proxy only in production
    if os.environ.get("TRUST_PROXY", "false").lower() == "true":
        app.wsgi_app = ProxyFix(
            app.wsgi_app,
            x_for=1,
            x_proto=1,
            x_host=0,
            x_prefix=0,
        )
    app.jinja_env.filters["number"] = format_number

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)

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