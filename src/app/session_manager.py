from typing import Dict, Optional, List
from datetime import datetime, timedelta
import logging
from .models import SessionData, Message
from .config import settings

logger = logging.getLogger(__name__)

class InMemorySessionManager:
    """
    In-memory session manager for proof of concept.
    In production, this would be replaced with Redis or database storage.
    """
    
    def __init__(self):
        self._sessions: Dict[str, SessionData] = {}
        self._cleanup_interval = timedelta(hours=settings.session_timeout_hours)
    
    async def get_session(self, session_id: str) -> Optional[SessionData]:
        """Get session data by ID."""
        session = self._sessions.get(session_id)
        if session:
            if datetime.utcnow() - session.last_activity > self._cleanup_interval:
                await self.delete_session(session_id)
                return None
            session.update_activity()
        return session
    
    async def create_session(self, session_id: str, user_id: Optional[str] = None) -> SessionData:
        """Create a new session."""
        session = SessionData(session_id=session_id, user_id=user_id)
        self._sessions[session_id] = session
        logger.info(f"Created new session: {session_id}")
        return session
    
    async def update_session(self, session_id: str, **kwargs) -> Optional[SessionData]:
        """Update session data."""
        session = await self.get_session(session_id)
        if session:
            for key, value in kwargs.items():
                if hasattr(session, key):
                    setattr(session, key, value)
            session.update_activity()
            logger.debug(f"Updated session {session_id}: {kwargs}")
        return session
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            logger.info(f"Deleted session: {session_id}")
            return True
        return False
    
    async def add_message(self, session_id: str, message: Message) -> bool:
        """Add a message to session history."""
        session = await self.get_session(session_id)
        if not session:
            session = await self.create_session(session_id)
        
        if len(session.context.get("messages", [])) >= settings.max_messages_per_session:
            session.context["messages"] = session.context.get("messages", [])[-50:]
        
        if "messages" not in session.context:
            session.context["messages"] = []
        
        session.context["messages"].append(message.model_dump())
        session.update_activity()
        return True
    
    async def get_messages(self, session_id: str, limit: Optional[int] = None) -> List[Message]:
        """Get message history for a session."""
        session = await self.get_session(session_id)
        if not session or "messages" not in session.context:
            return []
        
        messages_data = session.context["messages"]
        if limit:
            messages_data = messages_data[-limit:]
        
        return [Message(**msg) for msg in messages_data]
    
    async def cleanup_expired_sessions(self):
        """Remove expired sessions."""
        now = datetime.utcnow()
        expired_sessions = [
            session_id for session_id, session in self._sessions.items()
            if now - session.last_activity > self._cleanup_interval
        ]
        
        for session_id in expired_sessions:
            await self.delete_session(session_id)
        
        if expired_sessions:
            logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")

session_manager = InMemorySessionManager()
