"""
Markdown Exporter for generating documentation files when Confluence is not available
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime
import json
import os

logger = logging.getLogger(__name__)

class MarkdownExporter:
    """Exports documentation to markdown files for testing without Confluence"""
    
    def __init__(self, output_dir: str = "docs_export"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
    async def export_project_documentation(self, project_name: str, 
                                         architecture_result: Dict[str, Any],
                                         components_result: Dict[str, Any], 
                                         usage_result: Dict[str, Any]) -> Dict[str, str]:
        """Export all documentation to markdown files"""
        
        exported_files = {}
        
        try:
            # Create project directory
            project_dir = self.output_dir / self._sanitize_filename(project_name)
            project_dir.mkdir(exist_ok=True)
            
            # Export architecture documentation
            arch_file = await self._export_architecture_markdown(
                project_dir, project_name, architecture_result
            )
            exported_files["architecture"] = str(arch_file)
            
            # Export component documentation
            component_files = await self._export_components_markdown(
                project_dir, project_name, components_result
            )
            exported_files["components"] = component_files
            
            # Export usage documentation
            usage_file = await self._export_usage_markdown(
                project_dir, project_name, usage_result
            )
            exported_files["usage"] = str(usage_file)
            
            # Create index file
            index_file = await self._create_index_file(
                project_dir, project_name, exported_files
            )
            exported_files["index"] = str(index_file)
            
            logger.info(f"Exported documentation for {project_name} to {project_dir}")
            return exported_files
            
        except Exception as e:
            logger.error(f"Failed to export documentation: {e}")
            raise

    async def _export_architecture_markdown(self, project_dir: Path, project_name: str, 
                                          architecture_result: Dict[str, Any]) -> Path:
        """Export architecture documentation to markdown"""
        
        file_path = project_dir / "01-architecture.md"
        
        content = f"""# {project_name} - Architecture Overview

*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*

## Project Structure

### Overview
- **Total Files**: {architecture_result.get('project_structure', {}).get('total_files', 'Unknown')}
- **Directories**: {len(architecture_result.get('project_structure', {}).get('directories', {}))}

### File Types Distribution
"""
        
        # Add file types table
        file_types = architecture_result.get('project_structure', {}).get('file_types', {})
        if file_types:
            content += "\n| File Type | Count |\n|-----------|-------|\n"
            for ext, count in sorted(file_types.items()):
                content += f"| `{ext}` | {count} |\n"
        
        content += f"""

## Key Components

The following key components have been identified in the system:

"""
        
        # Add key components list
        key_components = architecture_result.get('key_components', [])
        for component in key_components:
            content += f"- **{component}**\n"
        
        content += f"""

## Architecture Patterns

The system implements the following architectural patterns:

"""
        
        # Add architecture patterns
        patterns = architecture_result.get('architecture_patterns', [])
        for pattern in patterns:
            content += f"- **{pattern}**\n"
        
        content += f"""

## Dependencies

### Frontend Dependencies
"""
        
        # Add dependencies
        dependencies = architecture_result.get('dependencies', {})
        frontend_deps = dependencies.get('frontend', [])
        if frontend_deps:
            for dep in frontend_deps[:10]:  # Limit to first 10
                content += f"- `{dep}`\n"
        else:
            content += "- No frontend dependencies identified\n"
        
        content += f"""
### Backend Dependencies
"""
        
        backend_deps = dependencies.get('backend', [])
        if backend_deps:
            for dep in backend_deps[:10]:  # Limit to first 10
                content += f"- `{dep}`\n"
        else:
            content += "- No backend dependencies identified\n"
        
        # Add mermaid diagrams if available
        diagrams = architecture_result.get('mermaid_diagrams', [])
        if diagrams:
            content += f"""

## Architecture Diagrams

"""
            for i, diagram in enumerate(diagrams[:3]):  # Limit to first 3
                content += f"""
### Diagram {i+1}

```mermaid
{diagram}
```

