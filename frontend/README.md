# Frontend (FR-09 MVP)

Simple React + TypeScript + MUI frontend for posting requests to `/search` and rendering ranked candidate responses.

## Stack
- React 19 + TypeScript
- Vite
- MUI (Material UI)

## Setup
1. Install dependencies

```bash
cd frontend
npm install
```

2. Create local env file (optional)

```bash
cp .env.example .env
```

- Default `VITE_API_BASE_URL` is `/api`.
- `vite.config.ts` proxies `/api/*` to `http://localhost:8000/*` in dev.

3. Start dev server

```bash
npm run dev
```

## Backend requirement
Run backend API locally at:
- `http://localhost:8000`

The frontend sends requests to:
- `POST /search` (through `/api/search` proxy in dev)

## Build
```bash
npm run build
```

## MVP scope
- Natural language query input
- Full hard filter input fields (`skill_terms`, `occupation_terms`, `industry_terms`, `experience`, `education`, `locations`, `limit`)
- Search response visualization (ranking cards, scores, summaries, matches, gaps)
- English UI with an industrial visual theme
