# Code Organization Standards

## Project Structure Patterns

### Frontend Projects

```
src/
├── components/       # Reusable UI components
│   ├── common/      # Shared components
│   └── features/    # Feature-specific components
├── pages/           # Page-level components
├── services/        # API and external services
├── hooks/           # Custom React/Vue hooks
├── utils/           # Utility functions
├── types/           # TypeScript definitions
└── styles/          # Global styles
```

### Backend Projects

```
src/
├── controllers/     # Request handlers
├── models/          # Data models
├── services/        # Business logic
├── repositories/    # Data access layer
├── middleware/      # Express/framework middleware
├── utils/           # Helper functions
├── config/          # Configuration files
└── types/           # Type definitions
```

## Architecture Principles

### 1. Separation of Concerns
- Keep business logic in services
- Data access in repositories
- HTTP handling in controllers
- UI logic in components

### 2. Dependency Direction
- Dependencies flow inward
- Core domain has no external dependencies
- Infrastructure depends on domain
- UI depends on application layer

### 3. Module Organization
- Group by feature, not by file type
- Keep related files close together
- Minimize cross-feature dependencies
- Use barrel exports (index files)

## Component Structure

### React/Vue Components
```
ComponentName/
├── ComponentName.tsx      # Main component
├── ComponentName.test.tsx # Tests
├── ComponentName.styles.ts # Styles
├── types.ts              # Local types
└── index.ts              # Barrel export
```

### Service Structure
```
ServiceName/
├── ServiceName.ts        # Main service
├── ServiceName.test.ts   # Tests
├── types.ts             # Service types
└── index.ts             # Export
```