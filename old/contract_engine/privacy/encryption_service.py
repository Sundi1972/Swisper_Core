import os
import logging
from typing import Dict, Any, Optional
import base64
import json
from swisper_core import get_logger

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False
    
    class MockFernet:
        def __init__(self, key): pass
        def encrypt(self, data): return data
        def decrypt(self, data): return data
        @staticmethod
        def generate_key(): return b'mock_key'
    
    class MockHashAlgorithm:
        pass
    
    class MockHashes:
        @staticmethod
        def SHA256(): return MockHashAlgorithm()
    
    class MockPBKDF2HMAC:
        def __init__(self, *args, **kwargs): pass
        def derive(self, key): return b'mock_derived_key'
    
    Fernet = MockFernet
    hashes = MockHashes()
    PBKDF2HMAC = MockPBKDF2HMAC


logger = get_logger(__name__)

class EncryptionService:
    """Per-user encryption service for sensitive memory data"""
    
    def __init__(self):
        if not CRYPTOGRAPHY_AVAILABLE:
            logger.warning("Cryptography not available, using fallback mode")
        self.master_key = self._get_or_create_master_key()
    
    def _get_or_create_master_key(self) -> bytes:
        """Get or create master encryption key"""
        key_env = os.getenv("SWISPER_MASTER_KEY")
        if key_env:
            return base64.urlsafe_b64decode(key_env.encode())
        
        master_key = Fernet.generate_key()
        logger.warning("Generated new master key. Set SWISPER_MASTER_KEY environment variable for production")
        return master_key
    

    
    def _derive_user_key(self, user_id: str) -> bytes:
        """Derive user-specific encryption key"""
        salt = f"swisper_user_{user_id}".encode()
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        return base64.urlsafe_b64encode(kdf.derive(self.master_key))
    
    def encrypt_user_data(self, user_id: str, data: Dict[str, Any]) -> str:
        """Encrypt data for specific user"""
        try:
            user_key = self._derive_user_key(user_id)
            fernet = Fernet(user_key)
            
            json_data = json.dumps(data, sort_keys=True)
            encrypted_data = fernet.encrypt(json_data.encode())
            
            return base64.urlsafe_b64encode(encrypted_data).decode()
            
        except Exception as e:
            logger.error(f"Failed to encrypt data for user {user_id}: {e}")
            raise
    
    def decrypt_user_data(self, user_id: str, encrypted_data: str) -> Dict[str, Any]:
        """Decrypt data for specific user"""
        try:
            user_key = self._derive_user_key(user_id)
            fernet = Fernet(user_key)
            
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted_data = fernet.decrypt(encrypted_bytes)
            
            return json.loads(decrypted_data.decode())
            
        except Exception as e:
            logger.error(f"Failed to decrypt data for user {user_id}: {e}")
            raise

encryption_service = EncryptionService()
