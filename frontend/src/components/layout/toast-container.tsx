"use client";

import { useUiStore } from "@/store/ui-store";
import { CheckCircle, AlertTriangle, AlertCircle, Info, X } from "lucide-react";

export default function ToastContainer() {
  const { toasts, removeToast } = useUiStore();

  if (toasts.length === 0) return null;

  const icons = {
    success: <CheckCircle className="w-5 h-5 text-emerald-500" />,
    error: <AlertCircle className="w-5 h-5 text-rose-500" />,
    warning: <AlertTriangle className="w-5 h-5 text-amber-500" />,
    info: <Info className="w-5 h-5 text-sky-500" />,
  };

  const borders = {
    success: "border-emerald-500/20 shadow-emerald-950/20",
    error: "border-rose-500/20 shadow-rose-950/20",
    warning: "border-amber-500/20 shadow-amber-950/20",
    info: "border-sky-500/20 shadow-sky-950/20",
  };

  return (
    <div className="fixed top-4 right-4 z-50 flex flex-col space-y-3 w-full max-w-sm">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className={`flex items-start bg-neutral-900/90 backdrop-blur border rounded-xl p-4 shadow-xl transition-all duration-300 transform translate-y-0 ${borders[toast.type]}`}
        >
          <div className="flex-shrink-0 mr-3 mt-0.5">{icons[toast.type]}</div>
          <div className="flex-1 mr-2">
            <h5 className="text-sm font-semibold text-neutral-100">{toast.title}</h5>
            <p className="text-xs text-neutral-400 mt-1 leading-relaxed">{toast.message}</p>
          </div>
          <button
            onClick={() => removeToast(toast.id)}
            className="flex-shrink-0 p-0.5 rounded-lg text-neutral-500 hover:text-neutral-300 hover:bg-white/5"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      ))}
    </div>
  );
}
