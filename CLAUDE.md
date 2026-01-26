# Project Guidelines

## Python Code Standards

Follow these to pass CI lint checks:

- **No unused imports** - Only import what you use
- **No unused variables** - Remove or use all declared variables
- **Line length** - Keep under 100 characters (but E501 is ignored)
- **Import order** - stdlib, then third-party, then local (ruff will fix this)

## Before Committing

Always run before committing Python changes:
```bash
poetry run ruff format . && poetry run ruff check --fix .
```

For frontend changes:
```bash
cd frontend && npm run lint -- --fix
```
