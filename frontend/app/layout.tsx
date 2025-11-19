import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Header from "@/components/Header";
import { ApiProvider } from "@/lib/api-context";
import { AuthProvider } from "@/components/AuthProvider";
import "@/lib/auth"; // Initialize Amplify
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "DPW Project Management",
  description: "AI-Powered Project Management for Public Works",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        <AuthProvider>
          <ApiProvider>
            <header className="sticky top-0">
              <Header />
            </header>
            {children}
          </ApiProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
