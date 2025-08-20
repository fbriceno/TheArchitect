# Confluence Documentation Generator

Una aplicación avanzada que extiende DeepWiki para generar documentación automática de arquitectura y componentes para Confluence, con agentes paralelos y servicio MCP.

## 🏗️ Arquitectura

### Componentes Principales

1. **Main API** (`main.py`): Servicio principal que orquesta la generación de documentación
2. **Agentes Paralelos** (`agents/`): Agentes especializados para análisis de arquitectura, componentes y uso
3. **Base de Datos** (`database/`): PostgreSQL para almacenar información de componentes y documentación
4. **Servicio MCP** (`mcp_server.py`): Servicio para exponer datos de componentes via MCP
5. **SDK de Agentes** (`sdk/`): Framework para crear nuevos agentes de documentación
6. **Cliente Confluence** (`confluence_client.py`): Cliente para integración con Confluence

### Flujo de Trabajo

```mermaid
graph TD
    A[Usuario solicita documentación] --> B[API Principal]
    B --> C[Crea Agentes Paralelos]
    C --> D[Agente Arquitectura]
    C --> E[Agente Componentes]
    C --> F[Agente Uso]
    D --> G[Base de Datos]
    E --> G
    F --> G
    G --> H[Cliente Confluence]
    H --> I[Páginas Confluence]
    G --> J[Servicio MCP]
    J --> K[Otros Agentes]
```

## 🚀 Características

- **Análisis de Arquitectura**: Detecta patrones, dependencias y estructura del proyecto
- **Documentación de Componentes**: Genera documentación detallada para cada componente
- **Guías de Uso**: Crea guías de inicio rápido, ejemplos de API y mejores prácticas
- **Agentes Paralelos**: Procesamiento simultáneo para máxima eficiencia
- **Servicio MCP**: Expone datos para que otros agentes puedan completar secciones
- **SDK Extensible**: Framework para crear agentes personalizados
- **Base de Datos PostgreSQL**: Almacenamiento robusto y escalable
- **Integración Confluence**: Creación y actualización automática de páginas
- **📝 Export Markdown**: Genera archivos markdown para pruebas sin Confluence
- **Formatos Múltiples**: Soporta Confluence, Markdown, o ambos simultáneamente

## 🛠️ Instalación y Configuración

### Opción 1: Docker Compose (Recomendado)

1. **Clonar el proyecto**:
```bash
git clone <repo-url>
cd deepwiki-open-main
```

2. **Configurar variables de entorno**:
```bash
cp .env.confluence.example .env
# Editar .env con tus claves API y configuración de Confluence
```

3. **Iniciar todos los servicios**:
```bash
docker-compose -f docker-compose.confluence.yml up -d
```

4. **Verificar servicios**:
```bash
# API Principal
curl http://localhost:8002/health

# Servicio MCP
curl http://localhost:8003/health

# Monitoring
open http://localhost:3001  # Grafana (admin/admin)
open http://localhost:9090  # Prometheus
```

### Opción 2: Instalación Manual

1. **Configurar base de datos (Recomendado: usar script)**:
```bash
# Setup automático de desarrollo
./scripts/setup-database.sh dev

# O setup manual
docker-compose -f docker-compose.dev.yml up -d postgres-dev
```

2. **Instalar dependencias**:
```bash
pip install -r confluence_generator/requirements.txt
```

3. **Configurar variables de entorno**:
```bash
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5433  # Puerto de desarrollo
export POSTGRES_DB=confluence_docs
export POSTGRES_USER=postgres
export POSTGRES_PASSWORD=password
export GOOGLE_API_KEY=AIzaSyBNxsPt3n1xUUq1azgf8dtbiYjXcgtp8TM
export OPENAI_API_KEY=your_key
export CONFLUENCE_BASE_URL=https://your-company.atlassian.net
export CONFLUENCE_USERNAME=your_email
export CONFLUENCE_API_TOKEN=your_token
```

4. **Verificar base de datos**:
```bash
./scripts/test-database.sh
```

5. **Ejecutar servicios**:
```bash
# API Principal
python -m confluence_generator.main

# Servicio MCP (en otra terminal)
python -c "import asyncio; from confluence_generator.mcp_server import MCPServer; asyncio.run(MCPServer().start())"

# Workers (en otra terminal)
python -m confluence_generator.worker
```

## 📖 Uso

### 1. Generar Documentación para Confluence

```bash
curl -X POST http://localhost:8002/generate-documentation \
  -H "Content-Type: application/json" \
  -d '{
    "repo_url": "https://github.com/user/repo",
    "confluence_space": "DOCS",
    "project_name": "Mi Proyecto",
    "components": ["ComponentA", "ComponentB"],
    "export_format": "confluence"
  }'
```

