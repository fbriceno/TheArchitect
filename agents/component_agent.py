"""
Component Analysis Agent
Analyzes individual components and generates component-specific documentation
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
from dataclasses import dataclass
import ast
import json

from adalflow import Component, Generator, get_logger

logger = get_logger(__name__)

@dataclass
class ComponentAnalysis:
    name: str
    type: str
    description: str
    interfaces: List[str]
    dependencies: List[str]
    usage_examples: List[str]
    confluence_content: str

class ComponentAgent(Component):
    """Agent responsible for analyzing individual components"""
    
    def __init__(self):
        super().__init__()
        self.generator = Generator(
            model_client="google",
            model_kwargs={"model": "gemini-2.5-flash", "temperature": 0.1}
        )
    
    async def analyze_components(self, repo_url: str, component_names: List[str] = None) -> Dict[str, Any]:
        """Analyze specified components or auto-discover them"""
        try:
            logger.info(f"Starting component analysis for {repo_url}")
            
            repo_path = await self._get_repo_path(repo_url)
            
            if not component_names:
                component_names = await self._discover_components(repo_path)
            
            components_analysis = {}
            
            # Analyze each component in parallel
            tasks = [
                self._analyze_single_component(repo_path, comp_name)
                for comp_name in component_names
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Failed to analyze component {component_names[i]}: {result}")
                    continue
                
                components_analysis[component_names[i]] = result
            
            logger.info(f"Component analysis completed for {len(components_analysis)} components")
            return {"components": components_analysis}
            
        except Exception as e:
            logger.error(f"Component analysis failed: {e}")
            raise

    async def _get_repo_path(self, repo_url: str) -> Path:
        """Get local repository path"""
        repo_name = repo_url.split("/")[-1].replace(".git", "")
        return Path(f"/tmp/repos/{repo_name}")

    async def _discover_components(self, repo_path: Path) -> List[str]:
        """Auto-discover components in the repository"""
        components = []
        
        # Look for common component patterns
        component_patterns = [
            "src/components/**/*.tsx",
            "src/components/**/*.ts",
            "src/components/**/*.jsx",
            "src/components/**/*.js",
            "components/**/*.py",
            "api/**/*.py",
            "services/**/*.py",
            "modules/**/*.py"
        ]
        
        for pattern in component_patterns:
            for file_path in repo_path.glob(pattern):
                component_name = file_path.stem
                if component_name not in components:
                    components.append(component_name)
        
        return components[:20]  # Limit to 20 components

    async def _analyze_single_component(self, repo_path: Path, component_name: str) -> ComponentAnalysis:
        """Analyze a single component"""
        
        # Find component files
        component_files = await self._find_component_files(repo_path, component_name)
        
        if not component_files:
            return ComponentAnalysis(
                name=component_name,
                type="Unknown",
                description=f"Component {component_name} - files not found",
                interfaces=[],
                dependencies=[],
                usage_examples=[],
                confluence_content=""
            )
        
        # Read component source code
        source_code = await self._read_component_source(component_files)
        
        # Analyze component using AI
        analysis = await self._ai_analyze_component(component_name, source_code)
        
        # Generate component-specific documentation
        confluence_content = await self._generate_component_documentation(
            component_name, analysis, source_code
        )
        
        return ComponentAnalysis(
            name=component_name,
            type=analysis.get("type", "Component"),
            description=analysis.get("description", ""),
            interfaces=analysis.get("interfaces", []),
            dependencies=analysis.get("dependencies", []),
            usage_examples=analysis.get("usage_examples", []),
            confluence_content=confluence_content
        )

    async def _find_component_files(self, repo_path: Path, component_name: str) -> List[Path]:
        """Find all files related to a component"""
        files = []
        
        # Common file extensions for components
        extensions = [".tsx", ".ts", ".jsx", ".js", ".py", ".vue", ".svelte"]
        
        for ext in extensions:
            # Direct matches
            for pattern in [
                f"**/{component_name}{ext}",
                f"**/{component_name.lower()}{ext}",
                f"**/{component_name}/**/*{ext}"
            ]:
                files.extend(repo_path.glob(pattern))
        
        return list(set(files))[:5]  # Limit to 5 files per component

    async def _read_component_source(self, file_paths: List[Path]) -> Dict[str, str]:
        """Read source code from component files"""
        source_code = {}
        
        for file_path in file_paths:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Limit content size for AI processing
                    if len(content) > 10000:
                        content = content[:10000] + "\n... (truncated)"
                    source_code[str(file_path)] = content
            except Exception as e:
                logger.error(f"Failed to read file {file_path}: {e}")
                continue
        
        return source_code

    async def _ai_analyze_component(self, component_name: str, source_code: Dict[str, str]) -> Dict[str, Any]:
        """Use AI to analyze component"""
        
        prompt = f"""
        Analyze this component '{component_name}' and its source code:
        
        Source Files:
        {json.dumps({k: v[:2000] for k, v in source_code.items()}, indent=2)}
        
        Provide analysis in JSON format:
        {{
            "type": "React Component|Service|Module|API|etc",
            "description": "Brief description of what this component does",
            "interfaces": ["list of public methods/props"],
            "dependencies": ["list of external dependencies"],
            "usage_examples": ["example usage patterns"],
            "complexity": "Low|Medium|High",
            "testing_coverage": "description of test coverage",
            "documentation_level": "Poor|Fair|Good|Excellent"
        }}
        """
        
        try:
            response = await self.generator.acall(prompt)
            # Try to parse JSON response
            analysis = json.loads(response.data)
            return analysis
        except Exception as e:
            logger.error(f"Failed to analyze component {component_name}: {e}")
            return {
                "type": "Component",
                "description": f"Component {component_name}",
                "interfaces": [],
                "dependencies": [],
                "usage_examples": []
            }

    async def _generate_component_documentation(self, component_name: str, 
                                              analysis: Dict[str, Any], 
                                              source_code: Dict[str, str]) -> str:
        """Generate Confluence documentation for component"""
        
        prompt = f"""
        Generate comprehensive Confluence documentation for component '{component_name}':
        
        Analysis: {json.dumps(analysis, indent=2)}
        
        Include:
        1. Component Overview
        2. Purpose and Functionality
        3. Public Interface (methods, props, APIs)
        4. Dependencies and Requirements
        5. Usage Examples with code
        6. Configuration Options
        7. Testing Guidelines
        8. Best Practices
        9. Known Issues/Limitations
        
        Format as Confluence wiki markup with proper headings, code blocks, and tables.
        """
        
        try:
            response = await self.generator.acall(prompt)
            return response.data
        except Exception as e:
            logger.error(f"Failed to generate documentation for {component_name}: {e}")
            return self._generate_fallback_documentation(component_name, analysis)

    def _generate_fallback_documentation(self, component_name: str, analysis: Dict[str, Any]) -> str:
        """Generate fallback documentation if AI fails"""
        
        interfaces_list = "\n".join([f"- {interface}" for interface in analysis.get("interfaces", [])])
        dependencies_list = "\n".join([f"- {dep}" for dep in analysis.get("dependencies", [])])
        examples_list = "\n".join([f"- {example}" for example in analysis.get("usage_examples", [])])
        
        return f"""
# {component_name} Component Documentation

## Overview
{analysis.get('description', f'Component {component_name}')}

**Type:** {analysis.get('type', 'Component')}

## Public Interface
{interfaces_list or "- No public interfaces documented"}

## Dependencies
{dependencies_list or "- No dependencies identified"}

## Usage Examples
{examples_list or "- No usage examples available"}

## Configuration
Configuration details to be documented.

## Testing
Testing guidelines to be documented.

## Notes
- Complexity: {analysis.get('complexity', 'Unknown')}
- Documentation Level: {analysis.get('documentation_level', 'Unknown')}
        """