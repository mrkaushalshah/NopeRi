# Project Startup Commands

This document lists all the necessary commands to start different parts of the NopeRi project, including the core Python backend (Naukri bot) and Phase 6 (Local Company Outreach Engine).

## 1. Environment Setup (One-time)
Make sure you have your virtual environment set up (if any) and dependencies installed.
```bash
# Install Python backend dependencies
pip install -r requirements.txt

# Install UI frontend dependencies
cd ui
npm install
```

## 2. Core Project / Previous Phases (Naukri Automation)

To run the main Naukri bot/AI agent script:
```bash
python main.py
```
*(Alternatively, use `py main.py` on Windows)*

To run the daily update script:
```bash
python updateDaily.py
```

## 3. Phase 6 (Local Company Outreach Engine)

Phase 6 consists of a FastAPI backend and an Angular frontend. You need to run **both** in separate terminal windows.

### Start the FastAPI Backend
From the root directory (`NopeRi`), run:
```bash
uvicorn src.api.app:app --reload
```
*(If `uvicorn` is not in your path, you can run `python -m uvicorn src.api.app:app --reload`)*

### Start the Angular UI (Frontend)
Open a new terminal, navigate to the `ui` directory, and start the development server:
```bash
cd ui
npm start
```
*(This will run `ng serve`. You can access the UI at `http://localhost:4200`)*

## Summary of All Running Processes for Full System
If you want to run the complete Phase 6 experience, you need these running simultaneously:
1. `uvicorn src.api.app:app --reload` (Backend API)
2. `cd ui && npm start` (Angular UI)
