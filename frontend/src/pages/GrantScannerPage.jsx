import React, { useState, useEffect, useCallback } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
  Radar, Sparkles, Loader2, ExternalLink, RefreshCw, Bookmark, Wand2, Trash2,
} from "lucide-react";

import { API } from "../config";
import { useAuth } from "@/context/AuthContext";

const SECTORS = [
  "child protection", "safe housing", "education", "food security",
  "women/mothers support", "street children", "poverty relief",
];
const REGIONS = ["Namibia", "Africa", "International"];
const SOURCES = [
  "UNICEF", "UNDP", "EU Funding & Tenders", "USAID", "GIZ",
  "African Development Bank", "GlobalGiving", "Gates Foundation",
  "Ford Foundation", "Embassy small grants", "NGO funding calls",
];

export default function GrantScannerPage() {
  const { authHeaders } = useAuth();
  const navigate = useNavigate();
  const [sectors, setSectors] = useState([]);
  const [region, setRegion] = useState("Africa");
  const [sources, setSources] = useState(SOURCES);
  const [results, setResults] = useState([]);
  const [scanning, setScanning] = useState(false);

  const fetchResults = useCallback(async () => {
    try {
      const res = await axios.get(`${API}/automation/grants/results`, { headers: authHeaders() });
      setResults(res.data || []);
    } catch { /* ignore */ }
  }, [authHeaders]);

  useEffect(() => { fetchResults(); }, [fetchResults]);

  const toggleSector = (s) => setSectors(p => p.includes(s) ? p.filter(x => x !== s) : [...p, s]);
  const toggleSource = (s) => setSources(p => p.includes(s) ? p.filter(x => x !== s) : [...p, s]);

  const scan = async () => {
    setScanning(true);
    try {
      const res = await axios.post(`${API}/automation/grants/scan`, {
        sectors, region, sources, save: true,
      }, { headers: authHeaders() });
      toast.success(`${res.data.saved || res.data.items.length} grants added`);
      fetchResults();
    } catch (e) {
      toast.error("Scan failed — previous results kept");
    } finally {
      setScanning(false);
    }
  };

  const updateStatus = async (id, status) => {
    try {
      await axios.put(`${API}/automation/grants/results/${id}/status`, { status }, { headers: authHeaders() });
      setResults(p => p.map(r => r.id === id ? { ...r, status } : r));
      toast.success(`Marked ${status}`);
    } catch { toast.error("Failed"); }
  };

  const removeItem = async (id) => {
    await axios.delete(`${API}/automation/grants/results/${id}`, { headers: authHeaders() });
    setResults(p => p.filter(r => r.id !== id));
  };

  return (
    <div className="space-y-6 animate-fade-in" data-testid="grant-scanner-page">
      <div className="flex items-center gap-3">
        <Radar className="w-7 h-7 text-blue-400" />
        <div>
          <h1 className="text-2xl sm:text-3xl font-semibold text-white tracking-tight" style={{ fontFamily: "Outfit" }}>
            Grant Scanner
          </h1>
          <p className="text-sm text-gray-400 mt-0.5">Scan real funders for new opportunities that match Pro Youth Foundation.</p>
        </div>
      </div>

      {/* Filter panel */}
      <div className="bg-[#12141A] border border-white/[0.05] rounded-xl p-5 space-y-4" data-testid="scanner-filters">
        <div>
          <p className="text-xs text-gray-400 mb-2">Sectors</p>
          <div className="flex flex-wrap gap-2">
            {SECTORS.map(s => (
              <button key={s} onClick={() => toggleSector(s)}
                data-testid={`chip-sector-${s.replace(/\W+/g, "-")}`}
                className={`px-3 py-1.5 rounded-full text-xs border transition-colors ${sectors.includes(s) ? "bg-blue-600/20 border-blue-500/40 text-blue-300" : "bg-[#0B0C10] border-white/10 text-gray-400 hover:text-white"}`}>
                {s}
              </button>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <p className="text-xs text-gray-400 mb-1.5">Region</p>
            <Select value={region} onValueChange={setRegion}>
              <SelectTrigger className="bg-[#0B0C10] border-white/10 text-gray-200 h-10" data-testid="select-region"><SelectValue /></SelectTrigger>
              <SelectContent className="bg-[#1A1D24] border-white/10">
                {REGIONS.map(r => <SelectItem key={r} value={r} className="text-gray-200">{r}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
        </div>

        <div>
          <p className="text-xs text-gray-400 mb-2">Sources</p>
          <div className="flex flex-wrap gap-2">
            {SOURCES.map(s => (
              <button key={s} onClick={() => toggleSource(s)}
                data-testid={`chip-source-${s.replace(/\W+/g, "-")}`}
                className={`px-3 py-1.5 rounded-full text-xs border transition-colors ${sources.includes(s) ? "bg-emerald-600/15 border-emerald-500/30 text-emerald-300" : "bg-[#0B0C10] border-white/10 text-gray-400 hover:text-white"}`}>
                {s}
              </button>
            ))}
          </div>
        </div>

        <div className="flex items-center gap-3">
          <Button onClick={scan} disabled={scanning} data-testid="scan-btn" className="bg-blue-600 hover:bg-blue-500 text-white">
            {scanning ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Sparkles className="w-4 h-4 mr-2" />}
            Scan Now
          </Button>
          <Button onClick={fetchResults} variant="outline" className="border-white/10 text-gray-300 text-xs" data-testid="refresh-btn">
            <RefreshCw className="w-3.5 h-3.5 mr-2" />Refresh
          </Button>
        </div>
      </div>

      {/* Results */}
      <div className="space-y-2" data-testid="scanner-results">
        {results.length === 0 ? (
          <div className="text-center py-10 text-sm text-gray-500">No scan results yet — click "Scan Now".</div>
        ) : results.map(r => (
          <div key={r.id} className="bg-[#12141A] border border-white/[0.05] rounded-xl p-4" data-testid={`scan-row-${r.id}`}>
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <Badge className={`border-0 text-[10px] ${r.fit_score >= 70 ? "bg-emerald-600/15 text-emerald-400" : r.fit_score >= 50 ? "bg-blue-600/15 text-blue-400" : "bg-white/5 text-gray-400"}`}>Fit {r.fit_score}</Badge>
                  <Badge className="bg-white/5 border-0 text-gray-300 text-[10px]">{r.funder}</Badge>
                  <Badge className="bg-white/5 border-0 text-gray-400 text-[10px]">{r.sector || "—"}</Badge>
                  <Badge className="bg-white/5 border-0 text-gray-400 text-[10px]">{r.submission_type}</Badge>
                  {r.status !== "new" && <Badge className="bg-amber-500/10 text-amber-400 border-0 text-[10px]">{r.status}</Badge>}
                </div>
                <p className="text-sm font-medium text-white">{r.title}</p>
                <p className="text-xs text-gray-400 mt-1">{r.summary}</p>
                <div className="flex flex-wrap items-center gap-3 text-[11px] text-gray-500 mt-2">
                  <span>{r.amount_text}</span>
                  <span>· {r.deadline}</span>
                  <span>· {r.country_eligibility}</span>
                </div>
              </div>
              <div className="flex flex-col gap-2 shrink-0">
                {r.official_url && (
                  <a href={r.official_url} target="_blank" rel="noopener noreferrer" data-testid={`open-${r.id}`}>
                    <Button size="sm" variant="outline" className="border-white/10 text-gray-300 text-xs w-full"><ExternalLink className="w-3.5 h-3.5 mr-1.5" />Open</Button>
                  </a>
                )}
                <Button size="sm" onClick={() => updateStatus(r.id, "saved")} variant="outline" className="border-white/10 text-gray-300 text-xs" data-testid={`save-${r.id}`}>
                  <Bookmark className="w-3.5 h-3.5 mr-1.5" />Save
                </Button>
                <Button size="sm" onClick={() => navigate(`/search?search=${encodeURIComponent(r.funder)}`)} variant="outline" className="border-white/10 text-gray-300 text-xs" data-testid={`wizard-${r.id}`}>
                  <Wand2 className="w-3.5 h-3.5 mr-1.5" />Find in Search
                </Button>
                <Button size="sm" onClick={() => updateStatus(r.id, "ignored")} variant="outline" className="border-white/10 text-gray-500 text-xs" data-testid={`ignore-${r.id}`}>Ignore</Button>
                <button onClick={() => removeItem(r.id)} className="text-gray-600 hover:text-red-400 text-xs" data-testid={`del-${r.id}`}><Trash2 className="w-3.5 h-3.5 inline" /></button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
