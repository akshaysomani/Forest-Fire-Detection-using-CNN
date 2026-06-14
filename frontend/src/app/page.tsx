"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/store/auth-store";
import {
  Flame,
  Shield,
  BrainCircuit,
  Map,
  BarChart3,
  Zap,
  ArrowRight,
  Satellite,
  TreePine,
  Globe,
  ChevronDown,
} from "lucide-react";

export default function Home() {
  const router = useRouter();
  const { accessToken } = useAuthStore();
  const [scrollY, setScrollY] = useState(0);

  useEffect(() => {
    // If already authenticated, go straight to dashboard
    if (accessToken) {
      router.replace("/dashboard");
    }
  }, [accessToken, router]);

  useEffect(() => {
    const handleScroll = () => setScrollY(window.scrollY);
    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  // If authenticated, show loading while redirecting
  if (accessToken) {
    return (
      <div className="min-h-screen bg-neutral-950 flex items-center justify-center">
        <div className="w-10 h-10 border-4 border-emerald-500/20 border-t-emerald-500 rounded-full animate-spin" />
      </div>
    );
  }

  const features = [
    {
      icon: BrainCircuit,
      title: "CNN-Powered Detection",
      description:
        "Convolutional Neural Network trained on 50,000+ satellite and ground-level wildfire images with 97.2% accuracy.",
      gradient: "from-emerald-500 to-teal-500",
    },
    {
      icon: Satellite,
      title: "Real-Time Satellite Feed",
      description:
        "Continuous monitoring of high-risk zones via satellite imagery with sub-minute processing latency.",
      gradient: "from-cyan-500 to-blue-500",
    },
    {
      icon: Map,
      title: "GIS Intelligence Hub",
      description:
        "Interactive geospatial mapping with containment rings, geofencing grids, and coordinate intelligence scanning.",
      gradient: "from-violet-500 to-purple-500",
    },
    {
      icon: Shield,
      title: "Emergency Response",
      description:
        "Automated alert escalation, incident management, and response team dispatch coordination.",
      gradient: "from-rose-500 to-orange-500",
    },
    {
      icon: BarChart3,
      title: "Analytics & Reporting",
      description:
        "Business intelligence dashboards with KPI tracking, trend analysis, and automated PDF/CSV report generation.",
      gradient: "from-amber-500 to-yellow-500",
    },
    {
      icon: Zap,
      title: "MLOps Pipeline",
      description:
        "Enterprise model registry, A/B testing, deployment tracking, and performance monitoring infrastructure.",
      gradient: "from-pink-500 to-rose-500",
    },
  ];

  const stats = [
    { value: "97.2%", label: "Detection Accuracy" },
    { value: "<500ms", label: "Inference Latency" },
    { value: "24/7", label: "Monitoring Coverage" },
    { value: "50K+", label: "Training Images" },
  ];

  return (
    <div className="min-h-screen bg-neutral-950 text-neutral-100 overflow-x-hidden">
      {/* Navigation Bar */}
      <nav className="fixed top-0 left-0 right-0 z-50 border-b border-white/5 bg-neutral-950/80 backdrop-blur-xl">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center space-x-2.5">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-rose-500 to-orange-500 flex items-center justify-center">
              <Flame className="w-4.5 h-4.5 text-white" />
            </div>
            <span className="font-extrabold text-lg tracking-tight">
              <span className="text-white">Ignis</span>
              <span className="text-emerald-400">AI</span>
            </span>
          </Link>
          <div className="flex items-center space-x-4">
            <Link
              href="/auth/login"
              className="text-sm text-neutral-400 hover:text-white transition font-medium px-4 py-2"
            >
              Sign In
            </Link>
            <Link
              href="/auth/register"
              className="text-sm font-semibold bg-emerald-600 hover:bg-emerald-500 text-white px-5 py-2.5 rounded-lg transition-all hover:shadow-lg hover:shadow-emerald-500/20"
            >
              Get Started
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative min-h-screen flex items-center justify-center pt-16">
        {/* Animated background gradient */}
        <div className="absolute inset-0 overflow-hidden">
          <div
            className="absolute top-1/4 -left-1/4 w-[800px] h-[800px] rounded-full opacity-10"
            style={{
              background: "radial-gradient(circle, #10b981 0%, transparent 70%)",
              transform: `translate(${scrollY * 0.05}px, ${scrollY * -0.02}px)`,
            }}
          />
          <div
            className="absolute bottom-1/4 -right-1/4 w-[600px] h-[600px] rounded-full opacity-10"
            style={{
              background: "radial-gradient(circle, #f43f5e 0%, transparent 70%)",
              transform: `translate(${scrollY * -0.03}px, ${scrollY * 0.04}px)`,
            }}
          />
          {/* Grid overlay */}
          <div
            className="absolute inset-0 opacity-[0.03]"
            style={{
              backgroundImage:
                "linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)",
              backgroundSize: "60px 60px",
            }}
          />
        </div>

        <div className="relative z-10 text-center max-w-4xl mx-auto px-6">
          {/* Badge */}
          <div className="inline-flex items-center space-x-2 bg-emerald-500/10 border border-emerald-500/20 rounded-full px-4 py-1.5 mb-8">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            <span className="text-xs font-semibold text-emerald-400 uppercase tracking-wider">
              AI-Powered Wildfire Prevention
            </span>
          </div>

          <h1 className="text-5xl md:text-7xl font-black tracking-tight leading-[1.1] mb-6">
            <span className="text-white">Detect Wildfires</span>
            <br />
            <span className="bg-gradient-to-r from-emerald-400 via-teal-400 to-cyan-400 bg-clip-text text-transparent">
              Before They Spread
            </span>
          </h1>

          <p className="text-lg md:text-xl text-neutral-400 max-w-2xl mx-auto mb-10 leading-relaxed">
            Enterprise-grade wildfire detection platform powered by deep learning.
            Monitor forests in real-time, predict fire risks, and coordinate emergency
            response with military precision.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-16">
            <Link
              href="/auth/register"
              className="group inline-flex items-center space-x-2 bg-emerald-600 hover:bg-emerald-500 text-white font-semibold px-8 py-4 rounded-xl transition-all hover:shadow-xl hover:shadow-emerald-500/20 text-base"
            >
              <span>Launch Detection Platform</span>
              <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
            </Link>
            <Link
              href="/auth/login"
              className="inline-flex items-center space-x-2 border border-white/10 hover:border-white/20 text-neutral-300 hover:text-white font-medium px-8 py-4 rounded-xl transition-all text-base"
            >
              <span>Sign In to Dashboard</span>
            </Link>
          </div>

          {/* Stats Row */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6 md:gap-8 max-w-3xl mx-auto">
            {stats.map((stat) => (
              <div key={stat.label} className="text-center">
                <div className="text-2xl md:text-3xl font-black text-white">{stat.value}</div>
                <div className="text-xs text-neutral-500 font-semibold uppercase tracking-wider mt-1">
                  {stat.label}
                </div>
              </div>
            ))}
          </div>

          {/* Scroll indicator */}
          <div className="mt-16 animate-bounce">
            <ChevronDown className="w-5 h-5 text-neutral-600 mx-auto" />
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-24 px-6 relative">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <span className="text-xs font-bold text-emerald-400 uppercase tracking-[0.2em] block mb-3">
              PLATFORM CAPABILITIES
            </span>
            <h2 className="text-3xl md:text-4xl font-extrabold text-white tracking-tight">
              Enterprise Detection Infrastructure
            </h2>
            <p className="text-neutral-400 mt-4 max-w-xl mx-auto text-sm">
              Built with production-grade architecture — from CNN inference to GIS mapping
              and real-time operations control.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {features.map((feature) => {
              const Icon = feature.icon;
              return (
                <div
                  key={feature.title}
                  className="group relative bg-neutral-900/50 border border-white/5 rounded-2xl p-8 hover:border-emerald-500/20 transition-all duration-500 hover:-translate-y-1"
                >
                  <div
                    className={`w-12 h-12 rounded-xl bg-gradient-to-br ${feature.gradient} flex items-center justify-center mb-5 opacity-80 group-hover:opacity-100 transition-opacity`}
                  >
                    <Icon className="w-6 h-6 text-white" />
                  </div>
                  <h3 className="text-lg font-bold text-white mb-2">{feature.title}</h3>
                  <p className="text-sm text-neutral-400 leading-relaxed">{feature.description}</p>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* Architecture Section */}
      <section className="py-24 px-6 border-t border-white/5">
        <div className="max-w-5xl mx-auto text-center">
          <span className="text-xs font-bold text-emerald-400 uppercase tracking-[0.2em] block mb-3">
            TECHNOLOGY STACK
          </span>
          <h2 className="text-3xl md:text-4xl font-extrabold text-white tracking-tight mb-6">
            Production-Grade Architecture
          </h2>
          <p className="text-neutral-400 max-w-2xl mx-auto text-sm mb-16">
            Built with enterprise patterns — FastAPI backend, Next.js frontend, SQLAlchemy ORM,
            JWT security, and a full MLOps pipeline.
          </p>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="bg-neutral-900/30 border border-white/5 rounded-2xl p-8 text-left">
              <div className="w-10 h-10 rounded-lg bg-cyan-500/10 flex items-center justify-center mb-4">
                <Globe className="w-5 h-5 text-cyan-400" />
              </div>
              <h4 className="font-bold text-white mb-2">Next.js Frontend</h4>
              <p className="text-xs text-neutral-400 leading-relaxed">
                React 18 with server components, Tailwind CSS, Zustand state management, React Query,
                and Recharts visualization.
              </p>
            </div>
            <div className="bg-neutral-900/30 border border-white/5 rounded-2xl p-8 text-left">
              <div className="w-10 h-10 rounded-lg bg-emerald-500/10 flex items-center justify-center mb-4">
                <Zap className="w-5 h-5 text-emerald-400" />
              </div>
              <h4 className="font-bold text-white mb-2">FastAPI Backend</h4>
              <p className="text-xs text-neutral-400 leading-relaxed">
                Async Python with SQLAlchemy, JWT auth, rate limiting, event bus,
                background job scheduler, and observability middleware.
              </p>
            </div>
            <div className="bg-neutral-900/30 border border-white/5 rounded-2xl p-8 text-left">
              <div className="w-10 h-10 rounded-lg bg-rose-500/10 flex items-center justify-center mb-4">
                <TreePine className="w-5 h-5 text-rose-400" />
              </div>
              <h4 className="font-bold text-white mb-2">CNN Model</h4>
              <p className="text-xs text-neutral-400 leading-relaxed">
                TensorFlow/Keras deep learning model with transfer learning,
                data augmentation, and optimized inference pipeline.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-24 px-6 border-t border-white/5">
        <div className="max-w-3xl mx-auto text-center">
          <div className="bg-gradient-to-br from-neutral-900 to-neutral-950 border border-white/5 rounded-3xl p-12 relative overflow-hidden">
            <div className="absolute inset-0 bg-gradient-to-br from-emerald-500/5 to-transparent" />
            <div className="relative z-10">
              <Flame className="w-12 h-12 text-rose-500 mx-auto mb-6 animate-pulse" />
              <h2 className="text-3xl font-extrabold text-white mb-4">
                Ready to Protect Our Forests?
              </h2>
              <p className="text-neutral-400 text-sm mb-8 max-w-lg mx-auto">
                Deploy the IgnisAI platform and start monitoring wildfire-prone regions
                with state-of-the-art AI detection capabilities.
              </p>
              <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                <Link
                  href="/auth/register"
                  className="group inline-flex items-center space-x-2 bg-emerald-600 hover:bg-emerald-500 text-white font-semibold px-8 py-4 rounded-xl transition-all hover:shadow-xl hover:shadow-emerald-500/20"
                >
                  <span>Create Free Account</span>
                  <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                </Link>
                <a
                  href="https://github.com/akshaysomani/Forest-Fire-Detection-using-CNN"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center space-x-2 border border-white/10 hover:border-white/20 text-neutral-300 hover:text-white font-medium px-8 py-4 rounded-xl transition-all"
                >
                  <span>View on GitHub</span>
                </a>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-12 px-6 border-t border-white/5">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center space-x-2">
            <Flame className="w-4 h-4 text-rose-500" />
            <span className="text-sm font-bold text-neutral-400">
              IgnisAI — Forest Fire Detection Platform
            </span>
          </div>
          <div className="flex items-center space-x-6 text-xs text-neutral-500">
            <a
              href="https://github.com/akshaysomani/Forest-Fire-Detection-using-CNN"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-neutral-300 transition"
            >
              GitHub
            </a>
            <span>Built with FastAPI + Next.js + TensorFlow</span>
            <span>© {new Date().getFullYear()} IgnisAI</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
