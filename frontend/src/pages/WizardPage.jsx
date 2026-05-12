import React, { useState, useEffect, useCallback } from "react";
import axios from "axios";
import { useAuth } from "@/context/AuthContext";
import { useNavigate, useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Progress } from "@/components/ui/progress";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Wand2, Sparkles, Loader2, CheckCircle, Circle, ArrowRight, ArrowLeft,
  FileText, Search as SearchIcon, ClipboardCheck, Send, DollarSign, Calendar,
  ChevronDown, ChevronUp, Target, Rocket
} from "lucide-react";

import { API } from "../config";
import HowToApplyPanel from "@/components/HowToApplyPanel";

const STEP_ICONS = [null, SearchIcon, Target, Sparkles, FileText, ClipboardCheck, Send];
const STEP_COLORS = [null, "text-blue-400", "text-emerald-400", "text-purple-400", "text-amber-400", "text-cyan-400", "text-green-400"];

function formatValue(n) {
  if (!n) return "$0";
  if (n >= 1000000) return `$${(n / 1000000).toFixed(1)}M`;
  if (n >= 1000) return `$${(n / 1000).toFixed(0)}K`;
  return `$${n}`;
}

function getDaysUntil(d) { return Math.ceil((new Date(d) - new Date()) / 86400000); }

