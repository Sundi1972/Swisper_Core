import pytest
from unittest.mock import patch, MagicMock
from contract_engine.privacy.pii_redactor import PIIRedactor

def test_pii_redactor_initialization():
    """Test PIIRedactor initialization with different configurations"""
    redactor = PIIRedactor(use_ner=True, use_llm_fallback=False)
    assert redactor.use_ner == True
    assert redactor.use_llm_fallback == False
    
    redactor_full = PIIRedactor(use_ner=True, use_llm_fallback=True)
    assert redactor_full.use_ner == True
    assert redactor_full.use_llm_fallback == False

def test_email_detection_and_redaction():
    """Test email PII detection and redaction"""
    redactor = PIIRedactor(use_ner=False, use_llm_fallback=False)
    text = "Contact me at john.doe@example.com for more info"
    
    redacted = redactor.redact(text, "placeholder")
    assert "john.doe@example.com" not in redacted
    assert "[REDACTED_EMAIL]" in redacted
    
    redacted_hash = redactor.redact(text, "hash")
    assert "john.doe@example.com" not in redacted_hash
    assert "[EMAIL_" in redacted_hash

def test_swiss_phone_detection():
    """Test Swiss phone number detection"""
    redactor = PIIRedactor(use_ner=False, use_llm_fallback=False)
    text = "Call me at +41 44 123 45 67"
    
    redacted = redactor.redact(text, "placeholder")
    assert "+41 44 123 45 67" not in redacted
    assert "[REDACTED_SWISS_PHONE]" in redacted

def test_multiple_pii_types():
    """Test detection of multiple PII types in one text"""
    redactor = PIIRedactor(use_ner=False, use_llm_fallback=False)
    text = "Email: test@example.com, Phone: +41 44 123 45 67, IBAN: CH93 0076 2011 6238 5295 7"
    
    redacted = redactor.redact(text, "placeholder")
    assert "test@example.com" not in redacted
    assert "+41 44 123 45 67" not in redacted
    assert "CH93 0076 2011 6238 5295 7" not in redacted
    assert "[REDACTED_EMAIL]" in redacted
    assert "[REDACTED_SWISS_PHONE]" in redacted
    assert "[REDACTED_IBAN]" in redacted

@patch('spacy.load')
def test_ner_integration(mock_spacy_load):
    """Test spaCy NER integration"""
    mock_nlp = MagicMock()
    mock_doc = MagicMock()
    mock_ent = MagicMock()
    mock_ent.text = "John Smith"
    mock_ent.label_ = "PERSON"
    mock_ent.start_char = 8
    mock_ent.end_char = 18
    mock_doc.ents = [mock_ent]
    mock_nlp.return_value = mock_doc
    mock_spacy_load.return_value = mock_nlp
    
    redactor = PIIRedactor(use_ner=True, use_llm_fallback=False)
    text = "Contact John Smith for details"
    
    redacted = redactor.redact(text, "placeholder")
    assert "John Smith" not in redacted
    assert "[REDACTED_PERSON]" in redacted

def test_pii_detection_without_redaction():
    """Test PII detection for analysis without redaction"""
    redactor = PIIRedactor(use_ner=False, use_llm_fallback=False)
    text = "Email: test@example.com, Phone: +41 44 123 45 67"
    
    detected_pii = redactor.detect_pii(text)
    
    assert len(detected_pii) >= 2
    email_detected = any(pii["label"] == "EMAIL" for pii in detected_pii)
    phone_detected = any(pii["label"] == "SWISS_PHONE" for pii in detected_pii)
    assert email_detected
    assert phone_detected

def test_text_safety_check():
    """Test text safety for vector storage"""
    redactor = PIIRedactor(use_ner=False, use_llm_fallback=False)
    
    safe_text = "I prefer gaming laptops with good graphics"
    unsafe_text = "My email is test@example.com"
    
    assert redactor.is_text_safe_for_storage(safe_text) == True
    assert redactor.is_text_safe_for_storage(unsafe_text) == False

def test_hash_consistency():
    """Test that PII hashing is consistent"""
    redactor = PIIRedactor(use_ner=False, use_llm_fallback=False)
    text = "Contact test@example.com"
    
    redacted1 = redactor.redact(text, "hash")
    redacted2 = redactor.redact(text, "hash")
    
    assert redacted1 == redacted2

@patch('contract_engine.privacy.pii_redactor.OpenAI')
def test_llm_fallback_integration(mock_openai):
    """Test LLM fallback integration"""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "Contact [REDACTED] for details"
    mock_client.chat.completions.create.return_value = mock_response
    mock_openai.return_value = mock_client
    
    redactor = PIIRedactor(use_ner=False, use_llm_fallback=True)
    text = "Contact John Smith for details"
    
    redacted = redactor.redact(text, "placeholder")
    
    mock_client.chat.completions.create.assert_called_once()

def test_business_context_patterns():
    """Test business-specific PII patterns"""
    redactor = PIIRedactor(use_ner=False, use_llm_fallback=False)
    
    text = "SSN: 756.1234.5678.90"
    redacted = redactor.redact(text, "placeholder")
    assert "756.1234.5678.90" not in redacted
    assert "[REDACTED_SWISS_SSN]" in redacted
    
    text = "Card: 4111 1111 1111 1111"
    redacted = redactor.redact(text, "placeholder")
    assert "4111 1111 1111 1111" not in redacted
    assert "[REDACTED_CREDIT_CARD]" in redacted
