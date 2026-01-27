# Start Feature

Begin implementing the next task from the PRD.

## Steps

1. **Read the task ledger**
   ```bash
   cat .claude/task-ledger.json
   ```

2. **Identify next pending task** from the current sprint

3. **Read the relevant PRD section** for full requirements
   ```bash
   cat prd.md
   ```

4. **Create feature branch**
   ```bash
   git checkout main
   git pull origin main
   git checkout -b feature/{task-name}
   ```

5. **Update task ledger** - mark task as `in_progress`

6. **Implement the feature** following the worker agent workflow:
   - Backend: schemas -> models -> migration -> service -> API -> tests
   - Frontend: types -> API client -> hook -> component -> page -> tests

7. **Verify**
   - Backend: `make test`
   - Frontend: `cd frontend && npm run build`

8. **When complete**, use `/commit-and-pr` to finalize

## Arguments

If called with an argument (e.g., `/start-feature sprint1-task3`), start that specific task instead of the next pending one.
