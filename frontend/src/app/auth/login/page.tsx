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
import { Flame } from "lucide-react";

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

      // Fetch user profile immediately
      const profile = await authService.getProfile();
      setUser(profile);

      addToast({
        type: "success",
        title: "Access Granted",
        message: `Welcome back, ${profile.username}! Authentication successful.`,
      });

      router.push("/dashboard");
    } catch (err: any) {
      setErrors({ api: err.message || "Failed to log in. Please check your credentials." });
      addToast({
        type: "error",
        title: "Authentication Failed",
        message: err.message || "Please check your network or login details.",
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto w-full max-w-[440px] px-4">
      <Card className="border border-white/5 shadow-glass" glow>
        <CardHeader className="flex flex-col items-center pt-8 pb-4 text-center border-b-0">
          <div className="w-12 h-12 rounded-xl bg-emerald-500/10 flex items-center justify-center border border-emerald-500/20 mb-3">
            <Flame className="w-6 h-6 text-emerald-400" />
          </div>
          <h2 className="text-2xl font-extrabold tracking-tight text-white">
            IGNISAI PORTAL
          </h2>
          <p className="text-xs text-neutral-400 mt-1 uppercase tracking-wider font-semibold">
            Emergency Response & Prevention
          </p>
        </CardHeader>
        <CardContent className="px-8 pb-8 pt-2">
          {errors.api && (
            <div className="mb-4 p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-xs text-rose-400 font-semibold leading-relaxed">
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
            <div className="flex justify-between items-center text-xs">
              <span className="text-neutral-500">Demo: admin / SuperSecurePassword123!</span>
              <Link
                href="/auth/forgot"
                className="font-medium text-emerald-500 hover:text-emerald-400 transition"
              >
                Forgot Password?
              </Link>
            </div>
            <Button variant="primary" type="submit" loading={loading} className="w-full py-3 mt-2">
              Authenticate Access
            </Button>
          </form>

          <div className="mt-6 text-center text-xs text-neutral-400">
            Need command credentials?{" "}
            <Link
              href="/auth/register"
              className="font-semibold text-emerald-500 hover:text-emerald-400 transition"
            >
              Request Account
            </Link>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
