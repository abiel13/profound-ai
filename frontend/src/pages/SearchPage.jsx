import React, { useState, useEffect } from "react";
import axios from "axios";
import { useAuth } from "@/context/AuthContext";
import OpportunityCard from "@/components/OpportunityCard";
import { toast } from "sonner";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Search as SearchIcon, SlidersHorizontal, X } from "lucide-react";

import { API } from "../config";

export default function SearchPage() {
  const { authHeaders } = useAuth();
  const [opportunities, setOpportunities] = useState([]);
  const [filters, setFilters] = useState({ sectors: [], donor_types: [] });
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [sector, setSector] = useState("all");
  const [donorType, setDonorType] = useState("all");
  const [sortBy, setSortBy] = useState("deadline");
  const [submission, setSubmission] = useState("all");
  const [savedIds, setSavedIds] = useState(new Set());
  const [showFilters, setShowFilters] = useState(false);

  useEffect(() => {
    fetchFilters();
    fetchSaved();
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => fetchOpportunities(), 300);
    return () => clearTimeout(timer);
  }, [search, sector, donorType, sortBy, submission]);

  const fetchFilters = async () => {
    try {
      const res = await axios.get(`${API}/filters`, { headers: authHeaders() });
      setFilters(res.data);
    } catch { /* ignore */ }
  };

  const fetchSaved = async () => {
    try {
      const res = await axios.get(`${API}/saved`, { headers: authHeaders() });
      setSavedIds(new Set(res.data.map(s => s.id)));
    } catch { /* ignore */ }
  };

  const fetchOpportunities = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (search) params.append("search", search);
      if (sector && sector !== "all") params.append("sector", sector);
      if (donorType && donorType !== "all") params.append("donor_type", donorType);
      if (submission && submission !== "all") params.append("submission", submission);
      if (sortBy) params.append("sort_by", sortBy);
      const res = await axios.get(`${API}/opportunities?${params}`, { headers: authHeaders() });
      setOpportunities(res.data);
    } catch {
      toast.error("Failed to load opportunities");
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (oppId) => {
    try {
      await axios.post(`${API}/saved`, { opportunity_id: oppId }, { headers: authHeaders() });
      setSavedIds(prev => new Set([...prev, oppId]));
      toast.success("Opportunity saved");
    } catch {
      toast.error("Failed to save");
    }
  };

  const clearFilters = () => {
    setSearch("");
    setSector("all");
    setDonorType("all");
    setSortBy("deadline");
    setSubmission("all");
  };

  const hasActiveFilters = search || (sector && sector !== "all") || (donorType && donorType !== "all") || (submission && submission !== "all");

  return (
    <div className="space-y-6 animate-fade-in" data-testid="search-page">
      {/* Header */}
      <div>
        <h1 className="text-2xl sm:text-3xl font-semibold text-white tracking-tight" style={{ fontFamily: 'Outfit, sans-serif' }}>
          Search Opportunities
        </h1>
        <p className="text-sm text-gray-400 mt-1">Find international grants, donations, and funding</p>
      </div>

      {/* Search + Filters */}
      <div className="space-y-4">
        <div className="flex gap-3">
          <div className="relative flex-1">
            <SearchIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search grants, donors, sectors..."
              className="pl-10 bg-[#12141A] border-white/10 text-white placeholder:text-gray-600 h-11"
              data-testid="search-input"
            />
          </div>
          <button
            onClick={() => setShowFilters(!showFilters)}
            data-testid="toggle-filters-btn"
            className={`flex items-center gap-2 px-4 h-11 rounded-lg border text-sm font-medium transition-colors ${
              showFilters ? "bg-blue-600/10 border-blue-500/30 text-blue-400" : "bg-[#12141A] border-white/10 text-gray-400 hover:text-white"
            }`}
          >
            <SlidersHorizontal className="w-4 h-4" />
            Filters
          </button>
        </div>

        {showFilters && (
          <div className="flex flex-wrap gap-3 p-4 bg-[#12141A] border border-white/[0.05] rounded-xl" data-testid="filter-panel">
            <Select value={sector} onValueChange={setSector}>
              <SelectTrigger className="w-[180px] bg-[#0B0C10] border-white/10 text-gray-300 h-10" data-testid="filter-sector">
                <SelectValue placeholder="Sector" />
              </SelectTrigger>
              <SelectContent className="bg-[#1A1D24] border-white/10">
                <SelectItem value="all" className="text-gray-300">All Sectors</SelectItem>
                {filters.sectors.map(s => (
                  <SelectItem key={s} value={s} className="text-gray-300">{s}</SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select value={donorType} onValueChange={setDonorType}>
              <SelectTrigger className="w-[180px] bg-[#0B0C10] border-white/10 text-gray-300 h-10" data-testid="filter-donor-type">
                <SelectValue placeholder="Donor Type" />
              </SelectTrigger>
              <SelectContent className="bg-[#1A1D24] border-white/10">
                <SelectItem value="all" className="text-gray-300">All Types</SelectItem>
                {filters.donor_types.map(t => (
                  <SelectItem key={t} value={t} className="text-gray-300">{t}</SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select value={sortBy} onValueChange={setSortBy}>
              <SelectTrigger className="w-[180px] bg-[#0B0C10] border-white/10 text-gray-300 h-10" data-testid="filter-sort">
                <SelectValue placeholder="Sort by" />
              </SelectTrigger>
              <SelectContent className="bg-[#1A1D24] border-white/10">
                <SelectItem value="deadline" className="text-gray-300">Deadline (Soonest)</SelectItem>
                <SelectItem value="funding" className="text-gray-300">Funding (Highest)</SelectItem>
                <SelectItem value="match" className="text-gray-300">Match Score</SelectItem>
                <SelectItem value="recent" className="text-gray-300">Recently Added</SelectItem>
              </SelectContent>
            </Select>

            <Select value={submission} onValueChange={setSubmission}>
              <SelectTrigger className="w-[180px] bg-[#0B0C10] border-white/10 text-gray-300 h-10" data-testid="filter-submission">
                <SelectValue placeholder="Submission" />
              </SelectTrigger>
              <SelectContent className="bg-[#1A1D24] border-white/10">
                <SelectItem value="all" className="text-gray-300">All Submission Types</SelectItem>
                <SelectItem value="email" className="text-gray-300">Email Submission</SelectItem>
                <SelectItem value="portal" className="text-gray-300">Open Portal</SelectItem>
                <SelectItem value="form" className="text-gray-300">Downloadable Form</SelectItem>
                <SelectItem value="active" className="text-gray-300">Active Deadline</SelectItem>
              </SelectContent>
            </Select>

            {hasActiveFilters && (
              <button
                onClick={clearFilters}
                data-testid="clear-filters-btn"
                className="flex items-center gap-1 px-3 h-10 text-sm text-gray-400 hover:text-white transition-colors"
              >
                <X className="w-3.5 h-3.5" />
                Clear
              </button>
            )}
          </div>
        )}
      </div>

      {/* Results count */}
      <p className="text-sm text-gray-500">
        {loading ? "Searching..." : `${opportunities.length} opportunities found`}
      </p>

      {/* Results grid */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1,2,3,4,5,6].map(i => <div key={i} className="h-48 skeleton-loading rounded-xl" />)}
        </div>
      ) : opportunities.length === 0 ? (
        <div className="text-center py-16">
          <SearchIcon className="w-12 h-12 text-gray-600 mx-auto mb-3" />
          <p className="text-gray-400">No opportunities found matching your criteria</p>
          <button onClick={clearFilters} className="text-sm text-blue-400 hover:text-blue-300 mt-2">Clear filters</button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4" data-testid="search-results">
          {opportunities.map(opp => (
            <OpportunityCard key={opp.id} opportunity={opp} onSave={handleSave} isSaved={savedIds.has(opp.id)} />
          ))}
        </div>
      )}
    </div>
  );
}