"""
        
        # Write file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return file_path

    async def _export_components_markdown(self, project_dir: Path, project_name: str,
                                        components_result: Dict[str, Any]) -> Dict[str, str]:
        """Export component documentation to markdown files"""
        
        component_files = {}
        components_dir = project_dir / "components"
        components_dir.mkdir(exist_ok=True)
        
        components = components_result.get('components', {})
        
        # Create components index
        index_content = f"""# {project_name} - Components

*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*

This section contains detailed documentation for each component in the system.

## Components List

"""
        
        for component_name, component_data in components.items():
            # Create individual component file
            file_path = components_dir / f"{self._sanitize_filename(component_name)}.md"
            
            component_content = f"""# {component_name} Component

## Overview

**Type**: {component_data.get('type', 'Unknown')}  
**Complexity**: {component_data.get('complexity', 'Unknown')}  
**Documentation Level**: {component_data.get('documentation_level', 'Unknown')}

## Description

{component_data.get('description', 'No description available')}

## Public Interface

The component exposes the following interfaces:

"""
            
            interfaces = component_data.get('interfaces', [])
            if interfaces:
                for interface in interfaces:
                    component_content += f"- `{interface}`\n"
            else:
                component_content += "- No public interfaces documented\n"
            
            component_content += f"""

## Dependencies

This component depends on:

"""
            
            dependencies = component_data.get('dependencies', [])
            if dependencies:
                for dep in dependencies:
                    component_content += f"- `{dep}`\n"
            else:
                component_content += "- No dependencies identified\n"
            
            component_content += f"""

## Usage Examples

"""
            
            usage_examples = component_data.get('usage_examples', [])
            if usage_examples:
                for i, example in enumerate(usage_examples):
                    component_content += f"""
### Example {i+1}

```
{example}
```

"""
            else:
                component_content += "No usage examples available.\n"
            
            # Add testing information if available
            testing_coverage = component_data.get('testing_coverage', 'Unknown')
            if testing_coverage != 'Unknown':
                component_content += f"""

## Testing

**Coverage**: {testing_coverage}

"""
            
            # Write component file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(component_content)
            
            component_files[component_name] = str(file_path)
            
            # Add to index
            index_content += f"- [{component_name}](components/{self._sanitize_filename(component_name)}.md) - {component_data.get('description', 'No description')[:100]}...\n"
        
        # Write components index
        index_file = project_dir / "02-components.md"
        with open(index_file, 'w', encoding='utf-8') as f:
            f.write(index_content)
        
        component_files["_index"] = str(index_file)
        return component_files

    async def _export_usage_markdown(self, project_dir: Path, project_name: str,
                                   usage_result: Dict[str, Any]) -> Path:
        """Export usage documentation to markdown"""
        
        file_path = project_dir / "03-usage-guide.md"
        
        content = f"""# {project_name} - Usage Guide

*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*

## Getting Started

{usage_result.get('getting_started', 'Getting started guide not available')}

## API Examples

"""
        
        # Add API examples
        api_examples = usage_result.get('api_examples', [])
        if api_examples:
            for example_group in api_examples:
                group_name = example_group.get('group', 'API Group')
                content += f"""
### {group_name.title()} APIs

{example_group.get('description', 'No description available')}

"""
                
                examples = example_group.get('examples', [])
                for example in examples:
                    content += f"""
#### {example.get('method', 'GET')} {example.get('endpoint', '/api/endpoint')}

{example.get('description', 'No description available')}

**Request Example:**
```bash
{example.get('request_example', 'No example available')}
```

**Response Example:**
```json
{example.get('response_example', '{}')}
```

**Use Cases:**
"""
                    use_cases = example.get('use_cases', [])
                    for use_case in use_cases:
                        content += f"- {use_case}\n"
                    
                    content += "\n"
        else:
            content += "No API examples available.\n"
        
        # Add integration guides
        content += f"""

## Integration Guides

"""
        
        integration_guides = usage_result.get('integration_guides', [])
        if integration_guides:
            for guide in integration_guides:
                content += f"""
### {guide.get('title', 'Integration Guide')}

{guide.get('content', 'No content available')}

"""
        else:
            content += "No integration guides available.\n"
        
        # Add troubleshooting
        content += f"""

## Troubleshooting

