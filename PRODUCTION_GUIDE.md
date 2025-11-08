# Production Deployment Guide

## 🚀 Deploying Xtractor to Production

### Pre-Deployment Checklist

- [ ] All tests passing (`python test_setup.py`)
- [ ] Requirements.txt up to date
- [ ] .env file configured for production
- [ ] Database backup created
- [ ] Static files collected
- [ ] Error logging configured
- [ ] CORS configured (if needed)
- [ ] Security headers set

---

## 📋 Production Configuration

### 1. Update .env for Production

```env
FLASK_ENV=production
PORT=80
DATABASE_URL=sqlite:///./data/xtractor.db
SECRET_KEY=your_secure_random_key_here
```

Generate a secure key:

```python
import secrets
print(secrets.token_hex(32))
```

### 2. Update app.py for Production

```python
if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=int(os.getenv('PORT', 5000)),
        debug=False,  # NEVER True in production
        threaded=True
    )
```

### 3. Production Dependencies

Consider adding to requirements.txt:

```txt
gunicorn==21.2.0          # Production WSGI server
python-dotenv==1.0.0      # Environment variables
prometheus-flask==0.22.0  # Monitoring
Flask-Cors==4.0.0         # CORS support
```

---

## 🔒 Security Hardening

### 1. Add Security Headers

Update `app/routes.py`:

```python
@app.after_request
def set_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response
```

### 2. Input Validation

```python
from werkzeug.utils import secure_filename

def validate_filename(filename):
    """Validate and secure filename"""
    filename = secure_filename(filename)
    if not filename or len(filename) > 100:
        raise ValueError("Invalid filename")
    return filename
```

### 3. Rate Limiting

```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

@bp.route('/api/upload', methods=['POST'])
@limiter.limit("10 per hour")
def upload_pdf():
    # ...
```

---

## 🚀 Deployment Options

### Option 1: Gunicorn + Nginx

#### Install Gunicorn

```bash
pip install gunicorn
```

#### Create gunicorn_config.py

```python
bind = "127.0.0.1:5000"
workers = 4
worker_class = "sync"
timeout = 120
keepalive = 2
```

#### Start with Gunicorn

```bash
gunicorn --config gunicorn_config.py app:app
```

#### Nginx Configuration

```nginx
upstream xtractor {
    server 127.0.0.1:5000;
}

server {
    listen 80;
    server_name your_domain.com;

    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name your_domain.com;

    # SSL configuration
    ssl_certificate /etc/ssl/certs/your_cert.crt;
    ssl_certificate_key /etc/ssl/private/your_key.key;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000" always;
    add_header X-Content-Type-Options "nosniff" always;

    # Proxy settings
    location / {
        proxy_pass http://xtractor;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # File upload handling
    client_max_body_size 50M;
}
```

---

### Option 2: Docker Deployment

#### Create Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create necessary directories
RUN mkdir -p uploads extracted_data data logs

# Expose port
EXPOSE 5000

# Run application
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
```

#### Create docker-compose.yml

```yaml
version: "3.8"

services:
  xtractor:
    build: .
    ports:
      - "5000:5000"
    volumes:
      - ./uploads:/app/uploads
      - ./extracted_data:/app/extracted_data
      - ./data:/app/data
    environment:
      - FLASK_ENV=production
      - DATABASE_URL=sqlite:///./data/xtractor.db
    restart: unless-stopped

  nginx:
    image: nginx:latest
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - xtractor
    restart: unless-stopped
```

#### Build and Run

```bash
docker-compose up -d
```

---

### Option 3: Cloud Platforms

#### Heroku Deployment

Create `Procfile`:

```
web: gunicorn app:app
```

Deploy:

```bash
heroku login
heroku create xtractor-app
git push heroku main
```

#### AWS Elastic Beanstalk

```bash
pip install awsebcli

eb init -p python-3.11 xtractor-app
eb create xtractor-env
eb deploy
```

---

## 📊 Monitoring and Logging

### 1. Application Logging

```python
import logging
from logging.handlers import RotatingFileHandler

