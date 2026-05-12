import React, { useState, useEffect, useCallback } from "react";
import axios from "axios";
import { useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
  Music2, Sparkles, Loader2, Copy, Trash2, FileDown, Hash,
  MessageCircle, Facebook, ShieldCheck, Wand2
} from "lucide-react";
import jsPDF from "jspdf";

import { API } from "../config";
import { useAuth } from "@/context/AuthContext";

const CAUSES = [
  { value: "school_fees", label: "School fees" },
  { value: "food_parcels", label: "Food parcels" },
  { value: "clothing", label: "Clothing" },
  { value: "abuse_protection", label: "Abuse protection" },
  { value: "safe_housing", label: "Safe housing" },
  { value: "street_children", label: "Street children" },
  { value: "emergency_support", label: "Emergency support" },
];

const TONES = [
  { value: "emotional", label: "Emotional" },
  { value: "urgent", label: "Urgent" },
  { value: "hopeful", label: "Hopeful" },
  { value: "transparent", label: "Transparent" },
];

function copyText(label, text) {
  navigator.clipboard.writeText(text);
  toast.success(`Copied ${label}`);
}

export default function TikTokCampaignsPage() {
  const { authHeaders } = useAuth();
  const [searchParams] = useSearchParams();
  const [form, setForm] = useState({
    campaign_title: searchParams.get("title") || "",
    target_amount: searchParams.get("target") || "",
    cause_category: "school_fees",
    location: "Windhoek",
    deadline: "30 days",
    donation_link: searchParams.get("link") || "",
    tone: "emotional",
  });
  const [pack, setPack] = useState(null);
  const [generating, setGenerating] = useState(false);
  const [saved, setSaved] = useState([]);

  const fetchSaved = useCallback(async () => {
    try {
      const res = await axios.get(`${API}/v11/tiktok`, { headers: authHeaders() });
      setSaved(res.data || []);
    } catch { /* ignore */ }
  }, [authHeaders]);

  useEffect(() => { fetchSaved(); }, [fetchSaved]);

  const onChange = (k, v) => setForm(prev => ({ ...prev, [k]: v }));

  const generate = async () => {
    if (!form.campaign_title || !form.target_amount) {
      toast.error("Please fill the campaign title and target amount");
      return;
    }
    setGenerating(true);
    try {
      const res = await axios.post(`${API}/v11/tiktok/generate`, { ...form, save: true }, { headers: authHeaders() });
      setPack(res.data);
      toast.success("TikTok pack generated");
      fetchSaved();
    } catch (e) {
      toast.error("Generation failed - try again");
    } finally {
      setGenerating(false);
    }
  };

  const loadSaved = async (id) => {
    const res = await axios.get(`${API}/v11/tiktok/${id}`, { headers: authHeaders() });
    setPack({ ...res.data.pack, id: res.data.id });
    // Restore form values
    setForm({
      campaign_title: res.data.campaign_title,
      target_amount: res.data.target_amount,
      cause_category: res.data.cause_category,
      location: res.data.location,
      deadline: res.data.deadline,
      donation_link: res.data.donation_link,
      tone: res.data.tone,
    });
  };

  const deleteSaved = async (id) => {
    await axios.delete(`${API}/v11/tiktok/${id}`, { headers: authHeaders() });
    toast.success("Deleted");
    fetchSaved();
    if (pack && pack.id === id) setPack(null);
  };

  const downloadPdf = () => {
    if (!pack) return;
    const doc = new jsPDF({ unit: "pt", format: "a4" });
    const margin = 48;
    const pageWidth = doc.internal.pageSize.getWidth();
    const pageHeight = doc.internal.pageSize.getHeight();
    const usable = pageWidth - margin * 2;
    let y = margin;

    const writeBlock = (title, body, extraSpace = 8) => {
      if (y > pageHeight - margin - 60) { doc.addPage(); y = margin; }
      doc.setFont("helvetica", "bold"); doc.setFontSize(13);
      doc.text(title, margin, y); y += 18;
      doc.setFont("helvetica", "normal"); doc.setFontSize(10);
      const lines = doc.splitTextToSize(body, usable);
      lines.forEach(l => {
        if (y > pageHeight - margin) { doc.addPage(); y = margin; }
        doc.text(l, margin, y); y += 13;
      });
      y += extraSpace;
    };

    doc.setFont("helvetica", "bold"); doc.setFontSize(18);
    doc.text(form.campaign_title || "TikTok Campaign Pack", margin, y); y += 22;
    doc.setFont("helvetica", "normal"); doc.setFontSize(10); doc.setTextColor(120);
    doc.text(`Target NAD ${form.target_amount} • ${form.location} • ${form.deadline}`, margin, y); y += 18;
    doc.setTextColor(0);

    (pack.scripts || []).forEach((s, i) => {
      const text = `Hook: ${s.hook}\nVisual: ${s.visual}\nVoice-over: ${s.voiceover}\nOn-screen: ${s.on_screen_text}\nCTA: ${s.cta}\nLength: ${s.length_seconds}s`;
      writeBlock(`Script ${i + 1}`, text, 12);
    });
    writeBlock("Captions", (pack.captions || []).map((c, i) => `${i + 1}. ${c}`).join("\n"));
    writeBlock("Hashtags", (pack.hashtags || []).join(" "));
    writeBlock("WhatsApp Message", pack.whatsapp_message || "");
    writeBlock("Facebook Post", pack.facebook_post || "");
    writeBlock("Donor Trust Checklist", (pack.trust_checklist || []).map((t, i) => `${i + 1}. ${t}`).join("\n"));

    const safe = (form.campaign_title || "tiktok_campaign").replace(/[^a-z0-9]+/gi, "_").slice(0, 60);
    doc.save(`${safe}.pdf`);
    toast.success("PDF downloaded");
  };

  return (
    <div className="space-y-6 animate-fade-in" data-testid="tiktok-campaigns-page">
      <div className="flex items-center gap-3">
        <Music2 className="w-7 h-7 text-pink-400" />
        <div>
          <h1 className="text-2xl sm:text-3xl font-semibold text-white tracking-tight" style={{ fontFamily: "Outfit" }}>
            TikTok Donation Campaigns
          </h1>
          <p className="text-sm text-gray-400 mt-0.5">
            Build a complete TikTok pack — scripts, captions, hashtags, WhatsApp, Facebook, donor trust checklist.
          </p>
        </div>
      </div>

      {/* Form */}
      <div className="bg-[#12141A] border border-white/[0.05] rounded-xl p-5 space-y-4" data-testid="tiktok-form">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Field label="Campaign title" testid="field-title">
            <Input value={form.campaign_title} onChange={e => onChange("campaign_title", e.target.value)} placeholder="e.g. Warm clothes for 30 children" className="bg-[#0B0C10] border-white/10 text-white" data-testid="input-title" />
          </Field>
          <Field label="Target amount (NAD)" testid="field-amount">
            <Input value={form.target_amount} onChange={e => onChange("target_amount", e.target.value)} placeholder="e.g. 5000" className="bg-[#0B0C10] border-white/10 text-white" data-testid="input-amount" />
          </Field>
          <Field label="Cause category" testid="field-cause">
            <Select value={form.cause_category} onValueChange={v => onChange("cause_category", v)}>
              <SelectTrigger className="bg-[#0B0C10] border-white/10 text-gray-200 h-10" data-testid="select-cause"><SelectValue /></SelectTrigger>
              <SelectContent className="bg-[#1A1D24] border-white/10">
                {CAUSES.map(c => <SelectItem key={c.value} value={c.value} className="text-gray-200">{c.label}</SelectItem>)}
              </SelectContent>
            </Select>
          </Field>
          <Field label="Tone" testid="field-tone">
            <Select value={form.tone} onValueChange={v => onChange("tone", v)}>
              <SelectTrigger className="bg-[#0B0C10] border-white/10 text-gray-200 h-10" data-testid="select-tone"><SelectValue /></SelectTrigger>
              <SelectContent className="bg-[#1A1D24] border-white/10">
                {TONES.map(t => <SelectItem key={t.value} value={t.value} className="text-gray-200">{t.label}</SelectItem>)}
              </SelectContent>
            </Select>
          </Field>
          <Field label="Location" testid="field-location">
            <Input value={form.location} onChange={e => onChange("location", e.target.value)} className="bg-[#0B0C10] border-white/10 text-white" data-testid="input-location" />
          </Field>
          <Field label="Deadline" testid="field-deadline">
            <Input value={form.deadline} onChange={e => onChange("deadline", e.target.value)} placeholder="e.g. 30 days" className="bg-[#0B0C10] border-white/10 text-white" data-testid="input-deadline" />
          </Field>
          <Field label="Donation link" testid="field-link" full>
            <Input value={form.donation_link} onChange={e => onChange("donation_link", e.target.value)} placeholder="https://paypal.me/..." className="bg-[#0B0C10] border-white/10 text-white" data-testid="input-link" />
          </Field>
        </div>
        <Button onClick={generate} disabled={generating} data-testid="generate-btn" className="bg-pink-600 hover:bg-pink-500 text-white">
          {generating ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Sparkles className="w-4 h-4 mr-2" />}
          Generate TikTok Content
        </Button>
      </div>

      {/* Output */}
      {pack && (
        <div className="space-y-5" data-testid="tiktok-output">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-medium text-white" style={{ fontFamily: "Outfit" }}>Your TikTok Pack</h2>
            <Button onClick={downloadPdf} data-testid="download-pdf-btn" variant="outline" className="border-white/10 text-gray-300 text-xs">
              <FileDown className="w-3.5 h-3.5 mr-2" />Download Campaign Pack as PDF
            </Button>
          </div>

          {/* Scripts */}
          <Section title="5 Video Scripts" icon={Wand2}>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {(pack.scripts || []).map((s, i) => (
                <div key={i} className="bg-[#0B0C10] border border-white/[0.06] rounded-lg p-4 text-sm space-y-2" data-testid={`script-${i}`}>
                  <div className="flex items-center justify-between">
                    <Badge className="bg-pink-600/15 text-pink-400 border-0 text-[10px]">Script {i + 1} • {s.length_seconds}s</Badge>
                    <button onClick={() => copyText(`Script ${i + 1}`, JSON.stringify(s, null, 2))} className="text-gray-500 hover:text-pink-400" data-testid={`copy-script-${i}`}><Copy className="w-3.5 h-3.5" /></button>
                  </div>
                  <Row label="Hook" value={s.hook} />
                  <Row label="Visual" value={s.visual} />
                  <Row label="Voice-over" value={s.voiceover} />
                  <Row label="On-screen" value={s.on_screen_text} />
                  <Row label="CTA" value={s.cta} />
                </div>
              ))}
            </div>
          </Section>

          {/* Captions */}
          <Section title="10 Captions" icon={MessageCircle}>
            <ul className="space-y-2">
              {(pack.captions || []).map((c, i) => (
                <li key={i} className="bg-[#0B0C10] border border-white/[0.06] rounded-lg p-3 text-sm text-gray-200 flex items-start gap-3" data-testid={`caption-${i}`}>
                  <span className="text-xs text-gray-500 w-5 shrink-0">#{i + 1}</span>
                  <span className="flex-1">{c}</span>
                  <button onClick={() => copyText(`Caption ${i + 1}`, c)} className="text-gray-500 hover:text-pink-400" data-testid={`copy-caption-${i}`}><Copy className="w-3.5 h-3.5" /></button>
                </li>
              ))}
            </ul>
            <div className="mt-3"><Button variant="outline" onClick={() => copyText("All captions", (pack.captions || []).join("\n"))} className="border-white/10 text-gray-300 text-xs" data-testid="copy-all-captions">
              <Copy className="w-3.5 h-3.5 mr-2" />Copy all captions
            </Button></div>
          </Section>

          {/* Hashtags */}
          <Section title="30 Hashtags" icon={Hash}>
            <div className="flex flex-wrap gap-2 mb-3">
              {(pack.hashtags || []).map((h, i) => (
                <Badge key={i} className="bg-pink-600/10 text-pink-300 border-0 text-xs" data-testid={`hashtag-${i}`}>{h}</Badge>
              ))}
            </div>
            <Button variant="outline" onClick={() => copyText("hashtags", (pack.hashtags || []).join(" "))} className="border-white/10 text-gray-300 text-xs" data-testid="copy-hashtags">
              <Copy className="w-3.5 h-3.5 mr-2" />Copy Hashtags
            </Button>
          </Section>

          {/* Messages */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Section title="WhatsApp Share Message" icon={MessageCircle}>
              <Textarea value={pack.whatsapp_message || ""} readOnly rows={5} className="bg-[#0B0C10] border-white/10 text-gray-200 text-sm" data-testid="textarea-whatsapp" />
              <Button variant="outline" onClick={() => copyText("WhatsApp message", pack.whatsapp_message || "")} className="mt-2 border-white/10 text-gray-300 text-xs" data-testid="copy-whatsapp">
                <Copy className="w-3.5 h-3.5 mr-2" />Copy WhatsApp Message
              </Button>
            </Section>
            <Section title="Facebook Post" icon={Facebook}>
              <Textarea value={pack.facebook_post || ""} readOnly rows={5} className="bg-[#0B0C10] border-white/10 text-gray-200 text-sm" data-testid="textarea-facebook" />
              <Button variant="outline" onClick={() => copyText("Facebook post", pack.facebook_post || "")} className="mt-2 border-white/10 text-gray-300 text-xs" data-testid="copy-facebook">
                <Copy className="w-3.5 h-3.5 mr-2" />Copy Facebook Post
              </Button>
            </Section>
          </div>

          {/* Trust */}
          <Section title="Donor Trust Checklist" icon={ShieldCheck}>
            <ul className="space-y-2">
              {(pack.trust_checklist || []).map((t, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-gray-300" data-testid={`trust-${i}`}>
                  <ShieldCheck className="w-4 h-4 text-emerald-400 mt-0.5 shrink-0" />{t}
                </li>
              ))}
            </ul>
          </Section>
        </div>
      )}

      {/* Saved list */}
      {saved.length > 0 && (
        <div className="bg-[#12141A] border border-white/[0.05] rounded-xl p-5" data-testid="tiktok-saved">
          <h3 className="text-sm font-medium text-white mb-3" style={{ fontFamily: "Outfit" }}>Saved TikTok Campaigns</h3>
          <div className="space-y-2">
            {saved.map(s => (
              <div key={s.id} className="flex items-center justify-between gap-3 bg-[#0B0C10] border border-white/[0.06] rounded-lg px-4 py-3">
                <div className="min-w-0">
                  <p className="text-sm text-white truncate">{s.campaign_title || "(untitled)"}</p>
                  <p className="text-xs text-gray-500 truncate">{s.cause_category} • NAD {s.target_amount} • {s.location} • {s.deadline}</p>
                </div>
                <div className="flex items-center gap-2">
                  <Button onClick={() => loadSaved(s.id)} variant="outline" className="border-white/10 text-gray-300 text-xs h-8" data-testid={`load-${s.id}`}>Open</Button>
                  <button onClick={() => deleteSaved(s.id)} className="text-gray-500 hover:text-red-400" data-testid={`delete-${s.id}`}><Trash2 className="w-4 h-4" /></button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function Field({ label, children, full, testid }) {
  return (
    <div className={full ? "md:col-span-2" : ""} data-testid={testid}>
      <p className="text-xs text-gray-400 mb-1.5">{label}</p>
      {children}
    </div>
  );
}
function Section({ title, icon: Icon, children }) {
  return (
    <div className="bg-[#12141A] border border-white/[0.05] rounded-xl p-5">
      <div className="flex items-center gap-2 mb-3">
        {Icon && <Icon className="w-4 h-4 text-pink-400" />}
        <h3 className="text-sm font-medium text-white" style={{ fontFamily: "Outfit" }}>{title}</h3>
      </div>
      {children}
    </div>
  );
}
function Row({ label, value }) {
  return (
    <div>
      <span className="text-[10px] text-gray-500 uppercase tracking-wider">{label}</span>
      <p className="text-gray-200 text-sm leading-relaxed">{value}</p>
    </div>
  );
}
