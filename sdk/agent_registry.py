"""
Agent Registry for managing and discovering available documentation agents
"""

import logging
from typing import Dict, List, Any, Optional, Set
import json
from datetime import datetime
from pathlib import Path

from .agent_sdk import BaseAgent, AgentCapabilities

logger = logging.getLogger(__name__)

class AgentRegistry:
    """Registry for managing and discovering documentation generation agents"""
    
    def __init__(self, registry_file: Optional[str] = None):
        self.registry_file = registry_file or "agent_registry.json"
        self.agents: Dict[str, Dict[str, Any]] = {}
        self.capabilities_index: Dict[str, Set[str]] = {}  # input_type -> set of agent names
        self.language_index: Dict[str, Set[str]] = {}     # language -> set of agent names
        self.load_registry()
    
    def register_agent(self, agent: BaseAgent, metadata: Dict[str, Any] = None):
        """Register an agent in the registry"""
        agent_name = agent.capabilities.name
        
        agent_info = {
            "name": agent_name,
            "description": agent.capabilities.description,
            "capabilities": {
                "input_types": agent.capabilities.input_types,
                "output_types": agent.capabilities.output_types,
                "supported_languages": agent.capabilities.supported_languages,
                "max_parallel_tasks": agent.capabilities.max_parallel_tasks,
                "timeout_seconds": agent.capabilities.timeout_seconds
            },
            "class_name": agent.__class__.__name__,
            "module_path": agent.__class__.__module__,
            "metadata": metadata or {},
            "registered_at": datetime.utcnow().isoformat(),
            "version": metadata.get("version", "1.0.0") if metadata else "1.0.0"
        }
        
        self.agents[agent_name] = agent_info
        self._update_indices(agent_name, agent.capabilities)
        self.save_registry()
        
        logger.info(f"Registered agent in registry: {agent_name}")
    
    def unregister_agent(self, agent_name: str):
        """Unregister an agent from the registry"""
        if agent_name in self.agents:
            agent_info = self.agents[agent_name]
            
            # Remove from indices
            for input_type in agent_info["capabilities"]["input_types"]:
                if input_type in self.capabilities_index:
                    self.capabilities_index[input_type].discard(agent_name)
                    if not self.capabilities_index[input_type]:
                        del self.capabilities_index[input_type]
            
            for language in agent_info["capabilities"]["supported_languages"]:
                if language in self.language_index:
                    self.language_index[language].discard(agent_name)
                    if not self.language_index[language]:
                        del self.language_index[language]
            
            del self.agents[agent_name]
            self.save_registry()
            
            logger.info(f"Unregistered agent from registry: {agent_name}")
    
    def _update_indices(self, agent_name: str, capabilities: AgentCapabilities):
        """Update search indices for the agent"""
        # Index by input types
        for input_type in capabilities.input_types:
            if input_type not in self.capabilities_index:
                self.capabilities_index[input_type] = set()
            self.capabilities_index[input_type].add(agent_name)
        
        # Index by supported languages
        for language in capabilities.supported_languages:
            if language not in self.language_index:
                self.language_index[language] = set()
            self.language_index[language].add(agent_name)
    
    def find_agents_by_input_type(self, input_type: str) -> List[Dict[str, Any]]:
        """Find agents that can handle a specific input type"""
        agent_names = self.capabilities_index.get(input_type, set())
        return [self.agents[name] for name in agent_names if name in self.agents]
    
    def find_agents_by_language(self, language: str) -> List[Dict[str, Any]]:
        """Find agents that support a specific programming language"""
        agent_names = self.language_index.get(language, set())
        return [self.agents[name] for name in agent_names if name in self.agents]
    
    def find_agents_by_output_type(self, output_type: str) -> List[Dict[str, Any]]:
        """Find agents that produce a specific output type"""
        matching_agents = []
        for agent_info in self.agents.values():
            if output_type in agent_info["capabilities"]["output_types"]:
                matching_agents.append(agent_info)
        return matching_agents
    
    def get_agent(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """Get agent information by name"""
        return self.agents.get(agent_name)
    
    def list_all_agents(self) -> List[Dict[str, Any]]:
        """List all registered agents"""
        return list(self.agents.values())
    
    def search_agents(self, query: str) -> List[Dict[str, Any]]:
        """Search agents by name or description"""
        query_lower = query.lower()
        matching_agents = []
        
        for agent_info in self.agents.values():
            name_match = query_lower in agent_info["name"].lower()
            desc_match = query_lower in agent_info["description"].lower()
            
            if name_match or desc_match:
                matching_agents.append(agent_info)
        
        return matching_agents
    
    def get_compatible_agents(self, requirements: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find agents compatible with specific requirements"""
        compatible_agents = []
        
        required_input_types = requirements.get("input_types", [])
        required_output_types = requirements.get("output_types", [])
        required_languages = requirements.get("languages", [])
        max_timeout = requirements.get("max_timeout_seconds")
        min_parallel_tasks = requirements.get("min_parallel_tasks")
        
        for agent_info in self.agents.values():
            capabilities = agent_info["capabilities"]
            
            # Check input types compatibility
            if required_input_types:
                if not any(input_type in capabilities["input_types"] for input_type in required_input_types):
                    continue
            
            # Check output types compatibility
            if required_output_types:
                if not any(output_type in capabilities["output_types"] for output_type in required_output_types):
                    continue
            
            # Check language support
            if required_languages:
                if not any(lang in capabilities["supported_languages"] for lang in required_languages):
                    continue
            
            # Check timeout requirements
            if max_timeout and capabilities["timeout_seconds"] > max_timeout:
                continue
            
            # Check parallel tasks requirements
            if min_parallel_tasks and capabilities["max_parallel_tasks"] < min_parallel_tasks:
                continue
            
            compatible_agents.append(agent_info)
        
        return compatible_agents
    
    def recommend_workflow(self, workflow_requirements: Dict[str, Any]) -> Dict[str, List[str]]:
        """Recommend agents for a workflow based on requirements"""
        recommendations = {}
        
        for step_name, step_requirements in workflow_requirements.items():
            compatible_agents = self.get_compatible_agents(step_requirements)
            
            # Sort by compatibility score (simple scoring based on capabilities match)
            scored_agents = []
            for agent_info in compatible_agents:
                score = self._calculate_compatibility_score(agent_info, step_requirements)
                scored_agents.append((score, agent_info["name"]))
            
            scored_agents.sort(reverse=True, key=lambda x: x[0])
            recommendations[step_name] = [agent_name for _, agent_name in scored_agents[:3]]  # Top 3
        
        return recommendations
    
    def _calculate_compatibility_score(self, agent_info: Dict[str, Any], requirements: Dict[str, Any]) -> float:
        """Calculate compatibility score between agent and requirements"""
        score = 0.0
        capabilities = agent_info["capabilities"]
        
        # Score based on input type matches
        required_inputs = set(requirements.get("input_types", []))
        supported_inputs = set(capabilities["input_types"])
        input_overlap = len(required_inputs & supported_inputs)
        if required_inputs:
            score += (input_overlap / len(required_inputs)) * 30
        
        # Score based on output type matches
        required_outputs = set(requirements.get("output_types", []))
        supported_outputs = set(capabilities["output_types"])
        output_overlap = len(required_outputs & supported_outputs)
        if required_outputs:
            score += (output_overlap / len(required_outputs)) * 30
        
        # Score based on language support
        required_languages = set(requirements.get("languages", []))
        supported_languages = set(capabilities["supported_languages"])
        if required_languages:
            lang_overlap = len(required_languages & supported_languages)
            score += (lang_overlap / len(required_languages)) * 20
        
        # Bonus for higher parallel task capacity
        max_parallel = capabilities["max_parallel_tasks"]
        if max_parallel >= 5:
            score += 10
        elif max_parallel >= 3:
            score += 5
        
        # Penalty for very long timeouts
        timeout = capabilities["timeout_seconds"]
        if timeout <= 60:
            score += 5
        elif timeout <= 300:
            score += 2
        elif timeout > 600:
            score -= 5
        
        return score
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get registry statistics"""
        total_agents = len(self.agents)
        
        input_type_counts = {
            input_type: len(agents)
            for input_type, agents in self.capabilities_index.items()
        }
        
        language_counts = {
            language: len(agents)
            for language, agents in self.language_index.items()
        }
        
        output_types = set()
        for agent_info in self.agents.values():
            output_types.update(agent_info["capabilities"]["output_types"])
        
        return {
            "total_agents": total_agents,
            "input_types": dict(sorted(input_type_counts.items())),
            "supported_languages": dict(sorted(language_counts.items())),
            "output_types": sorted(list(output_types)),
            "registry_file": self.registry_file,
            "last_updated": datetime.utcnow().isoformat()
        }
    
    def validate_registry(self) -> List[str]:
        """Validate registry consistency and return any issues"""
        issues = []
        
        # Check for required fields
        for agent_name, agent_info in self.agents.items():
            required_fields = ["name", "description", "capabilities", "class_name", "module_path"]
            for field in required_fields:
                if field not in agent_info:
                    issues.append(f"Agent '{agent_name}': missing required field '{field}'")
            
            # Validate capabilities structure
            if "capabilities" in agent_info:
                capabilities = agent_info["capabilities"]
                required_cap_fields = ["input_types", "output_types", "supported_languages"]
                for field in required_cap_fields:
                    if field not in capabilities:
                        issues.append(f"Agent '{agent_name}': missing capability field '{field}'")
                    elif not isinstance(capabilities[field], list):
                        issues.append(f"Agent '{agent_name}': capability field '{field}' must be a list")
        
        # Check index consistency
        for input_type, agent_names in self.capabilities_index.items():
            for agent_name in agent_names:
                if agent_name not in self.agents:
                    issues.append(f"Capabilities index contains non-existent agent '{agent_name}' for input type '{input_type}'")
        
        for language, agent_names in self.language_index.items():
            for agent_name in agent_names:
                if agent_name not in self.agents:
                    issues.append(f"Language index contains non-existent agent '{agent_name}' for language '{language}'")
        
        return issues
    
    def save_registry(self):
        """Save registry to file"""
        try:
            registry_data = {
                "agents": self.agents,
                "capabilities_index": {k: list(v) for k, v in self.capabilities_index.items()},
                "language_index": {k: list(v) for k, v in self.language_index.items()},
                "last_saved": datetime.utcnow().isoformat()
            }
            
            with open(self.registry_file, 'w') as f:
                json.dump(registry_data, f, indent=2)
            
            logger.debug(f"Saved agent registry to {self.registry_file}")
            
        except Exception as e:
            logger.error(f"Failed to save agent registry: {e}")
    
    def load_registry(self):
        """Load registry from file"""
        try:
            registry_path = Path(self.registry_file)
            if not registry_path.exists():
                logger.info(f"Registry file {self.registry_file} does not exist, starting with empty registry")
                return
            
            with open(self.registry_file, 'r') as f:
                registry_data = json.load(f)
            
            self.agents = registry_data.get("agents", {})
            
            # Rebuild indices from loaded data
            capabilities_index_data = registry_data.get("capabilities_index", {})
            self.capabilities_index = {k: set(v) for k, v in capabilities_index_data.items()}
            
            language_index_data = registry_data.get("language_index", {})
            self.language_index = {k: set(v) for k, v in language_index_data.items()}
            
            logger.info(f"Loaded agent registry from {self.registry_file} ({len(self.agents)} agents)")
            
        except Exception as e:
            logger.error(f"Failed to load agent registry: {e}")
            # Continue with empty registry
            self.agents = {}
            self.capabilities_index = {}
            self.language_index = {}
    
    def export_registry(self, output_file: str):
        """Export registry to a different file"""
        try:
            registry_data = {
                "agents": self.agents,
                "statistics": self.get_statistics(),
                "exported_at": datetime.utcnow().isoformat()
            }
            
            with open(output_file, 'w') as f:
                json.dump(registry_data, f, indent=2)
            
            logger.info(f"Exported agent registry to {output_file}")
            
        except Exception as e:
            logger.error(f"Failed to export agent registry: {e}")
            raise
    
    def import_registry(self, input_file: str, merge: bool = False):
        """Import registry from a file"""
        try:
            with open(input_file, 'r') as f:
                imported_data = json.load(f)
            
            imported_agents = imported_data.get("agents", {})
            
            if not merge:
                # Replace entire registry
                self.agents = {}
                self.capabilities_index = {}
                self.language_index = {}
            
            # Import agents
            for agent_name, agent_info in imported_agents.items():
                self.agents[agent_name] = agent_info
                
                # Rebuild indices for imported agents
                if "capabilities" in agent_info:
                    capabilities = agent_info["capabilities"]
                    
                    for input_type in capabilities.get("input_types", []):
                        if input_type not in self.capabilities_index:
                            self.capabilities_index[input_type] = set()
                        self.capabilities_index[input_type].add(agent_name)
                    
                    for language in capabilities.get("supported_languages", []):
                        if language not in self.language_index:
                            self.language_index[language] = set()
                        self.language_index[language].add(agent_name)
            
            self.save_registry()
            logger.info(f"Imported {len(imported_agents)} agents from {input_file}")
            
        except Exception as e:
            logger.error(f"Failed to import agent registry: {e}")
            raise