"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useUiStore } from "@/store/ui-store";
import { authService } from "@/services/auth";
import { Card, CardHeader, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  ShieldAlert,
  Eye,
  TreePine,
  FlaskConical,
  Siren,
  CheckCircle2,
} from "lucide-react";

const ROLES = [
  {
    id: "Viewer",
    label: "Viewer",
    icon: Eye,
    description: "Read-only access to predictions and reports",
    color: "text-sky-400",
    border: "border-sky-500/30",
    bg: "bg-sky-500/10",
    activeBg: "bg-sky-500/15",
    activeBorder: "border-sky-400",
  },
  {
    id: "Forest Officer",
    label: "Forest Officer",
    icon: TreePine,
    description: "Upload images, run detections, receive alerts",
    color: "text-emerald-400",
    border: "border-emerald-500/30",
    bg: "bg-emerald-500/10",
    activeBg: "bg-emerald-500/15",
    activeBorder: "border-emerald-400",
  },
  {
    id: "Emergency Response Officer",
    label: "Emergency Officer",
    icon: Siren,
    description: "View predictions, reports and emergency alerts",
    color: "text-rose-400",
    border: "border-rose-500/30",
    bg: "bg-rose-500/10",
    activeBg: "bg-rose-500/15",
    activeBorder: "border-rose-400",
  },
  {
    id: "Research Analyst",
    label: "Research Analyst",
    icon: FlaskConical,
    description: "Analyse data, run spatial scripts, view reports",
    color: "text-amber-400",
    border: "border-amber-500/30",
    bg: "bg-amber-500/10",
    activeBg: "bg-amber-500/15",
    activeBorder: "border-amber-400",
  },
];

export default function RegisterPage() {
  const router = useRouter();
  const { addToast } = useUiStore();

  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [selectedRole, setSelectedRole] = useState("Viewer");
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const validate = () => {
    const tempErrors: Record<string, string> = {};
    if (!email.trim() || !/\S+@\S+\.\S+/.test(email))
      tempErrors.email = "Valid email is required";
    if (username.length < 3)
      tempErrors.username = "Username must be at least 3 characters";
    if (password.length < 8)
      tempErrors.password = "Password must be at least 8 characters";
    if (password !== confirmPassword)
      tempErrors.confirmPassword = "Passwords do not match";
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
        role: selectedRole,
      });

      addToast({
        type: "success",
        title: "Account Created",
        message: `Registered as ${selectedRole}. You can now sign in!`,
      });

      router.push("/auth/login");
    } catch (err: any) {
      setErrors({ api: err.message || "Failed to register account." });
      addToast({
        type: "error",
        title: "Registration Failed",
        message: err.message || "Failed to submit request.",
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto w-full max-w-[560px] px-4 py-6">
      <Card className="border border-white/5 shadow-glass" glow>
        {/* Header */}
        <CardHeader className="flex flex-col items-center pt-8 pb-5 text-center border-b border-white/5">
          <div className="w-12 h-12 rounded-2xl bg-emerald-500/10 flex items-center justify-center border border-emerald-500/20 mb-3">
            <ShieldAlert className="w-6 h-6 text-emerald-400" />
          </div>
          <h2 className="text-2xl font-extrabold tracking-tight text-white">
            Create Account
          </h2>
          <p className="text-xs text-neutral-500 mt-1 uppercase tracking-widest font-semibold">
            Wildfire Operations Command
          </p>
        </CardHeader>

        <CardContent className="px-7 pb-8 pt-6">
          {errors.api && (
            <div className="mb-5 p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-xs text-rose-400 font-semibold leading-relaxed">
              {errors.api}
            </div>
          )}

          {/* ── Role Selector ── */}
          <div className="mb-6">
            <p className="text-xs font-bold uppercase tracking-widest text-neutral-500 mb-3">
              Select Your Role
            </p>
            <div className="grid grid-cols-2 gap-2.5">
              {ROLES.map((role) => {
                const Icon = role.icon;
                const isActive = selectedRole === role.id;
                return (
                  <button
                    key={role.id}
                    type="button"
                    onClick={() => setSelectedRole(role.id)}
                    className={`relative flex flex-col items-start p-3.5 rounded-xl border text-left transition-all duration-200 ${
                      isActive
                        ? `${role.activeBg} ${role.activeBorder} shadow-sm`
                        : `${role.bg} ${role.border} hover:brightness-110`
                    }`}
                  >
                    {isActive && (
                      <CheckCircle2
                        className={`absolute top-2.5 right-2.5 w-3.5 h-3.5 ${role.color}`}
                      />
                    )}
                    <Icon className={`w-5 h-5 ${role.color} mb-2`} />
                    <span
                      className={`text-xs font-bold leading-tight ${
                        isActive ? "text-white" : "text-neutral-300"
                      }`}
                    >
                      {role.label}
                    </span>
                    <span className="text-[10px] text-neutral-500 mt-1 leading-snug">
                      {role.description}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* ── Form Fields ── */}
          <form onSubmit={handleRegister} className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
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
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
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
            </div>

            {/* Selected role confirmation pill */}
            <div className="flex items-center gap-2 py-2 px-3 rounded-lg bg-neutral-900/60 border border-white/5 text-xs text-neutral-400">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 shrink-0" />
              <span>
                Registering as{" "}
                <span className="font-bold text-white">{selectedRole}</span>
              </span>
            </div>

            <Button
              variant="primary"
              type="submit"
              loading={loading}
              className="w-full py-3 mt-1"
            >
              Create Account
            </Button>
          </form>

          <div className="mt-6 text-center text-xs text-neutral-500">
            Already have access?{" "}
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
