"""
Usage Documentation Agent
Generates usage guides and examples for components and APIs
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
from dataclasses import dataclass
import json
import re

from adalflow import Component, Generator, get_logger

logger = get_logger(__name__)

@dataclass
class UsageDocumentation:
    getting_started: str
    api_examples: List[Dict[str, str]]
    integration_guides: List[Dict[str, str]]
    troubleshooting: str
    best_practices: List[str]
    confluence_content: str

class UsageAgent(Component):
    """Agent responsible for generating usage documentation"""
    
    def __init__(self):
        super().__init__()
        self.generator = Generator(
            model_client="google",
            model_kwargs={"model": "gemini-2.5-flash", "temperature": 0.2}
        )
    
    async def generate_usage_docs(self, repo_url: str, components: List[str] = None) -> Dict[str, Any]:
        """Generate comprehensive usage documentation"""
        try:
            logger.info(f"Starting usage documentation generation for {repo_url}")
            
            repo_path = await self._get_repo_path(repo_url)
            
            # Analyze project for usage patterns
            project_info = await self._analyze_project_for_usage(repo_path)
            
            # Generate getting started guide
            getting_started = await self._generate_getting_started(repo_path, project_info)
            
            # Generate API examples
            api_examples = await self._generate_api_examples(repo_path, project_info)
            
            # Generate integration guides
            integration_guides = await self._generate_integration_guides(repo_path, project_info)
            
            # Generate troubleshooting guide
            troubleshooting = await self._generate_troubleshooting(repo_path, project_info)
            
            # Generate best practices
            best_practices = await self._generate_best_practices(repo_path, project_info)
            
            # Generate consolidated Confluence content
            confluence_content = await self._generate_usage_confluence_content(
                getting_started, api_examples, integration_guides, troubleshooting, best_practices
            )
            
            result = {
                "getting_started": getting_started,
                "api_examples": api_examples,
                "integration_guides": integration_guides,
                "troubleshooting": troubleshooting,
                "best_practices": best_practices,
                "confluence_content": confluence_content
            }
            
            logger.info("Usage documentation generation completed")
            return result
            
        except Exception as e:
            logger.error(f"Usage documentation generation failed: {e}")
            raise

    async def _get_repo_path(self, repo_url: str) -> Path:
        """Get local repository path"""
        repo_name = repo_url.split("/")[-1].replace(".git", "")
        return Path(f"/tmp/repos/{repo_name}")

    async def _analyze_project_for_usage(self, repo_path: Path) -> Dict[str, Any]:
        """Analyze project to understand usage patterns"""
        project_info = {
            "readme_content": "",
            "package_info": {},
            "api_endpoints": [],
            "example_files": [],
            "config_files": [],
            "docker_setup": False,
            "test_files": []
        }
        
        # Read README files
        readme_files = ["README.md", "README.rst", "readme.txt"]
        for readme_file in readme_files:
            readme_path = repo_path / readme_file
            if readme_path.exists():
                try:
                    with open(readme_path, 'r', encoding='utf-8') as f:
                        project_info["readme_content"] = f.read()
                        break
                except Exception as e:
                    logger.error(f"Failed to read README: {e}")
        
        # Check package.json
        package_json = repo_path / "package.json"
        if package_json.exists():
            try:
                with open(package_json, 'r') as f:
                    project_info["package_info"] = json.load(f)
            except Exception as e:
                logger.error(f"Failed to read package.json: {e}")
        
        # Find API endpoints
        project_info["api_endpoints"] = await self._find_api_endpoints(repo_path)
        
        # Find example files
        project_info["example_files"] = await self._find_example_files(repo_path)
        
        # Find configuration files
        project_info["config_files"] = await self._find_config_files(repo_path)
        
        # Check for Docker setup
        project_info["docker_setup"] = (repo_path / "Dockerfile").exists() or (repo_path / "docker-compose.yml").exists()
        
        # Find test files
        project_info["test_files"] = await self._find_test_files(repo_path)
        
        return project_info

    async def _find_api_endpoints(self, repo_path: Path) -> List[Dict[str, str]]:
        """Find API endpoints in the project"""
        endpoints = []
        
        # Look for common API patterns
        api_patterns = [
            "**/*api*.py",
            "**/*route*.py",
            "**/*endpoint*.py",
            "**/api/**/*.py",
            "**/routes/**/*.py"
        ]
        
        for pattern in api_patterns:
            for file_path in repo_path.glob(pattern):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        # Extract API routes using regex
                        route_patterns = [
                            r'@app\.(get|post|put|delete|patch)\(["\']([^"\']+)["\']',
                            r'router\.(get|post|put|delete|patch)\(["\']([^"\']+)["\']',
                            r'@router\.(get|post|put|delete|patch)\(["\']([^"\']+)["\']'
                        ]
                        
                        for route_pattern in route_patterns:
                            matches = re.findall(route_pattern, content)
                            for method, route in matches:
                                endpoints.append({
                                    "method": method.upper(),
                                    "path": route,
                                    "file": str(file_path.relative_to(repo_path))
                                })
                except Exception as e:
                    logger.error(f"Failed to analyze API file {file_path}: {e}")
        
        return endpoints[:20]  # Limit to 20 endpoints

    async def _find_example_files(self, repo_path: Path) -> List[str]:
        """Find example files in the project"""
        example_files = []
        
        example_patterns = [
            "**/example*",
            "**/examples/**/*",
            "**/demo*",
            "**/sample*",
            "**/tutorial*"
        ]
        
        for pattern in example_patterns:
            for file_path in repo_path.glob(pattern):
                if file_path.is_file():
                    example_files.append(str(file_path.relative_to(repo_path)))
        
        return example_files[:10]  # Limit to 10 examples

    async def _find_config_files(self, repo_path: Path) -> List[str]:
        """Find configuration files"""
        config_files = []
        
        config_patterns = [
            "*.json",
            "*.yaml",
            "*.yml",
            "*.toml",
            "*.ini",
            "*.env*",
            "**/config/**/*"
        ]
        
        for pattern in config_patterns:
            for file_path in repo_path.glob(pattern):
                if file_path.is_file():
                    config_files.append(str(file_path.relative_to(repo_path)))
        
        return config_files[:15]  # Limit to 15 config files

    async def _find_test_files(self, repo_path: Path) -> List[str]:
        """Find test files"""
        test_files = []
        
        test_patterns = [
            "**/test_*.py",
            "**/*_test.py",
            "**/tests/**/*.py",
            "**/*.test.js",
            "**/*.test.ts",
            "**/*.spec.js",
            "**/*.spec.ts"
        ]
        
        for pattern in test_patterns:
            for file_path in repo_path.glob(pattern):
                test_files.append(str(file_path.relative_to(repo_path)))
        
        return test_files[:10]  # Limit to 10 test files

    async def _generate_getting_started(self, repo_path: Path, project_info: Dict) -> str:
        """Generate getting started guide"""
        
        prompt = f"""
        Generate a comprehensive "Getting Started" guide based on this project information:
        
        README Content: {project_info["readme_content"][:3000]}
        Package Info: {json.dumps(project_info.get("package_info", {}), indent=2)[:1000]}
        Docker Setup: {project_info["docker_setup"]}
        Config Files: {project_info["config_files"][:5]}
        
        Include:
        1. Prerequisites and requirements
        2. Installation instructions
        3. Basic configuration
        4. First steps to run the application
        5. Verification steps
        
        Make it beginner-friendly and step-by-step.
        """
        
        try:
            response = await self.generator.acall(prompt)
            return response.data
        except Exception as e:
            logger.error(f"Failed to generate getting started guide: {e}")
            return self._generate_fallback_getting_started(project_info)

    async def _generate_api_examples(self, repo_path: Path, project_info: Dict) -> List[Dict[str, str]]:
        """Generate API usage examples"""
        api_examples = []
        
        if not project_info["api_endpoints"]:
            return api_examples
        
        # Group endpoints by functionality
        endpoint_groups = {}
        for endpoint in project_info["api_endpoints"]:
            path_parts = endpoint["path"].split("/")
            group_name = path_parts[1] if len(path_parts) > 1 else "general"
            if group_name not in endpoint_groups:
                endpoint_groups[group_name] = []
            endpoint_groups[group_name].append(endpoint)
        
        # Generate examples for each group
        for group_name, endpoints in list(endpoint_groups.items())[:5]:  # Limit to 5 groups
            prompt = f"""
            Generate API usage examples for the '{group_name}' group with these endpoints:
            {json.dumps(endpoints, indent=2)}
            
            For each endpoint, provide:
            1. Description of what it does
            2. Request example (curl and/or code)
            3. Response example
            4. Common use cases
            
            Return as JSON with structure:
            {{
                "group": "{group_name}",
                "description": "Group description",
                "examples": [
                    {{
                        "endpoint": "endpoint_path",
                        "method": "HTTP_METHOD",
                        "description": "What this endpoint does",
                        "request_example": "curl example or code",
                        "response_example": "expected response",
                        "use_cases": ["use case 1", "use case 2"]
                    }}
                ]
            }}
            """
            
            try:
                response = await self.generator.acall(prompt)
                example_data = json.loads(response.data)
                api_examples.append(example_data)
            except Exception as e:
                logger.error(f"Failed to generate API examples for {group_name}: {e}")
                # Add fallback example
                api_examples.append({
                    "group": group_name,
                    "description": f"API endpoints for {group_name}",
                    "examples": [
                        {
                            "endpoint": ep["path"],
                            "method": ep["method"],
                            "description": f"{ep['method']} endpoint",
                            "request_example": f"curl -X {ep['method']} /api{ep['path']}",
                            "response_example": "{}",
                            "use_cases": ["Basic usage"]
                        } for ep in endpoints[:3]
                    ]
                })
        
        return api_examples

    async def _generate_integration_guides(self, repo_path: Path, project_info: Dict) -> List[Dict[str, str]]:
        """Generate integration guides"""
        integration_guides = []
        
        # Determine integration scenarios based on project structure
        integration_scenarios = []
        
        if project_info["docker_setup"]:
            integration_scenarios.append("Docker Deployment")
        
        if any("test" in f for f in project_info.get("config_files", [])):
            integration_scenarios.append("Testing Integration")
        
        if "package.json" in str(project_info.get("package_info", {})):
            integration_scenarios.append("Frontend Integration")
        
        if any(ep["method"] == "POST" for ep in project_info.get("api_endpoints", [])):
            integration_scenarios.append("API Integration")
        
        # Default scenarios
        if not integration_scenarios:
            integration_scenarios = ["Basic Integration", "Development Setup"]
        
        # Generate guides for each scenario
        for scenario in integration_scenarios[:4]:  # Limit to 4 scenarios
            prompt = f"""
            Generate an integration guide for '{scenario}' scenario based on:
            
            Project Info: {json.dumps({k: v for k, v in project_info.items() if k != "readme_content"}, indent=2)[:2000]}
            
            Include:
            1. Overview of the integration
            2. Step-by-step instructions
            3. Configuration requirements
            4. Common integration patterns
            5. Troubleshooting tips
            
            Make it practical and actionable.
            """
            
            try:
                response = await self.generator.acall(prompt)
                integration_guides.append({
                    "title": f"{scenario} Guide",
                    "content": response.data
                })
            except Exception as e:
                logger.error(f"Failed to generate integration guide for {scenario}: {e}")
        
        return integration_guides

    async def _generate_troubleshooting(self, repo_path: Path, project_info: Dict) -> str:
        """Generate troubleshooting guide"""
        
        prompt = f"""
        Generate a comprehensive troubleshooting guide based on this project:
        
        Project Type: Based on files and structure
        Docker Setup: {project_info["docker_setup"]}
        API Endpoints: {len(project_info.get("api_endpoints", []))} endpoints
        Config Files: {project_info["config_files"][:5]}
        
        Include common issues and solutions for:
        1. Installation and setup problems
        2. Configuration issues
        3. Runtime errors
        4. API connectivity problems
        5. Performance issues
        6. Docker-related issues (if applicable)
        
        Format as FAQ with clear problem descriptions and step-by-step solutions.
        """
        
        try:
            response = await self.generator.acall(prompt)
            return response.data
        except Exception as e:
            logger.error(f"Failed to generate troubleshooting guide: {e}")
            return self._generate_fallback_troubleshooting()

    async def _generate_best_practices(self, repo_path: Path, project_info: Dict) -> List[str]:
        """Generate best practices"""
        
        prompt = f"""
        Generate best practices for using this project based on:
        
        Project Structure and Files
        API Endpoints: {len(project_info.get("api_endpoints", []))}
        Test Files: {len(project_info.get("test_files", []))}
        Config Files: {project_info["config_files"][:5]}
        
        Return a list of best practices covering:
        1. Development practices
        2. Configuration management
        3. API usage
        4. Testing
        5. Deployment
        6. Monitoring
        7. Security
        
        Each practice should be concise and actionable.
        """
        
        try:
            response = await self.generator.acall(prompt)
            # Parse list from response
            practices = self._parse_list_from_response(response.data)
            return practices
        except Exception as e:
            logger.error(f"Failed to generate best practices: {e}")
            return self._generate_fallback_best_practices()

    async def _generate_usage_confluence_content(self, getting_started: str, api_examples: List, 
                                               integration_guides: List, troubleshooting: str, 
                                               best_practices: List[str]) -> str:
        """Generate consolidated Confluence content for usage documentation"""
        
        api_examples_content = ""
        for example_group in api_examples:
            api_examples_content += f"\n## {example_group['group'].title()} APIs\n"
            api_examples_content += f"{example_group['description']}\n\n"
            for example in example_group.get('examples', []):
                api_examples_content += f"### {example['method']} {example['endpoint']}\n"
                api_examples_content += f"{example['description']}\n\n"
                api_examples_content += f"**Request Example:**\n```\n{example['request_example']}\n```\n\n"
                api_examples_content += f"**Response Example:**\n```json\n{example['response_example']}\n```\n\n"
        
        integration_guides_content = ""
        for guide in integration_guides:
            integration_guides_content += f"\n## {guide['title']}\n{guide['content']}\n"
        
        best_practices_content = "\n".join([f"- {practice}" for practice in best_practices])
        
        confluence_content = f"""
