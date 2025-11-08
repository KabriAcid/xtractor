import pdfplumber
import json
import re
import logging

logger = logging.getLogger(__name__)

# All 36 Nigerian states (alphabetically ordered)
NIGERIAN_STATES = [
    "ABIA", "ADAMAWA", "AKWA IBOM", "ANAMBRA", "BAUCHI", "BAYELSA",
    "BENUE", "BORNO", "CROSS RIVER", "DELTA", "EBONYI", "EDO",
    "EKITI", "ENUGU", "GOMBE", "IMO", "JIGAWA", "KADUNA",
    "KANO", "KATSINA", "KEBBI", "KOGI", "KWARA", "LAGOS",
    "NASARAWA", "NIGER", "OGUN", "ONDO", "OSUN", "OYO",
    "PLATEAU", "RIVERS", "SOKOTO", "TARABA", "YOBE", "ZAMFARA"
]

REGION_KEYWORDS = ["NORTH", "SOUTH", "EAST", "WEST", "CENTRAL"]
TABLE_HEADER_KEYWORDS = ["LGA NAME", "WARD NAME", "WARD CODE", "LGA CODE"]


class PDFExtractor:
    def __init__(self, pdf_path):
        self.pdf_path = pdf_path
        self.data = {
            "states": []
        }
        self.seen_states = set()
        self.seen_lgas = set()
        self.seen_wards = set()
        self.current_state = None
        self.current_lga = None

    def extract_all(self):
        """Main extraction pipeline"""
        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    logger.info(f"Processing page {page_num + 1}/{len(pdf.pages)}")
                    
                    # Try table extraction first
                    tables = page.extract_tables()
                    if tables:
                        self._extract_tables(page, tables)
                    
                    # Also extract text for state headers
                    text = page.extract_text()
                    if text:
                        self._extract_text(text)
            
            logger.info(f"Extraction complete: {len(self.data['states'])} states")
            return self.data
        except Exception as e:
            logger.error(f"Error extracting PDF: {str(e)}")
            raise

    def _extract_tables(self, page, tables):
        """Extract data from PDF tables"""
        for table in tables:
            for row in table:
                self._process_row(row)

    def _extract_text(self, text):
        """Extract state headers from text"""
        lines = text.split('\n')
        for line in lines:
            clean_line = line.strip().upper()
            if self._is_state_header(clean_line):
                self._add_state(clean_line)

    def _process_row(self, row):
        """Process a single table row"""
        if not row or all(cell is None or str(cell).strip() == '' for cell in row):
            return
        
        # Clean row data
        clean_row = [str(cell).strip() if cell else '' for cell in row]
        
        # Skip table headers
        if self._is_table_header(clean_row):
            return
        
        # Skip region rows
        if self._is_region_row(clean_row):
            return
        
        # Check if this looks like an LGA + Wards data row or Ward data
        self._detect_lga_ward_data(clean_row)

    def _is_state_header(self, text):
        """Check if text is a valid state name"""
        text_upper = text.upper().strip()
        return text_upper in NIGERIAN_STATES and not any(char.isdigit() for char in text)

    def _is_table_header(self, row):
        """Check if row contains table headers"""
        row_text = ' '.join(str(cell).upper() for cell in row)
        return any(keyword in row_text for keyword in TABLE_HEADER_KEYWORDS)

    def _is_region_row(self, row):
        """Check if row is a region identifier"""
        first_cell = str(row[0]).strip().upper()
        return any(keyword in first_cell for keyword in REGION_KEYWORDS)

    def _looks_like_code(self, text):
        """Check if text looks like a code (numeric, 1-5 digits)"""
        text = str(text).strip()
        return bool(re.match(r'^\d{1,5}$', text))

    def _detect_lga_ward_data(self, row):
        """Detect and parse LGA and Ward data from table rows"""
        # Remove completely empty cells
        row = [cell for cell in row if cell and str(cell).strip()]
        
        if len(row) < 2:
            return
        
        first_cell = str(row[0]).strip()
        second_cell = str(row[1]).strip() if len(row) > 1 else ""
        
        # Pattern 1: [LGA_NAME, LGA_CODE] - LGA data
        if len(row) >= 2 and self._looks_like_code(second_cell):
            lga_name = first_cell.upper()
            lga_code = second_cell
            
            # Check if current state is set
            if self.current_state:
                self._add_lga(lga_name, lga_code)
        
        # Pattern 2: [WARD_NAME, ..., WARD_CODE] - Ward data
        elif len(row) >= 2:
            # Look for codes in later positions
            for i in range(1, min(len(row), 6)):
                if self._looks_like_code(row[i]):
                    ward_name = first_cell.upper()
                    ward_code = row[i]
                    if self.current_state and self.current_lga:
                        self._add_ward(ward_name, ward_code)
                    break

    def _add_state(self, state_name):
        """Add state to data structure"""
        state_upper = state_name.upper().strip()
        
        if state_upper not in self.seen_states and state_upper in NIGERIAN_STATES:
            self.seen_states.add(state_upper)
            self.current_state = state_upper
            self.current_lga = None  # Reset LGA context
            
            self.data["states"].append({
                "name": state_upper,
                "lgas": []
            })
            logger.info(f"Added state: {state_upper}")

    def _add_lga(self, lga_name, lga_code):
        """Add LGA to current state"""
        if not self.current_state:
            return
        
        lga_key = f"{self.current_state}_{lga_name}_{lga_code}"
        
        if lga_key not in self.seen_lgas:
            self.seen_lgas.add(lga_key)
            self.current_lga = lga_name  # Update LGA context
            
            # Find current state in data
            for state in self.data["states"]:
                if state["name"] == self.current_state:
                    state["lgas"].append({
                        "name": lga_name,
                        "code": lga_code,
                        "wards": []
                    })
                    logger.debug(f"Added LGA: {lga_name} ({lga_code}) to {self.current_state}")
                    break

    def _add_ward(self, ward_name, ward_code):
        """Add ward to current LGA"""
        if not self.current_state or not self.current_lga:
            return
        
        ward_key = f"{self.current_state}_{self.current_lga}_{ward_name}_{ward_code}"
        
        if ward_key not in self.seen_wards:
            self.seen_wards.add(ward_key)
            
            # Find current state and LGA in data
            for state in self.data["states"]:
                if state["name"] == self.current_state:
                    for lga in state["lgas"]:
                        if lga["name"] == self.current_lga:
                            lga["wards"].append({
                                "name": ward_name,
                                "code": ward_code
                            })
                            logger.debug(f"Added Ward: {ward_name} ({ward_code})")
                            break
                    break

    def to_json(self):
        """Export extracted data as JSON string"""
        return json.dumps(self.data, indent=2, ensure_ascii=False)

    def save_json(self, output_path):
        """Save extracted data to JSON file"""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(self.to_json())
        logger.info(f"Data saved to {output_path}")

    def export_to_json(self, output_path):
        """Alias for save_json for compatibility"""
        self.save_json(output_path)

    def get_statistics(self):
        """Get extraction statistics"""
        total_lgas = sum(len(state.get("lgas", [])) for state in self.data["states"])
        total_wards = sum(
            len(ward) 
            for state in self.data["states"] 
            for lga in state.get("lgas", []) 
            for ward in lga.get("wards", [])
        )
        
        return {
            "total_states": len(self.data["states"]),
            "total_lgas": total_lgas,
            "total_wards": total_wards,
            "states": [state["name"] for state in self.data["states"]]
        }
