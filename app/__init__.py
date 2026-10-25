import os
from flask import Flask, session
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
from config import Config

db = SQLAlchemy()
csrf = CSRFProtect()


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
    db.init_app(app)
    csrf.init_app(app)

    from .routes import bp
    from .i18n import T, LANGS
    from .services import policy_text
    app.register_blueprint(bp)

    @app.template_filter("dt")
    def fmt_dt(d):
        return d.strftime("%d %b %Y, %I:%M %p") if d else ""

    @app.context_processor
    def inject():
        lang = session.get("lang", "en")
        tt = lambda k, **kw: T(lang, k, **kw)
        return dict(t=tt, lang=lang, LANGS=LANGS, app_name=Config.APP_NAME, cfg=Config,
                    policy_text=lambda b: policy_text(tt, b))
    return app
