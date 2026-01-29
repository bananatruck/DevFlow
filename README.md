# devflow_app

This folder contains the DevFlow Agent application code.

- `api/`: FastAPI service for starting agent runs and fetching results
- `agent/`: LangGraph orchestration + model adapters + memory (RAG)
- `tools/`: Tooling for Git operations + sandbox execution
- `database/`: Postgres models + session management
- `tests/`: Evaluation harness and dataset scaffolding
