import React, { useState, useEffect, useCallback, useMemo } from "react";
import axios from "axios";
import { useAuth } from "@/context/AuthContext";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  ChevronLeft, ChevronRight, Calendar as CalendarIcon, Target,
  Clock, Mail, FileText, CheckCircle, XCircle, MessageSquare,
  AlertTriangle, DollarSign, Zap, ArrowRight, BarChart3, Briefcase
} from "lucide-react";

import { API } from "../config";

const EVENT_CONFIG = {
  deadline:    { icon: Clock,          color: "text-amber-400",   bg: "bg-amber-500/10", border: "border-amber-500/20", label: "Deadline" },
  follow_up:   { icon: Mail,           color: "text-blue-400",    bg: "bg-blue-500/10",   border: "border-blue-500/20",  label: "Follow-Up" },
  submission:  { icon: FileText,       color: "text-purple-400",  bg: "bg-purple-500/10", border: "border-purple-500/20",label: "Submitted" },
  decision:    { icon: CheckCircle,    color: "text-emerald-400", bg: "bg-emerald-500/10",border: "border-emerald-500/20",label: "Decision" },
  interaction: { icon: MessageSquare,  color: "text-cyan-400",    bg: "bg-cyan-500/10",   border: "border-cyan-500/20",  label: "Interaction" },
};

const URGENCY_DOT = {
  critical: "bg-red-500", high: "bg-amber-500", medium: "bg-blue-500",
  success: "bg-emerald-500", danger: "bg-red-500", info: "bg-gray-400",
};

function formatValue(n) {
  if (!n) return "";
  if (n >= 1000000) return `$${(n / 1000000).toFixed(1)}M`;
  if (n >= 1000) return `$${(n / 1000).toFixed(0)}K`;
  return `$${n}`;
}

const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];

