# Local Development Setup Guide - After Frontend Docker Removal

## What Changed

### Files Modified
1. **`docker-compose.yml`** - Removed the entire frontend service (lines 4-15)
2. **`Dockerfile.frontend`** - **DELETED** (no longer needed)

### Files Unchanged (Important)
- **`frontend-template/`** folder - **KEPT** (it's a reusable template for future projects)
- All backend services remain in Docker
- Frontend source code in `frontend/` folder unchanged

## Step-by-Step Local Setup

### Prerequisites
- Docker and Docker Compose installed
- Node.js 18+ installed
- Poetry installed (for Python dependencies)

### 1. Clone and Navigate to Repository
```bash
git clone https://github.com/Sundi1972/Swisper_Core.git
cd Swisper_Core
```

### 2. Pull Latest Changes (if updating existing repo)
```bash
git checkout main
git pull origin main
```

### 3. Set Up Environment Variables

#### Backend Environment (.env in root directory)
Create a `.env` file in the root directory:
```bash
# Backend environment variables
POSTGRES_DB=swisper_db
POSTGRES_USER=swisper_user
POSTGRES_PASSWORD=your_password_here
OPENAI_API_KEY=your_openai_key_here
SEARCHAPI_API_KEY=your_searchapi_key_here
```

#### Frontend Environment (.env in frontend/ directory)
Create a `.env` file in the `frontend/` directory:
```bash
# Frontend environment variables
VITE_API_BASE_URL=http://localhost:8000
```

**Important**: The frontend `.env` file is required to connect to the backend API. Without it, the frontend will try to connect to port 8001 instead of 8000 where the backend actually runs.

#### Frontend Environment (.env in frontend/ directory)
Create a `.env` file in the `frontend/` directory:
```bash
# Frontend environment variables
VITE_API_BASE_URL=http://localhost:8000
```

**Important**: The frontend `.env` file is required to connect to the backend API. Without it, the frontend will try to connect to port 8001 instead of 8000 where the backend actually runs.

### 4. Start Backend Services (Docker)
```bash
# Start all backend services (gateway, postgres, redis)
docker-compose up --build

# Or run in background
docker-compose up --build -d
```

**Backend services will be available at:**
- Gateway API: `http://localhost:8000`
- PostgreSQL: `localhost:5432`
- Redis: `localhost:6379`

### 5. Start Frontend (Manual - No Docker)
Open a **new terminal** and run:
```bash
cd frontend
npm install
npm run dev
```

**Frontend will be available at:**
- Frontend UI: `http://localhost:5173`

### 6. Verify Everything Works
1. **Backend**: Visit `http://localhost:8000/docs` (FastAPI docs)
2. **Frontend**: Visit `http://localhost:5173` (React app)
3. **Integration**: Frontend should connect to backend API automatically

## New Development Workflow

### Daily Development
1. **Start backend**: `docker-compose up -d` (runs in background)
2. **Start frontend**: `cd frontend && npm run dev` (runs with hot reload)
3. **Develop**: Make changes to frontend code, see instant updates
4. **Stop**: `Ctrl+C` for frontend, `docker-compose down` for backend

### Benefits of This Setup
- ✅ **Faster frontend development** - No Docker rebuild needed
- ✅ **Hot module replacement** - Instant code changes
- ✅ **Better debugging** - Direct access to browser dev tools
- ✅ **Simplified workflow** - Backend stays containerized for consistency

## Frontend-Template Folder Explanation

### What is `frontend-template/`?
The `frontend-template/` folder is a **reusable template** for creating new Swisper frontend applications. It should be **KEPT**.

### Purpose & Contents
- **Modern tech stack**: React 19 + TypeScript + Vite + Tailwind CSS
- **Reusable UI components**: Button, InputField, TabBar, Header, Sidebar
- **Integration patterns**: Pre-configured for Swisper Core backend
- **Development standards**: Establishes coding patterns for future projects

### When to Use
- Creating new frontend applications for Swisper
- Starting fresh frontend projects with consistent patterns
- Reference for component structure and TypeScript configuration

### How to Use
```bash
# Copy template to create new frontend project
cp -r frontend-template/ my-new-frontend/
cd my-new-frontend/
npm install
npm run dev
```

## Troubleshooting

### Backend Issues
```bash
# Check backend logs
docker-compose logs gateway

# Restart backend services
docker-compose down
docker-compose up --build
```

### Frontend Issues
```bash
# Clear node modules and reinstall
cd frontend
rm -rf node_modules package-lock.json
npm install
npm run dev
```

### Connection Issues
If you see "Something went wrong" when testing queries:
1. **Check frontend/.env file exists** with `VITE_API_BASE_URL=http://localhost:8000`
2. **Verify backend is running** at `http://localhost:8000/docs`
3. **Check browser network tab** for failed API calls
4. **Restart frontend** after creating/modifying .env file

### Port Conflicts
- Backend (8000): Change in `docker-compose.yml` ports section
- Frontend (5173): Change in `frontend/vite.config.js`

### Environment Variables
- Backend: Add to `.env` file in root directory
- Frontend: Add to `frontend/.env` with `VITE_` prefix

## Testing Your Setup

### Run Linting
```bash
# Backend linting
poetry run pylint contract_engine gateway haystack_pipeline orchestrator tool_adapter

# Frontend linting
cd frontend && npm run lint
```

### Run Tests
```bash
# Backend tests
poetry run pytest

# Frontend tests (if available)
cd frontend && npm test
```

## Summary

**Before (Docker):**
- Frontend ran in Docker container
- Slower development cycle
- Required Docker rebuild for changes

**After (Manual):**
- Frontend runs with `npm run dev`
- Instant hot reload
- Backend services still in Docker
- Faster development workflow

The `frontend-template/` folder is a valuable reusable template and should be kept for future projects.
