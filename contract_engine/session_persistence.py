"""
Enhanced Session Persistence for Pipeline Architecture

This module provides improved session management and persistence for the new
pipeline-based architecture, including pipeline state persistence and enhanced
context serialization.
"""

import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from swisper_core.types import SwisperContext
from swisper_core.errors import OperationMode
from swisper_core.monitoring import health_monitor
from swisper_core import get_logger

logger = get_logger(__name__)

class PipelineSessionManager:
    """
    Enhanced session manager for pipeline-based architecture.
    
    Handles persistence of:
    - Pipeline execution state
    - Enhanced context with pipeline metadata
    - Service health status per session
    - Performance metrics and caching
    """
    
    def __init__(self):
        self.pipeline_cache = {}
        self.session_metrics = {}
        self.context_cache = {}
        
    def save_pipeline_state(self, session_id: str, pipeline_name: str, 
                           pipeline_result: Dict[str, Any], execution_time: Optional[float] = None) -> None:
        """
        Save pipeline execution state for session recovery.
        
        Args:
            session_id: Session identifier
            pipeline_name: Name of the pipeline (product_search, preference_match)
            pipeline_result: Result from pipeline execution
            execution_time: Time taken for pipeline execution in seconds
        """
        try:
            if session_id not in self.pipeline_cache:
                self.pipeline_cache[session_id] = {}
            
            pipeline_state = {
                "result": pipeline_result,
                "timestamp": datetime.now().isoformat(),
                "execution_time": execution_time,
                "status": pipeline_result.get("status", "unknown"),
                "operation_mode": health_monitor.get_operation_mode().value
            }
            
            self.pipeline_cache[session_id][pipeline_name] = pipeline_state
            
            self._update_session_metrics(session_id, pipeline_name, execution_time)
            
            logger.info(f"Saved pipeline state for session {session_id}, pipeline {pipeline_name}")
            
        except Exception as e:
            logger.error(f"Error saving pipeline state for session {session_id}: {e}")
    
    def get_pipeline_state(self, session_id: str, pipeline_name: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached pipeline state for session.
        
        Args:
            session_id: Session identifier
            pipeline_name: Name of the pipeline
            
        Returns:
            Pipeline state dict or None if not found
        """
        try:
            if session_id in self.pipeline_cache:
                pipeline_state = self.pipeline_cache[session_id].get(pipeline_name)
                
                if pipeline_state:
                    timestamp = datetime.fromisoformat(pipeline_state["timestamp"])
                    if datetime.now() - timestamp < timedelta(minutes=30):
                        logger.debug(f"Retrieved fresh pipeline state for session {session_id}, pipeline {pipeline_name}")
                        return pipeline_state
                    else:
                        logger.debug(f"Pipeline state expired for session {session_id}, pipeline {pipeline_name}")
                        del self.pipeline_cache[session_id][pipeline_name]
            
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving pipeline state for session {session_id}: {e}")
            return None
    
    def save_enhanced_context(self, session_id: str, context: SwisperContext, 
                            pipeline_metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Save enhanced context with pipeline metadata.
        
        Args:
            session_id: Session identifier
            context: SwisperContext instance
            pipeline_metadata: Additional pipeline execution metadata
        """
        try:
            context_dict = context.to_dict()
            
            if pipeline_metadata:
                context_dict["pipeline_metadata"] = pipeline_metadata
            
            if session_id in self.session_metrics:
                context_dict["session_metrics"] = self.session_metrics[session_id]
            
            context_dict["operation_mode"] = health_monitor.get_operation_mode().value
            
            if session_id in self.pipeline_cache:
                pipeline_summary = {}
                for pipeline_name, state in self.pipeline_cache[session_id].items():
                    pipeline_summary[pipeline_name] = {
                        "status": state.get("status"),
                        "timestamp": state.get("timestamp"),
                        "execution_time": state.get("execution_time")
                    }
                context_dict["pipeline_cache_summary"] = pipeline_summary
            
            self.context_cache[session_id] = {
                "context": context_dict,
                "saved_at": datetime.now().isoformat()
            }
            
            from orchestrator.session_store import set_contract_fsm
            
            class EnhancedContextContainer:
                def __init__(self, context_dict):
                    self.context = SwisperContext.from_dict(context_dict)
                    self.contract_template = context_dict.get("contract_template", "contract_templates/purchase_item.yaml")
            
            enhanced_fsm = EnhancedContextContainer(context_dict)
            set_contract_fsm(session_id, enhanced_fsm)
            
            logger.info(f"Saved enhanced context for session {session_id}")
            
        except Exception as e:
            logger.error(f"Error saving enhanced context for session {session_id}: {e}")
    
    def load_enhanced_context(self, session_id: str) -> Optional[SwisperContext]:
        """
        Load enhanced context with pipeline metadata.
        
        Args:
            session_id: Session identifier
            
        Returns:
            SwisperContext instance or None if not found
        """
        try:
            if session_id in self.context_cache:
                cached_data = self.context_cache[session_id]
                saved_at = datetime.fromisoformat(cached_data["saved_at"])
                
                if datetime.now() - saved_at < timedelta(minutes=5):
                    context_dict = cached_data["context"]
                    logger.debug(f"Using cached enhanced context for session {session_id}")
                    return SwisperContext.from_dict(context_dict)
            
            from orchestrator.session_store import get_contract_context
            
            context_dict = get_contract_context(session_id)
            if context_dict:
                pipeline_metadata = context_dict.get("pipeline_metadata", {})
                session_metrics = context_dict.get("session_metrics", {})
                
                if pipeline_metadata:
                    logger.debug(f"Restored pipeline metadata for session {session_id}: {list(pipeline_metadata.keys())}")
                
                if session_metrics:
                    self.session_metrics[session_id] = session_metrics
                
                clean_context_dict = {k: v for k, v in context_dict.items() 
                                    if k not in ["pipeline_metadata", "session_metrics", "operation_mode", "pipeline_cache_summary"]}
                
                context = SwisperContext.from_dict(clean_context_dict)
                
                self.context_cache[session_id] = {
                    "context": context_dict,
                    "saved_at": datetime.now().isoformat()
                }
                
                logger.info(f"Loaded enhanced context for session {session_id}")
                return context
            
            return None
            
        except Exception as e:
            logger.error(f"Error loading enhanced context for session {session_id}: {e}")
            return None
    
    def get_session_metrics(self, session_id: str) -> Dict[str, Any]:
        """
        Get performance metrics for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Dictionary of session metrics
        """
        return self.session_metrics.get(session_id, {
            "total_pipeline_executions": 0,
            "total_execution_time": 0.0,
            "average_execution_time": 0.0,
            "pipeline_success_rate": 0.0,
            "last_activity": None
        })
    
    def cleanup_expired_sessions(self, max_age_hours: int = 24) -> int:
        """
        Clean up expired session data.
        
        Args:
            max_age_hours: Maximum age of sessions to keep
            
        Returns:
            Number of sessions cleaned up
        """
        try:
            cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
            cleaned_count = 0
            
            expired_sessions = []
            for session_id, pipelines in self.pipeline_cache.items():
                session_expired = True
                for pipeline_name, state in list(pipelines.items()):
                    timestamp = datetime.fromisoformat(state["timestamp"])
                    if timestamp < cutoff_time:
                        del pipelines[pipeline_name]
                        cleaned_count += 1
                    else:
                        session_expired = False
                
                if session_expired and not pipelines:
                    expired_sessions.append(session_id)
            
            for session_id in expired_sessions:
                del self.pipeline_cache[session_id]
                if session_id in self.session_metrics:
                    del self.session_metrics[session_id]
                if session_id in self.context_cache:
                    del self.context_cache[session_id]
            
            logger.info(f"Cleaned up {cleaned_count} expired pipeline states and {len(expired_sessions)} expired sessions")
            return cleaned_count + len(expired_sessions)
            
        except Exception as e:
            logger.error(f"Error during session cleanup: {e}")
            return 0
    
    def _update_session_metrics(self, session_id: str, pipeline_name: str, execution_time: Optional[float] = None) -> None:
        """Update session performance metrics."""
        try:
            if session_id not in self.session_metrics:
                self.session_metrics[session_id] = {
                    "total_pipeline_executions": 0,
                    "total_execution_time": 0.0,
                    "pipeline_executions": {},
                    "pipeline_success_count": 0,
                    "pipeline_failure_count": 0,
                    "last_activity": None
                }
            
            metrics = self.session_metrics[session_id]
            metrics["total_pipeline_executions"] += 1
            metrics["last_activity"] = datetime.now().isoformat()
            
            if execution_time is not None:
                metrics["total_execution_time"] += execution_time
                metrics["average_execution_time"] = metrics["total_execution_time"] / metrics["total_pipeline_executions"]
            
            if pipeline_name not in metrics["pipeline_executions"]:
                metrics["pipeline_executions"][pipeline_name] = 0
            metrics["pipeline_executions"][pipeline_name] += 1
            
            metrics["pipeline_success_count"] += 1
            total_attempts = metrics["pipeline_success_count"] + metrics["pipeline_failure_count"]
            metrics["pipeline_success_rate"] = metrics["pipeline_success_count"] / total_attempts if total_attempts > 0 else 0.0
            
        except Exception as e:
            logger.error(f"Error updating session metrics for {session_id}: {e}")

session_manager = PipelineSessionManager()

def save_pipeline_execution(session_id: str, pipeline_name: str, result: Dict[str, Any], execution_time: Optional[float] = None) -> None:
    """
    Convenience function to save pipeline execution state.
    
    Args:
        session_id: Session identifier
        pipeline_name: Name of the pipeline
        result: Pipeline execution result
        execution_time: Execution time in seconds
    """
    session_manager.save_pipeline_state(session_id, pipeline_name, result, execution_time)

def get_cached_pipeline_result(session_id: str, pipeline_name: str) -> Optional[Dict[str, Any]]:
    """
    Convenience function to get cached pipeline result.
    
    Args:
        session_id: Session identifier
        pipeline_name: Name of the pipeline
        
    Returns:
        Cached pipeline result or None
    """
    state = session_manager.get_pipeline_state(session_id, pipeline_name)
    return state.get("result") if state else None

def save_session_context(session_id: str, context: SwisperContext, pipeline_metadata: Optional[Dict[str, Any]] = None) -> None:
    """
    Convenience function to save enhanced session context.
    
    Args:
        session_id: Session identifier
        context: SwisperContext instance
        pipeline_metadata: Additional pipeline metadata
    """
    session_manager.save_enhanced_context(session_id, context, pipeline_metadata)

def load_session_context(session_id: str) -> Optional[SwisperContext]:
    """
    Convenience function to load enhanced session context.
    
    Args:
        session_id: Session identifier
        
    Returns:
        SwisperContext instance or None
    """
    return session_manager.load_enhanced_context(session_id)

def get_session_performance_metrics(session_id: str) -> Dict[str, Any]:
    """
    Convenience function to get session performance metrics.
    
    Args:
        session_id: Session identifier
        
    Returns:
        Dictionary of performance metrics
    """
    return session_manager.get_session_metrics(session_id)

def cleanup_old_sessions(max_age_hours: int = 24) -> int:
    """
    Convenience function to clean up old session data.
    
    Args:
        max_age_hours: Maximum age of sessions to keep
        
    Returns:
        Number of items cleaned up
    """
    return session_manager.cleanup_expired_sessions(max_age_hours)
