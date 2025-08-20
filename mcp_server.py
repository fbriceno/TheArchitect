"""
MCP (Model Context Protocol) Server for exposing component documentation data
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
import json
from datetime import datetime

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from .database import DatabaseManager

logger = logging.getLogger(__name__)

class ComponentQuery(BaseModel):
    project_id: Optional[str] = None
    component_name: Optional[str] = None
    component_type: Optional[str] = None
    search_query: Optional[str] = None

class ArchitectureQuery(BaseModel):
    project_id: str
    include_diagrams: bool = True

class ProjectQuery(BaseModel):
    repo_url: Optional[str] = None
    project_name: Optional[str] = None

class MCPResponse(BaseModel):
    success: bool
    data: Any = None
    error: Optional[str] = None
    timestamp: datetime = None
    
    def __init__(self, **data):
        super().__init__(**data)
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()

class MCPServer:
    """MCP Server for exposing documentation data"""
    
    def __init__(self):
        self.app = FastAPI(
            title="Documentation MCP Server",
            description="MCP server for accessing component documentation data",
            version="1.0.0"
        )
        self.db_manager = DatabaseManager()
        self.setup_routes()
        self.setup_middleware()
    
    def setup_middleware(self):
        """Setup CORS and other middleware"""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    def setup_routes(self):
        """Setup API routes"""
        
        @self.app.on_event("startup")
        async def startup_event():
            await self.db_manager.initialize()
            logger.info("MCP Server initialized")
        
        @self.app.on_event("shutdown")
        async def shutdown_event():
            await self.db_manager.close()
            logger.info("MCP Server shutdown")
        
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint"""
            return MCPResponse(success=True, data={"status": "healthy"})
        
        @self.app.get("/mcp/projects")
        async def list_projects() -> MCPResponse:
            """List all projects"""
            try:
                # Implementation would query all projects
                return MCPResponse(success=True, data={"projects": []})
            except Exception as e:
                logger.error(f"Failed to list projects: {e}")
                return MCPResponse(success=False, error=str(e))
        
        @self.app.get("/mcp/projects/{project_id}")
        async def get_project(project_id: str) -> MCPResponse:
            """Get project details"""
            try:
                # Get project info, architecture, and components
                project_data = await self._get_complete_project_data(project_id)
                
                if not project_data:
                    raise HTTPException(status_code=404, detail="Project not found")
                
                return MCPResponse(success=True, data=project_data)
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Failed to get project {project_id}: {e}")
                return MCPResponse(success=False, error=str(e))
        
        @self.app.post("/mcp/projects/search")
        async def search_projects(query: ProjectQuery) -> MCPResponse:
            """Search projects by repo URL or name"""
            try:
                projects = []
                
                if query.repo_url:
                    project = await self.db_manager.get_project_by_repo_url(query.repo_url)
                    if project:
                        projects.append(project)
                
                # Add search by name logic if needed
                
                return MCPResponse(success=True, data={"projects": projects})
                
            except Exception as e:
                logger.error(f"Failed to search projects: {e}")
                return MCPResponse(success=False, error=str(e))
        
        @self.app.get("/mcp/projects/{project_id}/architecture")
        async def get_project_architecture(project_id: str, 
                                         include_diagrams: bool = Query(True)) -> MCPResponse:
            """Get project architecture information"""
            try:
                architecture = await self.db_manager.get_project_architecture(project_id)
                
                if not architecture:
                    raise HTTPException(status_code=404, detail="Architecture not found")
                
                if not include_diagrams:
                    architecture.pop("mermaid_diagrams", None)
                
                await self._track_mcp_request("GET", f"/mcp/projects/{project_id}/architecture")
                
                return MCPResponse(success=True, data=architecture)
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Failed to get project architecture: {e}")
                return MCPResponse(success=False, error=str(e))
        
        @self.app.get("/mcp/projects/{project_id}/components")
        async def get_project_components(project_id: str) -> MCPResponse:
            """Get all components for a project"""
            try:
                components = await self.db_manager.get_project_components(project_id)
                
                await self._track_mcp_request("GET", f"/mcp/projects/{project_id}/components")
                
                return MCPResponse(success=True, data={"components": components})
                
            except Exception as e:
                logger.error(f"Failed to get project components: {e}")
                return MCPResponse(success=False, error=str(e))
        
        @self.app.get("/mcp/projects/{project_id}/components/{component_name}")
        async def get_component(project_id: str, component_name: str) -> MCPResponse:
            """Get specific component details"""
            try:
                component = await self.db_manager.get_component_by_name(project_id, component_name)
                
                if not component:
                    raise HTTPException(status_code=404, detail="Component not found")
                
                await self._track_mcp_request("GET", f"/mcp/projects/{project_id}/components/{component_name}")
                
                return MCPResponse(success=True, data=component)
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Failed to get component: {e}")
                return MCPResponse(success=False, error=str(e))
        
        @self.app.post("/mcp/components/search")
        async def search_components(query: ComponentQuery) -> MCPResponse:
            """Search components across projects"""
            try:
                results = []
                
                if query.project_id and query.search_query:
                    components = await self.db_manager.search_components(
                        query.project_id, query.search_query
                    )
                    results.extend(components)
                
                await self._track_mcp_request("POST", "/mcp/components/search", {
                    "project_id": query.project_id,
                    "search_query": query.search_query
                })
                
                return MCPResponse(success=True, data={"components": results})
                
            except Exception as e:
                logger.error(f"Failed to search components: {e}")
                return MCPResponse(success=False, error=str(e))
        
        @self.app.get("/mcp/projects/{project_id}/statistics")
        async def get_project_statistics(project_id: str) -> MCPResponse:
            """Get project statistics"""
            try:
                stats = await self.db_manager.get_project_statistics(project_id)
                
                await self._track_mcp_request("GET", f"/mcp/projects/{project_id}/statistics")
                
                return MCPResponse(success=True, data=stats)
                
            except Exception as e:
                logger.error(f"Failed to get project statistics: {e}")
                return MCPResponse(success=False, error=str(e))
        
        @self.app.get("/mcp/agents/{agent_type}/capabilities")
        async def get_agent_capabilities(agent_type: str) -> MCPResponse:
            """Get capabilities of specific agent type"""
            try:
                capabilities = await self._get_agent_capabilities(agent_type)
                return MCPResponse(success=True, data=capabilities)
                
            except Exception as e:
                logger.error(f"Failed to get agent capabilities: {e}")
                return MCPResponse(success=False, error=str(e))
        
        @self.app.post("/mcp/documentation/generate")
        async def trigger_documentation_generation(request: Dict[str, Any]) -> MCPResponse:
            """Trigger documentation generation for new agents"""
            try:
                # This would integrate with the main documentation service
                # to trigger generation of specific sections
                
                job_id = await self._trigger_documentation_job(request)
                
                return MCPResponse(success=True, data={"job_id": job_id})
                
            except Exception as e:
                logger.error(f"Failed to trigger documentation generation: {e}")
                return MCPResponse(success=False, error=str(e))
    
    async def _get_complete_project_data(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Get complete project data including architecture and components"""
        try:
            # This would be implemented to gather all project data
            architecture = await self.db_manager.get_project_architecture(project_id)
            components = await self.db_manager.get_project_components(project_id)
            statistics = await self.db_manager.get_project_statistics(project_id)
            
            return {
                "project_id": project_id,
                "architecture": architecture,
                "components": components,
                "statistics": statistics,
                "last_updated": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get complete project data: {e}")
            return None
    
    async def _track_mcp_request(self, method: str, endpoint: str, params: Dict = None):
        """Track MCP request for analytics"""
        try:
            await self.db_manager.track_mcp_request(
                method=method,
                endpoint=endpoint,
                request_params=params or {}
            )
        except Exception as e:
            logger.error(f"Failed to track MCP request: {e}")
    
    async def _get_agent_capabilities(self, agent_type: str) -> Dict[str, Any]:
        """Get capabilities information for agent type"""
        capabilities = {
            "architecture": {
                "description": "Analyzes repository architecture and generates architectural documentation",
                "inputs": ["repository_url", "access_tokens"],
                "outputs": ["project_structure", "key_components", "architecture_patterns", "dependencies", "mermaid_diagrams"],
                "supported_languages": ["Python", "JavaScript", "TypeScript", "Java", "Go", "Rust"],
                "analysis_types": ["structure", "patterns", "dependencies", "complexity"]
            },
            "component": {
                "description": "Analyzes individual components and generates component-specific documentation", 
                "inputs": ["repository_url", "component_names", "file_patterns"],
                "outputs": ["component_details", "interfaces", "dependencies", "usage_examples"],
                "supported_formats": ["React", "Vue", "Angular", "Python modules", "Java classes"],
                "analysis_depth": ["interfaces", "dependencies", "complexity", "testing_coverage"]
            },
            "usage": {
                "description": "Generates usage guides and examples for components and APIs",
                "inputs": ["repository_url", "component_list", "api_endpoints"],
                "outputs": ["getting_started", "api_examples", "integration_guides", "troubleshooting", "best_practices"],
                "documentation_types": ["quickstart", "tutorials", "api_reference", "troubleshooting"],
                "output_formats": ["confluence", "markdown", "html"]
            }
        }
        
        return capabilities.get(agent_type, {
            "description": "Unknown agent type",
            "supported": False
        })
    
    async def _trigger_documentation_job(self, request: Dict[str, Any]) -> str:
        """Trigger a new documentation generation job"""
        # This would integrate with the main documentation service
        # to generate specific documentation sections
        
        import uuid
        job_id = str(uuid.uuid4())
        
        # Log the request for now
        logger.info(f"Documentation generation requested: {job_id}")
        logger.info(f"Request details: {request}")
        
        return job_id
    
    async def start(self, host: str = "0.0.0.0", port: int = 8003):
        """Start the MCP server"""
        config = uvicorn.Config(
            app=self.app,
            host=host,
            port=port,
            log_level="info"
        )
        server = uvicorn.Server(config)
        await server.serve()
    
    async def stop(self):
        """Stop the MCP server"""
        logger.info("MCP Server stopping...")
        # Cleanup logic here if needed