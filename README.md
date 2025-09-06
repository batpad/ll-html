# WARNING: AI Slop Ahead

This is totally experimental and me messing with Claude Code on a weekend - please do not take any of this seriously.

# LL-HTML: Large Language HTML Generation System

**Generate web applications and dashboards from natural language requests using STAC catalogs and web APIs**

---

## What is LL-HTML?

LL-HTML is a system that generates functional web applications from natural language descriptions. It uses a REACT (Reason-Act-Observe) agent architecture to research data sources, validate APIs, and produce complete HTML applications with working maps and charts.

**Input:** Natural language request  
**Output:** Complete web application with real data integration

Example:
```
Request: "Create a map showing recent earthquakes with magnitude data"
Result: Interactive web app with Leaflet map, Chart.js visualizations, real earthquake data from STAC sources
```

## How It Works

### Three-Stage Pipeline

1. **Research Agent**: Searches web APIs, validates endpoints, samples data from STAC catalogs
2. **HTML Generation**: Creates application using pre-loaded templates (Leaflet, Chart.js, Bootstrap)  
3. **Validation Agent**: Checks HTML/JavaScript syntax, fixes errors, validates URLs

### Key Components

- **STAC Integration**: Connects to SpatioTemporal Asset Catalogs for geospatial data
- **API Validation**: Tests endpoints before integration to ensure accessibility
- **Template System**: Pre-loaded with common libraries to avoid dependency issues
- **Quality Assurance**: Automatic validation and fixing of generated code

## Quick Start

### Setup
```bash
git clone <repository>
cd ll-html
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Add OpenAI API key to .env

# Initialize
python manage.py migrate
python manage.py create_base_templates
python manage.py runserver
```

### Usage
1. Go to http://localhost:8000/generator/demo/
2. Enter request: "Create earthquake monitoring dashboard"
3. Wait for generation (30-60 seconds)
4. View generated application

## Data Sources

### STAC Catalogs
Configure STAC (SpatioTemporal Asset Catalog) endpoints:
```bash
python manage.py crawl_stac_catalog https://your-stac-endpoint.com/stac/
python manage.py show_data_sources --active-only --show-collections
```

### Web APIs
The system researches and validates web APIs during generation:
- Searches for current data sources relevant to requests
- Tests endpoint accessibility and response format
- Integrates validated APIs into generated applications

## Generated Applications Include

- **Interactive Maps**: Leaflet.js with real geographic data
- **Charts & Graphs**: Chart.js with data from STAC collections
- **Responsive Design**: Bootstrap-based layouts
- **Error Handling**: Try/catch blocks and fallback messaging
- **Data Loading**: Proper async data fetching with loading states

## Configuration

### Agent Settings (Optional)
```bash
# In .env file
AGENT_MAX_ITERATIONS=10          # Research depth
AGENT_MAX_LLM_CALLS=15          # LLM calls per generation
AGENT_MAX_TOKENS_FINAL_GENERATION=6000  # Output complexity
```

### Data Source Priority
The system prioritizes configured STAC catalogs over external APIs found through web search.

## Management Commands

### Data Management
```bash
# View configured STAC catalogs and collections
python manage.py show_data_sources --active-only --show-collections

# Add new STAC catalog
python manage.py crawl_stac_catalog <catalog-url>
```

### Debugging
```bash
# Analyze generated applications
python manage.py analyze_pages --count=5 --show-urls

# Test system components
python manage.py debug_tools --test-tools
python manage.py test_validation
```

### Templates
```bash
# View available HTML templates
python manage.py show_templates --active-only

# Recreate templates with latest libraries
python manage.py create_base_templates --overwrite
```

## Requirements

- Python 3.8+
- Django 5.2+
- OpenAI API key (for GPT-4o-mini)
- Internet connection for data fetching

## Architecture

```
ll-html/
├── agents/              # REACT agent system
│   ├── react_agent.py   # Main orchestrator
│   ├── tools.py         # Web search, STAC fetching, API validation
│   └── validation_*     # HTML/JS validation and fixing
├── datasets/            # STAC catalog management
├── generator/           # HTML templates and generation
└── storage/             # Generated page storage
```

## Technical Details

See [AGENTS.md](AGENTS.md) for detailed architecture documentation and development commands.
