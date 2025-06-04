import re
import spacy
import logging
from typing import List, Dict, Any, Tuple, Optional
from openai import OpenAI

logger = logging.getLogger(__name__)

class PIIRedactor:
    """
    Multi-layered PII detection and redaction for Swisper Core
    
    Layers:
    1. Regex patterns for structured PII (emails, phones, credit cards)
    2. spaCy NER for named entities (PERSON, GPE, ORG, DATE)
    3. Optional LLM fallback for complex/fuzzy PII detection
    """
    
    def __init__(self, use_ner=True, use_llm_fallback=False):
        self.use_ner = use_ner
        self.use_llm_fallback = use_llm_fallback
        
        self.regex_patterns = {
            "EMAIL": re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
            "SWISS_PHONE": re.compile(r'(\+41|0041|0)\s?[1-9]\d{1,2}\s?\d{3}\s?\d{2}\s?\d{2}'),
            "IBAN": re.compile(r'\bCH\d{2}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{1}\b'),
            "SWISS_SSN": re.compile(r'\b756\.\d{4}\.\d{4}\.\d{2}\b'),
            "CREDIT_CARD": re.compile(r'\b(?:\d[ -]*?){13,16}\b'),
            "PHONE": re.compile(r'\+?\d[\d -]{7,}\d'),
        }
        
        self.ner_model = None
        if use_ner:
            try:
                self.ner_model = spacy.load("en_core_web_lg")
                logger.info("Loaded spaCy en_core_web_lg model for NER")
            except OSError:
                logger.warning("en_core_web_lg not found, falling back to en_core_web_sm")
                try:
                    self.ner_model = spacy.load("en_core_web_sm")
                except OSError:
                    logger.error("No spaCy model available, NER disabled")
                    self.use_ner = False
        
        self.llm_client = None
        if use_llm_fallback:
            try:
                self.llm_client = OpenAI()
                logger.info("Initialized OpenAI client for LLM fallback")
            except Exception as e:
                logger.warning(f"Failed to initialize LLM client: {e}")
                self.use_llm_fallback = False
    
    def redact(self, text: str, redaction_method: str = "placeholder") -> str:
        """
        Apply multi-layered PII redaction to text
        
        Args:
            text: Input text to redact
            redaction_method: "placeholder" or "hash"
        
        Returns:
            Redacted text with PII replaced
        """
        redacted = text
        detected_entities = []
        
        for label, pattern in self.regex_patterns.items():
            matches = list(pattern.finditer(redacted))
            for match in matches:
                pii_text = match.group()
                detected_entities.append({
                    "text": pii_text,
                    "label": label,
                    "start": match.start(),
                    "end": match.end(),
                    "method": "regex"
                })
                
                if redaction_method == "hash":
                    replacement = self._hash_pii(pii_text, label)
                else:
                    replacement = f"[REDACTED_{label}]"
                
                redacted = redacted.replace(pii_text, replacement)
        
        if self.use_ner and self.ner_model:
            try:
                doc = self.ner_model(redacted)
                for ent in doc.ents:
                    if ent.label_ in ["PERSON", "GPE", "ORG", "DATE"]:
                        detected_entities.append({
                            "text": ent.text,
                            "label": ent.label_,
                            "start": ent.start_char,
                            "end": ent.end_char,
                            "method": "ner"
                        })
                        
                        if redaction_method == "hash":
                            replacement = self._hash_pii(ent.text, ent.label_)
                        else:
                            replacement = f"[REDACTED_{ent.label_}]"
                        
                        redacted = redacted.replace(ent.text, replacement)
            except Exception as e:
                logger.error(f"NER processing failed: {e}")
        
        if self.use_llm_fallback and self.llm_client:
            try:
                prompt = (
                    "Redact any personal or sensitive identifiers in the following text. "
                    "Replace them with [REDACTED] where needed. Only return the redacted text:\n\n" + redacted
                )
                response = self.llm_client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=512,
                    temperature=0
                )
                llm_redacted = response.choices[0].message.content.strip()
                
                if len(llm_redacted) < len(redacted) * 0.9:
                    redacted = llm_redacted
                    detected_entities.append({
                        "text": "LLM_DETECTED",
                        "label": "LLM_FALLBACK",
                        "method": "llm"
                    })
                    
            except Exception as e:
                logger.error(f"LLM fallback failed: {e}")
        
        logger.info(f"PIIRedactor processed text: {len(detected_entities)} entities detected")
        return redacted
    
    def detect_pii(self, text: str) -> List[Dict[str, Any]]:
        """
        Detect PII without redaction for analysis
        
        Returns:
            List of detected PII entities with metadata
        """
        detected_entities = []
        
        for label, pattern in self.regex_patterns.items():
            matches = list(pattern.finditer(text))
            for match in matches:
                detected_entities.append({
                    "text": match.group(),
                    "label": label,
                    "start": match.start(),
                    "end": match.end(),
                    "confidence": 0.9,
                    "method": "regex"
                })
        
        if self.use_ner and self.ner_model:
            try:
                doc = self.ner_model(text)
                for ent in doc.ents:
                    if ent.label_ in ["PERSON", "GPE", "ORG", "DATE"]:
                        detected_entities.append({
                            "text": ent.text,
                            "label": ent.label_,
                            "start": ent.start_char,
                            "end": ent.end_char,
                            "confidence": 0.8,  # Default NER confidence
                            "method": "ner"
                        })
            except Exception as e:
                logger.error(f"NER detection failed: {e}")
        
        return detected_entities
    
    def is_text_safe_for_storage(self, text: str, confidence_threshold: float = 0.7) -> bool:
        """
        Check if text is safe for vector storage
        
        Args:
            text: Text to check
            confidence_threshold: Minimum confidence for PII detection
        
        Returns:
            True if text is safe for storage, False if PII detected
        """
        detected_pii = self.detect_pii(text)
        
        for pii in detected_pii:
            if pii.get("confidence", 1.0) >= confidence_threshold:
                return False
        
        return True
    
    def _hash_pii(self, pii_text: str, label: str) -> str:
        """Create consistent hash for PII"""
        import hashlib
        hash_input = f"{label}_{pii_text}".encode()
        hash_value = hashlib.sha256(hash_input).hexdigest()[:8]
        return f"[{label}_{hash_value}]"

pii_redactor = PIIRedactor(use_ner=True, use_llm_fallback=False)
