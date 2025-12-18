# Encrypted and Compressed Key-Value Store with Pattern Analysis (Cloud-Ready)

Secure key-value store with encryption, compression, authentication, a modern web UI, and real-time pattern analysis (daily), built with FastAPI. Supports local SQLite (default) or Redis (cloud) backends. Containerized with Docker and Compose.

## Features

- **Secure storage**: AES-Fernet with PBKDF2-derived key
- **Compression**: LZ4 compression algorithm
- **Authentication**: Register/Login/Logout with session tokens; role support
- **Modern Web UI**: Store/Retrieve/Delete, Keys list, Analytics, Settings
- **Real-time analytics**: Operation distribution, daily usage (dates), recent access history with date/time, top keys, performance stats
- **Cloud-ready**: Pluggable backends; Dockerfile and docker-compose included

## Project Structure (key files)

- `main.py` – FastAPI app, routes, auth, static routes (`/` login, `/app` UI)
- `kv_store.py` – SQLite key-value store implementation
- `redis_store.py` – Redis-backed store (when `KV_BACKEND=redis`)
- `encryption.py` – Encryption/decryption helpers
- `compression.py` – Compression helpers
- `pattern_analysis.py` – SQLite analytics (daily, recent history)
- `redis_pattern_analysis.py` – Redis analytics (cloud mode)
- `user_auth.py` – User DB, register/login/session management
- `static/index.html`, `static/style.css`, `static/script.js` – Web UI
- `Dockerfile`, `docker-compose.yml`, `requirements.txt`
- Databases at runtime: `kv_store.db`, `pattern_analysis.db`, `users.db`

Removed unused: old DB backups, sample data, `__pycache__`, and the unused `.venv` (you can recreate if needed).

## Installation & Setup

### Prerequisites
- Python 3.11+ (Python 3.13 may have compatibility issues with some packages)
- Docker Desktop (optional, for Redis)
- Windows PowerShell or Command Prompt

### Step-by-Step Setup (Windows)

#### Option 1: SQLite Backend (Default - No Docker Required)

1. **Create virtual environment** (recommended):
```powershell
cd C:\Users\chira\Desktop\maj_proj
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. **Install dependencies**:
```powershell
pip install -r requirements.txt
```

3. **Run the application**:
```powershell
python main.py
```

4. **Access the application**:
- Web UI: `http://localhost:8000` (login) → redirects to `/app` after login
- API docs: `http://localhost:8000/docs`

#### Option 2: Redis Backend (Cloud-Ready)

1. **Start Redis using Docker**:
```powershell
docker run -d --name kv-redis -p 6379:6379 redis:7
docker exec -it kv-redis redis-cli PING   # Should return PONG
```

2. **Set environment variables** (in the SAME PowerShell window):
```powershell
$env:KV_BACKEND="redis"
$env:REDIS_URL="redis://localhost:6379/0"
```

3. **Install dependencies** (if not done already):
```powershell
cd C:\Users\chira\Desktop\maj_proj
.\.venv\Scripts\Activate.ps1
pip install fastapi==0.104.1 uvicorn==0.24.0 cryptography==41.0.7 lz4==4.3.2 python-multipart==0.0.6 pydantic==2.5.0 redis==5.0.1
```

4. **Run the application**:
```powershell
python main.py
```

### Default Admin Credentials (First Run)
- Username: `admin`
- Password: `admin123` (change in production!)

## Authentication Endpoints

- `POST /register` – Create user: `{ username, email, password }`
- `POST /login` – Returns `{ session_token, user }`
- `POST /logout` – Invalidate session
- `GET /me` – Current user info (requires `Authorization: Bearer <token>`)
- `GET /users` – List users (admin/manager only)

All data/store endpoints require the `Authorization` header.

## Data Endpoints (Protected)

- `POST /store` – Body: `{ key, value, encrypt, compress }` → returns size and `duration_ms`
- `GET /retrieve/{key}` – Returns value plus size and `duration_ms`
- `DELETE /delete/{key}` – Delete a key
- `GET /keys` – List keys

## Analytics

