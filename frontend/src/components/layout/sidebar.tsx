"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuthStore } from "@/store/auth-store";
import { useUiStore } from "@/store/ui-store";
import {
  LayoutDashboard,
  Database,
  BrainCircuit,
  Map,
  ShieldAlert,
  BarChart3,
  Settings,
  X,
  Flame,
} from "lucide-react";

export default function Sidebar() {
  const pathname = usePathname();
  const { user } = useAuthStore();
  const { sidebarOpen, setSidebar } = useUiStore();

  const isLinkActive = (path: string) => pathname?.startsWith(path);

  const menuItems = [
    { name: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
    { name: "Datasets", href: "/datasets", icon: Database },
    { name: "Inference Engine", href: "/predictions", icon: BrainCircuit },
    { name: "GIS Intelligence", href: "/gis", icon: Map },
    { name: "Operations Hub", href: "/operations", icon: ShieldAlert },
    { name: "Analytics & Reports", href: "/analytics", icon: BarChart3 },
  ];

  // Admin section link
  const isAdmin = user?.roles.some((r) => r.name.toLowerCase() === "super admin");
  if (isAdmin) {
    menuItems.push({ name: "Governance & Admin", href: "/admin", icon: Settings });
  }

  if (!sidebarOpen) return null;

  return (
    <aside className="fixed inset-y-0 left-0 z-40 w-64 bg-neutral-900 border-r border-white/5 flex flex-col justify-between transition-transform duration-300">
      <div>
        {/* Header */}
        <div className="h-16 flex items-center justify-between px-6 border-b border-white/5">
          <Link href="/dashboard" className="flex items-center space-x-2.5">
            <Flame className="w-6 h-6 text-rose-500 animate-pulse" />
            <span className="font-bold text-base uppercase tracking-wider text-gradient">
              IgnisAI
            </span>
          </Link>
          <button
            onClick={() => setSidebar(false)}
            className="md:hidden p-1 rounded hover:bg-white/5 text-neutral-400 hover:text-white"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Navigation links */}
        <nav className="p-4 space-y-1">
          {menuItems.map((item) => {
            const Icon = item.icon;
            const active = isLinkActive(item.href);
            return (
              <Link
                key={item.name}
                href={item.href}
                className={`flex items-center space-x-3 px-4 py-3 rounded-lg text-sm font-medium transition-all ${
                  active
                    ? "bg-emerald-600/10 text-emerald-400 border-l-2 border-emerald-500"
                    : "text-neutral-400 hover:text-neutral-100 hover:bg-neutral-800/40"
                }`}
              >
                <Icon className={`w-4 h-4 ${active ? "text-emerald-400" : "text-neutral-400"}`} />
                <span>{item.name}</span>
              </Link>
            );
          })}
        </nav>
      </div>

      {/* User profile section at the bottom */}
      <div className="p-4 border-t border-white/5 bg-neutral-950/20">
        <div className="flex items-center space-x-3">
          <div className="w-9 h-9 rounded-full bg-emerald-700 flex items-center justify-center font-bold text-white text-sm uppercase">
            {user?.username?.[0] || "U"}
          </div>
          <div className="overflow-hidden">
            <h4 className="text-sm font-semibold text-neutral-200 truncate">{user?.username}</h4>
            <p className="text-xs text-neutral-500 truncate">{user?.email}</p>
          </div>
        </div>
      </div>
    </aside>
  );
}