if not app.debug:
    if not os.path.exists('logs'):
        os.mkdir('logs')

    file_handler = RotatingFileHandler('logs/xtractor.log',
                                       maxBytes=10240000,
                                       backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
```

### 2. Error Tracking (Sentry)

```python
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration

sentry_sdk.init(
    dsn="your_sentry_dsn",
    integrations=[FlaskIntegration()]
)
```

### 3. Performance Monitoring

```python
from flask_talisman import Talisman

Talisman(app)  # Security headers
```

---

## 🗄️ Database Management

### Backup Strategy

```bash
# Automated daily backup
0 2 * * * sqlite3 /path/to/data/xtractor.db ".backup '/backups/xtractor_$(date +\%Y\%m\%d).db'"
```

### Migration Management

```bash
# If using Alembic for migrations
alembic upgrade head
```

---

## ⚡ Performance Optimization

### 1. Database Indexing

Already implemented in models.py, but verify:

```python
state_name = Column(String(100), index=True)
lga_code = Column(String(20), index=True)
```

### 2. Query Optimization

Use eager loading for related objects:

```python
from sqlalchemy.orm import joinedload

states = db.query(State).options(joinedload(State.lgas)).all()
```

### 3. Caching

```python
from flask_caching import Cache

cache = Cache(app, config={'CACHE_TYPE': 'simple'})

@bp.route('/api/states')
@cache.cached(timeout=300)
def get_states():
    # ...
```

---

## 📈 Scaling Strategies

### 1. Database Optimization

- Use PostgreSQL instead of SQLite for production
- Add read replicas
- Implement connection pooling

### 2. Application Scaling

- Run multiple Gunicorn workers
- Use load balancer (Nginx, HAProxy)
- Implement message queue (Celery)

### 3. Caching Layer

- Add Redis for session storage
- Cache API responses
- Cache database queries

### Example Production Setup

```
Load Balancer (HAProxy)
    ├── Gunicorn Worker 1
    ├── Gunicorn Worker 2
    ├── Gunicorn Worker 3
    └── Gunicorn Worker 4
         ↓
    PostgreSQL Database
    Redis Cache
```

---

## 🔄 Continuous Deployment

### GitHub Actions Example

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v2

      - name: Install dependencies
        run: |
          pip install -r requirements.txt

      - name: Run tests
        run: python test_setup.py

      - name: Deploy to server
        run: |
          ssh user@server 'cd /app && git pull && systemctl restart xtractor'
```

---

## 🚨 Disaster Recovery

### 1. Regular Backups

```bash
# Weekly backup script
#!/bin/bash
BACKUP_DIR="/backups/xtractor"
mkdir -p $BACKUP_DIR
sqlite3 /app/data/xtractor.db ".backup '$BACKUP_DIR/xtractor_$(date +%Y%m%d_%H%M%S).db'"
# Keep only last 30 days
find $BACKUP_DIR -name "*.db" -mtime +30 -delete
```

### 2. Restore Database

```bash
# Restore from backup
sqlite3 /app/data/xtractor.db ".restore '/backups/xtractor/xtractor_20251108_000000.db'"
```

### 3. Health Checks

```python
@bp.route('/health')
def health_check():
    try:
        db = get_db_session()
        db.query(State).first()
        db.close()
        return jsonify({"status": "healthy"}), 200
    except Exception as e:
        return jsonify({"status": "unhealthy", "error": str(e)}), 500
```

---

## ✅ Post-Deployment Verification

- [ ] Application accessible from public domain
- [ ] SSL certificate valid
- [ ] File uploads working
- [ ] Database queries returning correct data
- [ ] API endpoints responsive
- [ ] Error logging configured
- [ ] Backup system active
- [ ] Monitoring dashboard setup
- [ ] Performance acceptable (<200ms response time)

---

## 📞 Support and Maintenance

### Regular Tasks

- Weekly: Review logs for errors
- Monthly: Database optimization
- Quarterly: Security updates
- Annually: Full system audit

### Maintenance Window

Schedule maintenance at low-traffic times (e.g., Sunday 2-4 AM)

---

**Last Updated**: November 2025  
**Version**: 1.0.0 Production Ready
