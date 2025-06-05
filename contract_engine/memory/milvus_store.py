try:
    from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility
    MILVUS_AVAILABLE = True
except ImportError:
    MILVUS_AVAILABLE = False
    class Collection:
        def __init__(self, *args, **kwargs): 
            self._data = []
        def insert(self, *args, **kwargs): 
            return {"insert_count": 0}
        def search(self, *args, **kwargs): 
            return [[]]  # Return empty search results
        def load(self): 
            pass
        def release(self): 
            pass
        def create_index(self, *args, **kwargs): 
            pass
        def flush(self): 
            pass
        def query(self, *args, **kwargs): 
            return []
        def delete(self, *args, **kwargs): 
            pass
    
    class FieldSchema:
        def __init__(self, *args, **kwargs): 
            pass
    
    class CollectionSchema:
        def __init__(self, *args, **kwargs): 
            pass
    
    class DataType:
        FLOAT_VECTOR = "FLOAT_VECTOR"
        INT64 = "INT64"
        VARCHAR = "VARCHAR"
        JSON = "JSON"  # Add missing JSON type
    
    class connections:
        @staticmethod
        def connect(*args, **kwargs): 
            pass
        @staticmethod
        def disconnect(*args, **kwargs): 
            pass
    
    class utility:
        @staticmethod
        def has_collection(*args, **kwargs): 
            return False
        @staticmethod
        def drop_collection(*args, **kwargs): 
            pass
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any, Optional
import time
import json
from swisper_core import get_logger

logger = get_logger(__name__)

