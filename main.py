"""
Confluence Documentation Generator
Generates architecture and component usage documentation for Confluence
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from pathlib import Path
import json
from datetime import datetime

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from .agents import ArchitectureAgent, ComponentAgent, UsageAgent
from .database import DatabaseManager
from .mcp_server import MCPServer
from .confluence_client import ConfluenceClient
from .markdown_exporter import MarkdownExporter

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Confluence Documentation Generator", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
db_manager = DatabaseManager()
mcp_server = MCPServer()
confluence_client = ConfluenceClient()
markdown_exporter = MarkdownExporter()

@dataclass
class DocumentationRequest:
    repo_url: str
    confluence_space: Optional[str]
    project_name: str
    components: List[str]
    export_format: str = "confluence"
    output_dir: Optional[str] = None
    
class DocumentationRequestModel(BaseModel):
    repo_url: str
    confluence_space: Optional[str] = None
    project_name: str
    components: List[str] = []
    export_format: str = "confluence"  # "confluence", "markdown", or "both"
    output_dir: Optional[str] = None

@dataclass
class DocumentationResult:
    id: str
    status: str
    confluence_pages: List[Dict[str, Any]]
    markdown_files: Optional[Dict[str, Any]] = None
    generated_at: datetime = None
    agents_results: Dict[str, Any] = None

class DocumentationService:
    def __init__(self):
        self.active_jobs = {}
        
    async def generate_documentation(self, request: DocumentationRequest) -> str:
        """Generate documentation using parallel agents"""
        job_id = f"doc_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        self.active_jobs[job_id] = {
            "status": "running",
            "started_at": datetime.now(),
            "request": request
        }
        
        try:
            # Initialize agents
            architecture_agent = ArchitectureAgent()
            component_agent = ComponentAgent()
            usage_agent = UsageAgent()
            
            # Run agents in parallel
            tasks = [
                architecture_agent.analyze_repository(request.repo_url),
                component_agent.analyze_components(request.repo_url, request.components),
                usage_agent.generate_usage_docs(request.repo_url, request.components)
            ]
            
            architecture_result, components_result, usage_result = await asyncio.gather(*tasks)
            
            # Store results in database
            await self._store_results(job_id, {
                "architecture": architecture_result,
                "components": components_result,
                "usage": usage_result
            })
            
            # Generate output based on format
            confluence_pages = []
            markdown_files = None
            
            if request.export_format in ["confluence", "both"]:
                if request.confluence_space:
                    confluence_pages = await self._create_confluence_pages(
                        request, architecture_result, components_result, usage_result
                    )
                else:
                    logger.warning("Confluence space not specified, skipping Confluence export")
            
            if request.export_format in ["markdown", "both"]:
                # Set up markdown exporter with custom output directory if specified
                if request.output_dir:
                    exporter = MarkdownExporter(request.output_dir)
                else:
                    exporter = markdown_exporter
                
                markdown_files = await exporter.export_project_documentation(
                    request.project_name, architecture_result, components_result, usage_result
                )
            
            # Update job status
            self.active_jobs[job_id]["status"] = "completed"
            self.active_jobs[job_id]["confluence_pages"] = confluence_pages
            self.active_jobs[job_id]["markdown_files"] = markdown_files
            
            return job_id
            
        except Exception as e:
            self.active_jobs[job_id]["status"] = "failed"
            self.active_jobs[job_id]["error"] = str(e)
            logger.error(f"Documentation generation failed: {e}")
            raise
    
    async def _store_results(self, job_id: str, results: Dict[str, Any]):
        """Store results in database"""
        await db_manager.store_documentation_results(job_id, results)
    
    async def _create_confluence_pages(self, request: DocumentationRequest, 
                                     arch_result: Dict, comp_result: Dict, 
                                     usage_result: Dict) -> List[Dict]:
        """Create Confluence pages from generated content"""
        if not request.confluence_space:
            logger.warning("No Confluence space specified, skipping Confluence page creation")
            return []
        
        pages = []
        
        try:
            # Main architecture page
            arch_page = await confluence_client.create_page(
                space=request.confluence_space,
                title=f"{request.project_name} - Architecture Overview",
                content=arch_result.get("confluence_content", "")
            )
            pages.append(arch_page)
            
            # Component pages
            for component, details in comp_result.get("components", {}).items():
                comp_page = await confluence_client.create_page(
                    space=request.confluence_space,
                    title=f"{request.project_name} - {component} Component",
                    content=details.get("confluence_content", ""),
                    parent_id=arch_page["id"]
                )
                pages.append(comp_page)
            
            # Usage documentation page
            usage_page = await confluence_client.create_page(
                space=request.confluence_space,
                title=f"{request.project_name} - Usage Guide",
                content=usage_result.get("confluence_content", ""),
                parent_id=arch_page["id"]
            )
            pages.append(usage_page)
            
        except Exception as e:
            logger.error(f"Failed to create Confluence pages: {e}")
            # Don't fail the entire job if only Confluence fails
        
        return pages

documentation_service = DocumentationService()

@app.post("/generate-documentation")
async def generate_documentation(request: DocumentationRequestModel, background_tasks: BackgroundTasks):
    """Generate documentation for a repository"""
    try:
        doc_request = DocumentationRequest(
            repo_url=request.repo_url,
            confluence_space=request.confluence_space,
            project_name=request.project_name,
            components=request.components,
            export_format=request.export_format,
            output_dir=request.output_dir
        )
        
        job_id = await documentation_service.generate_documentation(doc_request)
        
        return {"job_id": job_id, "status": "started"}
        
    except Exception as e:
        logger.error(f"Error starting documentation generation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/jobs/{job_id}")
async def get_job_status(job_id: str):
    """Get status of documentation generation job"""
    if job_id not in documentation_service.active_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = documentation_service.active_jobs[job_id]
    return {
        "job_id": job_id,
        "status": job["status"],
        "started_at": job["started_at"],
        "confluence_pages": job.get("confluence_pages", []),
        "markdown_files": job.get("markdown_files", None)
    }

@app.post("/generate-markdown")
async def generate_markdown_only(request: DocumentationRequestModel):
    """Generate documentation as markdown files only (for testing without Confluence)"""
    try:
        # Force markdown export format
        request.export_format = "markdown"
        
        doc_request = DocumentationRequest(
            repo_url=request.repo_url,
            confluence_space=None,  # No Confluence needed
            project_name=request.project_name,
            components=request.components,
            export_format="markdown",
            output_dir=request.output_dir
        )
        
        job_id = await documentation_service.generate_documentation(doc_request)
        
        return {"job_id": job_id, "status": "started", "export_format": "markdown"}
        
    except Exception as e:
        logger.error(f"Error starting markdown documentation generation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now()}

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    await db_manager.initialize()
    await mcp_server.start()
    logger.info("Confluence Documentation Generator started")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    await db_manager.close()
    await mcp_server.stop()
    logger.info("Confluence Documentation Generator stopped")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)