# Contributing to Wheelwright Framework

Thank you for your interest in contributing to Wheelwright! This document provides guidelines and information for contributors.

## Code of Conduct

Be respectful, inclusive, and constructive. We're building tools that help everyone work better with AI.

## How to Contribute

### Reporting Issues

1. Check existing issues to avoid duplicates
2. Use the issue templates when available
3. Include:
   - Clear description of the problem
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment details (OS, Python version, etc.)

### Suggesting Features

1. Open a discussion or issue with the `enhancement` label
2. Describe the use case and benefit
3. Consider how it fits with Wheelwright's philosophy

### Submitting Code

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Make your changes
4. Write/update tests as needed
5. Ensure all tests pass: `python -m pytest tests/`
6. Submit a pull request

## Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/framework.git
cd framework

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Run tests
python -m pytest tests/
```

## Project Structure

```
framework/
├── WAI                       # Main CLI entry point (shell script)
├── wai_cli/                  # Modular CLI implementation
│   ├── core.py               # Orchestration and routing
│   ├── commands/             # Command handlers (18 modules)
│   ├── ui/                   # Interactive menu system
│   ├── utils/                # Shared utilities
│   └── integrations/         # IDE/tool integrations
├── templates/                # Template files
│   ├── wheel/                # Wheel templates
│   └── hub/                  # Hub templates
├── docs/                     # Documentation
│   ├── architecture/         # Architecture documentation
│   ├── QUICKSTART.md
│   └── SPOKES.md
├── tests/                    # Test suite
│   ├── unit/                 # Unit tests
│   ├── integration/          # Integration tests
│   └── scripts/              # Smoke test scripts
├── WAI-Spoke/                # This project's own Wheelwright context
├── CHANGELOG.md              # Version history
└── README.md                 # Project overview
```

**Architecture Documentation:**
- [CLI Module Structure](docs/architecture/CLI_MODULE_STRUCTURE.md) - Detailed CLI architecture
- [Framework Overview](docs/architecture/FRAMEWORK_OVERVIEW.md) - High-level architecture

## Coding Standards

### Python

- Follow PEP 8 style guide
- Use type hints where practical
- Write docstrings for public functions
- Keep functions focused and small

### Documentation

- Update docs when changing functionality
- Use clear, concise language
- Include code examples where helpful

### Commits

- Use clear, descriptive commit messages
- Reference issues when applicable: `Fix #123`
- Keep commits focused on single changes

## Testing

- Write tests for new functionality
- Maintain existing test coverage
- Use descriptive test names

```bash
# Run all tests
python -m pytest tests/

# Run specific test file
python -m pytest tests/test_cli.py

# Run with coverage
python -m pytest --cov=. tests/
```

## Pull Request Process

1. Update README.md if needed
2. Update documentation for new features
3. Add tests for new functionality
4. Ensure CI passes
5. Request review from maintainers

## Philosophy Alignment

When contributing, keep Wheelwright's core philosophy in mind:

- **Universal**: Works with any AI, any project type
- **Simple**: Easy to understand and use
- **Extensible**: Spokes add capability without complexity
- **Responsible**: AI as partner, not just enabler

## Questions?

- Open a discussion on GitHub
- Check existing documentation
- Review closed issues for similar questions

---

*"We aren't reinventing the wheel - we're evolving it faster than one person ever could."*
