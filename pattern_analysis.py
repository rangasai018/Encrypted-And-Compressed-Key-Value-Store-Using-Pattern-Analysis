import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Any, List
from collections import defaultdict, Counter
import statistics

class PatternAnalyzer:
    def __init__(self, db_path: str = "pattern_analysis.db"):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize database for pattern tracking"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS access_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key_name TEXT NOT NULL,
                operation TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                response_time_ms REAL,
                data_size INTEGER
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS key_patterns (
                key_name TEXT PRIMARY KEY,
                key_type TEXT,
                value_type TEXT,
                avg_size INTEGER,
                access_frequency REAL,
                last_accessed TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def record_access(self, key: str, operation: str, response_time_ms: float = 0, data_size: int = 0):
        """Record an access pattern"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO access_patterns (key_name, operation, response_time_ms, data_size)
            VALUES (?, ?, ?, ?)
        ''', (key, operation, response_time_ms, data_size))
        
        # Update key patterns
        cursor.execute('''
            INSERT OR REPLACE INTO key_patterns 
            (key_name, last_accessed, access_frequency)
            VALUES (?, CURRENT_TIMESTAMP, 
                (SELECT COUNT(*) FROM access_patterns WHERE key_name = ? AND 
                 timestamp > datetime('now', '-24 hours')) / 24.0)
        ''', (key, key))
        
        conn.commit()
        conn.close()
    
    def analyze_patterns(self, kv_store) -> Dict[str, Any]:
        """Analyze access patterns and generate insights"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get basic statistics
        cursor.execute("SELECT COUNT(*) FROM access_patterns")
        total_accesses = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT key_name) FROM access_patterns")
        unique_keys = cursor.fetchone()[0]
        
        # Get operation distribution
        cursor.execute("SELECT operation, COUNT(*) FROM access_patterns GROUP BY operation")
        operation_stats = dict(cursor.fetchall())
        
        # Get most accessed keys with last access datetime (local time)
        cursor.execute('''
            SELECT 
                key_name, 
                COUNT(*) as access_count,
                datetime(MAX(timestamp), 'localtime') as last_access_local,
                date(MAX(datetime(timestamp, 'localtime'))) as last_access_date,
                time(MAX(datetime(timestamp, 'localtime'))) as last_access_time
            FROM access_patterns 
            GROUP BY key_name 
            ORDER BY access_count DESC 
            LIMIT 10
        ''')
        top_keys = [
            {
                "key": row[0],
                "access_count": row[1],
                "last_access_datetime": row[2],
                "last_access_date": row[3],
                "last_access_time": row[4],
            }
            for row in cursor.fetchall()
        ]
        
        # Get access patterns by date (using local time)
        cursor.execute('''
            SELECT date(datetime(timestamp, 'localtime')) as date, COUNT(*) as count
            FROM access_patterns 
            GROUP BY date 
            ORDER BY date DESC
        ''')
        daily_patterns = dict(cursor.fetchall())
        
        # Get recent access history with dates
        cursor.execute('''
            SELECT key_name, operation, datetime(timestamp, 'localtime') as local_datetime,
                   date(datetime(timestamp, 'localtime')) as local_date,
                   time(datetime(timestamp, 'localtime')) as local_time,
                   response_time_ms, data_size
            FROM access_patterns 
            ORDER BY timestamp DESC 
            LIMIT 20
        ''')
        recent_access_history = [
            {
                "key": row[0],
                "operation": row[1],
                "datetime": row[2],
                "date": row[3],
                "time": row[4],
                "response_time_ms": row[5],
                "data_size": row[6]
            }
            for row in cursor.fetchall()
        ]
        
        # Get response time statistics
        cursor.execute('''
            SELECT AVG(response_time_ms), MIN(response_time_ms), MAX(response_time_ms)
            FROM access_patterns 
            WHERE response_time_ms > 0
        ''')
        response_stats = cursor.fetchone()
        
        # Get store statistics
        store_stats = kv_store.get_stats()
        
        conn.close()
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            operation_stats, top_keys, store_stats, response_stats
        )
        
        return {
            "total_keys": store_stats["total_keys"],
            "access_patterns": {
                "total_accesses": total_accesses,
                "unique_keys_accessed": unique_keys,
                "operation_distribution": operation_stats,
                "top_accessed_keys": top_keys,
                "daily_access_patterns": daily_patterns,
                "recent_access_history": recent_access_history,
                "response_time_stats": {
                    "avg_ms": response_stats[0] if response_stats[0] else 0,
                    "min_ms": response_stats[1] if response_stats[1] else 0,
                    "max_ms": response_stats[2] if response_stats[2] else 0
                }
            },
            "compression_stats": {
                "compressed_keys": store_stats["compressed_keys"],
                "compression_ratio": store_stats["compressed_keys"] / max(store_stats["total_keys"], 1)
            },
            "encryption_stats": {
                "encrypted_keys": store_stats["encrypted_keys"],
                "encryption_ratio": store_stats["encrypted_keys"] / max(store_stats["total_keys"], 1)
            },
            "recommendations": recommendations
        }
    
    def _generate_recommendations(self, operation_stats: Dict, top_keys: List, 
                                store_stats: Dict, response_stats: tuple) -> List[str]:
        """Generate recommendations based on patterns"""
        recommendations = []
        
        # Compression recommendations
        compression_ratio = store_stats["compressed_keys"] / max(store_stats["total_keys"], 1)
        if compression_ratio < 0.8:
            recommendations.append("Consider enabling compression for more keys to save storage space")
        
        # Encryption recommendations
        encryption_ratio = store_stats["encrypted_keys"] / max(store_stats["total_keys"], 1)
        if encryption_ratio < 0.9:
            recommendations.append("Consider enabling encryption for more keys to improve security")
        
        # Performance recommendations
        if response_stats[0] and response_stats[0] > 100:
            recommendations.append("Average response time is high. Consider optimizing frequently accessed keys")
        
        # Access pattern recommendations
        if operation_stats.get("read", 0) > operation_stats.get("write", 0) * 3:
            recommendations.append("High read-to-write ratio detected. Consider implementing caching")
        
        # Key naming recommendations
        if len(top_keys) > 0:
            key_patterns = [key["key"] for key in top_keys[:5]]
            if self._detect_naming_patterns(key_patterns):
                recommendations.append("Detected consistent key naming patterns. Consider implementing key hierarchies")
        
        # Storage recommendations
        if store_stats["total_size_bytes"] > 100 * 1024 * 1024:  # 100MB
            recommendations.append("Large storage usage detected. Consider implementing data archival for old keys")
        
        return recommendations
    
    def _detect_naming_patterns(self, keys: List[str]) -> bool:
        """Detect if keys follow naming patterns"""
        if len(keys) < 3:
            return False
        
        # Check for common separators
        separators = [".", "_", "-", "/"]
        for sep in separators:
            if all(sep in key for key in keys):
                return True
        
        # Check for prefix patterns
        if len(set(key.split("_")[0] for key in keys if "_" in key)) == 1:
            return True
        
        return False
    
    def get_key_insights(self, key: str) -> Dict[str, Any]:
        """Get detailed insights for a specific key"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get access history
        cursor.execute('''
            SELECT operation, timestamp, response_time_ms, data_size
            FROM access_patterns 
            WHERE key_name = ? 
            ORDER BY timestamp DESC 
            LIMIT 50
        ''', (key,))
        
        access_history = [
            {
                "operation": row[0],
                "timestamp": row[1],
                "response_time_ms": row[2],
                "data_size": row[3]
            }
            for row in cursor.fetchall()
        ]
        
        # Get statistics
        cursor.execute('''
            SELECT 
                COUNT(*) as total_accesses,
                AVG(response_time_ms) as avg_response_time,
                MIN(response_time_ms) as min_response_time,
                MAX(response_time_ms) as max_response_time,
                AVG(data_size) as avg_data_size
            FROM access_patterns 
            WHERE key_name = ?
        ''', (key,))
        
        stats = cursor.fetchone()
        
        conn.close()
        
        return {
            "key": key,
            "access_history": access_history,
            "statistics": {
                "total_accesses": stats[0],
                "avg_response_time_ms": stats[1] or 0,
                "min_response_time_ms": stats[2] or 0,
                "max_response_time_ms": stats[3] or 0,
                "avg_data_size": stats[4] or 0
            }
        }
