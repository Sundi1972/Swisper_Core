from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime

class SwisperContext(BaseModel):
    session_id: str
    contract_type: str = "purchase_item"
    current_state: str = "start"
    step_log: List[str] = Field(default_factory=list)
    
    product_query: Optional[str] = None
    enhanced_query: Optional[str] = None
    preferences: Dict[str, str] = Field(default_factory=dict)
    constraints: List[str] = Field(default_factory=list)
    must_match_model: Optional[bool] = None
    
    search_results: List[Dict[str, Any]] = Field(default_factory=list)
    extracted_attributes: List[str] = Field(default_factory=list)
    selected_product: Optional[Dict[str, Any]] = None
    tools_used: List[str] = Field(default_factory=list)
    
    product_recommendations: Optional[Dict[str, Any]] = None
    top_products: List[Dict[str, Any]] = Field(default_factory=list)
    
    confirmation_pending: bool = False
    is_cancelled: bool = False
    contract_status: Optional[str] = "active"
    
    contract_template_path: Optional[str] = None
    contract_template: Optional[str] = None
    contract_version: Optional[str] = "1.0"
    success_criteria: Optional[List[str]] = None
    
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: Optional[str] = None
    
    def update_state(self, new_state: str):
        """Update current state and log the transition"""
        self.step_log.append(f"{self.current_state} -> {new_state}")
        self.current_state = new_state
        self.updated_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dictionary"""
        return self.dict()
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SwisperContext':
        """Create from dictionary with validation"""
        return cls(**data)
