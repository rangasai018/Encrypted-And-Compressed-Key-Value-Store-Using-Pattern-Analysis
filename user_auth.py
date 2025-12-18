import sqlite3
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import os

class UserAuth:
    def __init__(self, db_path: str = "users.db"):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize user database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                role TEXT DEFAULT 'user',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                session_token TEXT UNIQUE NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        conn.commit()
        conn.close()
        
        # Create default admin user if no users exist
        self._create_default_admin()
    
    def _create_default_admin(self):
        """Create default admin user if no users exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        
        if user_count == 0:
            # Create default admin user
            username = "admin"
            email = "admin@example.com"
            password = "admin123"  # Change this in production!
            
            salt = secrets.token_hex(16)
            password_hash = self._hash_password(password, salt)
            
            cursor.execute('''
                INSERT INTO users (username, email, password_hash, salt, role)
                VALUES (?, ?, ?, ?, ?)
            ''', (username, email, password_hash, salt, 'admin'))
            
            conn.commit()
            print(f"Created default admin user: {username} / {password}")
        
        conn.close()
    
    def _hash_password(self, password: str, salt: str) -> str:
        """Hash password with salt"""
        return hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000).hex()
    
    def _verify_password(self, password: str, salt: str, password_hash: str) -> bool:
        """Verify password against hash"""
        return self._hash_password(password, salt) == password_hash
    
    def register_user(self, username: str, email: str, password: str) -> Dict[str, Any]:
        """Register a new user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Check if username or email already exists
            cursor.execute("SELECT username FROM users WHERE username = ? OR email = ?", (username, email))
            existing_user = cursor.fetchone()
            
            if existing_user:
                return {"success": False, "message": "Username or email already exists"}
            
            # Create user
            salt = secrets.token_hex(16)
            password_hash = self._hash_password(password, salt)
            
            cursor.execute('''
                INSERT INTO users (username, email, password_hash, salt)
                VALUES (?, ?, ?, ?)
            ''', (username, email, password_hash, salt))
            
            user_id = cursor.lastrowid
            conn.commit()
            
            return {
                "success": True, 
                "message": "User registered successfully",
                "user_id": user_id,
                "username": username
            }
            
        except Exception as e:
            return {"success": False, "message": f"Registration failed: {str(e)}"}
        finally:
            conn.close()
    
    def login_user(self, username: str, password: str) -> Dict[str, Any]:
        """Login user and create session"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Get user
            cursor.execute('''
                SELECT id, username, email, password_hash, salt, role, is_active
                FROM users WHERE username = ?
            ''', (username,))
            
            user = cursor.fetchone()
            
            if not user:
                return {"success": False, "message": "Invalid credentials"}
            
            user_id, db_username, email, password_hash, salt, role, is_active = user
            
            if not is_active:
                return {"success": False, "message": "Account is deactivated"}
            
            # Verify password
            if not self._verify_password(password, salt, password_hash):
                return {"success": False, "message": "Invalid credentials"}
            
            # Update last login
            cursor.execute('''
                UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?
            ''', (user_id,))
            
            # Create session
            session_token = secrets.token_urlsafe(32)
            expires_at = datetime.now() + timedelta(hours=24)  # 24 hour session
            
            cursor.execute('''
                INSERT INTO sessions (user_id, session_token, expires_at)
                VALUES (?, ?, ?)
            ''', (user_id, session_token, expires_at))
            
            conn.commit()
            
            return {
                "success": True,
                "message": "Login successful",
                "session_token": session_token,
                "user": {
                    "id": user_id,
                    "username": db_username,
                    "email": email,
                    "role": role
                }
            }
            
        except Exception as e:
            return {"success": False, "message": f"Login failed: {str(e)}"}
        finally:
            conn.close()
    
    def verify_session(self, session_token: str) -> Optional[Dict[str, Any]]:
        """Verify session token and return user info"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT s.user_id, s.expires_at, u.username, u.email, u.role, u.is_active
                FROM sessions s
                JOIN users u ON s.user_id = u.id
                WHERE s.session_token = ? AND s.expires_at > CURRENT_TIMESTAMP AND u.is_active = 1
            ''', (session_token,))
            
            session = cursor.fetchone()
            
            if not session:
                return None
            
            user_id, expires_at, username, email, role, is_active = session
            
            return {
                "user_id": user_id,
                "username": username,
                "email": email,
                "role": role,
                "expires_at": expires_at
            }
            
        except Exception as e:
            return None
        finally:
            conn.close()
    
    def logout_user(self, session_token: str) -> bool:
        """Logout user by invalidating session"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("DELETE FROM sessions WHERE session_token = ?", (session_token,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception:
            return False
        finally:
            conn.close()
    
    def get_all_users(self) -> list:
        """Get all users (admin only)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT id, username, email, role, created_at, last_login, is_active
                FROM users ORDER BY created_at DESC
            ''')
            
            users = []
            for row in cursor.fetchall():
                users.append({
                    "id": row[0],
                    "username": row[1],
                    "email": row[2],
                    "role": row[3],
                    "created_at": row[4],
                    "last_login": row[5],
                    "is_active": bool(row[6])
                })
            
            return users
        finally:
            conn.close()
    
    def delete_user(self, user_id: int) -> bool:
        """Delete user (admin only)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Delete user sessions first
            cursor.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
            
            # Delete user
            cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
            
            conn.commit()
            return cursor.rowcount > 0
        except Exception:
            return False
        finally:
            conn.close()
