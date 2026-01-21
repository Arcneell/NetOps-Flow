# Contributing to Inframate

Thank you for your interest in contributing to Inframate! This document provides guidelines for contributing.

## License

This project is licensed under the **Elastic License 2.0 (ELv2)**. By contributing, you agree that your contributions will be licensed under the same terms.

## How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported in [Issues](https://github.com/Arcneell/Inframate/issues)
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

### Pull Requests

1. Fork the repository
2. Create a feature branch from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. Make your changes following our coding standards
4. Test your changes locally with `docker-compose up --build`
5. Commit with clear messages (see below)
6. Push to your fork and submit a Pull Request

## Development Setup

### Prerequisites

- Docker and Docker Compose
- Node.js 18+ (for frontend development)
- Python 3.11+ (for backend development)

### Quick Start

```bash
# Clone and configure
git clone https://github.com/YOUR_USERNAME/Inframate.git
cd Inframate
cp .env.example .env

# Generate required secrets
openssl rand -base64 32  # For JWT_SECRET_KEY
openssl rand -base64 32 | tr '+/' '-_'  # For ENCRYPTION_KEY (Fernet, url-safe base64)

# Start
docker-compose up --build
```

### Database Migrations

```bash
# Apply migrations
docker-compose exec backend alembic upgrade head

# Create new migration
docker-compose exec backend alembic revision --autogenerate -m "description"
```

## Coding Standards

### Python (Backend)

- Follow PEP 8 style guidelines
- Use type hints
- Use SQLAlchemy 2.0 style queries
- Use Pydantic for request/response schemas
- Use FastAPI dependencies for authentication

### Vue.js (Frontend)

- Use Vue 3 Composition API with `<script setup>`
- Use Pinia for state management
- Use `useI18n()` for translations with namespaced keys (e.g., `t('tickets.title')`)
- Use PrimeVue components
- Follow the Modern Slate design system (see `style.css`)

### Commits

- Use clear, descriptive commit messages
- Start with a verb: `Add`, `Fix`, `Update`, `Remove`, `Refactor`
- Reference issues when applicable: `Fix #123`

Examples:
```
Add user avatar upload feature
Fix ticket SLA calculation with business hours
Update password validation to require special characters
```

## Project Structure

```
backend/
├── core/           # Config, security, middleware, cache
├── routers/        # API endpoints
├── models.py       # SQLAlchemy models
├── schemas.py      # Pydantic schemas
└── app.py          # FastAPI application

frontend/src/
├── components/     # Reusable Vue components
├── views/          # Page components
├── stores/         # Pinia stores
├── i18n/           # Translations (EN/FR)
└── api.js          # Axios client

worker/
└── tasks.py        # Celery async tasks
```

## Testing Checklist

Before submitting a PR:

- [ ] Application builds without errors (`docker-compose up --build`)
- [ ] Existing functionality still works
- [ ] New features work as expected
- [ ] No console errors in browser
- [ ] Translations added for new text (EN + FR)

## Questions?

Open an issue with the `question` label.
