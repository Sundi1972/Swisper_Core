"""
Privacy and governance utilities for Swisper Core

This module provides convenient imports from the existing privacy module structure
while maintaining the current organization and functionality.
"""

try:
    from contract_engine.privacy.pii_redactor import PIIRedactor
    from contract_engine.privacy.encryption_service import EncryptionService
    from contract_engine.privacy.audit_store import S3AuditStore, get_audit_store
    
    _pii_redactor = None
    _encryption_service = None
    _audit_store = None
    
    def get_pii_redactor():
        global _pii_redactor
        if _pii_redactor is None:
            _pii_redactor = PIIRedactor(use_ner=True, use_llm_fallback=False)
        return _pii_redactor
    
    def get_encryption_service():
        global _encryption_service
        if _encryption_service is None:
            _encryption_service = EncryptionService()
        return _encryption_service
    
    pii_redactor = get_pii_redactor()
    encryption_service = get_encryption_service()
    audit_store = get_audit_store()
    
except ImportError as e:
    from .. import get_logger
    logger = get_logger(__name__)
    logger.warning(f"Privacy module dependencies not available: {e}")
    
    class MockPIIRedactor:
        def redact_pii(self, text): return text
        def extract_pii(self, text): return []
    
    class MockEncryptionService:
        def encrypt(self, data): return data
        def decrypt(self, data): return data
    
    class MockAuditStore:
        def store_audit_log(self, data): pass
        def get_audit_logs(self): return []
    
    PIIRedactor = MockPIIRedactor
    EncryptionService = MockEncryptionService
    S3AuditStore = MockAuditStore
    
    pii_redactor = MockPIIRedactor()
    encryption_service = MockEncryptionService()
    audit_store = MockAuditStore()

__all__ = [
    'PIIRedactor', 'EncryptionService', 'S3AuditStore',
    'pii_redactor', 'encryption_service', 'audit_store'
]