### 1.1. Generar Documentación en Markdown (Sin Confluence)

Para probar sin configurar Confluence:

```bash
curl -X POST http://localhost:8002/generate-markdown \
  -H "Content-Type: application/json" \
  -d '{
    "repo_url": "https://github.com/user/repo",
    "project_name": "Mi Proyecto",
    "components": ["ComponentA", "ComponentB"],
    "output_dir": "my_docs_export"
  }'
```

### 1.2. Generar Ambos Formatos

```bash
curl -X POST http://localhost:8002/generate-documentation \
  -H "Content-Type: application/json" \
  -d '{
    "repo_url": "https://github.com/user/repo",
    "confluence_space": "DOCS",
    "project_name": "Mi Proyecto",
    "components": ["ComponentA", "ComponentB"],
    "export_format": "both",
    "output_dir": "backup_docs"
  }'
```

### 2. Consultar Estado del Trabajo

```bash
curl http://localhost:8002/jobs/{job_id}
```

El resultado incluirá información sobre archivos markdown generados:

```json
{
  "job_id": "doc_20241217_143022",
  "status": "completed",
  "confluence_pages": [...],
  "markdown_files": {
    "index": "docs_export/Mi_Proyecto/README.md",
    "architecture": "docs_export/Mi_Proyecto/01-architecture.md",
    "usage": "docs_export/Mi_Proyecto/03-usage-guide.md",
    "components": {
      "ComponentA": "docs_export/Mi_Proyecto/components/componenta.md",
      "_index": "docs_export/Mi_Proyecto/02-components.md"
    }
  }
}
```

## 📁 Estructura de Archivos Markdown Generados

Cuando usas el formato markdown, la estructura de archivos es:

```
docs_export/
└── Mi_Proyecto/
    ├── README.md                    # Índice principal
    ├── 01-architecture.md           # Documentación de arquitectura
    ├── 02-components.md             # Índice de componentes
    ├── 03-usage-guide.md            # Guía de uso
    └── components/
        ├── componenta.md            # Documentación del ComponenteA
        ├── componentb.md            # Documentación del ComponenteB
        └── ...
```

### Contenido de los Archivos

