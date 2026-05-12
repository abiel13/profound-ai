import React, { useState, useEffect, useCallback } from "react";
import axios from "axios";
import { useAuth } from "@/context/AuthContext";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import {
  Building2, Sparkles, Loader2, Trash2, Copy, Send,
  ChevronDown, ChevronUp, RefreshCw,
} from "lucide-react";

import { API } from "../config";

const TIER_STYLES = {
  bronze: "bg-amber-700/20 text-amber-300",
  silver: "bg-gray-400/10 text-gray-300",
  gold: "bg-yellow-500/10 text-yellow-400",
};
const STATUS_STYLES = {
  draft: "bg-amber-500/10 text-amber-400",
  sent: "bg-blue-500/10 text-blue-400",
  won: "bg-emerald-500/10 text-emerald-400",
  lost: "bg-red-500/10 text-red-400",
  archived: "bg-zinc-500/10 text-zinc-500",
};

function copyText(t) { navigator.clipboard.writeText(t || ""); toast.success("Copied"); }

export default function SponsorsPage() {
  const { authHeaders } = useAuth();
  const [sponsors, setSponsors] = useState([]);
  const [links, setLinks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [form, setForm] = useState({ sponsor_name: "", sponsor_type: "small_business", offer_tier: "silver" });
  const [expandedId, setExpandedId] = useState(null);
  const [enqueueForm, setEnqueueForm] = useState({ channel: "email", recipient: "", recipient_label: "" });
  const [enqueuingId, setEnqueuingId] = useState(null);

  const fetchAll = useCallback(async () => {
    try {
      const [s, l] = await Promise.all([
        axios.get(`${API}/v11/sponsors`, { headers: authHeaders() }),
        axios.get(`${API}/v11/payment-links`, { headers: authHeaders() }),
      ]);
      setSponsors(s.data || []);
      setLinks(l.data || []);
    } catch { toast.error("Failed to load sponsors"); }
    finally { setLoading(false); }
  }, [authHeaders]);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  const generate = async () => {
    if (!form.sponsor_name.trim()) return toast.error("Enter sponsor name");
    setGenerating(true);
    try {
      await axios.post(`${API}/v11/sponsors/generate`, form, { headers: authHeaders(), timeout: 180000 });
      toast.success("Sponsor offer generated");
      setForm({ ...form, sponsor_name: "" });
      fetchAll();
    } catch (e) { toast.error(e?.response?.data?.detail || "Generation failed (AI upstream)"); }
    finally { setGenerating(false); }
  };

  const del = async (id) => {
    if (!window.confirm("Delete this sponsor offer?")) return;
    await axios.delete(`${API}/v11/sponsors/${id}`, { headers: authHeaders() });
    toast.success("Deleted");
    fetchAll();
  };

  const updateField = async (id, patch) => {
    try { await axios.patch(`${API}/v11/sponsors/${id}`, patch, { headers: authHeaders() }); fetchAll(); }
    catch { toast.error("Update failed"); }
  };

  const enqueue = async (id) => {
    if (!enqueueForm.recipient) return toast.error("Enter recipient");
    setEnqueuingId(id);
    try {
      await axios.post(`${API}/v11/sponsors/${id}/enqueue`, enqueueForm, { headers: authHeaders() });
      toast.success(`Queued (mock ${enqueueForm.channel})`);
      setEnqueueForm({ channel: "email", recipient: "", recipient_label: "" });
    } catch { toast.error("Failed to queue"); }
    finally { setEnqueuingId(null); }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6" data-testid="sponsors-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-semibold text-white tracking-tight flex items-center gap-3">
            <Building2 className="w-7 h-7 text-cyan-400" />
            Sponsor Outreach
          </h1>
          <p className="text-sm text-gray-400 mt-1">AI-generated business-sponsor packages ($100–$1000).</p>
        </div>
        <Button variant="outline" size="sm" onClick={fetchAll} data-testid="refresh-sponsors-btn">
          <RefreshCw className="w-4 h-4 mr-2" />Refresh
        </Button>
      </div>

      <div className="glass-surface border border-white/[0.06] rounded-xl p-5 space-y-3" data-testid="sponsor-generator">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-blue-400" />
          <h2 className="text-sm font-semibold text-white">Generate New Sponsor Pitch</h2>
        </div>
        <div className="grid md:grid-cols-4 gap-3">
          <div className="md:col-span-2">
            <Label className="text-xs text-gray-400">Sponsor Name</Label>
            <Input
              placeholder="e.g. Kalahari Sands Hotel"
              value={form.sponsor_name}
              onChange={(e) => setForm({ ...form, sponsor_name: e.target.value })}
              data-testid="sponsor-name-input"
            />
          </div>
          <div>
            <Label className="text-xs text-gray-400">Type</Label>
            <Select value={form.sponsor_type} onValueChange={(v) => setForm({ ...form, sponsor_type: v })}>
              <SelectTrigger data-testid="sponsor-type-select"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="small_business">Small Business</SelectItem>
                <SelectItem value="sme">SME</SelectItem>
                <SelectItem value="corporate_local">Local Corporate</SelectItem>
                <SelectItem value="shop">Shop / Retail</SelectItem>
                <SelectItem value="brand">Brand</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label className="text-xs text-gray-400">Tier</Label>
            <Select value={form.offer_tier} onValueChange={(v) => setForm({ ...form, offer_tier: v })}>
              <SelectTrigger data-testid="sponsor-tier-select"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="bronze">Bronze ($100–$250)</SelectItem>
                <SelectItem value="silver">Silver ($250–$500)</SelectItem>
                <SelectItem value="gold">Gold ($500–$1000)</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
        <Button onClick={generate} disabled={generating} data-testid="generate-sponsor-btn">
          {generating ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Generating…</> : <><Sparkles className="w-4 h-4 mr-2" />Generate Offer</>}
        </Button>
      </div>

      {loading ? <div className="text-gray-500 text-sm">Loading…</div> :
       sponsors.length === 0 ? (
        <div className="text-gray-500 text-sm py-12 text-center glass-surface border border-white/[0.06] rounded-xl" data-testid="sponsors-empty">
          No sponsor offers yet. Generate your first pitch above.
        </div>
      ) : (
        <div className="space-y-3">
          {sponsors.map((s) => {
            const isOpen = expandedId === s.id;
            return (
              <div key={s.id} className="glass-surface border border-white/[0.06] rounded-xl p-5" data-testid={`sponsor-${s.id}`}>
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <Badge className={TIER_STYLES[s.offer_tier] || TIER_STYLES.silver}>{(s.offer_tier || "").toUpperCase()}</Badge>
                      <Badge className={STATUS_STYLES[s.status] || STATUS_STYLES.draft}>{s.status}</Badge>
                      <span className="text-xs text-gray-500">${Math.round(s.suggested_amount_min)}–${Math.round(s.suggested_amount_max)}</span>
                    </div>
                    <h3 className="text-lg font-semibold text-white mt-1 truncate">{s.sponsor_name}</h3>
                    <p className="text-xs text-gray-500 mt-0.5">{s.sponsor_type}</p>
                  </div>
                  <div className="flex items-center gap-1">
                    <Button size="sm" variant="ghost" onClick={() => setExpandedId(isOpen ? null : s.id)} data-testid={`toggle-sponsor-${s.id}`}>
                      {isOpen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                    </Button>
                    <Button size="sm" variant="ghost" onClick={() => del(s.id)} data-testid={`delete-sponsor-${s.id}`}>
                      <Trash2 className="w-4 h-4 text-red-400" />
                    </Button>
                  </div>
                </div>

                {isOpen && (
                  <div className="mt-4 space-y-4 border-t border-white/[0.06] pt-4">
                    {[
                      ["Value Proposition", s.value_proposition],
                      ["Benefits", s.benefits_list],
                      ["Email Subject", s.email_subject],
                      ["Email Body", s.email_body],
                      ["WhatsApp Message", s.whatsapp_message],
                      ["Ad Copy", s.ad_copy],
                      ["Follow-Up Plan", s.follow_up_plan],
                    ].map(([label, val]) => (
                      <div key={label}>
                        <div className="flex items-center justify-between mb-1">
                          <Label className="text-xs text-gray-400">{label}</Label>
                          {val && (
                            <Button size="sm" variant="ghost" className="h-6 px-2" onClick={() => copyText(val)}>
                              <Copy className="w-3 h-3" />
                            </Button>
                          )}
                        </div>
                        <div className="text-sm text-gray-200 whitespace-pre-wrap bg-white/[0.02] rounded-md p-3 border border-white/[0.04]">
                          {val || <span className="text-gray-600">—</span>}
                        </div>
                      </div>
                    ))}

                    <div className="grid md:grid-cols-3 gap-3">
                      <div>
                        <Label className="text-xs text-gray-400">Payment Link</Label>
                        <Select
                          value={s.payment_link_id || ""}
                          onValueChange={(v) => updateField(s.id, { payment_link_id: v })}
                        >
                          <SelectTrigger data-testid={`s-payment-select-${s.id}`}><SelectValue placeholder="None" /></SelectTrigger>
                          <SelectContent>
                            {links.map((l) => <SelectItem key={l.id} value={l.id}>{l.label}</SelectItem>)}
                          </SelectContent>
                        </Select>
                      </div>
                      <div>
                        <Label className="text-xs text-gray-400">Status</Label>
                        <Select value={s.status} onValueChange={(v) => updateField(s.id, { status: v })}>
                          <SelectTrigger data-testid={`s-status-select-${s.id}`}><SelectValue /></SelectTrigger>
                          <SelectContent>
                            <SelectItem value="draft">Draft</SelectItem>
                            <SelectItem value="sent">Sent</SelectItem>
                            <SelectItem value="won">Won</SelectItem>
                            <SelectItem value="lost">Lost</SelectItem>
                            <SelectItem value="archived">Archived</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                    </div>

                    <div className="bg-blue-500/[0.03] border border-blue-500/[0.15] rounded-lg p-3 space-y-2">
                      <div className="flex items-center gap-2 text-xs text-blue-300 font-medium">
                        <Send className="w-3 h-3" />Queue a Mock Send
                      </div>
                      <div className="grid md:grid-cols-4 gap-2">
                        <Select value={enqueueForm.channel} onValueChange={(v) => setEnqueueForm({ ...enqueueForm, channel: v })}>
                          <SelectTrigger data-testid={`s-enq-channel-${s.id}`}><SelectValue /></SelectTrigger>
                          <SelectContent>
                            <SelectItem value="email">Email</SelectItem>
                            <SelectItem value="whatsapp">WhatsApp</SelectItem>
                            <SelectItem value="sms">SMS</SelectItem>
                          </SelectContent>
                        </Select>
                        <Input
                          placeholder="Email / phone"
                          value={enqueueForm.recipient}
                          onChange={(e) => setEnqueueForm({ ...enqueueForm, recipient: e.target.value })}
                          data-testid={`s-enq-recipient-${s.id}`}
                        />
                        <Input
                          placeholder="Label"
                          value={enqueueForm.recipient_label}
                          onChange={(e) => setEnqueueForm({ ...enqueueForm, recipient_label: e.target.value })}
                          data-testid={`s-enq-label-${s.id}`}
                        />
                        <Button size="sm" disabled={enqueuingId === s.id} onClick={() => enqueue(s.id)} data-testid={`s-enq-submit-${s.id}`}>
                          {enqueuingId === s.id ? <Loader2 className="w-3 h-3 animate-spin" /> : "Queue"}
                        </Button>
                      </div>
                    </div>
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
