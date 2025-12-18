import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from typing import Optional

class EncryptionManager:
    def __init__(self, password: Optional[str] = None):
        self.password = password or os.environ.get('KV_STORE_PASSWORD', 'default_password_change_me')
        self._key = self._derive_key()
        self._fernet = Fernet(self._key)
    
    def _derive_key(self) -> bytes:
        """Derive encryption key from password"""
        # Use a fixed salt for simplicity (in production, use random salt)
        salt = b'kv_store_salt_2024'
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(self.password.encode()))
        return key
    
    def encrypt(self, data: bytes) -> bytes:
        """Encrypt data"""
        try:
            return self._fernet.encrypt(data)
        except Exception as e:
            raise Exception(f"Encryption failed: {str(e)}")
    
    def decrypt(self, encrypted_data: bytes) -> bytes:
        """Decrypt data"""
        try:
            return self._fernet.decrypt(encrypted_data)
        except Exception as e:
            raise Exception(f"Decryption failed: {str(e)}")
    
    def generate_new_key(self) -> str:
        """Generate a new encryption key"""
        return Fernet.generate_key().decode()
    
    def is_encrypted(self, data: bytes) -> bool:
        """Check if data appears to be encrypted (basic check)"""
        try:
            # Try to decrypt - if it works, it's encrypted
            self._fernet.decrypt(data)
            return True
        except:
            return False
