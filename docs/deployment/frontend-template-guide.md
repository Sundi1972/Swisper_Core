# Frontend Template Guide

## Overview

The `frontend-template/` directory contains a reusable React + TypeScript + Vite template for building Swisper frontend applications. This template provides a solid foundation with modern tooling and best practices.

## Template Assessment

### Technology Stack

**Core Technologies**:
- **React 19.0.0**: Latest React with concurrent features
- **TypeScript 5.7.2**: Strong typing for better development experience
- **Vite 6.2.0**: Fast build tool with hot module replacement
- **Tailwind CSS 3.4.17**: Utility-first CSS framework

**Development Tools**:
- **Prettier**: Code formatting
- **ESLint**: Code linting (configured via package.json scripts)
- **PostCSS**: CSS processing with Autoprefixer

### Template Structure

```
frontend-template/
├── src/
│   ├── components/
│   │   ├── ui/                 # Reusable UI components
│   │   │   ├── Button.tsx      # Styled button component
│   │   │   ├── InputField.tsx  # Form input component
│   │   │   └── TabBar.tsx      # Tab navigation component
│   │   └── common/             # Common layout components
│   │       ├── Header.tsx      # Application header
│   │       └── Sidebar.tsx     # Navigation sidebar
│   ├── pages/                  # Page components
│   ├── styles/                 # Global styles and Tailwind config
│   └── types/                  # TypeScript type definitions
├── public/                     # Static assets
├── package.json               # Dependencies and scripts
├── tsconfig.json              # TypeScript configuration
├── tailwind.config.js         # Tailwind CSS configuration
└── vite.config.ts             # Vite build configuration
```

## Reusable Components

### UI Components

**Button Component** (`src/components/ui/Button.tsx`):
```typescript
interface ButtonProps {
  children: React.ReactNode;
  onClick?: () => void;
  variant?: 'primary' | 'secondary' | 'outline';
  size?: 'sm' | 'md' | 'lg';
  disabled?: boolean;
  className?: string;
}
```

**Features**:
- Multiple variants (primary, secondary, outline)
- Size variations (small, medium, large)
- Disabled state handling
- Custom className support
- Tailwind CSS styling with dark theme support

**InputField Component** (`src/components/ui/InputField.tsx`):
```typescript
interface InputFieldProps {
  placeholder?: string;
  value?: string;
  onChange?: (e: React.ChangeEvent<HTMLInputElement>) => void;
  className?: string;
  type?: string;
  disabled?: boolean;
}
```

**Features**:
- Controlled component pattern
- Type support (text, password, email, etc.)
- Disabled state handling
- Consistent styling with focus states
- Placeholder support

### Common Components

**Header Component** (`src/components/common/Header.tsx`):
- Application branding and navigation
- User authentication status
- Responsive design
- Dark theme support

**Sidebar Component** (`src/components/common/Sidebar.tsx`):
- Navigation menu
- Collapsible design
- Active state indication
- Mobile-responsive

## Configuration Issues and Fixes

### Current Issues

1. **TypeScript Configuration**:
   - Path mapping configuration needs verification
   - Some strict type checking options could be enhanced

2. **Package.json Issues**:
   - Build script has `--noCheck` flag which bypasses type checking
   - Missing some development dependencies for optimal DX

### Recommended Fixes

**1. Fix TypeScript Build Script**:
```json
{
  "scripts": {
    "build": "tsc && vite build",
    "build:check": "tsc --noEmit && vite build"
  }
}
```

**2. Enhanced TypeScript Configuration**:
```json
{
  "compilerOptions": {
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noImplicitReturns": true,
    "noFallthroughCasesInSwitch": true
  }
}
```

**3. Add Missing Development Dependencies**:
```json
{
  "devDependencies": {
    "@typescript-eslint/eslint-plugin": "^6.0.0",
    "@typescript-eslint/parser": "^6.0.0",
    "eslint": "^8.0.0",
    "eslint-plugin-react": "^7.33.0",
    "eslint-plugin-react-hooks": "^4.6.0"
  }
}
```

## Usage Guide

### Creating a New Frontend Application

1. **Copy Template**:
   ```bash
   cp -r frontend-template/ my-new-app/
   cd my-new-app/
   ```

2. **Update Package Configuration**:
   ```bash
   # Update package.json name and version
   npm pkg set name="my-new-app"
   npm pkg set version="1.0.0"
   ```

