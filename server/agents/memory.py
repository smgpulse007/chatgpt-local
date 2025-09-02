import aiosqlite
import asyncio
import json
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
import logging

from .settings import settings

logger = logging.getLogger(__name__)

class ConversationManager:
    """Manages conversations and messages in SQLite database"""
    
    def __init__(self):
        self.db_path = settings.database_path
    
    async def initialize(self):
        """Initialize database with required tables"""
        async with aiosqlite.connect(self.db_path) as db:
            # Create conversations table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    summary TEXT,
                    metadata TEXT DEFAULT '{}'
                )
            """)
            
            # Create messages table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT DEFAULT '{}',
                    FOREIGN KEY (conversation_id) REFERENCES conversations (id) ON DELETE CASCADE
                )
            """)
            
            # Create indexes
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_conversation_id 
                ON messages(conversation_id)
            """)
            
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_created_at 
                ON messages(created_at)
            """)
            
            await db.commit()
            logger.info("Database initialized successfully")
    
    async def create_conversation(self, title: str, summary: str = "") -> str:
        """Create a new conversation"""
        conversation_id = str(uuid.uuid4())
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO conversations (id, title, summary)
                VALUES (?, ?, ?)
            """, (conversation_id, title, summary))
            await db.commit()
        
        logger.info(f"Created conversation: {conversation_id}")
        return conversation_id
    
    async def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get conversation by ID"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM conversations WHERE id = ?
            """, (conversation_id,))
            row = await cursor.fetchone()
            
            if row:
                return {
                    "id": row["id"],
                    "title": row["title"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                    "summary": row["summary"],
                    "metadata": json.loads(row["metadata"] or "{}")
                }
        return None
    
    async def list_conversations(self, limit: int = 50) -> List[Dict[str, Any]]:
        """List conversations ordered by last update"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT c.*, COUNT(m.id) as message_count
                FROM conversations c
                LEFT JOIN messages m ON c.id = m.conversation_id
                GROUP BY c.id
                ORDER BY c.updated_at DESC
                LIMIT ?
            """, (limit,))
            rows = await cursor.fetchall()
            
            conversations = []
            for row in rows:
                conversations.append({
                    "id": row["id"],
                    "title": row["title"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                    "message_count": row["message_count"],
                    "summary": row["summary"]
                })
            
            return conversations
    
    async def add_message(self, conversation_id: str, role: str, content: str, 
                         metadata: Dict[str, Any] = None) -> str:
        """Add a message to a conversation"""
        message_id = str(uuid.uuid4())
        metadata = metadata or {}
        
        async with aiosqlite.connect(self.db_path) as db:
            # Insert message
            await db.execute("""
                INSERT INTO messages (id, conversation_id, role, content, metadata)
                VALUES (?, ?, ?, ?, ?)
            """, (message_id, conversation_id, role, content, json.dumps(metadata)))
            
            # Update conversation timestamp
            await db.execute("""
                UPDATE conversations 
                SET updated_at = CURRENT_TIMESTAMP 
                WHERE id = ?
            """, (conversation_id,))
            
            await db.commit()
        
        return message_id
    
    async def get_messages(self, conversation_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get messages for a conversation"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM messages 
                WHERE conversation_id = ?
                ORDER BY created_at ASC
                LIMIT ?
            """, (conversation_id, limit))
            rows = await cursor.fetchall()
            
            messages = []
            for row in rows:
                messages.append({
                    "id": row["id"],
                    "role": row["role"],
                    "content": row["content"],
                    "created_at": row["created_at"],
                    "metadata": json.loads(row["metadata"] or "{}")
                })
            
            return messages
    
    async def delete_conversation(self, conversation_id: str):
        """Delete a conversation and all its messages"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
            await db.commit()
        
        logger.info(f"Deleted conversation: {conversation_id}")
    
    async def update_conversation_summary(self, conversation_id: str, summary: str):
        """Update conversation summary"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE conversations 
                SET summary = ?, updated_at = CURRENT_TIMESTAMP 
                WHERE id = ?
            """, (summary, conversation_id))
            await db.commit()
    
    async def get_conversation_context(self, conversation_id: str, 
                                     max_messages: int = 20) -> Dict[str, Any]:
        """Get conversation context for the agent"""
        conversation = await self.get_conversation(conversation_id)
        if not conversation:
            return {"conversation": None, "messages": [], "summary": ""}
        
        messages = await self.get_messages(conversation_id, limit=max_messages)
        
        return {
            "conversation": conversation,
            "messages": messages,
            "summary": conversation.get("summary", "")
        }
    
    async def create_memory_summary(self, conversation_id: str, 
                                  max_tokens: int = 500) -> str:
        """Create a memory summary for the conversation"""
        try:
            context = await self.get_conversation_context(conversation_id)
            messages = context["messages"]
            
            if not messages:
                return ""
            
            # Extract key information from conversation
            user_messages = [msg for msg in messages if msg["role"] == "user"]
            assistant_messages = [msg for msg in messages if msg["role"] == "assistant"]
            
            summary_parts = []
            
            # User preferences and patterns
            if user_messages:
                recent_topics = [msg["content"][:100] for msg in user_messages[-3:]]
                summary_parts.append(f"Recent topics: {'; '.join(recent_topics)}")
            
            # Key assistant responses
            if assistant_messages:
                key_responses = [msg["content"][:100] for msg in assistant_messages[-2:]]
                summary_parts.append(f"Key responses: {'; '.join(key_responses)}")
            
            summary = " | ".join(summary_parts)
            
            # Truncate if too long
            if len(summary) > max_tokens * 4:  # Rough token estimate
                summary = summary[:max_tokens * 4] + "..."
            
            # Save summary
            await self.update_conversation_summary(conversation_id, summary)
            
            return summary
            
        except Exception as e:
            logger.error(f"Error creating memory summary: {e}")
            return ""
