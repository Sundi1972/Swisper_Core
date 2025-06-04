from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility
from sentence_transformers import SentenceTransformer
import logging
from typing import List, Dict, Any, Optional
import time
import json

logger = logging.getLogger(__name__)

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
            connections.connect(
                alias="default",
                uri=self.db_path
            )
            logger.info(f"Milvus Lite connected: {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to connect to Milvus Lite: {e}")
            raise
    
    def _initialize_collection(self):
        """Initialize semantic memory collection"""
        try:
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
            raise
    
    def _initialize_embedding_model(self):
        """Initialize sentence-transformers model"""
        try:
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("Sentence-transformers model loaded")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise
    
    def add_memory(self, user_id: str, content: str, memory_type: str = "preference", metadata: Dict[str, Any] = None) -> bool:
        """Add semantic memory to Milvus store"""
        try:
            if not self.collection or not self.embedding_model:
                return False
            
            embedding = self.embedding_model.encode([content])[0].tolist()
            
            data = [{
                "user_id": user_id,
                "content": content,
                "embedding": embedding,
                "metadata": json.dumps({
                    "type": memory_type,
                    **(metadata or {})
                }),
                "timestamp": int(time.time() * 1000)
            }]
            
            self.collection.insert(data)
            self.collection.flush()
            
            logger.info(f"Added semantic memory for user {user_id}: {content[:50]}...")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add semantic memory: {e}")
            return False
    
    def search_memories(self, user_id: str, query: str, top_k: int = 3, similarity_threshold: float = 0.7) -> List[Dict[str, Any]]:
        """Search semantic memories for user"""
        try:
            if not self.collection or not self.embedding_model:
                return []
            
            query_embedding = self.embedding_model.encode([query])[0].tolist()
            
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
                return {}
            
            result = self.collection.query(
                expr=f'user_id == "{user_id}"',
                output_fields=["id"],
                limit=10000
            )
            
            return {
                "total_memories": len(result),
                "user_id": user_id
            }
            
        except Exception as e:
            logger.error(f"Failed to get memory stats: {e}")
            return {}

milvus_semantic_store = MilvusSemanticStore()
