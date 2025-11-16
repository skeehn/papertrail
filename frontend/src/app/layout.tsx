import type { Metadata } from "next";
import "./globals.css";
import { QueryProvider } from "../lib/query-provider";
import { ThemeProvider } from "@/components/providers/theme-provider";
import { Toaster } from "@/components/ui/sonner";
import { GlobalCommandPalette } from "@/components/search/global-command-palette";

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
    <html lang="en" suppressHydrationWarning>
      <body className="antialiased">
        <ThemeProvider
          attribute="class"
          defaultTheme="light"
          enableSystem
          disableTransitionOnChange
        >
          <QueryProvider>
            {children}
            <Toaster />
            <GlobalCommandPalette />
          </QueryProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
