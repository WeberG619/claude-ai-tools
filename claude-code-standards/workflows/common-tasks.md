# Common Task Workflows

## Feature Implementation Workflow

### 1. Initial Analysis
- Search for similar existing features
- Review current architecture
- Check for reusable components
- Identify required dependencies

### 2. Planning Phase
- Create TodoWrite list for complex tasks
- Break down into manageable steps
- Identify test requirements
- Plan integration points

### 3. Implementation Steps
1. Create/modify data models
2. Implement business logic
3. Add API endpoints/handlers
4. Create UI components
5. Write tests
6. Update documentation (if requested)

### 4. Verification
- Run linter and formatter
- Execute test suite
- Check type safety
- Manual testing

## Bug Fix Workflow

### 1. Investigation
```bash
# Search for error patterns
Task: "Search for error message in codebase"

# Check recent changes
git log --oneline -10

# Review related files
Grep pattern="ErrorClassName" include="*.ts"
```

### 2. Root Cause Analysis
- Reproduce the issue
- Add logging if needed
- Check edge cases
- Review related tests

### 3. Fix Implementation
- Make minimal changes
- Add test for the bug
- Verify fix doesn't break other features
- Clean up debug code

## Refactoring Workflow

### 1. Pre-Refactoring
- Ensure tests pass
- Create safety net tests
- Document current behavior
- Plan refactoring steps

### 2. Refactoring Steps
- Make small incremental changes
- Run tests after each change
- Keep commits atomic
- Preserve functionality

### 3. Post-Refactoring
- Verify all tests pass
- Check performance impact
- Update documentation
- Clean up old code