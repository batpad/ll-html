# Contributing to LL-HTML

## Local Development Setup

### Prerequisites
- Python 3.8+
- Git
- OpenAI API key

### Initial Setup

1. **Clone and setup environment**
   ```bash
   git clone <repository-url>
   cd ll-html
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Environment configuration**
   ```bash
   cp .env.example .env
   # Edit .env and add your OpenAI API key:
   # OPENAI_API_KEY=your_openai_api_key_here
   ```

3. **Database setup**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   python manage.py create_base_templates
   ```

4. **Create Django superuser (Admin Access)**
   ```bash
   python manage.py createsuperuser
   # Follow prompts to create admin username/password
   ```

5. **Run development server**
   ```bash
   python manage.py runserver
   ```

### Access Points
- **Demo Interface**: http://localhost:8000/generator/demo/
- **Django Admin**: http://localhost:8000/admin/ (use superuser credentials)
- **API Documentation**: Available through Django admin or direct endpoint testing

## Development Workflow

### Testing Changes
Always test your changes with the demo interface:
```bash
# Start server
python manage.py runserver

# Visit demo page and test generation
# Monitor console output for debugging information
```

### Adding STAC Data Sources
```bash
# Add new STAC catalog
python manage.py crawl_stac_catalog https://your-stac-endpoint.com/stac/

# View configured sources
python manage.py show_data_sources --active-only --show-collections
```

### Debugging Generation Issues
```bash
# Analyze recent generations for patterns
python manage.py analyze_pages --count=10 --show-agent-details

# Test specific generation with debug output
python manage.py debug_generation --test-generation

# Test agent tools
python manage.py debug_tools --test-tools

# Test validation system
python manage.py test_validation --test-type=both
```

## Architecture Overview

### Django Apps
- **agents/**: REACT agent system with research tools
- **datasets/**: STAC catalog and data source management  
- **generator/**: HTML templates and page generation
- **storage/**: Future version control system

### Key Files to Understand
- `agents/react_agent.py`: Main orchestrator with REACT loop
- `agents/tools.py`: Research tools (web search, API validation, STAC)
- `agents/validation_agent.py`: HTML/JS validation and fixing
- `generator/views.py`: API endpoints and generation flow
- `datasets/models.py`: Data source and STAC catalog models

### Generation Pipeline
```
User Request → Research Agent → HTML Generation → Validation Agent → Final Output
```

## Common Development Issues

### Environment and Dependencies
- **Missing OpenAI API Key**: Generation will fail silently. Ensure `OPENAI_API_KEY` is set in `.env`
- **Database Migration Issues**: Delete `db.sqlite3` and run migrations again if schema conflicts occur
- **Template Loading Errors**: Run `python manage.py create_base_templates --overwrite` to refresh templates

### Agent Configuration
- **Rate Limiting**: OpenAI API rate limits may cause generation failures. Check console output for rate limit messages
- **Tool Timeouts**: Long-running research may timeout. Adjust `AGENT_TOOL_TIMEOUT` in `.env` if needed
- **Insufficient Research**: Agent may proceed with minimal research. Check `AGENT_MAX_ITERATIONS` setting

### Data Source Issues  
- **STAC Catalog Connectivity**: Network issues or invalid STAC URLs will cause research failures
- **API Endpoint Changes**: External APIs may change or become unavailable, affecting generated applications
- **Data Format Mismatches**: STAC collections may have unexpected schemas that break data integration

### HTML Generation and Validation
- **Template Rendering Errors**: Check Django template syntax in generated content using Django admin
- **JavaScript Library Conflicts**: Multiple library versions may conflict. Templates include specific versions
- **Validation Agent Failures**: LLM-based fixes may not resolve all HTML/JS issues on first attempt

## Making Changes

### Adding New Research Tools
1. Add tool class in `agents/tools.py`
2. Register tool in `ReactAgent.available_tools` 
3. Update tool descriptions for LLM context
4. Test with `python manage.py debug_tools --test-tools`

### Modifying Templates
1. Edit templates in `generator/templates/` or use Django admin
2. Run `python manage.py create_base_templates --overwrite` if needed
3. Test generation with updated templates
4. View templates with `python manage.py show_templates --active-only`

### Validation Rules
1. Add validation logic in `agents/validation_tools.py`
2. Update validation agent prompts in `agents/validation_agent.py`
3. Test with `python manage.py test_validation`

## Useful Django Admin Features

Access Django admin at http://localhost:8000/admin/ with your superuser account:

- **Generated Pages**: View all generated HTML content, debug failures
- **HTML Templates**: Edit and preview template code and libraries
- **Data Sources**: Manage STAC catalogs and API endpoints
- **Generation Requests**: Track LLM usage and performance metrics

## Environment Variables

Optional configuration in `.env`:

```bash
# Agent Configuration
AGENT_MAX_ITERATIONS=10          # REACT loop depth
AGENT_MAX_LLM_CALLS=15          # Total LLM calls per generation  
AGENT_TOOL_TIMEOUT=60           # Tool execution timeout
AGENT_MAX_TOKENS_FINAL_GENERATION=6000  # HTML generation complexity

# Feature Toggles
AGENT_ENABLE_WEB_SEARCH=True
AGENT_ENABLE_API_VALIDATION=True
```

## Submitting Changes

1. Test your changes thoroughly with the demo interface
2. Run validation tests: `python manage.py test_validation`  
3. Check that agent tools work: `python manage.py debug_tools --test-tools`
4. Verify templates load correctly: `python manage.py show_templates --active-only`
5. Test with various generation requests to ensure stability

## Getting Help

- Check Django admin for detailed error logs and generation history
- Use management commands for debugging specific issues
- Monitor console output during development for agent execution details
- Test individual components with provided debug commands