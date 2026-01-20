# Coding Standards

## General Rules

### 1. Code Comments
- NO COMMENTS unless explicitly requested
- Code should be self-documenting
- Use descriptive variable and function names
- Extract complex logic into named functions

### 2. Code Style
- Follow existing project conventions
- Maintain consistent indentation
- Use project's formatting tools
- Never mix tabs and spaces

### 3. Naming Conventions

#### Variables
- camelCase for JavaScript/TypeScript
- snake_case for Python
- Descriptive names over short names
- Boolean prefixes: is, has, should

#### Functions
- Verb prefixes for actions
- get/set for accessors
- handle for event handlers
- validate for validation functions

#### Constants
- UPPER_SNAKE_CASE for true constants
- PascalCase for constructor functions
- Prefix with DEFAULT_ for defaults

## Language-Specific Standards

### JavaScript/TypeScript
```typescript
// Prefer const over let
const userCount = users.length

// Use arrow functions for callbacks
users.map(user => user.name)

// Destructuring over property access
const { name, email } = user

// Template literals over concatenation
const message = `Hello ${name}`
```

### Python
```python
# Type hints for function signatures
def process_user(user_id: int) -> User:
    pass

# List comprehensions for simple transforms
active_users = [u for u in users if u.is_active]

# Context managers for resources
with open('file.txt') as f:
    content = f.read()
```

## Testing Standards

### Test Organization
- One test file per source file
- Group related tests in describe blocks
- Test file naming: `*.test.ts` or `*_test.py`
- Clear test descriptions

### Test Structure
```typescript
describe('UserService', () => {
  describe('createUser', () => {
    it('should create user with valid data', () => {
      // Arrange
      // Act
      // Assert
    })
  })
})
```