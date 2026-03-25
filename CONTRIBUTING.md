# Contributing Guidelines

Thank you for your interest in contributing to the Enterprise Multimodal RAG Pipeline!

## Code of Conduct

Be respectful, inclusive, and professional in all interactions.

## Development Setup

1. Fork the repository
2. Clone your fork: `git clone <your-fork-url>`
3. Create a virtual environment: `python -m venv venv`
4. Install dependencies: `pip install -r requirements.txt`
5. Install dev dependencies: `pip install pytest pytest-cov black isort mypy`

## Development Workflow

### 1. Create a Branch

```bash
git checkout -b feature/your-feature-name
```

### 2. Make Changes

Follow the existing code style and patterns.

### 3. Run Tests

```bash
pytest tests/ -v --cov=src
```

### 4. Format Code

```bash
black src/ tests/
isort src/ tests/
```

### 5. Type Check

```bash
mypy src/
```

### 6. Commit Changes

```bash
git add .
git commit -m "feat: add new feature"
```

Use conventional commits:
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation
- `refactor:` Code refactoring
- `test:` Tests
- `chore:` Maintenance

### 7. Push and Create PR

```bash
git push origin feature/your-feature-name
```

Create a Pull Request with:
- Clear description
- Test results
- Screenshots (if applicable)

## Code Style

- Follow PEP 8
- Use type hints
- Write docstrings
- Keep functions focused
- Maximum line length: 100 characters

## Testing

- Write unit tests for new features
- Maintain >80% code coverage
- Test edge cases
- Use mocks for external services

## Documentation

- Update README.md if needed
- Add docstrings to functions
- Update ARCHITECTURE.md for design changes
- Include examples in docstrings

## Pull Request Process

1. Ensure all tests pass
2. Update documentation
3. Add entry to CHANGELOG.md
4. Request review from maintainers
5. Address review comments
6. Squash commits if requested

## Questions?

Open an issue or contact the maintainers.

Thank you for contributing! 🙏
