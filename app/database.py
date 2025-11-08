"""Database operations for storing extracted data"""

from sqlalchemy.orm import Session
from typing import List, Dict, Optional
import logging
from datetime import datetime

from app.models import State, LGA, Ward, ExtractionLog

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manage database operations for extracted data"""
    
    @staticmethod
    def save_extraction_data(db: Session, extracted_data: Dict, filename: str) -> ExtractionLog:
        """
        Save extracted data to database
        
        Args:
            db: Database session
            extracted_data: Dictionary containing states, lgas, wards data
            filename: Original PDF filename
            
        Returns:
            ExtractionLog object
        """
        # Create extraction log
        log = ExtractionLog(
            filename=filename,
            status="in_progress"
        )
        db.add(log)
        db.flush()  # Get the ID
        
        try:
            # Process and save states
            state_map = {}
            for state_data in extracted_data.get("states", []):
                state = DatabaseManager._get_or_create_state(db, state_data)
                state_map[state_data["name"]] = state
            
            # Process and save LGAs
            lga_map = {}
            for lga_data in extracted_data.get("lgas", []):
                state_name = lga_data.get("state")
                if state_name and state_name in state_map:
                    lga = DatabaseManager._get_or_create_lga(db, lga_data, state_map[state_name])
                    lga_map[f"{state_name}_{lga_data['name']}"] = lga
            
            # Process and save Wards
            for ward_data in extracted_data.get("wards", []):
                state_name = ward_data.get("state")
                lga_name = ward_data.get("lga")
                key = f"{state_name}_{lga_name}"
                
                if key in lga_map:
                    DatabaseManager._get_or_create_ward(db, ward_data, lga_map[key])
            
            # Commit all changes
            db.commit()
            
            # Update log
            log.total_lgas_extracted = len(extracted_data.get("lgas", []))
            log.total_wards_extracted = len(extracted_data.get("wards", []))
            log.status = "success"
            log.completed_at = datetime.utcnow()
            db.commit()
            
            logger.info(f"Successfully saved data to database from {filename}")
            return log
            
        except Exception as e:
            db.rollback()
            log.status = "failed"
            log.error_message = str(e)
            log.completed_at = datetime.utcnow()
            db.commit()
            logger.error(f"Error saving data to database: {str(e)}")
            raise
    
    @staticmethod
    def _get_or_create_state(db: Session, state_data: Dict) -> State:
        """Get existing state or create new one"""
        state = db.query(State).filter(
            State.state_name.ilike(state_data["name"])
        ).first()
        
        if not state:
            state = State(
                state_name=state_data["name"],
                state_code=state_data.get("code", "")
            )
            db.add(state)
            db.flush()
            logger.info(f"Created new state: {state_data['name']}")
        
        return state
    
    @staticmethod
    def _get_or_create_lga(db: Session, lga_data: Dict, state: State) -> LGA:
        """Get existing LGA or create new one"""
        lga = db.query(LGA).filter(
            LGA.lga_name.ilike(lga_data["name"]),
            LGA.state_id == state.id
        ).first()
        
        if not lga:
            lga = LGA(
                lga_name=lga_data["name"],
                lga_code=lga_data.get("code", ""),
                state_id=state.id
            )
            db.add(lga)
            db.flush()
            logger.info(f"Created new LGA: {lga_data['name']} in {state.state_name}")
        
        return lga
    
    @staticmethod
    def _get_or_create_ward(db: Session, ward_data: Dict, lga: LGA) -> Ward:
        """Get existing ward or create new one"""
        ward = db.query(Ward).filter(
            Ward.ward_name.ilike(ward_data["name"]),
            Ward.lga_id == lga.id
        ).first()
        
        if not ward:
            ward = Ward(
                ward_name=ward_data["name"],
                ward_code=ward_data.get("code", ""),
                lga_id=lga.id
            )
            db.add(ward)
            db.flush()
            logger.info(f"Created new Ward: {ward_data['name']} in {lga.lga_name}")
        
        return ward
    
    @staticmethod
    def get_all_states(db: Session) -> List[State]:
        """Get all states from database"""
        return db.query(State).all()
    
    @staticmethod
    def get_state_by_name(db: Session, state_name: str) -> Optional[State]:
        """Get state by name"""
        return db.query(State).filter(State.state_name.ilike(state_name)).first()
    
    @staticmethod
    def get_lgas_by_state(db: Session, state_id: int) -> List[LGA]:
        """Get all LGAs in a state"""
        return db.query(LGA).filter(LGA.state_id == state_id).all()
    
    @staticmethod
    def get_wards_by_lga(db: Session, lga_id: int) -> List[Ward]:
        """Get all wards in an LGA"""
        return db.query(Ward).filter(Ward.lga_id == lga_id).all()
    
    @staticmethod
    def get_extraction_logs(db: Session, limit: int = 100) -> List[ExtractionLog]:
        """Get recent extraction logs"""
        return db.query(ExtractionLog).order_by(
            ExtractionLog.created_at.desc()
        ).limit(limit).all()
    
    @staticmethod
    def get_database_stats(db: Session) -> Dict:
        """Get database statistics"""
        total_states = db.query(State).count()
        total_lgas = db.query(LGA).count()
        total_wards = db.query(Ward).count()
        total_extractions = db.query(ExtractionLog).count()
        
        return {
            "total_states": total_states,
            "total_lgas": total_lgas,
            "total_wards": total_wards,
            "total_extractions": total_extractions
        }
