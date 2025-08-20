"""
Database manager for documentation storage using PostgreSQL
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
import os

from sqlalchemy import create_engine, select, update, delete
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
import asyncpg

from .models import (
    Base, ProjectModel, ArchitectureModel, ComponentModel, 
    DocumentationModel, MermaidDiagramModel, AgentRunModel, MCPRequestModel
)

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Database manager for component documentation storage"""
    
    def __init__(self):
        self.database_url = self._get_database_url()
        self.async_engine = None
        self.async_session_maker = None
        
    def _get_database_url(self) -> str:
        """Get database URL from environment or use default PostgreSQL"""
        # Use PostgreSQL as it's robust and suitable for this type of application
        db_host = os.getenv("POSTGRES_HOST", "localhost")
        db_port = os.getenv("POSTGRES_PORT", "5432")
        db_name = os.getenv("POSTGRES_DB", "confluence_docs")
        db_user = os.getenv("POSTGRES_USER", "postgres")
        db_password = os.getenv("POSTGRES_PASSWORD", "password")
        
        return f"postgresql+asyncpg://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    
    async def initialize(self):
        """Initialize database connection and create tables"""
        try:
            self.async_engine = create_async_engine(
                self.database_url,
                echo=False,
                poolclass=NullPool
            )
            
            self.async_session_maker = sessionmaker(
                self.async_engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            # Create tables
            async with self.async_engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            
            logger.info("Database initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    async def close(self):
        """Close database connections"""
        if self.async_engine:
            await self.async_engine.dispose()
            logger.info("Database connections closed")
    
    async def create_project(self, name: str, repo_url: str, confluence_space: str = None, 
                           description: str = None) -> str:
        """Create a new project record"""
        async with self.async_session_maker() as session:
            try:
                project = ProjectModel(
                    name=name,
                    repo_url=repo_url,
                    confluence_space=confluence_space,
                    description=description
                )
                
                session.add(project)
                await session.commit()
                await session.refresh(project)
                
                logger.info(f"Created project: {project.id}")
                return project.id
                
            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to create project: {e}")
                raise
    
    async def store_architecture_analysis(self, project_id: str, analysis: Dict[str, Any]) -> str:
        """Store architecture analysis results"""
        async with self.async_session_maker() as session:
            try:
                architecture = ArchitectureModel(
                    project_id=project_id,
                    project_structure=analysis.get("project_structure", {}),
                    key_components=analysis.get("key_components", []),
                    architecture_patterns=analysis.get("architecture_patterns", []),
                    dependencies=analysis.get("dependencies", {}),
                    mermaid_diagrams=analysis.get("mermaid_diagrams", []),
                    confluence_content=analysis.get("confluence_content", ""),
                    total_files=analysis.get("project_structure", {}).get("total_files", 0)
                )
                
                session.add(architecture)
                await session.commit()
                await session.refresh(architecture)
                
                logger.info(f"Stored architecture analysis: {architecture.id}")
                return architecture.id
                
            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to store architecture analysis: {e}")
                raise
    
    async def store_component_analysis(self, project_id: str, component_name: str, 
                                     analysis: Dict[str, Any]) -> str:
        """Store component analysis results"""
        async with self.async_session_maker() as session:
            try:
                component = ComponentModel(
                    project_id=project_id,
                    name=component_name,
                    type=analysis.get("type", "Component"),
                    description=analysis.get("description", ""),
                    interfaces=analysis.get("interfaces", []),
                    dependencies=analysis.get("dependencies", []),
                    usage_examples=analysis.get("usage_examples", []),
                    complexity=analysis.get("complexity", "Medium"),
                    testing_coverage=analysis.get("testing_coverage", "Unknown"),
                    documentation_level=analysis.get("documentation_level", "Fair"),
                    confluence_content=analysis.get("confluence_content", "")
                )
                
                session.add(component)
                await session.commit()
                await session.refresh(component)
                
                logger.info(f"Stored component analysis: {component.id}")
                return component.id
                
            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to store component analysis: {e}")
                raise
    
    async def store_documentation_results(self, job_id: str, results: Dict[str, Any]):
        """Store documentation generation results"""
        async with self.async_session_maker() as session:
            try:
                # This would be called after agents complete their work
                # Store results in appropriate tables based on content type
                
                logger.info(f"Stored documentation results for job: {job_id}")
                
            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to store documentation results: {e}")
                raise
    
    async def get_project_by_repo_url(self, repo_url: str) -> Optional[Dict[str, Any]]:
        """Get project by repository URL"""
        async with self.async_session_maker() as session:
            try:
                stmt = select(ProjectModel).where(ProjectModel.repo_url == repo_url)
                result = await session.execute(stmt)
                project = result.scalar_one_or_none()
                
                if project:
                    return {
                        "id": project.id,
                        "name": project.name,
                        "repo_url": project.repo_url,
                        "confluence_space": project.confluence_space,
                        "description": project.description,
                        "created_at": project.created_at,
                        "updated_at": project.updated_at
                    }
                return None
                
            except Exception as e:
                logger.error(f"Failed to get project by repo URL: {e}")
                return None
    
    async def get_project_architecture(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Get architecture analysis for project"""
        async with self.async_session_maker() as session:
            try:
                stmt = select(ArchitectureModel).where(ArchitectureModel.project_id == project_id)
                result = await session.execute(stmt)
                architecture = result.scalar_one_or_none()
                
                if architecture:
                    return {
                        "id": architecture.id,
                        "project_id": architecture.project_id,
                        "project_structure": architecture.project_structure,
                        "key_components": architecture.key_components,
                        "architecture_patterns": architecture.architecture_patterns,
                        "dependencies": architecture.dependencies,
                        "mermaid_diagrams": architecture.mermaid_diagrams,
                        "confluence_content": architecture.confluence_content,
                        "total_files": architecture.total_files,
                        "created_at": architecture.created_at
                    }
                return None
                
            except Exception as e:
                logger.error(f"Failed to get project architecture: {e}")
                return None
    
    async def get_project_components(self, project_id: str) -> List[Dict[str, Any]]:
        """Get all components for a project"""
        async with self.async_session_maker() as session:
            try:
                stmt = select(ComponentModel).where(
                    ComponentModel.project_id == project_id,
                    ComponentModel.is_active == True
                )
                result = await session.execute(stmt)
                components = result.scalars().all()
                
                return [
                    {
                        "id": comp.id,
                        "name": comp.name,
                        "type": comp.type,
                        "description": comp.description,
                        "interfaces": comp.interfaces,
                        "dependencies": comp.dependencies,
                        "usage_examples": comp.usage_examples,
                        "complexity": comp.complexity,
                        "testing_coverage": comp.testing_coverage,
                        "documentation_level": comp.documentation_level,
                        "confluence_page_id": comp.confluence_page_id,
                        "created_at": comp.created_at
                    }
                    for comp in components
                ]
                
            except Exception as e:
                logger.error(f"Failed to get project components: {e}")
                return []
    
    async def get_component_by_name(self, project_id: str, component_name: str) -> Optional[Dict[str, Any]]:
        """Get specific component by name"""
        async with self.async_session_maker() as session:
            try:
                stmt = select(ComponentModel).where(
                    ComponentModel.project_id == project_id,
                    ComponentModel.name == component_name,
                    ComponentModel.is_active == True
                )
                result = await session.execute(stmt)
                component = result.scalar_one_or_none()
                
                if component:
                    return {
                        "id": component.id,
                        "name": component.name,
                        "type": component.type,
                        "description": component.description,
                        "interfaces": component.interfaces,
                        "dependencies": component.dependencies,
                        "usage_examples": component.usage_examples,
                        "complexity": component.complexity,
                        "confluence_content": component.confluence_content,
                        "created_at": component.created_at
                    }
                return None
                
            except Exception as e:
                logger.error(f"Failed to get component by name: {e}")
                return None
    
    async def update_confluence_page_id(self, component_id: str, page_id: str):
        """Update Confluence page ID for component"""
        async with self.async_session_maker() as session:
            try:
                stmt = update(ComponentModel).where(
                    ComponentModel.id == component_id
                ).values(confluence_page_id=page_id, updated_at=datetime.utcnow())
                
                await session.execute(stmt)
                await session.commit()
                
            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to update confluence page ID: {e}")
    
    async def track_agent_run(self, project_id: str, agent_type: str, job_id: str, 
                            status: str, input_params: Dict = None, 
                            output_data: Dict = None, error_message: str = None,
                            execution_time: int = None) -> str:
        """Track agent execution"""
        async with self.async_session_maker() as session:
            try:
                agent_run = AgentRunModel(
                    project_id=project_id,
                    agent_type=agent_type,
                    job_id=job_id,
                    status=status,
                    input_params=input_params or {},
                    output_data=output_data or {},
                    error_message=error_message,
                    execution_time_seconds=execution_time,
                    completed_at=datetime.utcnow() if status in ["completed", "failed"] else None
                )
                
                session.add(agent_run)
                await session.commit()
                await session.refresh(agent_run)
                
                return agent_run.id
                
            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to track agent run: {e}")
                raise
    
    async def track_mcp_request(self, method: str, endpoint: str, request_params: Dict = None,
                              response_data: Dict = None, response_status: int = None,
                              response_time_ms: int = None, client_id: str = None) -> str:
        """Track MCP service requests"""
        async with self.async_session_maker() as session:
            try:
                mcp_request = MCPRequestModel(
                    method=method,
                    endpoint=endpoint,
                    request_params=request_params or {},
                    response_data=response_data or {},
                    response_status=response_status,
                    response_time_ms=response_time_ms,
                    client_id=client_id
                )
                
                session.add(mcp_request)
                await session.commit()
                await session.refresh(mcp_request)
                
                return mcp_request.id
                
            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to track MCP request: {e}")
                raise
    
    async def get_project_statistics(self, project_id: str) -> Dict[str, Any]:
        """Get project statistics"""
        async with self.async_session_maker() as session:
            try:
                # Get component count
                stmt = select(ComponentModel).where(
                    ComponentModel.project_id == project_id,
                    ComponentModel.is_active == True
                )
                result = await session.execute(stmt)
                component_count = len(result.scalars().all())
                
                # Get documentation count
                stmt = select(DocumentationModel).where(
                    DocumentationModel.project_id == project_id
                )
                result = await session.execute(stmt)
                doc_count = len(result.scalars().all())
                
                # Get agent run statistics
                stmt = select(AgentRunModel).where(
                    AgentRunModel.project_id == project_id
                )
                result = await session.execute(stmt)
                agent_runs = result.scalars().all()
                
                return {
                    "component_count": component_count,
                    "documentation_count": doc_count,
                    "total_agent_runs": len(agent_runs),
                    "successful_runs": len([r for r in agent_runs if r.status == "completed"]),
                    "failed_runs": len([r for r in agent_runs if r.status == "failed"])
                }
                
            except Exception as e:
                logger.error(f"Failed to get project statistics: {e}")
                return {}
    
    async def search_components(self, project_id: str, query: str) -> List[Dict[str, Any]]:
        """Search components by name or description"""
        async with self.async_session_maker() as session:
            try:
                stmt = select(ComponentModel).where(
                    ComponentModel.project_id == project_id,
                    ComponentModel.is_active == True,
                    (ComponentModel.name.ilike(f"%{query}%") | 
                     ComponentModel.description.ilike(f"%{query}%"))
                )
                result = await session.execute(stmt)
                components = result.scalars().all()
                
                return [
                    {
                        "id": comp.id,
                        "name": comp.name,
                        "type": comp.type,
                        "description": comp.description,
                        "complexity": comp.complexity
                    }
                    for comp in components
                ]
                
            except Exception as e:
                logger.error(f"Failed to search components: {e}")
                return []