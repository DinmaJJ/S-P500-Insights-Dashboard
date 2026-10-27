import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "S&P 500 Insight",
  description: "Daily automated analysis of the S&P 500",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  );
}
