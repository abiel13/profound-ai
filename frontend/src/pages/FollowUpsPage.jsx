import React, { useState, useEffect, useCallback } from "react";
import axios from "axios";
import { useAuth } from "@/context/AuthContext";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Mail, Sparkles, Loader2, Send, Trash2, Eye, RefreshCw,
  ChevronDown, ChevronUp, Clock, AlertTriangle, CheckCircle, Copy, Scan
} from "lucide-react";

import { API } from "../config";

const TYPE_LABELS = {
  application_followup: "Application Follow-Up",
  relationship_reengagement: "Re-Engagement",
  post_rejection: "Post-Rejection",
  post_approval_thanks: "Thank You",
  partnership_continuation: "Partnership"
};

const URGENCY_STYLES = {
  high: "bg-red-500/10 text-red-400 border-red-500/20",
  medium: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  low: "bg-gray-500/10 text-gray-400 border-gray-500/20"
};

const STATUS_STYLES = {
  pending: "bg-amber-500/10 text-amber-400",
  draft: "bg-blue-500/10 text-blue-400",
  sent: "bg-emerald-500/10 text-emerald-400",
  dismissed: "bg-gray-500/10 text-gray-500"
};

export default function FollowUpsPage() {
  const { authHeaders } = useAuth();
  const navigate = useNavigate();
  const [followUps, setFollowUps] = useState([]);
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);
  const [generatingId, setGeneratingId] = useState(null);
  const [expandedId, setExpandedId] = useState(null);
  const [editDraft, setEditDraft] = useState({});

  const fetchFollowUps = useCallback(async () => {
    try {
      const res = await axios.get(`${API}/follow-ups`, { headers: authHeaders() });
      setFollowUps(res.data);
    } catch { toast.error("Failed to load follow-ups"); }
    finally { setLoading(false); }
  }, [authHeaders]);

  useEffect(() => { fetchFollowUps(); }, [fetchFollowUps]);

  const scanForFollowUps = async () => {
    setScanning(true);
    try {
      const res = await axios.post(`${API}/follow-ups/scan`, {}, { headers: authHeaders() });
      if (res.data.follow_ups_created > 0) {
        toast.success(`Found ${res.data.follow_ups_created} new follow-ups`);
      } else {
        toast.info("No new follow-ups detected");
      }
      fetchFollowUps();
    } catch { toast.error("Scan failed"); }
    finally { setScanning(false); }
  };

  const generateDraft = async (id) => {
    setGeneratingId(id);
    try {
      const res = await axios.post(`${API}/follow-ups/${id}/generate`, {}, { headers: authHeaders() });
      toast.success("Email draft generated");
      setExpandedId(id);
      setEditDraft(prev => ({ ...prev, [id]: { subject: res.data.subject, body: res.data.body } }));
      fetchFollowUps();
    } catch { toast.error("Generation failed"); }
    finally { setGeneratingId(null); }
  };

  const saveDraft = async (id) => {
    const draft = editDraft[id];
    if (!draft) return;
    try {
      await axios.put(`${API}/follow-ups/${id}`, {
        email_subject: draft.subject,
        email_draft: draft.body,
        status: "draft"
      }, { headers: authHeaders() });
      toast.success("Draft saved");
      fetchFollowUps();
    } catch { toast.error("Save failed"); }
  };

  const markSent = async (id) => {
    try {
      await axios.post(`${API}/follow-ups/${id}/mark-sent`, {}, { headers: authHeaders() });
      toast.success("Marked as sent - interaction logged");
      fetchFollowUps();
    } catch { toast.error("Failed"); }
  };

  const dismiss = async (id) => {
    try {
      await axios.delete(`${API}/follow-ups/${id}`, { headers: authHeaders() });
      toast.success("Dismissed");
      fetchFollowUps();
    } catch { toast.error("Failed"); }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text).then(() => toast.success("Copied to clipboard"));
  };

  if (loading) {
    return (
      <div className="space-y-4 animate-fade-in">
        <div className="h-8 w-48 skeleton-loading rounded-lg" />
        {[1,2,3].map(i => <div key={i} className="h-32 skeleton-loading rounded-xl" />)}
      </div>
    );
  }

  const pending = followUps.filter(f => f.status === "pending");
  const drafts = followUps.filter(f => f.status === "draft");
  const sent = followUps.filter(f => f.status === "sent");

  return (
    <div className="space-y-6 animate-fade-in max-w-4xl" data-testid="follow-ups-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl sm:text-3xl font-semibold text-white tracking-tight" style={{ fontFamily: 'Outfit, sans-serif' }}>
            Follow-Up Emails
          </h1>
          <p className="text-sm text-gray-400 mt-1">AI-generated personalized donor follow-ups for review and sending</p>
        </div>
        <Button onClick={scanForFollowUps} disabled={scanning} data-testid="scan-followups-btn"
          className="bg-blue-600 hover:bg-blue-500 text-white text-sm">
          {scanning ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Scan className="w-4 h-4 mr-2" />}
          {scanning ? "Scanning..." : "Scan for Follow-Ups"}
        </Button>
      </div>

      {/* Summary */}
      <div className="flex gap-3">
        <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-amber-500/10">
          <Clock className="w-3 h-3 text-amber-400" />
          <span className="text-xs text-amber-400">{pending.length} Pending</span>
        </div>
        <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-500/10">
          <Mail className="w-3 h-3 text-blue-400" />
          <span className="text-xs text-blue-400">{drafts.length} Drafts</span>
        </div>
        <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-500/10">
          <CheckCircle className="w-3 h-3 text-emerald-400" />
          <span className="text-xs text-emerald-400">{sent.length} Sent</span>
        </div>
      </div>

      {followUps.length === 0 ? (
        <div className="text-center py-16">
          <Mail className="w-12 h-12 text-gray-600 mx-auto mb-3" />
          <p className="text-gray-400">No follow-ups detected</p>
          <p className="text-sm text-gray-500 mt-1">Click "Scan for Follow-Ups" to check for pending communications</p>
        </div>
      ) : (
        <div className="space-y-3" data-testid="follow-ups-list">
          {followUps.filter(f => f.status !== 'dismissed').map(fu => {
            const isExpanded = expandedId === fu.id;
            const draft = editDraft[fu.id] || { subject: fu.email_subject || "", body: fu.email_draft || "" };
            const hasDraft = fu.email_draft && fu.email_draft.length > 10;
            return (
              <div key={fu.id} className="bg-[#12141A] border border-white/[0.05] rounded-xl overflow-hidden" data-testid={`followup-${fu.id}`}>
                {/* Header row */}
                <div className="flex items-center gap-3 p-4 cursor-pointer hover:bg-white/[0.02]"
                  onClick={() => setExpandedId(isExpanded ? null : fu.id)}>
                  <div className="w-9 h-9 rounded-lg bg-blue-600/10 flex items-center justify-center text-xs font-bold text-blue-400 shrink-0">
                    {fu.donor_name?.[0]}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <h3 className="text-sm font-medium text-white">{fu.donor_name}</h3>
                      <Badge className={`${URGENCY_STYLES[fu.urgency]} border text-[10px]`}>{fu.urgency}</Badge>
                      <Badge className={`${STATUS_STYLES[fu.status]} border-0 text-[10px]`}>{fu.status}</Badge>
                    </div>
                    <p className="text-xs text-gray-400 mt-0.5 line-clamp-1">{fu.reason}</p>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <Badge className="bg-white/[0.04] text-gray-400 border-0 text-[10px]">
                      {TYPE_LABELS[fu.email_type] || fu.email_type}
                    </Badge>
                    {!hasDraft && fu.status === 'pending' && (
                      <Button size="sm" onClick={(e) => { e.stopPropagation(); generateDraft(fu.id); }}
                        disabled={generatingId === fu.id} data-testid={`generate-btn-${fu.id}`}
                        className="bg-blue-600/10 text-blue-400 hover:bg-blue-600/20 text-xs h-8">
                        {generatingId === fu.id ? <Loader2 className="w-3 h-3 animate-spin" /> : <Sparkles className="w-3 h-3 mr-1" />}
                        {generatingId === fu.id ? "" : "Generate"}
                      </Button>
                    )}
                    {hasDraft && fu.status !== 'sent' && (
                      <Button size="sm" onClick={(e) => { e.stopPropagation(); setExpandedId(fu.id); }}
                        className="bg-emerald-600/10 text-emerald-400 hover:bg-emerald-600/20 text-xs h-8">
                        <Eye className="w-3 h-3 mr-1" />View Draft
                      </Button>
                    )}
                    {isExpanded ? <ChevronUp className="w-4 h-4 text-gray-400" /> : <ChevronDown className="w-4 h-4 text-gray-400" />}
                  </div>
                </div>

                {/* Expanded: Draft view/edit */}
                {isExpanded && (
                  <div className="border-t border-white/[0.05] p-5 space-y-4">
                    {hasDraft || editDraft[fu.id] ? (
                      <>
                        <div className="space-y-2">
                          <Label className="text-xs text-gray-500">Subject</Label>
                          <Input value={draft.subject}
                            onChange={(e) => setEditDraft(prev => ({ ...prev, [fu.id]: { ...draft, subject: e.target.value } }))}
                            className="bg-[#0B0C10] border-white/10 text-white h-10" data-testid={`subject-${fu.id}`}
                            readOnly={fu.status === 'sent'} />
                        </div>
                        <div className="space-y-2">
                          <Label className="text-xs text-gray-500">Email Body</Label>
                          <Textarea value={draft.body}
                            onChange={(e) => setEditDraft(prev => ({ ...prev, [fu.id]: { ...draft, body: e.target.value } }))}
                            rows={8} className="bg-[#0B0C10] border-white/10 text-white text-sm leading-relaxed resize-none"
                            data-testid={`body-${fu.id}`} readOnly={fu.status === 'sent'} />
                        </div>
                        <div className="flex items-center gap-2 pt-2">
                          {fu.status !== 'sent' && (
                            <>
                              <Button size="sm" onClick={() => saveDraft(fu.id)} data-testid={`save-draft-${fu.id}`}
                                className="bg-white/[0.06] text-gray-300 hover:text-white text-xs">Save Draft</Button>
                              <Button size="sm" onClick={() => markSent(fu.id)} data-testid={`mark-sent-${fu.id}`}
                                className="bg-emerald-600 hover:bg-emerald-500 text-white text-xs">
                                <Send className="w-3 h-3 mr-1" />Mark as Sent
                              </Button>
                              <Button size="sm" onClick={() => generateDraft(fu.id)} disabled={generatingId === fu.id}
                                className="bg-blue-600/10 text-blue-400 hover:bg-blue-600/20 text-xs" data-testid={`regen-${fu.id}`}>
                                {generatingId === fu.id ? <Loader2 className="w-3 h-3 animate-spin" /> : <RefreshCw className="w-3 h-3 mr-1" />}
                                Regenerate
                              </Button>
                            </>
                          )}
                          <Button size="sm" onClick={() => copyToClipboard(`Subject: ${draft.subject}\n\n${draft.body}`)}
                            className="bg-white/[0.04] text-gray-400 hover:text-white text-xs" data-testid={`copy-${fu.id}`}>
                            <Copy className="w-3 h-3 mr-1" />Copy
                          </Button>
                          {fu.status !== 'sent' && (
                            <Button size="sm" onClick={() => dismiss(fu.id)} variant="ghost"
                              className="text-gray-500 hover:text-red-400 text-xs ml-auto" data-testid={`dismiss-${fu.id}`}>
                              <Trash2 className="w-3 h-3 mr-1" />Dismiss
                            </Button>
                          )}
                        </div>
                      </>
                    ) : (
                      <div className="text-center py-6">
                        <Mail className="w-8 h-8 text-gray-600 mx-auto mb-2" />
                        <p className="text-sm text-gray-400">No draft generated yet</p>
                        <Button size="sm" onClick={() => generateDraft(fu.id)} disabled={generatingId === fu.id}
                          className="mt-3 bg-blue-600 hover:bg-blue-500 text-white text-xs" data-testid={`generate-expand-${fu.id}`}>
                          {generatingId === fu.id ? <Loader2 className="w-3 h-3 mr-1 animate-spin" /> : <Sparkles className="w-3 h-3 mr-1" />}
                          Generate Email Draft
                        </Button>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
