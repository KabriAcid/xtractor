"""
PDF Extractor for Nigerian LGA and Ward data using LGA code-based state detection
"""
import pdfplumber
import json
import re
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)

# All 37 Nigerian states (36 states + FCT) in alphabetical order
NIGERIAN_STATES = [
    "ABIA", "ADAMAWA", "AKWA IBOM", "ANAMBRA", "BAUCHI", "BAYELSA",
    "BENUE", "BORNO", "CROSS RIVER", "DELTA", "EBONYI", "EDO",
    "EKITI", "ENUGU", "FCT", "GOMBE", "IMO", "JIGAWA",
    "KADUNA", "KANO", "KATSINA", "KEBBI", "KOGI", "KWARA",
    "LAGOS", "NASARAWA", "NIGER", "OGUN", "ONDO", "OSUN",
    "OYO", "PLATEAU", "RIVERS", "SOKOTO", "TARABA", "YOBE",
    "ZAMFARA"
]


class PDFExtractor:
    """Extract Nigerian LGA and Ward data from PDF using LGA code-based state detection"""

    def __init__(self, pdf_path):
        self.pdf_path = pdf_path
        self.data = {"states": []}
        self.state_index = 0
        self.current_state_name = NIGERIAN_STATES[0]
        self.current_lga = None
        self.previous_lga_code = None
        self.seen_lgas = set()
        self.seen_wards = set()

    def extract_all(self) -> Dict:
        """Main extraction pipeline - process all pages"""
        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                total_pages = len(pdf.pages)
                logger.info(f"Starting extraction from {total_pages} pages")

                for page_num, page in enumerate(pdf.pages):
                    logger.info(f"Processing page {page_num + 1}/{total_pages}")
                    tables = page.extract_tables()
                    if tables:
                        for table in tables:
                            self._process_table(table)

            logger.info(f"Extraction complete: {len(self.data['states'])} states")
            return self.data

        except Exception as e:
            logger.error(f"Error extracting PDF: {str(e)}")
            raise

    def _process_table(self, table: List[List]) -> None:
        """Process a single table from the PDF"""
        for row in table:
            self._process_row(row)

    def _process_row(self, row: List) -> None:
        """Process a single table row"""
        if not row or all(cell is None or str(cell).strip() == '' for cell in row):
            return

        # Clean row cells
        clean_row = [str(cell).strip() if cell else '' for cell in row]

        # Ensure we have at least 6 columns: [LGA_NAME, LGA_CODE, WARD_NAME, empty, empty, WARD_CODE]
        if len(clean_row) < 6:
            return

        lga_name = clean_row[0]
        lga_code = clean_row[1]
        ward_name = clean_row[2]
        ward_code = clean_row[5]

        # Skip if both LGA code and ward code are empty
        if not lga_code and not ward_code:
            return

        # Skip table headers
        if self._is_table_header(lga_name, lga_code):
            return

        # DETECT STATE CHANGE: LGA code reset to 01
        if lga_code and self._looks_like_code(lga_code):
            current_code = int(lga_code)

            if (self.previous_lga_code is not None and
                    current_code < int(self.previous_lga_code)):
                # LGA code reset detected - move to next state
                self.state_index += 1
                if self.state_index < len(NIGERIAN_STATES):
                    self.current_state_name = NIGERIAN_STATES[self.state_index]
                    logger.info(f"State change detected: Moving to {self.current_state_name}")
                    self.current_lga = None

            self.previous_lga_code = lga_code

        # PROCESS LGA: If LGA name is present, create new LGA entry
        if lga_name and lga_code and self._looks_like_code(lga_code):
            self._add_lga(lga_name, lga_code)

        # PROCESS WARD: If ward name and code are present
        if ward_name and ward_code and self._looks_like_code(ward_code):
            self._add_ward(ward_name, ward_code)

    def _is_table_header(self, lga_name: str, lga_code: str) -> bool:
        """Check if this row is a table header"""
        header_keywords = ["LGA NAME", "LGA CODE", "WARD NAME", "WARD CODE", "S/N"]
        text = f"{lga_name} {lga_code}".upper()
        return any(keyword in text for keyword in header_keywords)

    def _looks_like_code(self, text: str) -> bool:
        """Check if text looks like a numeric code (1-3 digits, typically 01-99)"""
        text = str(text).strip()
        return bool(re.match(r'^\d{1,3}$', text)) and len(text) <= 3

    def _add_lga(self, lga_name: str, lga_code: str) -> None:
        """Add LGA to current state"""
        if self.state_index >= len(NIGERIAN_STATES):
            return

        lga_name = lga_name.upper().strip()
        lga_code = lga_code.strip()

        lga_key = f"{self.current_state_name}_{lga_name}_{lga_code}"

        if lga_key not in self.seen_lgas:
            self.seen_lgas.add(lga_key)
            self.current_lga = lga_name

            # Find or create current state
            state_entry = None
            for state in self.data["states"]:
                if state["name"] == self.current_state_name:
                    state_entry = state
                    break

            # If state doesn't exist, create it
            if not state_entry:
                state_entry = {
                    "name": self.current_state_name,
                    "lgas": []
                }
                self.data["states"].append(state_entry)

            # Add LGA to state
            state_entry["lgas"].append({
                "name": lga_name,
                "code": lga_code,
                "wards": []
            })

            logger.debug(f"Added LGA: {lga_name} ({lga_code}) to {self.current_state_name}")

    def _add_ward(self, ward_name: str, ward_code: str) -> None:
        """Add ward to current LGA"""
        if not self.current_lga or self.state_index >= len(NIGERIAN_STATES):
            return

        ward_name = ward_name.upper().strip()
        ward_code = ward_code.strip()

        ward_key = f"{self.current_state_name}_{self.current_lga}_{ward_name}_{ward_code}"

        if ward_key not in self.seen_wards:
            self.seen_wards.add(ward_key)

            # Find current state and LGA
            for state in self.data["states"]:
                if state["name"] == self.current_state_name:
                    for lga in state["lgas"]:
                        if lga["name"] == self.current_lga:
                            lga["wards"].append({
                                "name": ward_name,
                                "code": ward_code
                            })
                            logger.debug(f"Added Ward: {ward_name} ({ward_code})")
                            return

    def to_json(self) -> str:
        """Export extracted data as JSON string"""
        return json.dumps(self.data, indent=2, ensure_ascii=False)

    def save_json(self, output_path: str) -> None:
        """Save extracted data to JSON file"""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(self.to_json())
        logger.info(f"Data saved to {output_path}")

    def export_to_json(self, output_path: str) -> None:
        """Alias for save_json for compatibility"""
        self.save_json(output_path)

    def get_statistics(self) -> Dict:
        """Get extraction statistics"""
        total_lgas = sum(len(state.get("lgas", [])) for state in self.data["states"])
        total_wards = sum(
            len(ward)
            for state in self.data["states"]
            for lga in state.get("lgas", [])
            for ward in lga.get("wards", [])
        )

        return {
            "total_states": len([s for s in self.data["states"] if s.get("lgas")]),
            "total_lgas": total_lgas,
            "total_wards": total_wards,
            "states": [state["name"] for state in self.data["states"] if state.get("lgas")]
        }