class MilvusSemanticStore:
    """Milvus Lite embedded store for semantic long-term memory"""
    
    def __init__(self, db_path: str = "./milvus_semantic_memory.db"):
        self.db_path = db_path
        self.collection_name = "semantic_memory"
        self.collection = None
        self.embedding_model = None
        self._initialize_connection()
        self._initialize_collection()
        self._initialize_embedding_model()
    
    def _initialize_connection(self):
        """Initialize Milvus Lite connection"""
        try:
            if not MILVUS_AVAILABLE:
                logger.warning("Milvus not available, using fallback mode")
                return
            
            connections.connect(
                alias="default",
                uri=self.db_path
            )
            logger.info(f"Milvus Lite connected: {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to connect to Milvus Lite: {e}")
            if not MILVUS_AVAILABLE:
                logger.info("Continuing with fallback mode")
            else:
                raise
    
    def _initialize_collection(self):
        """Initialize semantic memory collection"""
        try:
            if not MILVUS_AVAILABLE:
                self.collection = Collection()
                logger.warning("Using fallback collection (Milvus not available)")
                return
            
            fields = [
                FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                FieldSchema(name="user_id", dtype=DataType.VARCHAR, max_length=100),
                FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=1000),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=384),
                FieldSchema(name="metadata", dtype=DataType.JSON),
                FieldSchema(name="timestamp", dtype=DataType.INT64)
            ]
            
            schema = CollectionSchema(fields, "Semantic memory for user preferences and facts")
            
            if utility.has_collection(self.collection_name):
                self.collection = Collection(self.collection_name)
                logger.info(f"Using existing collection: {self.collection_name}")
            else:
                self.collection = Collection(self.collection_name, schema)
                logger.info(f"Created new collection: {self.collection_name}")
                
                index_params = {
                    "metric_type": "COSINE",
                    "index_type": "IVF_FLAT",
                    "params": {"nlist": 128}
                }
                self.collection.create_index("embedding", index_params)
                logger.info("Created vector index for semantic search")
            
            self.collection.load()
            
        except Exception as e:
            logger.error(f"Failed to initialize Milvus collection: {e}")
            if not MILVUS_AVAILABLE:
                self.collection = Collection()
                logger.info("Continuing with fallback collection")
            else:
                raise
    
    def _initialize_embedding_model(self):
        """Initialize sentence-transformers model"""
        try:
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("Sentence-transformers model loaded")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            class FallbackEmbeddingModel:
                def encode(self, texts):
                    if isinstance(texts, list):
                        return [[0.1] * 384 for _ in texts]
                    return [0.1] * 384
            
            self.embedding_model = FallbackEmbeddingModel()
            logger.warning("Using fallback embedding model (sentence-transformers not available)")
    
    def add_memory(self, user_id: str, content: str, memory_type: str = "preference", metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Add semantic memory to Milvus store with PII protection"""
        try:
            if not self.collection or not self.embedding_model:
                return False
            
            from contract_engine.privacy.pii_redactor import pii_redactor
            
            if not pii_redactor.is_text_safe_for_storage(content):
                logger.warning(f"Content contains PII, applying redaction for user {user_id}")
                content = pii_redactor.redact(content, redaction_method="hash")
                
                if metadata is None:
                    metadata = {}
                metadata["pii_detected"] = True
                metadata["pii_redacted"] = True
            
            embedding_result = self.embedding_model.encode([content])
            
            if isinstance(embedding_result, list):
                if len(embedding_result) > 0:
                    embedding = embedding_result[0]
                    if hasattr(embedding, 'tolist'):
                        embedding = embedding.tolist()
                else:
                    embedding = [0.1] * 384  # Fallback embedding
            else:
                if hasattr(embedding_result, 'tolist'):
                    embedding_list = embedding_result.tolist()
                    embedding = embedding_list[0] if isinstance(embedding_list, list) and len(embedding_list) > 0 else embedding_list
                else:
                    embedding = [0.1] * 384  # Fallback embedding
            
            data = [{
                "user_id": user_id,
                "content": content,
                "embedding": embedding,
                "metadata": json.dumps({
                    "type": memory_type,
                    "privacy_processed": True,
                    "created_at": int(time.time() * 1000),
                    **(metadata or {})
                }),
                "timestamp": int(time.time() * 1000)
            }]
            
            self.collection.insert(data)
            self.collection.flush()
            
            logger.info(f"Added privacy-protected semantic memory for user {user_id}: {content[:50]}...")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add semantic memory: {e}")
            return False
    
    def search_memories(self, user_id: str, query: str, top_k: int = 3, similarity_threshold: float = 0.7) -> List[Dict[str, Any]]:
        """Search semantic memories for user"""
        try:
            if not self.collection or not self.embedding_model:
                return []
            
            query_result = self.embedding_model.encode([query])
            if isinstance(query_result, list) and len(query_result) > 0:
                query_embedding = query_result[0]
                if hasattr(query_embedding, 'tolist'):
                    query_embedding = query_embedding.tolist()
            else:
                if hasattr(query_result, 'tolist'):
                    query_list = query_result.tolist()
                    query_embedding = query_list[0] if isinstance(query_list, list) and len(query_list) > 0 else query_list
                else:
                    query_embedding = [0.1] * 384  # Fallback embedding
            
            search_params = {
                "metric_type": "COSINE",
                "params": {"nprobe": 10}
            }
            
            results = self.collection.search(
                data=[query_embedding],
                anns_field="embedding",
                param=search_params,
                limit=top_k,
                expr=f'user_id == "{user_id}"',
                output_fields=["user_id", "content", "metadata", "timestamp"]
            )
            
            memories = []
            for hits in results:
                for hit in hits:
                    if hit.score >= similarity_threshold:
                        memories.append({
                            "content": hit.entity.get("content"),
                            "metadata": json.loads(hit.entity.get("metadata", "{}")),
                            "timestamp": hit.entity.get("timestamp"),
                            "similarity_score": hit.score
                        })
            
            logger.info(f"Found {len(memories)} semantic memories for user {user_id}")
            return memories
            
        except Exception as e:
            logger.error(f"Failed to search semantic memories: {e}")
            return []
    
    def get_user_memory_stats(self, user_id: str) -> Dict[str, Any]:
        """Get memory statistics for user"""
        try:
            if not self.collection:
                return {"total_memories": 0, "error": "Collection not available"}
            
            expr = f'user_id == "{user_id}"'
            results = self.collection.query(
                expr=expr,
                output_fields=["metadata", "timestamp"],
                limit=1000
            )
            
            total_memories = len(results)
            memory_types = {}
            pii_protected_count = 0
            
            for result in results:
                try:
                    metadata = json.loads(result.get("metadata", "{}"))
                    memory_type = metadata.get("type", "unknown")
                    memory_types[memory_type] = memory_types.get(memory_type, 0) + 1
                    
                    if metadata.get("pii_detected", False):
                        pii_protected_count += 1
                except:
                    pass
            
            return {
                "total_memories": total_memories,
                "memory_types": memory_types,
                "pii_protected_memories": pii_protected_count,
                "user_id": user_id
            }
            
        except Exception as e:
            logger.error(f"Failed to get user memory stats: {e}")
            return {"total_memories": 0, "error": str(e)}
    
    def delete_user_memories(self, user_id: str) -> bool:
        """Delete all memories for a user (GDPR compliance)"""
        try:
            if not self.collection:
                return False
            
            expr = f'user_id == "{user_id}"'
            self.collection.delete(expr)
            self.collection.flush()
            
            logger.info(f"Deleted all memories for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete user memories: {e}")
            return False

milvus_semantic_store = MilvusSemanticStore()
