import React, { useState, useEffect } from "react";
import axios from "axios";
import { useAuth } from "@/context/AuthContext";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Bookmark, Calendar, DollarSign, Trash2, StickyNote } from "lucide-react";
import { Textarea } from "@/components/ui/textarea";

import { API } from "../config";

const STATUS_OPTIONS = ["New", "Identified", "Analyzing", "Reviewing", "Drafting", "Preparing", "Ready to Submit", "Submitted", "Rejected", "Approved"];
const STATUS_COLORS = {
  New: "status-new",
  Identified: "status-new",
  Analyzing: "status-reviewing",
  Reviewing: "status-reviewing",
  Drafting: "status-preparing",
  Preparing: "status-preparing",
  "Ready to Submit": "status-submitted",
  Submitted: "status-submitted",
  Rejected: "status-rejected",
  Approved: "status-approved",
};

function getDaysUntil(deadline) {
  return Math.ceil((new Date(deadline) - new Date()) / (1000 * 60 * 60 * 24));
}

function formatCurrency(min, max) {
  const fmt = (n) => n >= 1000000 ? `$${(n/1000000).toFixed(1)}M` : n >= 1000 ? `$${(n/1000).toFixed(0)}K` : `$${n}`;
  return `${fmt(min)} - ${fmt(max)}`;
}

export default function SavedPage() {
  const { authHeaders } = useAuth();
  const navigate = useNavigate();
  const [saved, setSaved] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => { fetchSaved(); }, []);

  const fetchSaved = async () => {
    try {
      const res = await axios.get(`${API}/saved`, { headers: authHeaders() });
      setSaved(res.data);
    } catch {
      toast.error("Failed to load saved opportunities");
    } finally {
      setLoading(false);
    }
  };

  const updateStatus = async (savedId, status) => {
    try {
      await axios.put(`${API}/saved/${savedId}`, { status }, { headers: authHeaders() });
      setSaved(prev => prev.map(s => s.saved_id === savedId ? { ...s, status } : s));
      toast.success(`Status updated to ${status}`);
    } catch {
      toast.error("Failed to update status");
    }
  };

  const removeSaved = async (savedId) => {
    try {
      await axios.delete(`${API}/saved/${savedId}`, { headers: authHeaders() });
      setSaved(prev => prev.filter(s => s.saved_id !== savedId));
      toast.success("Removed from saved");
    } catch {
      toast.error("Failed to remove");
    }
  };

  if (loading) {
    return (
      <div className="space-y-4 animate-fade-in">
        <div className="h-8 w-48 skeleton-loading rounded-lg" />
        {[1,2,3].map(i => <div key={i} className="h-32 skeleton-loading rounded-xl" />)}
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in" data-testid="saved-page">
      <div>
        <h1 className="text-2xl sm:text-3xl font-semibold text-white tracking-tight" style={{ fontFamily: 'Outfit, sans-serif' }}>
          Saved Opportunities
        </h1>
        <p className="text-sm text-gray-400 mt-1">Track and manage your selected funding opportunities</p>
      </div>

      {saved.length === 0 ? (
        <div className="text-center py-16">
          <Bookmark className="w-12 h-12 text-gray-600 mx-auto mb-3" />
          <p className="text-gray-400">No saved opportunities yet</p>
          <button onClick={() => navigate("/search")} className="text-sm text-blue-400 hover:text-blue-300 mt-2">
            Search opportunities
          </button>
        </div>
      ) : (
        <div className="space-y-3" data-testid="saved-list">
          {saved.map(item => {
            const days = getDaysUntil(item.deadline);
            return (
              <div
                key={item.saved_id}
                data-testid={`saved-item-${item.saved_id}`}
                className="bg-[#12141A] border border-white/[0.05] rounded-xl p-5 card-hover"
              >
                <div className="flex flex-col sm:flex-row sm:items-center gap-4">
                  <div className="flex-1 min-w-0 cursor-pointer" onClick={() => navigate(`/opportunity/${item.id}`)}>
                    <h3 className="text-sm font-semibold text-white hover:text-blue-400 transition-colors line-clamp-1" style={{ fontFamily: 'Outfit, sans-serif' }}>
                      {item.title}
                    </h3>
                    <p className="text-xs text-gray-400 mt-1">{item.donor_name}</p>
                    <div className="flex items-center gap-4 mt-2 text-xs">
                      <span className="flex items-center gap-1 text-gray-400">
                        <DollarSign className="w-3 h-3" />
                        {formatCurrency(item.funding_min, item.funding_max)}
                      </span>
                      <span className={`flex items-center gap-1 ${days <= 14 ? 'text-amber-400' : 'text-gray-400'}`}>
                        <Calendar className="w-3 h-3" />
                        {days > 0 ? `${days} days left` : "Expired"}
                      </span>
                    </div>
                  </div>
                  <div className="flex items-center gap-3 shrink-0">
                    <Select value={item.status} onValueChange={(val) => updateStatus(item.saved_id, val)}>
                      <SelectTrigger className={`w-[140px] h-9 text-xs border-0 rounded-lg ${STATUS_COLORS[item.status] || ""}`} data-testid={`status-select-${item.saved_id}`}>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent className="bg-[#1A1D24] border-white/10">
                        {STATUS_OPTIONS.map(s => (
                          <SelectItem key={s} value={s} className="text-gray-300 text-xs">{s}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <button
                      onClick={() => removeSaved(item.saved_id)}
                      data-testid={`remove-saved-${item.saved_id}`}
                      className="p-2 rounded-lg text-gray-500 hover:text-red-400 hover:bg-red-500/10 transition-colors"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
