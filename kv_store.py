import json
import os
import sqlite3
from datetime import datetime
from typing import Any, Optional, Dict, List
import pickle
import base64

class KeyValueStore:
    def __init__(self, db_path: str = "kv_store.db", data_dir: str = "data"):
        self.db_path = db_path
        self.data_dir = data_dir
        self._ensure_data_dir()
        self._init_database()
    
    def _ensure_data_dir(self):
        """Ensure data directory exists"""
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
    
    def _init_database(self):
        """Initialize SQLite database for metadata"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS kv_metadata (
                key TEXT PRIMARY KEY,
                file_path TEXT NOT NULL,
                encrypted BOOLEAN NOT NULL,
                compressed BOOLEAN NOT NULL,
                size_bytes INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                access_count INTEGER DEFAULT 0
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def store(self, key: str, value: Any, encrypt: bool = True, 
              compress: bool = True, encryption_manager=None, compression_manager=None) -> Dict[str, Any]:
        """Store a key-value pair"""
        # Serialize the value
        serialized_data = self._serialize_value(value)
        original_size = len(serialized_data)
        
        # Apply compression if requested
        if compress and compression_manager:
            serialized_data = compression_manager.compress(serialized_data)
            compressed = True
        else:
            compressed = False
        
        # Apply encryption if requested
        if encrypt and encryption_manager:
            serialized_data = encryption_manager.encrypt(serialized_data)
            encrypted = True
        else:
            encrypted = False
        
        # Save to file
        file_path = os.path.join(self.data_dir, f"{key}.dat")
        with open(file_path, 'wb') as f:
            f.write(serialized_data)
        
        # Update database metadata
        self._update_metadata(key, file_path, encrypted, compressed, len(serialized_data))
        
        return {
            "key": key,
            "value": value,
            "timestamp": datetime.now(),
            "encrypted": encrypted,
            "compressed": compressed,
            "size_bytes": len(serialized_data)
        }
    
    def retrieve(self, key: str, encryption_manager=None, compression_manager=None) -> Optional[Dict[str, Any]]:
        """Retrieve a value by key"""
        # Get metadata
        metadata = self._get_metadata(key)
        if not metadata:
            return None
        
        file_path = metadata['file_path']
        if not os.path.exists(file_path):
            return None
        
        # Read file
        with open(file_path, 'rb') as f:
            data = f.read()
        
        # Decrypt if needed
        if metadata['encrypted'] and encryption_manager:
            data = encryption_manager.decrypt(data)
        
        # Decompress if needed
        if metadata['compressed'] and compression_manager:
            data = compression_manager.decompress(data)
        
        # Deserialize value
        value = self._deserialize_value(data)
        
        # Update access count
        self._increment_access_count(key)
        
        return {
            "key": key,
            "value": value,
            "timestamp": datetime.now(),
            "encrypted": metadata['encrypted'],
            "compressed": metadata['compressed'],
            "size_bytes": metadata['size_bytes']
        }
    
    def delete(self, key: str) -> bool:
        """Delete a key-value pair"""
        metadata = self._get_metadata(key)
        if not metadata:
            return False
        
        # Delete file
        file_path = metadata['file_path']
        if os.path.exists(file_path):
            os.remove(file_path)
        
        # Remove from database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM kv_metadata WHERE key = ?", (key,))
        conn.commit()
        conn.close()
        
        return True
    
    def list_keys(self) -> List[str]:
        """List all keys in the store"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT key FROM kv_metadata ORDER BY key")
        keys = [row[0] for row in cursor.fetchall()]
        conn.close()
        return keys
    
    def get_stats(self) -> Dict[str, Any]:
        """Get store statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Total keys
        cursor.execute("SELECT COUNT(*) FROM kv_metadata")
        total_keys = cursor.fetchone()[0]
        
        # Total size
        cursor.execute("SELECT SUM(size_bytes) FROM kv_metadata")
        total_size = cursor.fetchone()[0] or 0
        
        # Encryption stats
        cursor.execute("SELECT COUNT(*) FROM kv_metadata WHERE encrypted = 1")
        encrypted_count = cursor.fetchone()[0]
        
        # Compression stats
        cursor.execute("SELECT COUNT(*) FROM kv_metadata WHERE compressed = 1")
        compressed_count = cursor.fetchone()[0]
        
        # Most accessed keys
        cursor.execute("SELECT key, access_count FROM kv_metadata ORDER BY access_count DESC LIMIT 5")
        top_accessed = [{"key": row[0], "access_count": row[1]} for row in cursor.fetchall()]
        
        conn.close()
        
        return {
            "total_keys": total_keys,
            "total_size_bytes": total_size,
            "encrypted_keys": encrypted_count,
            "compressed_keys": compressed_count,
            "top_accessed_keys": top_accessed
        }
    
    def _serialize_value(self, value: Any) -> bytes:
        """Serialize value to bytes"""
        try:
            # Try JSON first for simple types
            json_str = json.dumps(value)
            return json_str.encode('utf-8')
        except (TypeError, ValueError):
            # Fall back to pickle for complex objects
            return pickle.dumps(value)
    
    def _deserialize_value(self, data: bytes) -> Any:
        """Deserialize bytes to value"""
        try:
            # Try JSON first
            json_str = data.decode('utf-8')
            return json.loads(json_str)
        except (UnicodeDecodeError, json.JSONDecodeError):
            # Fall back to pickle
            return pickle.loads(data)
    
    def _update_metadata(self, key: str, file_path: str, encrypted: bool, 
                        compressed: bool, size_bytes: int):
        """Update metadata in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO kv_metadata 
            (key, file_path, encrypted, compressed, size_bytes, updated_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (key, file_path, encrypted, compressed, size_bytes))
        
        conn.commit()
        conn.close()
    
    def _get_metadata(self, key: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a key"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT key, file_path, encrypted, compressed, size_bytes, 
                   created_at, updated_at, access_count
            FROM kv_metadata WHERE key = ?
        ''', (key,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'key': row[0],
                'file_path': row[1],
                'encrypted': bool(row[2]),
                'compressed': bool(row[3]),
                'size_bytes': row[4],
                'created_at': row[5],
                'updated_at': row[6],
                'access_count': row[7]
            }
        return None
    
    def _increment_access_count(self, key: str):
        """Increment access count for a key"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("UPDATE kv_metadata SET access_count = access_count + 1 WHERE key = ?", (key,))
        conn.commit()
        conn.close()
