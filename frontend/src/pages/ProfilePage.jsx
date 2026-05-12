import React, { useState, useEffect } from "react";
import axios from "axios";
import { useAuth } from "@/context/AuthContext";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Building2, Save, Plus, X } from "lucide-react";

import { API } from "../config";

export default function ProfilePage() {
  const { authHeaders } = useAuth();
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [newSector, setNewSector] = useState("");
  const [newBeneficiary, setNewBeneficiary] = useState("");

  useEffect(() => { fetchProfile(); }, []);

  const fetchProfile = async () => {
    try {
      const res = await axios.get(`${API}/profile`, { headers: authHeaders() });
      setProfile(res.data);
    } catch {
      toast.error("Failed to load profile");
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const res = await axios.put(`${API}/profile`, profile, { headers: authHeaders() });
      setProfile(res.data);
      toast.success("Profile updated successfully");
    } catch {
      toast.error("Failed to update profile");
    } finally {
      setSaving(false);
    }
  };

  const addSector = () => {
    if (newSector.trim() && !profile.focus_sectors.includes(newSector.trim())) {
      setProfile(prev => ({ ...prev, focus_sectors: [...prev.focus_sectors, newSector.trim()] }));
      setNewSector("");
    }
  };

  const removeSector = (s) => {
    setProfile(prev => ({ ...prev, focus_sectors: prev.focus_sectors.filter(x => x !== s) }));
  };

  const addBeneficiary = () => {
    if (newBeneficiary.trim() && !profile.beneficiaries.includes(newBeneficiary.trim())) {
      setProfile(prev => ({ ...prev, beneficiaries: [...prev.beneficiaries, newBeneficiary.trim()] }));
      setNewBeneficiary("");
    }
  };

  const removeBeneficiary = (b) => {
    setProfile(prev => ({ ...prev, beneficiaries: prev.beneficiaries.filter(x => x !== b) }));
  };

  if (loading) {
    return (
      <div className="space-y-4 animate-fade-in">
        <div className="h-8 w-48 skeleton-loading rounded-lg" />
        <div className="h-96 skeleton-loading rounded-xl" />
      </div>
    );
  }

  if (!profile) return null;

  return (
    <div className="space-y-6 animate-fade-in max-w-3xl" data-testid="profile-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl sm:text-3xl font-semibold text-white tracking-tight" style={{ fontFamily: 'Outfit, sans-serif' }}>
            Organization Profile
          </h1>
          <p className="text-sm text-gray-400 mt-1">AI uses this to match grants to your organization</p>
        </div>
        <Button onClick={handleSave} disabled={saving} data-testid="save-profile-btn" className="bg-blue-600 hover:bg-blue-500 text-white">
          <Save className="w-4 h-4 mr-2" />
          {saving ? "Saving..." : "Save"}
        </Button>
      </div>

      <div className="bg-[#12141A] border border-white/[0.05] rounded-xl p-6 space-y-5">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
          <div className="space-y-2">
            <Label className="text-sm text-gray-300">Organization Name</Label>
            <Input
              value={profile.name}
              onChange={(e) => setProfile(prev => ({ ...prev, name: e.target.value }))}
              className="bg-[#0B0C10] border-white/10 text-white h-11"
              data-testid="profile-name-input"
            />
          </div>
          <div className="space-y-2">
            <Label className="text-sm text-gray-300">Country</Label>
            <Input
              value={profile.country}
              onChange={(e) => setProfile(prev => ({ ...prev, country: e.target.value }))}
              className="bg-[#0B0C10] border-white/10 text-white h-11"
              data-testid="profile-country-input"
            />
          </div>
        </div>

        <div className="space-y-2">
          <Label className="text-sm text-gray-300">Mission Statement</Label>
          <Textarea
            value={profile.mission}
            onChange={(e) => setProfile(prev => ({ ...prev, mission: e.target.value }))}
            rows={3}
            className="bg-[#0B0C10] border-white/10 text-white resize-none"
            data-testid="profile-mission-input"
          />
        </div>

        {/* Focus Sectors */}
        <div className="space-y-2">
          <Label className="text-sm text-gray-300">Focus Sectors</Label>
          <div className="flex flex-wrap gap-2 mb-2">
            {profile.focus_sectors.map(s => (
              <Badge key={s} className="bg-blue-600/10 text-blue-400 border-0 gap-1 pr-1">
                {s}
                <button onClick={() => removeSector(s)} className="ml-1 hover:text-white"><X className="w-3 h-3" /></button>
              </Badge>
            ))}
          </div>
          <div className="flex gap-2">
            <Input
              value={newSector}
              onChange={(e) => setNewSector(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), addSector())}
              placeholder="Add sector..."
              className="bg-[#0B0C10] border-white/10 text-white h-9 text-sm"
              data-testid="add-sector-input"
            />
            <Button onClick={addSector} size="sm" className="bg-white/[0.06] text-gray-300 hover:bg-white/10 h-9">
              <Plus className="w-4 h-4" />
            </Button>
          </div>
        </div>

        {/* Beneficiaries */}
        <div className="space-y-2">
          <Label className="text-sm text-gray-300">Target Beneficiaries</Label>
          <div className="flex flex-wrap gap-2 mb-2">
            {profile.beneficiaries.map(b => (
              <Badge key={b} className="bg-emerald-600/10 text-emerald-400 border-0 gap-1 pr-1">
                {b}
                <button onClick={() => removeBeneficiary(b)} className="ml-1 hover:text-white"><X className="w-3 h-3" /></button>
              </Badge>
            ))}
          </div>
          <div className="flex gap-2">
            <Input
              value={newBeneficiary}
              onChange={(e) => setNewBeneficiary(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), addBeneficiary())}
              placeholder="Add beneficiary..."
              className="bg-[#0B0C10] border-white/10 text-white h-9 text-sm"
              data-testid="add-beneficiary-input"
            />
            <Button onClick={addBeneficiary} size="sm" className="bg-white/[0.06] text-gray-300 hover:bg-white/10 h-9">
              <Plus className="w-4 h-4" />
            </Button>
          </div>
        </div>

        {/* Funding Needs */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
          <div className="space-y-2">
            <Label className="text-sm text-gray-300">Min Funding Need (USD)</Label>
            <Input
              type="number"
              value={profile.funding_needs_min}
              onChange={(e) => setProfile(prev => ({ ...prev, funding_needs_min: parseFloat(e.target.value) || 0 }))}
              className="bg-[#0B0C10] border-white/10 text-white h-11"
              data-testid="profile-funding-min-input"
            />
          </div>
          <div className="space-y-2">
            <Label className="text-sm text-gray-300">Max Funding Need (USD)</Label>
            <Input
              type="number"
              value={profile.funding_needs_max}
              onChange={(e) => setProfile(prev => ({ ...prev, funding_needs_max: parseFloat(e.target.value) || 0 }))}
              className="bg-[#0B0C10] border-white/10 text-white h-11"
              data-testid="profile-funding-max-input"
            />
          </div>
        </div>
      </div>
    </div>
  );
}
