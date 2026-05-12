import React from "react";
import { useNavigate } from "react-router-dom";
import { Badge } from "@/components/ui/badge";
import { Bookmark, Calendar, DollarSign, MapPin } from "lucide-react";

function getDaysUntil(deadline) {
  const diff = Math.ceil((new Date(deadline) - new Date()) / (1000 * 60 * 60 * 24));
  return diff;
}

function getUrgencyClass(days) {
  if (days <= 7) return "urgency-critical";
  if (days <= 14) return "urgency-high";
  if (days <= 30) return "urgency-medium";
  return "urgency-low";
}

function formatCurrency(min, max) {
  const fmt = (n) => {
    if (n >= 1000000) return `$${(n / 1000000).toFixed(1)}M`;
    if (n >= 1000) return `$${(n / 1000).toFixed(0)}K`;
    return `$${n}`;
  };
  return `${fmt(min)} - ${fmt(max)}`;
}

export default function OpportunityCard({ opportunity, onSave, isSaved, compact = false }) {
  const navigate = useNavigate();
  const days = getDaysUntil(opportunity.deadline);
  const urgencyClass = getUrgencyClass(days);

  return (
    <div
      data-testid={`opportunity-card-${opportunity.id}`}
      className="bg-[#12141A] border border-white/[0.05] rounded-xl p-5 card-hover cursor-pointer group"
      onClick={() => navigate(`/opportunity/${opportunity.id}`)}
    >
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-semibold text-white group-hover:text-blue-400 transition-colors line-clamp-2 leading-snug" style={{ fontFamily: 'Outfit, sans-serif' }}>
            {opportunity.title}
          </h3>
          <p className="text-xs text-gray-400 mt-1">{opportunity.donor_name}</p>
        </div>
        {opportunity.ai_match_score > 0 && (
          <div className="shrink-0 w-10 h-10 rounded-full flex items-center justify-center text-xs font-bold border-2"
            style={{
              borderColor: opportunity.ai_match_score >= 70 ? '#10B981' : opportunity.ai_match_score >= 40 ? '#F59E0B' : '#6B7280',
              color: opportunity.ai_match_score >= 70 ? '#10B981' : opportunity.ai_match_score >= 40 ? '#F59E0B' : '#9CA3AF'
            }}
          >
            {opportunity.ai_match_score}%
          </div>
        )}
      </div>

      <div className="flex flex-wrap gap-1.5 mb-3">
        <Badge variant="secondary" className="text-[10px] bg-blue-600/10 text-blue-400 border-0 px-2 py-0.5">
          {opportunity.donor_type}
        </Badge>
        <Badge variant="secondary" className="text-[10px] bg-white/[0.06] text-gray-300 border-0 px-2 py-0.5">
          {opportunity.sector}
        </Badge>
        {opportunity.africa_eligible === 1 && (
          <Badge variant="secondary" className="text-[10px] bg-emerald-600/10 text-emerald-400 border-0 px-2 py-0.5">
            Africa Eligible
          </Badge>
        )}
        {opportunity.decision_label === "Apply Now" && (
          <Badge variant="secondary" className="text-[10px] bg-green-600/10 text-green-400 border-0 px-2 py-0.5 font-semibold">
            Apply Now
          </Badge>
        )}
        {opportunity.decision_label === "Review First" && (
          <Badge variant="secondary" className="text-[10px] bg-amber-600/10 text-amber-400 border-0 px-2 py-0.5">
            Review First
          </Badge>
        )}
      </div>

      {!compact && (
        <p className="text-xs text-gray-500 line-clamp-2 mb-3 leading-relaxed">
          {opportunity.description?.substring(0, 150)}...
        </p>
      )}

      <div className="flex items-center justify-between text-xs">
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1 text-gray-400">
            <DollarSign className="w-3 h-3" />
            {formatCurrency(opportunity.funding_min, opportunity.funding_max)}
          </span>
          <span className={`flex items-center gap-1 ${urgencyClass}`}>
            <Calendar className="w-3 h-3" />
            {days > 0 ? `${days}d left` : "Expired"}
          </span>
        </div>
        <div className="flex items-center gap-2">
          {opportunity.donor_country && (
            <span className="flex items-center gap-1 text-gray-500">
              <MapPin className="w-3 h-3" />
              {opportunity.donor_country}
            </span>
          )}
          {onSave && !isSaved && (
            <button
              data-testid={`save-btn-${opportunity.id}`}
              onClick={(e) => { e.stopPropagation(); onSave(opportunity.id); }}
              className="p-1.5 rounded-md hover:bg-blue-600/10 text-gray-400 hover:text-blue-400 transition-colors"
            >
              <Bookmark className="w-3.5 h-3.5" />
            </button>
          )}
          {isSaved && (
            <Bookmark className="w-3.5 h-3.5 text-blue-500 fill-blue-500" />
          )}
        </div>
      </div>
    </div>
  );
}
