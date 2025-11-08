import pdfplumber
import json
import re
from typing import List, Dict, Tuple, Optional
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PDFExtractor:
    """Extract LGA and Ward information from Nigerian Electoral PDFs"""
    
    def __init__(self, pdf_path: str):
        """
        Initialize PDF extractor
        
        Args:
            pdf_path: Path to the PDF file
        """
        self.pdf_path = pdf_path
        self.extracted_data = {
            "states": [],
            "lgas": [],
            "wards": []
        }
        self.current_state = None
        self.current_lga = None
        
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
        """Process a single page from the PDF"""
        text = page.extract_text()
        tables = page.extract_tables()
        
        if text:
            self._extract_text_data(text)
        
        if tables:
            for table in tables:
                self._extract_table_data(table)
    
    def _extract_text_data(self, text: str):
        """Extract data from plain text"""
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            
            if not line:
                continue
            
            # Try to detect state headers (usually in caps)
            if self._is_state_header(line):
                self._process_state_line(line)
            
            # Try to detect LGA lines
            elif self._is_lga_line(line):
                self._process_lga_line(line)
            
            # Try to detect Ward lines
            elif self._is_ward_line(line):
                self._process_ward_line(line)
    
    def _extract_table_data(self, table: List[List]):
        """Extract data from PDF tables"""
        for row in table:
            if not row or all(cell is None or cell == '' for cell in row):
                continue
            
            # Convert row to strings and clean
            clean_row = [str(cell).strip() if cell else '' for cell in row]
            
            # Try to parse as LGA/Ward row
            self._parse_table_row(clean_row)
    
    def _is_state_header(self, line: str) -> bool:
        """Check if line is a state header"""
        # State headers typically:
        # - Are in all caps
        # - Are relatively short (< 50 chars)
        # - Don't contain numbers
        if len(line) > 50 or len(line) < 3:
            return False
        
        if line.isupper() and line.isalpha():
            return True
        
        # Also check for patterns like "STATE: NAME"
        if line.startswith(('STATE:', 'State:', 'STATE ')):
            return True
        
        return False
    
    def _is_lga_line(self, line: str) -> bool:
        """Check if line is an LGA line"""
        # LGA lines typically contain:
        # - LGA name and code
        # - Pattern: "LGA NAME    CODE" or similar
        if 'LGA' in line.upper() and len(line) > 5:
            return True
        
        # Look for pattern with numbers that could be codes
        if re.search(r'^[A-Z\s]+\s+\d+', line):
            return True
        
        return False
    
    def _is_ward_line(self, line: str) -> bool:
        """Check if line is a ward line"""
        # Ward lines typically:
        # - Start with number or "Ward"
        # - Contain ward name and code
        if line.startswith(('Ward', 'WARD', '1', '2', '3', '4', '5', '6', '7', '8', '9', '0')):
            # Should have some text and possibly a number code
            if len(line) > 5 and any(c.isalpha() for c in line):
                return True
        
        return False
    
    def _process_state_line(self, line: str):
        """Process and store state information"""
        state_name = line.replace('STATE:', '').replace('State:', '').strip()
        state_code = self._generate_code(state_name)
        
        state_data = {
            "name": state_name,
            "code": state_code
        }
        
        # Check if state already exists
        if not any(s["name"].upper() == state_name.upper() for s in self.extracted_data["states"]):
            self.extracted_data["states"].append(state_data)
            self.current_state = state_data
            logger.info(f"Found state: {state_name}")
    
    def _process_lga_line(self, line: str):
        """Process and store LGA information"""
        if not self.current_state:
            return
        
        # Try to extract LGA name and code
        lga_name, lga_code = self._parse_lga_line(line)
        
        if lga_name:
            lga_data = {
                "name": lga_name,
                "code": lga_code,
                "state": self.current_state["name"]
            }
            
            # Check if LGA already exists
            if not any(lg["name"].upper() == lga_name.upper() and lg["state"] == self.current_state["name"] 
                      for lg in self.extracted_data["lgas"]):
                self.extracted_data["lgas"].append(lga_data)
                self.current_lga = lga_data
                logger.info(f"Found LGA: {lga_name} in {self.current_state['name']}")
    
    def _process_ward_line(self, line: str):
        """Process and store Ward information"""
        if not self.current_lga:
            return
        
        # Try to extract ward name and code
        ward_name, ward_code = self._parse_ward_line(line)
        
        if ward_name:
            ward_data = {
                "name": ward_name,
                "code": ward_code,
                "lga": self.current_lga["name"],
                "state": self.current_state["name"]
            }
            
            # Check if ward already exists
            if not any(w["name"].upper() == ward_name.upper() and w["lga"] == self.current_lga["name"] 
                      for w in self.extracted_data["wards"]):
                self.extracted_data["wards"].append(ward_data)
                logger.info(f"Found Ward: {ward_name} in {self.current_lga['name']}")
    
    def _parse_table_row(self, row: List[str]):
        """Parse a row from a PDF table"""
        if len(row) < 2:
            return
        
        # Common table structures:
        # [Code, Name] or [Name, Code] or [State, LGA, Ward, Code]
        
        # Try to identify the structure
        has_numbers = any(any(c.isdigit() for c in cell) for cell in row)
        
        if len(row) >= 2 and has_numbers:
            # Likely contains data
            first_cell = row[0].strip()
            second_cell = row[1].strip() if len(row) > 1 else ""
            
            # If first cell is mostly numbers and second has text, it's [Code, Name]
            if first_cell.replace(' ', '').isdigit() and second_cell and any(c.isalpha() for c in second_cell):
                # This could be an LGA or Ward
                if not self.current_lga:
                    self._process_lga_line(f"{second_cell} {first_cell}")
                else:
                    self._process_ward_line(f"{second_cell} {first_cell}")
            # If first cell has text and second has numbers, it's [Name, Code]
            elif any(c.isalpha() for c in first_cell) and second_cell.replace(' ', '').isdigit():
                if not self.current_lga:
                    self._process_lga_line(f"{first_cell} {second_cell}")
                else:
                    self._process_ward_line(f"{first_cell} {second_cell}")
    
    def _parse_lga_line(self, line: str) -> Tuple[Optional[str], str]:
        """
        Parse LGA name and code from a line
        
        Returns:
            Tuple of (lga_name, lga_code)
        """
        # Remove common prefixes
        line = re.sub(r'^(LGA|Lga|lga)\s*[-:]?\s*', '', line)
        
        # Try to extract code (usually at the end, numeric)
        match = re.search(r'\s+(\d+)\s*$', line)
        if match:
            code = match.group(1)
            name = line[:match.start()].strip()
            return name, code
        
        # If no code found, generate one
        return line.strip(), self._generate_code(line)
    
    def _parse_ward_line(self, line: str) -> Tuple[Optional[str], str]:
        """
        Parse Ward name and code from a line
        
        Returns:
            Tuple of (ward_name, ward_code)
        """
        # Remove common prefixes
        line = re.sub(r'^(Ward|WARD|ward)\s*[-:]?\s*', '', line)
        
        # Try to extract code
        match = re.search(r'\s+(\d+)\s*$', line)
        if match:
            code = match.group(1)
            name = line[:match.start()].strip()
            return name, code
        
        return line.strip(), self._generate_code(line)
    
    def _generate_code(self, name: str) -> str:
        """Generate a code from a name (fallback method)"""
        # Create code from first letters + length
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
