# Xtractor - Nigerian LGA and Ward Data Extractor

A Python Flask application that extracts LGA (Local Government Area) names, codes, ward names, and ward codes from Nigerian Electoral PDF documents and stores them in a SQLite database.

## Features

- 📄 PDF extraction using pdfplumber
- 📊 SQLite database storage with SQLAlchemy ORM
- 🔍 Search functionality for States, LGAs, and Wards
- 📤 Upload and process PDF files
- 📥 Export extracted data as JSON
- 🎯 RESTful API endpoints
- 📝 Extraction logging and statistics

## Project Structure

```
xtractor/
├── app/
│   ├── __init__.py              # Flask app initialization
│   ├── models.py                # Database models (State, LGA, Ward, ExtractionLog)
│   ├── parser.py                # PDF extraction logic (PDFExtractor class)
│   ├── database.py              # Database operations (DatabaseManager class)
│   ├── extraction_service.py    # Extraction service wrapper
│   └── routes.py                # Flask routes and API endpoints
├── templates/
│   └── index.html               # Web interface
├── static/
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── main.js
├── logs/                        # Application logs
├── uploads/                     # Uploaded PDF files
├── extracted_data/              # Exported JSON files
├── data/                        # SQLite database
├── app.py                       # Application entry point
├── requirements.txt             # Python dependencies
├── .env                         # Environment variables
└── README.md                    # This file
```

## Installation

### Prerequisites

- Python 3.8+
- pip

### Setup Steps

1. **Clone or navigate to the project directory:**

   ```powershell
   cd c:\xampp\htdocs\xtractor
   ```

2. **Create a virtual environment:**

   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate
   ```

3. **Install dependencies:**

   ```powershell
   pip install -r requirements.txt
   ```

4. **Verify environment setup:**

   - Check that `.env` file exists in the root directory
   - Ensure `data/` and `uploads/` directories are created

5. **Run the application:**

   ```powershell
   python app.py
   ```

   The application will be available at `http://localhost:5000`

## Database Models

### State

```python
- id (Integer, Primary Key)
- state_name (String)
- state_code (String)
- created_at (DateTime)
- updated_at (DateTime)
- lgas (Relationship to LGA)
```

### LGA (Local Government Area)

```python
- id (Integer, Primary Key)
- lga_name (String)
- lga_code (String)
- state_id (Foreign Key)
- created_at (DateTime)
- updated_at (DateTime)
- state (Relationship to State)
- wards (Relationship to Ward)
```

### Ward

```python
- id (Integer, Primary Key)
- ward_name (String)
- ward_code (String)
- lga_id (Foreign Key)
- created_at (DateTime)
- updated_at (DateTime)
- lga (Relationship to LGA)
```

### ExtractionLog

```python
- id (Integer, Primary Key)
- filename (String)
- total_lgas_extracted (Integer)
- total_wards_extracted (Integer)
- status (String: pending, success, failed)
- error_message (String, optional)
- created_at (DateTime)
- completed_at (DateTime)
```

## API Endpoints

### 1. Upload PDF and Extract Data

**POST** `/api/upload`

Upload a PDF file for extraction.

**Request:**

- Content-Type: multipart/form-data
- Body: `file` (PDF file)

**Response:**

```json
{
  "status": "success",
  "message": "Extraction completed successfully",
  "data": {
    "success": true,
    "filename": "document.pdf",
    "stats": {
      "total_states": 5,
      "total_lgas": 25,
      "total_wards": 100,
      "extraction_time": "2025-11-08T10:30:45.123456"
    },
    "database_log_id": 1
  }
}
```

**Status Codes:**

- 200: Success
- 400: Bad request (no file, invalid file type, file too large)
- 500: Server error

### 2. Get All States

**GET** `/api/states`

Retrieve all states from the database.

**Response:**

```json
[
  {
    "id": 1,
    "name": "Lagos",
    "code": "LG",
    "lga_count": 20
  },
  {
    "id": 2,
    "name": "Abuja",
    "code": "AB",
    "lga_count": 6
  }
]
```

**Status Codes:**

- 200: Success
- 500: Server error

### 3. Get LGAs by State

**GET** `/api/states/<state_id>/lgas`

Retrieve all LGAs in a specific state.

**Parameters:**

- `state_id` (path): The ID of the state

**Response:**

```json
[
  {
    "id": 1,
    "name": "Ajeromi-Ifelodun",
    "code": "001",
    "ward_count": 10
  },
  {
    "id": 2,
    "name": "Alimosho",
    "code": "002",
    "ward_count": 12
  }
]
```

### 4. Get Wards by LGA

**GET** `/api/lgas/<lga_id>/wards`

Retrieve all wards in a specific LGA.

**Parameters:**

- `lga_id` (path): The ID of the LGA

**Response:**

```json
[
  {
    "id": 1,
    "name": "Ward 1",
    "code": "001"
  },
  {
    "id": 2,
    "name": "Ward 2",
    "code": "002"
  }
]
```

### 5. Get Extraction Status

**GET** `/api/status`

Retrieve extraction statistics and recent logs.

**Response:**

