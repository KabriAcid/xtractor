import pdfplumber
import json
import re
from typing import List, Dict, Tuple, Optional
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Nigerian states in alphabetical order
NIGERIAN_STATES = [
    "ABIA", "ADAMAWA", "AKWA IBOM", "ANAMBRA", "BAUCHI", "BAYELSA",
    "BENUE", "BORNO", "CROSS RIVER", "DELTA", "EBONYI", "EDO",
    "EKITI", "ENUGU", "FCT", "GOMBE", "IMO", "JIGAWA", "KADUNA",
    "KANO", "KATSINA", "KEBBI", "KOGI", "KWARA", "LAGOS", "LARABA",
    "NASARAWA", "NIGER", "OGUN", "ONDO", "OSUN", "OYO", "PLATEAU",
    "RIVERS", "SOKOTO", "TARABA", "YOBE", "ZAMFARA"
]


class PDFExtractor:
    """Extract LGA and Ward information from Nigerian Electoral PDFs"""
    
    def __init__(self, pdf_path: str):
        """Initialize PDF extractor"""
        self.pdf_path = pdf_path
        self.extracted_data = {
            "states": [],
            "lgas": [],
            "wards": []
        }
        self.current_state = None
        self.current_lga = None
        self.seen_states = set()
        self.seen_lgas = set()
        self.seen_wards = set()
        
    def extract_all(self) -> Dict:
        """Extract all data from PDF"""
        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                logger.info(f"PDF opened successfully. Total pages: {len(pdf.pages)}")
                
                for page_num, page in enumerate(pdf.pages):
                    logger.info(f"Processing page {page_num + 1}/{len(pdf.pages)}")
                    self._process_page(page, page_num)
                    
            logger.info("PDF extraction completed successfully")
            return self.extracted_data
            
        except Exception as e:
            logger.error(f"Error extracting PDF: {str(e)}")
            raise
    
    def _process_page(self, page, page_num: int):
        """Process a single page - prioritize tables over text"""
        # First try to extract from tables (more structured)
        tables = page.extract_tables()
        if tables:
            for table in tables:
                self._extract_table_data(table)
        
        # Then extract from text for state headers and other data
        text = page.extract_text()
        if text:
            self._extract_text_data(text)
    
    def _extract_text_data(self, text: str):
        """Extract data from plain text - mainly for state headers"""
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            
            if not line or len(line) < 2:
                continue
            
            # Detect state headers (all caps, relatively short)
            if self._is_state_header(line):
                self._process_state_line(line)
    
    def _extract_table_data(self, table: List[List]):
        """
        Extract data from PDF tables.
        Expected structure:
        | LGA NAME | LGA CODE | WARD NAME | [empty] | [empty] | WARD CODE |
        """
        if not table or len(table) == 0:
            return
        
        # Skip header rows
        for row_idx, row in enumerate(table):
            if not row or all(cell is None or cell == '' for cell in row):
                continue
            
            # Clean row
            clean_row = [str(cell).strip() if cell else '' for cell in row]
            
            # Check if this is a header row (contains "LGA NAME", "WARD CODE" etc)
            if self._is_table_header(clean_row):
                continue
            
            # Parse the row
            self._parse_table_row(clean_row, row_idx)
    
    def _is_table_header(self, row: List[str]) -> bool:
        """Check if row is a table header"""
        header_keywords = ['LGA NAME', 'WARD NAME', 'WARD CODE', 'LGA CODE', 'CODE']
        row_text = ' '.join(row).upper()
        return sum(1 for kw in header_keywords if kw in row_text) >= 2
    
    def _is_state_header(self, line: str) -> bool:
        """Detect state headers"""
        # State headers are typically:
        # - All uppercase
        # - No numbers
        # - 3-30 characters
        # - Single line
        
        if len(line) > 40 or len(line) < 3:
            return False
        
        # Check if all uppercase and mostly letters
        upper_count = sum(1 for c in line if c.isupper())
        letter_count = sum(1 for c in line if c.isalpha() or c.isspace())
        
        if upper_count > len(line) * 0.8 and letter_count > len(line) * 0.7:
            return True
        
        return False
    
    def _parse_table_row(self, row: List[str], row_idx: int):
        """
        Parse table row.
        Structure: [LGA_NAME, LGA_CODE, WARD_NAME, _, _, WARD_CODE]
        or variations with different column counts
        """
        # Filter out empty cells
        non_empty = [cell for cell in row if cell]
        
        if len(non_empty) < 2:
            return
        
        # Try to identify the structure
        # Common patterns:
        # 1. [LGA_NAME, LGA_CODE, WARD_NAME, WARD_CODE]
        # 2. [LGA_CODE, LGA_NAME, WARD_NAME, WARD_CODE]
        # 3. Multiple rows per LGA with Ward data
        
        # Check if row has mostly text in first column and codes in others
        has_code = any(cell.isdigit() or (cell.isalnum() and len(cell) <= 5) 
                      for cell in non_empty[-2:])
        
        if not has_code:
            return
        
        # Try to parse as LGA + Ward row
        if len(non_empty) >= 2:
            self._detect_lga_ward_data(non_empty)
    
    def _detect_lga_ward_data(self, cells: List[str]):
        """
        Detect LGA and Ward data from a row of cells.
        Handles various table structures.
        """
        if not self.current_state:
            return
        
        # Filter empty cells
        cells = [c.strip() for c in cells if c.strip()]
        
        if len(cells) < 2:
            return
        
        # Strategy: look for patterns
        # If we have 2 cells and one looks like a code, it's likely LGA
        # If we have 4+ cells, it's likely LGA + WARD
        
        if len(cells) == 2:
            # Could be [LGA_NAME, LGA_CODE] or [WARD_NAME, WARD_CODE]
            name, code = cells[0], cells[1]
            
            if self._looks_like_code(code):
                if not self.current_lga or self._is_new_lga(name, code):
                    self._add_lga(name, code)
                else:
                    self._add_ward(name, code)
        
        elif len(cells) >= 3:
            # Pattern: [LGA_NAME, LGA_CODE, WARD_NAME, WARD_CODE, ...]
            # Or: [LGA_NAME, WARD_NAME, WARD_CODE, ...]
            
            # Find codes (numeric or alphanumeric)
            code_indices = [i for i, c in enumerate(cells) 
                          if self._looks_like_code(c)]
            
            if len(code_indices) >= 2:
                # We have at least 2 codes, likely LGA + WARD
                lga_code_idx = 0
                ward_code_idx = code_indices[0]
                
                if len(code_indices) > 1:
                    ward_code_idx = code_indices[-1]
                
                # Extract LGA
                lga_name = cells[0]
                lga_code = cells[1] if len(cells) > 1 and self._looks_like_code(cells[1]) else ''
                
                if lga_code:
                    self._add_lga(lga_name, lga_code)
                
                # Extract WARD(S)
                if len(cells) >= 4:
                    ward_name = cells[2]
                    ward_code = cells[3] if len(cells) > 3 else ''
                    if ward_name and ward_code:
                        self._add_ward(ward_name, ward_code)
            
            elif len(code_indices) == 1:
                # Only one code, treat as LGA
                code_idx = code_indices[0]
                if code_idx <= 1:
                    self._add_lga(cells[0], cells[code_idx])
                else:
                    # Code at end, likely WARD
                    self._add_ward(cells[0], cells[code_idx])
    
    def _looks_like_code(self, text: str) -> bool:
        """Check if text looks like a code (numeric or short alphanumeric)"""
        if not text:
            return False
        
        text = text.strip()
        
        # Pure numbers
        if text.isdigit():
            return len(text) <= 5
        
        # Short alphanumeric
        if text.isalnum() and len(text) <= 5:
            digit_count = sum(1 for c in text if c.isdigit())
            return digit_count > 0
        
        return False
    
    def _is_new_lga(self, name: str, code: str) -> bool:
        """Check if this is a new LGA (not the current one)"""
        if not self.current_lga:
            return True
        
        return (self.current_lga['name'].upper() != name.upper() or 
                self.current_lga['code'] != code)
    
    def _add_state(self, name: str, code: str = ''):
        """Add a state to extracted data"""
        key = name.upper()
        
        if key in self.seen_states:
            return
        
        state_data = {
            "name": name,
            "code": code or self._generate_code(name)
        }
        
        self.extracted_data["states"].append(state_data)
        self.current_state = state_data
        self.current_lga = None
        self.seen_states.add(key)
        
        logger.info(f"Found state: {name}")
    
    def _add_lga(self, name: str, code: str = ''):
        """Add an LGA to extracted data"""
        if not self.current_state:
            logger.warning(f"No current state for LGA {name}")
            return
        
        key = f"{self.current_state['name'].upper()}_{name.upper()}"
        
        if key in self.seen_lgas:
            # Update current LGA
            for lga in self.extracted_data["lgas"]:
                if lga['name'].upper() == name.upper() and lga['state'] == self.current_state['name']:
                    self.current_lga = lga
                    return
            return
        
        lga_data = {
            "name": name,
            "code": code or self._generate_code(name),
            "state": self.current_state["name"]
        }
        
        self.extracted_data["lgas"].append(lga_data)
        self.current_lga = lga_data
        self.seen_lgas.add(key)
        
        logger.info(f"Found LGA: {name} in {self.current_state['name']}")
    
    def _add_ward(self, name: str, code: str = ''):
        """Add a ward to extracted data"""
        if not self.current_lga or not self.current_state:
            logger.warning(f"No current LGA for Ward {name}")
            return
        
        key = f"{self.current_state['name'].upper()}_{self.current_lga['name'].upper()}_{name.upper()}"
        
        if key in self.seen_wards:
            return
        
        ward_data = {
            "name": name,
            "code": code or self._generate_code(name),
            "lga": self.current_lga["name"],
            "state": self.current_state["name"]
        }
        
        self.extracted_data["wards"].append(ward_data)
        self.seen_wards.add(key)
        
        logger.info(f"Found Ward: {name} in {self.current_lga['name']}")
    
    def _process_state_line(self, line: str):
        """Process state header line"""
        state_name = line.replace('STATE:', '').replace('State:', '').strip()
        self._add_state(state_name)
    
    def _generate_code(self, name: str) -> str:
        """Generate a code from a name"""
        code = ''.join(word[0].upper() for word in name.split() if word)
        return code if code else "XX"
    
    def export_to_json(self, output_path: str = "extracted_data.json"):
        """Export extracted data to JSON file"""
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(self.extracted_data, f, indent=2, ensure_ascii=False)
            logger.info(f"Data exported to {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"Error exporting to JSON: {str(e)}")
            raise
    
    def get_statistics(self) -> Dict:
        """Get extraction statistics"""
        return {
            "total_states": len(self.extracted_data["states"]),
            "total_lgas": len(self.extracted_data["lgas"]),
            "total_wards": len(self.extracted_data["wards"]),
            "extraction_time": datetime.utcnow().isoformat()
        }