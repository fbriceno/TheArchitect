"""
SDK for building documentation generation agents
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Callable
from abc import ABC, abstractmethod
from dataclasses import dataclass
import json
from datetime import datetime
import traceback

from adalflow import Component, Generator, get_logger

logger = get_logger(__name__)

@dataclass
class AgentCapabilities:
    """Agent capabilities definition"""
    name: str
    description: str
    input_types: List[str]
    output_types: List[str]
    supported_languages: List[str]
    max_parallel_tasks: int = 5
    timeout_seconds: int = 300

@dataclass
class AgentTask:
    """Task definition for agents"""
    id: str
    type: str
    input_data: Dict[str, Any]
    priority: int = 1
    timeout_seconds: Optional[int] = None
    metadata: Dict[str, Any] = None

@dataclass
class AgentResult:
    """Result from agent execution"""
    task_id: str
    success: bool
    data: Any = None
    error: Optional[str] = None
    execution_time: float = 0
    metadata: Dict[str, Any] = None

class BaseAgent(ABC):
    """Base class for all documentation generation agents"""
    
    def __init__(self, capabilities: AgentCapabilities):
        self.capabilities = capabilities
        self.logger = logging.getLogger(f"agent.{capabilities.name}")
        self.active_tasks: Dict[str, AgentTask] = {}
        
    @abstractmethod
    async def process_task(self, task: AgentTask) -> AgentResult:
        """Process a single task"""
        pass
    
    async def execute_task(self, task: AgentTask) -> AgentResult:
        """Execute task with error handling and timing"""
        start_time = datetime.utcnow()
        self.active_tasks[task.id] = task
        
        try:
            self.logger.info(f"Starting task {task.id} of type {task.type}")
            
            # Set timeout
            timeout = task.timeout_seconds or self.capabilities.timeout_seconds
            result = await asyncio.wait_for(
                self.process_task(task),
                timeout=timeout
            )
            
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            result.execution_time = execution_time
            
            self.logger.info(f"Completed task {task.id} in {execution_time:.2f}s")
            return result
            
        except asyncio.TimeoutError:
            error_msg = f"Task {task.id} timed out after {timeout}s"
            self.logger.error(error_msg)
            return AgentResult(
                task_id=task.id,
                success=False,
                error=error_msg,
                execution_time=(datetime.utcnow() - start_time).total_seconds()
            )
            
        except Exception as e:
            error_msg = f"Task {task.id} failed: {str(e)}"
            self.logger.error(f"{error_msg}\n{traceback.format_exc()}")
            return AgentResult(
                task_id=task.id,
                success=False,
                error=error_msg,
                execution_time=(datetime.utcnow() - start_time).total_seconds()
            )
            
        finally:
            self.active_tasks.pop(task.id, None)
    
    async def execute_tasks_parallel(self, tasks: List[AgentTask]) -> List[AgentResult]:
        """Execute multiple tasks in parallel"""
        semaphore = asyncio.Semaphore(self.capabilities.max_parallel_tasks)
        
        async def execute_with_semaphore(task):
            async with semaphore:
                return await self.execute_task(task)
        
        results = await asyncio.gather(
            *[execute_with_semaphore(task) for task in tasks],
            return_exceptions=True
        )
        
        # Convert exceptions to error results
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                final_results.append(AgentResult(
                    task_id=tasks[i].id,
                    success=False,
                    error=str(result)
                ))
            else:
                final_results.append(result)
        
        return final_results
    
    def get_status(self) -> Dict[str, Any]:
        """Get agent status"""
        return {
            "name": self.capabilities.name,
            "active_tasks": len(self.active_tasks),
            "active_task_ids": list(self.active_tasks.keys()),
            "capabilities": {
                "max_parallel_tasks": self.capabilities.max_parallel_tasks,
                "timeout_seconds": self.capabilities.timeout_seconds,
                "input_types": self.capabilities.input_types,
                "output_types": self.capabilities.output_types
            }
        }

class AgentSDK:
    """SDK for managing and coordinating documentation generation agents"""
    
    def __init__(self):
        self.agents: Dict[str, BaseAgent] = {}
        self.task_queue: asyncio.Queue = asyncio.Queue()
        self.result_handlers: Dict[str, Callable] = {}
        
    def register_agent(self, agent: BaseAgent):
        """Register an agent with the SDK"""
        self.agents[agent.capabilities.name] = agent
        logger.info(f"Registered agent: {agent.capabilities.name}")
    
    def unregister_agent(self, agent_name: str):
        """Unregister an agent"""
        if agent_name in self.agents:
            del self.agents[agent_name]
            logger.info(f"Unregistered agent: {agent_name}")
    
    def get_agent(self, agent_name: str) -> Optional[BaseAgent]:
        """Get agent by name"""
        return self.agents.get(agent_name)
    
    def list_agents(self) -> List[Dict[str, Any]]:
        """List all registered agents with their capabilities"""
        return [
            {
                "name": agent.capabilities.name,
                "description": agent.capabilities.description,
                "input_types": agent.capabilities.input_types,
                "output_types": agent.capabilities.output_types,
                "supported_languages": agent.capabilities.supported_languages,
                "status": agent.get_status()
            }
            for agent in self.agents.values()
        ]
    
    async def execute_task(self, agent_name: str, task: AgentTask) -> AgentResult:
        """Execute a task with a specific agent"""
        agent = self.get_agent(agent_name)
        if not agent:
            return AgentResult(
                task_id=task.id,
                success=False,
                error=f"Agent '{agent_name}' not found"
            )
        
        return await agent.execute_task(task)
    
    async def execute_workflow(self, workflow: Dict[str, Any]) -> Dict[str, List[AgentResult]]:
        """Execute a workflow of tasks across multiple agents"""
        results = {}
        
        # Execute tasks for each agent in parallel
        agent_tasks = []
        for agent_name, tasks_data in workflow.items():
            agent = self.get_agent(agent_name)
            if not agent:
                results[agent_name] = [AgentResult(
                    task_id="unknown",
                    success=False,
                    error=f"Agent '{agent_name}' not found"
                )]
                continue
            
            # Convert task data to AgentTask objects
            tasks = [
                AgentTask(
                    id=task_data.get("id", f"{agent_name}_{i}"),
                    type=task_data.get("type", "default"),
                    input_data=task_data.get("input_data", {}),
                    priority=task_data.get("priority", 1),
                    metadata=task_data.get("metadata", {})
                )
                for i, task_data in enumerate(tasks_data)
            ]
            
            agent_tasks.append((agent_name, agent, tasks))
        
        # Execute all agents in parallel
        agent_results = await asyncio.gather(
            *[agent.execute_tasks_parallel(tasks) for _, agent, tasks in agent_tasks],
            return_exceptions=True
        )
        
        # Organize results by agent
        for i, (agent_name, _, _) in enumerate(agent_tasks):
            agent_result = agent_results[i]
            if isinstance(agent_result, Exception):
                results[agent_name] = [AgentResult(
                    task_id="unknown",
                    success=False,
                    error=str(agent_result)
                )]
            else:
                results[agent_name] = agent_result
        
        return results
    
    def register_result_handler(self, task_type: str, handler: Callable[[AgentResult], None]):
        """Register a handler for specific task types"""
        self.result_handlers[task_type] = handler
    
    async def process_result(self, result: AgentResult, task_type: str):
        """Process a task result with registered handlers"""
        if task_type in self.result_handlers:
            try:
                await self.result_handlers[task_type](result)
            except Exception as e:
                logger.error(f"Result handler failed for {task_type}: {e}")
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get overall system status"""
        total_active_tasks = sum(len(agent.active_tasks) for agent in self.agents.values())
        
        return {
            "total_agents": len(self.agents),
            "total_active_tasks": total_active_tasks,
            "agents": {
                name: agent.get_status()
                for name, agent in self.agents.items()
            }
        }

