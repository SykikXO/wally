from flask import Flask
from config import Config
from app.extensions import db, migrate, login_manager
from flask import render_template

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    # Register Blueprints
    from app.routes.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from app.routes.main import bp as main_bp
    app.register_blueprint(main_bp)

    # Register CLI commands
    from app.commands import load_wallpapers_command, make_admin_command
    app.cli.add_command(load_wallpapers_command)
    app.cli.add_command(make_admin_command)

    # Ensure upload directories exist
    import os
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['QUARANTINE_FOLDER'], exist_ok=True)

    # Register error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/error.html', code=404, title="Page Not Found", message="What you're looking for seems to have vanished into the void."), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('errors/error.html', code=500, title="Server Error", message="Something went wrong on our end. We're dispatching a digital cleanup crew."), 500

    return app


