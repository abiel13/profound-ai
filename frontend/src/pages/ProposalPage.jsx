import React, { useState, useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import axios from "axios";
import { useAuth } from "@/context/AuthContext";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import {
  FileText, Sparkles, Loader2, Trash2, ChevronDown, ChevronUp, ArrowLeft, Mail, ScrollText, ClipboardList, ListChecks, FileCheck, Download
} from "lucide-react";

import { API } from "../config";

export default function ProposalPage() {
  const { authHeaders } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const oppId = searchParams.get("opp");
  const [proposals, setProposals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [expandedId, setExpandedId] = useState(null);
  const [opportunity, setOpportunity] = useState(null);
  const [form, setForm] = useState({ project_idea: "", beneficiaries: "", funding_amount: "" });

  useEffect(() => { fetchProposals(); }, []);

  useEffect(() => {
    if (oppId) fetchOpportunity(oppId);
  }, [oppId]);

  const fetchProposals = async () => {
    try {
      const res = await axios.get(`${API}/proposals`, { headers: authHeaders() });
      setProposals(res.data);
    } catch { /* ignore */ }
    finally { setLoading(false); }
  };

  const fetchOpportunity = async (id) => {
    try {
      const res = await axios.get(`${API}/opportunities/${id}`, { headers: authHeaders() });
      setOpportunity(res.data);
    } catch { /* ignore */ }
  };

  const handleGenerate = async () => {
    if (!oppId || !form.project_idea.trim()) {
      toast.error("Please fill in the project idea");
      return;
    }
    setGenerating(true);
    try {
      const res = await axios.post(`${API}/proposals/generate`, {
        opportunity_id: oppId,
        project_idea: form.project_idea,
        beneficiaries: form.beneficiaries,
        funding_amount: parseFloat(form.funding_amount) || 0
      }, { headers: authHeaders() });
      setProposals(prev => [res.data, ...prev]);
      setExpandedId(res.data.id);
      setForm({ project_idea: "", beneficiaries: "", funding_amount: "" });
      toast.success("Proposal generated successfully");
    } catch {
      toast.error("Failed to generate proposal");
    } finally {
      setGenerating(false);
    }
  };

  const deleteProposal = async (id) => {
    try {
      await axios.delete(`${API}/proposals/${id}`, { headers: authHeaders() });
      setProposals(prev => prev.filter(p => p.id !== id));
      toast.success("Proposal deleted");
    } catch {
      toast.error("Failed to delete");
    }
  };

  const exportPDF = async (id) => {
    try {
      const res = await axios.get(`${API}/proposals/${id}/pdf`, {
        headers: authHeaders(),
        responseType: 'blob'
      });
      const url = window.URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `proposal_${id.slice(0, 8)}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      toast.success("PDF exported");
    } catch {
      toast.error("Failed to export PDF");
    }
  };

  const sectionIcons = {
    donor_email: <Mail className="w-4 h-4 text-blue-400" />,
    letter_of_interest: <ScrollText className="w-4 h-4 text-emerald-400" />,
    concept_note: <ClipboardList className="w-4 h-4 text-purple-400" />,
    proposal_outline: <ListChecks className="w-4 h-4 text-amber-400" />,
    checklist: <FileCheck className="w-4 h-4 text-cyan-400" />
  };

  const sectionLabels = {
    donor_email: "Donor Email",
    letter_of_interest: "Letter of Interest",
    concept_note: "Concept Note",
    proposal_outline: "Proposal Outline",
    checklist: "Application Checklist"
  };

  return (
    <div className="space-y-6 animate-fade-in max-w-4xl" data-testid="proposal-page">
      <div>
        <h1 className="text-2xl sm:text-3xl font-semibold text-white tracking-tight" style={{ fontFamily: 'Outfit, sans-serif' }}>
          Proposal Generator
        </h1>
        <p className="text-sm text-gray-400 mt-1">Generate professional funding proposals using AI</p>
      </div>

      {/* Generate form */}
      {oppId && opportunity && (
        <div className="bg-[#12141A] border border-white/[0.05] rounded-xl p-6 space-y-5 ai-glow" data-testid="proposal-form">
          <div className="flex items-center gap-2 mb-1">
            <Sparkles className="w-4 h-4 text-blue-400" />
            <h2 className="text-base font-medium text-white" style={{ fontFamily: 'Outfit, sans-serif' }}>Generate Proposal</h2>
          </div>
          <div className="bg-[#0B0C10] rounded-lg p-3 border border-white/[0.05]">
            <p className="text-sm text-white font-medium">{opportunity.title}</p>
            <p className="text-xs text-gray-500 mt-0.5">{opportunity.donor_name}</p>
          </div>

          <div className="space-y-2">
            <Label className="text-sm text-gray-300">Project Idea</Label>
            <Textarea
              value={form.project_idea}
              onChange={(e) => setForm(prev => ({ ...prev, project_idea: e.target.value }))}
              placeholder="Describe your project idea for this grant..."
              rows={3}
              className="bg-[#0B0C10] border-white/10 text-white resize-none"
              data-testid="proposal-idea-input"
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label className="text-sm text-gray-300">Target Beneficiaries</Label>
              <Input
                value={form.beneficiaries}
                onChange={(e) => setForm(prev => ({ ...prev, beneficiaries: e.target.value }))}
                placeholder="e.g., 500 unemployed youth in rural Namibia"
                className="bg-[#0B0C10] border-white/10 text-white h-11"
                data-testid="proposal-beneficiaries-input"
              />
            </div>
            <div className="space-y-2">
              <Label className="text-sm text-gray-300">Requested Amount (USD)</Label>
              <Input
                type="number"
                value={form.funding_amount}
                onChange={(e) => setForm(prev => ({ ...prev, funding_amount: e.target.value }))}
                placeholder="e.g., 150000"
                className="bg-[#0B0C10] border-white/10 text-white h-11"
                data-testid="proposal-amount-input"
              />
            </div>
          </div>

          <Button
            onClick={handleGenerate}
            disabled={generating || !form.project_idea.trim()}
            data-testid="generate-proposal-submit-btn"
            className="bg-blue-600 hover:bg-blue-500 text-white"
          >
            {generating ? (
              <span className="flex items-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin" />
                AI is generating your proposal...
              </span>
            ) : (
              <span className="flex items-center gap-2">
                <Sparkles className="w-4 h-4" />
                Generate Proposal
              </span>
            )}
          </Button>
        </div>
      )}

      {!oppId && (
        <div className="bg-[#12141A] border border-white/[0.05] rounded-xl p-6 text-center">
          <FileText className="w-10 h-10 text-gray-600 mx-auto mb-3" />
          <p className="text-gray-400 text-sm">To generate a new proposal, go to an opportunity detail page and click "Generate Proposal"</p>
          <button onClick={() => navigate("/search")} className="text-sm text-blue-400 hover:text-blue-300 mt-2">Browse opportunities</button>
        </div>
      )}

      {/* Proposals list */}
      {proposals.length > 0 && (
        <div className="space-y-3" data-testid="proposals-list">
          <h2 className="text-lg font-medium text-white" style={{ fontFamily: 'Outfit, sans-serif' }}>Generated Proposals</h2>
          {proposals.map(p => (
            <div key={p.id} className="bg-[#12141A] border border-white/[0.05] rounded-xl overflow-hidden" data-testid={`proposal-${p.id}`}>
              <div
                className="flex items-center justify-between p-5 cursor-pointer hover:bg-white/[0.02] transition-colors"
                onClick={() => setExpandedId(expandedId === p.id ? null : p.id)}
              >
                <div className="flex-1 min-w-0">
                  <h3 className="text-sm font-medium text-white line-clamp-1">{p.opportunity_title}</h3>
                  <p className="text-xs text-gray-500 mt-0.5">
                    {new Date(p.created_at).toLocaleDateString()} - USD {parseFloat(p.funding_amount).toLocaleString()}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={(e) => { e.stopPropagation(); exportPDF(p.id); }}
                    data-testid={`export-pdf-${p.id}`}
                    className="p-2 text-gray-500 hover:text-blue-400 hover:bg-blue-500/10 rounded-lg transition-colors"
                    title="Export as PDF"
                  >
                    <Download className="w-4 h-4" />
                  </button>
                  <button
                    onClick={(e) => { e.stopPropagation(); deleteProposal(p.id); }}
                    data-testid={`delete-proposal-${p.id}`}
                    className="p-2 text-gray-500 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                  {expandedId === p.id ? <ChevronUp className="w-4 h-4 text-gray-400" /> : <ChevronDown className="w-4 h-4 text-gray-400" />}
                </div>
              </div>

              {expandedId === p.id && (
                <div className="px-5 pb-5 space-y-4 border-t border-white/[0.05] pt-4">
                  {Object.entries(sectionLabels).map(([key, label]) => (
                    p[key] && (
                      <div key={key}>
                        <div className="flex items-center gap-2 mb-2">
                          {sectionIcons[key]}
                          <h4 className="text-sm font-medium text-white">{label}</h4>
                        </div>
                        <div className="bg-[#0B0C10] rounded-lg p-4 text-sm text-gray-300 leading-relaxed whitespace-pre-line">
                          {p[key]}
                        </div>
                      </div>
                    )
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
