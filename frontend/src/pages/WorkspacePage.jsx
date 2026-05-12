import React, { useState, useEffect } from "react";
import axios from "axios";
import { useAuth } from "@/context/AuthContext";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import {
  Briefcase, Calendar, DollarSign, MapPin, FileText, Sparkles,
  ChevronDown, ChevronUp, ExternalLink, Loader2, ArrowRight
} from "lucide-react";

import { API } from "../config";

const STATUS_FLOW = ["Identified", "Analyzing", "Reviewing", "Drafting", "Preparing", "Ready to Submit", "Submitted", "Approved", "Rejected"];
const STATUS_COLORS = {
  Identified: "bg-gray-500/10 text-gray-400",
  Analyzing: "bg-blue-500/10 text-blue-400",
  Reviewing: "bg-amber-500/10 text-amber-400",
  Drafting: "bg-purple-500/10 text-purple-400",
  Preparing: "bg-cyan-500/10 text-cyan-400",
  "Ready to Submit": "bg-emerald-500/10 text-emerald-400",
  Submitted: "bg-green-500/10 text-green-400",
  Approved: "bg-green-600/15 text-green-300",
  Rejected: "bg-red-500/10 text-red-400",
  New: "bg-blue-500/10 text-blue-400",
};

function getDaysUntil(deadline) {
  return Math.ceil((new Date(deadline) - new Date()) / (1000 * 60 * 60 * 24));
}

function formatCurrency(min, max) {
  const fmt = (n) => n >= 1000000 ? `$${(n/1000000).toFixed(1)}M` : n >= 1000 ? `$${(n/1000).toFixed(0)}K` : `$${n}`;
  return `${fmt(min)} - ${fmt(max)}`;
}

