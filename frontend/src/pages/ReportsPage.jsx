import React, { useState, useEffect, useCallback } from "react";
import axios from "axios";
import { useAuth } from "@/context/AuthContext";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  FileText, Sparkles, Loader2, Download, ChevronDown, ChevronUp,
  TrendingUp, Target, AlertTriangle, Users, BarChart3, Lightbulb, Zap, Calendar
} from "lucide-react";

import { API } from "../config";

const SECTION_CONFIG = [
  { key: "executive_summary", label: "Executive Summary", icon: TrendingUp, color: "text-blue-400" },
  { key: "top_opportunities", label: "Top Opportunities", icon: Target, color: "text-emerald-400" },
  { key: "urgent_actions", label: "Urgent Actions", icon: AlertTriangle, color: "text-red-400" },
  { key: "relationship_health", label: "Relationship Health", icon: Users, color: "text-cyan-400" },
  { key: "pipeline_overview", label: "Pipeline Overview", icon: BarChart3, color: "text-purple-400" },
  { key: "performance_insights", label: "Performance Insights", icon: Lightbulb, color: "text-amber-400" },
  { key: "ai_recommendations", label: "AI Recommendations", icon: Zap, color: "text-blue-400" },
];

function formatValue(n) {
  if (!n) return "$0";
  if (n >= 1000000) return `$${(n / 1000000).toFixed(1)}M`;
  if (n >= 1000) return `$${(n / 1000).toFixed(0)}K`;
  return `$${n}`;
}

