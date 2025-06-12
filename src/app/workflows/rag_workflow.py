from typing import Dict, Any, List, Optional
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
import logging
from ..models import DocumentQuery, DocumentResponse
from ..config import settings

logger = logging.getLogger(__name__)

class RAGWorkflow:
    """
    RAG (Retrieval-Augmented Generation) workflow using LangChain.
    Replaces the original Haystack RAG pipeline with modern LangChain components.
    """
    
    def __init__(self):
        if settings.openai_api_key and settings.openai_api_key != "your_openai_api_key_here":
            self.llm = ChatOpenAI(
                model=settings.openai_model,
                api_key=settings.openai_api_key,
                temperature=0.1
            )
            
            self.embeddings = OpenAIEmbeddings(
                api_key=settings.openai_api_key
            )
            
            self.vector_store = None
            self._initialize_mock_documents()
            
            self.rag_prompt = ChatPromptTemplate.from_messages([
                ("system", """You are a helpful assistant that answers questions based on the provided context documents.

Instructions:
- Use ONLY the information from the provided context to answer questions
- If the context doesn't contain enough information, say "I don't have enough information in the provided documents to answer that question"
- Be precise and cite specific parts of the context when possible
- If asked about contracts, policies, or agreements, be especially careful to quote exact terms

Context Documents:
{context}"""),
                ("user", "Question: {question}")
            ])
            
            self.rag_chain = self.rag_prompt | self.llm | StrOutputParser()
        else:
            self.llm = None
            self.embeddings = None
            self.vector_store = None
            self.rag_prompt = None
            self.rag_chain = None
            logger.warning("RAG workflow initialized without OpenAI API key - some features will be disabled")
    
    def _initialize_mock_documents(self):
        """Initialize with mock documents for demonstration."""
        try:
            if not self.embeddings:
                logger.info("Skipping mock document initialization - no embeddings available")
                return
                
            mock_documents = [
                Document(
                    page_content="""
                    SWISPER AI ASSISTANT SERVICE AGREEMENT
                    
                    1. SERVICE DESCRIPTION
                    Swisper provides an AI-powered assistant service that helps users with:
                    - Product search and purchase recommendations
                    - Document analysis and question answering
                    - General conversation and information retrieval
                    
                    2. USER RESPONSIBILITIES
                    Users must provide accurate information and use the service responsibly.
                    Users are responsible for verifying product information before making purchases.
                    
                    3. PRIVACY POLICY
                    We collect and store conversation data to improve service quality.
                    Personal information is encrypted and not shared with third parties.
                    Users can request data deletion at any time.
                    
                    4. LIMITATION OF LIABILITY
                    Swisper is not responsible for purchase decisions made based on AI recommendations.
                    The service is provided "as is" without warranties.
                    """,
                    metadata={"source": "service_agreement.pdf", "type": "contract"}
                ),
                Document(
                    page_content="""
                    PRODUCT RECOMMENDATION POLICY
                    
                    Our AI assistant uses the following criteria for product recommendations:
                    
                    1. RELEVANCE SCORING
                    - Products are scored based on query matching (40%)
                    - User preference history (30%)
                    - Product ratings and reviews (20%)
                    - Price competitiveness (10%)
                    
                    2. RANKING ALGORITHM
                    The system ranks products using a weighted scoring system.
                    Higher-rated products with more reviews are preferred.
                    Price is considered but not the primary factor.
                    
                    3. QUALITY ASSURANCE
                    All recommended products must have:
                    - Minimum 3.5-star rating
                    - At least 10 customer reviews
                    - Valid product information and pricing
                    
                    4. DISCLAIMER
                    Recommendations are AI-generated and should be verified by users.
                    Prices and availability may change without notice.
                    """,
                    metadata={"source": "recommendation_policy.pdf", "type": "policy"}
                ),
                Document(
                    page_content="""
                    TECHNICAL ARCHITECTURE DOCUMENTATION
                    
                    SYSTEM COMPONENTS:
                    
                    1. INTENT DETECTION
                    - Hybrid keyword + LLM classification
                    - Supports: contract, rag, websearch, chat intents
                    - Uses GPT-4o for final classification
                    
                    2. CONTRACT WORKFLOW
                    - LangGraph-based state machine
                    - States: search → rank → present → confirm → complete
                    - Integrates with product search APIs
                    
                    3. RAG SYSTEM
                    - OpenAI embeddings for document vectorization
                    - FAISS vector store for similarity search
                    - Context-aware answer generation
                    
                    4. SESSION MANAGEMENT
                    - In-memory storage for development
                    - Redis recommended for production
                    - Automatic cleanup of expired sessions
                    """,
                    metadata={"source": "technical_docs.md", "type": "documentation"}
                )
            ]
            
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200,
                length_function=len
            )
            
            split_docs = text_splitter.split_documents(mock_documents)
            
            self.vector_store = FAISS.from_documents(split_docs, self.embeddings)
            
            logger.info(f"Initialized RAG with {len(split_docs)} document chunks")
            
        except Exception as e:
            logger.error(f"Error initializing mock documents: {e}", exc_info=True)
            self.vector_store = None
    
    async def process_query(self, query: DocumentQuery) -> DocumentResponse:
        """
        Process a RAG query and return an answer with sources.
        
        Args:
            query: DocumentQuery containing the question and session info
            
        Returns:
            DocumentResponse with answer and source citations
        """
        try:
            logger.info(f"Processing RAG query: {query.question[:100]}...")
            
            if not self.llm or not self.embeddings or not self.vector_store or not self.rag_chain:
                return DocumentResponse(
                    answer="RAG system requires a valid OpenAI API key to function. Please configure your API key in the .env file.",
                    sources=[],
                    confidence=0.0
                )
            
            relevant_docs = self.vector_store.similarity_search(
                query.question,
                k=query.context_limit
            )
            
            if not relevant_docs:
                return DocumentResponse(
                    answer="I couldn't find any relevant documents to answer your question.",
                    sources=[],
                    confidence=0.0
                )
            
            context = self._format_context(relevant_docs)
            
            answer = await self.rag_chain.ainvoke({
                "context": context,
                "question": query.question
            })
            
            sources = [doc.metadata.get("source", "Unknown") for doc in relevant_docs]
            
            confidence = self._calculate_confidence(relevant_docs, query.question)
            
            logger.info(f"RAG query processed successfully with {len(sources)} sources")
            
            return DocumentResponse(
                answer=answer,
                sources=list(set(sources)),  # Remove duplicates
                confidence=confidence
            )
            
        except Exception as e:
            logger.error(f"Error processing RAG query: {e}", exc_info=True)
            return DocumentResponse(
                answer=f"I encountered an error while processing your question: {str(e)}",
                sources=[],
                confidence=0.0
            )
    
    def _format_context(self, documents: List[Document]) -> str:
        """Format retrieved documents as context for the LLM."""
        context_parts = []
        
        for i, doc in enumerate(documents, 1):
            source = doc.metadata.get("source", "Unknown")
            doc_type = doc.metadata.get("type", "document")
            
            context_parts.append(
                f"Document {i} ({doc_type} - {source}):\n{doc.page_content}\n"
            )
        
        return "\n---\n".join(context_parts)
    
    def _calculate_confidence(self, documents: List[Document], question: str) -> float:
        """Calculate confidence score based on retrieval quality."""
        if not documents:
            return 0.0
        
        base_confidence = min(len(documents) / 5.0, 1.0)  # More docs = higher confidence
        
        question_terms = set(question.lower().split())
        content_terms = set()
        
        for doc in documents:
            content_terms.update(doc.page_content.lower().split())
        
        term_overlap = len(question_terms.intersection(content_terms)) / len(question_terms)
        
        final_confidence = (base_confidence + term_overlap) / 2.0
        return min(final_confidence, 1.0)
    
    async def add_document(self, content: str, metadata: Dict[str, Any]) -> bool:
        """Add a new document to the RAG system."""
        try:
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200
            )
            
            doc = Document(page_content=content, metadata=metadata)
            chunks = text_splitter.split_documents([doc])
            
            if self.vector_store:
                self.vector_store.add_documents(chunks)
            else:
                self.vector_store = FAISS.from_documents(chunks, self.embeddings)
            
            logger.info(f"Added document with {len(chunks)} chunks to RAG system")
            return True
            
        except Exception as e:
            logger.error(f"Error adding document to RAG: {e}", exc_info=True)
            return False
    
    async def search_documents(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search for documents similar to the query."""
        try:
            if not self.vector_store:
                return []
            
            docs = self.vector_store.similarity_search(query, k=limit)
            
            return [
                {
                    "content": doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content,
                    "metadata": doc.metadata,
                    "source": doc.metadata.get("source", "Unknown")
                }
                for doc in docs
            ]
            
        except Exception as e:
            logger.error(f"Error searching documents: {e}", exc_info=True)
            return []

rag_workflow = RAGWorkflow()
