"use client";

import Image from "next/image";
import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get("error") === "confirm_failed") {
      setError(
        "Email confirmation failed or expired. Please sign in or sign up again."
      );
    }
  }, []);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    const supabase = createClient();
    const { error: authError } = await supabase.auth.signInWithPassword({
      email,
      password,
    });
    setLoading(false);
    if (authError) {
      setError(authError.message);
      return;
    }
    router.push("/dashboard");
    router.refresh();
  }

  return (
    <main className="min-h-screen flex items-center justify-center px-4">
      <div className="w-full max-w-md animate-fadeIn">
        <div className="mb-10 text-center">
          <div className="relative mx-auto mb-5 h-28 w-28">
            <Image
              src="/brand/lucero.webp"
              alt="L.U.C.E.R.O"
              fill
              priority
              className="object-contain drop-shadow-[0_0_24px_rgba(34,211,238,0.35)]"
            />
          </div>
          <p className="font-display text-5xl tracking-[0.2em] text-jarvis-text">
            L.U.C.E.R.O
          </p>
          <p className="mt-3 text-jarvis-muted text-sm">
            Your AI business partner
          </p>
        </div>

        <form
          onSubmit={onSubmit}
          className="rounded-2xl border border-jarvis-border bg-jarvis-panel/80 backdrop-blur p-8 shadow-glow"
        >
          <h1 className="text-lg font-medium mb-6">Sign in</h1>

          <label className="block text-xs uppercase tracking-wider text-jarvis-muted mb-2">
            Email
          </label>
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full mb-4 rounded-lg bg-jarvis-bg border border-jarvis-border px-3 py-2.5 text-sm outline-none focus:border-jarvis-accent"
          />

          <label className="block text-xs uppercase tracking-wider text-jarvis-muted mb-2">
            Password
          </label>
          <input
            type="password"
            required
            minLength={6}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full mb-6 rounded-lg bg-jarvis-bg border border-jarvis-border px-3 py-2.5 text-sm outline-none focus:border-jarvis-accent"
          />

          {error && (
            <p className="mb-4 text-sm text-jarvis-danger">{error}</p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-lg bg-jarvis-cyan text-jarvis-bg font-medium py-2.5 text-sm hover:bg-jarvis-accentDim transition disabled:opacity-60"
          >
            {loading ? "Signing in…" : "Sign in"}
          </button>

          <p className="mt-6 text-center text-sm text-jarvis-muted">
            Need an account?{" "}
            <Link href="/signup" className="text-jarvis-cyan hover:underline">
              Sign up
            </Link>
          </p>
        </form>
      </div>
    </main>
  );
}
