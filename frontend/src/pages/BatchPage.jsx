import React, { useState, useEffect, useCallback } from "react";
import axios from "axios";
import { useAuth } from "@/context/AuthContext";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Layers, Sparkles, Loader2, CheckCircle, AlertTriangle, Target,
  DollarSign, Calendar, ArrowRight, Rocket, Eye, XCircle, Search
} from "lucide-react";

import { API } from "../config";

function formatValue(n) {
  if (!n) return "$0";
  if (n >= 1000000) return `$${(n / 1000000).toFixed(1)}M`;
  if (n >= 1000) return `$${(n / 1000).toFixed(0)}K`;
  return `$${n}`;
}

function getDaysUntil(d) { return Math.ceil((new Date(d) - new Date()) / 86400000); }

export default function BatchPage() {
  const { authHeaders } = useAuth();
  const navigate = useNavigate();
  const [opportunities, setOpportunities] = useState([]);
  const [selected, setSelected] = useState(new Set());
  const [reviewQueue, setReviewQueue] = useState([]);
  const [batchStatus, setBatchStatus] = useState({ running: false });
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState("select");

  const fetchData = useCallback(async () => {
    try {
      const [oppsRes, reviewRes, statusRes] = await Promise.all([
        axios.get(`${API}/opportunities?sort_by=match`, { headers: authHeaders() }),
        axios.get(`${API}/batch/review`, { headers: authHeaders() }),
        axios.get(`${API}/batch/status`, { headers: authHeaders() })
      ]);
      const today = new Date().toISOString().split('T')[0];
      setOpportunities(oppsRes.data.filter(o => o.ai_match_score >= 75 && o.deadline >= today));
      setReviewQueue(reviewRes.data);
      setBatchStatus(statusRes.data);
      if (statusRes.data.running) setTab("progress");
      else if (reviewRes.data.length > 0) setTab("review");
    } catch { toast.error("Failed to load"); }
    finally { setLoading(false); }
  }, [authHeaders]);

  useEffect(() => { fetchData(); }, [fetchData]);

  // Poll batch status
  useEffect(() => {
    if (!batchStatus.running) return;
    const interval = setInterval(async () => {
      try {
        const res = await axios.get(`${API}/batch/status`, { headers: authHeaders() });
        setBatchStatus(res.data);
        if (!res.data.running) {
          clearInterval(interval);
          toast.success(`Batch complete: ${res.data.processed} applications processed`);
          fetchData();
          setTab("review");
        }
      } catch { /* ignore */ }
    }, 5000);
    return () => clearInterval(interval);
  }, [batchStatus.running, authHeaders, fetchData]);

  const toggleSelect = (id) => {
    setSelected(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else if (next.size < 10) next.add(id);
      else toast.error("Maximum 10 opportunities per batch");
      return next;
    });
  };

  const startBatch = async () => {
    if (selected.size === 0) { toast.error("Select at least one opportunity"); return; }
    try {
      await axios.post(`${API}/batch/start`, { opportunity_ids: [...selected] }, { headers: authHeaders() });
      toast.info(`Batch started: ${selected.size} applications being generated...`);
      setTab("progress");
      setBatchStatus({ running: true, total: selected.size, processed: 0, errors: 0, results: [] });
      setSelected(new Set());
    } catch { toast.error("Failed to start batch"); }
  };

  const approveItem = async (wizId) => {
    try {
      await axios.post(`${API}/batch/approve/${wizId}`, {}, { headers: authHeaders() });
      toast.success("Approved - Ready to Submit");
      fetchData();
    } catch { toast.error("Failed to approve"); }
  };

  if (loading) {
    return <div className="space-y-4 animate-fade-in"><div className="h-8 w-48 skeleton-loading rounded-lg" /><div className="h-96 skeleton-loading rounded-xl" /></div>;
  }

  return (
    <div className="space-y-6 animate-fade-in" data-testid="batch-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl sm:text-3xl font-semibold text-white tracking-tight" style={{ fontFamily: 'Outfit' }}>
            Batch Applications
          </h1>
          <p className="text-sm text-gray-400 mt-1">Generate multiple applications in parallel with quality control</p>
        </div>
        {tab === "select" && selected.size > 0 && (
          <Button onClick={startBatch} data-testid="start-batch-btn" className="bg-purple-600 hover:bg-purple-500 text-white text-sm">
            <Rocket className="w-4 h-4 mr-2" />Generate {selected.size} Applications
          </Button>
        )}
      </div>

      {/* Tabs */}
      <div className="flex gap-2" data-testid="batch-tabs">
        {[
          ["select", `Select (${opportunities.length})`, Search],
          ["progress", "Progress", Loader2],
          ["review", `Review (${reviewQueue.length})`, Eye]
        ].map(([key, label, Icon]) => (
          <button key={key} onClick={() => setTab(key)} data-testid={`tab-${key}`}
            className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-medium transition-colors ${
              tab === key ? 'bg-blue-600/10 text-blue-400' : 'text-gray-500 hover:text-white hover:bg-white/[0.04]'
            }`}>
            <Icon className={`w-3.5 h-3.5 ${key === "progress" && batchStatus.running ? 'animate-spin' : ''}`} />{label}
          </button>
        ))}
      </div>

      {/* SELECT TAB */}
      {tab === "select" && (
        <div className="space-y-3" data-testid="batch-select">
          <p className="text-xs text-gray-500">Showing opportunities with 75%+ match score and valid deadlines. Select up to 10.</p>
          {opportunities.length === 0 ? (
            <div className="text-center py-12">
              <Target className="w-10 h-10 text-gray-600 mx-auto mb-3" />
              <p className="text-gray-400 text-sm">No eligible opportunities. Run AI scoring first.</p>
            </div>
          ) : (
            <div className="space-y-2">
              {opportunities.map(opp => {
                const days = getDaysUntil(opp.deadline);
                const isSelected = selected.has(opp.id);
                return (
                  <label key={opp.id}
                    className={`flex items-center gap-4 p-4 rounded-xl border cursor-pointer transition-all ${
                      isSelected ? 'bg-purple-600/5 border-purple-500/20' : 'bg-[#12141A] border-white/[0.05] hover:border-white/10'
                    }`} data-testid={`batch-opp-${opp.id}`}>
                    <Checkbox checked={isSelected} onCheckedChange={() => toggleSelect(opp.id)} />
                    <div className="flex-1 min-w-0">
                      <h3 className="text-sm font-medium text-white line-clamp-1">{opp.title}</h3>
                      <div className="flex items-center gap-3 text-xs text-gray-400 mt-1">
                        <span>{opp.donor_name}</span>
                        <span className="flex items-center gap-1"><DollarSign className="w-3 h-3" />{formatValue(opp.funding_max)}</span>
                        <span className={`flex items-center gap-1 ${days <= 14 ? 'text-amber-400' : ''}`}><Calendar className="w-3 h-3" />{days}d</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <div className="w-9 h-9 rounded-full flex items-center justify-center text-xs font-bold border-2 border-emerald-500 text-emerald-400">
                        {opp.ai_match_score}%
                      </div>
                      {opp.decision_label === "Apply Now" && (
                        <Badge className="bg-emerald-600/10 text-emerald-400 border-0 text-[10px]">Apply Now</Badge>
                      )}
                    </div>
                  </label>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* PROGRESS TAB */}
      {tab === "progress" && (
        <div className="space-y-4" data-testid="batch-progress">
          {batchStatus.running ? (
            <div className="bg-purple-600/5 border border-purple-500/20 rounded-xl p-6 space-y-4">
              <div className="flex items-center gap-3">
                <Loader2 className="w-5 h-5 text-purple-400 animate-spin" />
                <span className="text-sm font-medium text-purple-300">Generating Applications...</span>
                <span className="text-xs text-purple-400 ml-auto">{batchStatus.processed}/{batchStatus.total}</span>
              </div>
              <Progress value={batchStatus.total ? (batchStatus.processed / batchStatus.total) * 100 : 0} className="h-2" />
              <p className="text-xs text-gray-500">Each application takes ~20 seconds. Do not close this page.</p>
            </div>
          ) : batchStatus.total > 0 ? (
            <div className="bg-[#12141A] border border-white/[0.05] rounded-xl p-6">
              <div className="flex items-center gap-3 mb-4">
                <CheckCircle className="w-5 h-5 text-emerald-400" />
                <span className="text-sm font-medium text-white">Batch Complete</span>
                <span className="text-xs text-gray-400">{batchStatus.processed}/{batchStatus.total} processed, {batchStatus.errors} errors</span>
              </div>
              <div className="space-y-2">
                {(batchStatus.results || []).map((r, i) => (
                  <div key={i} className="flex items-center gap-3 p-3 rounded-lg bg-[#0B0C10]">
                    {r.status === "ready_for_review" ? <CheckCircle className="w-4 h-4 text-emerald-400" /> :
                     r.status === "exists" ? <AlertTriangle className="w-4 h-4 text-amber-400" /> :
                     <XCircle className="w-4 h-4 text-red-400" />}
                    <span className="text-xs text-gray-300 flex-1">{r.title || r.opportunity_id}</span>
                    <Badge className={`border-0 text-[10px] ${r.status === 'ready_for_review' ? 'bg-emerald-600/10 text-emerald-400' : r.status === 'exists' ? 'bg-amber-600/10 text-amber-400' : 'bg-red-600/10 text-red-400'}`}>
                      {r.status === 'ready_for_review' ? 'Ready for Review' : r.status}
                    </Badge>
                    {r.quality_score && <span className="text-xs text-gray-500">Quality: {r.quality_score}%</span>}
                  </div>
                ))}
              </div>
              <Button onClick={() => setTab("review")} className="mt-4 bg-blue-600 hover:bg-blue-500 text-white text-sm">
                <Eye className="w-4 h-4 mr-2" />Review Applications
              </Button>
            </div>
          ) : (
            <div className="text-center py-12">
              <Layers className="w-10 h-10 text-gray-600 mx-auto mb-3" />
              <p className="text-gray-400 text-sm">No batch in progress. Select opportunities to start.</p>
            </div>
          )}
        </div>
      )}

      {/* REVIEW TAB */}
      {tab === "review" && (
        <div className="space-y-3" data-testid="batch-review">
          {reviewQueue.length === 0 ? (
            <div className="text-center py-12">
              <Eye className="w-10 h-10 text-gray-600 mx-auto mb-3" />
              <p className="text-gray-400 text-sm">No applications pending review</p>
            </div>
          ) : (
            <>
              <p className="text-xs text-gray-500">Review each application before approving for submission.</p>
              {reviewQueue.map(item => {
                const days = getDaysUntil(item.deadline);
                const qc = item.review_checklist || {};
                const qualityScore = qc.quality_score || 100;
                const flags = qc.flags || [];
                return (
                  <div key={item.id} className="bg-[#12141A] border border-white/[0.05] rounded-xl p-5" data-testid={`review-${item.id}`}>
                    <div className="flex items-center gap-4">
                      <div className={`w-11 h-11 rounded-xl flex items-center justify-center text-sm font-bold shrink-0 ${
                        qualityScore >= 80 ? 'bg-emerald-600/10 text-emerald-400 border border-emerald-500/20' :
                        qualityScore >= 60 ? 'bg-amber-600/10 text-amber-400 border border-amber-500/20' :
                        'bg-red-600/10 text-red-400 border border-red-500/20'
                      }`}>
                        {qualityScore}%
                      </div>
                      <div className="flex-1 min-w-0">
                        <h3 className="text-sm font-medium text-white line-clamp-1">{item.title}</h3>
                        <div className="flex items-center gap-3 text-xs text-gray-400 mt-1">
                          <span>{item.donor_name}</span>
                          <Badge className="bg-white/[0.04] text-gray-400 border-0 text-[10px]">{item.donor_type}</Badge>
                          <span className="flex items-center gap-1"><DollarSign className="w-3 h-3" />{formatValue(item.funding_max)}</span>
                          <span className={`flex items-center gap-1 ${days <= 14 ? 'text-amber-400' : ''}`}><Calendar className="w-3 h-3" />{days}d</span>
                          <span className="text-blue-400">{item.ai_match_score}% match</span>
                        </div>
                        {flags.length > 0 && (
                          <div className="flex gap-2 mt-2">
                            {flags.map((f, i) => (
                              <span key={i} className="text-[10px] text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded">
                                <AlertTriangle className="w-2.5 h-2.5 inline mr-1" />{f}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                      <div className="flex items-center gap-2 shrink-0">
                        <Button size="sm" onClick={() => navigate(`/wizard?wiz=${item.id}`)} data-testid={`view-${item.id}`}
                          className="bg-white/[0.06] text-gray-300 hover:text-white text-xs h-8">
                          <Eye className="w-3 h-3 mr-1" />Review
                        </Button>
                        <Button size="sm" onClick={() => approveItem(item.id)} data-testid={`approve-${item.id}`}
                          className="bg-emerald-600 hover:bg-emerald-500 text-white text-xs h-8">
                          <CheckCircle className="w-3 h-3 mr-1" />Approve
                        </Button>
                      </div>
                    </div>
                  </div>
                );
              })}
            </>
          )}
        </div>
      )}
    </div>
  );
}
