import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import redis


class RedisPatternAnalyzer:
    def __init__(self, redis_url: Optional[str] = None, namespace: str = "kv:pa"):
        self.redis_url = redis_url or os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        self.namespace = namespace or os.environ.get("REDIS_PA_NAMESPACE", "kv:pa")
        self._r = redis.Redis.from_url(self.redis_url, decode_responses=True)

        # Keys
        self.k_ops = f"{self.namespace}:ops"  # hash: operation -> count
        self.k_stats = f"{self.namespace}:stats"  # hash: totals (total_accesses, total_response_time_ms, min_ms, max_ms, total_data_size)
        self.k_top = f"{self.namespace}:top"  # zset: key -> access_count
        # per-key stats hash prefix
        self.k_key_stats_prefix = f"{self.namespace}:keystats:"

    def record_access(self, key: str, operation: str, response_time_ms: float = 0, data_size: int = 0):
        pipe = self._r.pipeline()

        # ops distribution
        pipe.hincrby(self.k_ops, operation, 1)

        # total counters
        pipe.hincrby(self.k_stats, "total_accesses", 1)
        if response_time_ms:
            pipe.hincrbyfloat(self.k_stats, "total_response_time_ms", float(response_time_ms))
        if data_size:
            pipe.hincrby(self.k_stats, "total_data_size", int(data_size))

        # min/max response time tracking (naive read/compare/write)
        pipe.execute()

        # update min/max outside pipeline to compare
        try:
            if response_time_ms:
                current_min = self._r.hget(self.k_stats, "min_ms")
                current_max = self._r.hget(self.k_stats, "max_ms")
                if current_min is None or float(response_time_ms) < float(current_min):
                    self._r.hset(self.k_stats, "min_ms", float(response_time_ms))
                if current_max is None or float(response_time_ms) > float(current_max):
                    self._r.hset(self.k_stats, "max_ms", float(response_time_ms))
        except Exception:
            pass

        # top accessed zset
        self._r.zincrby(self.k_top, 1, key)

        # per-key stats
        k_key_stats = f"{self.k_key_stats_prefix}{key}"
        pipe = self._r.pipeline()
        pipe.hincrby(k_key_stats, "total_accesses", 1)
        if response_time_ms:
            pipe.hincrbyfloat(k_key_stats, "total_response_time_ms", float(response_time_ms))
            # min/max per key
        pipe.execute()
        try:
            if response_time_ms:
                cmin = self._r.hget(k_key_stats, "min_ms")
                cmax = self._r.hget(k_key_stats, "max_ms")
                if cmin is None or float(response_time_ms) < float(cmin):
                    self._r.hset(k_key_stats, "min_ms", float(response_time_ms))
                if cmax is None or float(response_time_ms) > float(cmax):
                    self._r.hset(k_key_stats, "max_ms", float(response_time_ms))
        except Exception:
            pass

    def analyze_patterns(self, kv_store) -> Dict[str, Any]:
        # read global stats
        stats = self._r.hgetall(self.k_stats)
        total_accesses = int(stats.get("total_accesses", 0))
        total_response_time_ms = float(stats.get("total_response_time_ms", 0.0) or 0.0)
        min_ms = float(stats.get("min_ms", 0.0) or 0.0)
        max_ms = float(stats.get("max_ms", 0.0) or 0.0)

        avg_ms = (total_response_time_ms / total_accesses) if total_accesses > 0 else 0.0

        # ops distribution
        ops = self._r.hgetall(self.k_ops)
        operation_stats = {k: int(v) for k, v in ops.items()}

        # top accessed keys
        z = self._r.zrevrange(self.k_top, 0, 9, withscores=True)
        top_keys = [{"key": k, "access_count": int(s)} for k, s in z]

        # store stats from current backend
        store_stats = kv_store.get_stats()

        # recommendations (reuse heuristics)
        recommendations = []
        compression_ratio = store_stats["compressed_keys"] / max(store_stats["total_keys"], 1)
        if compression_ratio < 0.8:
            recommendations.append("Consider enabling compression for more keys to save storage space")

        encryption_ratio = store_stats["encrypted_keys"] / max(store_stats["total_keys"], 1)
        if encryption_ratio < 0.9:
            recommendations.append("Consider enabling encryption for more keys to improve security")

        if avg_ms and avg_ms > 100:
            recommendations.append("Average response time is high. Consider optimizing frequently accessed keys")

        if operation_stats.get("read", 0) > operation_stats.get("write", 0) * 3:
            recommendations.append("High read-to-write ratio detected. Consider implementing caching")

        if len(top_keys) >= 3:
            keys = [k["key"] for k in top_keys[:5]]
            if self._detect_naming_patterns(keys):
                recommendations.append("Detected consistent key naming patterns. Consider implementing key hierarchies")

        if store_stats["total_size_bytes"] > 100 * 1024 * 1024:
            recommendations.append("Large storage usage detected. Consider implementing data archival for old keys")

        return {
            "total_keys": store_stats["total_keys"],
            "access_patterns": {
                "total_accesses": total_accesses,
                "unique_keys_accessed": int(self._r.zcard(self.k_top)),
                "operation_distribution": operation_stats,
                "top_accessed_keys": top_keys,
                "response_time_stats": {
                    "avg_ms": avg_ms,
                    "min_ms": min_ms,
                    "max_ms": max_ms,
                },
            },
            "compression_stats": {
                "compressed_keys": store_stats["compressed_keys"],
                "compression_ratio": compression_ratio,
            },
            "encryption_stats": {
                "encrypted_keys": store_stats["encrypted_keys"],
                "encryption_ratio": encryption_ratio,
            },
            "recommendations": recommendations,
        }

    def get_key_insights(self, key: str) -> Dict[str, Any]:
        k_key_stats = f"{self.k_key_stats_prefix}{key}"
        h = self._r.hgetall(k_key_stats)
        total_accesses = int(h.get("total_accesses", 0))
        total_response_time_ms = float(h.get("total_response_time_ms", 0.0) or 0.0)
        avg = (total_response_time_ms / total_accesses) if total_accesses > 0 else 0.0

        return {
            "key": key,
            "access_history": [],  # not stored in Redis to save space
            "statistics": {
                "total_accesses": total_accesses,
                "avg_response_time_ms": avg,
                "min_response_time_ms": float(h.get("min_ms", 0.0) or 0.0),
                "max_response_time_ms": float(h.get("max_ms", 0.0) or 0.0),
                "avg_data_size": 0,
            },
        }

    def _detect_naming_patterns(self, keys: List[str]) -> bool:
        if len(keys) < 3:
            return False
        separators = [".", "_", "-", "/"]
        for sep in separators:
            if all(sep in key for key in keys):
                return True
        try:
            prefixes = set(key.split("_")[0] for key in keys if "_" in key)
            if len(prefixes) == 1:
                return True
        except Exception:
            pass
        return False


