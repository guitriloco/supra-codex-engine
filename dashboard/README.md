# Supra-Codex Engine — Orchestration Dashboard

The frontend dashboard for managing the Supra-Codex distributed automation platform.

## Tech Stack

- **React 18** — UI framework
- **TypeScript** — type safety
- **Vite 5** — build tool & dev server
- **Tailwind CSS v4** — utility-first styling
- **React Router v6** — client-side routing
- **Lucide React** — icon library

## Getting Started

```bash
# Install dependencies
bun install

# Start dev server (hot reload)
bun run dev

# Build for production
bun run build

# Preview production build
bun run preview
```

The dev server runs on **http://localhost:3000**.

## Project Structure

```
src/
├── components/       # Shared UI components (Button, Card, Sidebar, TopBar)
├── context/          # React context providers (AuthContext)
├── pages/            # Route page components
├── lib/              # Utility functions (future)
├── assets/           # Static assets (future)
├── App.tsx           # Router & layout setup
├── main.tsx          # Entry point
└── index.css         # Global styles & Tailwind config
```

## Routes

| Path | Page | Description |
|------|------|-------------|
| `/login` | Login | Authentication page |
| `/` | Dashboard | Infrastructure overview |
| `/pipelines` | Pipelines | Pipeline management |
| `/nodes` | Nodes | Cluster node view |
| `/marketplace` | Marketplace | Nectar module store |
| `/settings` | Settings | Account & preferences |

## Configuration

Copy `.env.example` to `.env` and set your API endpoints:

```
VITE_API_URL=http://localhost:8080
VITE_WS_URL=ws://localhost:8080/ws
```

## Design

Dark theme with a clean, professional aesthetic inspired by Vercel/Netlify dashboards.
The colour system uses CSS custom properties defined via Tailwind's `@theme` directive.

## License

Proprietary — Supra-Codex Engine