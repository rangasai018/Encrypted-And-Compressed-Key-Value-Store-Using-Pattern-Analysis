import os
import json
import pickle
from datetime import datetime
from typing import Any, Dict, List, Optional

import redis


class RedisKeyValueStore:
    def __init__(self, redis_url: Optional[str] = None, namespace: str = "kv"):
        self.redis_url = redis_url or os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        self.namespace = namespace or os.environ.get("REDIS_NAMESPACE", "kv")
        self._r = redis.Redis.from_url(self.redis_url, decode_responses=False)

        # Key patterns
        self._data_prefix = f"{self.namespace}:data:"
        self._meta_prefix = f"{self.namespace}:meta:"

    def _data_key(self, key: str) -> str:
        return f"{self._data_prefix}{key}"

    def _meta_key(self, key: str) -> str:
        return f"{self._meta_prefix}{key}"

    def store(
        self,
        key: str,
        value: Any,
        encrypt: bool = True,
        compress: bool = True,
        encryption_manager=None,
        compression_manager=None,
    ) -> Dict[str, Any]:
        serialized = self._serialize_value(value)

        # compress
        compressed_flag = False
        if compress and compression_manager:
            serialized = compression_manager.compress(serialized)
            compressed_flag = True

        # encrypt
        encrypted_flag = False
        if encrypt and encryption_manager:
            serialized = encryption_manager.encrypt(serialized)
            encrypted_flag = True

        # write data blob
        self._r.set(self._data_key(key), serialized)

        # write metadata hash
        meta = {
            "key": key,
            "encrypted": "1" if encrypted_flag else "0",
            "compressed": "1" if compressed_flag else "0",
            "size_bytes": str(len(serialized)),
            "updated_at": datetime.utcnow().isoformat(),
        }
        self._r.hset(self._meta_key(key), mapping=meta)

        return {
            "key": key,
            "value": value,
            "timestamp": datetime.utcnow(),
            "encrypted": encrypted_flag,
            "compressed": compressed_flag,
            "size_bytes": len(serialized),
        }

    def retrieve(
        self, key: str, encryption_manager=None, compression_manager=None
    ) -> Optional[Dict[str, Any]]:
        data = self._r.get(self._data_key(key))
        if data is None:
            return None

        meta = self._r.hgetall(self._meta_key(key))
        encrypted = meta.get(b"encrypted", b"0") == b"1"
        compressed = meta.get(b"compressed", b"0") == b"1"
        size_bytes = int(meta.get(b"size_bytes", b"0")) if meta else len(data)

        # decrypt
        if encrypted and encryption_manager:
            data = encryption_manager.decrypt(data)

        # decompress
        if compressed and compression_manager:
            data = compression_manager.decompress(data)

        value = self._deserialize_value(data)

        # increment an access counter in meta
        self._r.hincrby(self._meta_key(key), "access_count", 1)

        return {
            "key": key,
            "value": value,
            "timestamp": datetime.utcnow(),
            "encrypted": encrypted,
            "compressed": compressed,
            "size_bytes": size_bytes,
        }

    def delete(self, key: str) -> bool:
        pipe = self._r.pipeline()
        pipe.delete(self._data_key(key))
        pipe.delete(self._meta_key(key))
        deleted, _ = pipe.execute()
        return bool(deleted)

    def list_keys(self) -> List[str]:
        # scan meta keys
        keys: List[str] = []
        cursor = 0
        pattern = f"{self._meta_prefix}*"
        while True:
            cursor, batch = self._r.scan(cursor=cursor, match=pattern, count=500)
            for full_key in batch:
                # full_key like namespace:meta:<userkey>
                # extract suffix after prefix
                if isinstance(full_key, bytes):
                    full_key = full_key.decode()
                keys.append(full_key[len(self._meta_prefix) :])
            if cursor == 0:
                break
        keys.sort()
        return keys

    def get_stats(self) -> Dict[str, Any]:
        total_keys = 0
        encrypted_keys = 0
        compressed_keys = 0
        total_size = 0
        top_accessed: List[Dict[str, Any]] = []

        cursor = 0
        pattern = f"{self._meta_prefix}*"
        while True:
            cursor, batch = self._r.scan(cursor=cursor, match=pattern, count=500)
            for mk in batch:
                meta = self._r.hgetall(mk)
                total_keys += 1
                if meta.get(b"encrypted", b"0") == b"1":
                    encrypted_keys += 1
                if meta.get(b"compressed", b"0") == b"1":
                    compressed_keys += 1
                try:
                    total_size += int(meta.get(b"size_bytes", b"0"))
                except Exception:
                    pass
                access_count = int(meta.get(b"access_count", b"0"))
                key_name = mk.decode() if isinstance(mk, bytes) else mk
                key_name = key_name[len(self._meta_prefix) :]
                top_accessed.append({"key": key_name, "access_count": access_count})
            if cursor == 0:
                break

        top_accessed.sort(key=lambda x: x["access_count"], reverse=True)
        top_accessed = top_accessed[:5]

        return {
            "total_keys": total_keys,
            "total_size_bytes": total_size,
            "encrypted_keys": encrypted_keys,
            "compressed_keys": compressed_keys,
            "top_accessed_keys": top_accessed,
        }

    def _serialize_value(self, value: Any) -> bytes:
        try:
            return json.dumps(value).encode("utf-8")
        except (TypeError, ValueError):
            return pickle.dumps(value)

    def _deserialize_value(self, data: bytes) -> Any:
        try:
            return json.loads(data.decode("utf-8"))
        except Exception:
            return pickle.loads(data)


