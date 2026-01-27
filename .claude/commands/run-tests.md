# Run Tests

Run all tests and report results.

## Steps

1. **Run backend tests**
   ```bash
   make test
   ```

2. **Run frontend build** (type checking)
   ```bash
   cd frontend && npm run build
   ```

3. **Run frontend lint**
   ```bash
   cd frontend && npm run lint
   ```

4. **Run Playwright E2E tests** (if frontend changes)
   ```bash
   cd frontend && npm run test:e2e
   ```

5. **Summarize results**
   - Number of tests passed/failed
   - Any type errors
   - Any lint errors
   - Suggested fixes for failures

## Arguments

- `/run-tests backend` - Only run backend tests
- `/run-tests frontend` - Only run frontend tests
- `/run-tests e2e` - Only run Playwright tests
