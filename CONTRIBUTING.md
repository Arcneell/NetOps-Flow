# Contributing to NetOps Flow

Thank you for your interest in contributing to NetOps Flow! This document provides guidelines and instructions for contributing.

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment for everyone.

## How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported in [Issues](https://github.com/Arcneell/NetOps-Flow/issues)
2. If not, create a new issue with:
   - A clear, descriptive title
   - Steps to reproduce the bug
   - Expected vs actual behavior
   - Screenshots if applicable
   - Your environment (OS, browser, Docker version)

### Suggesting Features

1. Check existing issues for similar suggestions
2. Create a new issue with the label `enhancement`
3. Describe the feature and its use case
4. Explain why it would be useful

### Pull Requests

1. Fork the repository
2. Create a feature branch from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. Make your changes following our coding standards
4. Test your changes locally
5. Commit with clear, descriptive messages
6. Push to your fork and submit a Pull Request

## Development Setup

### Prerequisites

- Docker and Docker Compose
- Node.js 18+ (for frontend development)
- Python 3.11+ (for backend development)

### Local Development

1. Clone your fork:
   ```bash
   git clone https://github.com/YOUR_USERNAME/NetOps-Flow.git
   cd NetOps-Flow
   ```

2. Start the development environment:
   ```bash
   docker-compose up --build
   ```

3. For frontend development:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

4. For backend development:
   ```bash
   cd backend
   pip install -r requirements.txt
   uvicorn backend.main:app --reload
   ```

## Coding Standards

### Python (Backend)

- Follow PEP 8 style guidelines
- Use type hints where possible
- Write docstrings for functions and classes
- Keep functions small and focused

### JavaScript/Vue (Frontend)

- Use Vue 3 Composition API with `<script setup>`
- Follow the existing code style
- Use meaningful variable and function names
- Keep components focused and reusable

### Commits

- Use clear, descriptive commit messages
- Start with a verb (Add, Fix, Update, Remove, etc.)
- Reference issues when applicable: `Fix #123`

## Testing

Before submitting a PR, ensure:

1. The application builds without errors
2. Existing functionality still works
3. New features work as expected
4. No console errors in the browser

## Questions?

Feel free to open an issue with the `question` label if you need help.

Thank you for contributing!
