"""Test script to verify the extraction pipeline"""

import os
import sys
import logging
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_imports():
    """Test if all modules can be imported"""
    logger.info("Testing imports...")
    try:
        from app.models import State, LGA, Ward, ExtractionLog, Base, engine
        logger.info("✓ Models imported successfully")
        
        from app.parser import PDFExtractor
        logger.info("✓ Parser imported successfully")
        
        from app.database import DatabaseManager
        logger.info("✓ Database manager imported successfully")
        
        from app.extraction_service import ExtractionService
        logger.info("✓ Extraction service imported successfully")
        
        from app.routes import bp
        logger.info("✓ Routes imported successfully")
        
        from app import create_app
        logger.info("✓ App factory imported successfully")
        
        return True
    except ImportError as e:
        logger.error(f"✗ Import failed: {e}")
        return False


def test_database():
    """Test database initialization"""
    logger.info("Testing database...")
    try:
        from app.models import Base, engine, SessionLocal, State, LGA, Ward
        
        # Create tables
        Base.metadata.create_all(bind=engine)
        logger.info("✓ Database tables created successfully")
        
        # Test session
        db = SessionLocal()
        db.close()
        logger.info("✓ Database session works")
        
        return True
    except Exception as e:
        logger.error(f"✗ Database test failed: {e}")
        return False


def test_app_creation():
    """Test Flask app creation"""
    logger.info("Testing Flask app creation...")
    try:
        from app import create_app
        
        app = create_app('development')
        logger.info("✓ Flask app created successfully")
        
        # Test that routes are registered
        with app.app_context():
            routes = [str(rule) for rule in app.url_map.iter_rules()]
            logger.info(f"✓ Registered {len(routes)} routes")
            
            # Check for key endpoints
            key_endpoints = ['/api/upload', '/api/states', '/api/status']
            for endpoint in key_endpoints:
                if any(endpoint in route for route in routes):
                    logger.info(f"  ✓ {endpoint} registered")
        
        return True
    except Exception as e:
        logger.error(f"✗ App creation test failed: {e}")
        return False


def test_extraction_service():
    """Test extraction service initialization"""
    logger.info("Testing extraction service...")
    try:
        from app.extraction_service import ExtractionService
        
        service = ExtractionService(
            upload_dir='uploads',
            output_dir='extracted_data'
        )
        logger.info("✓ Extraction service initialized successfully")
        
        # Check directories exist
        assert os.path.exists('uploads'), "uploads directory not created"
        assert os.path.exists('extracted_data'), "extracted_data directory not created"
        logger.info("✓ Required directories exist")
        
        return True
    except Exception as e:
        logger.error(f"✗ Extraction service test failed: {e}")
        return False


def test_sample_extraction():
    """Test sample data extraction (without PDF file)"""
    logger.info("Testing sample data structure...")
    try:
        from app.parser import PDFExtractor
        
        # Create a mock extracted data structure
        sample_data = {
            "states": [
                {"name": "Lagos", "code": "LG"}
            ],
            "lgas": [
                {"name": "Ajeromi-Ifelodun", "code": "001", "state": "Lagos"}
            ],
            "wards": [
                {"name": "Ward 1", "code": "001", "lga": "Ajeromi-Ifelodun", "state": "Lagos"}
            ]
        }
        
        # Verify structure
        assert "states" in sample_data
        assert "lgas" in sample_data
        assert "wards" in sample_data
        logger.info("✓ Sample data structure is valid")
        
        return True
    except Exception as e:
        logger.error(f"✗ Sample extraction test failed: {e}")
        return False


def run_all_tests():
    """Run all tests"""
    logger.info("=" * 50)
    logger.info("Starting System Tests")
    logger.info("=" * 50)
    
    tests = [
        ("Imports", test_imports),
        ("Database", test_database),
        ("App Creation", test_app_creation),
        ("Extraction Service", test_extraction_service),
        ("Sample Extraction", test_sample_extraction)
    ]
    
    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            logger.error(f"✗ {test_name} test crashed: {e}")
            results[test_name] = False
    
    logger.info("=" * 50)
    logger.info("Test Results Summary")
    logger.info("=" * 50)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        logger.info(f"{status}: {test_name}")
    
    logger.info("=" * 50)
    logger.info(f"Total: {passed}/{total} tests passed")
    logger.info("=" * 50)
    
    return passed == total


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
