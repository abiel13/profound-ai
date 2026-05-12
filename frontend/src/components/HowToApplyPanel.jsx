import React, { useState } from "react";
import axios from "axios";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  ExternalLink, Mail, Copy, Send, RefreshCw, Loader2, Calendar,
  FileDown, ClipboardList, Globe2, AlertCircle
} from "lucide-react";
import jsPDF from "jspdf";

import { API } from "../config";
import { useAuth } from "@/context/AuthContext";

function daysUntil(d) {
  if (!d) return null;
  const t = new Date(d);
  if (isNaN(t)) return null;
  return Math.ceil((t - new Date()) / 86400000);
}

function joinDocs(docs) {
  if (!docs) return "";
  const order = [
    ["cover_letter", "COVER LETTER"],
    ["executive_summary", "EXECUTIVE SUMMARY"],
    ["project_narrative", "PROJECT NARRATIVE"],
    ["budget_justification", "BUDGET JUSTIFICATION"],
    ["sustainability_plan", "SUSTAINABILITY PLAN"],
    ["monitoring_plan", "MONITORING & EVALUATION"],
  ];
  const parts = [];
  order.forEach(([key, label]) => {
    const v = (docs[key] || "").trim();
    if (v) parts.push(`${label}\n${"=".repeat(label.length)}\n\n${v}`);
  });
  return parts.join("\n\n\n");
}

