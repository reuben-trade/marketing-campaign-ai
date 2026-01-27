# Commit and Create PR

Commit current changes and create a pull request.

## Prerequisites

Before running this command:
- All tests should pass (`make test`)
- Frontend should build (`cd frontend && npm run build`)
- Code should be linted (`make lint`)

## Steps

1. **Check current status**
   ```bash
   git status
   git diff --stat
   ```

2. **Stage changes**
   ```bash
   git add -A
   ```

3. **Create commit** with descriptive message (NO Claude attribution)
   ```bash
   git commit -m "feat: {description}

   - {change 1}
   - {change 2}

   Implements: {PRD section reference}"
   ```

   IMPORTANT: Do NOT add "Co-Authored-By: Claude" or any AI attribution.

4. **Push to remote**
   ```bash
   git push -u origin $(git branch --show-current)
   ```

5. **Create PR**
   ```bash
   gh pr create --title "feat: {title}" --body "## Summary
   {Brief description of changes}

   ## PRD Reference
   {Link to relevant PRD section}

   ## Changes
   - {change 1}
   - {change 2}

   ## Testing
   - [ ] Backend tests pass
   - [ ] Frontend builds successfully
   - [ ] New functionality has test coverage

   ## Screenshots (if UI changes)
   {Add screenshots if applicable}"
   ```

6. **Update task ledger** - mark task as `completed`, add PR number

## Arguments

If called with a message argument (e.g., `/commit-and-pr "Add project model"`), use that as the commit title.
