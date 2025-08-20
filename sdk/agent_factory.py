"""
Agent Factory for creating and managing documentation agents
"""

import logging
from typing import Dict, List, Any, Type, Optional
import importlib
import inspect

from .agent_sdk import BaseAgent, AgentCapabilities, ArchitectureAnalysisAgent, ComponentDocumentationAgent, UsageGuideAgent

logger = logging.getLogger(__name__)

class AgentFactory:
    """Factory for creating and managing documentation generation agents"""
    
    def __init__(self):
        self.registered_types: Dict[str, Type[BaseAgent]] = {}
        self.instances: Dict[str, BaseAgent] = {}
        self._register_builtin_agents()
    
    def _register_builtin_agents(self):
        """Register built-in agent types"""
        self.register_agent_type("architecture", ArchitectureAnalysisAgent)
        self.register_agent_type("component", ComponentDocumentationAgent)
        self.register_agent_type("usage", UsageGuideAgent)
        
        logger.info("Registered built-in agent types")
    
    def register_agent_type(self, agent_type: str, agent_class: Type[BaseAgent]):
        """Register a new agent type"""
        if not issubclass(agent_class, BaseAgent):
            raise ValueError(f"Agent class must inherit from BaseAgent")
        
        self.registered_types[agent_type] = agent_class
        logger.info(f"Registered agent type: {agent_type}")
    
    def create_agent(self, agent_type: str, config: Dict[str, Any] = None) -> BaseAgent:
        """Create an agent instance of the specified type"""
        if agent_type not in self.registered_types:
            raise ValueError(f"Unknown agent type: {agent_type}")
        
        agent_class = self.registered_types[agent_type]
        
        try:
            # Create agent instance
            if config:
                # Try to pass config to constructor
                try:
                    agent = agent_class(config=config)
                except TypeError:
                    # If config not supported, create without it
                    agent = agent_class()
            else:
                agent = agent_class()
            
            # Store instance
            instance_id = f"{agent_type}_{len(self.instances)}"
            self.instances[instance_id] = agent
            
            logger.info(f"Created agent instance: {instance_id}")
            return agent
            
        except Exception as e:
            logger.error(f"Failed to create agent of type {agent_type}: {e}")
            raise
    
    def get_agent_instance(self, instance_id: str) -> Optional[BaseAgent]:
        """Get agent instance by ID"""
        return self.instances.get(instance_id)
    
    def destroy_agent_instance(self, instance_id: str):
        """Destroy an agent instance"""
        if instance_id in self.instances:
            del self.instances[instance_id]
            logger.info(f"Destroyed agent instance: {instance_id}")
    
    def list_agent_types(self) -> List[Dict[str, Any]]:
        """List all registered agent types with their capabilities"""
        types_info = []
        
        for agent_type, agent_class in self.registered_types.items():
            try:
                # Create temporary instance to get capabilities
                temp_agent = agent_class()
                types_info.append({
                    "type": agent_type,
                    "class_name": agent_class.__name__,
                    "capabilities": {
                        "name": temp_agent.capabilities.name,
                        "description": temp_agent.capabilities.description,
                        "input_types": temp_agent.capabilities.input_types,
                        "output_types": temp_agent.capabilities.output_types,
                        "supported_languages": temp_agent.capabilities.supported_languages,
                        "max_parallel_tasks": temp_agent.capabilities.max_parallel_tasks,
                        "timeout_seconds": temp_agent.capabilities.timeout_seconds
                    }
                })
            except Exception as e:
                logger.error(f"Failed to get info for agent type {agent_type}: {e}")
                types_info.append({
                    "type": agent_type,
                    "class_name": agent_class.__name__,
                    "error": str(e)
                })
        
        return types_info
    
    def list_agent_instances(self) -> List[Dict[str, Any]]:
        """List all active agent instances"""
        instances_info = []
        
        for instance_id, agent in self.instances.items():
            try:
                instances_info.append({
                    "instance_id": instance_id,
                    "type": agent.capabilities.name,
                    "status": agent.get_status(),
                    "class_name": agent.__class__.__name__
                })
            except Exception as e:
                instances_info.append({
                    "instance_id": instance_id,
                    "error": str(e)
                })
        
        return instances_info
    
    def create_agents_for_workflow(self, workflow_config: Dict[str, Any]) -> Dict[str, BaseAgent]:
        """Create agents for a specific workflow"""
        agents = {}
        
        for step_name, step_config in workflow_config.items():
            agent_type = step_config.get("agent_type")
            agent_config = step_config.get("config", {})
            
            if not agent_type:
                logger.warning(f"No agent_type specified for workflow step {step_name}")
                continue
            
            try:
                agent = self.create_agent(agent_type, agent_config)
                agents[step_name] = agent
            except Exception as e:
                logger.error(f"Failed to create agent for workflow step {step_name}: {e}")
                raise
        
        return agents
    
    def load_custom_agent(self, module_path: str, class_name: str, agent_type: str):
        """Load a custom agent from a module"""
        try:
            # Import the module
            module = importlib.import_module(module_path)
            
            # Get the agent class
            agent_class = getattr(module, class_name)
            
            # Validate it's a proper agent class
            if not issubclass(agent_class, BaseAgent):
                raise ValueError(f"Class {class_name} must inherit from BaseAgent")
            
            # Register the agent type
            self.register_agent_type(agent_type, agent_class)
            
            logger.info(f"Loaded custom agent: {agent_type} from {module_path}.{class_name}")
            
        except Exception as e:
            logger.error(f"Failed to load custom agent {module_path}.{class_name}: {e}")
            raise
    
    def create_agent_pool(self, agent_type: str, pool_size: int, config: Dict[str, Any] = None) -> List[BaseAgent]:
        """Create a pool of agents of the same type for parallel processing"""
        agents = []
        
        for i in range(pool_size):
            try:
                agent = self.create_agent(agent_type, config)
                agents.append(agent)
            except Exception as e:
                logger.error(f"Failed to create agent {i} in pool: {e}")
                # Clean up created agents
                for created_agent in agents:
                    # Find and destroy the instance
                    for instance_id, stored_agent in list(self.instances.items()):
                        if stored_agent is created_agent:
                            self.destroy_agent_instance(instance_id)
                raise
        
        logger.info(f"Created agent pool of {pool_size} {agent_type} agents")
        return agents
    
    def get_agent_capabilities(self, agent_type: str) -> Optional[AgentCapabilities]:
        """Get capabilities for a specific agent type"""
        if agent_type not in self.registered_types:
            return None
        
        try:
            temp_agent = self.registered_types[agent_type]()
            return temp_agent.capabilities
        except Exception as e:
            logger.error(f"Failed to get capabilities for {agent_type}: {e}")
            return None
    
    def validate_workflow_config(self, workflow_config: Dict[str, Any]) -> List[str]:
        """Validate a workflow configuration and return any errors"""
        errors = []
        
        for step_name, step_config in workflow_config.items():
            agent_type = step_config.get("agent_type")
            
            if not agent_type:
                errors.append(f"Step '{step_name}': missing agent_type")
                continue
            
            if agent_type not in self.registered_types:
                errors.append(f"Step '{step_name}': unknown agent_type '{agent_type}'")
                continue
            
            # Validate required inputs are provided
            capabilities = self.get_agent_capabilities(agent_type)
            if capabilities:
                required_inputs = capabilities.input_types
                provided_inputs = step_config.get("inputs", {})
                
                for required_input in required_inputs:
                    if required_input not in provided_inputs:
                        errors.append(f"Step '{step_name}': missing required input '{required_input}'")
        
        return errors
    
    def cleanup_all_instances(self):
        """Clean up all agent instances"""
        instance_ids = list(self.instances.keys())
        for instance_id in instance_ids:
            self.destroy_agent_instance(instance_id)
        
        logger.info("Cleaned up all agent instances")