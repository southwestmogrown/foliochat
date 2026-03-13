// app/layout.tsx
//
// Drop-in Next.js App Router layout that adds the FolioChat widget to every
// page of your portfolio.
//
// Prerequisites
// ─────────────
// 1. Install the widget:
//      npm install foliochat
// 2. Copy .env.example → .env.local and set NEXT_PUBLIC_FOLIOCHAT_URL.
// 3. Run the FolioChat server:
//      foliochat build --username <your-github-username>
//      foliochat serve --username <your-github-username>

import type { Metadata } from "next";
import { FolioChat } from "foliochat";

export const metadata: Metadata = {
  title: "My Portfolio",
  description: "Welcome to my portfolio",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const foliochatUrl = process.env.NEXT_PUBLIC_FOLIOCHAT_URL ?? "http://localhost:8000";

  return (
    <html lang="en">
      <body>
        {children}

        {/* FolioChat widget — floats in the bottom-right corner of every page */}
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
