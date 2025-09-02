import httpx
import json
import asyncio
import logging
import re
from typing import List, Dict, Any, AsyncGenerator, Optional
import uuid

from .settings import settings
from .schemas import Message, TOOL_DEFINITIONS
from .tools import execute_tool
from .memory import ConversationManager
from .util import create_sse_data, parse_tool_calls

logger = logging.getLogger(__name__)

class Agent:
    """Main agent class that handles tool-calling and LLM interaction"""
    
    def __init__(self):
        self.http_client = httpx.AsyncClient(timeout=httpx.Timeout(30.0))
        self.conversation_manager = ConversationManager()
        self.system_prompt = self._get_system_prompt()
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for the agent"""
        return """You are Local ChatGPT running on the user's machine via Ollama.

CRITICAL INSTRUCTIONS FOR WEB BROWSING:
- When you receive web search results, you MUST synthesize them into a clear, informative response
- NEVER just repeat the raw search results or JSON data
- Always provide a well-formatted summary with key information
- Include relevant URLs when citing sources

When enable_browsing=true:
- If user asks for current/external info, use web_search tool first
- After receiving search results, write a comprehensive answer based on the results
- Format your response with clear sections and bullet points when appropriate
- Cite sources using the provided URLs

Available tools when enable_browsing=true:
- web_search(query, max_results=5): Search the web for current information
- web_read(url): Read and extract text from a webpage
- web_fetch(url): Get raw HTML from a URL
- time_now(): Get current date and time
- system_info(): Get system information

Example of good response formatting:
"Based on the latest search results, here are the key updates:

• **Topic 1**: Description with relevant details
• **Topic 2**: Another important update
• **Topic 3**: Additional information

Sources: [Title](URL), [Title](URL)"

