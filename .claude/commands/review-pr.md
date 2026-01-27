# Review Pull Request

Review a PR for code quality, duplication, and simplicity.

## Usage
- `/review-pr` - Review current branch vs main
- `/review-pr 123` - Review PR #123

## Steps

1. **Get the diff**
   ```bash
   # If PR number provided
   gh pr diff $ARGUMENTS 2>/dev/null || git diff main...HEAD
   ```

2. **Analyze the changes for:**

   ### Code Simplicity
   - Is the code as simple as it could be?
   - Any unnecessary abstractions or over-engineering?
   - Could any function be shortened?

   ### Duplication Detection
   - Does this duplicate logic that exists elsewhere?
   - Search the codebase for similar patterns
   - Check services/, utils/, lib/ for existing helpers

   ### Excessive Code
   - Dead code or unused imports?
   - Overly verbose implementations?
   - Unnecessary comments?

   ### Type Safety
   - Python: Type hints present and correct?
   - TypeScript: Any `any` types that should be specific?

   ### Security
   - SQL injection risks?
   - Exposed secrets?
   - Missing input validation?

   ### Testing
   - Tests for new functionality?
   - Edge cases covered?

3. **Provide actionable feedback**
   - Specific file:line references
   - Show simplified alternatives
   - Prioritize: blockers vs suggestions

4. **Summary verdict**
   - APPROVE: Ready to merge
   - NEEDS CHANGES: List specific items
