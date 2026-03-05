import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "AI Traffic Command Center",
  description: "Dynamic AI Traffic Flow Optimizer MVP",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
