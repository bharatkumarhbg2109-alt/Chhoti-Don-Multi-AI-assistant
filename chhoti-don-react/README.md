# CHHOTI DON AI Dashboard

A premium responsive Personal AI Assistant dashboard built with React, Vite, and Tailwind CSS.

## Visual identity

- CHHOTI DON branding throughout the interface
- Deep onyx and midnight-plum background
- Rose, orchid, violet, and subtle champagne accents
- Refined liquid-glass panels and focused glow effects
- CSS-only animated AI orb and custom cursor trail

## Included

- Responsive glassmorphic dashboard shell
- Mobile slide-out navigation
- Interactive chat composer and mock AI response flow
- Thinking animation and animated chat bubbles
- Accessibility-minded motion reduction support
- No heavy 3D or animation libraries

## Run locally

```bash
npm install
npm run dev
```

Open the local URL printed by Vite, normally `http://localhost:5173/`.

## Production build

```bash
npm run build
npm run preview
```

## Backend integration

This dashboard is wired to the Chhoti Don Flask backend (`app.py`, port 8000). In dev, Vite
proxies `/api` to `http://127.0.0.1:8000` (see `vite.config.js`); all calls live in
`src/services/chatApi.js` (`sendMessage`, `checkHealth`, `getStatus`, `resetMemory`).

Assistant replies are revealed with a frontend-simulated typewriter stream (the backend still
returns a single JSON response). Requests are cancellable via `AbortController`, and reduced-motion
users get instant reveal.

## Primary vs. fallback UI

- **Primary:** this React dashboard — `http://127.0.0.1:5173`.
- **Fallback:** the legacy single-file UI — `http://127.0.0.1:8000/` (served directly by `app.py`).

On Windows, `Start-ChhotiDon.ps1` in the project root starts the backend and this frontend, then
opens the React app automatically.
