from flask import Blueprint, render_template, request, jsonify
from werkzeug.utils import secure_filename
import os
import logging
from datetime import datetime

from app.models import DatabaseManager
from app.extraction_service import ExtractionService

# Configure logging
logger = logging.getLogger(__name__)

# Create blueprint
bp = Blueprint('main', __name__)

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf'}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialize extraction service
extraction_service = ExtractionService()


def allowed_file(filename):
    """Check if file is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@bp.route('/')
def index():
    """Home page"""
    return render_template('index.html')


@bp.route('/api/upload', methods=['POST'])
def upload_pdf():
    """
    Upload and extract from PDF
    
    Returns:
        JSON with extraction results
    """
    try:
        # Check if file is in request
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400
        
        if not allowed_file(file.filename):
            return jsonify({"error": "Only PDF files are allowed"}), 400
        
        # Check file size
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        
        if file_size > MAX_FILE_SIZE:
            return jsonify({"error": f"File too large. Maximum size: {MAX_FILE_SIZE / 1024 / 1024}MB"}), 400
        
        # Save uploaded file
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_")
        filename = timestamp + filename
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        
        logger.info(f"File uploaded: {filename}")
        
        # Process file
        try:
            result = extraction_service.process_uploaded_file(filepath)
            
            # Remove extracted data from response (can be large)
            if 'data' in result and result['data']:
                data = result['data'].copy()
                if 'extracted_data' in data:
                    data['extracted_data'] = {
                        'states': len(data['extracted_data'].get('states', [])),
                        'lgas': len(data['extracted_data'].get('lgas', [])),
                        'wards': len(data['extracted_data'].get('wards', []))
                    }
                result['data'] = data
            
            return jsonify(result), 200
            
        except Exception as e:
            logger.error(f"Error processing file: {str(e)}")
            return jsonify({"status": "error", "message": str(e)}), 500
            
    except Exception as e:
        logger.error(f"Error in upload endpoint: {str(e)}")
        return jsonify({"error": f"Upload failed: {str(e)}"}), 500


@bp.route('/api/states', methods=['GET'])
def get_states():
    """Get all states"""
    try:
        states = DatabaseManager.get_all_states()
        return jsonify(states), 200
    except Exception as e:
        logger.error(f"Error fetching states: {str(e)}")
        return jsonify({"error": str(e)}), 500


@bp.route('/api/states/<int:state_id>/lgas', methods=['GET'])
def get_state_lgas(state_id):
    """Get LGAs for a state"""
    try:
        lgas = DatabaseManager.get_lgas_by_state(state_id)
        return jsonify(lgas), 200
    except Exception as e:
        logger.error(f"Error fetching LGAs: {str(e)}")
        return jsonify({"error": str(e)}), 500


@bp.route('/api/lgas/<int:lga_id>/wards', methods=['GET'])
def get_lga_wards(lga_id):
    """Get wards for an LGA"""
    try:
        wards = DatabaseManager.get_wards_by_lga(lga_id)
        return jsonify(wards), 200
    except Exception as e:
        logger.error(f"Error fetching wards: {str(e)}")
        return jsonify({"error": str(e)}), 500


@bp.route('/api/status', methods=['GET'])
def get_status():
    """Get extraction status and statistics"""
    try:
        status = extraction_service.get_extraction_status()
        return jsonify(status), 200
    except Exception as e:
        logger.error(f"Error fetching status: {str(e)}")
        return jsonify({"error": str(e)}), 500


@bp.route('/api/search', methods=['GET'])
def search():
    """Search for states, LGAs, or wards"""
    try:
        query = request.args.get('q', '').strip()
        search_type = request.args.get('type', 'all')  # all, state, lga, ward
        
        if not query or len(query) < 2:
            return jsonify({"error": "Search query too short"}), 400
        
        results = DatabaseManager.search(query, search_type)
        return jsonify(results), 200
            
    except Exception as e:
        logger.error(f"Error in search: {str(e)}")
        return jsonify({"error": str(e)}), 500


@bp.route('/api/export', methods=['GET'])
def export_data():
    """Export all data as JSON"""
    try:
        export_data = DatabaseManager.export_all_data()
        return jsonify(export_data), 200
    except Exception as e:
        logger.error(f"Error exporting data: {str(e)}")
        return jsonify({"error": str(e)}), 500


@bp.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        stats = DatabaseManager.get_database_stats()
        return jsonify({"status": "healthy", "stats": stats}), 200
    except Exception as e:
        return jsonify({"status": "unhealthy", "error": str(e)}), 500

