# Design Pattern Standards

## Common Patterns

### 1. Repository Pattern
Used for data access abstraction:

```typescript
interface UserRepository {
  findById(id: string): Promise<User>
  findAll(): Promise<User[]>
  save(user: User): Promise<void>
  delete(id: string): Promise<void>
}
```

### 2. Service Pattern
Business logic encapsulation:

```typescript
class UserService {
  constructor(private userRepo: UserRepository) {}
  
  async createUser(data: CreateUserDto): Promise<User> {
    // Business logic here
    return this.userRepo.save(user)
  }
}
```

### 3. Factory Pattern
Object creation logic:

```typescript
class ConfigFactory {
  static create(env: string): Config {
    switch(env) {
      case 'production': return new ProdConfig()
      case 'development': return new DevConfig()
      default: return new DefaultConfig()
    }
  }
}
```

## State Management

### Frontend State
- Use Context API for simple state
- Redux/Zustand for complex state
- Local component state when possible
- Avoid prop drilling

### Backend State
- Stateless services
- Database for persistent state
- Cache for temporary state
- Session management patterns

## Error Handling

### Standard Error Structure
```typescript
class AppError extends Error {
  constructor(
    public statusCode: number,
    public message: string,
    public isOperational = true
  ) {
    super(message)
  }
}
```

### Error Propagation
- Catch at boundaries
- Log with context
- Return user-friendly messages
- Preserve stack traces in development