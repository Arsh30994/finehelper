import type { Metadata } from "next";
import "./globals.css";
import { Manrope, Sora, IBM_Plex_Mono } from "next/font/google";
import { cn } from "@/lib/utils";
import { AppProviders } from "@/components/providers";

const display = Sora({
  subsets: ["latin"],
  variable: "--font-display",
});

const sans = Manrope({
  subsets: ["latin"],
  variable: "--font-sans",
});

const mono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-mono",
});

export const metadata: Metadata = {
  title: "TrustMesh",
  description: "Thin-file trust scoring from synthetic UPI and bill signals — not CIBIL.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      className={cn(display.variable, sans.variable, mono.variable)}
      suppressHydrationWarning
    >
      <body className="min-h-screen bg-mist-50 font-sans text-ink-800 antialiased" suppressHydrationWarning>
        <AppProviders>{children}</AppProviders>
      </body>
    </html>
  );
}
