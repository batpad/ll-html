# LL-HTML: Large Language HTML Generation System

## Project Overview: Intelligent Disaster Response Web Applications

LL-HTML is a sophisticated LLM-mediated system that generates professional disaster response web applications from natural language requests. Using a multi-stage REACT (Reason-Act-Observe) agent architecture, it researches current data, validates sources, and produces high-quality HTML applications with working maps, charts, and real-time data integration.

## Core Concept

**"Ask for a disaster response app in natural language → Get a fully functional web application with real data"**

1. **Research-First Approach**: Agent must gather intelligence before generating HTML
2. **Quality Assurance**: Multi-layered validation and automatic error fixing
3. **Real Data Integration**: Connects to validated data sources (STAC catalogs, APIs)
4. **Production-Ready Output**: Professional applications with proper dependencies and error handling

## Current Architecture (Production Ready)

### 🤖 Three-Stage Generation Pipeline

```
User Request → Research Agent → HTML Generation → Validation Agent → Final Output
              (gathers data)    (creates app)      (validates & fixes)
```

**Stage 1: Research Agent (REACT Loop)**
- Uses web search, API validation, and STAC data fetching
- Enforces minimum 2 successful tool calls before proceeding
- Prioritizes configured data sources over external alternatives

**Stage 2: HTML Generation Agent**
- Uses pre-loaded template system with all major libraries
- Applies gathered intelligence to create accurate applications
- Includes robust error handling and proper API integration

**Stage 3: Validation Agent**
- HTML structure validation (missing elements, syntax)
- JavaScript validation (library usage, undefined variables)
- Dependency checking (duplicate imports, missing IDs)
- Automatic fixing using LLM-based corrections

### 🏗️ Django Architecture

```
ll-html/
├── agents/              # REACT Agent System
│   ├── react_agent.py   # Main orchestrator
│   ├── tools.py         # Research tools (web search, STAC, API validation)
│   ├── validation_agent.py  # Quality assurance agent
│   └── validation_tools.py  # HTML/JS validators
├── datasets/            # Data Source Management
│   ├── models.py        # DataSource model with STAC support
│   └── services.py      # STAC catalog discovery
├── generator/           # HTML Generation & Templates
│   ├── models.py        # HTMLTemplate, GeneratedPage
│   └── views.py         # API endpoints
└── storage/             # Version Control (Future)
```

### 📊 Key Components

**REACT Agent (agents/react_agent.py)**
- Implements full Reason-Act-Observe loop
- Tool orchestration with configurable limits
- Context management and intelligence gathering
- Data source prioritization enforcement

**Research Tools (agents/tools.py)**
- `WebSearchTool`: DuckDuckGo search for current information
- `ValidateAPITool`: Test endpoint accessibility and response format
- `FetchSTACDataTool`: Sample data from STAC catalogs
- `ValidateHTMLEndpointsTool`: Extract and validate URLs from generated HTML

**Template System (generator/models.py)**
- Pre-loaded libraries: Leaflet, Chart.js, Bootstrap, Font Awesome
- Three template types: Map, Dashboard, Comprehensive
- Utility functions included: `createMap()`, `createChart()`, `showLoading()`

**Data Source Management (datasets/models.py)**
- STAC catalog integration with collection metadata
- Query pattern definitions and LLM context
- API endpoint validation and caching

## Implementation Status

### ✅ Phase 1: Data Source Enforcement (COMPLETE)
- **Configured Source Priority**: Configured data sources prioritized over external alternatives
- **STAC Integration**: Full STAC catalog support with collection metadata
- **Research Requirements**: HTML generation blocked until sufficient research conducted
- **Enhanced Context**: Visual priority messaging and detailed collection information

### ✅ Phase 2: Enhanced Templates with Dependencies (COMPLETE)  
- **Universal Libraries**: All templates include Leaflet, Chart.js, Bootstrap, Font Awesome
- **No Missing Dependencies**: Eliminates "L is undefined" and similar errors
- **Code Examples**: Built-in utility functions and usage patterns
- **Smart Defaults**: Pre-configured elements and styling for common use cases

### ✅ Phase 3: HTML/JS Validation Agent (COMPLETE)
- **Automated QA**: Structure, syntax, and dependency validation
- **Auto-Fixing**: LLM-based correction of identified issues
- **JSON Escaping**: Robust handling of backslashes in generated JavaScript
- **Quality Metrics**: Severity scoring and improvement tracking

### 🎯 Current Capabilities
- **Real-time disaster data** from configured STAC catalogs
- **Working maps** with Leaflet integration and geographic data
- **Interactive charts** using Chart.js with proper data binding
- **Responsive design** with Bootstrap components and mobile optimization
- **Error handling** with try/catch blocks and fallback messaging
- **URL validation** preventing hallucinated API endpoints

## Development Setup & Commands

### Environment Setup
```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Environment configuration
cp .env.example .env
# Edit .env with your OpenAI API key and settings
```

### Django Commands
```bash
# Run migrations
python manage.py makemigrations
python manage.py migrate

# Create superuser for admin access
python manage.py createsuperuser

# Run development server
python manage.py runserver

# Create enhanced HTML templates with pre-loaded libraries
python manage.py create_base_templates

# Access admin interface at http://localhost:8000/admin/
# Access demo interface at http://localhost:8000/generator/demo/
```

### Management Commands for Development & Debugging

**Data Source Management**
```bash
# View configured data sources and their collections
python manage.py show_data_sources --active-only --show-collections

# Crawl and import STAC catalogs
python manage.py crawl_stac_catalog <catalog-url>
```

**Template Management**
```bash
# View available HTML templates and their libraries
python manage.py show_templates --active-only --show-libraries

# Recreate templates with latest improvements
python manage.py create_base_templates --overwrite
```

**Generation Analysis & Debugging**
```bash
# Analyze recent page generations for issues
python manage.py analyze_pages --count=5 --show-urls --show-agent-details

# Debug specific generated page
python manage.py analyze_pages --page-id=<ID> --show-urls

# Debug generation process with detailed output
python manage.py debug_generation --test-generation --analyze-recent
```

**Agent & Tool Testing**
```bash
# Test all agent tools with sample data
python manage.py debug_tools --test-tools

# Debug specific agent session
python manage.py debug_tools --session-id=<session_id>

# Test validation system with problematic content
python manage.py test_validation --test-type=both
```

## Production Deployment Notes

### Required Environment Variables
```bash
# LLM Integration
OPENAI_API_KEY=your_openai_api_key_here

# Agent Configuration (Optional - defaults provided)
AGENT_MAX_ITERATIONS=10          # REACT loop iterations
AGENT_MAX_LLM_CALLS=15          # Total LLM calls per generation
AGENT_TOOL_TIMEOUT=60           # Tool execution timeout (seconds)
AGENT_MAX_TOKENS_FINAL_GENERATION=6000  # HTML generation tokens
AGENT_MAX_TOKENS_REASONING=2000  # Reasoning step tokens

# Feature Toggles
AGENT_ENABLE_WEB_SEARCH=True
AGENT_ENABLE_API_VALIDATION=True
```

### Performance Considerations
- **Generation Time**: 30-60 seconds per application (includes research)
- **Token Usage**: ~8,000-15,000 tokens per generation (varies by complexity)
- **Rate Limits**: Respects OpenAI rate limits with built-in retry logic
- **Caching**: Tool results cached per session to avoid duplicate API calls