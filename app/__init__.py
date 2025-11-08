from flask import Flask
import logging

def create_app(config_name='development'):
    """Application factory"""
    app = Flask(__name__)
    
    # Configuration
    app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size
    app.config['UPLOAD_FOLDER'] = 'uploads'
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    # Initialize database
    from app.models import init_db
    init_db()
    
    # Register blueprints
    from app.routes import bp
    app.register_blueprint(bp)
    
    return app
