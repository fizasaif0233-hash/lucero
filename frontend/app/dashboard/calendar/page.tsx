"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import FullCalendar from "@fullcalendar/react";
import dayGridPlugin from "@fullcalendar/daygrid";
import timeGridPlugin from "@fullcalendar/timegrid";
import listPlugin from "@fullcalendar/list";
import interactionPlugin from "@fullcalendar/interaction";
import type { EventClickArg } from "@fullcalendar/core";
import { SecondaryShell } from "@/components/jarvis/SecondaryShell";
import { api } from "@/services/api";
import type { Booking, CalendarEvent } from "@/types";

const STATUS_COLORS: Record<string, string> = {
  pending: "#eab308",
  confirmed: "#22d3ee",
  completed: "#4ade80",
  cancelled: "#f87171",
};

export default function CalendarPage() {
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [bookings, setBookings] = useState<Booking[]>([]);
  const [filter, setFilter] = useState("");
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<CalendarEvent | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [ev, bk] = await Promise.all([
        api.calendarEvents(),
        api.bookings({ search: search || undefined, status: filter || undefined }),
      ]);
      setEvents(ev);
      setBookings(bk);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }, [filter, search]);

  useEffect(() => {
    load();
  }, [load]);

  const fcEvents = useMemo(
    () =>
      events
        .filter((e) => !filter || e.status === filter)
        .filter((e) => {
          if (!search) return true;
          const s = search.toLowerCase();
          const props = e.extendedProps || {};
          return (
            e.title.toLowerCase().includes(s) ||
            String(props.customer_name || "")
              .toLowerCase()
              .includes(s) ||
            String(props.email || "")
              .toLowerCase()
              .includes(s)
          );
        })
        .map((e) => ({
          id: e.id,
          title: e.title,
          start: e.start,
          end: e.end || undefined,
          backgroundColor: STATUS_COLORS[e.status] || "#64748b",
          borderColor: "transparent",
          extendedProps: { ...e.extendedProps, status: e.status },
        })),
    [events, filter, search]
  );

  const today = new Date().toISOString().slice(0, 10);
  const todays = bookings.filter((b) => b.booking_date === today);
  const upcoming = bookings
    .filter(
      (b) =>
        b.booking_date &&
        b.booking_date >= today &&
        ["pending", "confirmed"].includes(b.status)
    )
    .slice(0, 8);

  function onEventClick(info: EventClickArg) {
    setSelected({
      id: info.event.id,
      title: info.event.title,
      start: info.event.start?.toISOString() || "",
      end: info.event.end?.toISOString() || null,
      status: String(info.event.extendedProps.status || ""),
      extendedProps: info.event.extendedProps as Record<string, unknown>,
    });
  }

  return (
    <SecondaryShell title="Calendar">
      <div className="h-full overflow-y-auto p-6 md:p-8">
        <div className="mx-auto max-w-6xl animate-fadeIn">
          <h1 className="font-display text-3xl mb-2 tracking-wide">Calendar</h1>
          <p className="text-sm text-jarvis-muted mb-6">
            Internal booking calendar (PostgreSQL + FullCalendar). No Google
            Calendar.
          </p>

          {error && <p className="mb-4 text-sm text-jarvis-danger">{error}</p>}

          <div className="mb-4 flex flex-wrap gap-2">
            <input
              placeholder="Search bookings"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="rounded-lg border border-jarvis-border bg-jarvis-bg px-3 py-2 text-sm"
            />
            {["", "pending", "confirmed", "completed", "cancelled"].map((s) => (
              <button
                key={s || "all"}
                type="button"
                onClick={() => setFilter(s)}
                className={`rounded-lg px-3 py-1.5 text-sm ${
                  filter === s
                    ? "bg-jarvis-cyan text-jarvis-bg"
                    : "border border-jarvis-border text-jarvis-muted"
                }`}
              >
                {s || "All"}
              </button>
            ))}
          </div>

          <div className="grid gap-6 lg:grid-cols-[1fr_280px]">
            <div className="rounded-2xl border border-jarvis-border bg-jarvis-elevated/40 p-3 lucero-calendar">
              {loading ? (
                <p className="py-20 text-center text-sm text-jarvis-muted">
                  Loading calendar…
                </p>
              ) : (
                <FullCalendar
                  plugins={[
                    dayGridPlugin,
                    timeGridPlugin,
                    listPlugin,
                    interactionPlugin,
                  ]}
                  initialView="dayGridMonth"
                  headerToolbar={{
                    left: "prev,next today",
                    center: "title",
                    right: "dayGridMonth,timeGridWeek,timeGridDay,listWeek",
                  }}
                  height="auto"
                  events={fcEvents}
                  eventClick={onEventClick}
                  nowIndicator
                />
              )}
            </div>

            <aside className="space-y-4">
              <div className="rounded-2xl border border-jarvis-border bg-jarvis-panel/50 p-4">
                <p className="text-xs uppercase tracking-[0.16em] text-jarvis-cyan mb-3">
                  Today&apos;s schedule
                </p>
                {todays.length === 0 ? (
                  <p className="text-sm text-jarvis-muted">Nothing today.</p>
                ) : (
                  <ul className="space-y-2 text-sm">
                    {todays.map((b) => (
                      <li key={b.id}>
                        <span className="text-jarvis-text">
                          {b.booking_time} · {b.customer_name}
                        </span>
                        <span className="block text-xs text-jarvis-muted">
                          {b.status}
                        </span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
              <div className="rounded-2xl border border-jarvis-border bg-jarvis-panel/50 p-4">
                <p className="text-xs uppercase tracking-[0.16em] text-jarvis-cyan mb-3">
                  Upcoming
                </p>
                {upcoming.length === 0 ? (
                  <p className="text-sm text-jarvis-muted">No upcoming bookings.</p>
                ) : (
                  <ul className="space-y-2 text-sm">
                    {upcoming.map((b) => (
                      <li key={b.id}>
                        {b.booking_date} {b.booking_time}
                        <span className="block text-xs text-jarvis-muted">
                          {b.customer_name} · {b.status}
                        </span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </aside>
          </div>
        </div>
      </div>

      {selected && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
          onClick={() => setSelected(null)}
        >
          <div
            className="w-full max-w-md rounded-2xl border border-jarvis-border bg-jarvis-panel p-6"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 className="font-display text-xl mb-2">{selected.title}</h2>
            <p className="text-sm text-jarvis-muted mb-4">
              {selected.start}
              {selected.end ? ` → ${selected.end}` : ""}
            </p>
            <dl className="space-y-2 text-sm">
              <div className="flex justify-between gap-4">
                <dt className="text-jarvis-muted">Status</dt>
                <dd>{selected.status}</dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-jarvis-muted">Customer</dt>
                <dd>
                  {String(selected.extendedProps?.customer_name || "—")}
                </dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-jarvis-muted">Email</dt>
                <dd>{String(selected.extendedProps?.email || "—")}</dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-jarvis-muted">Guests</dt>
                <dd>{String(selected.extendedProps?.guests || "—")}</dd>
              </div>
              {selected.extendedProps?.notes ? (
                <div>
                  <dt className="text-jarvis-muted mb-1">Notes</dt>
                  <dd className="text-jarvis-text">
                    {String(selected.extendedProps.notes)}
                  </dd>
                </div>
              ) : null}
            </dl>
            <button
              type="button"
              onClick={() => setSelected(null)}
              className="mt-6 w-full rounded-lg border border-jarvis-border py-2 text-sm"
            >
              Close
            </button>
          </div>
        </div>
      )}
    </SecondaryShell>
  );
}
