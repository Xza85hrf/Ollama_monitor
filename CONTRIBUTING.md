# Contributing to Ollama Monitor

Thank you for your interest in contributing to Ollama Monitor! This document provides guidelines and instructions for contributing.

## Code of Conduct

Be respectful and constructive in all interactions. We're all here to build better software together.

## Getting Started

### 1. Fork and Clone

```bash
git fork https://github.com/Xza85hrf/Ollama_monitor
git clone https://github.com/YOUR_USERNAME/Ollama_monitor.git
cd Ollama_monitor
```

### 2. Set Up Development Environment

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install
```

### 3. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/issue-number-description
```

## Development Workflow

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=ollama_monitor --cov-report=html

# Run specific test file
pytest tests/test_ollama_monitor.py

# Run with verbose output
pytest -v
```

### Code Quality

We use several tools to maintain code quality:

```bash
# Format code
black ollama_monitor.py tests/

# Sort imports
isort ollama_monitor.py tests/

# Lint code
pylint ollama_monitor.py

# Type check
mypy ollama_monitor.py
```

Pre-commit hooks will run these automatically, but you can also run them manually:

```bash
pre-commit run --all-files
```

### Running the Application

```bash
# Basic health check
python ollama_monitor.py --url http://localhost:11434

# With configuration file
python ollama_monitor.py --config config.yaml

# Load testing
python ollama_monitor.py --load-test --num-requests 100 --concurrency 10

# Continuous monitoring
python ollama_monitor.py --continuous --interval 60 --prometheus
```

### Docker Testing

```bash
# Build image
docker build -t ollama-monitor:dev .

# Run container
docker run -p 8000:8000 ollama-monitor:dev

# Run with docker-compose
docker-compose up
```

## Contribution Guidelines

### Code Style

- Follow PEP 8 style guidelines
- Use type hints for all function signatures
- Maximum line length: 100 characters (Black default)
- Use descriptive variable and function names
- Add docstrings for all public functions and classes

Example:

```python
async def check_endpoint(
    self,
    client: httpx.AsyncClient,
    endpoint: str,
    config: EndpointConfig
) -> Tuple[float, int]:
    """
    Check endpoint availability and performance.

    Args:
        client: Async HTTP client
        endpoint: Endpoint path to check
        config: Endpoint configuration

    Returns:
        Tuple of (response_time, status_code)

    Raises:
        httpx.HTTPError: If request fails
    """
    # Implementation
```

### Testing Requirements

- Write tests for all new features
- Maintain or improve code coverage (target: >80%)
- Test both success and error cases
- Use meaningful test names

Example:

```python
@pytest.mark.asyncio
async def test_check_endpoint_success(monitor, endpoint_config):
    """Test successful endpoint check returns correct values."""
    # Test implementation
```

### Commit Messages

Follow conventional commits format:

```
<type>(<scope>): <subject>

<body>

<footer>
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `test`: Adding or updating tests
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `chore`: Build process or auxiliary tool changes
- `ci`: CI/CD changes

Examples:

```bash
feat(monitoring): add support for custom headers in requests

fix(docker): resolve permission issue with non-root user

docs(readme): update installation instructions

test(endpoints): add integration tests for API endpoints
```

### Pull Request Process

1. **Update Documentation**: Ensure README and other docs reflect your changes
2. **Add Tests**: Include tests for new functionality
3. **Update CHANGELOG**: Add entry in CHANGELOG.md
4. **Run Tests Locally**: Ensure all tests pass
5. **Create PR**: Submit pull request with clear description

PR Template:

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
Describe how you tested your changes

## Checklist
- [ ] Tests pass locally
- [ ] Code follows style guidelines
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
```

## Feature Requests and Bug Reports

### Reporting Bugs

Include:
- Clear, descriptive title
- Steps to reproduce
- Expected vs actual behavior
- Environment details (OS, Python version, etc.)
- Relevant logs or error messages

### Requesting Features

Include:
- Clear use case
- Proposed solution or approach
- Alternative solutions considered
- Willingness to implement

## Project Structure

```
Ollama_monitor/
├── ollama_monitor.py       # Main application
├── config_validator.py     # Pydantic configuration models
├── logger_config.py        # Structured logging setup
├── report_generator.py     # Multi-format report generation
├── alerting.py            # Webhook alerting
├── tests/                 # Test suite
│   ├── conftest.py       # Test fixtures
│   └── test_*.py         # Test modules
├── k8s/                   # Kubernetes manifests
├── Dockerfile            # Container image
├── docker-compose.yml    # Local development stack
└── requirements*.txt     # Python dependencies
```

## Getting Help

- Check existing issues and discussions
- Review documentation and examples
- Ask questions in issue comments
- Join project discussions

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

## Recognition

Contributors will be recognized in:
- README.md contributors section
- Release notes
- Git commit history

Thank you for contributing! 🎉
