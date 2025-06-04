import logging
from typing import Optional, Dict, Any
from collections import defaultdict
import time
from contract_engine.context import SwisperContext

class UnifiedSessionStore:
    """High-performance single source of truth for FSM session persistence"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._cache = {}
        self._cache_timestamps = {}
        self._cache_ttl = 300  # 5 minutes TTL
        self._performance_metrics = defaultdict(list)
    
    def save_fsm_state(self, session_id: str, fsm) -> bool:
        """High-performance atomic FSM state save with validation"""
        start_time = time.time()
        
        try:
            if not self._validate_fsm_state(fsm):
                self.logger.error(f"FSM state validation failed for session {session_id}")
                return False
            
            context_dict = fsm.context.to_dict()
            context_dict['contract_template'] = getattr(fsm, 'contract_template', 'contract_templates/purchase_item.yaml')
            
            success = self._save_to_postgres_atomic(session_id, context_dict)
            
            if success:
                self._cache_state(session_id, context_dict)
                self.logger.info(f"Successfully saved FSM state for session {session_id}, state: {fsm.context.current_state}")
                
                save_time = time.time() - start_time
                self._performance_metrics['save_times'].append(save_time)
                if save_time > 0.01:  # Log slow saves (>10ms)
                    self.logger.warning(f"Slow FSM save for session {session_id}: {save_time:.3f}s")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error saving FSM state for session {session_id}: {e}")
            return False
    
    def load_fsm_state(self, session_id: str):
        """High-performance FSM state load with caching and integrity validation"""
        start_time = time.time()
        
        try:
            cached_context = self._get_cached_state(session_id)
            if cached_context:
                fsm = self._reconstruct_fsm(session_id, cached_context)
                if fsm:
                    load_time = time.time() - start_time
                    self._performance_metrics['cache_hit_times'].append(load_time)
                    self.logger.debug(f"Cache hit for session {session_id}, load time: {load_time:.3f}s")
                    return fsm
            
            context_dict = self._load_from_postgres_atomic(session_id)
            
            if not context_dict:
                return None
            
            if not self._validate_context_dict(context_dict):
                self.logger.error(f"Loaded context validation failed for session {session_id}")
                return None
            
            fsm = self._reconstruct_fsm(session_id, context_dict)
            
            if fsm:
                self._cache_state(session_id, context_dict)
                
                load_time = time.time() - start_time
                self._performance_metrics['db_load_times'].append(load_time)
                if load_time > 0.01:  # Log slow loads (>10ms)
                    self.logger.warning(f"Slow FSM load for session {session_id}: {load_time:.3f}s")
                
                self.logger.info(f"Successfully loaded FSM state for session {session_id}, state: {fsm.context.current_state}")
            
            return fsm
            
        except Exception as e:
            self.logger.error(f"Error loading FSM state for session {session_id}: {e}")
            return None
    
    def _validate_fsm_state(self, fsm) -> bool:
        """Fast FSM state consistency validation"""
        if not fsm or not fsm.context:
            return False
        if not fsm.context.current_state:
            return False
        if not fsm.context.session_id:
            return False
        return True
    
    def _validate_context_dict(self, context_dict: Dict[str, Any]) -> bool:
        """Fast context dictionary integrity validation"""
        required_fields = ["session_id", "current_state"]
        return all(field in context_dict and context_dict[field] for field in required_fields)
    
    def _get_cached_state(self, session_id: str) -> Optional[Dict]:
        """High-performance cache lookup with TTL"""
        if session_id not in self._cache:
            return None
        
        if time.time() - self._cache_timestamps.get(session_id, 0) > self._cache_ttl:
            self._cache.pop(session_id, None)
            self._cache_timestamps.pop(session_id, None)
            return None
        
        return self._cache[session_id]
    
    def _cache_state(self, session_id: str, state_dict: Dict):
        """Cache state for performance optimization"""
        self._cache[session_id] = state_dict.copy()
        self._cache_timestamps[session_id] = time.time()
        
        if len(self._cache) > 1000:
            oldest_sessions = sorted(
                self._cache_timestamps.items(), 
                key=lambda x: x[1]
            )[:100]  # Remove oldest 100
            
            for old_session_id, _ in oldest_sessions:
                self._cache.pop(old_session_id, None)
                self._cache_timestamps.pop(old_session_id, None)
    
    def _save_to_postgres_atomic(self, session_id: str, context_dict: Dict) -> bool:
        """Atomic save to PostgreSQL with transaction"""
        try:
            from orchestrator.postgres_session_store import PostgresSessionStore
            store = PostgresSessionStore()
            return store.save_session_context_atomic(session_id, context_dict)
        except ImportError:
            from orchestrator.session_store import save_session_context
            save_session_context(session_id, context_dict)
            return True
    
    def _load_from_postgres_atomic(self, session_id: str) -> Optional[Dict]:
        """Atomic load from PostgreSQL"""
        try:
            from orchestrator.postgres_session_store import PostgresSessionStore
            store = PostgresSessionStore()
            return store.get_session_context_atomic(session_id)
        except ImportError:
            from orchestrator.session_store import get_session_context
            return get_session_context(session_id)
    
    def _reconstruct_fsm(self, session_id: str, context_dict: Dict):
        """Reconstruct FSM from context dictionary"""
        try:
            from contract_engine.contract_engine import ContractStateMachine
            
            contract_template = context_dict.get('contract_template', 'contract_templates/purchase_item.yaml')
            fsm = ContractStateMachine(contract_template)
            fsm.context = SwisperContext.from_dict(context_dict)
            
            return fsm
        except Exception as e:
            self.logger.error(f"Error reconstructing FSM for session {session_id}: {e}")
            return None
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for monitoring"""
        metrics = {}
        
        for metric_name, times in self._performance_metrics.items():
            if times:
                metrics[metric_name] = {
                    'count': len(times),
                    'avg_ms': sum(times) * 1000 / len(times),
                    'max_ms': max(times) * 1000,
                    'min_ms': min(times) * 1000
                }
        
        metrics['cache_size'] = len(self._cache)
        metrics['cache_hit_rate'] = (
            len(self._performance_metrics.get('cache_hit_times', [])) / 
            max(1, len(self._performance_metrics.get('cache_hit_times', [])) + 
                len(self._performance_metrics.get('db_load_times', [])))
        )
        
        return metrics
