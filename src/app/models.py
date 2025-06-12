from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field
from datetime import datetime
import uuid

class Message(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class ChatRequest(BaseModel):
    messages: List[Message]
    session_id: str
    user_id: Optional[str] = None

class ChatResponse(BaseModel):
    reply: str
    session_id: str
    intent: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class Product(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    price: float
    currency: str = "USD"
    url: Optional[str] = None
    image_url: Optional[str] = None
    rating: Optional[float] = None
    reviews_count: Optional[int] = None

class ContractState(BaseModel):
    """State for the contract workflow LangGraph."""
    session_id: str
    user_query: str
    intent: str = "unknown"
    
    search_results: List[Product] = Field(default_factory=list)
    
    ranked_products: List[Product] = Field(default_factory=list)
    selected_product: Optional[Product] = None
    
    user_confirmation: Optional[bool] = None
    order_details: Dict[str, Any] = Field(default_factory=dict)
    
    current_step: str = "start"
    completed: bool = False
    error_message: Optional[str] = None
    
    messages: List[Message] = Field(default_factory=list)

class DocumentQuery(BaseModel):
    question: str
    session_id: str
    context_limit: int = 5

class DocumentResponse(BaseModel):
    answer: str
    sources: List[str] = Field(default_factory=list)
    confidence: Optional[float] = None

class SessionData(BaseModel):
    session_id: str
    user_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_activity: datetime = Field(default_factory=datetime.utcnow)
    message_count: int = 0
    context: Dict[str, Any] = Field(default_factory=dict)
    
    def update_activity(self):
        self.last_activity = datetime.utcnow()
        self.message_count += 1
