"use client";

import Image from "next/image";
import Link from "next/link";
import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";

export default function SignupPage() {
  const router = useRouter();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<"owner" | "wife">("owner");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setSuccess(null);

    const supabase = createClient();
    const origin =
      process.env.NEXT_PUBLIC_SITE_URL?.replace(/\/$/, "") ||
      window.location.origin;
    const emailRedirectTo = `${origin}/auth/callback`;

    const { data, error: authError } = await supabase.auth.signUp({
      email,
      password,
      options: {
        emailRedirectTo,
        data: {
          full_name: fullName,
          role,
        },
      },
    });

    setLoading(false);

    if (authError) {
      setError(authError.message);
      return;
    }

    // Email confirmation required — no session until they click the link.
    if (!data.session) {
      setSuccess(
        `We sent a confirmation email to ${email}. Open that link to activate your account, then sign in.`
      );
      return;
    }

    // Confirmations disabled in Supabase — signed in immediately.
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
          <p className="font-display text-5xl tracking-[0.2em]">L.U.C.E.R.O</p>
          <p className="mt-3 text-jarvis-muted text-sm">
            Create your business partner account
          </p>
        </div>

        <div className="rounded-2xl border border-jarvis-border bg-jarvis-panel/80 backdrop-blur p-8 shadow-glow">
          {success ? (
            <div className="space-y-5">
              <h1 className="text-lg font-medium">Check your email</h1>
              <p className="text-sm text-jarvis-muted leading-relaxed">
                {success}
              </p>
              <p className="text-xs text-jarvis-muted">
                Didn&apos;t get it? Check spam, or wait a minute and try again.
              </p>
              <Link
                href="/login"
                className="inline-flex w-full items-center justify-center rounded-lg bg-jarvis-accent text-jarvis-bg font-medium py-2.5 text-sm hover:bg-jarvis-accentDim transition"
              >
                Go to sign in
              </Link>
            </div>
          ) : (
            <form onSubmit={onSubmit}>
              <h1 className="text-lg font-medium mb-6">Sign up</h1>

              <label className="block text-xs uppercase tracking-wider text-jarvis-muted mb-2">
                Full name
              </label>
              <input
                required
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                className="w-full mb-4 rounded-lg bg-jarvis-bg border border-jarvis-border px-3 py-2.5 text-sm outline-none focus:border-jarvis-accent"
              />

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
                className="w-full mb-4 rounded-lg bg-jarvis-bg border border-jarvis-border px-3 py-2.5 text-sm outline-none focus:border-jarvis-accent"
              />

              <label className="block text-xs uppercase tracking-wider text-jarvis-muted mb-2">
                Role
              </label>
              <div className="grid grid-cols-2 gap-2 mb-6">
                {(["owner", "wife"] as const).map((r) => (
                  <button
                    key={r}
                    type="button"
                    onClick={() => setRole(r)}
                    className={`rounded-lg border py-2.5 text-sm capitalize transition ${
                      role === r
                        ? "border-jarvis-accent bg-jarvis-accent/10 text-jarvis-accent"
                        : "border-jarvis-border text-jarvis-muted hover:border-jarvis-muted"
                    }`}
                  >
                    {r}
                  </button>
                ))}
              </div>

              {error && (
                <p className="mb-4 text-sm text-jarvis-danger">{error}</p>
              )}

              <button
                type="submit"
                disabled={loading}
                className="w-full rounded-lg bg-jarvis-accent text-jarvis-bg font-medium py-2.5 text-sm hover:bg-jarvis-accentDim transition disabled:opacity-60"
              >
                {loading ? "Creating…" : "Create account"}
              </button>

              <p className="mt-6 text-center text-sm text-jarvis-muted">
                Already have an account?{" "}
                <Link
                  href="/login"
                  className="text-jarvis-accent hover:underline"
                >
                  Sign in
                </Link>
              </p>
            </form>
          )}
        </div>
      </div>
    </main>
  );
}
