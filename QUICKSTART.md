# Xtractor - Quick Start Guide

## 🚀 5-Minute Setup

### Step 1: Install Dependencies (1 min)

```powershell
cd c:\xampp\htdocs\xtractor
pip install -r requirements.txt
```

### Step 2: Verify Installation (1 min)

```powershell
python test_setup.py
```

Expected output: `Total: 5/5 tests passed`

### Step 3: Start the Server (1 min)

```powershell
python app.py
```

You should see:

```
 * Running on http://127.0.0.1:5000
 * Press CTRL+C to quit
```

### Step 4: Access the Application (1 min)

Open your browser and navigate to:

```
http://localhost:5000
```

### Step 5: Test an API Endpoint (1 min)

#### Option A: Using PowerShell

```powershell
Invoke-WebRequest -Uri "http://localhost:5000/api/states" | ConvertFrom-Json
```

#### Option B: Using curl

```powershell
curl "http://localhost:5000/api/states"
```

Expected response: `[]` (empty array, no data yet)

---

## 📤 Upload Your First PDF

### Using cURL

```powershell
curl -X POST -F "file=@C:\path\to\your\pdf\file.pdf" http://localhost:5000/api/upload
```

### Using PowerShell

```powershell
$file = "C:\path\to\your\pdf\file.pdf"
$uri = "http://localhost:5000/api/upload"
$form = @{
    file = Get-Item -Path $file
}
Invoke-WebRequest -Uri $uri -Method Post -Form $form
```

---

## 📊 Test Data Operations

After uploading a PDF, test these endpoints:

### 1. Get All States

```powershell
curl "http://localhost:5000/api/states"
```

### 2. Get LGAs in a State (replace 1 with actual state ID)

```powershell
curl "http://localhost:5000/api/states/1/lgas"
```

### 3. Get Wards in an LGA (replace 1 with actual LGA ID)

```powershell
curl "http://localhost:5000/api/lgas/1/wards"
```

### 4. Search for Data

```powershell
curl "http://localhost:5000/api/search?q=lagos&type=state"
```

### 5. Get System Status

```powershell
curl "http://localhost:5000/api/status"
```

### 6. Export All Data

```powershell
curl "http://localhost:5000/api/export" | Out-File -FilePath exported_data.json
```

---

## 🗂️ Important Directories

| Directory         | Purpose                  |
| ----------------- | ------------------------ |
| `uploads/`        | Uploaded PDF files       |
| `extracted_data/` | Exported JSON files      |
| `data/`           | SQLite database          |
| `app/`            | Application source code  |
| `templates/`      | HTML templates           |
| `static/`         | CSS and JavaScript files |

---

## ⚙️ Configuration

### Change Server Port

Edit `.env`:

```env
PORT=8000  # instead of 5000
```

### Change Database Location

Edit `.env`:

```env
DATABASE_URL=sqlite:///./data/my_database.db
```

### Run in Production Mode

Edit `.env`:

```env
FLASK_ENV=production
```

---

## 🐛 Common Issues & Solutions

### Issue: "ModuleNotFoundError: No module named 'pdfplumber'"

```powershell
pip install pdfplumber==0.10.3
```

### Issue: Port 5000 already in use

```powershell
# Change PORT in .env to 8000, 8080, or any available port
```

### Issue: Permission denied on uploads folder

```powershell
icacls uploads /grant Everyone:F /T
```

### Issue: Database is locked

```powershell
# Delete the database and restart
Remove-Item -Path data\xtractor.db
python app.py
```

---

## 📝 Example Workflow

1. **Start the server**

   ```powershell
   python app.py
   ```

2. **Upload a PDF file**

   ```powershell
   curl -X POST -F "file=@electoral_data.pdf" http://localhost:5000/api/upload
   ```

3. **Check extraction status**

   ```powershell
   curl "http://localhost:5000/api/status"
   ```

4. **Search for specific data**

   ```powershell
   curl "http://localhost:5000/api/search?q=ajeromi&type=lga"
   ```

5. **Export all extracted data**
   ```powershell
   curl "http://localhost:5000/api/export" | Out-File export.json
   ```

---

## 🎯 What Each Component Does

- **PDFExtractor** - Reads PDF files and extracts text/tables
- **DatabaseManager** - Saves/retrieves data from SQLite
- **ExtractionService** - Orchestrates the extraction process
- **Routes** - Provides HTTP API endpoints
- **Models** - Defines database schema (State, LGA, Ward)

---

## 📚 File Reference

| File                        | Contains             |
| --------------------------- | -------------------- |
| `app/models.py`             | Database models      |
| `app/parser.py`             | PDF extraction logic |
| `app/database.py`           | Database operations  |
| `app/extraction_service.py` | Service layer        |
| `app/routes.py`             | API endpoints        |
| `app.py`                    | Server entry point   |
| `.env`                      | Configuration        |
| `requirements.txt`          | Dependencies         |

---

## 🔗 Useful Links

- Flask Documentation: https://flask.palletsprojects.com/
- SQLAlchemy ORM: https://docs.sqlalchemy.org/
- pdfplumber Documentation: https://github.com/jsvine/pdfplumber

---

## ⏸️ Stopping the Server

Press `CTRL+C` in the terminal where the server is running.

---

## ✅ Success Indicators

- ✓ Server starts without errors
- ✓ Can access http://localhost:5000
- ✓ API endpoints return responses
- ✓ Can upload PDF files
- ✓ Database creates entries after upload
- ✓ Can query extracted data

---

**Need Help?** Check the comprehensive `README.md` for detailed API documentation.
