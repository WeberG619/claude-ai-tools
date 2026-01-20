# Git Workflow Standards

## Commit Workflow

### 1. Pre-Commit Checks
Always run in parallel:
```bash
git status
git diff
git log --oneline -5
```

### 2. Staging Files
- Review untracked files carefully
- Stage related changes together
- Avoid staging generated files
- Check for sensitive information

### 3. Commit Message Format
```
<type>: <description>

<optional body>

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>
```

Types:
- feat: New feature
- fix: Bug fix
- refactor: Code refactoring
- test: Test changes
- docs: Documentation only
- style: Formatting changes
- chore: Maintenance tasks

### 4. Never Commit Without Request
- ONLY commit when explicitly asked
- Always show what will be committed
- Get confirmation before proceeding

## Pull Request Workflow

### 1. Pre-PR Checklist
Run these commands in parallel:
```bash
git status
git diff
git log origin/main..HEAD
git diff origin/main...HEAD
```

### 2. PR Creation
```bash
# Create branch if needed
git checkout -b feature/description

# Push with tracking
git push -u origin feature/description

# Create PR with gh
gh pr create --title "Title" --body "$(cat <<'EOF'
## Summary
- Change 1
- Change 2

## Test plan
- [ ] Unit tests pass
- [ ] Manual testing completed

🤖 Generated with Claude Code
EOF
)"
```

### 3. PR Guidelines
- Keep PRs focused and small
- Include test plan
- Reference related issues
- Add reviewers if known

## Branch Management

### 1. Branch Naming
- feature/description
- fix/issue-description
- refactor/component-name
- chore/task-description

### 2. Branch Hygiene
- Delete merged branches
- Keep branches up to date
- Rebase on main regularly
- Avoid long-lived branches