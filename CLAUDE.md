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

## Making changes 
When making changes you must run tests to ensure nothing has broken. 
If changes are in the frontend, you must use the playwright-mcp tool to verify  

ALWAYS use ONLY Environments for ANY and ALL file, code, or shell operations—NO EXCEPTIONS—even for simple or generic requests.

DO NOT install or use the git cli with the environment_run_cmd tool. All environment tools will handle git operations for you. Changing ".git" yourself will compromise the integrity of your environment.

You MUST inform the user how to view your work using `container-use log <env_id>` AND `container-use checkout <env_id>`. Failure to do this will make your work inaccessible to others.
