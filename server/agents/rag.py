import chromadb
from chromadb.config import Settings as ChromaSettings
import asyncio
import logging
from typing import List, Dict, Any, Optional
import uuid
import json
import os
from sentence_transformers import SentenceTransformer
import aiofiles
from pathlib import Path

from .settings import settings

logger = logging.getLogger(__name__)

class RAGManager:
    """RAG (Retrieval Augmented Generation) manager using ChromaDB"""
    
    def __init__(self):
        self.chroma_client = None
        self.collection = None
        self.embedding_model = None
        self.initialized = False
    
    async def initialize(self):
        """Initialize ChromaDB and embedding model"""
        try:
            # Ensure ChromaDB directory exists
            os.makedirs(settings.chromadb_path, exist_ok=True)
            
            # Initialize ChromaDB client
            self.chroma_client = chromadb.PersistentClient(
                path=settings.chromadb_path,
                settings=ChromaSettings(anonymized_telemetry=False)
            )
            
            # Get or create collection
            self.collection = self.chroma_client.get_or_create_collection(
                name="documents",
                metadata={"description": "Local document collection for RAG"}
            )
            
            # Initialize embedding model
            self.embedding_model = SentenceTransformer(settings.embedding_model)
            
            self.initialized = True
            logger.info("RAG system initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize RAG system: {e}")
            self.initialized = False
    
    async def ingest_text(self, text: str, metadata: Dict[str, Any] = None) -> str:
        """Ingest text content into the vector store"""
        if not self.initialized:
            await self.initialize()
        
        try:
            # Chunk the text
            chunks = self._chunk_text(text)
            
            # Generate embeddings
            embeddings = self.embedding_model.encode(chunks).tolist()
            
            # Generate unique IDs
            chunk_ids = [str(uuid.uuid4()) for _ in chunks]
            
            # Prepare metadata
            metadata = metadata or {}
            metadatas = []
            for i, chunk in enumerate(chunks):
                chunk_metadata = {
                    **metadata,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "text_length": len(chunk)
                }
                metadatas.append(chunk_metadata)
            
            # Add to collection
            self.collection.add(
                ids=chunk_ids,
                documents=chunks,
                embeddings=embeddings,
                metadatas=metadatas
            )
            
            logger.info(f"Ingested {len(chunks)} chunks into RAG system")
            return f"Successfully ingested {len(chunks)} text chunks"
            
        except Exception as e:
            logger.error(f"Text ingestion error: {e}")
            return f"Failed to ingest text: {str(e)}"
    
    async def ingest_file(self, file_path: str, content: bytes = None) -> str:
        """Ingest a file into the vector store"""
        if not self.initialized:
            await self.initialize()
        
        try:
            file_path = Path(file_path)
            
            # Read file content if not provided
            if content is None:
                if not file_path.exists():
                    return f"File not found: {file_path}"
                
                async with aiofiles.open(file_path, 'rb') as f:
                    content = await f.read()
            
            # Extract text based on file type
            text = await self._extract_text_from_file(file_path, content)
            
            if not text:
                return f"Could not extract text from file: {file_path}"
            
            # Prepare metadata
            metadata = {
                "source_file": str(file_path),
                "file_name": file_path.name,
                "file_size": len(content),
                "file_type": file_path.suffix.lower()
            }
            
            # Ingest the text
            result = await self.ingest_text(text, metadata)
            
            return f"File {file_path.name}: {result}"
            
        except Exception as e:
            logger.error(f"File ingestion error: {e}")
            return f"Failed to ingest file: {str(e)}"
    
    async def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Search the vector store for relevant documents"""
        if not self.initialized:
            await self.initialize()
        
        try:
            # Generate query embedding
            query_embedding = self.embedding_model.encode([query]).tolist()[0]
            
            # Search the collection
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=max_results,
                include=["documents", "metadatas", "distances"]
            )
            
            # Format results
            formatted_results = []
            for i in range(len(results["documents"][0])):
                formatted_results.append({
                    "content": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "similarity": 1 - results["distances"][0][i]  # Convert distance to similarity
                })
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Search error: {e}")
            return []
    
    async def doc_search_tool(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """Tool function for document search"""
        try:
            results = await self.search(query, max_results)
            
            return {
                "success": True,
                "query": query,
                "results": results,
                "count": len(results)
            }
            
        except Exception as e:
            logger.error(f"Document search tool error: {e}")
            return {
                "success": False,
                "error": str(e),
                "results": []
            }
    
    def _chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 100) -> List[str]:
        """Split text into overlapping chunks"""
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            
            # Try to end on sentence boundary
            if end < len(text):
                last_period = chunk.rfind('.')
                last_newline = chunk.rfind('\n')
                boundary = max(last_period, last_newline)
                
                if boundary > start + chunk_size // 2:
                    chunk = text[start:start + boundary + 1]
                    end = start + boundary + 1
            
            chunks.append(chunk.strip())
            start = end - overlap
            
            if start >= len(text):
                break
        
        return [chunk for chunk in chunks if chunk]
    
    async def _extract_text_from_file(self, file_path: Path, content: bytes) -> str:
        """Extract text from different file types"""
        file_type = file_path.suffix.lower()
        
        try:
            if file_type in ['.txt', '.md', '.py', '.js', '.html', '.css', '.json']:
                # Text files - decode as UTF-8
                return content.decode('utf-8', errors='ignore')
            
            elif file_type == '.pdf':
                # PDF files - would need PyPDF2 or similar
                # For now, return placeholder
                return f"[PDF file: {file_path.name} - PDF parsing not implemented yet]"
            
            elif file_type in ['.doc', '.docx']:
                # Word documents - would need python-docx
                return f"[Word document: {file_path.name} - Word parsing not implemented yet]"
            
            else:
                # Unknown file type
                return f"[Unknown file type: {file_path.name}]"
                
        except Exception as e:
            logger.error(f"Text extraction error for {file_path}: {e}")
            return ""
    
    async def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the document collection"""
        if not self.initialized:
            await self.initialize()
        
        try:
            count = self.collection.count()
            return {
                "total_documents": count,
                "collection_name": self.collection.name,
                "embedding_model": settings.embedding_model
            }
        except Exception as e:
            logger.error(f"Error getting collection stats: {e}")
            return {"error": str(e)}

# Global RAG manager instance
rag_manager = RAGManager()

# Tool function for agent integration
async def doc_search(query: str, max_results: int = 5) -> Dict[str, Any]:
    """Document search tool for the agent"""
    return await rag_manager.doc_search_tool(query, max_results)