export default function WizardPage() {
  const { authHeaders } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const oppId = searchParams.get("opp");
  const wizId = searchParams.get("wiz");
  const [wizards, setWizards] = useState([]);
  const [active, setActive] = useState(null);
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  const [checklist, setChecklist] = useState({});

  const fetchWizards = useCallback(async () => {
    try {
      const res = await axios.get(`${API}/wizard`, { headers: authHeaders() });
      setWizards(res.data);
    } catch { /* ignore */ }
    finally { setLoading(false); }
  }, [authHeaders]);

  useEffect(() => { fetchWizards(); }, [fetchWizards]);

  // Auto-start wizard if oppId provided
  useEffect(() => {
    if (oppId && !wizId) startWizard(oppId);
  }, [oppId]);

  // Load specific wizard
  useEffect(() => {
    if (wizId) loadWizard(wizId);
  }, [wizId]);

  const startWizard = async (opportunityId) => {
    try {
      const res = await axios.post(`${API}/wizard/start`, { opportunity_id: opportunityId }, { headers: authHeaders() });
      if (res.data.exists) {
        loadWizard(res.data.id);
      } else {
        toast.success("Application Wizard started");
        loadWizard(res.data.id);
      }
    } catch { toast.error("Failed to start wizard"); }
  };

  const loadWizard = async (id) => {
    try {
      const res = await axios.get(`${API}/wizard/${id}`, { headers: authHeaders() });
      setActive(res.data);
      if (res.data.review_checklist) setChecklist(res.data.review_checklist);
    } catch { toast.error("Failed to load wizard"); }
  };

  const runStep1 = async () => {
    if (!active) return;
    setProcessing(true);
    try {
      const res = await axios.post(`${API}/wizard/${active.id}/analyze`, {}, { headers: authHeaders() });
      toast.success("Grant analyzed - requirements extracted");
      loadWizard(active.id);
      fetchWizards();
    } catch { toast.error("Analysis failed"); }
    finally { setProcessing(false); }
  };

  const advanceToStep3 = async () => {
    await axios.put(`${API}/wizard/${active.id}/step`, { current_step: 3 }, { headers: authHeaders() });
    loadWizard(active.id);
  };

  const runStep3 = async () => {
    if (!active) return;
    setProcessing(true);
    try {
      await axios.post(`${API}/wizard/${active.id}/generate-docs`, {}, { headers: authHeaders() });
      toast.success("Application documents generated");
      loadWizard(active.id);
      fetchWizards();
    } catch { toast.error("Document generation failed"); }
    finally { setProcessing(false); }
  };

  const advanceStep = async (step, extras = {}) => {
    try {
      await axios.put(`${API}/wizard/${active.id}/step`, { current_step: step, ...extras }, { headers: authHeaders() });
      loadWizard(active.id);
      fetchWizards();
      if (step >= 6) toast.success("Application ready to submit!");
    } catch { toast.error("Failed to advance"); }
  };

  const toggleCheck = (key) => {
    setChecklist(prev => {
      const updated = { ...prev, [key]: !prev[key] };
      return updated;
    });
  };

  if (loading) {
    return <div className="space-y-4 animate-fade-in"><div className="h-8 w-64 skeleton-loading rounded-lg" /><div className="h-96 skeleton-loading rounded-xl" /></div>;
  }

  // If no active wizard, show list
  if (!active) {
    return (
      <div className="space-y-6 animate-fade-in" data-testid="wizard-list-page">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl sm:text-3xl font-semibold text-white tracking-tight" style={{ fontFamily: 'Outfit' }}>Application Wizard</h1>
            <p className="text-sm text-gray-400 mt-1">Turn any opportunity into a submission-ready application</p>
          </div>
          <Button onClick={() => navigate("/search")} data-testid="find-opportunity-btn" className="bg-blue-600 hover:bg-blue-500 text-white text-sm">
            <SearchIcon className="w-4 h-4 mr-2" />Find Opportunity
          </Button>
        </div>

        {wizards.length === 0 ? (
          <div className="bg-[#12141A] border border-white/[0.05] rounded-xl p-12 text-center">
            <Wand2 className="w-14 h-14 text-gray-700 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-300" style={{ fontFamily: 'Outfit' }}>No Applications Started</h3>
            <p className="text-sm text-gray-500 mt-1">Go to any opportunity and click "Start Wizard" to begin</p>
          </div>
        ) : (
          <div className="space-y-3" data-testid="wizard-list">
            {wizards.map(w => {
              const days = getDaysUntil(w.deadline);
              return (
                <div key={w.id} className="bg-[#12141A] border border-white/[0.05] rounded-xl p-5 card-hover cursor-pointer"
                  onClick={() => loadWizard(w.id)} data-testid={`wizard-item-${w.id}`}>
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 rounded-xl bg-blue-600/10 flex items-center justify-center shrink-0">
                      <span className="text-lg font-bold text-blue-400">{w.completion_pct}%</span>
                    </div>
                    <div className="flex-1 min-w-0">
                      <h3 className="text-sm font-medium text-white line-clamp-1">{w.title}</h3>
                      <div className="flex items-center gap-3 text-xs text-gray-400 mt-1">
                        <span>{w.donor_name}</span>
                        <span className="flex items-center gap-1"><DollarSign className="w-3 h-3" />{formatValue(w.funding_max)}</span>
                        <span className={`flex items-center gap-1 ${days <= 14 ? 'text-amber-400' : ''}`}><Calendar className="w-3 h-3" />{days}d left</span>
                      </div>
                      <Progress value={w.completion_pct} className="h-1 mt-2" />
                    </div>
                    <Badge className={`border-0 text-[10px] ${w.status === 'complete' ? 'bg-emerald-600/10 text-emerald-400' : 'bg-blue-600/10 text-blue-400'}`}>
                      {w.status === 'complete' ? 'Ready' : `Step ${w.current_step}/6`}
                    </Badge>
                    <ArrowRight className="w-4 h-4 text-gray-500" />
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    );
  }

  // Active wizard view
  const opp = active.opportunity || {};
  const analysis = active.grant_analysis || {};
  const docs = active.documents || {};
  const step = active.current_step;
  const steps = active.steps || [];

  const DEFAULT_CHECKLIST_ITEMS = [
    "Cover letter reviewed and customized",
    "Executive summary reflects donor priorities",
    "Project narrative is specific and measurable",
    "Budget is realistic and justified",
    "All eligibility criteria confirmed",
    "Organization details are accurate",
    "Deadline and submission method confirmed",
    "All required attachments prepared"
  ];

  return (
    <div className="space-y-6 animate-fade-in max-w-5xl" data-testid="wizard-active-page">
      {/* Header */}
      <div className="flex items-center gap-3">
        <button onClick={() => setActive(null)} className="text-gray-400 hover:text-white"><ArrowLeft className="w-5 h-5" /></button>
        <div className="flex-1">
          <h1 className="text-xl font-semibold text-white tracking-tight" style={{ fontFamily: 'Outfit' }}>{active.title}</h1>
          <p className="text-xs text-gray-400">{active.donor_name} - {formatValue(opp.funding_max)} - {getDaysUntil(opp.deadline)}d left</p>
        </div>
        <Badge className={`${active.status === 'complete' ? 'bg-emerald-600/10 text-emerald-400' : 'bg-blue-600/10 text-blue-400'} border-0`}>
          {active.completion_pct}% Complete
        </Badge>
      </div>

      {/* Step Progress */}
      <div className="bg-[#12141A] border border-white/[0.05] rounded-xl p-4" data-testid="wizard-steps">
        <div className="flex items-center gap-1">
          {steps.map((s, i) => {
            const Icon = STEP_ICONS[s.step] || Circle;
            const done = step > s.step;
            const current = step === s.step;
            return (
              <React.Fragment key={s.step}>
                <div className={`flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-medium transition-all ${
                  done ? 'bg-emerald-600/10 text-emerald-400' : current ? 'bg-blue-600/10 text-blue-400 ring-1 ring-blue-500/30' : 'text-gray-600'
                }`}>
                  {done ? <CheckCircle className="w-3.5 h-3.5" /> : <Icon className={`w-3.5 h-3.5 ${current ? STEP_COLORS[s.step] : ''}`} />}
                  <span className="hidden sm:inline">{s.name}</span>
                </div>
                {i < steps.length - 1 && <div className={`flex-1 h-px ${done ? 'bg-emerald-500/30' : 'bg-white/[0.06]'}`} />}
              </React.Fragment>
            );
          })}
        </div>
      </div>

      {/* Step Content */}
      <div className="bg-[#12141A] border border-white/[0.05] rounded-xl p-6" data-testid="wizard-content">
        {/* Step 1: Analyze */}
        {step === 1 && (
          <div className="text-center py-8 space-y-4">
            <SearchIcon className="w-10 h-10 text-blue-400 mx-auto" />
            <h2 className="text-lg font-medium text-white" style={{ fontFamily: 'Outfit' }}>Step 1: Analyze Grant</h2>
            <p className="text-sm text-gray-400 max-w-md mx-auto">AI will analyze this opportunity, extract requirements, assess eligibility fit, and recommend a strategic approach.</p>
            <Button onClick={runStep1} disabled={processing} data-testid="analyze-btn" className="bg-blue-600 hover:bg-blue-500 text-white">
              {processing ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Sparkles className="w-4 h-4 mr-2" />}
              {processing ? "Analyzing..." : "Analyze Grant"}
            </Button>
          </div>
        )}

        {/* Step 2: Org Fit */}
        {step === 2 && (
          <div className="space-y-5">
            <h2 className="text-lg font-medium text-white" style={{ fontFamily: 'Outfit' }}>Step 2: Organization Fit Check</h2>
            {analysis.eligibility_fit && (
              <div className="bg-emerald-500/5 border border-emerald-500/15 rounded-xl p-4">
                <p className="text-xs text-emerald-400 uppercase tracking-wider mb-1">Eligibility Fit</p>
                <p className="text-sm text-gray-300">{analysis.eligibility_fit}</p>
              </div>
            )}
            {analysis.strategic_angle && (
              <div className="bg-blue-500/5 border border-blue-500/15 rounded-xl p-4">
                <p className="text-xs text-blue-400 uppercase tracking-wider mb-1">Recommended Approach</p>
                <p className="text-sm text-gray-300">{analysis.strategic_angle}</p>
              </div>
            )}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {analysis.requirements && (
                <div className="bg-[#0B0C10] rounded-lg p-4">
                  <p className="text-xs text-gray-500 uppercase tracking-wider mb-2">Requirements</p>
                  <ul className="space-y-1">{(Array.isArray(analysis.requirements) ? analysis.requirements : []).map((r, i) => <li key={i} className="text-xs text-gray-400 flex items-start gap-2"><Circle className="w-2 h-2 mt-1 text-blue-400 shrink-0 fill-current" />{r}</li>)}</ul>
                </div>
              )}
              {analysis.required_documents && (
                <div className="bg-[#0B0C10] rounded-lg p-4">
                  <p className="text-xs text-gray-500 uppercase tracking-wider mb-2">Required Documents</p>
                  <ul className="space-y-1">{(Array.isArray(analysis.required_documents) ? analysis.required_documents : []).map((d, i) => <li key={i} className="text-xs text-gray-400 flex items-start gap-2"><FileText className="w-3 h-3 mt-0.5 text-purple-400 shrink-0" />{d}</li>)}</ul>
                </div>
              )}
            </div>
            <div className="flex items-center gap-3 text-xs text-gray-400">
              {analysis.estimated_effort && <Badge className="bg-white/[0.04] border-0 text-gray-400 text-[10px]">Effort: {analysis.estimated_effort}</Badge>}
              {analysis.success_probability && <Badge className="bg-emerald-600/10 text-emerald-400 border-0 text-[10px]">Success: {analysis.success_probability}</Badge>}
            </div>
            <Button onClick={advanceToStep3} data-testid="proceed-to-docs-btn" className="bg-blue-600 hover:bg-blue-500 text-white">
              Proceed to Document Generation <ArrowRight className="w-4 h-4 ml-2" />
            </Button>
          </div>
        )}

        {/* Step 3: Generate Docs */}
        {step === 3 && (
          <div className="text-center py-8 space-y-4">
            <Sparkles className="w-10 h-10 text-purple-400 mx-auto" />
            <h2 className="text-lg font-medium text-white" style={{ fontFamily: 'Outfit' }}>Step 3: Generate Documents</h2>
            <p className="text-sm text-gray-400 max-w-md mx-auto">AI will generate your complete application package: cover letter, executive summary, project narrative, budget justification, and more.</p>
            <Button onClick={runStep3} disabled={processing} data-testid="generate-docs-btn" className="bg-purple-600 hover:bg-purple-500 text-white">
              {processing ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Sparkles className="w-4 h-4 mr-2" />}
              {processing ? "Generating..." : "Generate Application Package"}
            </Button>
          </div>
        )}

        {/* Step 4: Review */}
        {step === 4 && (
          <div className="space-y-4">
            <h2 className="text-lg font-medium text-white" style={{ fontFamily: 'Outfit' }}>Step 4: Review & Edit</h2>
            <p className="text-xs text-gray-500">Review each document. Edit in Proposals page for full editing.</p>
            {Object.entries(docs).filter(([_, v]) => v).map(([key, content]) => (
              <DocSection key={key} title={key.replace(/_/g, ' ')} content={content} />
            ))}
            <Button onClick={() => advanceStep(5)} data-testid="proceed-to-checklist-btn" className="bg-blue-600 hover:bg-blue-500 text-white">
              Proceed to Checklist <ArrowRight className="w-4 h-4 ml-2" />
            </Button>
          </div>
        )}

        {/* Step 5: Checklist */}
        {step === 5 && (
          <div className="space-y-4">
            <h2 className="text-lg font-medium text-white" style={{ fontFamily: 'Outfit' }}>Step 5: Submission Checklist</h2>
            <div className="space-y-2">
              {DEFAULT_CHECKLIST_ITEMS.map((item, i) => (
                <label key={i} className="flex items-center gap-3 p-3 rounded-lg bg-[#0B0C10] cursor-pointer hover:bg-white/[0.03]" data-testid={`check-${i}`}>
                  <Checkbox checked={!!checklist[`item_${i}`]} onCheckedChange={() => toggleCheck(`item_${i}`)} />
                  <span className={`text-sm ${checklist[`item_${i}`] ? 'text-emerald-400 line-through' : 'text-gray-300'}`}>{item}</span>
                </label>
              ))}
            </div>
            <Button onClick={async () => {
              await advanceStep(6, { review_checklist: checklist });
              // Auto-fetch submission details on first entry to step 6
              try {
                if (active?.opportunity?.id && !active.opportunity.submission_fetched_at) {
                  await axios.post(`${API}/opportunities/${active.opportunity.id}/fetch-submission`, {}, { headers: authHeaders() });
                  await loadWizard(active.id);
                }
              } catch { /* non-blocking */ }
            }} data-testid="finalize-btn" className="bg-emerald-600 hover:bg-emerald-500 text-white">
              <Rocket className="w-4 h-4 mr-2" />Mark Ready to Submit
            </Button>
          </div>
        )}

        {/* Step 6: Submit (How to Apply) */}
        {step >= 6 && (
          <div className="space-y-6" data-testid="wizard-step6">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-emerald-600/15 flex items-center justify-center">
                <CheckCircle className="w-5 h-5 text-emerald-400" />
              </div>
              <div>
                <h2 className="text-lg font-medium text-white" style={{ fontFamily: 'Outfit' }}>Application Ready</h2>
                <p className="text-xs text-gray-400">All documents generated. Use the panel below to submit manually.</p>
              </div>
            </div>

            <HowToApplyPanel
              opportunity={opp}
              documents={docs}
              onRefreshOpp={() => loadWizard(active.id)}
            />

            <div className="flex items-center justify-end gap-3 pt-2 border-t border-white/[0.05]">
              <Button onClick={() => navigate(`/proposals?opp=${active.opportunity_id}`)} variant="outline" className="border-white/10 text-gray-300 text-sm">
                <FileText className="w-4 h-4 mr-2" />Edit Documents
              </Button>
              <Button onClick={() => navigate("/workspace")} variant="outline" className="border-white/10 text-gray-300 text-sm">
                Go to Workspace
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function DocSection({ title, content }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="bg-[#0B0C10] rounded-xl border border-white/[0.05] overflow-hidden">
      <button onClick={() => setOpen(!open)} className="flex items-center gap-3 w-full p-4 text-left hover:bg-white/[0.02]">
        <FileText className="w-4 h-4 text-purple-400" />
        <span className="text-sm font-medium text-white capitalize flex-1">{title}</span>
        {open ? <ChevronUp className="w-4 h-4 text-gray-400" /> : <ChevronDown className="w-4 h-4 text-gray-400" />}
      </button>
      {open && <div className="px-4 pb-4 text-sm text-gray-300 leading-relaxed whitespace-pre-line border-t border-white/[0.03] pt-3">{content}</div>}
    </div>
  );
}
