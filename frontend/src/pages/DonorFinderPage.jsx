import React, { useState, useEffect, useCallback } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Users2, Sparkles, Loader2, Copy, ExternalLink, Mail, Trash2, RefreshCw, SendHorizontal, Handshake,
} from "lucide-react";

import { API } from "../config";
import { useAuth } from "@/context/AuthContext";

const CATEGORIES = [
  "Namibian companies", "banks", "pharmacies", "supermarkets",
  "lodges/hotels", "churches", "embassies", "CSR departments",
  "foundations", "NGOs", "international donors", "local businesses",
];

export default function DonorFinderPage() {
  const { authHeaders } = useAuth();
  const navigate = useNavigate();
  const [categories, setCategories] = useState(["banks", "embassies", "Namibian companies", "supermarkets"]);
  const [country, setCountry] = useState("Namibia");
  const [city, setCity] = useState("Windhoek");
  const [prospects, setProspects] = useState([]);
  const [generating, setGenerating] = useState(false);

  const fetchProspects = useCallback(async () => {
    try {
      const res = await axios.get(`${API}/automation/donors`, { headers: authHeaders() });
      setProspects(res.data || []);
    } catch { /* ignore */ }
  }, [authHeaders]);

  useEffect(() => { fetchProspects(); }, [fetchProspects]);

  const toggleCategory = (c) => setCategories(p => p.includes(c) ? p.filter(x => x !== c) : [...p, c]);

  const generate = async () => {
    setGenerating(true);
    try {
      const res = await axios.post(`${API}/automation/donors/generate`, { categories, country, city, save: true }, { headers: authHeaders() });
      toast.success(`${res.data.saved || (res.data.prospects || []).length} prospects added`);
      fetchProspects();
    } catch { toast.error("Generation failed — previous results kept"); }
    finally { setGenerating(false); }
  };

  const updateStatus = async (id, status) => {
    await axios.put(`${API}/automation/donors/${id}/status`, { status }, { headers: authHeaders() });
    setProspects(p => p.map(x => x.id === id ? { ...x, status } : x));
    toast.success(`Marked ${status}`);
  };

  const removeProspect = async (id) => {
    await axios.delete(`${API}/automation/donors/${id}`, { headers: authHeaders() });
    setProspects(p => p.filter(x => x.id !== id));
  };

  const generateSponsorEmail = (p) => {
    const params = new URLSearchParams({
      kind: "sponsor", org: p.organization || "", ctx: p.suggested_campaign || p.outreach_angle || "",
    });
    navigate(`/email-drafts?${params.toString()}`);
  };

  const copy = (label, text) => {
    navigator.clipboard.writeText(text || "");
    toast.success(`Copied ${label}`);
  };

  return (
    <div className="space-y-6 animate-fade-in" data-testid="donor-finder-page">
      <div className="flex items-center gap-3">
        <Users2 className="w-7 h-7 text-emerald-400" />
        <div>
          <h1 className="text-2xl sm:text-3xl font-semibold text-white tracking-tight" style={{ fontFamily: "Outfit" }}>
            Donor Finder
          </h1>
          <p className="text-sm text-gray-400 mt-0.5">Generate targeted donor & sponsor prospects. Contact details are NEVER invented — blank = manual lookup required.</p>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-[#12141A] border border-white/[0.05] rounded-xl p-5 space-y-4" data-testid="donor-filters">
        <div>
          <p className="text-xs text-gray-400 mb-2">Prospect categories</p>
          <div className="flex flex-wrap gap-2">
            {CATEGORIES.map(c => (
              <button key={c} onClick={() => toggleCategory(c)}
                data-testid={`chip-cat-${c.replace(/\W+/g, "-")}`}
                className={`px-3 py-1.5 rounded-full text-xs border transition-colors ${categories.includes(c) ? "bg-emerald-600/15 border-emerald-500/30 text-emerald-300" : "bg-[#0B0C10] border-white/10 text-gray-400 hover:text-white"}`}>
                {c}
              </button>
            ))}
          </div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div><p className="text-xs text-gray-400 mb-1.5">Country</p><Input value={country} onChange={e => setCountry(e.target.value)} className="bg-[#0B0C10] border-white/10 text-white" data-testid="input-country" /></div>
          <div><p className="text-xs text-gray-400 mb-1.5">City</p><Input value={city} onChange={e => setCity(e.target.value)} className="bg-[#0B0C10] border-white/10 text-white" data-testid="input-city" /></div>
        </div>
        <div className="flex items-center gap-3">
          <Button onClick={generate} disabled={generating} data-testid="generate-donors-btn" className="bg-emerald-600 hover:bg-emerald-500 text-white">
            {generating ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Sparkles className="w-4 h-4 mr-2" />}
            Generate Donor List
          </Button>
          <Button onClick={fetchProspects} variant="outline" className="border-white/10 text-gray-300 text-xs" data-testid="refresh-btn">
            <RefreshCw className="w-3.5 h-3.5 mr-2" />Refresh
          </Button>
        </div>
      </div>

      {/* Prospects */}
      <div className="space-y-2" data-testid="prospects-list">
        {prospects.length === 0 ? (
          <div className="text-center py-10 text-sm text-gray-500">No prospects yet — click "Generate Donor List".</div>
        ) : prospects.map(p => (
          <div key={p.id} className="bg-[#12141A] border border-white/[0.05] rounded-xl p-4" data-testid={`prospect-${p.id}`}>
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2 flex-wrap mb-1">
                  <Badge className={`border-0 text-[10px] ${p.priority_score >= 70 ? "bg-emerald-600/15 text-emerald-400" : p.priority_score >= 50 ? "bg-blue-600/15 text-blue-400" : "bg-white/5 text-gray-400"}`}>Pri {p.priority_score}</Badge>
                  <Badge className="bg-white/5 border-0 text-gray-300 text-[10px]">{p.category}</Badge>
                  {p.manual_lookup_required ? (
                    <Badge className="bg-amber-500/15 text-amber-300 border-0 text-[10px]">manual lookup required</Badge>
                  ) : (
                    <Badge className="bg-emerald-500/10 text-emerald-300 border-0 text-[10px]">contact known</Badge>
                  )}
                  {p.status !== "new" && <Badge className="bg-white/5 text-gray-300 border-0 text-[10px]">{p.status}</Badge>}
                </div>
                <p className="text-sm font-medium text-white">{p.organization}</p>
                <p className="text-xs text-gray-400 mt-0.5">{p.outreach_angle}</p>
                <div className="flex flex-wrap items-center gap-3 text-[11px] text-gray-500 mt-2">
                  <span>{p.city}{p.city && p.country ? ", " : ""}{p.country}</span>
                  {p.website && <a href={p.website} target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:underline inline-flex items-center gap-1"><ExternalLink className="w-3 h-3" />{p.website}</a>}
                  <span>· {p.suggested_amount}</span>
                  <span>· {p.suggested_campaign}</span>
                </div>
                {(p.email || p.phone) && (
                  <div className="flex flex-wrap items-center gap-3 text-[11px] text-gray-400 mt-1">
                    {p.email && (<span className="inline-flex items-center gap-1"><Mail className="w-3 h-3" />{p.email} <button onClick={() => copy("email", p.email)} className="ml-1 text-gray-500 hover:text-emerald-400"><Copy className="w-3 h-3" /></button></span>)}
                    {p.phone && <span>· {p.phone}</span>}
                  </div>
                )}
              </div>
              <div className="flex flex-col gap-2 shrink-0">
                <Button size="sm" onClick={() => generateSponsorEmail(p)} className="bg-purple-600 hover:bg-purple-500 text-white text-xs" data-testid={`email-${p.id}`}>
                  <Mail className="w-3.5 h-3.5 mr-1.5" />Generate Sponsor Email
                </Button>
                <Button size="sm" onClick={() => updateStatus(p.id, "contacted")} variant="outline" className="border-white/10 text-gray-300 text-xs" data-testid={`contact-${p.id}`}>
                  <Handshake className="w-3.5 h-3.5 mr-1.5" />Mark Contacted
                </Button>
                <Button size="sm" onClick={() => updateStatus(p.id, "rejected")} variant="outline" className="border-white/10 text-gray-500 text-xs" data-testid={`reject-${p.id}`}>Reject</Button>
                <button onClick={() => removeProspect(p.id)} className="text-gray-600 hover:text-red-400 text-xs" data-testid={`del-${p.id}`}><Trash2 className="w-3.5 h-3.5 inline" /></button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
