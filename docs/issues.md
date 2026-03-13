# FolioChat — Portfolio Integration Issues

These issues cover wiring the FolioChat React widget into the portfolio site and deploying
the API to Railway. Work them in order — each issue depends on the previous one.

---

## Issue 1: Deploy FolioChat API to Railway

**Labels:** `infrastructure`, `deployment`
**Depends on:** nothing — do this first

### Context
The FolioChat FastAPI server currently runs locally at `http://127.0.0.1:8000`. It needs
to be publicly accessible on Railway before the portfolio widget can point at it.

### Acceptance Criteria
- [ ] FolioChat repo is connected to a Railway project
- [ ] The following environment variables are set in Railway:
  - `ANTHROPIC_API_KEY`
  - `GITHUB_TOKEN`
  - `CORS_ORIGINS` set to the portfolio domain (e.g. `https://southwestmogrown.github.io`)
- [ ] A `Procfile` or `railway.toml` exists that runs:
  `foliochat serve --username southwestmogrown --llm anthropic`
- [ ] `GET https://<railway-domain>/health` returns `200 OK`
- [ ] `POST https://<railway-domain>/chat` with body `{"message": "What projects have you built?"}` returns a valid reply
- [ ] Railway domain is noted and ready for use in Issue 2

### Notes
- The build step (`foliochat build`) must run before or at deploy time to populate ChromaDB.
  Consider whether to commit the built `~/.foliochat/southwestmogrown/` directory or run
  build as part of the Railway start command.
- Do not hardcode the Railway URL anywhere — it goes in an environment variable in the
  portfolio repo (`VITE_FOLIOCHAT_API_URL` or `REACT_APP_FOLIOCHAT_API_URL`).

---

## Issue 2: Bundle FolioChat widget for portfolio consumption

**Labels:** `frontend`, `widget`
**Depends on:** Issue 1 (need the Railway URL)

### Context
`foliochat.tsx` is a self-contained React/TypeScript floating widget that lives in the
FolioChat repo. The portfolio site needs to consume it. Since the portfolio has no build
step in the FolioChat repo, the widget needs to be bundled and either published or copied.

### Acceptance Criteria
- [ ] A Vite or tsup build config is added to the FolioChat repo that bundles
  `foliochat.tsx` into a single `foliochat.umd.js` (or ESM equivalent)
- [ ] The bundle exposes a `FolioChat` React component as its default export
- [ ] Bundle is output to a `dist/` directory
- [ ] `dist/` is committed or published so the portfolio can import it
- [ ] The widget accepts these props:
  - `apiUrl: string` — points to the Railway API
  - `accentColor?: string` — defaults to `#f97316`
  - `theme?: "dark" | "light" | "auto"` — defaults to `"auto"`
  - `position?: "bottom-right" | "bottom-left"` — defaults to `"bottom-right"`
  - `greeting?: string` — optional override, falls back to `/context` endpoint

### Notes
- Do not split CSS into a separate file — keep styles inline or in the JS bundle so the
  portfolio only needs one import.
- The widget must not conflict with the portfolio's existing Tailwind or CSS setup.

---

## Issue 3: Implement streaming responses in the widget

**Labels:** `frontend`, `streaming`
**Depends on:** Issue 2

### Context
The `/chat` endpoint supports streaming. The widget should consume the stream and render
tokens progressively rather than waiting for the full response, which improves perceived
performance significantly with a local or remote LLM.

### Acceptance Criteria
- [ ] `POST /chat` is called with `Accept: text/event-stream` or equivalent streaming header
- [ ] The widget renders tokens as they arrive using `ReadableStream` / `fetch` streaming
- [ ] A blinking cursor or typing indicator is shown while the stream is active
- [ ] The send button is disabled while a response is streaming
- [ ] If the stream errors mid-response, a graceful fallback message is shown
- [ ] Streaming works correctly in both Chrome and Firefox

### Notes
- Use the native `fetch` API with `response.body.getReader()` — do not add a streaming
  library dependency.
- Test with both Ollama locally and Anthropic on Railway before closing this issue.

---

## Issue 4: Add dark/light theme auto-detection to the widget

**Labels:** `frontend`, `theming`
**Depends on:** Issue 2

### Context
The widget should match the portfolio's theme automatically using `prefers-color-scheme`,
and also respect an explicit `theme` prop override.

### Acceptance Criteria
- [ ] When `theme="auto"` (default), widget reads `window.matchMedia("(prefers-color-scheme: dark)")`
- [ ] Widget re-renders correctly if the OS theme changes while the page is open
  (use a `matchMedia` event listener)
- [ ] When `theme="dark"` or `theme="light"` is passed explicitly, it overrides system preference
- [ ] Dark theme: background `#0a0d14`, text `#f1f5f9`, border `#1e293b`
- [ ] Light theme: background `#ffffff`, text `#0f172a`, border `#e2e8f0`
- [ ] Accent color `#f97316` is used for the toggle button, send button, and user message bubbles in both themes

### Notes
- Keep theme tokens as CSS custom properties on the widget's root element so they are
  easy to override from the outside if needed.

---

## Issue 5: Make the widget mobile responsive

**Labels:** `frontend`, `responsive`
**Depends on:** Issue 2

### Context
The floating chat widget needs to work on mobile viewports without covering the entire
screen or breaking layout.

### Acceptance Criteria
- [ ] On viewports >= 480px: widget renders as a floating panel, 380px wide, anchored
  bottom-right (or bottom-left per `position` prop), with a toggle button
- [ ] On viewports < 480px: widget renders as a full-width bottom sheet, 100vw wide,
  max 60vh tall, with a drag handle or close button
- [ ] The message input and send button are always accessible above the mobile keyboard
  (use `env(safe-area-inset-bottom)` for iOS)
- [ ] The toggle button is always visible and tappable (min 44x44px tap target)
- [ ] No horizontal scroll is introduced on any viewport size
- [ ] Tested on Chrome mobile emulator at 375px and 414px widths

---

## Issue 6: Integrate FolioChat widget into portfolio page

**Labels:** `frontend`, `integration`
**Depends on:** Issues 1, 2, 3, 4, 5

### Context
All pieces are ready — API is live, widget is bundled, streaming and theming work. This
issue wires everything together in the actual portfolio site.

### Acceptance Criteria
- [ ] `FolioChat` component is imported into the portfolio's root `App.tsx` (or equivalent)
- [ ] `apiUrl` is read from `import.meta.env.VITE_FOLIOCHAT_API_URL` (Vite) or
  `process.env.REACT_APP_FOLIOCHAT_API_URL` (CRA)
- [ ] `.env.example` is updated with `VITE_FOLIOCHAT_API_URL=https://your-railway-domain.railway.app`
- [ ] Widget renders correctly on the deployed portfolio at all breakpoints
- [ ] Widget does not interfere with any existing portfolio UI or z-index stacking
- [ ] `GET /context` greeting loads correctly on widget open
- [ ] A test conversation is manually run on the live portfolio:
  - "What projects have you built?"
  - "Do you know PostgreSQL?"
  - "Tell me about FolioChat"
  - All three return accurate, coherent answers sourced from actual repo data
- [ ] DEVLOG.md is updated with a note marking FolioChat as publicly live

### Notes
- This is the milestone issue. When this closes, FolioChat is live and visible.
- Write the Dev.to launch article within one week of this issue closing while it's fresh.