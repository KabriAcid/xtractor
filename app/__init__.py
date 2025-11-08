from flask import Flask
import logging
import os

def create_app(config_name='development'):
    """Application factory"""
    # Get the root directory of the project
    root_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    
    # Create Flask app with explicit template and static paths
    app = Flask(
        __name__,
        template_folder=os.path.join(root_dir, 'templates'),
        static_folder=os.path.join(root_dir, 'static')
    )
    
    # Configuration
    app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size
    app.config['UPLOAD_FOLDER'] = os.path.join(root_dir, 'uploads')
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    # Initialize database
    from app.models import init_db
    init_db()
    
    # Register blueprints
    from app.routes import bp
    app.register_blueprint(bp)
    
    return app
