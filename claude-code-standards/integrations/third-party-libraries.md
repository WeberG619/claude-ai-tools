# Third-Party Library Standards

## Library Selection Rules

### 1. Pre-Check Requirements
- ALWAYS check if library already exists in project
- Review package.json, requirements.txt, Cargo.toml
- Never assume popular libraries are available
- Check neighboring files for imports

### 2. Selection Criteria
- Active maintenance (recent updates)
- Good documentation
- Appropriate license
- Security track record
- Community support
- Bundle size (for frontend)

### 3. Version Management
- Use exact versions in production
- Document breaking changes
- Test updates thoroughly
- Keep dependencies minimal

## Integration Patterns

### 1. Wrapper Pattern
Always wrap third-party libraries:

```typescript
// Bad: Direct usage throughout codebase
import axios from 'axios'
axios.get('/api/users')

// Good: Wrapped in service
export class ApiClient {
  async get(url: string) {
    return axios.get(url)
  }
}
```

### 2. Configuration
Centralize library configuration:

```typescript
// config/libraries.ts
export const libraryConfig = {
  axios: {
    timeout: 5000,
    baseURL: process.env.API_URL
  },
  logger: {
    level: process.env.LOG_LEVEL
  }
}
```

## Common Libraries

### Frontend
- **State**: Redux, Zustand, MobX
- **Routing**: React Router, Vue Router
- **Forms**: React Hook Form, Formik
- **Styling**: Styled Components, Emotion
- **HTTP**: Axios, Fetch API

### Backend
- **Web**: Express, Fastify, Koa
- **Database**: Prisma, TypeORM, Mongoose
- **Validation**: Joi, Yup, Zod
- **Authentication**: Passport, JWT
- **Testing**: Jest, Mocha, Pytest

### Utilities
- **Dates**: date-fns, dayjs (not moment)
- **Utilities**: Lodash (tree-shakeable)
- **Validation**: Zod, Yup
- **HTTP**: Axios, node-fetch