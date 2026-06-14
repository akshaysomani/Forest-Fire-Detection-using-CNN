"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useUiStore } from "@/store/ui-store";
import { authService } from "@/services/auth";
import { Card, CardHeader, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { KeyRound, ArrowLeft, CheckCircle } from "lucide-react";

export default function ForgotPasswordPage() {
  const { addToast } = useUiStore();

  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const validate = () => {
    const tempErrors: Record<string, string> = {};
    if (!email.trim() || !/\S+@\S+\.\S+/.test(email))
      tempErrors.email = "A valid email address is required";
    setErrors(tempErrors);
    return Object.keys(tempErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) return;

    setLoading(true);
    try {
      await authService.forgotPassword(email);
      setSubmitted(true);
      addToast({
        type: "success",
        title: "Reset Link Dispatched",
        message: "If an account with that email exists, a password reset link has been sent.",
      });
    } catch (err: any) {
      // Always show success to prevent email enumeration
      setSubmitted(true);
      addToast({
        type: "info",
        title: "Request Processed",
        message: "If an account with that email exists, instructions have been sent.",
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
            {submitted ? (
              <CheckCircle className="w-6 h-6 text-emerald-400" />
            ) : (
              <KeyRound className="w-6 h-6 text-emerald-400" />
            )}
          </div>
          <h2 className="text-2xl font-extrabold tracking-tight text-white">
            {submitted ? "CHECK YOUR EMAIL" : "RESET CREDENTIALS"}
          </h2>
          <p className="text-xs text-neutral-400 mt-1 uppercase tracking-wider font-semibold">
            {submitted
              ? "Password reset instructions have been sent"
              : "Enter your registered email to recover access"}
          </p>
        </CardHeader>
        <CardContent className="px-8 pb-8 pt-2">
          {!submitted ? (
            <>
              {errors.api && (
                <div className="mb-4 p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-xs text-rose-400 font-semibold leading-relaxed">
                  {errors.api}
                </div>
              )}
              <form onSubmit={handleSubmit} className="space-y-4">
                <Input
                  label="Email Address"
                  type="email"
                  placeholder="e.g. ranger@forestry.gov"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  error={errors.email}
                  disabled={loading}
                  autoComplete="email"
                />
                <Button
                  variant="primary"
                  type="submit"
                  loading={loading}
                  className="w-full py-3 mt-2"
                >
                  Send Reset Link
                </Button>
              </form>
            </>
          ) : (
            <div className="text-center space-y-4 py-4">
              <p className="text-sm text-neutral-400 leading-relaxed">
                If an account with <span className="text-emerald-400 font-semibold">{email}</span> exists in our system, you will receive password reset instructions shortly.
              </p>
              <p className="text-xs text-neutral-500">
                Check your inbox and spam folder. The link expires in 15 minutes.
              </p>
            </div>
          )}

          <div className="mt-6 text-center">
            <Link
              href="/auth/login"
              className="inline-flex items-center space-x-1.5 text-xs font-semibold text-emerald-500 hover:text-emerald-400 transition"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              <span>Back to Login</span>
            </Link>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
