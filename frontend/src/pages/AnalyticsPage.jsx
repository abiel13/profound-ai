import React, { useState, useEffect, useCallback } from "react";
import axios from "axios";
import { useAuth } from "@/context/AuthContext";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import {
  Trophy, TrendingUp, DollarSign, Target, BarChart3, ArrowUp, ArrowDown,
  CheckCircle, XCircle, Clock, Plus, Lightbulb, Sparkles, Calendar
} from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from "recharts";

import { API } from "../config";

function formatValue(n) {
  if (!n) return "$0";
  if (n >= 1000000) return `$${(n / 1000000).toFixed(1)}M`;
  if (n >= 1000) return `$${(n / 1000).toFixed(0)}K`;
  return `$${n.toFixed(0)}`;
}

export default function AnalyticsPage() {
  const { authHeaders } = useAuth();
  const navigate = useNavigate();
  const [analytics, setAnalytics] = useState(null);
  const [insights, setInsights] = useState(null);
  const [outcomes, setOutcomes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [form, setForm] = useState({ opportunity_id: "", outcome: "pending", amount_requested: "", amount_awarded: "", date_submitted: "", date_decided: "", rejection_reason: "", success_notes: "" });
  const [opportunities, setOpportunities] = useState([]);

  const fetchData = useCallback(async () => {
    try {
      const [aRes, iRes, oRes] = await Promise.all([
        axios.get(`${API}/analytics/performance`, { headers: authHeaders() }),
        axios.get(`${API}/analytics/learning-insights`, { headers: authHeaders() }),
        axios.get(`${API}/outcomes`, { headers: authHeaders() })
      ]);
      setAnalytics(aRes.data);
      setInsights(iRes.data);
      setOutcomes(oRes.data);
    } catch { toast.error("Failed to load analytics"); }
    finally { setLoading(false); }
  }, [authHeaders]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const openNewOutcome = async () => {
    try {
      const res = await axios.get(`${API}/saved`, { headers: authHeaders() });
      setOpportunities(res.data.filter(s => s.status === "Submitted" || s.status === "Approved" || s.status === "Rejected"));
    } catch { /* ignore */ }
    setDialogOpen(true);
  };

  const submitOutcome = async () => {
    if (!form.opportunity_id) { toast.error("Select an opportunity"); return; }
    try {
      await axios.post(`${API}/outcomes`, {
        ...form,
        amount_requested: parseFloat(form.amount_requested) || 0,
        amount_awarded: parseFloat(form.amount_awarded) || 0
      }, { headers: authHeaders() });
      toast.success("Outcome recorded");
      setDialogOpen(false);
      setForm({ opportunity_id: "", outcome: "pending", amount_requested: "", amount_awarded: "", date_submitted: "", date_decided: "", rejection_reason: "", success_notes: "" });
      fetchData();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed to save");
    }
  };

  const updateOutcome = async (id, data) => {
    try {
      await axios.put(`${API}/outcomes/${id}`, data, { headers: authHeaders() });
      toast.success("Updated");
      fetchData();
    } catch { toast.error("Failed to update"); }
  };

  if (loading) {
    return (
      <div className="space-y-4 animate-fade-in">
        <div className="h-8 w-48 skeleton-loading rounded-lg" />
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">{[1,2,3,4].map(i => <div key={i} className="h-28 skeleton-loading rounded-xl" />)}</div>
      </div>
    );
  }

  const s = analytics?.summary || {};
  const COLORS = ["#10B981", "#EF4444", "#F59E0B", "#3B82F6", "#8B5CF6"];
  const pieData = [
    { name: "Approved", value: s.approved_count || 0, color: "#10B981" },
    { name: "Rejected", value: s.rejected_count || 0, color: "#EF4444" },
    { name: "Pending", value: s.pending_count || 0, color: "#6B7280" }
  ].filter(d => d.value > 0);

  return (
    <div className="space-y-8 animate-fade-in" data-testid="analytics-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl sm:text-3xl font-semibold text-white tracking-tight" style={{ fontFamily: 'Outfit, sans-serif' }}>
            Funding Performance
          </h1>
          <p className="text-sm text-gray-400 mt-1">Track outcomes, learn from results, improve success rate</p>
        </div>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger asChild>
            <Button onClick={openNewOutcome} data-testid="record-outcome-btn" className="bg-blue-600 hover:bg-blue-500 text-white text-sm">
              <Plus className="w-4 h-4 mr-2" />Record Outcome
            </Button>
          </DialogTrigger>
          <DialogContent className="bg-[#12141A] border-white/10 sm:max-w-lg" data-testid="outcome-dialog">
            <DialogHeader>
              <DialogTitle className="text-white" style={{ fontFamily: 'Outfit' }}>Record Application Outcome</DialogTitle>
            </DialogHeader>
            <div className="space-y-4 mt-2">
              <div className="space-y-2">
                <Label className="text-sm text-gray-300">Opportunity</Label>
                <Select value={form.opportunity_id} onValueChange={v => setForm(p => ({ ...p, opportunity_id: v }))}>
                  <SelectTrigger className="bg-[#0B0C10] border-white/10 text-gray-300 h-11" data-testid="outcome-opp-select">
                    <SelectValue placeholder="Select submitted opportunity" />
                  </SelectTrigger>
                  <SelectContent className="bg-[#1A1D24] border-white/10">
                    {opportunities.map(o => <SelectItem key={o.id} value={o.id} className="text-gray-300 text-xs">{o.title} ({o.donor_name})</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-2">
                  <Label className="text-sm text-gray-300">Outcome</Label>
                  <Select value={form.outcome} onValueChange={v => setForm(p => ({ ...p, outcome: v }))}>
                    <SelectTrigger className="bg-[#0B0C10] border-white/10 text-gray-300 h-10" data-testid="outcome-status-select"><SelectValue /></SelectTrigger>
                    <SelectContent className="bg-[#1A1D24] border-white/10">
                      <SelectItem value="pending" className="text-gray-300">Pending</SelectItem>
                      <SelectItem value="approved" className="text-gray-300">Approved</SelectItem>
                      <SelectItem value="rejected" className="text-gray-300">Rejected</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label className="text-sm text-gray-300">Amount Requested (USD)</Label>
                  <Input type="number" value={form.amount_requested} onChange={e => setForm(p => ({ ...p, amount_requested: e.target.value }))}
                    className="bg-[#0B0C10] border-white/10 text-white h-10" data-testid="outcome-amount-req" />
                </div>
              </div>
              {form.outcome === "approved" && (
                <div className="space-y-2">
                  <Label className="text-sm text-gray-300">Amount Awarded (USD)</Label>
                  <Input type="number" value={form.amount_awarded} onChange={e => setForm(p => ({ ...p, amount_awarded: e.target.value }))}
                    className="bg-[#0B0C10] border-white/10 text-white h-10" data-testid="outcome-amount-awarded" />
                </div>
              )}
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-2">
                  <Label className="text-sm text-gray-300">Date Submitted</Label>
                  <Input type="date" value={form.date_submitted} onChange={e => setForm(p => ({ ...p, date_submitted: e.target.value }))}
                    className="bg-[#0B0C10] border-white/10 text-white h-10" data-testid="outcome-date-submitted" />
                </div>
                <div className="space-y-2">
                  <Label className="text-sm text-gray-300">Date Decided</Label>
                  <Input type="date" value={form.date_decided} onChange={e => setForm(p => ({ ...p, date_decided: e.target.value }))}
                    className="bg-[#0B0C10] border-white/10 text-white h-10" data-testid="outcome-date-decided" />
                </div>
              </div>
              {form.outcome === "rejected" && (
                <div className="space-y-2">
                  <Label className="text-sm text-gray-300">Rejection Reason</Label>
                  <Textarea value={form.rejection_reason} onChange={e => setForm(p => ({ ...p, rejection_reason: e.target.value }))}
                    className="bg-[#0B0C10] border-white/10 text-white resize-none" rows={2} data-testid="outcome-rejection-reason" />
                </div>
              )}
              {form.outcome === "approved" && (
                <div className="space-y-2">
                  <Label className="text-sm text-gray-300">Success Notes</Label>
                  <Textarea value={form.success_notes} onChange={e => setForm(p => ({ ...p, success_notes: e.target.value }))}
                    className="bg-[#0B0C10] border-white/10 text-white resize-none" rows={2} data-testid="outcome-success-notes" />
                </div>
              )}
              <Button onClick={submitOutcome} data-testid="submit-outcome-btn" className="w-full bg-blue-600 hover:bg-blue-500 text-white">
                Record Outcome
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4" data-testid="performance-stats">
        <div className="bg-[#12141A] border border-emerald-500/20 rounded-xl p-5 ai-glow">
          <div className="flex items-center gap-2 mb-2">
            <Trophy className="w-5 h-5 text-emerald-400" />
            <p className="text-xs text-gray-500">Total Secured</p>
          </div>
          <p className="text-2xl font-bold text-emerald-400">{formatValue(s.total_secured)}</p>
          <p className="text-[10px] text-gray-500 mt-1">{s.approved_count} approvals</p>
        </div>
        <div className="bg-[#12141A] border border-white/[0.05] rounded-xl p-5">
          <div className="flex items-center gap-2 mb-2">
            <Target className="w-5 h-5 text-blue-400" />
            <p className="text-xs text-gray-500">Approval Rate</p>
          </div>
          <p className="text-2xl font-bold text-white">{s.approval_rate || 0}%</p>
          <p className="text-[10px] text-gray-500 mt-1">{s.approved_count + s.rejected_count} decided</p>
        </div>
        <div className="bg-[#12141A] border border-white/[0.05] rounded-xl p-5">
          <div className="flex items-center gap-2 mb-2">
            <DollarSign className="w-5 h-5 text-amber-400" />
            <p className="text-xs text-gray-500">Avg Award</p>
          </div>
          <p className="text-2xl font-bold text-white">{formatValue(s.avg_award)}</p>
          <p className="text-[10px] text-gray-500 mt-1">per approval</p>
        </div>
        <div className="bg-[#12141A] border border-white/[0.05] rounded-xl p-5">
          <div className="flex items-center gap-2 mb-2">
            <BarChart3 className="w-5 h-5 text-purple-400" />
            <p className="text-xs text-gray-500">Pipeline vs Actual</p>
          </div>
          <p className="text-2xl font-bold text-white">{formatValue(analytics?.pipeline_vs_actual?.in_pipeline)}</p>
          <p className="text-[10px] text-emerald-400 mt-1">{formatValue(s.total_secured)} secured</p>
        </div>
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Outcome Breakdown */}
        <div className="bg-[#12141A] border border-white/[0.05] rounded-xl p-6" data-testid="outcome-chart">
          <h3 className="text-base font-medium text-white mb-4" style={{ fontFamily: 'Outfit' }}>Outcome Breakdown</h3>
          {pieData.length > 0 ? (
            <div className="flex items-center gap-6">
              <ResponsiveContainer width={140} height={140}>
                <PieChart>
                  <Pie data={pieData} cx="50%" cy="50%" innerRadius={40} outerRadius={65} dataKey="value" stroke="none">
                    {pieData.map((entry, i) => <Cell key={i} fill={entry.color} />)}
                  </Pie>
                </PieChart>
              </ResponsiveContainer>
              <div className="space-y-2">
                {pieData.map(d => (
                  <div key={d.name} className="flex items-center gap-2">
                    <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: d.color }} />
                    <span className="text-xs text-gray-400">{d.name}: {d.value}</span>
                  </div>
                ))}
              </div>
            </div>
          ) : <p className="text-sm text-gray-600 italic">No outcomes recorded yet</p>}
        </div>

        {/* Sector Performance */}
        <div className="bg-[#12141A] border border-white/[0.05] rounded-xl p-6" data-testid="sector-chart">
          <h3 className="text-base font-medium text-white mb-4" style={{ fontFamily: 'Outfit' }}>Sector Performance</h3>
          {(analytics?.top_sectors || []).length > 0 ? (
            <ResponsiveContainer width="100%" height={160}>
              <BarChart data={analytics.top_sectors} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis type="number" tick={{ fill: '#6B7280', fontSize: 10 }} />
                <YAxis dataKey="sector" type="category" width={120} tick={{ fill: '#9CA3AF', fontSize: 10 }} />
                <Tooltip contentStyle={{ backgroundColor: '#1A1D24', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, color: '#F3F4F6' }} />
                <Bar dataKey="wins" name="Approved" fill="#10B981" radius={[0, 4, 4, 0]} />
                <Bar dataKey="total" name="Total" fill="rgba(255,255,255,0.08)" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : <p className="text-sm text-gray-600 italic">No sector data yet</p>}
        </div>
      </div>

      {/* Top Donors */}
      {(analytics?.top_donors || []).length > 0 && (
        <section data-testid="top-donors-section">
          <h3 className="text-base font-medium text-white mb-3" style={{ fontFamily: 'Outfit' }}>Top Performing Donors</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {analytics.top_donors.map((d, i) => (
              <div key={i} className="bg-[#12141A] border border-white/[0.05] rounded-xl p-4">
                <p className="text-sm font-medium text-white">{d.donor_name}</p>
                <p className="text-xs text-gray-500 mt-0.5">{d.donor_type}</p>
                <div className="flex items-center gap-3 mt-2 text-xs">
                  <span className="text-emerald-400">{d.wins}/{d.total} won</span>
                  <span className="text-gray-400">{formatValue(d.secured)} secured</span>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* AI Learning Insights */}
      {insights?.has_data && insights.insights.length > 0 && (
        <section data-testid="learning-insights-section">
          <div className="flex items-center gap-2 mb-3">
            <Lightbulb className="w-4 h-4 text-amber-400" />
            <h3 className="text-base font-medium text-white" style={{ fontFamily: 'Outfit' }}>AI Learning Insights</h3>
          </div>
          <div className="space-y-2">
            {insights.insights.map((ins, i) => (
              <div key={i} className={`flex items-center gap-3 p-3 rounded-xl border ${
                ins.type === 'boost' ? 'border-emerald-500/15 bg-emerald-500/5' :
                ins.type === 'caution' ? 'border-amber-500/15 bg-amber-500/5' :
                'border-blue-500/15 bg-blue-500/5'
              }`} data-testid={`insight-${i}`}>
                {ins.type === 'boost' ? <ArrowUp className="w-4 h-4 text-emerald-400 shrink-0" /> :
                 ins.type === 'caution' ? <ArrowDown className="w-4 h-4 text-amber-400 shrink-0" /> :
                 <Sparkles className="w-4 h-4 text-blue-400 shrink-0" />}
                <span className="text-sm text-gray-300">{ins.message}</span>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Recent Outcomes */}
      {outcomes.length > 0 && (
        <section data-testid="outcomes-list">
          <h3 className="text-base font-medium text-white mb-3" style={{ fontFamily: 'Outfit' }}>Application Outcomes</h3>
          <div className="space-y-2">
            {outcomes.map(o => (
              <div key={o.id} className="bg-[#12141A] border border-white/[0.05] rounded-xl p-4" data-testid={`outcome-${o.id}`}>
                <div className="flex items-center gap-3">
                  {o.outcome === 'approved' ? <CheckCircle className="w-5 h-5 text-emerald-400 shrink-0" /> :
                   o.outcome === 'rejected' ? <XCircle className="w-5 h-5 text-red-400 shrink-0" /> :
                   <Clock className="w-5 h-5 text-gray-400 shrink-0" />}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-white line-clamp-1">{o.title}</p>
                    <p className="text-xs text-gray-400">{o.donor_name} - {o.sector}</p>
                  </div>
                  <div className="text-right shrink-0">
                    <Badge className={`border-0 text-[10px] ${
                      o.outcome === 'approved' ? 'bg-emerald-600/10 text-emerald-400' :
                      o.outcome === 'rejected' ? 'bg-red-600/10 text-red-400' :
                      'bg-gray-600/10 text-gray-400'
                    }`}>{o.outcome}</Badge>
                    {o.amount_awarded > 0 && <p className="text-xs text-emerald-400 mt-0.5">{formatValue(o.amount_awarded)}</p>}
                  </div>
                </div>
                {o.rejection_reason && <p className="text-xs text-red-400/70 mt-2 pl-8">{o.rejection_reason}</p>}
                {o.success_notes && <p className="text-xs text-emerald-400/70 mt-2 pl-8">{o.success_notes}</p>}
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