- `GET /analysis` – Returns:
  - `operation_distribution` (read/write/delete counts)
  - `daily_access_patterns` (YYYY-MM-DD)
  - `recent_access_history` (per access date and time, size, response time)
  - `top_accessed_keys` (includes last-access date/time)
  - `response_time_stats` (avg/min/max)

- `GET /stats` – Store stats: total keys/size, encrypted/compressed counts, top keys

## Web UI

- Login at `/` (Register and Login supported)
- App at `/app` with tabs: Operations, Keys, Analytics, Settings
- Quick actions include navigation to Store/Retrieve/Delete and Pattern Analysis
- Pattern Analysis view shows daily (by date), recent access history (date/time), and performance metrics

## Configuration

### Environment Variables

- `KV_BACKEND`: `sqlite` (default) or `redis`
- `REDIS_URL`: Redis connection URL (e.g., `redis://:password@host:6379/0`)
- `KV_STORE_PASSWORD`: Encryption password (default: `default_password_change_me`)

### Setting Environment Variables (PowerShell)

**For current session only**:
```powershell
$env:KV_BACKEND="redis"
$env:REDIS_URL="redis://localhost:6379/0"
python main.py
```

**For permanent (all future sessions)**:
```powershell
setx KV_BACKEND "redis"
setx REDIS_URL "redis://localhost:6379/0"
# Then restart PowerShell
```

### Using Redis Cloud (No Docker Required)

If you have a Redis Cloud account:
```powershell
$env:KV_BACKEND="redis"
$env:REDIS_URL="redis://:your_password@your_host:6379/0"
python main.py
```

## Docker

Build and run (SQLite backend):
```bash
docker build -t kv-store:latest .
docker run -p 8000:8000 --name kv-api kv-store:latest
```

### Docker Compose (API + Redis)
```bash
docker compose up -d
```
Sets `KV_BACKEND=redis` and links the API to `redis` service.

## Viewing Stored Data

### Via Web UI (Recommended)
- **Retrieve Data**: Go to `http://localhost:8000/app` → Operations tab → Enter key → Click Retrieve
- **List All Keys**: Keys tab shows all stored keys
- **Statistics**: Analytics tab shows store stats and pattern analysis

### Via API Endpoints
```powershell
# List all keys
curl http://localhost:8000/keys

# Retrieve a specific key
curl http://localhost:8000/retrieve/test

# Get store statistics
curl http://localhost:8000/stats

# Get pattern analysis
curl http://localhost:8000/analysis
```

### Viewing Data in Redis (Docker)

If using Redis backend, you can inspect data directly in the Redis container:

**From Windows PowerShell**:
```powershell
# List all data keys
docker exec -it kv-redis redis-cli KEYS "kv:data:*"

# List all metadata keys
docker exec -it kv-redis redis-cli KEYS "kv:meta:*"

# View metadata for a specific key (shows encrypted/compressed flags, size, etc.)
docker exec -it kv-redis redis-cli HGETALL "kv:meta:test"

# View raw data value (will be encrypted if encryption was enabled)
docker exec -it kv-redis redis-cli --raw GET "kv:data:test"

# View pattern analysis data
docker exec -it kv-redis redis-cli HGETALL "kv:pa:stats"
docker exec -it kv-redis redis-cli HGETALL "kv:pa:ops"
docker exec -it kv-redis redis-cli ZREVRANGE "kv:pa:top" 0 9 WITHSCORES
```

**From inside Docker container** (if you opened Exec in Docker Desktop):
```bash
redis-cli KEYS "kv:data:*"
redis-cli HGETALL "kv:meta:test"
redis-cli --raw GET "kv:data:test"
```

**Note**: If data was stored with encryption, the raw value in Redis will be encrypted (Fernet token). Use the app's Retrieve endpoint to see the decrypted value.

### Viewing Data in SQLite

If using SQLite backend (default), data is stored in:

**Data Files**: `data\<key>.dat` (binary files, encrypted if encryption enabled)

**Metadata Database**: `kv_store.db` (SQLite database)

