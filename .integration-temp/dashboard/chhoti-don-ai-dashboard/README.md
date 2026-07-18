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

## Connect a real AI backend

Replace the timeout-based mock response inside `src/App.jsx` with your API request. Keep `thinking` true while awaiting the response, then append the returned assistant message to `messages`.
