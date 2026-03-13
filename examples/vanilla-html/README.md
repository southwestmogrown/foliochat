# FolioChat — Vanilla HTML / CDN Integration Example

Add a floating AI portfolio chatbot to **any static HTML page** in minutes —
no npm, no build step, no framework required.

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

### 2. Add the widget to your HTML

Open `index.html` (or copy the relevant snippet into your own page). The only
thing you need to change is the `FOLIOCHAT_URL` variable near the bottom of the
`<script>` block:

```html
var FOLIOCHAT_URL = "http://localhost:8000"; // ← change this
```

For production, replace `http://localhost:8000` with the public URL where your
FolioChat server is deployed.

### 3. Open the page in your browser

```bash
# Simplest option — open the file directly
open index.html

# Or serve it with any static file server, e.g.
npx serve .
python -m http.server 8080
```

The 💬 button appears in the bottom-right corner. Click it and ask about your
projects!

---

## How It Works

The CDN integration loads three scripts in order:

```html
<!-- 1. React runtime -->
<script src="https://unpkg.com/react@18/umd/react.production.min.js"></script>

<!-- 2. ReactDOM for rendering -->
<script src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js"></script>

<!-- 3. FolioChat UMD bundle (includes the widget) -->
<script src="https://unpkg.com/foliochat/dist/foliochat.umd.js"></script>
```

Then a small inline script mounts the widget into a placeholder `<div>`:

```html
<div id="foliochat-root"></div>
<script>
  var root = ReactDOM.createRoot(document.getElementById("foliochat-root"));
  root.render(
    React.createElement(FolioChat.FolioChat, {
      endpoint: "http://localhost:8000",
      theme: "dark",
      position: "bottom-right",
      accentColor: "#f97316",
    })
  );
</script>
```

---

## Configuration Options

| Option | Type | Default | Description |
|---|---|---|---|
| `endpoint` | `string` | required | URL of your running FolioChat server |
| `theme` | `"dark"` \| `"light"` \| `"auto"` | `"dark"` | Color theme (`"auto"` follows the OS setting) |
| `position` | `"bottom-right"` \| `"bottom-left"` | `"bottom-right"` | Widget position |
| `accentColor` | `string` | `"#f97316"` | Button and highlight color (any CSS color) |
| `greeting` | `string` | auto-generated | Override the opening message |

---

## Production Deployment

1. Deploy the FolioChat server to any host that can run Python (Railway, Fly.io, a VPS, etc.).
2. In your HTML file, update `FOLIOCHAT_URL` to the deployed server URL:
   ```js
   var FOLIOCHAT_URL = "https://foliochat.yourserver.com";
   ```
3. Set `CORS_ORIGINS` on the FolioChat server to your portfolio's domain so the browser allows cross-origin requests:
   ```bash
   export CORS_ORIGINS=https://yourportfolio.com
   foliochat serve --username <your-github-username> --port 8000
   ```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Widget shows "Could not connect to FolioChat server" | Ensure `foliochat serve` is running and `FOLIOCHAT_URL` is correct |
| CORS errors in browser console | Set `CORS_ORIGINS=https://yourdomain.com` on the FolioChat server |
| Blank page / script errors | Check the browser DevTools console; ensure CDN scripts loaded successfully |
| Stale project data | Run `foliochat build --username <you> --refresh` to rebuild the database |
| Rate limit errors during build | Add `--token ghp_...` to use an authenticated GitHub API token |
