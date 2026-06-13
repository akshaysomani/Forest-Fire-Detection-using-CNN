"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useUiStore } from "@/store/ui-store";
import { authService } from "@/services/auth";
import { Card, CardHeader, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { ShieldAlert } from "lucide-react";

export default function RegisterPage() {
  const router = useRouter();
  const { addToast } = useUiStore();

  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const validate = () => {
    const tempErrors: Record<string, string> = {};
    if (!email.trim() || !/\S+@\S+\.\S+/.test(email)) tempErrors.email = "Valid email is required";
    if (username.length < 3) tempErrors.username = "Username must be at least 3 characters";
    if (password.length < 8) tempErrors.password = "Password must be at least 8 characters";
    if (password !== confirmPassword) tempErrors.confirmPassword = "Passwords do not match";
    setErrors(tempErrors);
    return Object.keys(tempErrors).length === 0;
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) return;

    setLoading(true);
    try {
      await authService.register({
        email,
        username,
        password,
        confirm_password: confirmPassword,
      });

      addToast({
        type: "success",
        title: "Account Request Sent",
        message: "Your registration is complete. Please check email for activation.",
      });

      router.push("/auth/login");
    } catch (err: any) {
      setErrors({ api: err.message || "Failed to register account." });
      addToast({
        type: "error",
        title: "Registration Rejected",
        message: err.message || "Failed to submit request.",
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto w-full max-w-[460px] px-4">
      <Card className="border border-white/5 shadow-glass" glow>
        <CardHeader className="flex flex-col items-center pt-8 pb-4 text-center border-b-0">
          <div className="w-12 h-12 rounded-xl bg-emerald-500/10 flex items-center justify-center border border-emerald-500/20 mb-3">
            <ShieldAlert className="w-6 h-6 text-emerald-400" />
          </div>
          <h2 className="text-2xl font-extrabold tracking-tight text-white">
            REQUEST CREDENTIALS
          </h2>
          <p className="text-xs text-neutral-400 mt-1 uppercase tracking-wider font-semibold">
            Wildfire Operations Command
          </p>
        </CardHeader>
        <CardContent className="px-8 pb-8 pt-2">
          {errors.api && (
            <div className="mb-4 p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-xs text-rose-400 font-semibold leading-relaxed">
              {errors.api}
            </div>
          )}
          <form onSubmit={handleRegister} className="space-y-4">
            <Input
              label="Email Address"
              type="email"
              placeholder="ranger@forestry.gov"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              error={errors.email}
              disabled={loading}
              autoComplete="email"
            />
            <Input
              label="Username"
              placeholder="e.g. ranger_smith"
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
              autoComplete="new-password"
            />
            <Input
              label="Confirm Password"
              type="password"
              placeholder="••••••••"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              error={errors.confirmPassword}
              disabled={loading}
              autoComplete="new-password"
            />
            <Button variant="primary" type="submit" loading={loading} className="w-full py-3 mt-2">
              Submit Request
            </Button>
          </form>

          <div className="mt-6 text-center text-xs text-neutral-400">
            Already have clearance?{" "}
            <Link
              href="/auth/login"
              className="font-semibold text-emerald-500 hover:text-emerald-400 transition"
            >
              Sign In
            </Link>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
