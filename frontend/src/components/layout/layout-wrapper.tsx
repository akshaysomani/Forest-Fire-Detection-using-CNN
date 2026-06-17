"use client";

import React, { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useAuthStore } from "@/store/auth-store";
import { useUiStore } from "@/store/ui-store";
import Sidebar from "./sidebar";
import Navbar from "./navbar";

export default function LayoutWrapper({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { accessToken, user } = useAuthStore();
  const { sidebarOpen, theme, setTheme } = useUiStore();
  const [hasHydrated, setHasHydrated] = React.useState(false);

  const isAuthPage = pathname?.startsWith("/auth");
  const isHomePage = pathname === "/";
  const isUsersPage = pathname === "/users";
  const isAdminPage = pathname?.startsWith("/admin");
  const isSuperAdmin = user?.roles?.some((r) => r.name.toLowerCase() === "super admin");

  useEffect(() => {
    setHasHydrated(true);
  }, []);

  useEffect(() => {
    // Sync store theme state with the class name applied on documentElement on mount
    const isDark = document.documentElement.classList.contains("dark");
    setTheme(isDark ? "dark" : "light");
  }, [setTheme]);

  useEffect(() => {
    // Sync class list with store changes
    const root = window.document.documentElement;
    if (theme === "dark") {
      root.classList.add("dark");
      root.classList.remove("light");
    } else {
      root.classList.add("light");
      root.classList.remove("dark");
    }
  }, [theme]);

  useEffect(() => {
    if (!hasHydrated) return;

    // If not authenticated and not on a public page, redirect to login
    if (!accessToken && !isAuthPage && !isHomePage && !isUsersPage) {
      router.push("/auth/login");
    }
    // If authenticated and tries to access admin page without permission, redirect to dashboard
    if (accessToken && isAdminPage && !isSuperAdmin) {
      router.push("/dashboard");
    }
  }, [hasHydrated, accessToken, isAuthPage, isHomePage, isUsersPage, isAdminPage, isSuperAdmin, router]);

  if (isAuthPage || isHomePage || isUsersPage) {
    return <div className="min-h-screen bg-neutral-950 flex flex-col justify-center">{children}</div>;
  }

  // If we don't have token and we are on a private page, show blank/loader while redirecting
  if (!hasHydrated || !accessToken) {
    return (
      <div className="min-h-screen bg-neutral-950 flex items-center justify-center">
        <div className="flex flex-col items-center space-y-4">
          <div className="w-10 h-10 border-4 border-emerald-500/20 border-t-emerald-500 rounded-full animate-spin" />
          <p className="text-sm font-semibold text-neutral-400">Authenticating Access...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-neutral-950 flex flex-col">
      <Sidebar />
      <div className={`flex flex-col min-h-screen transition-all duration-300 ${sidebarOpen ? "pl-64" : "pl-0"}`}>
        <Navbar />
        <main className="flex-1 p-6 md:p-8 bg-neutral-950 max-w-[1600px] w-full mx-auto overflow-y-auto">
          {children}
        </main>
      </div>
    </div>
  );
}