REMEMBER: Always provide helpful, well-formatted responses that synthesize the search results into useful information for the user."""

    async def run_streaming(
        self,
        messages: List[Message],
        conversation_id: Optional[str] = None,
        enable_browsing: bool = False,
        system: Optional[str] = None,
        temperature: float = 0.7,
        model: str = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Run agent with streaming response"""
        
        model = model or settings.model_id
        system_prompt = system or self.system_prompt
        
        # Add browsing context to system prompt
        if enable_browsing:
            system_prompt += f"\n\nBrowsing is ENABLED. You have access to these tools: {[tool['function']['name'] for tool in TOOL_DEFINITIONS]}"
            logger.info(f"BROWSING ENABLED - Enhanced system prompt active")
        else:
            system_prompt += "\n\nBrowsing is DISABLED. You cannot access web tools."
            logger.info(f"BROWSING DISABLED")
        
        # Convert messages to Ollama format
        formatted_messages = await self._format_messages_for_ollama(
            messages, system_prompt, conversation_id
        )
        
        max_iterations = 5
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            
            try:
                # Call Ollama
                response_content = ""
                tool_calls = []
                
                async for chunk in self._call_ollama_streaming(
                    formatted_messages, model, temperature
                ):
                    if chunk.get("type") == "token":
                        content = chunk.get("content", "")
                        response_content += content
                        yield chunk
                    elif chunk.get("type") == "error":
                        yield chunk
                        return
                
                # Check for tool calls in response
                if enable_browsing:
                    tool_calls = self._extract_tool_calls(response_content)
                    logger.info(f"TOOL EXTRACTION: Found {len(tool_calls)} tool calls in response")
                    
                    # Fallback: if browsing enabled but no tools called and user asks for current info
                    if not tool_calls and iteration == 1:
                        user_message = messages[-1].content.lower() if messages else ""
                        logger.info(f"FALLBACK CHECK: User message = '{user_message}'")
                        
                        # More comprehensive keyword detection
                        trigger_keywords = [
                            "current", "latest", "recent", "today", "news", "search", 
                            "what's", "what is", "happening", "update", "browse",
                            "world", "events", "now", "information", "find", "look up"
                        ]
                        
                        keyword_found = any(keyword in user_message for keyword in trigger_keywords)
                        logger.info(f"FALLBACK: Keyword found = {keyword_found}")
                        
                        if keyword_found:
                            logger.info(f"FALLBACK TRIGGERED: Auto-calling web_search for: {user_message}")
                            # Force a web search
                            search_query = messages[-1].content if messages else "current information"
                            tool_calls = [{
                                "name": "web_search",
                                "arguments": {"query": search_query, "max_results": 5}
                            }]
                            yield {
                                "type": "token",
                                "content": "\n\n[Auto-triggering web search for current information...]\n\n"
                            }
                
                if not tool_calls:
                    # No tool calls, we're done
                    break
                
                # Execute tool calls
                for tool_call in tool_calls:
                    yield {
                        "type": "tool_call",
                        "tool_name": tool_call["name"],
                        "arguments": tool_call["arguments"]
                    }
                    
                    # Execute the tool
                    result = await execute_tool(
                        tool_call["name"], 
                        **tool_call["arguments"]
                    )
                    
                    yield {
                        "type": "tool_result",
                        "tool_name": tool_call["name"],
                        "result": result
                    }
                    
                    # Add tool result to messages
                    formatted_messages.append({
                        "role": "assistant",
                        "content": response_content
                    })
                    
                    # Format tool result for better processing by LLM
                    if tool_call["name"] == "web_search" and isinstance(result, dict) and result.get("success"):
                        # Format search results nicely for LLM processing
                        search_results = result.get("results", [])
                        if search_results:
                            formatted_result = f"""You have successfully searched for '{tool_call['arguments'].get('query', '')}' and found {len(search_results)} results. Here are the search results:

"""
                            for i, item in enumerate(search_results[:5], 1):
                                formatted_result += f"{i}. **{item.get('title', 'No title')}**\n"
                                formatted_result += f"   URL: {item.get('url', 'No URL')}\n"
                                formatted_result += f"   Summary: {item.get('snippet', 'No description')}\n\n"
                            
                            formatted_result += """Now, based on these search results, please provide a comprehensive, well-formatted response to the user's question. 

Your response should:
- Synthesize the key information from the search results
- Use clear formatting with bullet points or sections
- Include relevant source citations
- Be informative and helpful
- NOT just repeat the raw search data

Please write your response now:"""
                        else:
                            formatted_result = f"Web search for '{tool_call['arguments'].get('query', '')}' returned no results. This might be due to search limitations or network issues. Please inform the user that current information search is temporarily unavailable and suggest they try again later or check news websites directly."
                    else:
                        # For other tools or failed searches, use the original format
                        formatted_result = f"Tool result for {tool_call['name']}: {json.dumps(result, indent=2)}"
                    
                    formatted_messages.append({
                        "role": "user",
                        "content": formatted_result
                    })
                
                # Clear response content for next iteration
                response_content = ""
                
            except Exception as e:
                logger.error(f"Agent error in iteration {iteration}: {e}")
                yield {
                    "type": "error",
                    "content": f"An error occurred: {str(e)}"
                }
                return
        
        if iteration >= max_iterations:
            yield {
                "type": "token",
                "content": "\n\n[Note: Reached maximum tool calling iterations]"
            }
    
    async def _format_messages_for_ollama(
        self, 
        messages: List[Message], 
        system_prompt: str,
        conversation_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Format messages for Ollama API"""
        
        formatted = []
        
        # Add system message
        formatted.append({
            "role": "system",
            "content": system_prompt
        })
        
        # Add conversation memory if available
        if conversation_id:
            try:
                context = await self.conversation_manager.get_conversation_context(conversation_id)
                if context["summary"]:
                    formatted.append({
                        "role": "system", 
                        "content": f"Previous conversation context: {context['summary']}"
                    })
            except Exception as e:
                logger.warning(f"Could not load conversation context: {e}")
        
        # Add user messages
        for msg in messages:
            formatted.append({
                "role": msg.role,
                "content": msg.content
            })
        
        return formatted
    
    async def _call_ollama_streaming(
        self,
        messages: List[Dict[str, Any]],
        model: str,
        temperature: float
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Call Ollama with streaming"""
        
        try:
            payload = {
                "model": model,
                "messages": messages,
                "stream": True,
                "options": {
                    "temperature": temperature
                }
            }
            
            async with self.http_client.stream(
                "POST",
                f"{settings.ollama_url}/api/chat",
                json=payload
            ) as response:
                
                if response.status_code != 200:
                    yield {
                        "type": "error",
                        "content": f"Ollama API error: {response.status_code}"
                    }
                    return
                
                async for line in response.aiter_lines():
                    if line.strip():
                        try:
                            data = json.loads(line)
                            
                            if "message" in data:
                                content = data["message"].get("content", "")
                                if content:
                                    yield {
                                        "type": "token",
                                        "content": content
                                    }
                            
                            if data.get("done", False):
                                break
                                
                        except json.JSONDecodeError:
                            continue
                            
        except Exception as e:
            logger.error(f"Ollama streaming error: {e}")
            yield {
                "type": "error",
                "content": f"Failed to connect to Ollama: {str(e)}"
            }
    
    def _extract_tool_calls(self, content: str) -> List[Dict[str, Any]]:
        """Extract tool calls from LLM response with multiple parsing strategies"""
        tool_calls = []
        
        try:
            # Strategy 1: OpenAI-style function calling JSON
            tool_pattern = r'\{"tool":\s*"([^"]+)",\s*"arguments":\s*(\{[^}]*\})\s*\}'
            matches = re.findall(tool_pattern, content)
            for match in matches:
                tool_name = match[0]
                try:
                    arguments = json.loads(match[1])
                    tool_calls.append({
                        "name": tool_name,
                        "arguments": arguments
                    })
                except json.JSONDecodeError:
                    continue
            
            # Strategy 2: Legacy format
            if not tool_calls:
                legacy_pattern = r'\{"tool_call":\s*\{"name":\s*"([^"]+)",\s*"arguments":\s*(\{[^}]*\})\s*\}\s*\}'
                matches = re.findall(legacy_pattern, content)
                for match in matches:
                    tool_name = match[0]
                    try:
                        arguments = json.loads(match[1])
                        tool_calls.append({
                            "name": tool_name,
                            "arguments": arguments
                        })
                    except json.JSONDecodeError:
                        continue
            
            # Strategy 3: Fenced JSON blocks
            if not tool_calls:
                json_blocks = re.findall(r'```json\s*(\{[^`]*\})\s*```', content, re.MULTILINE)
                for block in json_blocks:
                    try:
                        data = json.loads(block)
                        if "tool" in data and "arguments" in data:
                            tool_calls.append({
                                "name": data["tool"],
                                "arguments": data["arguments"]
                            })
                    except json.JSONDecodeError:
                        continue
            
            # Strategy 4: Direct function calls
            if not tool_calls:
                function_patterns = [
                    (r'web_search\(["\']([^"\']+)["\'](?:,\s*(\d+))?\)', lambda m: {
                        "name": "web_search", 
                        "arguments": {
                            "query": m.group(1), 
                            "max_results": int(m.group(2)) if m.group(2) else 5
                        }
                    }),
                    (r'web_read\(["\']([^"\']+)["\']\)', lambda m: {
                        "name": "web_read", 
                        "arguments": {"url": m.group(1)}
                    }),
                    (r'web_fetch\(["\']([^"\']+)["\']\)', lambda m: {
                        "name": "web_fetch", 
                        "arguments": {"url": m.group(1)}
                    }),
                    (r'time_now\(\)', lambda m: {
                        "name": "time_now", 
                        "arguments": {}
                    }),
                    (r'system_info\(\)', lambda m: {
                        "name": "system_info", 
                        "arguments": {}
                    }),
                ]
                
                for pattern, builder in function_patterns:
                    matches = re.finditer(pattern, content)
                    for match in matches:
                        tool_calls.append(builder(match))
        
        except Exception as e:
            logger.debug(f"Tool call extraction error: {e}")
        
        return tool_calls
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.http_client.aclose()
