import lz4.frame
import gzip
import zlib
from typing import Optional

class CompressionManager:
    def __init__(self, algorithm: str = "lz4"):
        self.algorithm = algorithm.lower()
        self._supported_algorithms = ["lz4", "gzip", "zlib"]
        
        if self.algorithm not in self._supported_algorithms:
            raise ValueError(f"Unsupported compression algorithm: {algorithm}")
    
    def compress(self, data: bytes) -> bytes:
        """Compress data using the specified algorithm"""
        try:
            if self.algorithm == "lz4":
                return lz4.frame.compress(data)
            elif self.algorithm == "gzip":
                return gzip.compress(data)
            elif self.algorithm == "zlib":
                return zlib.compress(data)
        except Exception as e:
            raise Exception(f"Compression failed: {str(e)}")
    
    def decompress(self, compressed_data: bytes) -> bytes:
        """Decompress data using the specified algorithm"""
        try:
            if self.algorithm == "lz4":
                return lz4.frame.decompress(compressed_data)
            elif self.algorithm == "gzip":
                return gzip.decompress(compressed_data)
            elif self.algorithm == "zlib":
                return zlib.decompress(compressed_data)
        except Exception as e:
            raise Exception(f"Decompression failed: {str(e)}")
    
    def get_compression_ratio(self, original_data: bytes, compressed_data: bytes) -> float:
        """Calculate compression ratio"""
        if len(original_data) == 0:
            return 0.0
        return len(compressed_data) / len(original_data)
    
    def is_compressed(self, data: bytes) -> bool:
        """Check if data appears to be compressed (basic check)"""
        try:
            # Try to decompress - if it works, it's compressed
            self.decompress(data)
            return True
        except:
            return False
    
    def get_supported_algorithms(self) -> list:
        """Get list of supported compression algorithms"""
        return self._supported_algorithms.copy()
    
    def set_algorithm(self, algorithm: str):
        """Change compression algorithm"""
        if algorithm.lower() not in self._supported_algorithms:
            raise ValueError(f"Unsupported compression algorithm: {algorithm}")
        self.algorithm = algorithm.lower()