export default function WorkspacePage() {
  const { authHeaders } = useAuth();
  const navigate = useNavigate();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [expandedId, setExpandedId] = useState(null);

  useEffect(() => { fetchWorkspace(); }, []);

  const fetchWorkspace = async () => {
    try {
      const res = await axios.get(`${API}/saved`, { headers: authHeaders() });
      setItems(res.data);
    } catch {
      toast.error("Failed to load workspace");
    } finally {
      setLoading(false);
    }
  };

  const updateStatus = async (savedId, status) => {
    try {
      await axios.put(`${API}/saved/${savedId}`, { status }, { headers: authHeaders() });
      setItems(prev => prev.map(s => s.saved_id === savedId ? { ...s, status } : s));
      toast.success(`Status: ${status}`);
    } catch {
      toast.error("Failed to update");
    }
  };

  if (loading) {
    return (
      <div className="space-y-4 animate-fade-in">
        <div className="h-8 w-48 skeleton-loading rounded-lg" />
        {[1,2,3].map(i => <div key={i} className="h-40 skeleton-loading rounded-xl" />)}
      </div>
    );
  }

  // Group by status
  const grouped = {};
  STATUS_FLOW.forEach(s => { grouped[s] = []; });
  items.forEach(item => {
    const status = item.status || "New";
    if (!grouped[status]) grouped[status] = [];
    grouped[status].push(item);
  });

  return (
    <div className="space-y-6 animate-fade-in" data-testid="workspace-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl sm:text-3xl font-semibold text-white tracking-tight" style={{ fontFamily: 'Outfit, sans-serif' }}>
            Application Workspace
          </h1>
          <p className="text-sm text-gray-400 mt-1">Manage your funding applications through every stage</p>
        </div>
        <Button onClick={() => navigate("/search")} data-testid="find-opportunities-btn" className="bg-blue-600 hover:bg-blue-500 text-white text-sm">
          <Sparkles className="w-4 h-4 mr-2" />
          Find Opportunities
        </Button>
      </div>

      {/* Status flow overview */}
      <div className="flex gap-2 overflow-x-auto pb-2">
        {STATUS_FLOW.filter(s => s !== "Rejected").map((status, i) => {
          const count = (grouped[status] || []).length;
          return (
            <React.Fragment key={status}>
              <div className={`shrink-0 px-3 py-2 rounded-lg border text-xs font-medium ${count > 0 ? STATUS_COLORS[status] + " border-current/20" : "bg-white/[0.02] border-white/[0.05] text-gray-600"}`}>
                {status} ({count})
              </div>
              {i < STATUS_FLOW.length - 2 && <ArrowRight className="w-3 h-3 text-gray-600 shrink-0 self-center" />}
            </React.Fragment>
          );
        })}
      </div>

      {items.length === 0 ? (
        <div className="text-center py-16">
          <Briefcase className="w-12 h-12 text-gray-600 mx-auto mb-3" />
          <p className="text-gray-400">No applications in workspace</p>
          <p className="text-sm text-gray-500 mt-1">Save opportunities from Search to start building your pipeline</p>
        </div>
      ) : (
        <div className="space-y-6" data-testid="workspace-list">
          {STATUS_FLOW.map(status => {
            const statusItems = grouped[status] || [];
            if (statusItems.length === 0) return null;
            return (
              <section key={status}>
                <div className="flex items-center gap-2 mb-3">
                  <Badge className={`${STATUS_COLORS[status]} border-0 text-xs`}>{status}</Badge>
                  <span className="text-xs text-gray-500">{statusItems.length} {statusItems.length === 1 ? 'application' : 'applications'}</span>
                </div>
                <div className="space-y-2">
                  {statusItems.map(item => {
                    const days = getDaysUntil(item.deadline);
                    const isExpanded = expandedId === item.saved_id;
                    return (
                      <div key={item.saved_id} className="bg-[#12141A] border border-white/[0.05] rounded-xl overflow-hidden" data-testid={`workspace-item-${item.saved_id}`}>
                        <div className="flex items-center gap-4 p-4 cursor-pointer hover:bg-white/[0.02] transition-colors"
                          onClick={() => setExpandedId(isExpanded ? null : item.saved_id)}>
                          <div className="flex-1 min-w-0">
                            <h3 className="text-sm font-medium text-white line-clamp-1">{item.title}</h3>
                            <div className="flex items-center gap-3 mt-1 text-xs text-gray-400">
                              <span>{item.donor_name}</span>
                              <span className="flex items-center gap-1"><DollarSign className="w-3 h-3" />{formatCurrency(item.funding_min, item.funding_max)}</span>
                              <span className={`flex items-center gap-1 ${days <= 7 ? 'text-red-400' : days <= 14 ? 'text-amber-400' : ''}`}>
                                <Calendar className="w-3 h-3" />{days > 0 ? `${days}d left` : "Expired"}
                              </span>
                            </div>
                          </div>
                          <Select value={item.status} onValueChange={(val) => { updateStatus(item.saved_id, val); }}>
                            <SelectTrigger className={`w-[150px] h-8 text-xs border-0 rounded-lg ${STATUS_COLORS[item.status] || ""}`}
                              onClick={(e) => e.stopPropagation()} data-testid={`workspace-status-${item.saved_id}`}>
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent className="bg-[#1A1D24] border-white/10">
                              {STATUS_FLOW.map(s => <SelectItem key={s} value={s} className="text-gray-300 text-xs">{s}</SelectItem>)}
                            </SelectContent>
                          </Select>
                          {isExpanded ? <ChevronUp className="w-4 h-4 text-gray-400 shrink-0" /> : <ChevronDown className="w-4 h-4 text-gray-400 shrink-0" />}
                        </div>

                        {isExpanded && (
                          <div className="border-t border-white/[0.05] p-5 space-y-4">
                            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                              <div>
                                <p className="text-[10px] text-gray-500 uppercase tracking-wider mb-1">Donor</p>
                                <p className="text-sm text-white">{item.donor_name}</p>
                                <p className="text-xs text-gray-400">{item.donor_type} - {item.donor_country}</p>
                              </div>
                              <div>
                                <p className="text-[10px] text-gray-500 uppercase tracking-wider mb-1">Funding Range</p>
                                <p className="text-sm text-white">{formatCurrency(item.funding_min, item.funding_max)}</p>
                              </div>
                              <div>
                                <p className="text-[10px] text-gray-500 uppercase tracking-wider mb-1">Deadline</p>
                                <p className={`text-sm font-medium ${days <= 7 ? 'text-red-400' : days <= 14 ? 'text-amber-400' : 'text-white'}`}>
                                  {item.deadline} ({days}d)
                                </p>
                              </div>
                              <div>
                                <p className="text-[10px] text-gray-500 uppercase tracking-wider mb-1">Match Score</p>
                                <p className="text-sm text-white">{item.ai_match_score > 0 ? `${item.ai_match_score}%` : "Not scored"}</p>
                              </div>
                            </div>

                            <div>
                              <p className="text-[10px] text-gray-500 uppercase tracking-wider mb-1">Eligibility</p>
                              <p className="text-xs text-gray-400 leading-relaxed">{item.eligibility}</p>
                            </div>

                            {item.ai_fit_explanation && (
                              <div className="bg-[#0B0C10] rounded-lg p-3 border border-blue-500/10">
                                <div className="flex items-center gap-1 mb-1">
                                  <Sparkles className="w-3 h-3 text-blue-400" />
                                  <p className="text-[10px] text-blue-400 uppercase tracking-wider">AI Fit Analysis</p>
                                </div>
                                <p className="text-xs text-gray-300 leading-relaxed">{item.ai_fit_explanation}</p>
                              </div>
                            )}

                            <div className="flex gap-2 pt-2">
                              <Button size="sm" onClick={() => navigate(`/opportunity/${item.id}`)} className="bg-white/[0.06] text-gray-300 hover:text-white hover:bg-white/10 text-xs">
                                View Details
                              </Button>
                              <Button size="sm" onClick={() => navigate(`/proposals?opp=${item.id}`)} className="bg-blue-600/10 text-blue-400 hover:bg-blue-600/20 text-xs">
                                <FileText className="w-3 h-3 mr-1" />
                                Generate Proposal
                              </Button>
                              {item.url && (
                                <a href={item.url} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1 px-3 py-1 text-xs text-gray-400 hover:text-blue-400">
                                  <ExternalLink className="w-3 h-3" />
                                  Donor Site
                                </a>
                              )}
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </section>
            );
          })}
        </div>
      )}
    </div>
  );
}
