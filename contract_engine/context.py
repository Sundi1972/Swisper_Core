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
    refinement_attempts: int = 0
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
    
    pipeline_executions: Dict[str, Any] = Field(default_factory=dict)
    last_pipeline_results: Dict[str, Any] = Field(default_factory=dict)
    pipeline_performance_metrics: Dict[str, float] = Field(default_factory=dict)
    
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: Optional[str] = None
    
    def update_state(self, new_state: str):
        """Update current state and log the transition"""
        self.step_log.append(f"{self.current_state} -> {new_state}")
        self.current_state = new_state
        self.updated_at = datetime.now().isoformat()
    
    def record_pipeline_execution(self, pipeline_name: str, result: Dict[str, Any], execution_time: float = None):
        """Record pipeline execution metadata"""
        execution_record = {
            "timestamp": datetime.now().isoformat(),
            "status": result.get("status", "unknown"),
            "execution_time": execution_time,
            "result_summary": {
                "items_count": len(result.get("items", result.get("ranked_products", []))),
                "status": result.get("status"),
                "ranking_method": result.get("ranking_method")
            }
        }
        
        if pipeline_name not in self.pipeline_executions:
            self.pipeline_executions[pipeline_name] = []
        
        self.pipeline_executions[pipeline_name].append(execution_record)
        self.last_pipeline_results[pipeline_name] = result
        
        if execution_time is not None:
            self.pipeline_performance_metrics[f"{pipeline_name}_avg_time"] = execution_time
        
        self.updated_at = datetime.now().isoformat()
    
    def get_pipeline_history(self, pipeline_name: str) -> List[Dict[str, Any]]:
        """Get execution history for a specific pipeline"""
        return self.pipeline_executions.get(pipeline_name, [])
    
    def get_last_pipeline_result(self, pipeline_name: str) -> Optional[Dict[str, Any]]:
        """Get the last result from a specific pipeline"""
        return self.last_pipeline_results.get(pipeline_name)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary with state validation"""
        context_dict = self.dict()
        context_dict["serialization_version"] = "1.0"
        
        if not context_dict.get("current_state"):
            raise ValueError(f"Invalid state in context serialization: {context_dict.get('current_state')}")
        
        return context_dict
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SwisperContext':
        """Create context from dictionary with integrity validation"""
        required_fields = ["session_id", "current_state"]
        for field in required_fields:
            if field not in data or data[field] is None:
                raise ValueError(f"Missing required field in context data: {field}")
        
        valid_states = ["start", "search", "refine_constraints", "collect_preferences", 
                       "match_preferences", "confirm_purchase", "completed", "cancelled", "failed"]
        if data["current_state"] not in valid_states:
            raise ValueError(f"Invalid state in context data: {data['current_state']}")
        
        clean_data = {k: v for k, v in data.items() if k != "serialization_version"}
        return cls(**clean_data)