- **README.md**: Índice navegable con enlaces a toda la documentación
- **01-architecture.md**: Análisis de arquitectura, patrones, dependencias y diagramas Mermaid
- **02-components.md**: Índice de componentes con descripciones breves
- **03-usage-guide.md**: Guía completa de uso, API, integración y troubleshooting
- **components/*.md**: Documentación detallada de cada componente individual

### 3. Usar el Servicio MCP

```bash
# Obtener arquitectura de proyecto
curl http://localhost:8003/mcp/projects/{project_id}/architecture

# Buscar componentes
curl -X POST http://localhost:8003/mcp/components/search \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "project_id",
    "search_query": "component_name"
  }'

# Obtener estadísticas
curl http://localhost:8003/mcp/projects/{project_id}/statistics
```

## 🤖 Crear Agentes Personalizados

### Ejemplo de Agente Personalizado

```python
from confluence_generator.sdk import BaseAgent, AgentCapabilities, AgentTask, AgentResult

class CustomDocumentationAgent(BaseAgent):
    def __init__(self):
        capabilities = AgentCapabilities(
            name="custom_documenter",
            description="Mi agente personalizado",
            input_types=["custom_input"],
            output_types=["custom_documentation"],
            supported_languages=["python", "javascript"],
            max_parallel_tasks=3
        )
        super().__init__(capabilities)
    
    async def process_task(self, task: AgentTask) -> AgentResult:
        # Lógica personalizada aquí
        return AgentResult(
            task_id=task.id,
            success=True,
            data={"custom_result": "data"}
        )

# Registrar el agente
from confluence_generator.sdk import AgentFactory

factory = AgentFactory()
factory.register_agent_type("custom", CustomDocumentationAgent)
```

### Usar el SDK

```python
from confluence_generator.sdk import AgentSDK, AgentTask

sdk = AgentSDK()
agent = factory.create_agent("custom")
sdk.register_agent(agent)

# Ejecutar tarea
task = AgentTask(
    id="task_1",
    type="custom_analysis",
    input_data={"repo_url": "https://github.com/user/repo"}
)

result = await sdk.execute_task("custom_documenter", task)
```

## 🔧 Configuración Avanzada

### Variables de Entorno

| Variable | Descripción | Requerido |
|----------|-------------|-----------|
| `GOOGLE_API_KEY` | Clave API de Google Gemini | Sí |
| `OPENAI_API_KEY` | Clave API de OpenAI | Sí |
| `CONFLUENCE_BASE_URL` | URL base de Confluence | Sí |
| `CONFLUENCE_USERNAME` | Usuario de Confluence | Sí |
| `CONFLUENCE_API_TOKEN` | Token API de Confluence | Sí |
| `POSTGRES_HOST` | Host de PostgreSQL | No |
| `POSTGRES_DB` | Base de datos | No |
| `REDIS_HOST` | Host de Redis | No |

### Configuración de Base de Datos

La aplicación usa PostgreSQL como base de datos principal por su robustez y capacidades de consulta avanzadas, ideal para:

- Almacenamiento de metadatos de componentes
- Índices de búsqueda de texto completo
- Relaciones complejas entre proyectos y componentes
- Transacciones ACID para integridad de datos

### Configuración de Agentes

Los agentes se pueden configurar individualmente:

```python
# Configurar límites de tareas paralelas
architecture_agent.capabilities.max_parallel_tasks = 5

# Configurar timeout personalizado
component_agent.capabilities.timeout_seconds = 600
```

## 📊 Monitoreo

### Métricas Disponibles

- **Prometheus**: Métricas de aplicación en `http://localhost:9090`
- **Grafana**: Dashboards en `http://localhost:3001`
- **Health Checks**: Endpoints `/health` en cada servicio

### Métricas Principales

- Número de trabajos de documentación procesados
- Tiempo de ejecución de agentes
- Errores de generación
- Uso de base de datos
- Estadísticas de MCP

## 🧪 Testing

### Base de Datos
```bash
# Test de conectividad de base de datos
./scripts/test-database.sh

# Setup de base de datos de desarrollo
./scripts/setup-database.sh dev

# Verificar estructura de base de datos
docker-compose -f docker-compose.dev.yml exec postgres-dev psql -U postgres -d confluence_docs -c "\dt"
```

### Aplicación
```bash
# Ejecutar tests (cuando estén creados)
pytest confluence_generator/tests/

# Test de integración
pytest confluence_generator/tests/integration/

# Test de carga
pytest confluence_generator/tests/load/
```

### Acceso a Base de Datos
```bash
# PgAdmin (interfaz web)
open http://localhost:8080
# Usuario: admin@example.com
# Contraseña: admin

# psql directo
docker-compose -f docker-compose.dev.yml exec postgres-dev psql -U postgres -d confluence_docs

# Consultas útiles
# Ver proyectos: SELECT * FROM v_project_summary;
# Ver rendimiento de agentes: SELECT * FROM v_agent_performance;
# Ver actividad diaria: SELECT * FROM v_daily_activity WHERE activity_date >= CURRENT_DATE - INTERVAL '7 days';
```

## 📈 Escalabilidad

### Escalar Horizontalmente

```bash
# Escalar workers
docker-compose -f docker-compose.confluence.yml up --scale agent_worker=5

# Escalar base de datos (usar PostgreSQL cluster)
# Usar Redis Cluster para caché distribuido
```

### Optimizaciones

- **Caché de Redis**: Resultados de análisis frecuentes
- **Pool de Conexiones**: Base de datos optimizada
- **Procesamiento Asíncrono**: Todas las operaciones IO son async
- **Compresión**: Documentos grandes comprimidos

## 🔒 Seguridad

- **Autenticación**: Tokens API seguros
- **Autorización**: Control de acceso basado en roles
- **Encriptación**: Comunicaciones HTTPS
- **Validación**: Input validation y sanitización
- **Logging**: Auditoría completa de operaciones

## 🐛 Troubleshooting

### Problemas Comunes

1. **Error de conexión a PostgreSQL**:
```bash
# Verificar que PostgreSQL esté corriendo
docker-compose logs postgres
```

2. **Agentes no responden**:
```bash
# Verificar workers
docker-compose logs agent_worker
```

3. **Error de Confluence API**:
```bash
# Verificar credenciales
curl -u user:token https://your-company.atlassian.net/rest/api/user/current
```

## 🤝 Contribuir

1. Fork el proyecto
2. Crear feature branch (`git checkout -b feature/nueva-caracteristica`)
3. Commit cambios (`git commit -am 'Agregar nueva característica'`)
4. Push al branch (`git push origin feature/nueva-caracteristica`)
5. Crear Pull Request

## 📄 Licencia

Este proyecto está licenciado bajo la Licencia MIT - ver el archivo [LICENSE](../LICENSE) para detalles.