# Built-in agent types for common documentation tasks

class ArchitectureAnalysisAgent(BaseAgent):
    """Agent for analyzing repository architecture"""
    
    def __init__(self):
        capabilities = AgentCapabilities(
            name="architecture_analyzer",
            description="Analyzes repository architecture and generates documentation",
            input_types=["repository_url", "project_structure"],
            output_types=["architecture_analysis", "mermaid_diagrams", "confluence_content"],
            supported_languages=["python", "javascript", "typescript", "java", "go"],
            max_parallel_tasks=3
        )
        super().__init__(capabilities)
        
        self.generator = Generator(
            model_client="google",
            model_kwargs={"model": "gemini-2.5-flash", "temperature": 0.1}
        )
    
    async def process_task(self, task: AgentTask) -> AgentResult:
        """Process architecture analysis task"""
        try:
            repo_url = task.input_data.get("repository_url")
            if not repo_url:
                return AgentResult(
                    task_id=task.id,
                    success=False,
                    error="repository_url is required"
                )
            
            # Perform architecture analysis (simplified version)
            analysis_result = await self._analyze_architecture(repo_url, task.input_data)
            
            return AgentResult(
                task_id=task.id,
                success=True,
                data=analysis_result,
                metadata={"agent_type": "architecture_analyzer"}
            )
            
        except Exception as e:
            return AgentResult(
                task_id=task.id,
                success=False,
                error=str(e)
            )
    
    async def _analyze_architecture(self, repo_url: str, input_data: Dict) -> Dict[str, Any]:
        """Perform architecture analysis"""
        # This would implement the actual architecture analysis logic
        # For now, return a placeholder result
        
        return {
            "project_structure": {
                "directories": ["src", "api", "components"],
                "total_files": 150,
                "file_types": {".py": 50, ".js": 40, ".tsx": 30, ".json": 30}
            },
            "key_components": ["API Server", "React Frontend", "Database Layer"],
            "architecture_patterns": ["MVC", "Component-Based", "API-Driven"],
            "dependencies": {
                "frontend": ["react", "typescript", "tailwindcss"],
                "backend": ["fastapi", "sqlalchemy", "postgresql"]
            },
            "confluence_content": f"# Architecture Analysis for {repo_url}\n\nThis is a comprehensive architecture analysis..."
        }

