import type { Metadata } from "next";
import "./globals.css";
import { Fraunces, Plus_Jakarta_Sans, IBM_Plex_Mono } from "next/font/google";
import { cn } from "@/lib/utils";
import { AppProviders } from "@/components/providers";

const display = Fraunces({
  subsets: ["latin"],
  variable: "--font-display",
});

const sans = Plus_Jakarta_Sans({
  subsets: ["latin"],
  variable: "--font-sans",
});

const mono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-mono",
});

export const metadata: Metadata = {
  title: "Finehelper",
  description: "Dataset, train, eval, deploy — one workbench for fine-tunes.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={cn(display.variable, sans.variable, mono.variable)}>
      <body className="min-h-screen font-sans antialiased text-wine-800">
        <AppProviders>{children}</AppProviders>
      </body>
    </html>
  );
}
