import React, { useState, useEffect } from "react";
import axios from "axios";
import { useAuth } from "@/context/AuthContext";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Globe2, Plus, Pencil, Trash2, ExternalLink } from "lucide-react";
import { Badge } from "@/components/ui/badge";

import { API } from "../config";
const SOURCE_TYPES = ["UN Agency", "Government", "Foundation", "International NGO", "Corporate CSR", "Other"];

export default function SourcesPage() {
  const { authHeaders } = useAuth();
  const [sources, setSources] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState({ name: "", url: "", type: "", description: "" });

  useEffect(() => { fetchSources(); }, []);

  const fetchSources = async () => {
    try {
      const res = await axios.get(`${API}/sources`, { headers: authHeaders() });
      setSources(res.data);
    } catch {
      toast.error("Failed to load sources");
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (!form.name.trim()) {
      toast.error("Name is required");
      return;
    }
    try {
      if (editing) {
        const res = await axios.put(`${API}/sources/${editing}`, form, { headers: authHeaders() });
        setSources(prev => prev.map(s => s.id === editing ? res.data : s));
        toast.success("Source updated");
      } else {
        const res = await axios.post(`${API}/sources`, form, { headers: authHeaders() });
        setSources(prev => [...prev, res.data]);
        toast.success("Source added");
      }
      resetForm();
    } catch {
      toast.error("Failed to save source");
    }
  };

  const handleDelete = async (id) => {
    try {
      await axios.delete(`${API}/sources/${id}`, { headers: authHeaders() });
      setSources(prev => prev.filter(s => s.id !== id));
      toast.success("Source deleted");
    } catch {
      toast.error("Failed to delete");
    }
  };

  const startEdit = (source) => {
    setEditing(source.id);
    setForm({ name: source.name, url: source.url, type: source.type, description: source.description });
    setDialogOpen(true);
  };

  const resetForm = () => {
    setForm({ name: "", url: "", type: "", description: "" });
    setEditing(null);
    setDialogOpen(false);
  };

  if (loading) {
    return (
      <div className="space-y-4 animate-fade-in">
        <div className="h-8 w-48 skeleton-loading rounded-lg" />
        {[1,2,3].map(i => <div key={i} className="h-20 skeleton-loading rounded-xl" />)}
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in max-w-4xl" data-testid="sources-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl sm:text-3xl font-semibold text-white tracking-tight" style={{ fontFamily: 'Outfit, sans-serif' }}>
            Source Manager
          </h1>
          <p className="text-sm text-gray-400 mt-1">Manage international donor sources and funding databases</p>
        </div>
        <Dialog open={dialogOpen} onOpenChange={(open) => { if (!open) resetForm(); setDialogOpen(open); }}>
          <DialogTrigger asChild>
            <Button data-testid="add-source-btn" className="bg-blue-600 hover:bg-blue-500 text-white">
              <Plus className="w-4 h-4 mr-2" />
              Add Source
            </Button>
          </DialogTrigger>
          <DialogContent className="bg-[#12141A] border-white/10 sm:max-w-lg" data-testid="source-dialog">
            <DialogHeader>
              <DialogTitle className="text-white" style={{ fontFamily: 'Outfit, sans-serif' }}>
                {editing ? "Edit Source" : "Add International Donor Source"}
              </DialogTitle>
            </DialogHeader>
            <div className="space-y-4 mt-4">
              <div className="space-y-2">
                <Label className="text-sm text-gray-300">Source Name</Label>
                <Input
                  value={form.name}
                  onChange={(e) => setForm(prev => ({ ...prev, name: e.target.value }))}
                  placeholder="e.g., World Bank Open Grants"
                  className="bg-[#0B0C10] border-white/10 text-white h-11"
                  data-testid="source-name-input"
                />
              </div>
              <div className="space-y-2">
                <Label className="text-sm text-gray-300">URL</Label>
                <Input
                  value={form.url}
                  onChange={(e) => setForm(prev => ({ ...prev, url: e.target.value }))}
                  placeholder="https://..."
                  className="bg-[#0B0C10] border-white/10 text-white h-11"
                  data-testid="source-url-input"
                />
              </div>
              <div className="space-y-2">
                <Label className="text-sm text-gray-300">Type</Label>
                <Select value={form.type} onValueChange={(val) => setForm(prev => ({ ...prev, type: val }))}>
                  <SelectTrigger className="bg-[#0B0C10] border-white/10 text-gray-300 h-11" data-testid="source-type-select">
                    <SelectValue placeholder="Select type" />
                  </SelectTrigger>
                  <SelectContent className="bg-[#1A1D24] border-white/10">
                    {SOURCE_TYPES.map(t => (
                      <SelectItem key={t} value={t} className="text-gray-300">{t}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label className="text-sm text-gray-300">Description</Label>
                <Textarea
                  value={form.description}
                  onChange={(e) => setForm(prev => ({ ...prev, description: e.target.value }))}
                  placeholder="Brief description..."
                  rows={2}
                  className="bg-[#0B0C10] border-white/10 text-white resize-none"
                  data-testid="source-description-input"
                />
              </div>
              <div className="flex gap-3 justify-end">
                <Button variant="outline" onClick={resetForm} className="border-white/10 text-gray-300">Cancel</Button>
                <Button onClick={handleSave} data-testid="save-source-btn" className="bg-blue-600 hover:bg-blue-500 text-white">
                  {editing ? "Update" : "Add Source"}
                </Button>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {sources.length === 0 ? (
        <div className="text-center py-16">
          <Globe2 className="w-12 h-12 text-gray-600 mx-auto mb-3" />
          <p className="text-gray-400">No sources added yet</p>
        </div>
      ) : (
        <div className="space-y-3" data-testid="sources-list">
          {sources.map(source => (
            <div key={source.id} className="bg-[#12141A] border border-white/[0.05] rounded-xl p-5 card-hover" data-testid={`source-${source.id}`}>
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="text-sm font-semibold text-white">{source.name}</h3>
                    {source.type && (
                      <Badge variant="secondary" className="text-[10px] bg-blue-600/10 text-blue-400 border-0">{source.type}</Badge>
                    )}
                  </div>
                  {source.description && <p className="text-xs text-gray-400 mt-1">{source.description}</p>}
                  {source.url && (
                    <a href={source.url} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1 text-xs text-blue-400 hover:text-blue-300 mt-2">
                      <ExternalLink className="w-3 h-3" />
                      {source.url}
                    </a>
                  )}
                </div>
                <div className="flex items-center gap-1 shrink-0">
                  <button
                    onClick={() => startEdit(source)}
                    data-testid={`edit-source-${source.id}`}
                    className="p-2 text-gray-500 hover:text-blue-400 hover:bg-blue-500/10 rounded-lg transition-colors"
                  >
                    <Pencil className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => handleDelete(source.id)}
                    data-testid={`delete-source-${source.id}`}
                    className="p-2 text-gray-500 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
