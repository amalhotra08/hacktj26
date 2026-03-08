import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Citywide Risk Engine",
  description: "High-intensity deck.gl visualization for urban intelligence.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  );
}