{usage_result.get('troubleshooting', 'No troubleshooting guide available')}

## Best Practices

"""
        
        # Add best practices
        best_practices = usage_result.get('best_practices', [])
        if best_practices:
            for practice in best_practices:
                content += f"- {practice}\n"
        else:
            content += "No best practices documented.\n"
        
        # Write file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return file_path

    async def _create_index_file(self, project_dir: Path, project_name: str, 
                               exported_files: Dict[str, Any]) -> Path:
        """Create main index file for the project documentation"""
        
        file_path = project_dir / "README.md"
        
        content = f"""# {project_name} - Documentation

*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*

This documentation has been automatically generated for the {project_name} project.

## 📚 Documentation Structure

### Core Documentation

1. **[Architecture Overview](01-architecture.md)** - System architecture, patterns, and dependencies
2. **[Components](02-components.md)** - Detailed component documentation
3. **[Usage Guide](03-usage-guide.md)** - Getting started, API examples, and best practices

### Component Details

"""
        
        # Add component links if available
        component_files = exported_files.get('components', {})
        if isinstance(component_files, dict):
            for component_name, file_path in component_files.items():
                if component_name != '_index':
                    relative_path = Path(file_path).relative_to(project_dir)
                    content += f"- [{component_name}]({relative_path})\n"
        
        content += f"""

## 🚀 Quick Navigation

- **New to the project?** Start with the [Usage Guide](03-usage-guide.md)
- **Want to understand the system?** Check the [Architecture Overview](01-architecture.md)
- **Looking for specific components?** Browse the [Components](02-components.md) section

## 📝 Notes

This documentation was automatically generated using AI analysis of the codebase. 
For the most up-to-date information, please refer to the source code and any 
existing manual documentation.

---

*Generated by DeepWiki Confluence Documentation Generator*
"""
        
        # Write file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return file_path

    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for filesystem compatibility"""
        # Remove or replace invalid characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        
        # Remove multiple underscores and strip
        filename = '_'.join(filter(None, filename.split('_')))
        
        # Ensure it's not empty and not too long
        if not filename:
            filename = "unnamed"
        if len(filename) > 100:
            filename = filename[:100]
        
        return filename.lower()

    async def export_single_component(self, component_name: str, component_data: Dict[str, Any],
                                    output_file: Optional[str] = None) -> str:
        """Export a single component to markdown file"""
        
        if not output_file:
            output_file = f"{self._sanitize_filename(component_name)}_component.md"
        
        file_path = self.output_dir / output_file
        
        content = f"""# {component_name} Component Documentation

*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*

## Overview

**Type**: {component_data.get('type', 'Unknown')}  
**Complexity**: {component_data.get('complexity', 'Unknown')}  

## Description

{component_data.get('description', 'No description available')}

## Interfaces

"""
        
        interfaces = component_data.get('interfaces', [])
        if interfaces:
            for interface in interfaces:
                content += f"- `{interface}`\n"
        else:
            content += "No interfaces documented\n"
        
        content += f"""

## Dependencies

"""
        
        dependencies = component_data.get('dependencies', [])
        if dependencies:
            for dep in dependencies:
                content += f"- `{dep}`\n"
        else:
            content += "No dependencies identified\n"
        
        content += f"""

## Usage Examples

"""
        
        usage_examples = component_data.get('usage_examples', [])
        if usage_examples:
            for example in usage_examples:
                content += f"```\n{example}\n```\n\n"
        else:
            content += "No usage examples available\n"
        
        # Write file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"Exported component {component_name} to {file_path}")
        return str(file_path)

    def get_export_summary(self, project_dir: Path) -> Dict[str, Any]:
        """Get summary of exported files"""
        
        if not project_dir.exists():
            return {"error": "Project directory does not exist"}
        
        files = list(project_dir.rglob("*.md"))
        
        return {
            "project_directory": str(project_dir),
            "total_files": len(files),
            "files": [str(f.relative_to(project_dir)) for f in files],
            "size_mb": sum(f.stat().st_size for f in files) / 1024 / 1024,
            "created": datetime.now().isoformat()
        }