import React from "react";
import QueryProvider from "@/providers/query-provider";
import ToastContainer from "@/components/layout/toast-container";
import LayoutWrapper from "@/components/layout/layout-wrapper";
import "./globals.css";

export const metadata = {
  title: "IgnisAI - Wildfire Detection Platform",
  description: "AI-Powered Wildfire Prevention, Monitoring and Response System",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap" rel="stylesheet" />
        {/* Leaflet CSS styling */}
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=" crossOrigin="" />
      </head>
      <body className="bg-neutral-950 text-neutral-100 font-sans selection:bg-emerald-500/30 selection:text-emerald-400">
        <QueryProvider>
          <LayoutWrapper>
            {children}
          </LayoutWrapper>
          <ToastContainer />
        </QueryProvider>
      </body>
    </html>
  );
}
