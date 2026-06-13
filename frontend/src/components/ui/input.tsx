import React from "react";
import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type = "text", label, error, ...props }, ref) => {
    return (
      <div className="w-full space-y-1.5">
        {label && (
          <label className="text-xs font-semibold text-neutral-400 uppercase tracking-wider">
            {label}
          </label>
        )}
        <input
          type={type}
          className={twMerge(
            clsx(
              "w-full px-4 py-2.5 bg-neutral-900/60 border border-white/10 rounded-lg text-neutral-100 placeholder-neutral-500 transition-all focus:outline-none focus:border-emerald-500/80 focus:ring-1 focus:ring-emerald-500/30",
              error && "border-rose-500/80 focus:border-rose-500 focus:ring-rose-500/20"
            ),
            className
          )}
          ref={ref}
          {...props}
        />
        {error && <p className="text-xs font-medium text-rose-500">{error}</p>}
      </div>
    );
  }
);

Input.displayName = "Input";
