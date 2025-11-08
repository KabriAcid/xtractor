from flask import Blueprint, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
import os
import logging
from datetime import datetime

from app.models import get_db, State, LGA, Ward
from app.extraction_service import ExtractionService
from app.database import DatabaseManager

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


def get_db_session():
    """Get database session"""
    from app.models import SessionLocal
    return SessionLocal()


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
        db = get_db_session()
        try:
            result = extraction_service.process_uploaded_file(filepath, db)
            
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
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error in upload endpoint: {str(e)}")
        return jsonify({"error": f"Upload failed: {str(e)}"}), 500


@bp.route('/api/states', methods=['GET'])
def get_states():
    """Get all states"""
    try:
        db = get_db_session()
        try:
            states = DatabaseManager.get_all_states(db)
            data = [
                {
                    "id": state.id,
                    "name": state.state_name,
                    "code": state.state_code,
                    "lga_count": len(state.lgas)
                }
                for state in states
            ]
            return jsonify(data), 200
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error fetching states: {str(e)}")
        return jsonify({"error": str(e)}), 500


@bp.route('/api/states/<int:state_id>/lgas', methods=['GET'])
def get_state_lgas(state_id):
    """Get LGAs for a state"""
    try:
        db = get_db_session()
        try:
            lgas = DatabaseManager.get_lgas_by_state(db, state_id)
            data = [
                {
                    "id": lga.id,
                    "name": lga.lga_name,
                    "code": lga.lga_code,
                    "ward_count": len(lga.wards)
                }
                for lga in lgas
            ]
            return jsonify(data), 200
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error fetching LGAs: {str(e)}")
        return jsonify({"error": str(e)}), 500


@bp.route('/api/lgas/<int:lga_id>/wards', methods=['GET'])
def get_lga_wards(lga_id):
    """Get wards for an LGA"""
    try:
        db = get_db_session()
        try:
            wards = DatabaseManager.get_wards_by_lga(db, lga_id)
            data = [
                {
                    "id": ward.id,
                    "name": ward.ward_name,
                    "code": ward.ward_code
                }
                for ward in wards
            ]
            return jsonify(data), 200
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error fetching wards: {str(e)}")
        return jsonify({"error": str(e)}), 500


@bp.route('/api/status', methods=['GET'])
def get_status():
    """Get extraction status and statistics"""
    try:
        db = get_db_session()
        try:
            status = extraction_service.get_extraction_status(db)
            return jsonify(status), 200
        finally:
            db.close()
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
        
        db = get_db_session()
        try:
            results = {
                "states": [],
                "lgas": [],
                "wards": []
            }
            
            if search_type in ['all', 'state']:
                states = db.query(State).filter(
                    State.state_name.ilike(f"%{query}%")
                ).all()
                results["states"] = [
                    {"id": s.id, "name": s.state_name, "code": s.state_code}
                    for s in states
                ]
            
            if search_type in ['all', 'lga']:
                lgas = db.query(LGA).filter(
                    LGA.lga_name.ilike(f"%{query}%")
                ).all()
                results["lgas"] = [
                    {"id": lg.id, "name": lg.lga_name, "code": lg.lga_code, "state": lg.state.state_name}
                    for lg in lgas
                ]
            
            if search_type in ['all', 'ward']:
                wards = db.query(Ward).filter(
                    Ward.ward_name.ilike(f"%{query}%")
                ).all()
                results["wards"] = [
                    {"id": w.id, "name": w.ward_name, "code": w.ward_code, "lga": w.lga.lga_name}
                    for w in wards
                ]
            
            return jsonify(results), 200
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error in search: {str(e)}")
        return jsonify({"error": str(e)}), 500


@bp.route('/api/export', methods=['GET'])
def export_data():
    """Export all data as JSON"""
    try:
        db = get_db_session()
        try:
            states = DatabaseManager.get_all_states(db)
            
            export_data = {
                "export_time": datetime.utcnow().isoformat(),
                "states": []
            }
            
            for state in states:
                state_data = {
                    "name": state.state_name,
                    "code": state.state_code,
                    "lgas": []
                }
                
                for lga in state.lgas:
                    lga_data = {
                        "name": lga.lga_name,
                        "code": lga.lga_code,
                        "wards": [
                            {"name": w.ward_name, "code": w.ward_code}
                            for w in lga.wards
                        ]
                    }
                    state_data["lgas"].append(lga_data)
                
                export_data["states"].append(state_data)
            
            return jsonify(export_data), 200
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error exporting data: {str(e)}")
        return jsonify({"error": str(e)}), 500
