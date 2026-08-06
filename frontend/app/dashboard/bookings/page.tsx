"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { Loader2, CalendarCheck } from "lucide-react";
import { SecondaryShell } from "@/components/jarvis/SecondaryShell";
import { api } from "@/services/api";
import type { Booking } from "@/types";
import { formatRelativeTime } from "@/lib/utils";

const STATUSES = ["", "pending", "confirmed", "completed", "cancelled"] as const;

export default function BookingsPage() {
  const [bookings, setBookings] = useState<Booking[]>([]);
  const [status, setStatus] = useState("");
  const [search, setSearch] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [summary, setSummary] = useState<string | null>(null);
  const [pendingPayload, setPendingPayload] = useState<Record<
    string,
    unknown
  > | null>(null);

  const [form, setForm] = useState({
    customer_name: "",
    email: "",
    phone: "",
    booking_date: "",
    booking_time: "",
    guests: 2,
    notes: "",
  });

  const load = useCallback(async () => {
    try {
      setBookings(
        await api.bookings({
          status: status || undefined,
          search: search || undefined,
        })
      );
    } catch (err) {
      setError((err as Error).message);
    }
  }, [status, search]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(null), 3000);
    return () => clearTimeout(t);
  }, [toast]);

  async function onSummary(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const res = await api.bookingSummary({
        ...form,
        guests: Number(form.guests),
      });
      setSummary(res.summary);
      setPendingPayload(res.payload);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function approveCreate() {
    if (!pendingPayload) return;
    setBusy(true);
    try {
      await api.createBooking({ ...pendingPayload, approve: true });
      setSummary(null);
      setPendingPayload(null);
      setForm({
        customer_name: "",
        email: "",
        phone: "",
        booking_date: "",
        booking_time: "",
        guests: 2,
        notes: "",
      });
      setToast("Booking confirmed — confirmation email draft created");
      await load();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function setBookingStatus(id: string, next: string) {
    setBusy(true);
    try {
      await api.updateBooking(id, { status: next });
      setToast(`Marked ${next}`);
      await load();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <SecondaryShell title="Bookings">
      <div className="h-full overflow-y-auto p-6 md:p-8">
        <div className="mx-auto max-w-4xl animate-fadeIn">
          <h1 className="font-display text-3xl mb-2 tracking-wide">
            Tasting bookings
          </h1>
          <p className="text-sm text-jarvis-muted mb-8">
            Collect details → review summary → approve. Links CRM, calendar, and
            confirmation email draft.
          </p>

          {toast && (
            <div className="mb-4 rounded-xl border border-jarvis-cyan/40 bg-jarvis-cyan/10 px-4 py-2 text-sm text-jarvis-cyan">
              {toast}
            </div>
          )}
          {error && <p className="mb-4 text-sm text-jarvis-danger">{error}</p>}

          <form
            onSubmit={onSummary}
            className="mb-8 rounded-2xl border border-jarvis-border bg-jarvis-elevated/40 p-5 grid gap-3 sm:grid-cols-2"
          >
            <input
              required
              placeholder="Customer name"
              value={form.customer_name}
              onChange={(e) =>
                setForm((f) => ({ ...f, customer_name: e.target.value }))
              }
              className="rounded-lg border border-jarvis-border bg-jarvis-bg px-3 py-2 text-sm"
            />
            <input
              required
              type="email"
              placeholder="Email"
              value={form.email}
              onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
              className="rounded-lg border border-jarvis-border bg-jarvis-bg px-3 py-2 text-sm"
            />
            <input
              placeholder="Phone"
              value={form.phone}
              onChange={(e) => setForm((f) => ({ ...f, phone: e.target.value }))}
              className="rounded-lg border border-jarvis-border bg-jarvis-bg px-3 py-2 text-sm"
            />
            <input
              required
              type="number"
              min={1}
              placeholder="Guests"
              value={form.guests}
              onChange={(e) =>
                setForm((f) => ({ ...f, guests: Number(e.target.value) }))
              }
              className="rounded-lg border border-jarvis-border bg-jarvis-bg px-3 py-2 text-sm"
            />
            <input
              required
              type="date"
              value={form.booking_date}
              onChange={(e) =>
                setForm((f) => ({ ...f, booking_date: e.target.value }))
              }
              className="rounded-lg border border-jarvis-border bg-jarvis-bg px-3 py-2 text-sm"
            />
            <input
              required
              type="time"
              value={form.booking_time}
              onChange={(e) =>
                setForm((f) => ({ ...f, booking_time: e.target.value }))
              }
              className="rounded-lg border border-jarvis-border bg-jarvis-bg px-3 py-2 text-sm"
            />
            <textarea
              placeholder="Notes"
              value={form.notes}
              onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))}
              className="sm:col-span-2 rounded-lg border border-jarvis-border bg-jarvis-bg px-3 py-2 text-sm"
              rows={2}
            />
            <button
              type="submit"
              disabled={busy}
              className="sm:col-span-2 inline-flex items-center justify-center gap-2 rounded-lg bg-jarvis-cyan px-4 py-2 text-sm font-medium text-jarvis-bg disabled:opacity-50"
            >
              {busy && <Loader2 size={14} className="animate-spin" />}
              Review summary
            </button>
          </form>

          {summary && (
            <div className="mb-8 rounded-2xl border border-jarvis-cyan/40 bg-jarvis-cyan/5 p-5">
              <p className="text-xs uppercase tracking-[0.16em] text-jarvis-cyan mb-2">
                Summary — approve to save
              </p>
              <pre className="whitespace-pre-wrap text-sm font-mono text-jarvis-text mb-4">
                {summary}
              </pre>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  disabled={busy}
                  onClick={approveCreate}
                  className="rounded-lg bg-jarvis-cyan px-4 py-2 text-sm text-jarvis-bg"
                >
                  Approve & save
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setSummary(null);
                    setPendingPayload(null);
                  }}
                  className="rounded-lg border border-jarvis-border px-4 py-2 text-sm text-jarvis-muted"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}

          <div className="mb-4 flex flex-wrap gap-2">
            <input
              placeholder="Search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="rounded-lg border border-jarvis-border bg-jarvis-bg px-3 py-2 text-sm"
            />
            <select
              value={status}
              onChange={(e) => setStatus(e.target.value)}
              className="rounded-lg border border-jarvis-border bg-jarvis-bg px-3 py-2 text-sm"
            >
              {STATUSES.map((s) => (
                <option key={s || "all"} value={s}>
                  {s ? s : "All statuses"}
                </option>
              ))}
            </select>
          </div>

          {bookings.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-jarvis-border py-16 text-center text-jarvis-muted">
              <CalendarCheck className="mx-auto mb-3 opacity-50" size={28} />
              <p className="text-sm">No bookings yet.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {bookings.map((b) => (
                <div
                  key={b.id}
                  className="rounded-xl border border-jarvis-border bg-jarvis-elevated/60 px-4 py-3"
                >
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div>
                      <p className="font-medium">
                        {b.customer_name || b.title}
                      </p>
                      <p className="text-sm text-jarvis-muted">
                        {b.booking_date} {b.booking_time} · {b.guests} guests ·{" "}
                        {b.email}
                      </p>
                      {b.notes && (
                        <p className="mt-1 text-xs text-jarvis-muted">
                          {b.notes}
                        </p>
                      )}
                      <p className="mt-1 text-[10px] text-jarvis-muted">
                        {b.created_at
                          ? formatRelativeTime(b.created_at)
                          : ""}
                      </p>
                    </div>
                    <div className="flex flex-col items-end gap-2">
                      <span className="rounded-md border border-jarvis-border px-2 py-0.5 text-[10px] uppercase text-jarvis-muted">
                        {b.status}
                      </span>
                      <div className="flex flex-wrap justify-end gap-1">
                        {b.status === "pending" && (
                          <button
                            type="button"
                            disabled={busy}
                            onClick={() => setBookingStatus(b.id, "confirmed")}
                            className="rounded-md bg-jarvis-cyan/20 px-2 py-1 text-[11px] text-jarvis-cyan"
                          >
                            Confirm
                          </button>
                        )}
                        {b.status === "confirmed" && (
                          <button
                            type="button"
                            disabled={busy}
                            onClick={() => setBookingStatus(b.id, "completed")}
                            className="rounded-md border border-jarvis-border px-2 py-1 text-[11px]"
                          >
                            Complete
                          </button>
                        )}
                        {b.status !== "cancelled" && (
                          <button
                            type="button"
                            disabled={busy}
                            onClick={() => setBookingStatus(b.id, "cancelled")}
                            className="rounded-md border border-jarvis-danger/40 px-2 py-1 text-[11px] text-jarvis-danger"
                          >
                            Cancel
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </SecondaryShell>
  );
}
