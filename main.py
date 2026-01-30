from fastapi import FastAPI, HTTPException, Depends, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import uvicorn
from datetime import datetime
import json
import webbrowser
import threading
import time
import os

from kv_store import KeyValueStore
from redis_store import RedisKeyValueStore
from encryption import EncryptionManager
from compression import CompressionManager
from pattern_analysis import PatternAnalyzer
from redis_pattern_analysis import RedisPatternAnalyzer
from user_auth import UserAuth

app = FastAPI(
    title="Encrypted Key-Value Store with Pattern Analysis",
    description="A secure, compressed key-value database with advanced pattern analysis",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Initialize components
# Choose backend via env: KV_BACKEND in {"sqlite", "redis"}
backend = os.environ.get("KV_BACKEND", "sqlite").lower()
if backend == "redis":
    kv_store = RedisKeyValueStore(os.environ.get("REDIS_URL"))
else:
    kv_store = KeyValueStore()
encryption_manager = EncryptionManager()
compression_manager = CompressionManager()
if backend == "redis":
    pattern_analyzer = RedisPatternAnalyzer(os.environ.get("REDIS_URL"))
else:
    pattern_analyzer = PatternAnalyzer()

# Initialize user authentication
user_auth = UserAuth()
security = HTTPBearer(auto_error=False)

# Pydantic models
class KeyValueRequest(BaseModel):
    key: str
    value: Any
    encrypt: bool = True
    compress: bool = True

class KeyValueResponse(BaseModel):
    key: str
    value: Any
    timestamp: datetime
    encrypted: bool
    compressed: bool
    size_bytes: int
    duration_ms: float | None = None

class PatternAnalysisResponse(BaseModel):
    total_keys: int
    access_patterns: Dict[str, Any]
    compression_stats: Dict[str, Any]
    encryption_stats: Dict[str, Any]
    recommendations: List[str]

class LoginRequest(BaseModel):
    username: str
    password: str

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str

class AuthResponse(BaseModel):
    success: bool
    message: str
    session_token: Optional[str] = None
    user: Optional[Dict[str, Any]] = None

# Authentication dependency
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = user_auth.verify_session(credentials.credentials)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user

# Optional authentication (for routes that work with or without auth)
async def get_current_user_optional(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Optional[Dict[str, Any]]:
    if not credentials:
        return None
    
    return user_auth.verify_session(credentials.credentials)


@app.get("/")
async def root():
    """Serve login page at root URL"""
    return FileResponse("static/login.html")

@app.get("/app")
async def app_page():
    """Serve main app page - requires authentication"""
    return FileResponse("static/index.html")

@app.get("/api")
async def api_info():
    return {"message": "Encrypted Key-Value Store API", "version": "1.0.0"}

# Authentication endpoints
@app.post("/register", response_model=AuthResponse)
async def register(request: RegisterRequest):
    """Register a new user"""
    result = user_auth.register_user(request.username, request.email, request.password)
    return AuthResponse(**result)

@app.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest):
    """Login user and create session"""
    result = user_auth.login_user(request.username, request.password)
    return AuthResponse(**result)

@app.post("/logout")
async def logout(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Logout user and invalidate session"""
    # Note: In a real implementation, you'd need to pass the session token
    # For now, we'll just return success
    return {"success": True, "message": "Logged out successfully"}

@app.get("/me")
async def get_current_user_info(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Get current user information"""
    return {"user": current_user}

@app.get("/users")
async def get_all_users(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Get all users (admin only)"""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    users = user_auth.get_all_users()
    return {"users": users}


@app.post("/store", response_model=KeyValueResponse)
async def store_value(request: KeyValueRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    """Store a key-value pair with optional encryption and compression"""
    try:
        start = time.perf_counter()
        # Store the value
        result = kv_store.store(
            key=request.key,
            value=request.value,
            encrypt=request.encrypt,
            compress=request.compress,
            encryption_manager=encryption_manager,
            compression_manager=compression_manager
        )
        duration_ms = (time.perf_counter() - start) * 1000.0
        result["duration_ms"] = duration_ms
        
        # Record access pattern
        pattern_analyzer.record_access(
            request.key,
            "write",
            response_time_ms=duration_ms,
            data_size=result.get("size_bytes", 0),
        )
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/retrieve/{key}", response_model=KeyValueResponse)
async def retrieve_value(key: str, current_user: Dict[str, Any] = Depends(get_current_user)):
    """Retrieve a value by key"""
    try:
        start = time.perf_counter()
        result = kv_store.retrieve(
            key=key,
            encryption_manager=encryption_manager,
            compression_manager=compression_manager
        )
        
        if result is None:
            raise HTTPException(status_code=404, detail="Key not found")
        duration_ms = (time.perf_counter() - start) * 1000.0
        result["duration_ms"] = duration_ms
        
        # Record access pattern
        pattern_analyzer.record_access(
            key,
            "read",
            response_time_ms=duration_ms,
            data_size=result.get("size_bytes", 0),
        )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/delete/{key}")
async def delete_value(key: str, current_user: Dict[str, Any] = Depends(get_current_user)):
    """Delete a key-value pair"""
    try:
        success = kv_store.delete(key)
        if not success:
            raise HTTPException(status_code=404, detail="Key not found")
        
        # Record access pattern
        pattern_analyzer.record_access(key, "delete")
        
        return {"message": f"Key '{key}' deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/keys")
async def list_keys(current_user: Dict[str, Any] = Depends(get_current_user)):
    """List all keys in the store"""
    try:
        keys = kv_store.list_keys()
        return {"keys": keys, "count": len(keys)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/analysis", response_model=PatternAnalysisResponse)
async def get_pattern_analysis(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Get pattern analysis and recommendations"""
    try:
        analysis = pattern_analyzer.analyze_patterns(kv_store)
        return analysis
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats")
async def get_store_stats(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Get basic store statistics"""
    try:
        stats = kv_store.get_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def open_browser():
    """Open browser after a short delay"""
    time.sleep(2)  # Wait for server to start
    webbrowser.open("http://localhost:8000")

if __name__ == "__main__":
    # Start browser in a separate thread
    browser_thread = threading.Thread(target=open_browser)
    browser_thread.daemon = True
    browser_thread.start()
    
    print("🚀 Starting Encrypted Key-Value Store...")
    print("🌐 Beautiful web interface will open automatically at: http://localhost:8000")
    print("📊 API documentation available at: http://localhost:8000/docs")
    print("🛑 Press CTRL+C to stop the server")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
