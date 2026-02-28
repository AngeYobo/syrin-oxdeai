import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Syrin Playground",
  description: "Web playground for testing Syrin agents",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="layout-main">{children}</div>
        <footer className="footer">
          <a href="https://syrin.ai" target="_blank" rel="noopener noreferrer">
            Powered by Syrin
          </a>
        </footer>
      </body>
    </html>
  );
}
