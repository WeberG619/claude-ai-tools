# API Integration Standards

## REST API Integration

### 1. Client Configuration
```typescript
class ApiClient {
  private baseURL: string
  private timeout: number
  
  constructor(config: ApiConfig) {
    this.baseURL = config.baseURL
    this.timeout = config.timeout || 5000
  }
  
  async request<T>(options: RequestOptions): Promise<T> {
    // Add auth headers
    // Handle errors
    // Parse response
  }
}
```

### 2. Error Handling
```typescript
class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string
  ) {
    super(message)
  }
}

// Usage
try {
  const data = await api.get('/users')
} catch (error) {
  if (error instanceof ApiError) {
    // Handle API errors
  }
}
```

### 3. Response Types
Always define response types:

```typescript
interface ApiResponse<T> {
  data: T
  meta?: {
    page: number
    total: number
  }
  errors?: ApiError[]
}

interface User {
  id: string
  name: string
  email: string
}
```

## GraphQL Integration

### 1. Query Organization
```
src/graphql/
├── queries/
│   ├── user.queries.ts
│   └── product.queries.ts
├── mutations/
│   ├── user.mutations.ts
│   └── product.mutations.ts
└── fragments/
    └── user.fragments.ts
```

### 2. Type Generation
- Use code generation tools
- Never manually write types
- Keep schema in sync
- Version control generated files

## WebSocket Integration

### 1. Connection Management
```typescript
class WebSocketClient {
  private ws: WebSocket | null = null
  private reconnectAttempts = 0
  
  connect() {
    // Implement reconnection logic
    // Handle connection states
    // Queue messages when disconnected
  }
}
```

### 2. Event Handling
- Use event emitter pattern
- Type-safe event definitions
- Handle reconnection gracefully
- Implement heartbeat/ping-pong