export default function HowToApplyPanel({ opportunity, documents, onRefreshOpp }) {
  const { authHeaders } = useAuth();
  const [refreshing, setRefreshing] = useState(false);
  const [emailGen, setEmailGen] = useState(null); // { to, subject, body }
  const [genLoading, setGenLoading] = useState(false);

  const opp = opportunity || {};
  const subType = (opp.submission_type || "").toLowerCase();
  const portalUrl = opp.submission_url || opp.url || "";
  const contactEmail = opp.submission_email || "";
  const days = daysUntil(opp.deadline);

  const refreshSubmission = async () => {
    if (!opp.id) return;
    setRefreshing(true);
    try {
      await axios.post(`${API}/opportunities/${opp.id}/fetch-submission`, {}, { headers: authHeaders() });
      toast.success("Submission details refreshed");
      if (onRefreshOpp) await onRefreshOpp();
    } catch {
      toast.error("Failed to fetch submission details");
    } finally {
      setRefreshing(false);
    }
  };

  const copyEmail = async () => {
    if (!contactEmail) return;
    await navigator.clipboard.writeText(contactEmail);
    toast.success(`Copied ${contactEmail}`);
  };

  const openMail = () => {
    const subject = encodeURIComponent(emailGen?.subject || `Grant Application – ${opp.title || ""}`);
    const body = encodeURIComponent(emailGen?.body || "");
    window.location.href = `mailto:${contactEmail}?subject=${subject}&body=${body}`;
  };

  const generateEmailTemplate = async () => {
    if (!opp.id) return;
    setGenLoading(true);
    try {
      const res = await axios.post(`${API}/opportunities/${opp.id}/email-template`, {}, { headers: authHeaders() });
      setEmailGen(res.data);
      toast.success("Email template generated");
    } catch {
      toast.error("Failed to generate email");
    } finally {
      setGenLoading(false);
    }
  };

  const copyAll = async () => {
    const txt = joinDocs(documents);
    if (!txt) {
      toast.error("No documents to copy yet");
      return;
    }
    await navigator.clipboard.writeText(txt);
    toast.success("Full application copied to clipboard");
  };

  const downloadPdf = () => {
    const txt = joinDocs(documents);
    if (!txt) {
      toast.error("No documents to export");
      return;
    }
    const doc = new jsPDF({ unit: "pt", format: "a4" });
    const margin = 48;
    const pageWidth = doc.internal.pageSize.getWidth();
    const pageHeight = doc.internal.pageSize.getHeight();
    const usableWidth = pageWidth - margin * 2;

    doc.setFont("helvetica", "bold");
    doc.setFontSize(16);
    doc.text(opp.title || "Grant Application", margin, margin);
    doc.setFont("helvetica", "normal");
    doc.setFontSize(10);
    doc.setTextColor(120);
    doc.text(`${opp.donor_name || ""}${opp.deadline ? "  •  Deadline: " + opp.deadline : ""}`, margin, margin + 16);
    doc.setTextColor(0);

    let y = margin + 40;
    doc.setFontSize(11);
    const lines = doc.splitTextToSize(txt, usableWidth);
    lines.forEach((line) => {
      if (y > pageHeight - margin) {
        doc.addPage();
        y = margin;
      }
      doc.text(line, margin, y);
      y += 14;
    });

    const safeTitle = (opp.title || "application").replace(/[^a-z0-9]+/gi, "_").slice(0, 60);
    doc.save(`${safeTitle}.pdf`);
    toast.success("PDF downloaded");
  };

  // ----- Render --------------------------------------------------------
  return (
    <div className="space-y-5" data-testid="how-to-apply-panel">
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <ClipboardList className="w-5 h-5 text-emerald-400" />
            <h3 className="text-base font-semibold text-white" style={{ fontFamily: "Outfit" }}>
              How to Apply
            </h3>
          </div>
          <p className="text-xs text-gray-400 mt-1">
            Submission details fetched from the official source. Apply manually using the link
            or email below.
          </p>
        </div>
        <Button
          onClick={refreshSubmission}
          disabled={refreshing}
          variant="outline"
          className="border-white/10 text-gray-300 text-xs"
          data-testid="refresh-submission-btn"
        >
          {refreshing ? <Loader2 className="w-3.5 h-3.5 mr-2 animate-spin" /> : <RefreshCw className="w-3.5 h-3.5 mr-2" />}
          Refresh
        </Button>
      </div>

      {/* Submission method strip */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <InfoTile
          label="Method"
          value={subType ? subType.toUpperCase() : "UNKNOWN"}
          tone={subType === "portal" ? "blue" : subType === "email" ? "emerald" : subType === "form" ? "amber" : "gray"}
          icon={subType === "email" ? Mail : Globe2}
        />
        <InfoTile
          label="Deadline"
          value={opp.deadline || "—"}
          tone={days !== null && days < 14 ? "amber" : "gray"}
          sub={days !== null ? `${days}d left` : ""}
          icon={Calendar}
        />
        <InfoTile
          label="Country eligibility"
          value={opp.donor_country || opp.region || "Open"}
          tone="gray"
          icon={Globe2}
        />
      </div>

      {/* Apply button (portal) */}
      {portalUrl && (
        <div className="bg-blue-500/5 border border-blue-500/15 rounded-xl p-4">
          <p className="text-xs text-blue-400 uppercase tracking-wider mb-2">Application Portal</p>
          <p className="text-xs text-gray-400 mb-3 break-all">{portalUrl}</p>
          <a href={portalUrl} target="_blank" rel="noopener noreferrer" data-testid="open-portal-btn">
            <Button className="bg-blue-600 hover:bg-blue-500 text-white">
              <ExternalLink className="w-4 h-4 mr-2" /> Open Application Portal
            </Button>
          </a>
        </div>
      )}

      {/* Email row */}
      {contactEmail ? (
        <div className="bg-emerald-500/5 border border-emerald-500/15 rounded-xl p-4">
          <p className="text-xs text-emerald-400 uppercase tracking-wider mb-2">Email Submission</p>
          <p className="text-sm text-gray-200 font-mono break-all" data-testid="submission-email">{contactEmail}</p>
          <div className="flex flex-wrap items-center gap-2 mt-3">
            <Button onClick={copyEmail} variant="outline" className="border-white/10 text-gray-300 text-xs" data-testid="copy-email-btn">
              <Copy className="w-3.5 h-3.5 mr-2" />Copy Email
            </Button>
            <Button onClick={openMail} variant="outline" className="border-white/10 text-gray-300 text-xs" data-testid="open-mail-btn">
              <Send className="w-3.5 h-3.5 mr-2" />Open Mail Client
            </Button>
            <Button onClick={generateEmailTemplate} disabled={genLoading} className="bg-emerald-600 hover:bg-emerald-500 text-white text-xs" data-testid="generate-email-template-btn">
              {genLoading ? <Loader2 className="w-3.5 h-3.5 mr-2 animate-spin" /> : <Mail className="w-3.5 h-3.5 mr-2" />}
              Generate Email Template
            </Button>
          </div>
          {emailGen && (
            <div className="mt-4 space-y-2 bg-[#0B0C10] border border-white/[0.06] rounded-lg p-3" data-testid="email-template-preview">
              <div>
                <p className="text-[10px] text-gray-500 uppercase tracking-wider">Subject</p>
                <p className="text-sm text-gray-200">{emailGen.subject}</p>
              </div>
              <div>
                <p className="text-[10px] text-gray-500 uppercase tracking-wider">Body</p>
                <pre className="text-xs text-gray-300 whitespace-pre-wrap font-sans">{emailGen.body}</pre>
              </div>
              <div className="flex gap-2">
                <Button
                  onClick={async () => {
                    await navigator.clipboard.writeText(`${emailGen.subject}\n\n${emailGen.body}`);
                    toast.success("Email copied");
                  }}
                  variant="outline"
                  className="border-white/10 text-gray-300 text-xs"
                  data-testid="copy-email-template-btn"
                >
                  <Copy className="w-3.5 h-3.5 mr-2" />Copy Email
                </Button>
              </div>
            </div>
          )}
        </div>
      ) : (
        <div className="bg-[#0B0C10] border border-white/[0.05] rounded-xl p-4 flex items-start gap-3">
          <AlertCircle className="w-4 h-4 text-amber-400 mt-0.5" />
          <div>
            <p className="text-sm text-gray-300">No email address detected on the official page.</p>
            <p className="text-xs text-gray-500 mt-1">
              Use the portal link above, or click "Refresh" to re-scan.
            </p>
          </div>
        </div>
      )}

      {/* Instructions */}
      {opp.apply_instructions && (
        <div className="bg-[#0B0C10] border border-white/[0.05] rounded-xl p-4">
          <p className="text-xs text-gray-500 uppercase tracking-wider mb-2">Instructions snippet</p>
          <p className="text-sm text-gray-300 italic">"{opp.apply_instructions}"</p>
        </div>
      )}

      {/* Export */}
      <div className="bg-[#0B0C10] border border-white/[0.05] rounded-xl p-4">
        <p className="text-xs text-gray-500 uppercase tracking-wider mb-3">Export Full Application</p>
        <div className="flex flex-wrap gap-2">
          <Button onClick={copyAll} className="bg-purple-600 hover:bg-purple-500 text-white text-xs" data-testid="copy-all-btn">
            <Copy className="w-3.5 h-3.5 mr-2" />Copy All
          </Button>
          <Button onClick={downloadPdf} variant="outline" className="border-white/10 text-gray-300 text-xs" data-testid="download-pdf-btn">
            <FileDown className="w-3.5 h-3.5 mr-2" />Download as PDF
          </Button>
        </div>
        <p className="text-[11px] text-gray-500 mt-2">
          Combines cover letter, executive summary, project narrative, and budget into one
          paste-ready document.
        </p>
      </div>
    </div>
  );
}

function InfoTile({ label, value, sub, tone = "gray", icon: Icon }) {
  const colors = {
    blue: "text-blue-400 bg-blue-500/5 border-blue-500/15",
    emerald: "text-emerald-400 bg-emerald-500/5 border-emerald-500/15",
    amber: "text-amber-400 bg-amber-500/5 border-amber-500/15",
    gray: "text-gray-300 bg-[#0B0C10] border-white/[0.06]",
  }[tone];
  return (
    <div className={`rounded-lg border p-3 ${colors}`}>
      <div className="flex items-center gap-2 text-[10px] uppercase tracking-wider opacity-80">
        {Icon && <Icon className="w-3 h-3" />} {label}
      </div>
      <p className="text-sm font-medium mt-1 break-words">{value}</p>
      {sub && <p className="text-[11px] opacity-70 mt-0.5">{sub}</p>}
    </div>
  );
}
