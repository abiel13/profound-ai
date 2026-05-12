import React, { useState } from "react";
import { NavLink, useLocation } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import {
  LayoutDashboard, Search, Bookmark, Clock, FileText, Globe2,
  Building2, LogOut, Menu, X, ChevronRight, Briefcase, Trophy, Users, Mail, CalendarDays, ScrollText, Wand2, Layers,
  HeartHandshake, Handshake, SendHorizontal, DollarSign, Music2, Radar, Users2
} from "lucide-react";

const navItems = [
  { to: "/", icon: LayoutDashboard, label: "Dashboard" },
  { to: "/command-center", icon: CalendarDays, label: "Command Center" },
  { to: "/reports", icon: ScrollText, label: "Intelligence" },
  { to: "/search", icon: Search, label: "Search" },
  { to: "/wizard", icon: Wand2, label: "Wizard" },
  { to: "/batch", icon: Layers, label: "Batch Apply" },
  { to: "/campaigns", icon: HeartHandshake, label: "Campaigns" },
  { to: "/sponsors", icon: Handshake, label: "Sponsors" },
  { to: "/send-queue", icon: SendHorizontal, label: "Send Queue" },
  { to: "/donations", icon: DollarSign, label: "Donations" },
  { to: "/tiktok-campaigns", icon: Music2, label: "TikTok Campaigns" },
  // V12.3 Automation
  { to: "/grant-scanner", icon: Radar, label: "Grant Scanner" },
  { to: "/donor-finder", icon: Users2, label: "Donor Finder" },
  { to: "/email-drafts", icon: Mail, label: "Email Drafts" },
  { to: "/saved", icon: Bookmark, label: "Saved" },
  { to: "/workspace", icon: Briefcase, label: "Workspace" },
  { to: "/donors", icon: Users, label: "Donors" },
  { to: "/follow-ups", icon: Mail, label: "Follow-Ups" },
  { to: "/analytics", icon: Trophy, label: "Performance" },
  { to: "/proposals", icon: FileText, label: "Proposals" },
  { to: "/sources", icon: Globe2, label: "Sources" },
  { to: "/profile", icon: Building2, label: "Profile" },
];

export default function Layout({ children }) {
  const { user, logout } = useAuth();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const location = useLocation();

  return (
    <div className="flex h-screen overflow-hidden bg-[#0B0C10]" data-testid="app-layout">
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div className="fixed inset-0 bg-black/60 z-40 lg:hidden" onClick={() => setSidebarOpen(false)} />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed lg:static inset-y-0 left-0 z-50 w-64 bg-[#0B0C10] border-r border-white/[0.06] flex flex-col transition-transform duration-300 ${
          sidebarOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
        }`}
        data-testid="sidebar"
      >
        {/* Logo */}
        <div className="flex items-center gap-3 px-6 h-16 border-b border-white/[0.06]">
          <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center">
            <Globe2 className="w-4 h-4 text-white" />
          </div>
          <span className="text-lg font-semibold text-white tracking-tight" style={{ fontFamily: 'Outfit, sans-serif' }}>
            ProFund AI
          </span>
          <button className="ml-auto lg:hidden text-gray-400 hover:text-white" onClick={() => setSidebarOpen(false)}>
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 py-4 px-3 space-y-1 overflow-y-auto">
          {navItems.map(item => {
            const isActive = item.to === "/" ? location.pathname === "/" : location.pathname.startsWith(item.to);
            return (
              <NavLink
                key={item.to}
                to={item.to}
                onClick={() => setSidebarOpen(false)}
                data-testid={`nav-${item.label.toLowerCase()}`}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-150 ${
                  isActive
                    ? "bg-blue-600/10 text-white border-l-2 border-blue-500 ml-0"
                    : "text-gray-400 hover:text-white hover:bg-white/[0.04]"
                }`}
              >
                <item.icon className={`w-[18px] h-[18px] ${isActive ? "text-blue-500" : ""}`} />
                {item.label}
                {isActive && <ChevronRight className="w-3.5 h-3.5 ml-auto text-blue-500/60" />}
              </NavLink>
            );
          })}
        </nav>

        {/* User section */}
        <div className="px-4 py-4 border-t border-white/[0.06]">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-8 h-8 rounded-full bg-blue-600/20 flex items-center justify-center text-xs font-medium text-blue-400">
              {user?.name?.[0] || "A"}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-200 truncate">{user?.name || "Admin"}</p>
              <p className="text-xs text-gray-500 truncate">{user?.email}</p>
            </div>
          </div>
          <button
            onClick={logout}
            data-testid="logout-button"
            className="flex items-center gap-2 w-full px-3 py-2 text-sm text-gray-400 hover:text-red-400 hover:bg-red-500/[0.06] rounded-lg transition-colors"
          >
            <LogOut className="w-4 h-4" />
            Sign Out
          </button>
        </div>
      </aside>

      {/* Main content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top bar */}
        <header className="h-16 glass-surface flex items-center px-4 lg:px-8 border-b border-white/[0.06] shrink-0" data-testid="top-header">
          <button
            className="lg:hidden mr-4 text-gray-400 hover:text-white"
            onClick={() => setSidebarOpen(true)}
            data-testid="mobile-menu-button"
          >
            <Menu className="w-5 h-5" />
          </button>
          <div className="flex-1" />
          <div className="flex items-center gap-4">
            <span className="text-xs text-gray-500 hidden sm:block">Private Dashboard</span>
            <div className="w-px h-5 bg-white/10 hidden sm:block" />
            <span className="text-xs text-gray-400 hidden sm:block">{user?.email}</span>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto p-4 lg:p-8" data-testid="main-content">
          {children}
        </main>
      </div>
    </div>
  );
}
