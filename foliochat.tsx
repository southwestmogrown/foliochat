import { useState, useEffect, useRef, useCallback } from "react";

// ── Types ─────────────────────────────────────────────────────────────────────

interface Message {
  role: "user" | "assistant";
  content: string;
  sources?: string[];
}

interface FolioChatProps {
  endpoint: string;
  theme?: "dark" | "light" | "auto";
  position?: "bottom-right" | "bottom-left";
  accentColor?: string;
  greeting?: string;
}

interface PortfolioContext {
  username: string;
  repo_count: number;
  greeting: string;
}

// ── Design tokens ─────────────────────────────────────────────────────────────

const THEMES = {
  dark: {
    bg: "#0A0A0A",
    surface: "#111111",
    border: "#262626",
    text: "#EDEDED",
    muted: "#5A5A5A",
    userBubble: "#1A1A1A",
    assistantBubble: "#0F0F0F",
    accentGlow: "rgba(242, 100, 25, 0.12)",
  },
  light: {
    bg: "#F5F5F5",
    surface: "#FFFFFF",
    border: "#D4D4D4",
    text: "#111111",
    muted: "#737373",
    userBubble: "#E8E8E8",
    assistantBubble: "#F0F0F0",
    accentGlow: "rgba(242, 100, 25, 0.08)",
  },
};

// ── FolioChat component ───────────────────────────────────────────────────────

