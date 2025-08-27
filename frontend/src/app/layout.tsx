import type { Metadata } from "next";
import "./globals.css";
import { QueryProvider } from "../lib/query-provider";

export const metadata: Metadata = {
  title: "PaperTrail - AI Research Assistant",
  description: "Multi-agent AI research platform for synthesizing, critiquing, and connecting ideas",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="antialiased">
        <QueryProvider>
          {children}
        </QueryProvider>
      </body>
    </html>
  );
}
