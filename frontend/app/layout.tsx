import type { Metadata } from "next";
import { Geist } from "next/font/google";
import "./globals.css";
import { ThemeProvider } from "@/components/theme-provider";
import { Toaster } from 'sonner';

const geist = Geist({
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "AI Language Tools",
  description: "Modern language processing tools powered by AI",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${geist.className} min-h-screen bg-background`} style={{ fontFamily: `'Geist', 'Times New Roman', serif` }}>
        <ThemeProvider
          attribute="class"
          defaultTheme="system"
          enableSystem
          disableTransitionOnChange
        >
          <main className="min-h-[calc(100vh-4rem)]">{children}</main>
        </ThemeProvider>
        <Toaster />
      </body>
    </html>
  );
}