```json
{
  "stats": {
    "total_states": 36,
    "total_lgas": 774,
    "total_wards": 8809,
    "total_extractions": 5
  },
  "recent_logs": [
    {
      "id": 5,
      "filename": "electoral_data_2025.pdf",
      "status": "success",
      "lgas_extracted": 10,
      "wards_extracted": 50,
      "created_at": "2025-11-08T10:30:45.123456",
      "completed_at": "2025-11-08T10:35:20.654321",
      "error": null
    }
  ]
}
```

### 6. Search

**GET** `/api/search`

Search for states, LGAs, or wards.

**Parameters:**

- `q` (query string): Search query (minimum 2 characters)
- `type` (query string): Search type - 'all', 'state', 'lga', or 'ward' (default: 'all')

**Example:**

```
GET /api/search?q=lagos&type=state
GET /api/search?q=ajeromi&type=lga
GET /api/search?q=ward&type=all
```

**Response:**

```json
{
  "states": [
    {
      "id": 1,
      "name": "Lagos",
      "code": "LG"
    }
  ],
  "lgas": [
    {
      "id": 5,
      "name": "Lagos Island",
      "code": "LI",
      "state": "Lagos"
    }
  ],
  "wards": []
}
```

### 7. Export All Data

**GET** `/api/export`

Export all extracted data as JSON.

**Response:**

```json
{
  "export_time": "2025-11-08T10:40:00.123456",
  "states": [
    {
      "name": "Lagos",
      "code": "LG",
      "lgas": [
        {
          "name": "Ajeromi-Ifelodun",
          "code": "001",
          "wards": [
            {
              "name": "Ward 1",
              "code": "001"
            }
          ]
        }
      ]
    }
  ]
}
```

## PDF Extraction Process

The `PDFExtractor` class processes PDFs using the following logic:

1. **Page Processing**: Reads each page's text and tables
2. **Text Parsing**: Identifies and extracts:
   - State headers (all-caps text)
   - LGA lines (contains "LGA" or follows patterns)
   - Ward lines (starts with numbers or "Ward")
3. **Table Processing**: Parses structured table data
4. **Data Validation**: Prevents duplicate entries
5. **Hierarchical Organization**: Links Wards → LGAs → States

### Detection Patterns

**State Headers:**

- All uppercase with only letters
- Pattern: "STATE: NAME" or "State: NAME"

**LGA Lines:**

- Contains "LGA" prefix
- Pattern: "LGA NAME CODE"
- Pattern: "NAME CODE" (numbers at end)

**Ward Lines:**

- Starts with "Ward" or numbers
- Contains alphanumeric name and code

## Usage Examples

### Example 1: Extract and Upload a PDF

```python
import requests

with open('electoral_data.pdf', 'rb') as f:
    files = {'file': f}
    response = requests.post('http://localhost:5000/api/upload', files=files)
    print(response.json())
```

### Example 2: Search for a State

```python
import requests

response = requests.get('http://localhost:5000/api/search',
                       params={'q': 'Lagos', 'type': 'state'})
states = response.json()['states']
print(states)
```

### Example 3: Get All Wards in an LGA

```python
import requests

# First get the LGA ID
lga_response = requests.get('http://localhost:5000/api/states/1/lgas')
lgas = lga_response.json()
lga_id = lgas[0]['id']

# Then get wards
wards_response = requests.get(f'http://localhost:5000/api/lgas/{lga_id}/wards')
wards = wards_response.json()
print(wards)
```

## Configuration

### Environment Variables (.env)

```env
FLASK_ENV=development          # development or production
PORT=5000                      # Port to run Flask on
DATABASE_URL=sqlite:///./data/xtractor.db  # Database URL
```

### File Size Limits

- Maximum upload file size: 50MB (configurable in `routes.py`)

### Supported File Formats

- PDF (.pdf)

## Troubleshooting

### Issue: "No module named 'pdfplumber'"

**Solution:** Ensure all dependencies are installed: `pip install -r requirements.txt`

### Issue: Database file not found

**Solution:** The `data/` directory is created automatically. If it doesn't exist, create it manually.

### Issue: File upload fails

**Solution:**

- Check file size (max 50MB)
- Ensure file is a valid PDF
- Check `uploads/` folder permissions

### Issue: Extraction takes too long

**Solution:**

- Large PDFs may take time
- Monitor logs in `logs/` folder
- Check system resources

## Performance Tips

1. **Batch Processing**: Process multiple PDFs sequentially
2. **Database Indexing**: Already implemented on frequently searched fields
3. **Search Optimization**: Use specific search types ('state', 'lga', 'ward') instead of 'all'
4. **Export**: For large datasets, use `/api/export` endpoint

## Logging

Logs are written to the console and can be configured in `app.py`.

Log entries include:

- PDF extraction progress
- Database operations
- API request errors
- Extraction statistics

## Future Enhancements

- [ ] Add support for other PDF formats
- [ ] Implement batch processing UI
- [ ] Add data validation and correction tools
- [ ] Support for multiple PDF sources
- [ ] API authentication and rate limiting
- [ ] Advanced search with filters
- [ ] Data import/export in multiple formats (CSV, Excel)

## License

This project is licensed under the MIT License.

## Support

For issues or questions, please create an issue in the repository.
