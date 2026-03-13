# FolioChat — Next.js Integration Example

Add a floating AI portfolio chatbot to your Next.js site in **under 5 minutes**.

---

## Quick Start

### 1. Build and start the FolioChat server

```bash
pip install foliochat

# Build the vector database from your GitHub profile
foliochat build --username <your-github-username>

# Start the API server (defaults to http://localhost:8000)
foliochat serve --username <your-github-username>
```

> **Tip:** Use `--embedder openai` for better retrieval quality, or `--llm ollama` to run fully locally for free.

### 2. Install the React widget

In your Next.js project:

```bash
npm install foliochat
```

### 3. Set your environment variable

Copy `.env.example` to `.env.local` in your Next.js project root:

```bash
cp .env.example .env.local
```

Edit `.env.local`:

```env
NEXT_PUBLIC_FOLIOCHAT_URL=http://localhost:8000
```

For production, replace `http://localhost:8000` with the public URL where your
FolioChat server is deployed.

### 4. Add the widget to your layout

Copy `layout.tsx` into your `app/` directory (Next.js App Router):

```bash
cp layout.tsx <your-nextjs-project>/app/layout.tsx
```

Or add just the `<FolioChat>` component to your existing layout:

```tsx
// app/layout.tsx
import { FolioChat } from "foliochat";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const foliochatUrl = process.env.NEXT_PUBLIC_FOLIOCHAT_URL ?? "http://localhost:8000";

  return (
    <html lang="en">
      <body>
        {children}
        <FolioChat
          endpoint={foliochatUrl}
          theme="dark"
          position="bottom-right"
          accentColor="#f97316"
        />
      </body>
    </html>
  );
}
```

### 5. Run your Next.js dev server

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). The 💬 button appears in
the bottom-right corner. Click it and ask about your projects!

---

## Component Props

| Prop | Type | Default | Description |
|---|---|---|---|
| `endpoint` | `string` | required | URL of your running FolioChat server |
| `theme` | `"dark"` \| `"light"` \| `"auto"` | `"dark"` | Color theme (`"auto"` follows the OS setting) |
| `position` | `"bottom-right"` \| `"bottom-left"` | `"bottom-right"` | Widget position |
| `accentColor` | `string` | `"#f97316"` | Button and highlight color (any CSS color) |
| `greeting` | `string` | auto-generated | Override the opening message |

---

## Production Deployment

1. Deploy the FolioChat server to any host that can run Python (Railway, Fly.io, a VPS, etc.).
2. Set `NEXT_PUBLIC_FOLIOCHAT_URL` in your hosting provider's environment variables to the deployed server URL.
3. Set `CORS_ORIGINS` on the FolioChat server to your portfolio's domain.

```bash
# On the server host
export CORS_ORIGINS=https://yourportfolio.com
foliochat serve --username <your-github-username> --port 8000
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Widget shows "Could not connect to FolioChat server" | Ensure `foliochat serve` is running and `NEXT_PUBLIC_FOLIOCHAT_URL` is correct |
| CORS errors in browser console | Set `CORS_ORIGINS=https://yourdomain.com` on the FolioChat server |
| Stale project data | Run `foliochat build --username <you> --refresh` to rebuild the database |
| Rate limit errors during build | Add `--token ghp_...` to use an authenticated GitHub API token |
