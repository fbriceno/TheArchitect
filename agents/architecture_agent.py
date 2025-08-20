"""
Architecture Analysis Agent
Analyzes repository architecture and generates architecture documentation
"""

import asyncio
import logging
from typing import Dict, List, Any
from pathlib import Path
import os
from dataclasses import dataclass

from adalflow import Component, Generator, get_logger
from adalflow.core.types import GeneratorOutput

logger = get_logger(__name__)

@dataclass
class ArchitectureAnalysis:
    project_structure: Dict[str, Any]
    key_components: List[str]
    architecture_patterns: List[str]
    dependencies: Dict[str, List[str]]
    confluence_content: str
    mermaid_diagrams: List[str]

class ArchitectureAgent(Component):
    """Agent responsible for analyzing repository architecture"""
    
    def __init__(self):
        super().__init__()
        self.generator = Generator(
            model_client="google",  # Using Google Gemini as in original project
            model_kwargs={"model": "gemini-2.5-flash", "temperature": 0.1}
        )
    
    async def analyze_repository(self, repo_url: str) -> Dict[str, Any]:
        """Analyze repository architecture"""
        try:
            logger.info(f"Starting architecture analysis for {repo_url}")
            
            # Clone repository (reuse existing logic from deepwiki)
            repo_path = await self._clone_repository(repo_url)
            
            # Analyze project structure
            structure = await self._analyze_project_structure(repo_path)
            
            # Identify key components
            components = await self._identify_key_components(repo_path, structure)
            
            # Detect architecture patterns
            patterns = await self._detect_architecture_patterns(repo_path, structure)
            
            # Analyze dependencies
            dependencies = await self._analyze_dependencies(repo_path)
            
            # Generate architecture documentation
            confluence_content = await self._generate_confluence_content(
                structure, components, patterns, dependencies
            )
            
            # Generate Mermaid diagrams
            diagrams = await self._generate_mermaid_diagrams(
                structure, components, dependencies
            )
            
            result = {
                "project_structure": structure,
                "key_components": components,
                "architecture_patterns": patterns,
                "dependencies": dependencies,
                "confluence_content": confluence_content,
                "mermaid_diagrams": diagrams
            }
            
            logger.info(f"Architecture analysis completed for {repo_url}")
            return result
            
        except Exception as e:
            logger.error(f"Architecture analysis failed: {e}")
            raise

    async def _clone_repository(self, repo_url: str) -> Path:
        """Clone repository to local directory"""
        # Implementation would reuse deepwiki's repository cloning logic
        # For now, return a placeholder path
        repo_name = repo_url.split("/")[-1].replace(".git", "")
        repo_path = Path(f"/tmp/repos/{repo_name}")
        
        # TODO: Implement actual cloning logic using git
        return repo_path

    async def _analyze_project_structure(self, repo_path: Path) -> Dict[str, Any]:
        """Analyze the project's directory structure"""
        structure = {
            "root_files": [],
            "directories": {},
            "file_types": {},
            "total_files": 0
        }
        
        if not repo_path.exists():
            return structure
        
        for item in repo_path.rglob("*"):
            if item.is_file():
                structure["total_files"] += 1
                file_ext = item.suffix
                if file_ext not in structure["file_types"]:
                    structure["file_types"][file_ext] = 0
                structure["file_types"][file_ext] += 1
                
                if item.parent == repo_path:
                    structure["root_files"].append(item.name)
            elif item.is_dir():
                rel_path = str(item.relative_to(repo_path))
                structure["directories"][rel_path] = len(list(item.iterdir()))
        
        return structure

    async def _identify_key_components(self, repo_path: Path, structure: Dict) -> List[str]:
        """Identify key components in the project"""
        components = []
        
        # Use AI to identify components based on structure
        prompt = f"""
        Analyze this project structure and identify the key components:
        
        Structure: {structure}
        
        Identify the main modules, services, or components that form the core of this application.
        Return a list of component names.
        """
        
        try:
            response: GeneratorOutput = await self.generator.acall(prompt)
            # Parse response to extract components
            components = self._parse_components_from_response(response.data)
        except Exception as e:
            logger.error(f"Failed to identify components: {e}")
            components = ["API", "Frontend", "Database", "Services"]  # Fallback
        
        return components

    async def _detect_architecture_patterns(self, repo_path: Path, structure: Dict) -> List[str]:
        """Detect architecture patterns used in the project"""
        patterns = []
        
        prompt = f"""
        Based on this project structure, identify the architecture patterns being used:
        
        Structure: {structure}
        
        Common patterns include: MVC, MVP, MVVM, Microservices, Layered Architecture, 
        Component-Based, Event-Driven, etc.
        
        Return a list of detected patterns.
        """
        
        try:
            response: GeneratorOutput = await self.generator.acall(prompt)
            patterns = self._parse_patterns_from_response(response.data)
        except Exception as e:
            logger.error(f"Failed to detect patterns: {e}")
            patterns = ["Component-Based", "API-Driven"]  # Fallback
        
        return patterns

    async def _analyze_dependencies(self, repo_path: Path) -> Dict[str, List[str]]:
        """Analyze project dependencies"""
        dependencies = {
            "frontend": [],
            "backend": [],
            "database": [],
            "external_services": []
        }
        
        # Check package.json for frontend dependencies
        package_json = repo_path / "package.json"
        if package_json.exists():
            try:
                import json
                with open(package_json, 'r') as f:
                    data = json.load(f)
                    deps = data.get("dependencies", {})
                    dev_deps = data.get("devDependencies", {})
                    dependencies["frontend"] = list(deps.keys()) + list(dev_deps.keys())
            except Exception as e:
                logger.error(f"Failed to parse package.json: {e}")
        
        # Check requirements.txt for Python dependencies
        requirements = repo_path / "requirements.txt"
        if requirements.exists():
            try:
                with open(requirements, 'r') as f:
                    deps = [line.split(">=")[0].split("==")[0].strip() 
                           for line in f.readlines() if line.strip()]
                    dependencies["backend"] = deps
            except Exception as e:
                logger.error(f"Failed to parse requirements.txt: {e}")
        
        return dependencies

    async def _generate_confluence_content(self, structure: Dict, components: List[str], 
                                         patterns: List[str], dependencies: Dict) -> str:
        """Generate Confluence-formatted documentation content"""
        
        prompt = f"""
        Generate comprehensive architecture documentation in Confluence format for a project with:
        
        Project Structure: {structure}
        Key Components: {components}
        Architecture Patterns: {patterns}
        Dependencies: {dependencies}
        
        Include:
        1. Executive Summary
        2. Architecture Overview
        3. Key Components Description
        4. Architecture Patterns Used
        5. Technology Stack
        6. Component Interactions
        7. Deployment Architecture
        
        Format the output as Confluence wiki markup.
        """
        
        try:
            response: GeneratorOutput = await self.generator.acall(prompt)
            return response.data
        except Exception as e:
            logger.error(f"Failed to generate confluence content: {e}")
            return self._generate_fallback_content(structure, components, patterns)

    async def _generate_mermaid_diagrams(self, structure: Dict, components: List[str], 
                                       dependencies: Dict) -> List[str]:
        """Generate Mermaid diagrams for architecture visualization"""
        diagrams = []
        
        # System architecture diagram
        arch_prompt = f"""
        Generate a Mermaid diagram showing the system architecture for:
        Components: {components}
        Dependencies: {dependencies}
        
        Create a flowchart showing how components interact.
        """
        
        try:
            response: GeneratorOutput = await self.generator.acall(arch_prompt)
            diagrams.append(response.data)
        except Exception as e:
            logger.error(f"Failed to generate architecture diagram: {e}")
        
        return diagrams

    def _parse_components_from_response(self, response: str) -> List[str]:
        """Parse components from AI response"""
        # Simple parsing logic - can be enhanced
        lines = response.split('\n')
        components = []
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#'):
                # Remove bullet points and numbering
                component = line.replace('-', '').replace('*', '').replace('1.', '').strip()
                if component:
                    components.append(component)
        return components[:10]  # Limit to 10 components

    def _parse_patterns_from_response(self, response: str) -> List[str]:
        """Parse patterns from AI response"""
        # Similar parsing logic for patterns
        lines = response.split('\n')
        patterns = []
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#'):
                pattern = line.replace('-', '').replace('*', '').replace('1.', '').strip()
                if pattern:
                    patterns.append(pattern)
        return patterns[:5]  # Limit to 5 patterns

    def _generate_fallback_content(self, structure: Dict, components: List[str], 
                                 patterns: List[str]) -> str:
        """Generate fallback content if AI generation fails"""
        return f"""
        # Architecture Documentation
        
        ## Project Overview
        This project consists of {structure.get('total_files', 0)} files organized across multiple directories.
        
        ## Key Components
        {chr(10).join(f"- {comp}" for comp in components)}
        
        ## Architecture Patterns
        {chr(10).join(f"- {pattern}" for pattern in patterns)}
        
        ## File Structure
        - Root files: {len(structure.get('root_files', []))}
        - Directories: {len(structure.get('directories', {}))}
        - File types: {', '.join(structure.get('file_types', {}).keys())}
        """