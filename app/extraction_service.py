"""Service for handling PDF extraction operations"""

import logging
from typing import Dict, Tuple, BinaryIO
from datetime import datetime
import tempfile
import os

from app.parser import PDFExtractor
from app.models import DatabaseManager

logger = logging.getLogger(__name__)


class ExtractionService:
    """Handle PDF extraction and data storage operations"""
    
    def __init__(self, output_dir: str = "extracted_data"):
        """
        Initialize extraction service
        
        Args:
            output_dir: Directory where extracted JSON files are stored
        """
        self.output_dir = output_dir
        
        # Create directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
    
    def extract_and_save(self, file_obj: BinaryIO, filename: str, save_to_db: bool = True, 
                        save_to_json: bool = False) -> Tuple[Dict, str]:
        """
        Extract data from PDF file object and optionally save to database
        
        Args:
            file_obj: File-like object containing PDF data
            filename: Original filename for logging
            save_to_db: Whether to save to database
            save_to_json: Whether to save to JSON file
            
        Returns:
            Tuple of (extracted_data, status_message)
        """
        temp_path = None
        try:
            logger.info(f"Starting extraction from {filename}")
            
            # Create a temporary file to pass to PDFExtractor
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
                temp_path = temp_file.name
                temp_file.write(file_obj.read())
            
            # Extract data from PDF
            extractor = PDFExtractor(temp_path)
            extracted_data = extractor.extract_all()
            stats = extractor.get_statistics()
            
            logger.info(f"Extraction completed. Stats: {stats}")
            
            # Save to JSON if requested
            json_path = None
            if save_to_json:
                # Remove timestamp prefix if present
                clean_filename = filename.split('_', 1)[-1] if '_' in filename else filename
                json_filename = f"{clean_filename.rsplit('.', 1)[0]}_extracted_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                json_path = os.path.join(self.output_dir, json_filename)
                extractor.export_to_json(json_path)
                logger.info(f"Data exported to JSON: {json_path}")
            
            # Save to database if requested
            log_id = None
            if save_to_db:
                result = DatabaseManager.save_extraction_data(extracted_data, filename)
                log_id = result['log_id']
                logger.info(f"Data saved to database. Log ID: {log_id}")
            
            result = {
                "success": True,
                "filename": filename,
                "stats": stats,
                "json_file": json_path,
                "database_log_id": log_id,
                "extracted_data": extracted_data
            }
            
            return result, "Extraction completed successfully"
            
        except FileNotFoundError:
            error_msg = f"PDF file error: {filename}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}, error_msg
        except Exception as e:
            error_msg = f"Error during extraction: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}, error_msg
        finally:
            # Clean up temporary file
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception as e:
                    logger.warning(f"Could not delete temp file {temp_path}: {e}")
    
    def process_uploaded_file(self, file_obj: BinaryIO, filename: str) -> Dict:
        """
        Process an uploaded PDF file (in-memory, no file saved)
        
        Args:
            file_obj: File-like object containing PDF data
            filename: Original filename
            
        Returns:
            Dictionary with processing results
        """
        try:
            result, message = self.extract_and_save(
                file_obj,
                filename,
                save_to_db=True,
                save_to_json=True
            )
            
            if result.get("success"):
                return {
                    "status": "success",
                    "message": message,
                    "data": result
                }
            else:
                return {
                    "status": "error",
                    "message": result.get("error"),
                    "data": None
                }
                
        except Exception as e:
            error_msg = f"Failed to process file: {str(e)}"
            logger.error(error_msg)
            return {
                "status": "error",
                "message": error_msg,
                "data": None
            }
    
    def get_extraction_status(self) -> Dict:
        """Get extraction statistics and recent logs"""
        try:
            stats = DatabaseManager.get_database_stats()
            logs = DatabaseManager.get_extraction_logs(limit=10)
            
            logs_data = [
                {
                    "id": log['id'],
                    "filename": log['filename'],
                    "status": log['status'],
                    "lgas_extracted": log['total_lgas_extracted'],
                    "wards_extracted": log['total_wards_extracted'],
                    "created_at": log['created_at'],
                    "completed_at": log['completed_at'],
                    "error": log['error_message']
                }
                for log in logs
            ]
            
            return {
                "stats": stats,
                "recent_logs": logs_data
            }
            
        except Exception as e:
            logger.error(f"Error getting extraction status: {str(e)}")
            return {
                "stats": {},
                "recent_logs": [],
                "error": str(e)
            }
