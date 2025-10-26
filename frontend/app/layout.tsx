import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ISPL - 보험약관 AI 시스템",
  description: "보험약관 기반 Agentic AI 시스템",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko">
      <body className="antialiased">
        {children}
      </body>
    </html>
  );
}

