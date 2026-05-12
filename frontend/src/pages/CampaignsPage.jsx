import React, { useState, useEffect, useCallback } from "react";
import axios from "axios";
import { useAuth } from "@/context/AuthContext";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import {
  HeartHandshake, Sparkles, Loader2, Trash2, Copy, Send,
  ChevronDown, ChevronUp, Tag, RefreshCw,
} from "lucide-react";

import { API } from "../config";

const STATUS_STYLES = {
  draft: "bg-amber-500/10 text-amber-400",
  active: "bg-emerald-500/10 text-emerald-400",
  paused: "bg-gray-500/10 text-gray-400",
  archived: "bg-zinc-500/10 text-zinc-500",
};

function copyText(t) {
  navigator.clipboard.writeText(t || "");
  toast.success("Copied");
}

export default function CampaignsPage() {
  const { authHeaders } = useAuth();
  const [campaigns, setCampaigns] = useState([]);
  const [links, setLinks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [theme, setTheme] = useState("");
  const [minAmt, setMinAmt] = useState(5);
  const [maxAmt, setMaxAmt] = useState(50);
  const [expandedId, setExpandedId] = useState(null);
  const [enqueueForm, setEnqueueForm] = useState({
    channel: "whatsapp",
    recipient: "",
    recipient_label: "",
  });
  const [enqueuingId, setEnqueuingId] = useState(null);

  const fetchAll = useCallback(async () => {
    try {
      const [c, l] = await Promise.all([
        axios.get(`${API}/v11/campaigns`, { headers: authHeaders() }),
        axios.get(`${API}/v11/payment-links`, { headers: authHeaders() }),
      ]);
      setCampaigns(c.data || []);
      setLinks(l.data || []);
    } catch {
      toast.error("Failed to load campaigns");
    } finally {
      setLoading(false);
    }
  }, [authHeaders]);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  const generate = async () => {
    if (!theme.trim()) return toast.error("Enter a theme");
    setGenerating(true);
    try {
      await axios.post(
        `${API}/v11/campaigns/generate`,
        { theme, amount_min: Number(minAmt), amount_max: Number(maxAmt) },
        { headers: authHeaders(), timeout: 180000 },
      );
      toast.success("Campaign generated");
      setTheme("");
      fetchAll();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Generation failed (AI upstream)");
    } finally {
      setGenerating(false);
    }
  };

  const del = async (id) => {
    if (!window.confirm("Delete this campaign?")) return;
    await axios.delete(`${API}/v11/campaigns/${id}`, { headers: authHeaders() });
    toast.success("Deleted");
    fetchAll();
  };

  const updateField = async (id, patch) => {
    try {
      await axios.patch(`${API}/v11/campaigns/${id}`, patch, { headers: authHeaders() });
      fetchAll();
    } catch {
      toast.error("Update failed");
    }
  };

  const enqueue = async (id) => {
    if (!enqueueForm.recipient) return toast.error("Enter recipient");
    setEnqueuingId(id);
    try {
      await axios.post(
        `${API}/v11/campaigns/${id}/enqueue`,
        enqueueForm,
        { headers: authHeaders() },
      );
      toast.success(`Queued (mock ${enqueueForm.channel})`);
      setEnqueueForm({ channel: "whatsapp", recipient: "", recipient_label: "" });
    } catch {
      toast.error("Failed to queue");
    } finally {
      setEnqueuingId(null);
    }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6" data-testid="campaigns-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-semibold text-white tracking-tight flex items-center gap-3">
            <HeartHandshake className="w-7 h-7 text-rose-400" />
            Small Donor Campaigns
          </h1>
          <p className="text-sm text-gray-400 mt-1">AI-generated donation copy for $5–$50 individual donors.</p>
        </div>
        <Button variant="outline" size="sm" onClick={fetchAll} data-testid="refresh-campaigns-btn">
          <RefreshCw className="w-4 h-4 mr-2" />Refresh
        </Button>
      </div>

      {/* Generator */}
      <div className="glass-surface border border-white/[0.06] rounded-xl p-5 space-y-3" data-testid="campaign-generator">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-blue-400" />
          <h2 className="text-sm font-semibold text-white">Generate New Campaign</h2>
        </div>
        <div className="grid md:grid-cols-4 gap-3">
          <div className="md:col-span-2">
            <Label className="text-xs text-gray-400">Theme / Angle</Label>
            <Input
              data-testid="campaign-theme-input"
              placeholder="e.g. Warm winter blankets for street kids in Windhoek"
              value={theme}
              onChange={(e) => setTheme(e.target.value)}
            />
          </div>
          <div>
            <Label className="text-xs text-gray-400">Min $</Label>
            <Input type="number" value={minAmt} onChange={(e) => setMinAmt(e.target.value)} data-testid="campaign-min-input" />
          </div>
          <div>
            <Label className="text-xs text-gray-400">Max $</Label>
            <Input type="number" value={maxAmt} onChange={(e) => setMaxAmt(e.target.value)} data-testid="campaign-max-input" />
          </div>
        </div>
        <Button onClick={generate} disabled={generating} data-testid="generate-campaign-btn">
          {generating ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Generating…</> : <><Sparkles className="w-4 h-4 mr-2" />Generate Campaign</>}
        </Button>
      </div>

      {/* List */}
      {loading ? (
        <div className="text-gray-500 text-sm">Loading…</div>
      ) : campaigns.length === 0 ? (
        <div className="text-gray-500 text-sm py-12 text-center glass-surface border border-white/[0.06] rounded-xl" data-testid="campaigns-empty">
          No campaigns yet. Generate your first one above.
        </div>
      ) : (
        <div className="space-y-3">
          {campaigns.map((c) => {
            const isOpen = expandedId === c.id;
            return (
              <div key={c.id} className="glass-surface border border-white/[0.06] rounded-xl p-5" data-testid={`campaign-${c.id}`}>
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <Badge className={STATUS_STYLES[c.status] || STATUS_STYLES.draft}>{c.status}</Badge>
                      <span className="text-xs text-gray-500">${Math.round(c.suggested_amount_min)}–${Math.round(c.suggested_amount_max)}</span>
                      {c.total_raised > 0 && (
                        <span className="text-xs text-emerald-400">${c.total_raised.toFixed(2)} raised · {c.donor_count} donors</span>
                      )}
                    </div>
                    <h3 className="text-lg font-semibold text-white mt-1 truncate">{c.title || c.theme}</h3>
                    <p className="text-xs text-gray-500 mt-0.5 truncate">{c.theme}</p>
                  </div>
                  <div className="flex items-center gap-1">
                    <Button size="sm" variant="ghost" onClick={() => setExpandedId(isOpen ? null : c.id)} data-testid={`toggle-campaign-${c.id}`}>
                      {isOpen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                    </Button>
                    <Button size="sm" variant="ghost" onClick={() => del(c.id)} data-testid={`delete-campaign-${c.id}`}>
                      <Trash2 className="w-4 h-4 text-red-400" />
                    </Button>
                  </div>
                </div>

                {isOpen && (
                  <div className="mt-4 space-y-4 border-t border-white/[0.06] pt-4">
                    {[
                      ["Story Hook", c.story_hook],
                      ["Short Post", c.short_post],
                      ["Long Post", c.long_post],
                      ["WhatsApp Message", c.whatsapp_message],
                      ["Facebook Ad", c.ad_copy_facebook],
                      ["Instagram Ad", c.ad_copy_instagram],
                      ["Call to Action", c.call_to_action],
                      ["Hashtags", c.hashtags],
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

                    {/* Link payment + status */}
                    <div className="grid md:grid-cols-3 gap-3">
                      <div>
                        <Label className="text-xs text-gray-400">Payment Link</Label>
                        <Select
                          value={c.payment_link_id || ""}
                          onValueChange={(v) => updateField(c.id, { payment_link_id: v })}
                        >
                          <SelectTrigger data-testid={`payment-select-${c.id}`}>
                            <SelectValue placeholder="None" />
                          </SelectTrigger>
                          <SelectContent>
                            {links.map((l) => (
                              <SelectItem key={l.id} value={l.id}>{l.label}</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                      <div>
                        <Label className="text-xs text-gray-400">Status</Label>
                        <Select value={c.status} onValueChange={(v) => updateField(c.id, { status: v })}>
                          <SelectTrigger data-testid={`status-select-${c.id}`}><SelectValue /></SelectTrigger>
                          <SelectContent>
                            <SelectItem value="draft">Draft</SelectItem>
                            <SelectItem value="active">Active</SelectItem>
                            <SelectItem value="paused">Paused</SelectItem>
                            <SelectItem value="archived">Archived</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                    </div>

                    {/* Enqueue */}
                    <div className="bg-blue-500/[0.03] border border-blue-500/[0.15] rounded-lg p-3 space-y-2">
                      <div className="flex items-center gap-2 text-xs text-blue-300 font-medium">
                        <Send className="w-3 h-3" />Queue a Mock Send
                      </div>
                      <div className="grid md:grid-cols-4 gap-2">
                        <Select
                          value={enqueueForm.channel}
                          onValueChange={(v) => setEnqueueForm({ ...enqueueForm, channel: v })}
                        >
                          <SelectTrigger data-testid={`enq-channel-${c.id}`}><SelectValue /></SelectTrigger>
                          <SelectContent>
                            <SelectItem value="whatsapp">WhatsApp</SelectItem>
                            <SelectItem value="email">Email</SelectItem>
                            <SelectItem value="sms">SMS</SelectItem>
                          </SelectContent>
                        </Select>
                        <Input
                          placeholder="Recipient (phone/email)"
                          value={enqueueForm.recipient}
                          onChange={(e) => setEnqueueForm({ ...enqueueForm, recipient: e.target.value })}
                          data-testid={`enq-recipient-${c.id}`}
                        />
                        <Input
                          placeholder="Label (optional)"
                          value={enqueueForm.recipient_label}
                          onChange={(e) => setEnqueueForm({ ...enqueueForm, recipient_label: e.target.value })}
                          data-testid={`enq-label-${c.id}`}
                        />
                        <Button
                          size="sm"
                          disabled={enqueuingId === c.id}
                          onClick={() => enqueue(c.id)}
                          data-testid={`enq-submit-${c.id}`}
                        >
                          {enqueuingId === c.id ? <Loader2 className="w-3 h-3 animate-spin" /> : "Queue"}
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
