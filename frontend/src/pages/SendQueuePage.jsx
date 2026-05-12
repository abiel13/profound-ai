import React, { useState, useEffect, useCallback } from "react";
import axios from "axios";
import { useAuth } from "@/context/AuthContext";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { SendHorizontal, Trash2, CheckCircle2, XCircle, RefreshCw, Copy, ShieldCheck } from "lucide-react";

import { API } from "../config";

const STATUS_STYLES = {
  pending: "bg-amber-500/10 text-amber-400",
  approved: "bg-blue-500/10 text-blue-400",
  sent: "bg-emerald-500/10 text-emerald-400",
  cancelled: "bg-gray-500/10 text-gray-400",
};
const CHANNEL_STYLES = {
  whatsapp: "bg-green-600/10 text-green-400",
  email: "bg-blue-500/10 text-blue-400",
  sms: "bg-purple-500/10 text-purple-400",
};

export default function SendQueuePage() {
  const { authHeaders } = useAuth();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("");
  const [expandedId, setExpandedId] = useState(null);

  const fetch = useCallback(async () => {
    try {
      const url = filter ? `${API}/v11/queue?status=${filter}` : `${API}/v11/queue`;
      const r = await axios.get(url, { headers: authHeaders() });
      setItems(r.data || []);
    } catch { toast.error("Failed to load queue"); }
    finally { setLoading(false); }
  }, [authHeaders, filter]);

  useEffect(() => { fetch(); }, [fetch]);

  const markSent = async (id) => {
    try {
      await axios.post(`${API}/v11/queue/${id}/mark-sent`, {}, { headers: authHeaders() });
      toast.success("Marked as sent — simulated donation logged");
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Only approved items can be marked sent");
    }
    fetch();
  };
  const approve = async (id) => {
    try {
      await axios.post(`${API}/v11/queue/${id}/approve`, {}, { headers: authHeaders() });
      toast.success("Approved");
    } catch {
      toast.error("Failed to approve");
    }
    fetch();
  };
  const cancel = async (id) => {
    await axios.post(`${API}/v11/queue/${id}/cancel`, {}, { headers: authHeaders() });
    toast.success("Cancelled");
    fetch();
  };
  const del = async (id) => {
    if (!window.confirm("Delete this queue item?")) return;
    await axios.delete(`${API}/v11/queue/${id}`, { headers: authHeaders() });
    fetch();
  };

  const counts = {
    pending: items.filter(i => i.status === "pending").length,
    approved: items.filter(i => i.status === "approved").length,
    sent: items.filter(i => i.status === "sent").length,
    cancelled: items.filter(i => i.status === "cancelled").length,
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6" data-testid="send-queue-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-semibold text-white tracking-tight flex items-center gap-3">
            <SendHorizontal className="w-7 h-7 text-indigo-400" />
            Send Queue
          </h1>
          <p className="text-sm text-gray-400 mt-1">
            All outbound messages queue here. <span className="text-amber-400">MOCK mode</span> — nothing is sent automatically. WhatsApp &amp; Meta APIs will plug in here later.
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={fetch} data-testid="refresh-queue-btn">
          <RefreshCw className="w-4 h-4 mr-2" />Refresh
        </Button>
      </div>

      {/* Filter pills */}
      <div className="flex items-center gap-2">
        {[["", `All (${items.length})`], ["pending", `Pending (${counts.pending})`], ["approved", `Approved (${counts.approved})`], ["sent", `Sent (${counts.sent})`], ["cancelled", `Cancelled (${counts.cancelled})`]].map(([k, label]) => (
          <button
            key={k || "all"}
            onClick={() => setFilter(k)}
            data-testid={`queue-filter-${k || "all"}`}
            className={`text-xs px-3 py-1.5 rounded-full border transition-colors ${
              filter === k ? "bg-white/10 text-white border-white/20" : "bg-white/[0.02] text-gray-400 border-white/[0.06] hover:text-white"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {loading ? <div className="text-gray-500 text-sm">Loading…</div> :
       items.length === 0 ? (
        <div className="text-gray-500 text-sm py-12 text-center glass-surface border border-white/[0.06] rounded-xl" data-testid="queue-empty">
          Queue is empty. Push messages from Campaigns or Sponsors.
        </div>
      ) : (
        <div className="space-y-2">
          {items.map((i) => {
            const isOpen = expandedId === i.id;
            return (
              <div key={i.id} className="glass-surface border border-white/[0.06] rounded-xl p-4" data-testid={`queue-item-${i.id}`}>
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0 cursor-pointer" onClick={() => setExpandedId(isOpen ? null : i.id)}>
                    <div className="flex items-center gap-2 flex-wrap">
                      <Badge className={CHANNEL_STYLES[i.channel] || "bg-gray-500/10 text-gray-400"}>{i.channel}</Badge>
                      <Badge className={STATUS_STYLES[i.status]}>{i.status}</Badge>
                      {i.mock === 1 && <Badge className="bg-amber-500/10 text-amber-400 text-[10px]">MOCK</Badge>}
                      <span className="text-xs text-gray-500">{i.target_type}</span>
                    </div>
                    <div className="flex items-baseline gap-2 mt-1">
                      <span className="text-sm text-white font-medium">{i.recipient_label || i.recipient || "(no recipient)"}</span>
                      {i.recipient_label && <span className="text-xs text-gray-500">{i.recipient}</span>}
                    </div>
                    {i.subject && <div className="text-xs text-gray-400 mt-0.5">Subject: {i.subject}</div>}
                    <p className="text-xs text-gray-500 mt-1 truncate">{i.message?.slice(0, 140)}</p>
                  </div>
                  <div className="flex items-center gap-1">
                    {i.status === "pending" && (
                      <>
                        <Button size="sm" variant="outline" onClick={() => approve(i.id)} data-testid={`approve-${i.id}`}>
                          <ShieldCheck className="w-3.5 h-3.5 mr-1 text-blue-400" />Approve
                        </Button>
                        <Button size="sm" variant="ghost" onClick={() => cancel(i.id)} data-testid={`cancel-${i.id}`}>
                          <XCircle className="w-4 h-4 text-gray-400" />
                        </Button>
                      </>
                    )}
                    {i.status === "approved" && (
                      <>
                        <Button size="sm" variant="outline" onClick={() => markSent(i.id)} data-testid={`mark-sent-${i.id}`}>
                          <CheckCircle2 className="w-3.5 h-3.5 mr-1 text-emerald-400" />Mark Sent
                        </Button>
                        <Button size="sm" variant="ghost" onClick={() => cancel(i.id)} data-testid={`cancel-${i.id}`}>
                          <XCircle className="w-4 h-4 text-gray-400" />
                        </Button>
                      </>
                    )}
                    <Button size="sm" variant="ghost" onClick={() => del(i.id)} data-testid={`delete-queue-${i.id}`}>
                      <Trash2 className="w-4 h-4 text-red-400" />
                    </Button>
                  </div>
                </div>
                {isOpen && (
                  <div className="mt-3 border-t border-white/[0.06] pt-3 space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-gray-400">Full message</span>
                      <Button size="sm" variant="ghost" className="h-6 px-2" onClick={() => { navigator.clipboard.writeText(i.message || ""); toast.success("Copied"); }}>
                        <Copy className="w-3 h-3" />
                      </Button>
                    </div>
                    <div className="text-sm text-gray-200 whitespace-pre-wrap bg-white/[0.02] rounded-md p-3 border border-white/[0.04]">
                      {i.message || "(empty)"}
                    </div>
                    {i.payment_link && (
                      <div className="text-xs text-gray-400">
                        Payment link: <span className="text-blue-400 break-all">{i.payment_link}</span>
                      </div>
                    )}
                    <div className="flex gap-4 text-[11px] text-gray-500">
                      <span>Created: {i.created_at?.slice(0, 19).replace("T", " ")}</span>
                      {i.sent_at && <span>Sent: {i.sent_at?.slice(0, 19).replace("T", " ")}</span>}
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