3. **Install Dependencies**:
   ```bash
   npm install
   ```

4. **Start Development**:
   ```bash
   npm run start
   ```

### Customization Guidelines

**1. Theming**:
- Modify `tailwind.config.js` for custom colors and spacing
- Update CSS custom properties in `src/styles/index.css`
- Customize component variants in UI components

**2. Component Extension**:
- Add new UI components following existing patterns
- Maintain consistent prop interfaces
- Include TypeScript types for all props

**3. Routing Setup**:
- Install React Router: `npm install react-router-dom`
- Configure routes in `src/App.tsx`
- Add route-based code splitting

## Integration with Swisper Core

### API Integration

**Environment Configuration**:
```typescript
// src/config/api.ts
export const API_CONFIG = {
  baseURL: process.env.VITE_API_BASE_URL || 'http://localhost:8000',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  }
};
```

**API Client Setup**:
```typescript
// src/services/api.ts
class SwisperAPIClient {
  private baseURL: string;
  
  constructor(baseURL: string) {
    this.baseURL = baseURL;
  }
  
  async chat(message: string, sessionId?: string) {
    const response = await fetch(`${this.baseURL}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, session_id: sessionId })
    });
    return response.json();
  }
}
```

### State Management

**Context Setup for Swisper Integration**:
```typescript
// src/context/SwisperContext.tsx
interface SwisperContextType {
  sessionId: string | null;
  messages: Message[];
  isLoading: boolean;
  sendMessage: (message: string) => Promise<void>;
}

export const SwisperContext = createContext<SwisperContextType | null>(null);
```

### Component Patterns

**Chat Interface Components**:
- `ChatContainer`: Main chat interface
- `MessageList`: Display conversation history
- `MessageInput`: User input component
- `ProductDisplay`: Show product search results
- `PreferenceSelector`: Handle user preferences

## Best Practices

### Development Workflow

1. **Component Development**:
   - Start with TypeScript interfaces
   - Implement component logic
   - Add styling with Tailwind
   - Write unit tests
   - Document component usage

2. **State Management**:
   - Use React Context for global state
   - Keep component state local when possible
   - Implement proper error boundaries
   - Handle loading states consistently

3. **Performance Optimization**:
   - Use React.memo for expensive components
   - Implement code splitting for routes
   - Optimize bundle size with tree shaking
   - Use proper key props for lists

### Code Quality

**TypeScript Best Practices**:
- Define strict interfaces for all props
- Use union types for component variants
- Implement proper error handling
- Avoid `any` types

**React Best Practices**:
- Use functional components with hooks
- Implement proper cleanup in useEffect
- Handle edge cases and error states
- Follow React naming conventions

## Deployment Considerations

### Build Optimization

**Vite Configuration**:
```typescript
// vite.config.ts
export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom'],
          router: ['react-router-dom']
        }
      }
    }
  }
});
```

### Environment Variables

**Production Configuration**:
```bash
# .env.production
VITE_API_BASE_URL=https://api.swisper.ch
VITE_APP_VERSION=1.0.0
VITE_ENVIRONMENT=production
```

## Recommendation

### Keep as Reusable Template

**Reasons to Maintain**:
1. **Modern Stack**: React 19 + TypeScript + Vite provides excellent DX
2. **Reusable Components**: Well-structured UI components save development time
3. **Consistent Patterns**: Establishes coding standards for future projects
4. **Tailwind Integration**: Utility-first CSS approach scales well

**Improvements Needed**:
1. Fix TypeScript configuration issues
2. Add comprehensive ESLint configuration
3. Include testing setup (Jest + React Testing Library)
4. Add Storybook for component documentation
5. Create deployment scripts and CI/CD configuration

### Next Steps

1. **Fix Configuration Issues**:
   - Update build scripts to include type checking
   - Add missing development dependencies
   - Enhance TypeScript strict mode settings

2. **Add Testing Infrastructure**:
   - Configure Jest and React Testing Library
   - Add example tests for components
   - Set up test coverage reporting

3. **Documentation Enhancement**:
   - Add component documentation with examples
   - Create usage guidelines for new developers
   - Document integration patterns with Swisper Core

4. **Template Maintenance**:
   - Regular dependency updates
   - Security vulnerability monitoring
   - Performance optimization guidelines

The frontend template provides significant value for future Swisper frontend implementations and should be maintained as a reusable foundation with the recommended improvements.
