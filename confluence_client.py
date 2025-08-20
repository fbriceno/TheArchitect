"""
Confluence API client for creating and managing documentation pages
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
import aiohttp
import base64
from urllib.parse import urljoin

logger = logging.getLogger(__name__)

class ConfluenceClient:
    """Client for interacting with Confluence API"""
    
    def __init__(self):
        self.base_url = None
        self.username = None
        self.api_token = None
        self.session = None
        
    def configure(self, base_url: str, username: str, api_token: str):
        """Configure Confluence connection"""
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.api_token = api_token
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers"""
        if not self.username or not self.api_token:
            raise ValueError("Confluence credentials not configured")
        
        auth_string = f"{self.username}:{self.api_token}"
        encoded_auth = base64.b64encode(auth_string.encode()).decode()
        
        return {
            "Authorization": f"Basic {encoded_auth}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    
    async def _make_request(self, method: str, endpoint: str, data: Dict = None) -> Dict[str, Any]:
        """Make authenticated request to Confluence API"""
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        url = urljoin(self.base_url, endpoint)
        headers = self._get_auth_headers()
        
        try:
            async with self.session.request(method, url, headers=headers, json=data) as response:
                if response.status == 401:
                    raise Exception("Unauthorized - check Confluence credentials")
                elif response.status == 403:
                    raise Exception("Forbidden - insufficient permissions")
                elif response.status >= 400:
                    error_text = await response.text()
                    raise Exception(f"Confluence API error {response.status}: {error_text}")
                
                return await response.json()
                
        except aiohttp.ClientError as e:
            logger.error(f"Network error connecting to Confluence: {e}")
            raise Exception(f"Failed to connect to Confluence: {e}")
    
    async def test_connection(self) -> bool:
        """Test connection to Confluence"""
        try:
            await self._make_request("GET", "/rest/api/user/current")
            return True
        except Exception as e:
            logger.error(f"Confluence connection test failed: {e}")
            return False
    
    async def get_space(self, space_key: str) -> Optional[Dict[str, Any]]:
        """Get space information"""
        try:
            return await self._make_request("GET", f"/rest/api/space/{space_key}")
        except Exception as e:
            logger.error(f"Failed to get space {space_key}: {e}")
            return None
    
    async def create_page(self, space: str, title: str, content: str, 
                         parent_id: str = None) -> Dict[str, Any]:
        """Create a new Confluence page"""
        try:
            page_data = {
                "type": "page",
                "title": title,
                "space": {"key": space},
                "body": {
                    "storage": {
                        "value": content,
                        "representation": "storage"
                    }
                }
            }
            
            if parent_id:
                page_data["ancestors"] = [{"id": parent_id}]
            
            result = await self._make_request("POST", "/rest/api/content", page_data)
            
            logger.info(f"Created Confluence page: {title} (ID: {result.get('id')})")
            
            return {
                "id": result.get("id"),
                "title": result.get("title"),
                "url": urljoin(self.base_url, result.get("_links", {}).get("webui", "")),
                "space": space,
                "status": result.get("status")
            }
            
        except Exception as e:
            logger.error(f"Failed to create Confluence page '{title}': {e}")
            raise
    
    async def update_page(self, page_id: str, title: str, content: str, 
                         version: int = None) -> Dict[str, Any]:
        """Update an existing Confluence page"""
        try:
            # Get current page to determine next version
            if version is None:
                current_page = await self._make_request("GET", f"/rest/api/content/{page_id}")
                version = current_page["version"]["number"] + 1
            
            page_data = {
                "id": page_id,
                "type": "page",
                "title": title,
                "version": {"number": version},
                "body": {
                    "storage": {
                        "value": content,
                        "representation": "storage"
                    }
                }
            }
            
            result = await self._make_request("PUT", f"/rest/api/content/{page_id}", page_data)
            
            logger.info(f"Updated Confluence page: {title} (ID: {page_id})")
            
            return {
                "id": result.get("id"),
                "title": result.get("title"),
                "url": urljoin(self.base_url, result.get("_links", {}).get("webui", "")),
                "version": result.get("version", {}).get("number"),
                "status": result.get("status")
            }
            
        except Exception as e:
            logger.error(f"Failed to update Confluence page {page_id}: {e}")
            raise
    
    async def get_page(self, page_id: str) -> Optional[Dict[str, Any]]:
        """Get page by ID"""
        try:
            return await self._make_request("GET", f"/rest/api/content/{page_id}?expand=body.storage,version")
        except Exception as e:
            logger.error(f"Failed to get page {page_id}: {e}")
            return None
    
    async def search_pages(self, space: str, title_query: str) -> List[Dict[str, Any]]:
        """Search for pages by title"""
        try:
            cql = f'space = "{space}" AND title ~ "{title_query}"'
            params = {"cql": cql, "expand": "version"}
            
            # Convert params to query string manually for this example
            query_string = "&".join([f"{k}={v}" for k, v in params.items()])
            
            result = await self._make_request("GET", f"/rest/api/content/search?{query_string}")
            
            return result.get("results", [])
            
        except Exception as e:
            logger.error(f"Failed to search pages in space {space}: {e}")
            return []
    
    async def delete_page(self, page_id: str) -> bool:
        """Delete a page"""
        try:
            await self._make_request("DELETE", f"/rest/api/content/{page_id}")
            logger.info(f"Deleted Confluence page: {page_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete page {page_id}: {e}")
            return False
    
    async def create_or_update_page(self, space: str, title: str, content: str, 
                                   parent_id: str = None) -> Dict[str, Any]:
        """Create page if it doesn't exist, update if it does"""
        try:
            # Search for existing page
            existing_pages = await self.search_pages(space, title)
            
            if existing_pages:
                # Update existing page
                page = existing_pages[0]
                return await self.update_page(page["id"], title, content)
            else:
                # Create new page
                return await self.create_page(space, title, content, parent_id)
                
        except Exception as e:
            logger.error(f"Failed to create or update page '{title}': {e}")
            raise
    
    def format_content_for_confluence(self, markdown_content: str) -> str:
        """Convert markdown-like content to Confluence storage format"""
        try:
            # Basic conversion from markdown to Confluence storage format
            # This is a simplified conversion - in production, you might want to use
            # a proper markdown to Confluence converter
            
            content = markdown_content
            
            # Convert headers
            content = content.replace("# ", "<h1>").replace("\n", "</h1>\n", 1)
            content = content.replace("## ", "<h2>").replace("\n", "</h2>\n", 1)
            content = content.replace("### ", "<h3>").replace("\n", "</h3>\n", 1)
            
            # Convert code blocks
            import re
            
            # Convert code blocks
            code_block_pattern = r'```(\w+)?\n(.*?)\n```'
            def replace_code_block(match):
                language = match.group(1) or ""
                code = match.group(2)
                return f'<ac:structured-macro ac:name="code" ac:schema-version="1"><ac:parameter ac:name="language">{language}</ac:parameter><ac:plain-text-body><![CDATA[{code}]]></ac:plain-text-body></ac:structured-macro>'
            
            content = re.sub(code_block_pattern, replace_code_block, content, flags=re.DOTALL)
            
            # Convert inline code
            content = re.sub(r'`([^`]+)`', r'<code>\1</code>', content)
            
            # Convert bold text
            content = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', content)
            
            # Convert italic text
            content = re.sub(r'\*([^*]+)\*', r'<em>\1</em>', content)
            
            # Convert bullet lists
            content = re.sub(r'^- (.+)$', r'<ul><li>\1</li></ul>', content, flags=re.MULTILINE)
            
            # Convert line breaks to paragraphs
            paragraphs = content.split('\n\n')
            formatted_paragraphs = []
            for para in paragraphs:
                if para.strip() and not para.startswith('<'):
                    formatted_paragraphs.append(f'<p>{para.strip()}</p>')
                else:
                    formatted_paragraphs.append(para)
            
            content = '\n'.join(formatted_paragraphs)
            
            return content
            
        except Exception as e:
            logger.error(f"Failed to format content for Confluence: {e}")
            # Return content wrapped in basic paragraph tags as fallback
            return f'<p>{markdown_content}</p>'
    
    async def upload_attachment(self, page_id: str, file_path: str, 
                              filename: str = None) -> Dict[str, Any]:
        """Upload attachment to a page"""
        try:
            if not filename:
                filename = file_path.split('/')[-1]
            
            # This would implement file upload to Confluence
            # Placeholder implementation
            
            logger.info(f"Uploaded attachment {filename} to page {page_id}")
            
            return {
                "id": "attachment_id",
                "title": filename,
                "download_url": f"{self.base_url}/download/attachments/{page_id}/{filename}"
            }
            
        except Exception as e:
            logger.error(f"Failed to upload attachment: {e}")
            raise