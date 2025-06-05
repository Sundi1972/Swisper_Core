Swisper Core

Swisper Core is a modular, privacy-first AI assistant architecture designed to reason, plan, and act on behalf of users. It blends LLM intelligence (GPT -4o) with structured contract execution, RAG-based document Q&A, and plug-and-play tool orchestration.

This refactored version introduces Haystack pipelines, a modular contract engine, and end-to-end Playwright tests.

🚀 What It Does

Swisper Core can:

🏍️ Execute contract-based product purchases

🧠 Answer document-based questions with RAG pipelines

🧪 Run unit tests and browser-based E2E flows

🔌 Interact with mock tools (like Google Shopping) via adapters

🧱 Project Structure

Path

Description

gateway/

FastAPI backend (main entrypoint)

frontend/

React + Tailwind frontend

orchestrator/

LLM routing, tool registry, session mgmt

contract_engine/

YAML-based contract execution engine

haystack_pipeline/

Haystack pipelines for RAG Q&A

tool_adapter/

Mock Google Shopping adapter

tests/

Unit tests for orchestrator and contracts

playwright_tests/

End-to-end test flows using Playwright

docs/architecture/

System design docs and planning artifacts

⚙️ Running the App

1. Backend (FastAPI)

make dev
# or
docker-compose up --build

Runs at: http://localhost:8000

2. Frontend (React + Vite)

cd frontend
npm install
npm run dev

Runs at: http://localhost:5173

📚 Example Flows

"I want to buy a GPU" → triggers contract engine

"yes" → confirms selected product

#rag What is Swisper Core? → returns document-based answer

🧪 Testing

Unit tests (in Docker):

docker-compose exec gateway pytest tests/

E2E tests (Playwright):

npm install
npm run test:e2e

📁 Folder Highlights

contract_templates/ → YAML templates like purchase_item.yaml

schemas/ → JSON schema for validating contracts

docs/ → Sample RAG documents

tmp/contracts/ → Saved JSON purchase contracts

🛡️ Privacy First

No telemetry. No third-party tracking. Data is processed locally or with user consent via trusted APIs.

📦 Stack

Python + FastAPI

GPT -4o via OpenAI SDK

Haystack 2.x

React + Vite + Tailwind

Playwright

