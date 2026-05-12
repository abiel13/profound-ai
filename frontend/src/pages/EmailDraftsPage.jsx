import React, { useState, useEffect, useCallback } from "react";
import axios from "axios";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
  Mail, Sparkles, Loader2, Copy, Send, Clock, Trash2, CheckCircle,
} from "lucide-react";

import { API } from "../config";
import { useAuth } from "@/context/AuthContext";

const KINDS = [
  { value: "grant", label: "Grant application" },
  { value: "sponsor", label: "Sponsor outreach" },
  { value: "thank_you", label: "Donor thank-you" },
  { value: "follow_up", label: "Follow-up" },
  { value: "reapply", label: "Re-application" },
];

export default function EmailDraftsPage() {
  const { authHeaders } = useAuth();
  const [form, setForm] = useState({
    kind: "grant", recipient_name: "", recipient_email: "",
    organization: "", context: "",
  });
  const [drafts, setDrafts] = useState([]);
  const [generating, setGenerating] = useState(false);
  const [active, setActive] = useState(null);

  const fetchDrafts = useCallback(async () => {
    try {
      const res = await axios.get(`${API}/automation/email-drafts`, { headers: authHeaders() });
      setDrafts(res.data || []);
    } catch { /* ignore */ }
  }, [authHeaders]);

  useEffect(() => { fetchDrafts(); }, [fetchDrafts]);

  const onChange = (k, v) => setForm(p => ({ ...p, [k]: v }));

  const generate = async () => {
    setGenerating(true);
    try {
      const res = await axios.post(`${API}/automation/email-drafts/generate`, { ...form, save: true }, { headers: authHeaders() });
      setActive(res.data);
      toast.success("Draft generated");
      fetchDrafts();
    } catch {
      toast.error("AI key required for generation — falling back to template");
    } finally {
      setGenerating(false);
    }
  };

  const copy = (label, text) => {
    navigator.clipboard.writeText(text || "");
    toast.success(`Copied ${label}`);
  };

  const openMail = () => {
    if (!active) return;
    const subject = encodeURIComponent(active.subject || "");
    const body = encodeURIComponent(active.body || "");
    const to = encodeURIComponent(form.recipient_email || "");
    window.location.href = `mailto:${to}?subject=${subject}&body=${body}`;
  };

  const markSent = async (id) => {
    await axios.put(`${API}/automation/email-drafts/${id}/mark-sent`, {}, { headers: authHeaders() });
    toast.success("Marked sent");
    fetchDrafts();
  };

  const scheduleFollowUp = async (id) => {
    await axios.put(`${API}/automation/email-drafts/${id}/follow-up`, {}, { headers: authHeaders() });
    toast.success("Follow-up flagged");
    fetchDrafts();
  };

  const removeDraft = async (id) => {
    await axios.delete(`${API}/automation/email-drafts/${id}`, { headers: authHeaders() });
    fetchDrafts();
    if (active && active.id === id) setActive(null);
  };

  const statusBadge = (s) => {
    if (s === "sent") return <Badge className="bg-emerald-600/15 text-emerald-400 border-0 text-[10px]">sent</Badge>;
    if (s === "follow_up_needed") return <Badge className="bg-amber-500/15 text-amber-400 border-0 text-[10px]">follow-up</Badge>;
    return <Badge className="bg-white/5 text-gray-400 border-0 text-[10px]">draft</Badge>;
  };

  return (
    <div className="space-y-6 animate-fade-in" data-testid="email-drafts-page">
      <div className="flex items-center gap-3">
        <Mail className="w-7 h-7 text-purple-400" />
        <div>
          <h1 className="text-2xl sm:text-3xl font-semibold text-white tracking-tight" style={{ fontFamily: "Outfit" }}>
            Email Drafts
          </h1>
          <p className="text-sm text-gray-400 mt-0.5">AI-generated drafts for grants, sponsors, donors, follow-ups, re-applications. Never auto-sent.</p>
        </div>
      </div>

      {/* Generator */}
      <div className="bg-[#12141A] border border-white/[0.05] rounded-xl p-5 space-y-4" data-testid="draft-form">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Field label="Email type">
            <Select value={form.kind} onValueChange={v => onChange("kind", v)}>
              <SelectTrigger className="bg-[#0B0C10] border-white/10 text-gray-200 h-10" data-testid="select-kind"><SelectValue /></SelectTrigger>
              <SelectContent className="bg-[#1A1D24] border-white/10">
                {KINDS.map(k => <SelectItem key={k.value} value={k.value} className="text-gray-200">{k.label}</SelectItem>)}
              </SelectContent>
            </Select>
          </Field>
          <Field label="Recipient name"><Input value={form.recipient_name} onChange={e => onChange("recipient_name", e.target.value)} placeholder="e.g. Maria" className="bg-[#0B0C10] border-white/10 text-white" data-testid="input-recipient-name" /></Field>
          <Field label="Recipient email"><Input value={form.recipient_email} onChange={e => onChange("recipient_email", e.target.value)} placeholder="name@org.com" className="bg-[#0B0C10] border-white/10 text-white" data-testid="input-recipient-email" /></Field>
          <Field label="Organization"><Input value={form.organization} onChange={e => onChange("organization", e.target.value)} placeholder="e.g. Bank Windhoek" className="bg-[#0B0C10] border-white/10 text-white" data-testid="input-organization" /></Field>
          <Field label="Context / topic" full><Textarea value={form.context} onChange={e => onChange("context", e.target.value)} rows={3} placeholder="e.g. school fees drive for 30 children" className="bg-[#0B0C10] border-white/10 text-white" data-testid="input-context" /></Field>
        </div>
        <Button onClick={generate} disabled={generating} data-testid="generate-draft-btn" className="bg-purple-600 hover:bg-purple-500 text-white">
          {generating ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Sparkles className="w-4 h-4 mr-2" />}
          Generate Draft
        </Button>
      </div>

      {/* Active draft */}
      {active && (
        <div className="bg-[#12141A] border border-white/[0.05] rounded-xl p-5 space-y-3" data-testid="active-draft">
          <div className="flex items-center gap-2">
            <Badge className="bg-purple-600/15 text-purple-300 border-0 text-[10px]">{active.draft_type || form.kind}</Badge>
          </div>
          <div>
            <p className="text-[10px] text-gray-500 uppercase tracking-wider mb-1">Subject</p>
            <p className="text-sm text-white">{active.subject}</p>
          </div>
          <div>
            <p className="text-[10px] text-gray-500 uppercase tracking-wider mb-1">Body</p>
            <pre className="bg-[#0B0C10] border border-white/[0.06] rounded-lg p-3 text-sm text-gray-200 whitespace-pre-wrap font-sans" data-testid="active-body">{active.body}</pre>
          </div>
          {active.cta && (<p className="text-xs text-gray-400"><b>CTA:</b> {active.cta}</p>)}
          {Array.isArray(active.attachments) && active.attachments.length > 0 && (
            <div>
              <p className="text-[10px] text-gray-500 uppercase tracking-wider mb-1">Attachments checklist</p>
              <ul className="list-disc list-inside text-xs text-gray-300 space-y-0.5">{active.attachments.map((a, i) => <li key={i}>{a}</li>)}</ul>
            </div>
          )}
          <div className="flex flex-wrap gap-2 pt-2 border-t border-white/[0.05]">
            <Button onClick={() => copy("subject", active.subject)} variant="outline" className="border-white/10 text-gray-300 text-xs" data-testid="copy-subject-btn"><Copy className="w-3.5 h-3.5 mr-2" />Copy Subject</Button>
            <Button onClick={() => copy("body", active.body)} variant="outline" className="border-white/10 text-gray-300 text-xs" data-testid="copy-body-btn"><Copy className="w-3.5 h-3.5 mr-2" />Copy Body</Button>
            <Button onClick={openMail} className="bg-blue-600 hover:bg-blue-500 text-white text-xs" data-testid="open-mail-btn"><Send className="w-3.5 h-3.5 mr-2" />Open Mail Client</Button>
            <Button onClick={() => markSent(active.id)} variant="outline" className="border-white/10 text-gray-300 text-xs" data-testid="mark-sent-btn"><CheckCircle className="w-3.5 h-3.5 mr-2" />Mark Sent</Button>
            <Button onClick={() => scheduleFollowUp(active.id)} variant="outline" className="border-white/10 text-gray-300 text-xs" data-testid="follow-up-btn"><Clock className="w-3.5 h-3.5 mr-2" />Schedule Follow-Up</Button>
          </div>
        </div>
      )}

      {/* History */}
      <div className="bg-[#12141A] border border-white/[0.05] rounded-xl p-5" data-testid="draft-history">
        <h3 className="text-sm font-medium text-white mb-3" style={{ fontFamily: "Outfit" }}>Saved drafts</h3>
        {drafts.length === 0 ? (
          <p className="text-sm text-gray-500">No drafts yet.</p>
        ) : (
          <div className="space-y-2">
            {drafts.map(d => (
              <div key={d.id} className="flex items-center gap-3 bg-[#0B0C10] border border-white/[0.06] rounded-lg px-4 py-3" data-testid={`draft-${d.id}`}>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    {statusBadge(d.status)}
                    <Badge className="bg-white/5 text-gray-300 border-0 text-[10px]">{d.draft_type}</Badge>
                    <span className="text-sm text-white truncate">{d.subject || "(no subject)"}</span>
                  </div>
                  <p className="text-xs text-gray-500 truncate">{d.recipient_name || "(no recipient)"} — {d.organization || "—"}</p>
                </div>
                <Button size="sm" onClick={() => setActive({ ...d, attachments: d.attachments || [] })} variant="outline" className="border-white/10 text-gray-300 text-xs">Open</Button>
                <button onClick={() => removeDraft(d.id)} className="text-gray-600 hover:text-red-400"><Trash2 className="w-4 h-4" /></button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function Field({ label, children, full }) {
  return (
    <div className={full ? "md:col-span-2" : ""}>
      <p className="text-xs text-gray-400 mb-1.5">{label}</p>
      {children}
    </div>
  );
}