**View metadata using SQLite**:
```powershell
# Using sqlite3 (if installed)
sqlite3 kv_store.db "SELECT key, file_path, encrypted, compressed, size_bytes, updated_at FROM kv_metadata ORDER BY updated_at DESC LIMIT 20;"

# Or use DB Browser for SQLite (GUI tool)
# Download from: https://sqlitebrowser.org/
# Open kv_store.db → Browse Data → kv_metadata table
```

**View raw data file** (only readable if NOT encrypted/compressed):
```powershell
type .\data\<your-key>.dat
```

**Note**: If encryption/compression was enabled, the `.dat` file will be binary. Use the app's Retrieve endpoint to see the actual value.

## Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'fastapi'"
**Solution**: Activate virtual environment and install dependencies:
```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Issue: "Error 10061 connecting to localhost:6379" (Redis connection refused)
**Solution**: Start Redis container:
```powershell
docker start kv-redis
# Or if container doesn't exist:
docker run -d --name kv-redis -p 6379:6379 redis:7
```

### Issue: Data not showing in Redis
**Check**:
1. Verify environment variables are set in the SAME PowerShell window:
```powershell
echo $env:KV_BACKEND
echo $env:REDIS_URL
```
2. Restart the app after setting environment variables
3. Verify Redis is running: `docker exec -it kv-redis redis-cli PING` (should return PONG)

### Issue: "docker: not found" when running redis-cli commands
**Solution**: You're inside the container. Use `redis-cli` directly (without `docker exec`):
```bash
redis-cli KEYS "kv:data:*"
```

### Issue: Can't see actual data value in Redis (shows encrypted token)
**Solution**: This is expected if encryption is enabled. Use the app's Retrieve endpoint or Web UI to see decrypted values. To store plaintext, uncheck "Encrypt" when storing.

### Issue: Python 3.13 compatibility errors
**Solution**: Use Python 3.11:
```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Issue: Virtual environment activation fails
**Solution**: 
```powershell
Set-ExecutionPolicy -Scope Process RemoteSigned
.\.venv\Scripts\Activate.ps1
```

## Security Notes

- Change default admin password immediately
- Use strong `KV_STORE_PASSWORD`
- When using Redis, prefer `rediss://` (TLS) and secure networking
- Lock down CORS and headers for production
- Never commit `.env` files or database files to version control

## Quick Reference

### Common Commands

**Start Redis (Docker)**:
```powershell
docker run -d --name kv-redis -p 6379:6379 redis:7
docker exec -it kv-redis redis-cli PING
```

**Run App with Redis**:
```powershell
$env:KV_BACKEND="redis"
$env:REDIS_URL="redis://localhost:6379/0"
python main.py
```

**View Data in Redis**:
```powershell
docker exec -it kv-redis redis-cli KEYS "kv:data:*"
docker exec -it kv-redis redis-cli HGETALL "kv:meta:test"
docker exec -it kv-redis redis-cli --raw GET "kv:data:test"
```

**Stop/Start Redis**:
```powershell
docker stop kv-redis
docker start kv-redis
```

**View App Logs**:
- Check the PowerShell window where you ran `python main.py`
- Or check Docker logs: `docker logs kv-redis`

### API Quick Examples

**Store data** (with authentication token):
```powershell
curl -X POST http://localhost:8000/store `
  -H "Content-Type: application/json" `
  -H "Authorization: Bearer YOUR_TOKEN" `
  -d '{"key":"test","value":"password@123","encrypt":true,"compress":true}'
```

**Retrieve data**:
```powershell
curl http://localhost:8000/retrieve/test `
  -H "Authorization: Bearer YOUR_TOKEN"
```

**List all keys**:
```powershell
curl http://localhost:8000/keys `
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Notes

- Times in analytics are shown in your local timezone
- Real-time metrics (size, duration_ms) are returned by `/store` and `/retrieve`
- Data stored with encryption will appear as encrypted tokens in Redis/SQLite - this is expected behavior
- If Redis container is stopped, the app will fall back to SQLite backend (if `KV_BACKEND` is not set)
- Recently, unused artifacts were cleaned; only files used by the app remain
- Virtual environment is recommended but not strictly necessary (can install packages globally)
