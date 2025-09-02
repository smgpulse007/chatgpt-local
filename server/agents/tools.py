import httpx
import asyncio
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime
import platform
import sys
import socket
import json
from urllib.parse import urljoin, urlparse
import re

from ddgs import DDGS
from readability import Document
from trafilatura import extract
from bs4 import BeautifulSoup

from .settings import settings
from .util import sanitize_url, is_valid_url, extract_domain, truncate_text

logger = logging.getLogger(__name__)

class ToolExecutor:
    """Base class for tool executors"""
    
    def __init__(self):
        self.http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(settings.web_timeout_seconds),
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            },
            follow_redirects=True
        )
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.http_client.aclose()

class WebSearchTool(ToolExecutor):
    """Web search using DuckDuckGo"""
    
    async def execute(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """Execute web search"""
        try:
            logger.info(f"Searching for: {query}")
            
            # Use DDGS for search
            with DDGS() as ddgs:
                results = []
                try:
                    search_results = ddgs.text(query, max_results=max_results)
                    logger.info(f"Raw search results type: {type(search_results)}")
                    
                    # Convert generator to list and process
                    search_list = list(search_results)
                    logger.info(f"Found {len(search_list)} raw results")
                    
                    for i, result in enumerate(search_list):
                        logger.info(f"Processing result {i}: {result}")
                        results.append({
                            "title": result.get("title", ""),
                            "url": result.get("href", ""),
                            "snippet": result.get("body", ""),
                            "domain": extract_domain(result.get("href", ""))
                        })
                        
                except Exception as search_error:
                    logger.error(f"Search execution error: {search_error}")
                    # Try a simpler search approach
                    try:
                        search_results = ddgs.text(f"news {query}", max_results=max_results)
                        search_list = list(search_results)
                        logger.info(f"Fallback search found {len(search_list)} results")
                        
                        for result in search_list:
                            results.append({
                                "title": result.get("title", ""),
                                "url": result.get("href", ""),
                                "snippet": result.get("body", ""),
                                "domain": extract_domain(result.get("href", ""))
                            })
                    except Exception as fallback_error:
                        logger.error(f"Fallback search also failed: {fallback_error}")
            
            logger.info(f"Final results count: {len(results)}")
            return {
                "success": True,
                "results": results,
                "query": query,
                "count": len(results)
            }
            
        except Exception as e:
            logger.error(f"Web search error: {e}")
            return {
                "success": False,
                "error": str(e),
                "results": []
            }

class WebFetchTool(ToolExecutor):
    """Fetch raw HTML from URLs"""
    
    async def execute(self, url: str) -> Dict[str, Any]:
        """Fetch HTML content from URL"""
        try:
            url = sanitize_url(url)
            if not is_valid_url(url):
                return {
                    "success": False,
                    "error": "Invalid URL format",
                    "url": url
                }
            
            logger.info(f"Fetching: {url}")
            
            response = await self.http_client.get(url)
            response.raise_for_status()
            
            content_length = len(response.content)
            max_size = settings.max_html_size_mb * 1024 * 1024
            
            if content_length > max_size:
                return {
                    "success": False,
                    "error": f"Content too large: {content_length} bytes (max: {max_size})",
                    "url": url
                }
            
            return {
                "success": True,
                "url": url,
                "status_code": response.status_code,
                "content_type": response.headers.get("content-type", ""),
                "content_length": content_length,
                "html": response.text[:50000],  # Limit HTML size
                "encoding": response.encoding
            }
            
        except httpx.RequestError as e:
            logger.error(f"Request error for {url}: {e}")
            return {
                "success": False,
                "error": f"Request failed: {str(e)}",
                "url": url
            }
        except Exception as e:
            logger.error(f"Fetch error for {url}: {e}")
            return {
                "success": False,
                "error": str(e),
                "url": url
            }

class WebReadTool(ToolExecutor):
    """Extract clean text content from web pages"""
    
    async def execute(self, url: str) -> Dict[str, Any]:
        """Extract readable content from URL"""
        try:
            url = sanitize_url(url)
            if not is_valid_url(url):
                return {
                    "success": False,
                    "error": "Invalid URL format",
                    "url": url
                }
            
            logger.info(f"Reading: {url}")
            
            # First fetch the HTML
            response = await self.http_client.get(url)
            response.raise_for_status()
            
            html = response.text
            
            # Try readability-lxml first
            extracted_content = self._extract_with_readability(html, url)
            
            # Fallback to trafilatura
            if not extracted_content.get("text"):
                extracted_content = self._extract_with_trafilatura(html, url)
            
            # Final fallback to BeautifulSoup
            if not extracted_content.get("text"):
                extracted_content = self._extract_with_bs4(html, url)
            
            # Truncate if too long
            if extracted_content.get("text"):
                extracted_content["text"] = truncate_text(
                    extracted_content["text"], 
                    max_tokens=2000
                )
            
            return {
                "success": True,
                "url": url,
                **extracted_content
            }
            
        except Exception as e:
            logger.error(f"Read error for {url}: {e}")
            return {
                "success": False,
                "error": str(e),
                "url": url
            }
    
    def _extract_with_readability(self, html: str, url: str) -> Dict[str, Any]:
        """Extract content using readability-lxml"""
        try:
            doc = Document(html)
            return {
                "title": doc.title(),
                "text": doc.summary(html_partial=False),
                "method": "readability"
            }
        except Exception as e:
            logger.debug(f"Readability extraction failed: {e}")
            return {}
    
    def _extract_with_trafilatura(self, html: str, url: str) -> Dict[str, Any]:
        """Extract content using trafilatura"""
        try:
            text = extract(html, include_links=True, include_images=False)
            if text:
                return {
                    "text": text,
                    "method": "trafilatura"
                }
        except Exception as e:
            logger.debug(f"Trafilatura extraction failed: {e}")
        return {}
    
    def _extract_with_bs4(self, html: str, url: str) -> Dict[str, Any]:
        """Extract content using BeautifulSoup as fallback"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Get title
            title = soup.title.string if soup.title else ""
            
            # Get main content
            text = soup.get_text()
            
            # Clean up text
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            return {
                "title": title.strip(),
                "text": text,
                "method": "beautifulsoup"
            }
        except Exception as e:
            logger.debug(f"BeautifulSoup extraction failed: {e}")
            return {}

class TimeNowTool(ToolExecutor):
    """Get current time"""
    
    async def execute(self) -> Dict[str, Any]:
        """Get current date and time"""
        try:
            now = datetime.now()
            return {
                "success": True,
                "timestamp": now.isoformat(),
                "utc_timestamp": datetime.utcnow().isoformat(),
                "formatted": now.strftime("%Y-%m-%d %H:%M:%S"),
                "timezone": str(now.astimezone().tzinfo)
            }
        except Exception as e:
            logger.error(f"Time error: {e}")
            return {
                "success": False,
                "error": str(e)
            }

class SystemInfoTool(ToolExecutor):
    """Get system information"""
    
    async def execute(self) -> Dict[str, Any]:
        """Get system information"""
        try:
            return {
                "success": True,
                "hostname": socket.gethostname(),
                "platform": platform.platform(),
                "system": platform.system(),
                "release": platform.release(),
                "machine": platform.machine(),
                "processor": platform.processor(),
                "python_version": sys.version,
                "python_executable": sys.executable
            }
        except Exception as e:
            logger.error(f"System info error: {e}")
            return {
                "success": False,
                "error": str(e)
            }

# Tool registry
TOOL_REGISTRY = {
    "web_search": WebSearchTool,
    "web_fetch": WebFetchTool,
    "web_read": WebReadTool,
    "time_now": TimeNowTool,
    "system_info": SystemInfoTool
}

async def execute_tool(tool_name: str, **kwargs) -> Dict[str, Any]:
    """Execute a tool by name"""
    if tool_name not in TOOL_REGISTRY:
        return {
            "success": False,
            "error": f"Unknown tool: {tool_name}"
        }
    
    tool_class = TOOL_REGISTRY[tool_name]
    async with tool_class() as tool:
        return await tool.execute(**kwargs)
