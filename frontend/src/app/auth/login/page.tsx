"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/store/auth-store";
import { useUiStore } from "@/store/ui-store";
import { authService } from "@/services/auth";
import { Card, CardHeader, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Flame, Zap } from "lucide-react";

export default function LoginPage() {
  const router = useRouter();
  const { setTokens, setUser } = useAuthStore();
  const { addToast } = useUiStore();

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const validate = () => {
    const tempErrors: Record<string, string> = {};
    if (!username.trim()) tempErrors.username = "Username or Email is required";
    if (!password) tempErrors.password = "Password is required";
    setErrors(tempErrors);
    return Object.keys(tempErrors).length === 0;
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) return;

    setLoading(true);
    try {
      const formData = new URLSearchParams();
      formData.append("username", username);
      formData.append("password", password);

      const loginRes = await authService.login(formData);
      setTokens(loginRes.access_token, loginRes.refresh_token);

      const profile = await authService.getProfile();
      setUser(profile);

      const roleLabel = profile.roles?.[0]?.name ?? "User";

      addToast({
        type: "success",
        title: "Access Granted",
        message: `Welcome back, ${profile.username}! Signed in as ${roleLabel}.`,
      });

      router.push("/dashboard");
    } catch (err: any) {
      setErrors({
        api: err.message || "Failed to log in. Please check your credentials.",
      });
      addToast({
        type: "error",
        title: "Authentication Failed",
        message: err.message || "Please check your credentials.",
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto w-full max-w-[420px] px-4">
      <Card className="border border-white/5 shadow-glass" glow>
        {/* Header */}
        <CardHeader className="flex flex-col items-center pt-9 pb-5 text-center border-b border-white/5">
          {/* Logo mark */}
          <div className="relative w-14 h-14 mb-3">
            <div className="absolute inset-0 rounded-2xl bg-emerald-500/10 border border-emerald-500/20" />
            <div className="absolute inset-0 flex items-center justify-center">
              <Flame className="w-7 h-7 text-emerald-400" />
            </div>
            <div className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-rose-500/80 border-2 border-neutral-950 flex items-center justify-center">
              <Zap className="w-2 h-2 text-white" />
            </div>
          </div>

          <h2 className="text-2xl font-extrabold tracking-tight text-white">
            IGNISAI
          </h2>
          <p className="text-[11px] text-neutral-500 mt-1 uppercase tracking-widest font-semibold">
            Forest Fire Detection System
          </p>
        </CardHeader>

        <CardContent className="px-7 pb-8 pt-6">
          {errors.api && (
            <div className="mb-5 p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-xs text-rose-400 font-semibold leading-relaxed">
              {errors.api}
            </div>
          )}

          <form onSubmit={handleLogin} className="space-y-4">
            <Input
              label="Username or Email"
              placeholder="e.g. administrator"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              error={errors.username}
              disabled={loading}
              autoComplete="username"
            />
            <Input
              label="Password"
              type="password"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              error={errors.password}
              disabled={loading}
              autoComplete="current-password"
            />

            {/* Hint + forgot password row */}
            <div className="flex items-center justify-between pt-0.5">
              <span className="text-[10px] text-neutral-600 font-medium bg-neutral-900/60 px-2.5 py-1 rounded-lg border border-white/5">
                Demo: admin / SuperSecurePassword123!
              </span>
              <Link
                href="/auth/forgot"
                className="text-xs font-medium text-neutral-400 hover:text-emerald-400 transition"
              >
                Forgot?
              </Link>
            </div>

            <Button
              variant="primary"
              type="submit"
              loading={loading}
              className="w-full py-3"
            >
              Sign In
            </Button>
          </form>

          {/* Divider */}
          <div className="my-6 flex items-center gap-3">
            <div className="flex-1 h-px bg-white/5" />
            <span className="text-[10px] text-neutral-600 uppercase tracking-widest">
              or
            </span>
            <div className="flex-1 h-px bg-white/5" />
          </div>

          <div className="text-center text-xs text-neutral-500">
            Don&apos;t have an account?{" "}
            <Link
              href="/auth/register"
              className="font-semibold text-emerald-500 hover:text-emerald-400 transition"
            >
              Register now
            </Link>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
