"use client";

import { useRouter } from "next/navigation";
import { useAuthStore } from "@/store/auth-store";
import { useUiStore } from "@/store/ui-store";
import { Menu, LogOut, ShieldCheck, Moon } from "lucide-react";

export default function Navbar() {
  const router = useRouter();
  const { clearAuth, refreshToken } = useAuthStore();
  const { toggleSidebar, addToast } = useUiStore();

  const handleLogout = async () => {
    try {
      if (refreshToken) {
        const { authService } = await import("@/services/auth");
        await authService.logout(refreshToken).catch(() => {});
      }
    } catch (e) {
    } finally {
      clearAuth();
      addToast({
        type: "success",
        title: "Session Terminated",
        message: "You have been successfully logged out.",
      });
      router.push("/auth/login");
    }
  };

  return (
    <header className="h-16 border-b border-white/5 bg-neutral-900/40 backdrop-blur-md sticky top-0 z-30 flex items-center justify-between px-6">
      <div className="flex items-center space-x-4">
        <button
          onClick={toggleSidebar}
          className="p-1.5 rounded-lg hover:bg-white/5 text-neutral-400 hover:text-white"
        >
          <Menu className="w-5 h-5" />
        </button>
        <div className="flex items-center space-x-2.5">
          <span className="text-xs bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2 py-0.5 rounded-full font-semibold flex items-center space-x-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-ping" />
            <span>LIVE INTERFACE</span>
          </span>
        </div>
      </div>

      <div className="flex items-center space-x-4">
        {/* Connection health indicator */}
        <div className="flex items-center space-x-2 text-neutral-400 text-xs font-medium border border-white/5 bg-neutral-950/20 rounded-lg px-3 py-1.5">
          <ShieldCheck className="w-3.5 h-3.5 text-emerald-500" />
          <span>DevSecOps Secure</span>
        </div>

        {/* Theme indicator */}
        <button className="p-2 rounded-lg hover:bg-white/5 text-neutral-400 hover:text-white">
          <Moon className="w-4 h-4" />
        </button>

        {/* Logout */}
        <button
          onClick={handleLogout}
          className="p-2 rounded-lg hover:bg-rose-500/10 text-neutral-400 hover:text-rose-400 border border-transparent hover:border-rose-500/20 transition-all flex items-center space-x-1.5"
          title="Sign Out"
        >
          <LogOut className="w-4 h-4" />
          <span className="text-xs font-semibold uppercase tracking-wider hidden md:inline-block">
            Logout
          </span>
        </button>
      </div>
    </header>
  );
}
