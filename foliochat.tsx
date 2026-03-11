import { useState, useEffect, useRef } from "react";

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

// ── Default styles ────────────────────────────────────────────────────────────

const THEMES = {
  dark: {
    bg: "#0f1117",
    surface: "#1a1f2e",
    border: "#2a3347",
    text: "#e2e8f0",
    muted: "#6b7280",
    userBubble: "#1e3a5f",
    assistantBubble: "#1a1f2e",
  },
  light: {
    bg: "#ffffff",
    surface: "#f8fafc",
    border: "#e2e8f0",
    text: "#1a202c",
    muted: "#718096",
    userBubble: "#ebf8ff",
    assistantBubble: "#f7fafc",
  },
};

// ── FolioChat component ───────────────────────────────────────────────────────

export function FolioChat({
  endpoint,
  theme = "dark",
  position = "bottom-right",
  accentColor = "#f97316",
  greeting,
}: FolioChatProps) {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [context, setContext] = useState<PortfolioContext | null>(null);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  const resolvedTheme = theme === "auto"
    ? (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light")
    : theme;
  const colors = THEMES[resolvedTheme];

  // Fetch context on mount
  useEffect(() => {
    fetch(`${endpoint}/context`)
      .then((r) => r.json())
      .then((data) => {
        setContext(data);
        const openingGreeting = greeting || data.greeting || "Hi! Ask me about this developer's projects.";
        setMessages([{ role: "assistant", content: openingGreeting }]);
      })
      .catch(() => {
        setError("Could not connect to FolioChat server.");
      });
  }, [endpoint, greeting]);

  // Scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

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
          content: "Sorry, something went wrong. Please try again.",
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
            width: "360px",
            height: "500px",
            background: colors.bg,
            border: `1px solid ${colors.border}`,
            borderRadius: "16px",
            display: "flex",
            flexDirection: "column",
            boxShadow: "0 20px 60px rgba(0,0,0,0.3)",
            marginBottom: "12px",
            overflow: "hidden",
          }}
        >
          {/* Header */}
          <div
            style={{
              background: colors.surface,
              borderBottom: `1px solid ${colors.border}`,
              padding: "14px 16px",
              display: "flex",
              alignItems: "center",
              gap: "10px",
            }}
          >
            <div
              style={{
                width: "32px",
                height: "32px",
                borderRadius: "8px",
                background: accentColor,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: "16px",
              }}
            >
              💬
            </div>
            <div>
              <div style={{ color: colors.text, fontWeight: "600", fontSize: "14px" }}>
                {context?.username ? `Ask about ${context.username}` : "Portfolio Chat"}
              </div>
              <div style={{ color: colors.muted, fontSize: "11px" }}>
                {context?.repo_count
                  ? `${context.repo_count} projects in knowledge base`
                  : "Loading..."}
              </div>
            </div>
            <button
              onClick={() => setOpen(false)}
              style={{
                marginLeft: "auto",
                background: "none",
                border: "none",
                color: colors.muted,
                cursor: "pointer",
                fontSize: "18px",
                lineHeight: 1,
                padding: "0",
              }}
            >
              ×
            </button>
          </div>

          {/* Messages */}
          <div
            style={{
              flex: 1,
              overflowY: "auto",
              padding: "16px",
              display: "flex",
              flexDirection: "column",
              gap: "12px",
            }}
          >
            {error && (
              <div style={{ color: "#ef4444", fontSize: "13px", textAlign: "center" }}>
                {error}
              </div>
            )}

            {messages.map((msg, i) => (
              <div
                key={i}
                style={{
                  display: "flex",
                  justifyContent: msg.role === "user" ? "flex-end" : "flex-start",
                }}
              >
                <div
                  style={{
                    maxWidth: "80%",
                    background: msg.role === "user" ? colors.userBubble : colors.assistantBubble,
                    border: `1px solid ${colors.border}`,
                    borderRadius: msg.role === "user"
                      ? "16px 16px 4px 16px"
                      : "16px 16px 16px 4px",
                    padding: "10px 14px",
                    fontSize: "13px",
                    color: colors.text,
                    lineHeight: "1.5",
                  }}
                >
                  {msg.content}
                  {msg.sources && msg.sources.length > 0 && (
                    <div
                      style={{
                        marginTop: "6px",
                        paddingTop: "6px",
                        borderTop: `1px solid ${colors.border}`,
                        fontSize: "10px",
                        color: colors.muted,
                      }}
                    >
                      Sources: {msg.sources.join(", ")}
                    </div>
                  )}
                </div>
              </div>
            ))}

            {loading && (
              <div style={{ display: "flex", justifyContent: "flex-start" }}>
                <div
                  style={{
                    background: colors.assistantBubble,
                    border: `1px solid ${colors.border}`,
                    borderRadius: "16px 16px 16px 4px",
                    padding: "10px 16px",
                    color: colors.muted,
                    fontSize: "20px",
                    letterSpacing: "2px",
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
              padding: "12px",
              display: "flex",
              gap: "8px",
              background: colors.surface,
            }}
          >
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKey}
              placeholder="Ask about projects, skills..."
              disabled={loading || !!error}
              style={{
                flex: 1,
                background: colors.bg,
                border: `1px solid ${colors.border}`,
                borderRadius: "8px",
                padding: "8px 12px",
                color: colors.text,
                fontSize: "13px",
                outline: "none",
              }}
            />
            <button
              onClick={sendMessage}
              disabled={loading || !input.trim() || !!error}
              style={{
                background: input.trim() && !loading ? accentColor : colors.border,
                color: input.trim() && !loading ? "#000" : colors.muted,
                border: "none",
                borderRadius: "8px",
                padding: "8px 14px",
                cursor: input.trim() && !loading ? "pointer" : "default",
                fontSize: "13px",
                fontWeight: "600",
                transition: "all 0.2s",
              }}
            >
              ↑
            </button>
          </div>
        </div>
      )}

      {/* Toggle button */}
      <div style={{ display: "flex", justifyContent: position === "bottom-right" ? "flex-end" : "flex-start" }}>
        <button
          onClick={() => setOpen((v) => !v)}
          style={{
            width: "56px",
            height: "56px",
            borderRadius: "50%",
            background: accentColor,
            border: "none",
            cursor: "pointer",
            fontSize: "22px",
            boxShadow: "0 4px 20px rgba(0,0,0,0.3)",
            transition: "transform 0.2s",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
          onMouseEnter={(e) => (e.currentTarget.style.transform = "scale(1.08)")}
          onMouseLeave={(e) => (e.currentTarget.style.transform = "scale(1)")}
        >
          {open ? "×" : "💬"}
        </button>
      </div>
    </div>
  );
}

export default FolioChat;