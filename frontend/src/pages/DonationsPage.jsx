import React, { useState, useEffect, useCallback } from "react";
import axios from "axios";
import { useAuth } from "@/context/AuthContext";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "@/components/ui/dialog";
import {
  DollarSign, Plus, Trash2, Link2, Copy, RefreshCw, TrendingUp, Music2,
} from "lucide-react";

import { API } from "../config";
import { useNavigate } from "react-router-dom";

function fmt(n) { return `$${(n || 0).toLocaleString(undefined, { maximumFractionDigits: 2 })}`; }

export default function DonationsPage() {
  const { authHeaders } = useAuth();
  const navigate = useNavigate();
  const [donations, setDonations] = useState([]);
  const [links, setLinks] = useState([]);
  const [summary, setSummary] = useState(null);
  const [campaigns, setCampaigns] = useState([]);
  const [sponsors, setSponsors] = useState([]);
  const [loading, setLoading] = useState(true);

  // Donation form
  const [showDForm, setShowDForm] = useState(false);
  const [dForm, setDForm] = useState({
    amount: "", currency: "USD", donor_name: "", donor_email: "",
    payment_method: "", payment_link_id: "", campaign_id: "", sponsor_offer_id: "",
    source: "", note: "",
  });

  // Payment link form
  const [showLForm, setShowLForm] = useState(false);
  const [lForm, setLForm] = useState({
    label: "", provider: "generic", url: "", purpose: "donation",
    utm_source: "", utm_medium: "", utm_campaign: "",
  });

  // Default payment links
  const [defaults, setDefaults] = useState({ small_donor: null, sponsor: null });
  const [showDefaultsForm, setShowDefaultsForm] = useState(false);
  const [defaultsForm, setDefaultsForm] = useState({ small_donor_link: "", sponsor_link: "" });

  const fetchAll = useCallback(async () => {
    try {
      const [d, l, sum, c, sp, def] = await Promise.all([
        axios.get(`${API}/v11/donations`, { headers: authHeaders() }),
        axios.get(`${API}/v11/payment-links`, { headers: authHeaders() }),
        axios.get(`${API}/v11/donations/summary`, { headers: authHeaders() }),
        axios.get(`${API}/v11/campaigns`, { headers: authHeaders() }),
        axios.get(`${API}/v11/sponsors`, { headers: authHeaders() }),
        axios.get(`${API}/v11/payment-links/defaults`, { headers: authHeaders() }),
      ]);
      setDonations(d.data || []);
      setLinks(l.data || []);
      setSummary(sum.data || null);
      setCampaigns(c.data || []);
      setSponsors(sp.data || []);
      setDefaults(def.data || { small_donor: null, sponsor: null });
      setDefaultsForm({
        small_donor_link: def.data?.small_donor?.url || "",
        sponsor_link: def.data?.sponsor?.url || "",
      });
    } catch { toast.error("Failed to load donations"); }
    finally { setLoading(false); }
  }, [authHeaders]);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  const addDonation = async () => {
    if (!dForm.amount) return toast.error("Enter amount");
    try {
      await axios.post(`${API}/v11/donations`, { ...dForm, amount: Number(dForm.amount) }, { headers: authHeaders() });
      toast.success("Donation logged");
      setShowDForm(false);
      setDForm({ amount: "", currency: "USD", donor_name: "", donor_email: "", payment_method: "", payment_link_id: "", campaign_id: "", sponsor_offer_id: "", source: "", note: "" });
      fetchAll();
    } catch { toast.error("Failed to log donation"); }
  };

  const delDonation = async (id) => {
    if (!window.confirm("Delete this donation?")) return;
    await axios.delete(`${API}/v11/donations/${id}`, { headers: authHeaders() });
    fetchAll();
  };

  const addLink = async () => {
    if (!lForm.label || !lForm.url) return toast.error("Label and URL required");
    try {
      await axios.post(`${API}/v11/payment-links`, lForm, { headers: authHeaders() });
      toast.success("Payment link created");
      setShowLForm(false);
      setLForm({ label: "", provider: "generic", url: "", purpose: "donation", utm_source: "", utm_medium: "", utm_campaign: "" });
      fetchAll();
    } catch { toast.error("Failed to create link"); }
  };

  const delLink = async (id) => {
    if (!window.confirm("Delete this payment link?")) return;
    await axios.delete(`${API}/v11/payment-links/${id}`, { headers: authHeaders() });
    fetchAll();
  };

  const saveDefaults = async () => {
    if (!defaultsForm.small_donor_link && !defaultsForm.sponsor_link) {
      toast.error("Enter at least one link");
      return;
    }
    try {
      await axios.post(`${API}/v11/payment-links/set`, defaultsForm, { headers: authHeaders() });
      toast.success("Default payment links saved");
      setShowDefaultsForm(false);
      fetchAll();
    } catch {
      toast.error("Failed to save defaults");
    }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6" data-testid="donations-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-semibold text-white tracking-tight flex items-center gap-3">
            <DollarSign className="w-7 h-7 text-emerald-400" />
            Donations
          </h1>
          <p className="text-sm text-gray-400 mt-1">Track incoming donations and manage generic payment links.</p>
        </div>
        <Button variant="outline" size="sm" onClick={fetchAll} data-testid="refresh-donations-btn">
          <RefreshCw className="w-4 h-4 mr-2" />Refresh
        </Button>
      </div>

      {/* TikTok campaign shortcut */}
      <div className="bg-gradient-to-br from-pink-600/10 to-fuchsia-600/5 border border-pink-500/20 rounded-xl p-4 flex items-center justify-between gap-4" data-testid="donations-tiktok-shortcut">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-pink-600/20 flex items-center justify-center">
            <Music2 className="w-4 h-4 text-pink-400" />
          </div>
          <div>
            <p className="text-sm font-medium text-white" style={{ fontFamily: "Outfit" }}>Boost a campaign on TikTok</p>
            <p className="text-xs text-gray-400">Generate scripts, captions, hashtags, and a share-ready WhatsApp message.</p>
          </div>
        </div>
        <Button
          onClick={() => {
            const link = (defaults?.small_donor?.url || "");
            const params = new URLSearchParams();
            if (link) params.set("link", link);
            navigate(`/tiktok-campaigns${params.toString() ? "?" + params.toString() : ""}`);
          }}
          data-testid="create-tiktok-campaign-btn"
          className="bg-pink-600 hover:bg-pink-500 text-white text-sm"
        >
          <Music2 className="w-4 h-4 mr-2" />Create TikTok Campaign
        </Button>
      </div>

      {/* Stat cards */}
      <div className="grid md:grid-cols-3 gap-4">
        <StatCard label="Total Raised" value={fmt(summary?.totals?.total)} icon={TrendingUp} color="emerald" />
        <StatCard label="Donations Count" value={summary?.totals?.c ?? 0} icon={DollarSign} color="blue" />
        <StatCard label="Active Payment Links" value={links.filter(l => l.active).length} icon={Link2} color="purple" />
      </div>

      {/* Default live-payment links (auto-attached to new campaigns/sponsors) */}
      <div className="glass-surface border border-white/[0.06] rounded-xl p-5" data-testid="defaults-card">
        <div className="flex items-center justify-between mb-3">
          <div>
            <h2 className="text-sm font-semibold text-white">Default Payment Links</h2>
            <p className="text-xs text-gray-400 mt-0.5">
              Auto-attached to every newly generated campaign + sponsor offer.
            </p>
          </div>
          <Button size="sm" variant="outline" onClick={() => setShowDefaultsForm(true)} data-testid="edit-defaults-btn">
            Edit
          </Button>
        </div>
        <div className="grid md:grid-cols-2 gap-3">
          <div className="bg-white/[0.02] border border-white/[0.04] rounded-md p-3">
            <div className="text-[11px] uppercase tracking-wide text-gray-500">Small Donor ($5–$50)</div>
            <div className="text-sm text-white mt-1 truncate" data-testid="default-small-donor-url">
              {defaults.small_donor ? (
                <span className="text-blue-300 break-all">{defaults.small_donor.tracking_url || defaults.small_donor.url}</span>
              ) : (
                <span className="text-gray-500">Not set</span>
              )}
            </div>
          </div>
          <div className="bg-white/[0.02] border border-white/[0.04] rounded-md p-3">
            <div className="text-[11px] uppercase tracking-wide text-gray-500">Sponsor ($100–$1000)</div>
            <div className="text-sm text-white mt-1 truncate" data-testid="default-sponsor-url">
              {defaults.sponsor ? (
                <span className="text-blue-300 break-all">{defaults.sponsor.tracking_url || defaults.sponsor.url}</span>
              ) : (
                <span className="text-gray-500">Not set</span>
              )}
            </div>
          </div>
        </div>
      </div>


      {/* Two column: Donations list + Payment links */}
      <div className="grid md:grid-cols-5 gap-6">
        {/* Donations */}
        <div className="md:col-span-3 space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-white">Recent Donations</h2>
            <Button size="sm" onClick={() => setShowDForm(true)} data-testid="add-donation-btn">
              <Plus className="w-4 h-4 mr-1" />Log Donation
            </Button>
          </div>

          {loading ? <div className="text-gray-500 text-sm">Loading…</div> :
           donations.length === 0 ? (
            <div className="text-gray-500 text-sm py-10 text-center glass-surface border border-white/[0.06] rounded-xl" data-testid="donations-empty">
              No donations logged yet.
            </div>
          ) : (
            <div className="space-y-2">
              {donations.map((d) => (
                <div key={d.id} className="glass-surface border border-white/[0.06] rounded-lg p-3 flex items-center gap-3" data-testid={`donation-${d.id}`}>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-baseline gap-2">
                      <span className="text-emerald-400 font-semibold">{fmt(d.amount)} {d.currency}</span>
                      <span className="text-sm text-white truncate">{d.donor_name || "(anonymous)"}</span>
                    </div>
                    <div className="text-xs text-gray-500 mt-0.5 flex gap-2 flex-wrap">
                      {d.payment_method && <span>{d.payment_method}</span>}
                      {d.source && <span>· {d.source}</span>}
                      {d.received_at && <span>· {d.received_at.slice(0, 10)}</span>}
                    </div>
                    {d.note && <p className="text-xs text-gray-400 mt-1 truncate">{d.note}</p>}
                  </div>
                  <Button size="sm" variant="ghost" onClick={() => delDonation(d.id)} data-testid={`delete-donation-${d.id}`}>
                    <Trash2 className="w-4 h-4 text-red-400" />
                  </Button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Payment Links */}
        <div className="md:col-span-2 space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-white">Payment Links</h2>
            <Button size="sm" onClick={() => setShowLForm(true)} data-testid="add-link-btn">
              <Plus className="w-4 h-4 mr-1" />New Link
            </Button>
          </div>

          {links.length === 0 ? (
            <div className="text-gray-500 text-sm py-10 text-center glass-surface border border-white/[0.06] rounded-xl" data-testid="links-empty">
              No payment links yet.
            </div>
          ) : (
            <div className="space-y-2">
              {links.map((l) => (
                <div key={l.id} className="glass-surface border border-white/[0.06] rounded-lg p-3" data-testid={`link-${l.id}`}>
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <Badge className="bg-blue-500/10 text-blue-400 text-[10px]">{l.provider}</Badge>
                        {l.active ? <Badge className="bg-emerald-500/10 text-emerald-400 text-[10px]">ACTIVE</Badge> : <Badge className="bg-gray-500/10 text-gray-400 text-[10px]">OFF</Badge>}
                      </div>
                      <div className="text-sm text-white mt-1 font-medium truncate">{l.label}</div>
                      <div className="text-xs text-gray-500 truncate">{l.tracking_url || l.url}</div>
                    </div>
                    <div className="flex items-center gap-1 shrink-0">
                      <Button size="sm" variant="ghost" onClick={() => { navigator.clipboard.writeText(l.tracking_url || l.url); toast.success("Copied"); }} data-testid={`copy-link-${l.id}`}>
                        <Copy className="w-3.5 h-3.5" />
                      </Button>
                      <Button size="sm" variant="ghost" onClick={() => delLink(l.id)} data-testid={`delete-link-${l.id}`}>
                        <Trash2 className="w-3.5 h-3.5 text-red-400" />
                      </Button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* By-campaign summary */}
      {summary?.by_campaign?.length > 0 && (
        <div className="glass-surface border border-white/[0.06] rounded-xl p-5">
          <h2 className="text-sm font-semibold text-white mb-3">Raised by Campaign</h2>
          <div className="space-y-2">
            {summary.by_campaign.slice(0, 10).map((c) => (
              <div key={c.id} className="flex items-center justify-between text-sm" data-testid={`by-campaign-${c.id}`}>
                <span className="text-gray-300 truncate mr-3">{c.title || "(untitled)"}</span>
                <span className="text-emerald-400 font-medium">{fmt(c.total)} <span className="text-gray-500 text-xs">· {c.count} donors</span></span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Default links dialog */}
      <Dialog open={showDefaultsForm} onOpenChange={setShowDefaultsForm}>
        <DialogContent className="max-w-lg">
          <DialogHeader><DialogTitle>Default Payment Links</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <p className="text-xs text-gray-400">
              Paste your real payment URLs (bank transfer, PayPal.me, M-Pesa, etc.).
              New campaigns will use the small-donor link; new sponsor offers will use the sponsor link.
              UTM tracking is auto-appended.
            </p>
            <div>
              <Label className="text-xs">Small Donor Link ($5–$50)</Label>
              <Input
                placeholder="https://paypal.me/proyouth or bank URL"
                value={defaultsForm.small_donor_link}
                onChange={(e) => setDefaultsForm({ ...defaultsForm, small_donor_link: e.target.value })}
                data-testid="default-small-donor-input"
              />
            </div>
            <div>
              <Label className="text-xs">Sponsor Link ($100–$1000)</Label>
              <Input
                placeholder="https://paypal.me/proyouth-sponsor or bank URL"
                value={defaultsForm.sponsor_link}
                onChange={(e) => setDefaultsForm({ ...defaultsForm, sponsor_link: e.target.value })}
                data-testid="default-sponsor-input"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowDefaultsForm(false)}>Cancel</Button>
            <Button onClick={saveDefaults} data-testid="save-defaults-btn">Save</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Donation dialog */}
      <Dialog open={showDForm} onOpenChange={setShowDForm}>
        <DialogContent className="max-w-lg">
          <DialogHeader><DialogTitle>Log a Donation</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <div className="grid grid-cols-3 gap-2">
              <div className="col-span-2">
                <Label className="text-xs">Amount</Label>
                <Input type="number" value={dForm.amount} onChange={(e) => setDForm({ ...dForm, amount: e.target.value })} data-testid="donation-amount-input" />
              </div>
              <div>
                <Label className="text-xs">Currency</Label>
                <Input value={dForm.currency} onChange={(e) => setDForm({ ...dForm, currency: e.target.value })} />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <Label className="text-xs">Donor Name</Label>
                <Input value={dForm.donor_name} onChange={(e) => setDForm({ ...dForm, donor_name: e.target.value })} />
              </div>
              <div>
                <Label className="text-xs">Donor Email</Label>
                <Input value={dForm.donor_email} onChange={(e) => setDForm({ ...dForm, donor_email: e.target.value })} />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <Label className="text-xs">Payment Method</Label>
                <Input placeholder="e.g. bank, paypal, cash" value={dForm.payment_method} onChange={(e) => setDForm({ ...dForm, payment_method: e.target.value })} />
              </div>
              <div>
                <Label className="text-xs">Source</Label>
                <Input placeholder="e.g. whatsapp, facebook" value={dForm.source} onChange={(e) => setDForm({ ...dForm, source: e.target.value })} />
              </div>
            </div>
            <div>
              <Label className="text-xs">Link to Campaign (optional)</Label>
              <Select value={dForm.campaign_id} onValueChange={(v) => setDForm({ ...dForm, campaign_id: v })}>
                <SelectTrigger><SelectValue placeholder="None" /></SelectTrigger>
                <SelectContent>
                  {campaigns.map((c) => <SelectItem key={c.id} value={c.id}>{c.title || c.theme}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label className="text-xs">Link to Sponsor (optional)</Label>
              <Select value={dForm.sponsor_offer_id} onValueChange={(v) => setDForm({ ...dForm, sponsor_offer_id: v })}>
                <SelectTrigger><SelectValue placeholder="None" /></SelectTrigger>
                <SelectContent>
                  {sponsors.map((s) => <SelectItem key={s.id} value={s.id}>{s.sponsor_name}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label className="text-xs">Note</Label>
              <Textarea rows={2} value={dForm.note} onChange={(e) => setDForm({ ...dForm, note: e.target.value })} />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowDForm(false)}>Cancel</Button>
            <Button onClick={addDonation} data-testid="save-donation-btn">Save</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Payment link dialog */}
      <Dialog open={showLForm} onOpenChange={setShowLForm}>
        <DialogContent className="max-w-lg">
          <DialogHeader><DialogTitle>New Payment Link</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <div>
              <Label className="text-xs">Label</Label>
              <Input placeholder="e.g. Bank Namibia" value={lForm.label} onChange={(e) => setLForm({ ...lForm, label: e.target.value })} data-testid="link-label-input" />
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <Label className="text-xs">Provider</Label>
                <Input placeholder="bank / paypal / mpesa" value={lForm.provider} onChange={(e) => setLForm({ ...lForm, provider: e.target.value })} />
              </div>
              <div>
                <Label className="text-xs">Purpose</Label>
                <Select value={lForm.purpose} onValueChange={(v) => setLForm({ ...lForm, purpose: v })}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="donation">Donation (small donor)</SelectItem>
                    <SelectItem value="sponsor">Sponsor</SelectItem>
                    <SelectItem value="grant">Grant</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div>
              <Label className="text-xs">URL</Label>
              <Input placeholder="https://..." value={lForm.url} onChange={(e) => setLForm({ ...lForm, url: e.target.value })} data-testid="link-url-input" />
            </div>
            <div className="grid grid-cols-3 gap-2">
              <div>
                <Label className="text-xs">utm_source</Label>
                <Input placeholder="whatsapp" value={lForm.utm_source} onChange={(e) => setLForm({ ...lForm, utm_source: e.target.value })} />
              </div>
              <div>
                <Label className="text-xs">utm_medium</Label>
                <Input placeholder="broadcast" value={lForm.utm_medium} onChange={(e) => setLForm({ ...lForm, utm_medium: e.target.value })} />
              </div>
              <div>
                <Label className="text-xs">utm_campaign</Label>
                <Input placeholder="streetkids" value={lForm.utm_campaign} onChange={(e) => setLForm({ ...lForm, utm_campaign: e.target.value })} />
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowLForm(false)}>Cancel</Button>
            <Button onClick={addLink} data-testid="save-link-btn">Save</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function StatCard({ label, value, icon: Icon, color }) {
  const colorMap = {
    emerald: "text-emerald-400 bg-emerald-500/10",
    blue: "text-blue-400 bg-blue-500/10",
    purple: "text-purple-400 bg-purple-500/10",
  };
  return (
    <div className="glass-surface border border-white/[0.06] rounded-xl p-5 flex items-center gap-4">
      <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${colorMap[color]}`}>
        <Icon className="w-5 h-5" />
      </div>
      <div>
        <div className="text-2xl font-semibold text-white">{value}</div>
        <div className="text-xs text-gray-400">{label}</div>
      </div>
    </div>
  );
}
