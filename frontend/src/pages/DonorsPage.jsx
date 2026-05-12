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
  Users, Heart, DollarSign, Mail, Phone, Calendar, FileText,
  ChevronDown, ChevronUp, ArrowRight, Target, Sparkles, AlertTriangle,
  ExternalLink, Plus, MessageSquare, RefreshCw
} from "lucide-react";

import { API } from "../config";
const INTERACTION_TYPES = ["email", "meeting", "call", "proposal_submitted", "follow_up", "response_received"];

function formatValue(n) {
  if (!n) return "$0";
  if (n >= 1000000) return `$${(n / 1000000).toFixed(1)}M`;
  if (n >= 1000) return `$${(n / 1000).toFixed(0)}K`;
  return `$${n}`;
}

function ScoreBadge({ score, level }) {
  const colors = {
    Strong: "bg-emerald-600/10 text-emerald-400 border-emerald-500/20",
    Growing: "bg-amber-600/10 text-amber-400 border-amber-500/20",
    New: "bg-gray-600/10 text-gray-400 border-gray-500/20"
  };
  return <Badge className={`${colors[level] || colors.New} border text-[10px]`}>{level} ({score}%)</Badge>;
}

export default function DonorsPage() {
  const { authHeaders } = useAuth();
  const navigate = useNavigate();
  const [donors, setDonors] = useState([]);
  const [insights, setInsights] = useState(null);
  const [loading, setLoading] = useState(true);
  const [expandedId, setExpandedId] = useState(null);
  const [detailDonor, setDetailDonor] = useState(null);
  const [interactionOpen, setInteractionOpen] = useState(false);
  const [interactionForm, setInteractionForm] = useState({ donor_id: "", type: "email", date: new Date().toISOString().split('T')[0], notes: "" });
  const [tab, setTab] = useState("all");

  const fetchData = useCallback(async () => {
    try {
      const [dRes, iRes] = await Promise.all([
        axios.get(`${API}/donors`, { headers: authHeaders() }),
        axios.get(`${API}/donors/dashboard/insights`, { headers: authHeaders() })
      ]);
      setDonors(dRes.data);
      setInsights(iRes.data);
    } catch { toast.error("Failed to load donors"); }
    finally { setLoading(false); }
  }, [authHeaders]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const loadDetail = async (id) => {
    if (expandedId === id) { setExpandedId(null); setDetailDonor(null); return; }
    try {
      const res = await axios.get(`${API}/donors/${id}`, { headers: authHeaders() });
      setDetailDonor(res.data);
      setExpandedId(id);
    } catch { toast.error("Failed to load donor"); }
  };

  const addInteraction = async () => {
    if (!interactionForm.donor_id) return;
    try {
      await axios.post(`${API}/donors/interactions`, interactionForm, { headers: authHeaders() });
      toast.success("Interaction logged");
      setInteractionOpen(false);
      setInteractionForm({ donor_id: "", type: "email", date: new Date().toISOString().split('T')[0], notes: "" });
      fetchData();
      if (expandedId) loadDetail(expandedId);
    } catch { toast.error("Failed to log interaction"); }
  };

  const openInteraction = (donorId) => {
    setInteractionForm(prev => ({ ...prev, donor_id: donorId }));
    setInteractionOpen(true);
  };

  if (loading) {
    return (
      <div className="space-y-4 animate-fade-in">
        <div className="h-8 w-48 skeleton-loading rounded-lg" />
        {[1,2,3,4].map(i => <div key={i} className="h-24 skeleton-loading rounded-xl" />)}
      </div>
    );
  }

  const recs = insights?.recommendations || [];
  const strong = donors.filter(d => d.relationship_level === "Strong");
  const growing = donors.filter(d => d.relationship_level === "Growing");
  const newDonors = donors.filter(d => d.relationship_level === "New");
  const filtered = tab === "strong" ? strong : tab === "growing" ? growing : tab === "new" ? newDonors : donors;

  return (
    <div className="space-y-6 animate-fade-in" data-testid="donors-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl sm:text-3xl font-semibold text-white tracking-tight" style={{ fontFamily: 'Outfit, sans-serif' }}>
            Donor Relationships
          </h1>
          <p className="text-sm text-gray-400 mt-1">Track and strengthen relationships with international donors</p>
        </div>
        <div className="flex items-center gap-3 text-xs">
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-emerald-500/10"><Heart className="w-3 h-3 text-emerald-400" /><span className="text-emerald-400">{strong.length} Strong</span></div>
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-amber-500/10"><Target className="w-3 h-3 text-amber-400" /><span className="text-amber-400">{growing.length} Growing</span></div>
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-gray-500/10"><Users className="w-3 h-3 text-gray-400" /><span className="text-gray-400">{newDonors.length} New</span></div>
        </div>
      </div>

      {/* Recommendations */}
      {recs.length > 0 && (
        <section data-testid="donor-recommendations">
          <div className="flex items-center gap-2 mb-3">
            <Sparkles className="w-4 h-4 text-blue-400" />
            <h2 className="text-base font-medium text-white" style={{ fontFamily: 'Outfit' }}>Relationship Intelligence</h2>
          </div>
          <div className="space-y-2">
            {recs.slice(0, 5).map((r, i) => {
              const colors = { high: "border-emerald-500/15 bg-emerald-500/5", medium: "border-amber-500/15 bg-amber-500/5", low: "border-gray-500/15 bg-gray-500/5" };
              const icons = { reapply: <RefreshCw className="w-4 h-4 text-emerald-400" />, follow_up: <MessageSquare className="w-4 h-4 text-amber-400" />, dormant: <AlertTriangle className="w-4 h-4 text-gray-400" /> };
              return (
                <div key={i} className={`flex items-center gap-3 p-3 rounded-xl border ${colors[r.priority] || ""}`} data-testid={`rec-${i}`}>
                  {icons[r.type]}
                  <span className="flex-1 text-sm text-gray-300">{r.message}</span>
                  <Badge className={`border-0 text-[10px] ${r.priority === 'high' ? 'bg-emerald-600/10 text-emerald-400' : r.priority === 'medium' ? 'bg-amber-600/10 text-amber-400' : 'bg-gray-600/10 text-gray-400'}`}>{r.priority}</Badge>
                </div>
              );
            })}
          </div>
        </section>
      )}

      {/* Filter tabs */}
      <div className="flex gap-2" data-testid="donor-tabs">
        {[["all", "All"], ["strong", "Strong"], ["growing", "Growing"], ["new", "New"]].map(([key, label]) => (
          <button key={key} onClick={() => setTab(key)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${tab === key ? 'bg-blue-600/10 text-blue-400' : 'text-gray-500 hover:text-white hover:bg-white/[0.04]'}`}
            data-testid={`tab-${key}`}>{label} ({key === "all" ? donors.length : key === "strong" ? strong.length : key === "growing" ? growing.length : newDonors.length})</button>
        ))}
      </div>

      {/* Donor list */}
      <div className="space-y-2" data-testid="donors-list">
        {filtered.map(donor => {
          const isExpanded = expandedId === donor.id;
          const dd = isExpanded ? detailDonor : null;
          return (
            <div key={donor.id} className="bg-[#12141A] border border-white/[0.05] rounded-xl overflow-hidden" data-testid={`donor-${donor.id}`}>
              <div className="flex items-center gap-4 p-4 cursor-pointer hover:bg-white/[0.02]" onClick={() => loadDetail(donor.id)}>
                <div className="w-10 h-10 rounded-lg bg-blue-600/10 flex items-center justify-center text-sm font-bold text-blue-400 shrink-0">
                  {donor.name?.[0]}
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="text-sm font-medium text-white">{donor.name}</h3>
                  <div className="flex items-center gap-3 text-xs text-gray-400 mt-0.5">
                    <span>{donor.type}</span>
                    {donor.country && <span>{donor.country}</span>}
                    {donor.total_funding_received > 0 && <span className="text-emerald-400">{formatValue(donor.total_funding_received)} secured</span>}
                  </div>
                </div>
                <div className="flex items-center gap-3 shrink-0">
                  <ScoreBadge score={donor.relationship_score} level={donor.relationship_level} />
                  <div className="text-right text-xs text-gray-500">
                    <p>{donor.total_approvals}W / {donor.total_rejections}L</p>
                    <p>{donor.total_applications} apps</p>
                  </div>
                  <button onClick={(e) => { e.stopPropagation(); openInteraction(donor.id); }}
                    className="p-2 text-gray-500 hover:text-blue-400 hover:bg-blue-500/10 rounded-lg" data-testid={`log-interaction-${donor.id}`}>
                    <Plus className="w-4 h-4" />
                  </button>
                  {isExpanded ? <ChevronUp className="w-4 h-4 text-gray-400" /> : <ChevronDown className="w-4 h-4 text-gray-400" />}
                </div>
              </div>

              {isExpanded && dd && (
                <div className="border-t border-white/[0.05] p-5 space-y-4">
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-center">
                    <div className="bg-[#0B0C10] rounded-lg p-3">
                      <p className="text-lg font-bold text-white">{dd.relationship_score}%</p>
                      <p className="text-[10px] text-gray-500">Relationship</p>
                    </div>
                    <div className="bg-[#0B0C10] rounded-lg p-3">
                      <p className="text-lg font-bold text-emerald-400">{formatValue(dd.total_funding_received)}</p>
                      <p className="text-[10px] text-gray-500">Funded</p>
                    </div>
                    <div className="bg-[#0B0C10] rounded-lg p-3">
                      <p className="text-lg font-bold text-white">{dd.total_approvals}/{dd.total_applications}</p>
                      <p className="text-[10px] text-gray-500">Won/Applied</p>
                    </div>
                    <div className="bg-[#0B0C10] rounded-lg p-3">
                      <p className="text-lg font-bold text-white">{(dd.interactions || []).length}</p>
                      <p className="text-[10px] text-gray-500">Interactions</p>
                    </div>
                  </div>

                  {/* Interactions timeline */}
                  {(dd.interactions || []).length > 0 && (
                    <div>
                      <h4 className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-2">Recent Interactions</h4>
                      <div className="space-y-1.5">
                        {dd.interactions.slice(0, 5).map(int => (
                          <div key={int.id} className="flex items-center gap-3 text-xs p-2 rounded-lg bg-[#0B0C10]">
                            <Badge className="bg-blue-600/10 text-blue-400 border-0 text-[10px]">{int.type}</Badge>
                            <span className="text-gray-400">{int.date}</span>
                            <span className="text-gray-300 flex-1 truncate">{int.notes}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Active opportunities */}
                  {(dd.opportunities || []).length > 0 && (
                    <div>
                      <h4 className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-2">Active Opportunities</h4>
                      <div className="space-y-1.5">
                        {dd.opportunities.map(opp => (
                          <div key={opp.id} className="flex items-center gap-3 text-xs p-2 rounded-lg bg-[#0B0C10] cursor-pointer hover:bg-white/[0.03]"
                            onClick={() => navigate(`/opportunity/${opp.id}`)}>
                            <span className="text-white flex-1 truncate">{opp.title}</span>
                            {opp.ai_match_score > 0 && <span className="text-blue-400">{opp.ai_match_score}%</span>}
                            <span className="text-gray-500">{opp.deadline}</span>
                            <ArrowRight className="w-3 h-3 text-gray-500" />
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Outcomes */}
                  {(dd.outcomes || []).length > 0 && (
                    <div>
                      <h4 className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-2">Application History</h4>
                      <div className="space-y-1.5">
                        {dd.outcomes.map(o => (
                          <div key={o.id} className="flex items-center gap-3 text-xs p-2 rounded-lg bg-[#0B0C10]">
                            <Badge className={`border-0 text-[10px] ${o.outcome === 'approved' ? 'bg-emerald-600/10 text-emerald-400' : o.outcome === 'rejected' ? 'bg-red-600/10 text-red-400' : 'bg-gray-600/10 text-gray-400'}`}>
                              {o.outcome}
                            </Badge>
                            <span className="text-white flex-1 truncate">{o.title}</span>
                            {o.amount_awarded > 0 && <span className="text-emerald-400">{formatValue(o.amount_awarded)}</span>}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {dd.website && (
                    <a href={dd.website} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1 text-xs text-blue-400 hover:text-blue-300">
                      <ExternalLink className="w-3 h-3" />Visit donor website
                    </a>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Log Interaction Dialog */}
      <Dialog open={interactionOpen} onOpenChange={setInteractionOpen}>
        <DialogContent className="bg-[#12141A] border-white/10 sm:max-w-md" data-testid="interaction-dialog">
          <DialogHeader>
            <DialogTitle className="text-white" style={{ fontFamily: 'Outfit' }}>Log Interaction</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 mt-2">
            <div className="space-y-2">
              <Label className="text-sm text-gray-300">Type</Label>
              <Select value={interactionForm.type} onValueChange={v => setInteractionForm(p => ({ ...p, type: v }))}>
                <SelectTrigger className="bg-[#0B0C10] border-white/10 text-gray-300 h-10" data-testid="interaction-type-select"><SelectValue /></SelectTrigger>
                <SelectContent className="bg-[#1A1D24] border-white/10">
                  {INTERACTION_TYPES.map(t => <SelectItem key={t} value={t} className="text-gray-300 text-xs">{t.replace('_', ' ')}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label className="text-sm text-gray-300">Date</Label>
              <Input type="date" value={interactionForm.date} onChange={e => setInteractionForm(p => ({ ...p, date: e.target.value }))}
                className="bg-[#0B0C10] border-white/10 text-white h-10" data-testid="interaction-date-input" />
            </div>
            <div className="space-y-2">
              <Label className="text-sm text-gray-300">Notes</Label>
              <Textarea value={interactionForm.notes} onChange={e => setInteractionForm(p => ({ ...p, notes: e.target.value }))}
                placeholder="Details about the interaction..." rows={3}
                className="bg-[#0B0C10] border-white/10 text-white resize-none" data-testid="interaction-notes-input" />
            </div>
            <Button onClick={addInteraction} data-testid="submit-interaction-btn" className="w-full bg-blue-600 hover:bg-blue-500 text-white">
              Log Interaction
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
