import React, { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import axios from "axios";
import { useAuth } from "@/context/AuthContext";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import {
  ArrowLeft, Bookmark, Calendar, DollarSign, MapPin, Globe2,
  ExternalLink, Sparkles, Target, FileText, Loader2, Wand2
} from "lucide-react";

import { API } from "../config";
import HowToApplyPanel from "@/components/HowToApplyPanel";

function formatCurrency(n) {
  if (n >= 1000000) return `$${(n / 1000000).toFixed(1)}M`;
  if (n >= 1000) return `$${(n / 1000).toFixed(0)}K`;
  return `$${n}`;
}

function getDaysUntil(deadline) {
  return Math.ceil((new Date(deadline) - new Date()) / (1000 * 60 * 60 * 24));
}

export default function OpportunityDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { authHeaders } = useAuth();
  const [opp, setOpp] = useState(null);
  const [loading, setLoading] = useState(true);
  const [aiLoading, setAiLoading] = useState({ summary: false, match: false, fit: false });
  const [aiData, setAiData] = useState({ summary: "", score: 0, explanation: "", fit: "" });

  useEffect(() => {
    fetchOpportunity();
  }, [id]);

  const fetchOpportunity = async () => {
    try {
      const res = await axios.get(`${API}/opportunities/${id}`, { headers: authHeaders() });
      setOpp(res.data);
      if (res.data.ai_summary) setAiData(prev => ({ ...prev, summary: res.data.ai_summary }));
      if (res.data.ai_match_score) setAiData(prev => ({ ...prev, score: res.data.ai_match_score }));
      if (res.data.ai_fit_explanation) setAiData(prev => ({ ...prev, fit: res.data.ai_fit_explanation }));
    } catch {
      toast.error("Opportunity not found");
      navigate("/");
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    try {
      await axios.post(`${API}/saved`, { opportunity_id: id }, { headers: authHeaders() });
      setOpp(prev => ({ ...prev, is_saved: true }));
      toast.success("Opportunity saved");
    } catch {
      toast.error("Already saved or failed");
    }
  };

  const runAISummary = async () => {
    setAiLoading(prev => ({ ...prev, summary: true }));
    try {
      const res = await axios.post(`${API}/ai/summarize`, { opportunity_id: id }, { headers: authHeaders() });
      setAiData(prev => ({ ...prev, summary: res.data.summary }));
      toast.success("Summary generated");
    } catch {
      toast.error("AI summary failed");
    } finally {
      setAiLoading(prev => ({ ...prev, summary: false }));
    }
  };

  const runAIMatch = async () => {
    setAiLoading(prev => ({ ...prev, match: true }));
    try {
      const res = await axios.post(`${API}/ai/match-score`, { opportunity_id: id }, { headers: authHeaders() });
      setAiData(prev => ({ ...prev, score: res.data.score, explanation: res.data.explanation }));
      toast.success("Match score calculated");
    } catch {
      toast.error("Match scoring failed");
    } finally {
      setAiLoading(prev => ({ ...prev, match: false }));
    }
  };

  const runAIFit = async () => {
    setAiLoading(prev => ({ ...prev, fit: true }));
    try {
      const res = await axios.post(`${API}/ai/fit-explanation`, { opportunity_id: id }, { headers: authHeaders() });
      setAiData(prev => ({ ...prev, fit: res.data.explanation }));
      toast.success("Fit analysis complete");
    } catch {
      toast.error("Fit analysis failed");
    } finally {
      setAiLoading(prev => ({ ...prev, fit: false }));
    }
  };

  if (loading) {
    return (
      <div className="space-y-6 animate-fade-in">
        <div className="h-8 w-32 skeleton-loading rounded-lg" />
        <div className="h-64 skeleton-loading rounded-xl" />
        <div className="h-48 skeleton-loading rounded-xl" />
      </div>
    );
  }

  if (!opp) return null;
  const days = getDaysUntil(opp.deadline);

  return (
    <div className="space-y-6 animate-fade-in max-w-6xl" data-testid="opportunity-detail-page">
      {/* Back button */}
      <button
        onClick={() => navigate(-1)}
        data-testid="back-button"
        className="flex items-center gap-2 text-sm text-gray-400 hover:text-white transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        Back
      </button>

      {/* Main content: split view */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        {/* Left: Details (3 cols) */}
        <div className="lg:col-span-3 space-y-6">
          {/* Header card */}
          <div className="bg-[#12141A] border border-white/[0.05] rounded-xl p-6">
            <div className="flex flex-wrap gap-2 mb-3">
              <Badge className="bg-blue-600/10 text-blue-400 border-0 text-xs">{opp.donor_type}</Badge>
              <Badge className="bg-white/[0.06] text-gray-300 border-0 text-xs">{opp.sector}</Badge>
              {opp.africa_eligible === 1 && (
                <Badge className="bg-emerald-600/10 text-emerald-400 border-0 text-xs">Africa Eligible</Badge>
              )}
            </div>
            <h1 className="text-xl sm:text-2xl font-semibold text-white tracking-tight mb-2" style={{ fontFamily: 'Outfit, sans-serif' }}>
              {opp.title}
            </h1>
            <p className="text-sm text-gray-400">{opp.donor_name}</p>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-5">
              <div className="flex items-center gap-2">
                <DollarSign className="w-4 h-4 text-emerald-400" />
                <div>
                  <p className="text-xs text-gray-500">Funding</p>
                  <p className="text-sm text-white font-medium">{formatCurrency(opp.funding_min)} - {formatCurrency(opp.funding_max)}</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Calendar className="w-4 h-4 text-amber-400" />
                <div>
                  <p className="text-xs text-gray-500">Deadline</p>
                  <p className={`text-sm font-medium ${days <= 14 ? 'text-amber-400' : 'text-white'}`}>
                    {opp.deadline} ({days}d)
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <MapPin className="w-4 h-4 text-blue-400" />
                <div>
                  <p className="text-xs text-gray-500">Donor Country</p>
                  <p className="text-sm text-white">{opp.donor_country}</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Globe2 className="w-4 h-4 text-purple-400" />
                <div>
                  <p className="text-xs text-gray-500">Region</p>
                  <p className="text-sm text-white">{opp.region}</p>
                </div>
              </div>
            </div>

            <div className="flex gap-3 mt-5">
              {!opp.is_saved && (
                <Button onClick={handleSave} data-testid="save-opportunity-btn" className="bg-blue-600 hover:bg-blue-500 text-white text-sm">
                  <Bookmark className="w-4 h-4 mr-2" />
                  Save Opportunity
                </Button>
              )}
              {opp.is_saved && (
                <Badge className="bg-blue-600/10 text-blue-400 border-0 px-3 py-1.5">
                  <Bookmark className="w-3 h-3 mr-1 fill-current" />
                  Saved - {opp.saved_status}
                </Badge>
              )}
              <Button
                onClick={() => navigate(`/proposals?opp=${opp.id}`)}
                data-testid="generate-proposal-btn"
                variant="outline"
                className="border-white/10 text-gray-300 hover:text-white hover:bg-white/[0.04] text-sm"
              >
                <FileText className="w-4 h-4 mr-2" />
                Generate Proposal
              </Button>
              <Button
                onClick={() => navigate(`/wizard?opp=${opp.id}`)}
                data-testid="start-wizard-btn"
                className="bg-purple-600 hover:bg-purple-500 text-white text-sm"
              >
                <Wand2 className="w-4 h-4 mr-2" />
                Start Wizard
              </Button>
              {opp.url && (
                <a href={opp.url} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1 px-3 py-2 text-sm text-gray-400 hover:text-blue-400 transition-colors">
                  <ExternalLink className="w-4 h-4" />
                </a>
              )}
            </div>
          </div>

          {/* Description */}
          <div className="bg-[#12141A] border border-white/[0.05] rounded-xl p-6">
            <h2 className="text-base font-medium text-white mb-3" style={{ fontFamily: 'Outfit, sans-serif' }}>Description</h2>
            <p className="text-sm text-gray-400 leading-relaxed whitespace-pre-line">{opp.description}</p>
          </div>

          {/* Eligibility */}
          <div className="bg-[#12141A] border border-white/[0.05] rounded-xl p-6">
            <h2 className="text-base font-medium text-white mb-3" style={{ fontFamily: 'Outfit, sans-serif' }}>Eligibility</h2>
            <p className="text-sm text-gray-400 leading-relaxed whitespace-pre-line">{opp.eligibility}</p>
          </div>

          {/* How to Apply */}
          <div className="bg-[#12141A] border border-white/[0.05] rounded-xl p-6">
            <HowToApplyPanel
              opportunity={opp}
              documents={null}
              onRefreshOpp={fetchOpportunity}
            />
          </div>
        </div>

        {/* Right: AI Analysis (2 cols) */}
        <div className="lg:col-span-2 space-y-6">
          {/* AI Summary */}
          <div className="bg-[#12141A] border border-white/[0.05] rounded-xl p-6 ai-glow">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-blue-400" />
                <h3 className="text-sm font-medium text-white" style={{ fontFamily: 'Outfit, sans-serif' }}>AI Summary</h3>
              </div>
              <Button
                onClick={runAISummary}
                disabled={aiLoading.summary}
                data-testid="ai-summary-btn"
                size="sm"
                className="bg-blue-600/10 text-blue-400 hover:bg-blue-600/20 border-0 text-xs h-8"
              >
                {aiLoading.summary ? <Loader2 className="w-3 h-3 animate-spin" /> : "Generate"}
              </Button>
            </div>
            {aiData.summary ? (
              <p className="text-sm text-gray-300 leading-relaxed">{aiData.summary}</p>
            ) : (
              <p className="text-sm text-gray-600 italic">Click Generate to get an AI summary of this opportunity</p>
            )}
          </div>

          {/* AI Match Score */}
          <div className="bg-[#12141A] border border-white/[0.05] rounded-xl p-6 ai-glow">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <Target className="w-4 h-4 text-emerald-400" />
                <h3 className="text-sm font-medium text-white" style={{ fontFamily: 'Outfit, sans-serif' }}>Match Score</h3>
              </div>
              <Button
                onClick={runAIMatch}
                disabled={aiLoading.match}
                data-testid="ai-match-btn"
                size="sm"
                className="bg-blue-600/10 text-blue-400 hover:bg-blue-600/20 border-0 text-xs h-8"
              >
                {aiLoading.match ? <Loader2 className="w-3 h-3 animate-spin" /> : "Analyze"}
              </Button>
            </div>
            {aiData.score > 0 ? (
              <div className="flex items-center gap-4">
                <div className="relative w-20 h-20">
                  <svg className="w-20 h-20 -rotate-90" viewBox="0 0 80 80">
                    <circle cx="40" cy="40" r="34" fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="6" />
                    <circle
                      cx="40" cy="40" r="34" fill="none"
                      stroke={aiData.score >= 70 ? '#10B981' : aiData.score >= 40 ? '#F59E0B' : '#6B7280'}
                      strokeWidth="6" strokeLinecap="round"
                      strokeDasharray={`${(aiData.score / 100) * 213.6} 213.6`}
                      className="match-score-ring"
                    />
                  </svg>
                  <div className="absolute inset-0 flex items-center justify-center">
                    <span className="text-lg font-bold text-white">{aiData.score}</span>
                  </div>
                </div>
                <div className="flex-1">
                  <p className="text-sm text-gray-300 leading-relaxed">{aiData.explanation}</p>
                </div>
              </div>
            ) : (
              <p className="text-sm text-gray-600 italic">Click Analyze to calculate how well this grant matches your organization</p>
            )}
          </div>

          {/* AI Fit Explanation */}
          <div className="bg-[#12141A] border border-white/[0.05] rounded-xl p-6 ai-glow">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-purple-400" />
                <h3 className="text-sm font-medium text-white" style={{ fontFamily: 'Outfit, sans-serif' }}>Fit Explanation</h3>
              </div>
              <Button
                onClick={runAIFit}
                disabled={aiLoading.fit}
                data-testid="ai-fit-btn"
                size="sm"
                className="bg-blue-600/10 text-blue-400 hover:bg-blue-600/20 border-0 text-xs h-8"
              >
                {aiLoading.fit ? <Loader2 className="w-3 h-3 animate-spin" /> : "Explain"}
              </Button>
            </div>
            {aiData.fit ? (
              <p className="text-sm text-gray-300 leading-relaxed whitespace-pre-line">{aiData.fit}</p>
            ) : (
              <p className="text-sm text-gray-600 italic">Click Explain to understand why this donor fits your organization</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
