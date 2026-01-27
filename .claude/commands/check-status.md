# Check Status

Review current progress on PRD implementation.

## Steps

1. **Read task ledger**
   ```bash
   cat .claude/task-ledger.json
   ```

2. **Show git status**
   ```bash
   git status
   git branch -v
   ```

3. **List open PRs**
   ```bash
   gh pr list
   ```

4. **Summarize progress**
   - Current sprint number
   - Tasks completed vs total in current sprint
   - Current task in progress (if any)
   - Any blocked tasks

5. **Suggest next action**
   - If a task is in progress: continue working on it
   - If no task in progress: suggest `/start-feature`
   - If sprint complete: note readiness for next sprint