export default function ReportsPage() {
  const { authHeaders } = useAuth();
  const [reports, setReports] = useState([]);
  const [activeReport, setActiveReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [expandedSection, setExpandedSection] = useState("executive_summary");

  const fetchData = useCallback(async () => {
    try {
      const [listRes, latestRes] = await Promise.all([
        axios.get(`${API}/reports`, { headers: authHeaders() }),
        axios.get(`${API}/reports/latest`, { headers: authHeaders() })
      ]);
      setReports(listRes.data);
      if (latestRes.data) setActiveReport(latestRes.data);
    } catch { /* ignore */ }
    finally { setLoading(false); }
  }, [authHeaders]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const generateReport = async () => {
    setGenerating(true);
    try {
      const res = await axios.post(`${API}/reports/generate`, {}, { headers: authHeaders() });
      setActiveReport(res.data);
      setReports(prev => [{ id: res.data.id, week_label: res.data.week_label, executive_summary: res.data.executive_summary, created_at: res.data.created_at, raw_data: {} }, ...prev]);
      setExpandedSection("executive_summary");
      toast.success("Weekly Intelligence Report generated");
    } catch {
      toast.error("Report generation failed");
    } finally {
      setGenerating(false);
    }
  };

  const loadReport = async (id) => {
    try {
      const res = await axios.get(`${API}/reports/${id}`, { headers: authHeaders() });
      setActiveReport(res.data);
      setExpandedSection("executive_summary");
    } catch { toast.error("Failed to load report"); }
  };

  const exportPDF = async (id) => {
    try {
      const res = await axios.get(`${API}/reports/${id}/pdf`, { headers: authHeaders(), responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `weekly_report.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      toast.success("PDF exported");
    } catch { toast.error("Export failed"); }
  };

  if (loading) {
    return (
      <div className="space-y-4 animate-fade-in">
        <div className="h-8 w-64 skeleton-loading rounded-lg" />
        <div className="h-96 skeleton-loading rounded-xl" />
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in" data-testid="reports-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl sm:text-3xl font-semibold text-white tracking-tight" style={{ fontFamily: 'Outfit, sans-serif' }}>
            Weekly Intelligence
          </h1>
          <p className="text-sm text-gray-400 mt-1">AI-generated strategic briefing for your funding operations</p>
        </div>
        <div className="flex items-center gap-2">
          {activeReport && (
            <Button size="sm" onClick={() => exportPDF(activeReport.id)} data-testid="export-report-pdf"
              className="bg-white/[0.06] text-gray-300 hover:text-white text-xs h-9">
              <Download className="w-3.5 h-3.5 mr-1.5" />Export PDF
            </Button>
          )}
          <Button onClick={generateReport} disabled={generating} data-testid="generate-report-btn"
            className="bg-blue-600 hover:bg-blue-500 text-white text-sm">
            {generating ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Sparkles className="w-4 h-4 mr-2" />}
            {generating ? "Generating..." : "Generate Report"}
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Main report content (3 cols) */}
        <div className="lg:col-span-3 space-y-4">
          {!activeReport ? (
            <div className="bg-[#12141A] border border-white/[0.05] rounded-xl p-12 text-center">
              <FileText className="w-14 h-14 text-gray-700 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-300" style={{ fontFamily: 'Outfit' }}>No Reports Yet</h3>
              <p className="text-sm text-gray-500 mt-1 mb-4">Generate your first Weekly Intelligence Report to get strategic AI guidance</p>
              <Button onClick={generateReport} disabled={generating} className="bg-blue-600 hover:bg-blue-500 text-white">
                {generating ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Sparkles className="w-4 h-4 mr-2" />}
                Generate First Report
              </Button>
            </div>
          ) : (
            <>
              {/* Report header */}
              <div className="bg-[#12141A] border border-blue-500/15 rounded-xl p-5 ai-glow" data-testid="report-header">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <Sparkles className="w-5 h-5 text-blue-400" />
                    <h2 className="text-base font-medium text-white" style={{ fontFamily: 'Outfit' }}>
                      Week {activeReport.week_label}
                    </h2>
                  </div>
                  <span className="text-xs text-gray-500">{activeReport.created_at?.slice(0, 10)}</span>
                </div>
                {activeReport.raw_data && (
                  <div className="flex gap-4 mt-3 text-xs">
                    <span className="text-blue-400">Pipeline: {formatValue(activeReport.raw_data.pipeline_total)}</span>
                    <span className="text-emerald-400">Secured: {formatValue(activeReport.raw_data.total_secured)}</span>
                    <span className="text-gray-400">Rate: {activeReport.raw_data.approval_rate}%</span>
                  </div>
                )}
              </div>

              {/* Report sections */}
              {SECTION_CONFIG.map(({ key, label, icon: Icon, color }) => {
                const content = activeReport[key];
                if (!content) return null;
                const isExpanded = expandedSection === key;
                const isRecommendations = key === "ai_recommendations";
                return (
                  <div key={key}
                    className={`bg-[#12141A] border rounded-xl overflow-hidden ${isRecommendations ? 'border-blue-500/20 ai-glow' : 'border-white/[0.05]'}`}
                    data-testid={`section-${key}`}>
                    <button className="flex items-center gap-3 w-full p-4 text-left hover:bg-white/[0.02] transition-colors"
                      onClick={() => setExpandedSection(isExpanded ? null : key)}>
                      <Icon className={`w-4 h-4 ${color} shrink-0`} />
                      <span className="text-sm font-medium text-white flex-1">{label}</span>
                      {isRecommendations && <Badge className="bg-blue-600/10 text-blue-400 border-0 text-[10px]">Key Actions</Badge>}
                      {isExpanded ? <ChevronUp className="w-4 h-4 text-gray-400" /> : <ChevronDown className="w-4 h-4 text-gray-400" />}
                    </button>
                    {isExpanded && (
                      <div className="px-5 pb-5 border-t border-white/[0.03]">
                        <div className="text-sm text-gray-300 leading-relaxed whitespace-pre-line pt-3">{content}</div>
                      </div>
                    )}
                  </div>
                );
              })}
            </>
          )}
        </div>

        {/* Sidebar: Report history (1 col) */}
        <div className="space-y-4">
          <div className="bg-[#12141A] border border-white/[0.05] rounded-xl p-5" data-testid="report-history">
            <div className="flex items-center gap-2 mb-3">
              <Calendar className="w-4 h-4 text-gray-400" />
              <h3 className="text-sm font-medium text-white" style={{ fontFamily: 'Outfit' }}>Report History</h3>
            </div>
            {reports.length === 0 ? (
              <p className="text-xs text-gray-600 py-4 text-center">No reports generated</p>
            ) : (
              <div className="space-y-2">
                {reports.map(r => (
                  <button key={r.id} onClick={() => loadReport(r.id)}
                    className={`w-full text-left p-3 rounded-lg transition-colors text-xs ${
                      activeReport?.id === r.id ? 'bg-blue-600/10 border border-blue-500/20' : 'hover:bg-white/[0.04] border border-transparent'
                    }`} data-testid={`report-${r.id}`}>
                    <p className="text-white font-medium">{r.week_label}</p>
                    <p className="text-gray-500 mt-0.5">{r.created_at?.slice(0, 10)}</p>
                    <p className="text-gray-400 mt-1 line-clamp-2">{r.executive_summary?.slice(0, 100)}...</p>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