class ComponentDocumentationAgent(BaseAgent):
    """Agent for generating component documentation"""
    
    def __init__(self):
        capabilities = AgentCapabilities(
            name="component_documenter",
            description="Generates detailed documentation for individual components",
            input_types=["component_info", "source_code"],
            output_types=["component_documentation", "api_reference", "usage_examples"],
            supported_languages=["python", "javascript", "typescript", "java"],
            max_parallel_tasks=5
        )
        super().__init__(capabilities)
        
        self.generator = Generator(
            model_client="google",
            model_kwargs={"model": "gemini-2.5-flash", "temperature": 0.2}
        )
    
    async def process_task(self, task: AgentTask) -> AgentResult:
        """Process component documentation task"""
        try:
            component_name = task.input_data.get("component_name")
            if not component_name:
                return AgentResult(
                    task_id=task.id,
                    success=False,
                    error="component_name is required"
                )
            
            # Generate component documentation
            documentation = await self._generate_component_docs(component_name, task.input_data)
            
            return AgentResult(
                task_id=task.id,
                success=True,
                data=documentation,
                metadata={"agent_type": "component_documenter", "component": component_name}
            )
            
        except Exception as e:
            return AgentResult(
                task_id=task.id,
                success=False,
                error=str(e)
            )
    
    async def _generate_component_docs(self, component_name: str, input_data: Dict) -> Dict[str, Any]:
        """Generate component documentation"""
        # This would implement actual component documentation generation
        # For now, return a placeholder result
        
        return {
            "component_name": component_name,
            "type": "React Component",
            "description": f"Documentation for {component_name} component",
            "interfaces": ["props", "methods", "events"],
            "usage_examples": [f"<{component_name} prop1='value' />"],
            "confluence_content": f"# {component_name} Component\n\nDetailed documentation for the {component_name} component..."
        }

class UsageGuideAgent(BaseAgent):
    """Agent for generating usage guides and tutorials"""
    
    def __init__(self):
        capabilities = AgentCapabilities(
            name="usage_guide_generator",
            description="Generates usage guides, tutorials, and best practices documentation",
            input_types=["project_info", "api_endpoints", "examples"],
            output_types=["usage_guide", "tutorials", "best_practices"],
            supported_languages=["any"],
            max_parallel_tasks=3
        )
        super().__init__(capabilities)
        
        self.generator = Generator(
            model_client="google",
            model_kwargs={"model": "gemini-2.5-flash", "temperature": 0.3}
        )
    
    async def process_task(self, task: AgentTask) -> AgentResult:
        """Process usage guide generation task"""
        try:
            project_name = task.input_data.get("project_name", "Project")
            
            # Generate usage documentation
            usage_docs = await self._generate_usage_docs(project_name, task.input_data)
            
            return AgentResult(
                task_id=task.id,
                success=True,
                data=usage_docs,
                metadata={"agent_type": "usage_guide_generator"}
            )
            
        except Exception as e:
            return AgentResult(
                task_id=task.id,
                success=False,
                error=str(e)
            )
    
    async def _generate_usage_docs(self, project_name: str, input_data: Dict) -> Dict[str, Any]:
        """Generate usage documentation"""
        # This would implement actual usage guide generation
        # For now, return a placeholder result
        
        return {
            "getting_started": f"# Getting Started with {project_name}\n\nStep-by-step guide...",
            "tutorials": ["Basic Setup", "Advanced Configuration", "Integration Examples"],
            "best_practices": [
                "Follow consistent naming conventions",
                "Write comprehensive tests",
                "Use proper error handling"
            ],
            "confluence_content": f"# {project_name} Usage Guide\n\nComprehensive usage guide..."
        }