export default function CommandCenterPage() {
  const { authHeaders } = useAuth();
  const navigate = useNavigate();
  const [events, setEvents] = useState([]);
  const [weekSummary, setWeekSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [currentMonth, setCurrentMonth] = useState(() => new Date());
  const [selectedDate, setSelectedDate] = useState(null);
  const [filterType, setFilterType] = useState("all");

  const monthStr = useMemo(() => `${currentMonth.getFullYear()}-${String(currentMonth.getMonth() + 1).padStart(2, '0')}`, [currentMonth]);

  const fetchData = useCallback(async () => {
    try {
      const [evRes, wsRes] = await Promise.all([
        axios.get(`${API}/calendar/events`, { headers: authHeaders() }),
        axios.get(`${API}/calendar/week-summary`, { headers: authHeaders() })
      ]);
      setEvents(evRes.data.events);
      setWeekSummary(wsRes.data);
    } catch { toast.error("Failed to load calendar"); }
    finally { setLoading(false); }
  }, [authHeaders]);

  useEffect(() => { fetchData(); }, [fetchData]);

  // Build calendar grid
  const calendarDays = useMemo(() => {
    const year = currentMonth.getFullYear();
    const month = currentMonth.getMonth();
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    let startDay = firstDay.getDay() - 1; // Mon=0
    if (startDay < 0) startDay = 6;
    const days = [];
    // Pad start
    for (let i = 0; i < startDay; i++) {
      const d = new Date(year, month, -startDay + i + 1);
      days.push({ date: d, outside: true });
    }
    // Month days
    for (let i = 1; i <= lastDay.getDate(); i++) {
      days.push({ date: new Date(year, month, i), outside: false });
    }
    // Pad end
    while (days.length % 7 !== 0) {
      const d = new Date(year, month + 1, days.length - startDay - lastDay.getDate() + 1);
      days.push({ date: d, outside: true });
    }
    return days;
  }, [currentMonth]);

  // Map events to dates
  const eventsByDate = useMemo(() => {
    const map = {};
    events.forEach(e => {
      if (!map[e.date]) map[e.date] = [];
      map[e.date].push(e);
    });
    return map;
  }, [events]);

  const prevMonth = () => setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() - 1));
  const nextMonth = () => setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1));
  const goToday = () => { setCurrentMonth(new Date()); setSelectedDate(new Date().toISOString().split('T')[0]); };

  const todayStr = new Date().toISOString().split('T')[0];
  const selectedEvents = selectedDate ? (eventsByDate[selectedDate] || []).filter(e => filterType === "all" || e.type === filterType) : [];

  // Upcoming (next 14 days, sorted)
  const upcoming = useMemo(() => {
    const cutoff = new Date();
    cutoff.setDate(cutoff.getDate() + 14);
    return events
      .filter(e => new Date(e.date) >= new Date(todayStr) && new Date(e.date) <= cutoff)
      .filter(e => filterType === "all" || e.type === filterType)
      .sort((a, b) => a.date.localeCompare(b.date))
      .slice(0, 10);
  }, [events, todayStr, filterType]);

  const ws = weekSummary || {};

  if (loading) {
    return (
      <div className="space-y-4 animate-fade-in">
        <div className="h-8 w-64 skeleton-loading rounded-lg" />
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="lg:col-span-2 h-96 skeleton-loading rounded-xl" />
          <div className="h-96 skeleton-loading rounded-xl" />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in" data-testid="command-center-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-semibold text-white tracking-tight" style={{ fontFamily: 'Outfit, sans-serif' }}>
            Command Center
          </h1>
          <p className="text-sm text-gray-400 mt-1">Your complete funding operations timeline</p>
        </div>
        <Button onClick={goToday} data-testid="today-btn" size="sm" className="bg-blue-600/10 text-blue-400 hover:bg-blue-600/20 text-xs h-8">
          <CalendarIcon className="w-3.5 h-3.5 mr-1.5" />Today
        </Button>
      </div>

      {/* Week Briefing */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3" data-testid="week-briefing">
        <div className="bg-[#12141A] border border-amber-500/15 rounded-xl p-4 flex items-center gap-3">
          <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0" />
          <div>
            <p className="text-lg font-bold text-white">{ws.deadlines_this_week || 0}</p>
            <p className="text-[10px] text-gray-500">Deadlines This Week</p>
          </div>
        </div>
        <div className="bg-[#12141A] border border-white/[0.05] rounded-xl p-4 flex items-center gap-3">
          <Clock className="w-5 h-5 text-blue-400 shrink-0" />
          <div>
            <p className="text-lg font-bold text-white">{ws.deadlines_next_week || 0}</p>
            <p className="text-[10px] text-gray-500">Next Week</p>
          </div>
        </div>
        <div className="bg-[#12141A] border border-white/[0.05] rounded-xl p-4 flex items-center gap-3">
          <Mail className="w-5 h-5 text-purple-400 shrink-0" />
          <div>
            <p className="text-lg font-bold text-white">{ws.pending_followups || 0}</p>
            <p className="text-[10px] text-gray-500">Pending Follow-Ups</p>
          </div>
        </div>
        <div className="bg-[#12141A] border border-white/[0.05] rounded-xl p-4 flex items-center gap-3">
          <Briefcase className="w-5 h-5 text-emerald-400 shrink-0" />
          <div>
            <p className="text-lg font-bold text-white">{ws.in_progress || 0}</p>
            <p className="text-[10px] text-gray-500">In Progress</p>
          </div>
        </div>
      </div>

      {/* Filter bar */}
      <div className="flex gap-2 flex-wrap" data-testid="event-filters">
        {[["all", "All Events"], ["deadline", "Deadlines"], ["follow_up", "Follow-Ups"], ["submission", "Submissions"], ["decision", "Decisions"], ["interaction", "Interactions"]].map(([key, label]) => {
          const count = key === "all" ? events.length : events.filter(e => e.type === key).length;
          const cfg = EVENT_CONFIG[key];
          return (
            <button key={key} onClick={() => setFilterType(key)} data-testid={`filter-${key}`}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                filterType === key ? (cfg ? `${cfg.bg} ${cfg.color}` : 'bg-blue-600/10 text-blue-400') : 'text-gray-500 hover:text-white hover:bg-white/[0.04]'
              }`}>
              {cfg && <cfg.icon className="w-3 h-3" />}
              {label} ({count})
            </button>
          );
        })}
      </div>

      {/* Main layout: Calendar + Sidebar */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        {/* Calendar Grid (3 cols) */}
        <div className="lg:col-span-3 bg-[#12141A] border border-white/[0.05] rounded-xl p-5" data-testid="calendar-grid">
          {/* Month nav */}
          <div className="flex items-center justify-between mb-4">
            <button onClick={prevMonth} data-testid="prev-month" className="p-1.5 rounded-lg text-gray-400 hover:text-white hover:bg-white/[0.06]">
              <ChevronLeft className="w-5 h-5" />
            </button>
            <h2 className="text-base font-medium text-white" style={{ fontFamily: 'Outfit' }}>
              {MONTHS[currentMonth.getMonth()]} {currentMonth.getFullYear()}
            </h2>
            <button onClick={nextMonth} data-testid="next-month" className="p-1.5 rounded-lg text-gray-400 hover:text-white hover:bg-white/[0.06]">
              <ChevronRight className="w-5 h-5" />
            </button>
          </div>

          {/* Day headers */}
          <div className="grid grid-cols-7 gap-px mb-1">
            {DAYS.map(d => <div key={d} className="text-center text-[10px] text-gray-500 py-1 font-medium">{d}</div>)}
          </div>

          {/* Day cells */}
          <div className="grid grid-cols-7 gap-px">
            {calendarDays.map(({ date, outside }, i) => {
              const dateStr = date.toISOString().split('T')[0];
              const dayEvents = (eventsByDate[dateStr] || []).filter(e => filterType === "all" || e.type === filterType);
              const isToday = dateStr === todayStr;
              const isSelected = dateStr === selectedDate;
              const hasDeadline = dayEvents.some(e => e.type === "deadline");
              const hasCritical = dayEvents.some(e => e.urgency === "critical" || e.urgency === "high");
              return (
                <button key={i} onClick={() => setSelectedDate(dateStr === selectedDate ? null : dateStr)}
                  data-testid={`day-${dateStr}`}
                  className={`relative aspect-square flex flex-col items-center justify-start pt-1.5 rounded-lg transition-colors text-xs ${
                    outside ? 'text-gray-700' : 'text-gray-300'
                  } ${isToday ? 'ring-1 ring-blue-500/50' : ''} ${
                    isSelected ? 'bg-blue-600/15 ring-1 ring-blue-500' : 'hover:bg-white/[0.04]'
                  }`}>
                  <span className={`text-xs font-medium ${isToday ? 'text-blue-400' : ''}`}>{date.getDate()}</span>
                  {dayEvents.length > 0 && (
                    <div className="flex gap-0.5 mt-1 flex-wrap justify-center">
                      {dayEvents.slice(0, 3).map((e, j) => (
                        <div key={j} className={`w-1.5 h-1.5 rounded-full ${URGENCY_DOT[e.urgency] || 'bg-gray-500'}`} />
                      ))}
                      {dayEvents.length > 3 && <span className="text-[8px] text-gray-500">+{dayEvents.length - 3}</span>}
                    </div>
                  )}
                </button>
              );
            })}
          </div>
        </div>

        {/* Right sidebar: Selected day events or upcoming */}
        <div className="lg:col-span-2 space-y-4">
          {selectedDate ? (
            <div className="bg-[#12141A] border border-white/[0.05] rounded-xl p-5" data-testid="selected-day-events">
              <h3 className="text-sm font-medium text-white mb-3" style={{ fontFamily: 'Outfit' }}>
                {new Date(selectedDate + 'T12:00:00').toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' })}
              </h3>
              {selectedEvents.length === 0 ? (
                <p className="text-xs text-gray-600 py-4 text-center">No events on this day</p>
              ) : (
                <div className="space-y-2">
                  {selectedEvents.map(event => <EventCard key={event.id} event={event} navigate={navigate} />)}
                </div>
              )}
            </div>
          ) : (
            <div className="bg-[#12141A] border border-white/[0.05] rounded-xl p-5" data-testid="upcoming-events">
              <div className="flex items-center gap-2 mb-3">
                <Zap className="w-4 h-4 text-amber-400" />
                <h3 className="text-sm font-medium text-white" style={{ fontFamily: 'Outfit' }}>Upcoming (14 Days)</h3>
              </div>
              {upcoming.length === 0 ? (
                <p className="text-xs text-gray-600 py-4 text-center">No upcoming events</p>
              ) : (
                <div className="space-y-2">
                  {upcoming.map(event => <EventCard key={event.id} event={event} navigate={navigate} showDate />)}
                </div>
              )}
            </div>
          )}

          {/* Quick Stats */}
          <div className="bg-[#12141A] border border-white/[0.05] rounded-xl p-5">
            <h3 className="text-sm font-medium text-white mb-3" style={{ fontFamily: 'Outfit' }}>Event Types</h3>
            <div className="space-y-2">
              {Object.entries(EVENT_CONFIG).map(([type, cfg]) => {
                const count = events.filter(e => e.type === type).length;
                return (
                  <div key={type} className="flex items-center justify-between text-xs">
                    <div className="flex items-center gap-2">
                      <cfg.icon className={`w-3.5 h-3.5 ${cfg.color}`} />
                      <span className="text-gray-400">{cfg.label}</span>
                    </div>
                    <span className="text-white font-medium">{count}</span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function EventCard({ event, navigate, showDate = false }) {
  const cfg = EVENT_CONFIG[event.type] || EVENT_CONFIG.interaction;
  const Icon = cfg.icon;
  return (
    <div className={`flex items-start gap-3 p-3 rounded-xl border ${cfg.border} ${cfg.bg} cursor-pointer hover:brightness-110 transition-all`}
      onClick={() => event.link && navigate(event.link)} data-testid={`event-${event.id}`}>
      <Icon className={`w-4 h-4 ${cfg.color} shrink-0 mt-0.5`} />
      <div className="flex-1 min-w-0">
        <p className="text-xs font-medium text-white line-clamp-1">{event.title}</p>
        {event.subtitle && <p className="text-[10px] text-gray-400 mt-0.5 line-clamp-1">{event.subtitle}</p>}
        <div className="flex items-center gap-2 mt-1">
          {showDate && <span className="text-[10px] text-gray-500">{event.date}</span>}
          {event.meta?.score > 0 && <span className="text-[10px] text-blue-400">{event.meta.score}%</span>}
          {event.meta?.funding > 0 && <span className="text-[10px] text-gray-400">{formatValue(event.meta.funding)}</span>}
          {event.meta?.label && <Badge className={`text-[8px] border-0 px-1.5 py-0 ${event.meta.label === 'Apply Now' ? 'bg-emerald-600/15 text-emerald-400' : 'bg-white/[0.04] text-gray-400'}`}>{event.meta.label}</Badge>}
          {event.meta?.outcome === 'approved' && <Badge className="text-[8px] border-0 px-1.5 py-0 bg-emerald-600/15 text-emerald-400">Approved</Badge>}
          {event.meta?.outcome === 'rejected' && <Badge className="text-[8px] border-0 px-1.5 py-0 bg-red-600/15 text-red-400">Rejected</Badge>}
        </div>
      </div>
      <div className={`w-1.5 h-1.5 rounded-full shrink-0 mt-2 ${URGENCY_DOT[event.urgency] || 'bg-gray-500'}`} />
    </div>
  );
}
