# Contributing to DevMind

Thank you for your interest in contributing to DevMind! We welcome contributions from the community.

## Ways to Contribute

### 🐛 Reporting Bugs

- Check [existing issues](https://github.com/NamelessMonsterr/Dev-Mind/issues) first
- Use the bug report template
- Include reproduction steps, expected behavior, and actual behavior
- Add relevant logs, screenshots, or error messages

### 💡 Suggesting Features

- Check [discussions](https://github.com/NamelessMonsterr/Dev-Mind/discussions) for existing requests
- Open a discussion to propose your idea
- Explain the use case and expected benefit

### 🔧 Contributing Code

1. **Fork the repository**

   ```bash
   git clone https://github.com/NamelessMonsterr/Dev-Mind.git
   cd Dev-Mind
   ```

2. **Create a feature branch**

   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Make your changes**
   - Follow code style guidelines
   - Add tests for new functionality
   - Update documentation as needed

4. **Run tests and linting**

   ```bash
   # Backend
   cd devmind-project
   pytest tests/ -v --cov=devmind
   black devmind/ tests/
   ruff check devmind/ tests/
   mypy devmind/

   # Frontend
   cd devmind-ui
   npm run lint
   npm run type-check
   ```

5. **Commit your changes**

   ```bash
   git add .
   git commit -m "feat: add amazing feature"
   ```

   **Commit Message Format:**
   - `feat:` New feature
   - `fix:` Bug fix
   - `docs:` Documentation changes
   - `test:` Adding or updating tests
   - `refactor:` Code refactoring
   - `chore:` Maintenance tasks

6. **Push and create a Pull Request**
   ```bash
   git push origin feature/your-feature-name
   ```

## Development Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker & Docker Compose

### Backend Development

```bash
cd devmind-project

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest tests/ -v

# Start dev server
python main.py
```

### Frontend Development

```bash
cd devmind-ui

# Install dependencies
npm install

# Run dev server
npm run dev

# Build
npm run build
```

## Code Style Guidelines

### Python

- Follow PEP 8
- Use type hints
- Write docstrings for functions and classes
- Maximum line length: 100 characters
- Use `black` for formatting
- Use `ruff` for linting
- Use `mypy` for type checking

### TypeScript/JavaScript

- Follow Airbnb style guide
- Use TypeScript for type safety
- Use ESLint and Prettier
- Write JSDoc comments for complex functions

## Testing Guidelines

- Write unit tests for new functions
- Write integration tests for API endpoints
- Aim for >80% code coverage
- Test edge cases and error conditions

## Documentation

- Update README.md if adding new features
- Update API documentation
- Add inline comments for complex logic
- Update DEPLOYMENT.md for infrastructure changes

## Pull Request Process

1. Ensure all tests pass
2. Update documentation
3. Add a clear PR description explaining:
   - What changed
   - Why it changed
   - How to test it
4. Link related issues
5. Wait for review and address feedback

## Code of Conduct

- Be respectful and inclusive
- Welcome newcomers
- Provide constructive feedback
- Focus on the code, not the person

## Questions?

- Open a [Discussion](https://github.com/NamelessMonsterr/Dev-Mind/discussions)
- Check existing [Issues](https://github.com/NamelessMonsterr/Dev-Mind/issues)

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to DevMind! 🚀