# Usage Guide

## Getting Started
{getting_started}

# API Examples
{api_examples_content}

# Integration Guides
{integration_guides_content}

## Troubleshooting
{troubleshooting}

## Best Practices
{best_practices_content}
        """
        
        return confluence_content

    def _parse_list_from_response(self, response: str) -> List[str]:
        """Parse list items from AI response"""
        lines = response.split('\n')
        practices = []
        for line in lines:
            line = line.strip()
            if line and (line.startswith('-') or line.startswith('*') or line[0].isdigit()):
                # Remove bullet points and numbering
                practice = re.sub(r'^[-*0-9.\s]+', '', line).strip()
                if practice:
                    practices.append(practice)
        return practices[:15]  # Limit to 15 practices

    def _generate_fallback_getting_started(self, project_info: Dict) -> str:
        """Generate fallback getting started guide"""
        return f"""
# Getting Started

## Prerequisites
- Node.js (for frontend applications)
- Python (for backend services)
- Docker (if using containerization)

## Installation
1. Clone the repository
2. Install dependencies:
   - For Node.js: `npm install`
   - For Python: `pip install -r requirements.txt`
3. Configure environment variables
4. Run the application

## Configuration
Check the configuration files:
{chr(10).join([f"- {f}" for f in project_info.get("config_files", [])[:5]])}

## Running the Application
Follow the instructions in the project README file.
        """

    def _generate_fallback_troubleshooting(self) -> str:
        """Generate fallback troubleshooting guide"""
        return """
# Troubleshooting

## Common Issues

### Installation Problems
- Check that all prerequisites are installed
- Verify network connectivity
- Clear cache and retry

### Configuration Issues
- Verify environment variables are set correctly
- Check configuration file syntax
- Ensure proper file permissions

### Runtime Errors
- Check application logs
- Verify all services are running
- Test network connectivity

### Performance Issues
- Monitor resource usage
- Check for memory leaks
- Optimize database queries
        """

    def _generate_fallback_best_practices(self) -> List[str]:
        """Generate fallback best practices"""
        return [
            "Follow consistent code style and formatting",
            "Write comprehensive unit tests for all components",
            "Use environment variables for configuration",
            "Implement proper error handling and logging",
            "Document all public APIs and interfaces",
            "Use version control best practices",
            "Implement continuous integration and deployment",
            "Monitor application performance and errors",
            "Keep dependencies up to date",
            "Follow security best practices"
        ]