export function FolioChat({
  endpoint,
  theme = "dark",
  position = "bottom-right",
  accentColor = "#F26419",
  greeting,
}: FolioChatProps) {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [context, setContext] = useState<PortfolioContext | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [systemDark, setSystemDark] = useState(
    typeof window !== "undefined"
      ? window.matchMedia("(prefers-color-scheme: dark)").matches
      : false
  );
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (theme !== "auto") return;
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const handler = (e: MediaQueryListEvent) => setSystemDark(e.matches);
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, [theme]);

  const resolvedTheme =
    theme === "auto" ? (systemDark ? "dark" : "light") : theme;
  const colors = THEMES[resolvedTheme];

  useEffect(() => {
    fetch(`${endpoint}/context`)
      .then((r) => r.json())
      .then((data) => {
        setContext(data);
        const openingGreeting = greeting || data.greeting || "ENCRYPTED_COMMS ONLINE.";
        setMessages([{ role: "assistant", content: openingGreeting }]);
      })
      .catch(() => {
        setError("CONNECTION REFUSED. CHECK ENDPOINT.");
      });
  }, [endpoint, greeting]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  useEffect(() => {
    if (open) {
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [open]);

  const handleWindowKey = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === "Escape" && open) setOpen(false);
    },
    [open]
  );
  useEffect(() => {
    window.addEventListener("keydown", handleWindowKey);
    return () => window.removeEventListener("keydown", handleWindowKey);
  }, [handleWindowKey]);

  const sendMessage = async () => {
    if (!input.trim() || loading) return;

    const userMessage = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: userMessage }]);
    setLoading(true);

    try {
      const response = await fetch(`${endpoint}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: userMessage,
          history: messages.map(({ role, content }) => ({ role, content })),
        }),
      });

      if (!response.ok) throw new Error("Chat request failed");

      const data = await response.json();
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: data.reply, sources: data.sources },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "TRANSMISSION ERROR. RETRY.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const positionStyle = position === "bottom-right"
    ? { right: "24px" }
    : { left: "24px" };

  return (
    <div style={{ position: "fixed", bottom: "24px", zIndex: 9999, ...positionStyle }}>
      {/* Chat window */}
      {open && (
        <div
          style={{
            width: "380px",
            height: "520px",
            background: colors.bg,
            border: `1px solid ${colors.border}`,
            borderRadius: "0",
            display: "flex",
            flexDirection: "column",
            boxShadow: `0 0 0 1px ${colors.border}, 0 24px 64px rgba(0,0,0,0.6), 0 0 32px ${colors.accentGlow}`,
            marginBottom: "8px",
            overflow: "hidden",
            fontFamily: "'JetBrains Mono', 'Fira Code', 'Courier New', monospace",
          }}
        >
          {/* Header */}
          <div
            style={{
              background: colors.surface,
              borderBottom: `1px solid ${colors.border}`,
              padding: "0",
            }}
          >
            {/* Top bar — system label */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "6px 12px",
                borderBottom: `1px solid ${colors.border}`,
                fontSize: "9px",
                letterSpacing: "0.15em",
                color: colors.muted,
              }}
            >
              <span>FOLIOCHAT // ENCRYPTED_COMMS</span>
              <span style={{ color: accentColor }}>● STATUS: OPTIMAL</span>
            </div>

            {/* Main header row */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "10px 12px",
              }}
            >
              <div>
                <div
                  style={{
                    color: colors.text,
                    fontWeight: "700",
                    fontSize: "11px",
                    letterSpacing: "0.12em",
                  }}
                >
                  {context?.username
                    ? `${context.username.toUpperCase()}.PORTFOLIO`
                    : "PORTFOLIO.COMMS"}
                </div>
                <div
                  style={{
                    color: colors.muted,
                    fontSize: "9px",
                    letterSpacing: "0.1em",
                    marginTop: "2px",
                  }}
                >
                  {context?.repo_count
                    ? `${context.repo_count} REPOS INDEXED`
                    : "INDEXING..."}
                </div>
              </div>
              <button
                onClick={() => setOpen(false)}
                aria-label="Close chat"
                style={{
                  background: "none",
                  border: `1px solid ${colors.border}`,
                  color: colors.muted,
                  cursor: "pointer",
                  fontSize: "11px",
                  letterSpacing: "0.05em",
                  padding: "3px 8px",
                  borderRadius: "0",
                  fontFamily: "inherit",
                  transition: "color 0.1s, border-color 0.1s",
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.color = accentColor;
                  e.currentTarget.style.borderColor = accentColor;
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.color = colors.muted;
                  e.currentTarget.style.borderColor = colors.border;
                }}
              >
                [X]
              </button>
            </div>
          </div>

          {/* Messages */}
          <div
            role="log"
            aria-live="polite"
            aria-label="Chat messages"
            style={{
              flex: 1,
              overflowY: "auto",
              padding: "16px 12px",
              display: "flex",
              flexDirection: "column",
              gap: "10px",
              scrollbarWidth: "thin",
              scrollbarColor: `${colors.border} transparent`,
            }}
          >
            {error && (
              <div
                role="alert"
                style={{
                  color: accentColor,
                  fontSize: "10px",
                  letterSpacing: "0.1em",
                  textAlign: "center",
                  border: `1px solid ${accentColor}`,
                  padding: "6px 10px",
                }}
              >
                {error}
              </div>
            )}

            {messages.map((msg, i) => (
              <div
                key={i}
                style={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: msg.role === "user" ? "flex-end" : "flex-start",
                }}
              >
                <div
                  style={{
                    fontSize: "9px",
                    letterSpacing: "0.12em",
                    color: msg.role === "user" ? accentColor : colors.muted,
                    marginBottom: "3px",
                    paddingLeft: msg.role === "user" ? "0" : "2px",
                    paddingRight: msg.role === "user" ? "2px" : "0",
                  }}
                >
                  {msg.role === "user" ? "> INPUT" : "// RESPONSE"}
                </div>
                <div
                  style={{
                    maxWidth: "88%",
                    background: msg.role === "user" ? colors.userBubble : colors.assistantBubble,
                    border: `1px solid ${msg.role === "user" ? accentColor + "33" : colors.border}`,
                    borderRadius: "0",
                    padding: "8px 12px",
                    fontSize: "12px",
                    color: colors.text,
                    lineHeight: "1.6",
                    fontFamily: msg.role === "user"
                      ? "inherit"
                      : "'Inter', 'Geist Sans', system-ui, sans-serif",
                  }}
                >
                  {msg.content}
                  {msg.sources && msg.sources.length > 0 && (
                    <div
                      style={{
                        marginTop: "8px",
                        paddingTop: "6px",
                        borderTop: `1px solid ${colors.border}`,
                        fontSize: "9px",
                        letterSpacing: "0.08em",
                        color: colors.muted,
                        fontFamily: "inherit",
                      }}
                    >
                      {"// SOURCES: "}
                      {msg.sources.map((repo, idx) => (
                        <span key={repo}>
                          {idx > 0 && " · "}
                          {context?.username ? (
                            <a
                              href={`https://github.com/${context.username}/${repo}`}
                              target="_blank"
                              rel="noopener noreferrer"
                              style={{
                                color: accentColor,
                                textDecoration: "none",
                                letterSpacing: "0.05em",
                              }}
                              onMouseEnter={(e) =>
                                (e.currentTarget.style.textDecoration = "underline")
                              }
                              onMouseLeave={(e) =>
                                (e.currentTarget.style.textDecoration = "none")
                              }
                            >
                              {repo}
                            </a>
                          ) : (
                            repo
                          )}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}

            {loading && (
              <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-start" }}>
                <div
                  style={{
                    fontSize: "9px",
                    letterSpacing: "0.12em",
                    color: colors.muted,
                    marginBottom: "3px",
                    paddingLeft: "2px",
                  }}
                >
                  // RESPONSE
                </div>
                <div
                  style={{
                    background: colors.assistantBubble,
                    border: `1px solid ${colors.border}`,
                    borderRadius: "0",
                    padding: "8px 16px",
                    color: accentColor,
                    fontSize: "14px",
                    letterSpacing: "0.3em",
                  }}
                >
                  ···
                </div>
              </div>
            )}

            <div ref={bottomRef} />
          </div>

          {/* Input */}
          <div
            style={{
              borderTop: `1px solid ${colors.border}`,
              padding: "10px 12px",
              display: "flex",
              gap: "8px",
              background: colors.surface,
            }}
          >
            <div
              style={{
                display: "flex",
                alignItems: "center",
                flex: 1,
                border: `1px solid ${colors.border}`,
                background: colors.bg,
              }}
            >
              <span
                style={{
                  color: accentColor,
                  fontSize: "11px",
                  padding: "0 8px",
                  letterSpacing: "0.05em",
                  userSelect: "none",
                }}
              >
                &gt;_
              </span>
              <input
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKey}
                placeholder="ENTER QUERY..."
                disabled={loading || !!error}
                aria-label="Type your message"
                style={{
                  flex: 1,
                  background: "transparent",
                  border: "none",
                  color: colors.text,
                  fontSize: "11px",
                  letterSpacing: "0.05em",
                  outline: "none",
                  padding: "8px 8px 8px 0",
                  fontFamily: "'JetBrains Mono', 'Fira Code', 'Courier New', monospace",
                }}
              />
            </div>
            <button
              onClick={sendMessage}
              disabled={loading || !input.trim() || !!error}
              aria-label="Send message"
              style={{
                background: input.trim() && !loading ? accentColor : colors.surface,
                color: input.trim() && !loading ? "#000000" : colors.muted,
                border: `1px solid ${input.trim() && !loading ? accentColor : colors.border}`,
                borderRadius: "0",
                padding: "8px 12px",
                cursor: input.trim() && !loading ? "pointer" : "default",
                fontSize: "10px",
                fontWeight: "700",
                letterSpacing: "0.1em",
                fontFamily: "'JetBrains Mono', 'Fira Code', 'Courier New', monospace",
                transition: "all 0.1s",
              }}
            >
              SEND
            </button>
          </div>
        </div>
      )}

      {/* Toggle button */}
      <div
        style={{
          display: "flex",
          justifyContent: position === "bottom-right" ? "flex-end" : "flex-start",
        }}
      >
        <button
          onClick={() => setOpen((v) => !v)}
          aria-label={open ? "Close portfolio chat" : "Open portfolio chat"}
          aria-expanded={open}
          style={{
            background: open ? colors.surface : accentColor,
            border: `1px solid ${open ? colors.border : accentColor}`,
            borderRadius: "0",
            cursor: "pointer",
            padding: "10px 16px",
            display: "flex",
            alignItems: "center",
            gap: "8px",
            boxShadow: open
              ? `0 0 0 1px ${colors.border}`
              : `0 0 24px ${accentColor}44, 0 4px 16px rgba(0,0,0,0.4)`,
            transition: "all 0.1s",
            fontFamily: "'JetBrains Mono', 'Fira Code', 'Courier New', monospace",
          }}
          onMouseEnter={(e) => {
            if (!open) e.currentTarget.style.boxShadow = `0 0 32px ${accentColor}66, 0 4px 16px rgba(0,0,0,0.4)`;
          }}
          onMouseLeave={(e) => {
            if (!open) e.currentTarget.style.boxShadow = `0 0 24px ${accentColor}44, 0 4px 16px rgba(0,0,0,0.4)`;
          }}
        >
          <span
            style={{
              fontSize: "9px",
              letterSpacing: "0.15em",
              color: open ? colors.muted : "#000000",
              fontWeight: "700",
            }}
          >
            {open ? "[CLOSE]" : "ENCRYPTED_COMMS"}
          </span>
          <span
            style={{
              width: "6px",
              height: "6px",
              background: open ? colors.muted : "#000000",
              borderRadius: "50%",
              flexShrink: 0,
            }}
          />
        </button>
      </div>
    </div>
  );
}

export default FolioChat;
