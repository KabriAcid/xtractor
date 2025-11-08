"""Service for handling PDF extraction operations"""

import os
import logging
from typing import Dict, Tuple
from datetime import datetime
import json
from pathlib import Path

from app.parser import PDFExtractor
from app.models import DatabaseManager

logger = logging.getLogger(__name__)


class ExtractionService:
    """Handle PDF extraction and data storage operations"""
    
    def __init__(self, upload_dir: str = "uploads", output_dir: str = "extracted_data"):
        """
        Initialize extraction service
        
        Args:
            upload_dir: Directory where uploaded PDFs are stored
            output_dir: Directory where extracted JSON files are stored
        """
        self.upload_dir = upload_dir
        self.output_dir = output_dir
        
        # Create directories if they don't exist
        os.makedirs(upload_dir, exist_ok=True)
        os.makedirs(output_dir, exist_ok=True)
    
    def extract_and_save(self, pdf_path: str, save_to_db: bool = True, 
                        save_to_json: bool = False) -> Tuple[Dict, str]:
        """
        Extract data from PDF and optionally save to database
        
        Args:
            pdf_path: Path to the PDF file
            save_to_db: Whether to save to database
            save_to_json: Whether to save to JSON file
            
        Returns:
            Tuple of (extracted_data, status_message)
        """
        try:
            filename = os.path.basename(pdf_path)
            logger.info(f"Starting extraction from {filename}")
            
            # Extract data from PDF
            extractor = PDFExtractor(pdf_path)
            extracted_data = extractor.extract_all()
            stats = extractor.get_statistics()
            
            logger.info(f"Extraction completed. Stats: {stats}")
            
            # Save to JSON if requested
            json_path = None
            if save_to_json:
                json_filename = f"{Path(filename).stem}_extracted_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
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
            error_msg = f"PDF file not found: {pdf_path}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}, error_msg
        except Exception as e:
            error_msg = f"Error during extraction: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}, error_msg
    
    def process_uploaded_file(self, file_path: str) -> Dict:
        """
        Process an uploaded PDF file
        
        Args:
            file_path: Path to the uploaded file
            
        Returns:
            Dictionary with processing results
        """
        try:
            result, message = self.extract_and_save(
                file_path,
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
