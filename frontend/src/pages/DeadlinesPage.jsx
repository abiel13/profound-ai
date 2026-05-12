import React, { useState, useEffect } from "react";
import axios from "axios";
import { useAuth } from "@/context/AuthContext";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Clock, Calendar, DollarSign, AlertTriangle } from "lucide-react";

import { API } from "../config";

function getDaysUntil(deadline) {
  return Math.ceil((new Date(deadline) - new Date()) / (1000 * 60 * 60 * 24));
}

function getUrgencyInfo(days) {
  if (days <= 7) return { label: "Critical", color: "bg-red-500/10 text-red-400", barColor: "bg-red-500" };
  if (days <= 14) return { label: "Urgent", color: "bg-amber-500/10 text-amber-400", barColor: "bg-amber-500" };
  if (days <= 30) return { label: "Approaching", color: "bg-blue-500/10 text-blue-400", barColor: "bg-blue-500" };
  return { label: "Comfortable", color: "bg-emerald-500/10 text-emerald-400", barColor: "bg-emerald-500" };
}

function formatCurrency(min, max) {
  const fmt = (n) => n >= 1000000 ? `$${(n/1000000).toFixed(1)}M` : n >= 1000 ? `$${(n/1000).toFixed(0)}K` : `$${n}`;
  return `${fmt(min)} - ${fmt(max)}`;
}

export default function DeadlinesPage() {
  const { authHeaders } = useAuth();
  const navigate = useNavigate();
  const [deadlines, setDeadlines] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => { fetchDeadlines(); }, []);

  const fetchDeadlines = async () => {
    try {
      const res = await axios.get(`${API}/deadlines`, { headers: authHeaders() });
      setDeadlines(res.data);
    } catch {
      toast.error("Failed to load deadlines");
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-4 animate-fade-in">
        <div className="h-8 w-48 skeleton-loading rounded-lg" />
        {[1,2,3,4].map(i => <div key={i} className="h-20 skeleton-loading rounded-xl" />)}
      </div>
    );
  }

  const critical = deadlines.filter(d => getDaysUntil(d.deadline) <= 14);
  const upcoming = deadlines.filter(d => { const days = getDaysUntil(d.deadline); return days > 14 && days <= 60; });
  const later = deadlines.filter(d => getDaysUntil(d.deadline) > 60);

  return (
    <div className="space-y-8 animate-fade-in" data-testid="deadlines-page">
      <div>
        <h1 className="text-2xl sm:text-3xl font-semibold text-white tracking-tight" style={{ fontFamily: 'Outfit, sans-serif' }}>
          Deadline Tracker
        </h1>
        <p className="text-sm text-gray-400 mt-1">Monitor upcoming grant deadlines and manage your timeline</p>
      </div>

      {/* Summary */}
      <div className="flex gap-4 flex-wrap">
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-red-500/10">
          <AlertTriangle className="w-3.5 h-3.5 text-red-400" />
          <span className="text-xs text-red-400 font-medium">{critical.length} critical</span>
        </div>
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-amber-500/10">
          <Clock className="w-3.5 h-3.5 text-amber-400" />
          <span className="text-xs text-amber-400 font-medium">{upcoming.length} upcoming</span>
        </div>
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-emerald-500/10">
          <Calendar className="w-3.5 h-3.5 text-emerald-400" />
          <span className="text-xs text-emerald-400 font-medium">{later.length} comfortable</span>
        </div>
      </div>

      {/* Critical & Urgent */}
      {critical.length > 0 && (
        <section data-testid="critical-deadlines">
          <h2 className="text-base font-medium text-red-400 mb-3 flex items-center gap-2" style={{ fontFamily: 'Outfit, sans-serif' }}>
            <AlertTriangle className="w-4 h-4" />
            Critical - Within 14 Days
          </h2>
          <div className="space-y-2">
            {critical.map(opp => <DeadlineRow key={opp.id} opp={opp} navigate={navigate} />)}
          </div>
        </section>
      )}

      {/* Upcoming */}
      {upcoming.length > 0 && (
        <section data-testid="upcoming-deadlines">
          <h2 className="text-base font-medium text-amber-400 mb-3 flex items-center gap-2" style={{ fontFamily: 'Outfit, sans-serif' }}>
            <Clock className="w-4 h-4" />
            Upcoming - 15 to 60 Days
          </h2>
          <div className="space-y-2">
            {upcoming.map(opp => <DeadlineRow key={opp.id} opp={opp} navigate={navigate} />)}
          </div>
        </section>
      )}

      {/* Later */}
      {later.length > 0 && (
        <section data-testid="later-deadlines">
          <h2 className="text-base font-medium text-emerald-400 mb-3 flex items-center gap-2" style={{ fontFamily: 'Outfit, sans-serif' }}>
            <Calendar className="w-4 h-4" />
            Comfortable - 60+ Days
          </h2>
          <div className="space-y-2">
            {later.map(opp => <DeadlineRow key={opp.id} opp={opp} navigate={navigate} />)}
          </div>
        </section>
      )}

      {deadlines.length === 0 && (
        <div className="text-center py-16">
          <Clock className="w-12 h-12 text-gray-600 mx-auto mb-3" />
          <p className="text-gray-400">No upcoming deadlines</p>
        </div>
      )}
    </div>
  );
}

function DeadlineRow({ opp, navigate }) {
  const days = getDaysUntil(opp.deadline);
  const urgency = getUrgencyInfo(days);
  const maxDays = 120;
  const progressWidth = Math.max(5, Math.min(100, ((maxDays - days) / maxDays) * 100));

  return (
    <div
      className="bg-[#12141A] border border-white/[0.05] rounded-xl p-4 card-hover cursor-pointer"
      onClick={() => navigate(`/opportunity/${opp.id}`)}
      data-testid={`deadline-${opp.id}`}
    >
      <div className="flex items-center justify-between gap-4 mb-3">
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-medium text-white hover:text-blue-400 transition-colors line-clamp-1">
            {opp.title}
          </h3>
          <div className="flex items-center gap-3 mt-1">
            <span className="text-xs text-gray-400">{opp.donor_name}</span>
            <span className="text-xs text-gray-500 flex items-center gap-1">
              <DollarSign className="w-3 h-3" />
              {formatCurrency(opp.funding_min, opp.funding_max)}
            </span>
          </div>
        </div>
        <div className="text-right shrink-0">
          <Badge className={`${urgency.color} border-0 text-[10px] mb-1`}>{urgency.label}</Badge>
          <p className="text-xs text-gray-400">{opp.deadline}</p>
          <p className={`text-sm font-bold ${days <= 7 ? 'text-red-400' : days <= 14 ? 'text-amber-400' : 'text-white'}`}>
            {days}d left
          </p>
        </div>
      </div>
      {/* Progress bar */}
      <div className="h-1.5 rounded-full bg-white/[0.04] overflow-hidden">
        <div className={`h-full rounded-full ${urgency.barColor} transition-all duration-500`} style={{ width: `${progressWidth}%` }} />
      </div>
    </div>
  );
}
