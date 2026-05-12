import React, { useState, useEffect, useCallback } from "react";
import axios from "axios";
import { useAuth } from "@/context/AuthContext";
import OpportunityCard from "@/components/OpportunityCard";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import {
  Globe2, TrendingUp, Clock, Bookmark, Plus, Search, AlertTriangle,
  Sparkles, Loader2, DollarSign, Zap, Target, BarChart3, ArrowRight,
  Radio, FileCheck, Rocket, Activity, Calendar, Trophy
} from "lucide-react";

import { API } from "../config";

function formatValue(n) {
  if (!n) return "$0";
  if (n >= 1000000) return `$${(n / 1000000).toFixed(1)}M`;
  if (n >= 1000) return `$${(n / 1000).toFixed(0)}K`;
  return `$${n}`;
}

export default function DashboardPage() {
  const { authHeaders } = useAuth();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [savedIds, setSavedIds] = useState(new Set());
  const [bulkRunning, setBulkRunning] = useState(false);
  const [bulkProgress, setBulkProgress] = useState({ total: 0, processed: 0 });
  const [extras, setExtras] = useState(null);
  const [queueRunning, setQueueRunning] = useState(false);
  const [perfData, setPerfData] = useState(null);
  const [autoSummary, setAutoSummary] = useState(null);

  const fetchDashboard = useCallback(async () => {
    try {
      const [dashRes, savedRes, extrasRes, perfRes] = await Promise.all([
        axios.get(`${API}/opportunities/dashboard`, { headers: authHeaders() }),
        axios.get(`${API}/saved`, { headers: authHeaders() }),
        axios.get(`${API}/dashboard/extras`, { headers: authHeaders() }),
        axios.get(`${API}/analytics/performance`, { headers: authHeaders() }).catch(() => ({ data: null }))
      ]);
      setData(dashRes.data);
      setSavedIds(new Set(savedRes.data.map(s => s.id)));
      setExtras(extrasRes.data);
      setPerfData(perfRes.data);
    } catch {
      toast.error("Failed to load dashboard");
    } finally {
      setLoading(false);
    }
  }, [authHeaders]);

  useEffect(() => { fetchDashboard(); }, [fetchDashboard]);

  // Poll bulk analysis status
  useEffect(() => {
    if (!bulkRunning) return;
    const interval = setInterval(async () => {
      try {
        const res = await axios.get(`${API}/ai/bulk-status`, { headers: authHeaders() });
        setBulkProgress({ total: res.data.total, processed: res.data.processed });
        if (!res.data.running) {
          setBulkRunning(false);
          toast.success(`AI analysis complete: ${res.data.processed} opportunities scored`);
          fetchDashboard();
        }
      } catch { /* ignore */ }
    }, 3000);
    return () => clearInterval(interval);
  }, [bulkRunning, authHeaders, fetchDashboard]);

  // V12.3 — fetch automation summary for the Automation Center widget
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await axios.get(`${API}/automation/summary`, { headers: authHeaders() });
        if (!cancelled) setAutoSummary(res.data);
      } catch { /* ignore */ }
    })();
    return () => { cancelled = true; };
  }, [authHeaders]);

  const handleSave = async (oppId) => {
    try {
      await axios.post(`${API}/saved`, { opportunity_id: oppId }, { headers: authHeaders() });
      setSavedIds(prev => new Set([...prev, oppId]));
      toast.success("Opportunity saved");
    } catch { toast.error("Failed to save"); }
  };

  const runBulkAnalysis = async () => {
    setBulkRunning(true);
    setBulkProgress({ total: 0, processed: 0 });
    try {
      await axios.post(`${API}/ai/bulk-analyze`, {}, { headers: authHeaders() });
      toast.info("AI analysis started - scoring all opportunities...");
    } catch {
      toast.error("Failed to start analysis");
      setBulkRunning(false);
    }
  };

  const runSmartQueue = async () => {
    setQueueRunning(true);
    try {
      await axios.post(`${API}/queue/generate`, {}, { headers: authHeaders() });
      toast.info("Smart Apply Queue generating - selecting top opportunities and drafting proposals...");
      // Poll for completion
      const poll = setInterval(async () => {
        try {
          const res = await axios.get(`${API}/queue/status`, { headers: authHeaders() });
          if (!res.data.generating) {
            clearInterval(poll);
            setQueueRunning(false);
            toast.success("Smart Apply Queue ready - priority applications prepared");
            fetchDashboard();
          }
        } catch { /* ignore */ }
      }, 5000);
    } catch {
      toast.error("Failed to start queue");
      setQueueRunning(false);
    }
  };

  const triggerScan = async () => {
    try {
      await axios.post(`${API}/monitoring/trigger`, {}, { headers: authHeaders() });
      toast.info("Monitoring scan triggered");
    } catch { toast.error("Scan failed"); }
  };

  if (loading) {
    return (
      <div className="space-y-6 animate-fade-in">
        <div className="h-8 w-48 skeleton-loading rounded-lg" />
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {[1,2,3,4].map(i => <div key={i} className="h-28 skeleton-loading rounded-xl" />)}
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1,2,3,4,5,6].map(i => <div key={i} className="h-48 skeleton-loading rounded-xl" />)}
        </div>
      </div>
    );
  }

  const stats = data?.stats || {};
  const pipeline = data?.pipeline || {};
  const actions = data?.actions || [];

  return (
    <div className="space-y-8 animate-fade-in" data-testid="dashboard-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-semibold text-white tracking-tight" style={{ fontFamily: 'Outfit, sans-serif' }}>
            Dashboard
          </h1>
          <p className="text-sm text-gray-400 mt-1">International funding opportunities for your organization</p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          {extras?.monitoring?.active && (
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20" data-testid="monitoring-indicator">
              <Radio className="w-3 h-3 text-emerald-400 animate-pulse" />
              <span className="text-[10px] text-emerald-400 font-medium">24/7 Active</span>
            </div>
          )}
          <Button onClick={runSmartQueue} disabled={queueRunning} data-testid="smart-queue-btn" size="sm"
            className="bg-emerald-600 hover:bg-emerald-500 text-white text-xs h-9">
            {queueRunning ? <Loader2 className="w-3.5 h-3.5 mr-1.5 animate-spin" /> : <Rocket className="w-3.5 h-3.5 mr-1.5" />}
            {queueRunning ? "Generating..." : "Smart Queue"}
          </Button>
          <Button onClick={runBulkAnalysis} disabled={bulkRunning} data-testid="bulk-analyze-btn" size="sm"
            className="bg-purple-600 hover:bg-purple-500 text-white text-xs h-9">
            {bulkRunning ? <Loader2 className="w-3.5 h-3.5 mr-1.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5 mr-1.5" />}
            {bulkRunning ? "Analyzing..." : "AI Score All"}
          </Button>
          <Button onClick={() => navigate("/search")} data-testid="search-opportunities-btn" size="sm" className="bg-blue-600 hover:bg-blue-500 text-white text-xs h-9">
            <Search className="w-3.5 h-3.5 mr-1.5" />Search
          </Button>
        </div>
      </div>

      {/* V12.3 Automation Center */}
      <div className="bg-[#12141A] border border-white/[0.05] rounded-xl p-5" data-testid="automation-center">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Zap className="w-4 h-4 text-amber-400" />
            <h2 className="text-sm font-semibold text-white uppercase tracking-wider" style={{ fontFamily: "Outfit" }}>Automation Center</h2>
          </div>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-4">
          <MetricTile label="New grants" value={autoSummary?.grants_new ?? 0} tone="blue" />
          <MetricTile label="High-fit grants" value={autoSummary?.grants_high_fit ?? 0} tone="emerald" />
          <MetricTile label="Donor prospects" value={autoSummary?.donors_new ?? 0} tone="purple" />
          <MetricTile label="Drafts waiting" value={autoSummary?.drafts_pending ?? 0} tone="amber" />
          <MetricTile label="Follow-ups due" value={autoSummary?.follow_ups_due ?? 0} tone="rose" />
        </div>
        <div className="flex flex-wrap gap-2">
          <Button size="sm" onClick={() => navigate("/grant-scanner")} className="bg-blue-600 hover:bg-blue-500 text-white text-xs" data-testid="open-grant-scanner">
            <Radio className="w-3.5 h-3.5 mr-1.5" />Scan Grants
          </Button>
          <Button size="sm" onClick={() => navigate("/donor-finder")} className="bg-emerald-600 hover:bg-emerald-500 text-white text-xs" data-testid="open-donor-finder">
            <Target className="w-3.5 h-3.5 mr-1.5" />Generate Donor List
          </Button>
          <Button size="sm" onClick={() => navigate("/email-drafts")} className="bg-purple-600 hover:bg-purple-500 text-white text-xs" data-testid="open-email-drafts">
            <FileCheck className="w-3.5 h-3.5 mr-1.5" />Generate Email Drafts
          </Button>
        </div>
      </div>

      {/* Bulk Analysis Progress */}
      {bulkRunning && (
        <div className="bg-purple-600/10 border border-purple-500/20 rounded-xl p-4" data-testid="bulk-progress">
          <div className="flex items-center gap-3 mb-2">
            <Loader2 className="w-4 h-4 text-purple-400 animate-spin" />
            <span className="text-sm text-purple-300 font-medium">AI Analysis in Progress</span>
            <span className="text-xs text-purple-400 ml-auto">{bulkProgress.processed}/{bulkProgress.total}</span>
          </div>
          <Progress value={bulkProgress.total ? (bulkProgress.processed / bulkProgress.total) * 100 : 0} className="h-1.5" />
        </div>
      )}

      {/* Pipeline Value + Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4" data-testid="dashboard-stats">
        <div className="bg-[#12141A] border border-blue-500/20 rounded-xl p-5 ai-glow">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-9 h-9 rounded-lg bg-blue-600/10 flex items-center justify-center">
              <DollarSign className="w-5 h-5 text-blue-500" />
            </div>
            <div>
              <p className="text-xs text-gray-500">Pipeline Value</p>
              <p className="text-xl font-bold text-white">{formatValue(pipeline.total)}</p>
            </div>
          </div>
          <p className="text-[10px] text-gray-500">{formatValue(pipeline.all_value)} total available</p>
        </div>
        <div className="bg-[#12141A] border border-white/[0.05] rounded-xl p-5">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-9 h-9 rounded-lg bg-emerald-600/10 flex items-center justify-center">
              <Globe2 className="w-5 h-5 text-emerald-500" />
            </div>
            <div>
              <p className="text-xs text-gray-500">Opportunities</p>
              <p className="text-xl font-bold text-white">{stats.total_opportunities || 0}</p>
            </div>
          </div>
          <p className="text-[10px] text-gray-500">{stats.analyzed_count || 0} AI scored</p>
        </div>
        <div className="bg-[#12141A] border border-white/[0.05] rounded-xl p-5">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-9 h-9 rounded-lg bg-amber-600/10 flex items-center justify-center">
              <Clock className="w-5 h-5 text-amber-500" />
            </div>
            <div>
              <p className="text-xs text-gray-500">Expiring Soon</p>
              <p className="text-xl font-bold text-white">{stats.expiring_soon_count || 0}</p>
            </div>
          </div>
          <p className="text-[10px] text-gray-500">Within 30 days</p>
        </div>
        <div className="bg-[#12141A] border border-white/[0.05] rounded-xl p-5">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-9 h-9 rounded-lg bg-purple-600/10 flex items-center justify-center">
              <Target className="w-5 h-5 text-purple-500" />
            </div>
            <div>
              <p className="text-xs text-gray-500">Apply Now</p>
              <p className="text-xl font-bold text-white">{stats.apply_now_count || 0}</p>
            </div>
          </div>
          <p className="text-[10px] text-gray-500">80%+ match score</p>
        </div>
      </div>

      {/* Pipeline Stage Breakdown */}
      {Object.keys(pipeline.stages || {}).length > 0 && (
        <section data-testid="pipeline-section">
          <div className="flex items-center gap-2 mb-4">
            <BarChart3 className="w-4 h-4 text-blue-500" />
            <h2 className="text-lg font-medium text-white" style={{ fontFamily: 'Outfit, sans-serif' }}>Funding Pipeline</h2>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            {["Reviewing", "Preparing", "Drafting", "Ready to Submit", "Submitted", "Approved"].map(stage => {
              const s = (pipeline.stages || {})[stage];
              if (!s) return null;
              const colors = {
                Reviewing: "border-amber-500/20 bg-amber-500/5",
                Preparing: "border-purple-500/20 bg-purple-500/5",
                Drafting: "border-blue-500/20 bg-blue-500/5",
                "Ready to Submit": "border-cyan-500/20 bg-cyan-500/5",
                Submitted: "border-emerald-500/20 bg-emerald-500/5",
                Approved: "border-green-500/20 bg-green-500/5"
              };
              return (
                <div key={stage} className={`rounded-xl border p-4 ${colors[stage] || "border-white/5"}`}>
                  <p className="text-[10px] text-gray-500 uppercase tracking-wider">{stage}</p>
                  <p className="text-lg font-bold text-white mt-1">{formatValue(s.total_max)}</p>
                  <p className="text-xs text-gray-400">{s.count} {s.count === 1 ? "grant" : "grants"}</p>
                </div>
              );
            })}
          </div>
        </section>
      )}

      {/* Funding Performance Summary */}
      {perfData?.summary?.total_secured > 0 && (
        <div className="flex items-center gap-6 p-4 bg-[#12141A] border border-emerald-500/15 rounded-xl cursor-pointer hover:bg-white/[0.02]"
          onClick={() => navigate("/analytics")} data-testid="performance-summary-bar">
          <div className="flex items-center gap-2">
            <Trophy className="w-5 h-5 text-emerald-400" />
            <span className="text-sm font-medium text-white">Funding Secured</span>
          </div>
          <span className="text-lg font-bold text-emerald-400">{formatValue(perfData.summary.total_secured)}</span>
          <div className="w-px h-5 bg-white/10" />
          <span className="text-xs text-gray-400">{perfData.summary.approval_rate}% approval rate</span>
          <div className="w-px h-5 bg-white/10" />
          <span className="text-xs text-gray-400">{perfData.summary.approved_count} approved</span>
          <ArrowRight className="w-3.5 h-3.5 text-gray-500 ml-auto" />
        </div>
      )}

      {/* Priority Applications (Smart Queue) */}
      {extras?.priority_apps?.length > 0 && (
        <section data-testid="priority-apps-section">
          <div className="flex items-center gap-2 mb-4">
            <Rocket className="w-4 h-4 text-emerald-400" />
            <h2 className="text-lg font-medium text-white" style={{ fontFamily: 'Outfit, sans-serif' }}>This Week's Priority Applications</h2>
            <Badge variant="secondary" className="text-[10px] bg-emerald-600/10 text-emerald-400 border-0">Smart Queue</Badge>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {extras.priority_apps.map(app => {
              const days = Math.ceil((new Date(app.deadline) - new Date()) / 86400000);
              return (
                <div key={app.id} className="bg-[#12141A] border border-emerald-500/10 rounded-xl p-4 card-hover cursor-pointer"
                  onClick={() => navigate(`/opportunity/${app.opportunity_id}`)} data-testid={`priority-${app.id}`}>
                  <div className="flex items-start justify-between gap-2 mb-2">
                    <div className="flex-1 min-w-0">
                      <h3 className="text-sm font-medium text-white line-clamp-1">{app.title}</h3>
                      <p className="text-xs text-gray-400 mt-0.5">{app.donor_name}</p>
                    </div>
                    <div className="shrink-0 w-9 h-9 rounded-full flex items-center justify-center text-xs font-bold border-2 border-emerald-500 text-emerald-400">
                      {app.ai_match_score}%
                    </div>
                  </div>
                  <div className="flex items-center gap-3 text-xs mb-2">
                    <span className="text-gray-400 flex items-center gap-1"><DollarSign className="w-3 h-3" />{formatValue(app.funding_max)}</span>
                    <span className={`flex items-center gap-1 ${days <= 7 ? 'text-red-400' : days <= 14 ? 'text-amber-400' : 'text-gray-400'}`}>
                      <Calendar className="w-3 h-3" />{days}d left
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <Badge className={`text-[10px] border-0 ${app.status === 'draft_ready' ? 'bg-emerald-600/10 text-emerald-400' : 'bg-blue-600/10 text-blue-400'}`}>
                      {app.status === 'draft_ready' ? 'Draft Ready' : 'Queued'}
                    </Badge>
                    <button className="text-xs text-blue-400 hover:text-blue-300" onClick={(e) => { e.stopPropagation(); navigate(`/proposals?opp=${app.opportunity_id}`); }}>
                      Review Draft
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      )}

      {/* Auto-Generated Drafts Ready */}
      {extras?.drafts_ready?.length > 0 && (
        <section data-testid="drafts-ready-section">
          <div className="flex items-center gap-2 mb-4">
            <FileCheck className="w-4 h-4 text-cyan-400" />
            <h2 className="text-lg font-medium text-white" style={{ fontFamily: 'Outfit, sans-serif' }}>Auto-Generated Drafts</h2>
            <Badge variant="secondary" className="text-[10px] bg-cyan-600/10 text-cyan-400 border-0">{extras.drafts_ready.length}</Badge>
          </div>
          <div className="space-y-2">
            {extras.drafts_ready.map(draft => (
              <div key={draft.proposal_id} className="flex items-center gap-3 bg-[#12141A] border border-white/[0.05] rounded-xl p-4 cursor-pointer hover:bg-white/[0.02]"
                onClick={() => navigate(`/proposals?opp=${draft.id}`)} data-testid={`draft-${draft.proposal_id}`}>
                <FileCheck className="w-4 h-4 text-cyan-400 shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-white line-clamp-1">{draft.title}</p>
                  <p className="text-xs text-gray-500">{draft.donor_name} - {draft.ai_match_score}% match</p>
                </div>
                <Badge className="bg-cyan-600/10 text-cyan-400 border-0 text-[10px]">Review Draft</Badge>
                <ArrowRight className="w-3.5 h-3.5 text-gray-500" />
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Monitoring Status Bar */}
      <div className="flex items-center gap-4 p-3 bg-[#12141A] border border-white/[0.05] rounded-xl" data-testid="monitoring-bar">
        <div className="flex items-center gap-2">
          <Activity className={`w-4 h-4 ${extras?.monitoring?.active ? 'text-emerald-400' : 'text-gray-500'}`} />
          <span className="text-xs text-gray-400">Monitoring: {extras?.monitoring?.active ? 'Active' : 'Inactive'}</span>
        </div>
        <div className="w-px h-4 bg-white/10" />
        <span className="text-xs text-gray-500">
          {extras?.monitoring?.scans_completed || 0} scans completed
        </span>
        {extras?.monitoring?.last_scan && (
          <>
            <div className="w-px h-4 bg-white/10" />
            <span className="text-xs text-gray-500">Last: {extras.monitoring.last_scan.status || 'N/A'}</span>
          </>
        )}
        <button onClick={triggerScan} className="ml-auto text-xs text-blue-400 hover:text-blue-300" data-testid="trigger-scan-btn">
          Scan Now
        </button>
      </div>

      {/* AI Recommended Actions */}
      {actions.length > 0 && (
        <section data-testid="ai-actions-section">
          <div className="flex items-center gap-2 mb-4">
            <Zap className="w-4 h-4 text-amber-400" />
            <h2 className="text-lg font-medium text-white" style={{ fontFamily: 'Outfit, sans-serif' }}>AI Recommended Actions</h2>
          </div>
          <div className="space-y-2">
            {actions.map((action, i) => {
              const colors = { high: "border-emerald-500/20 bg-emerald-500/5", critical: "border-red-500/20 bg-red-500/5", medium: "border-blue-500/20 bg-blue-500/5", low: "border-gray-500/20 bg-gray-500/5" };
              const icons = { apply: <Target className="w-4 h-4 text-emerald-400" />, urgent: <AlertTriangle className="w-4 h-4 text-red-400" />, prepare: <Sparkles className="w-4 h-4 text-blue-400" />, skip: <Clock className="w-4 h-4 text-gray-400" /> };
              const labels = { high: "status-submitted", critical: "status-rejected", medium: "status-new", low: "status-reviewing" };
              return (
                <div key={i} className={`flex items-center gap-3 rounded-xl border p-4 cursor-pointer hover:bg-white/[0.02] transition-colors ${colors[action.priority] || ""}`}
                  onClick={() => navigate(`/opportunity/${action.opportunity_id}`)} data-testid={`action-${i}`}>
                  {icons[action.type]}
                  <span className="flex-1 text-sm text-gray-300">{action.message}</span>
                  <Badge className={`${labels[action.priority] || ""} border-0 text-[10px]`}>{action.priority}</Badge>
                  <ArrowRight className="w-3.5 h-3.5 text-gray-500" />
                </div>
              );
            })}
          </div>
        </section>
      )}

      {/* Expiring Soon */}
      {data?.expiring_soon?.length > 0 && (
        <section data-testid="expiring-soon-section">
          <div className="flex items-center gap-2 mb-4">
            <AlertTriangle className="w-4 h-4 text-amber-500" />
            <h2 className="text-lg font-medium text-white" style={{ fontFamily: 'Outfit, sans-serif' }}>Expiring Soon</h2>
            <Badge variant="secondary" className="text-[10px] bg-amber-500/10 text-amber-400 border-0">{data.expiring_soon.length}</Badge>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {data.expiring_soon.map(opp => (
              <OpportunityCard key={opp.id} opportunity={opp} onSave={handleSave} isSaved={savedIds.has(opp.id)} />
            ))}
          </div>
        </section>
      )}

      {/* Top Opportunities (AI Scored) */}
      {data?.top_opportunities?.length > 0 && (
        <section data-testid="top-opportunities-section">
          <div className="flex items-center gap-2 mb-4">
            <TrendingUp className="w-4 h-4 text-blue-500" />
            <h2 className="text-lg font-medium text-white" style={{ fontFamily: 'Outfit, sans-serif' }}>Top Opportunities</h2>
            <Badge variant="secondary" className="text-[10px] bg-blue-600/10 text-blue-400 border-0">AI Scored</Badge>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {data.top_opportunities.map(opp => (
              <OpportunityCard key={opp.id} opportunity={opp} onSave={handleSave} isSaved={savedIds.has(opp.id)} />
            ))}
          </div>
        </section>
      )}

      {/* Recently Added */}
      <section data-testid="recently-added-section">
        <div className="flex items-center gap-2 mb-4">
          <Plus className="w-4 h-4 text-gray-400" />
          <h2 className="text-lg font-medium text-white" style={{ fontFamily: 'Outfit, sans-serif' }}>Recently Added</h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {(data?.recently_added || []).map(opp => (
            <OpportunityCard key={opp.id} opportunity={opp} onSave={handleSave} isSaved={savedIds.has(opp.id)} />
          ))}
        </div>
      </section>

      {/* Saved */}
      {data?.saved?.length > 0 && (
        <section data-testid="saved-section">
          <div className="flex items-center gap-2 mb-4">
            <Bookmark className="w-4 h-4 text-emerald-500" />
            <h2 className="text-lg font-medium text-white" style={{ fontFamily: 'Outfit, sans-serif' }}>Saved Opportunities</h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {data.saved.map(opp => (
              <OpportunityCard key={opp.id} opportunity={opp} isSaved={true} />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

function MetricTile({ label, value, tone = "gray" }) {
  const colors = {
    blue: "text-blue-400 bg-blue-500/5 border-blue-500/15",
    emerald: "text-emerald-400 bg-emerald-500/5 border-emerald-500/15",
    purple: "text-purple-400 bg-purple-500/5 border-purple-500/15",
    amber: "text-amber-400 bg-amber-500/5 border-amber-500/15",
    rose: "text-rose-400 bg-rose-500/5 border-rose-500/15",
    gray: "text-gray-300 bg-[#0B0C10] border-white/[0.06]",
  }[tone];
  return (
    <div className={`rounded-lg border p-3 ${colors}`}>
      <p className="text-[10px] uppercase tracking-wider opacity-80">{label}</p>
      <p className="text-2xl font-semibold mt-1" style={{ fontFamily: "Outfit" }}>{value}</p>
    </div>
  );
}
