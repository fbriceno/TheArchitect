"""
Database models for documentation storage
"""

from sqlalchemy import Column, String, Text, DateTime, JSON, Integer, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

Base = declarative_base()

class ProjectModel(Base):
    """Project information model"""
    __tablename__ = "projects"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    repo_url = Column(String(500), nullable=False)
    confluence_space = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    architectures = relationship("ArchitectureModel", back_populates="project")
    components = relationship("ComponentModel", back_populates="project")
    documentations = relationship("DocumentationModel", back_populates="project")

class ArchitectureModel(Base):
    """Architecture analysis model"""
    __tablename__ = "architectures"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    
    # Architecture data
    project_structure = Column(JSON, nullable=True)
    key_components = Column(JSON, nullable=True)  # List of component names
    architecture_patterns = Column(JSON, nullable=True)  # List of patterns
    dependencies = Column(JSON, nullable=True)  # Dependency mapping
    mermaid_diagrams = Column(JSON, nullable=True)  # List of diagram definitions
    
    # Analysis metadata
    total_files = Column(Integer, default=0)
    complexity_score = Column(Integer, default=0)  # 1-10 scale
    maintainability_score = Column(Integer, default=0)  # 1-10 scale
    
    # Generated content
    confluence_content = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    project = relationship("ProjectModel", back_populates="architectures")

class ComponentModel(Base):
    """Component analysis model"""
    __tablename__ = "components"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    
    # Component identification
    name = Column(String(255), nullable=False)
    type = Column(String(100), nullable=True)  # React Component, Service, Module, etc.
    file_path = Column(String(500), nullable=True)
    
    # Component analysis
    description = Column(Text, nullable=True)
    interfaces = Column(JSON, nullable=True)  # List of public methods/props
    dependencies = Column(JSON, nullable=True)  # List of dependencies
    usage_examples = Column(JSON, nullable=True)  # List of usage examples
    
    # Quality metrics
    complexity = Column(String(50), nullable=True)  # Low, Medium, High
    testing_coverage = Column(String(255), nullable=True)
    documentation_level = Column(String(50), nullable=True)  # Poor, Fair, Good, Excellent
    
    # Generated content
    confluence_content = Column(Text, nullable=True)
    confluence_page_id = Column(String(100), nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    project = relationship("ProjectModel", back_populates="components")

class DocumentationModel(Base):
    """Generated documentation model"""
    __tablename__ = "documentations"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    
    # Documentation metadata
    doc_type = Column(String(100), nullable=False)  # architecture, component, usage, api
    title = Column(String(500), nullable=False)
    version = Column(String(50), default="1.0.0")
    
    # Content
    content = Column(Text, nullable=True)  # Raw content
    confluence_content = Column(Text, nullable=True)  # Confluence-formatted content
    markdown_content = Column(Text, nullable=True)  # Markdown-formatted content
    
    # Confluence integration
    confluence_page_id = Column(String(100), nullable=True)
    confluence_page_url = Column(String(1000), nullable=True)
    confluence_space = Column(String(255), nullable=True)
    
    # Generation metadata
    agent_type = Column(String(100), nullable=True)  # Which agent generated this
    generation_job_id = Column(String(255), nullable=True)
    
    # Status and metrics
    status = Column(String(50), default="draft")  # draft, published, archived
    word_count = Column(Integer, default=0)
    last_published = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    project = relationship("ProjectModel", back_populates="documentations")

class MermaidDiagramModel(Base):
    """Mermaid diagrams model"""
    __tablename__ = "mermaid_diagrams"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    
    # Diagram metadata
    name = Column(String(255), nullable=False)
    diagram_type = Column(String(100), nullable=False)  # flowchart, sequence, class, etc.
    description = Column(Text, nullable=True)
    
    # Diagram content
    mermaid_code = Column(Text, nullable=False)
    svg_content = Column(Text, nullable=True)  # Rendered SVG
    
    # Usage context
    documentation_id = Column(String, ForeignKey("documentations.id"), nullable=True)
    component_id = Column(String, ForeignKey("components.id"), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class AgentRunModel(Base):
    """Agent execution tracking model"""
    __tablename__ = "agent_runs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    
    # Agent information
    agent_type = Column(String(100), nullable=False)  # architecture, component, usage
    agent_version = Column(String(50), default="1.0.0")
    
    # Execution details
    job_id = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False)  # running, completed, failed
    
    # Input/Output
    input_params = Column(JSON, nullable=True)
    output_data = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Performance metrics
    execution_time_seconds = Column(Integer, nullable=True)
    tokens_used = Column(Integer, nullable=True)
    
    # Timestamps
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class MCPRequestModel(Base):
    """MCP service request tracking"""
    __tablename__ = "mcp_requests"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Request details
    method = Column(String(100), nullable=False)
    endpoint = Column(String(500), nullable=False)
    request_params = Column(JSON, nullable=True)
    
    # Response details
    response_data = Column(JSON, nullable=True)
    response_status = Column(Integer, nullable=True)
    response_time_ms = Column(Integer, nullable=True)
    
    # Client information
    client_id = Column(String(255), nullable=True)
    user_agent = Column(String(500), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)