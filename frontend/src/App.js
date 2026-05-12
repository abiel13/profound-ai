import React from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "@/context/AuthContext";
import { Toaster } from "@/components/ui/sonner";
import LoginPage from "@/pages/LoginPage";
import DashboardPage from "@/pages/DashboardPage";
import SearchPage from "@/pages/SearchPage";
import OpportunityDetailPage from "@/pages/OpportunityDetailPage";
import SavedPage from "@/pages/SavedPage";
import ProfilePage from "@/pages/ProfilePage";
import ProposalPage from "@/pages/ProposalPage";
import SourcesPage from "@/pages/SourcesPage";
import DeadlinesPage from "@/pages/DeadlinesPage";
import WorkspacePage from "@/pages/WorkspacePage";
import AnalyticsPage from "@/pages/AnalyticsPage";
import DonorsPage from "@/pages/DonorsPage";
import FollowUpsPage from "@/pages/FollowUpsPage";
import CommandCenterPage from "@/pages/CommandCenterPage";
import ReportsPage from "@/pages/ReportsPage";
import WizardPage from "@/pages/WizardPage";
import BatchPage from "@/pages/BatchPage";
import CampaignsPage from "@/pages/CampaignsPage";
import SponsorsPage from "@/pages/SponsorsPage";
import SendQueuePage from "@/pages/SendQueuePage";
import DonationsPage from "@/pages/DonationsPage";
import TikTokCampaignsPage from "@/pages/TikTokCampaignsPage";
import GrantScannerPage from "@/pages/GrantScannerPage";
import EmailDraftsPage from "@/pages/EmailDraftsPage";
import DonorFinderPage from "@/pages/DonorFinderPage";
import Layout from "@/components/Layout";

function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();
  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-[#0B0C10]">
        <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }
  if (!user) return <Navigate to="/login" replace />;
  return <Layout>{children}</Layout>;
}

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
          <Route path="/search" element={<ProtectedRoute><SearchPage /></ProtectedRoute>} />
          <Route path="/opportunity/:id" element={<ProtectedRoute><OpportunityDetailPage /></ProtectedRoute>} />
          <Route path="/saved" element={<ProtectedRoute><SavedPage /></ProtectedRoute>} />
          <Route path="/workspace" element={<ProtectedRoute><WorkspacePage /></ProtectedRoute>} />
          <Route path="/analytics" element={<ProtectedRoute><AnalyticsPage /></ProtectedRoute>} />
          <Route path="/donors" element={<ProtectedRoute><DonorsPage /></ProtectedRoute>} />
          <Route path="/follow-ups" element={<ProtectedRoute><FollowUpsPage /></ProtectedRoute>} />
          <Route path="/command-center" element={<ProtectedRoute><CommandCenterPage /></ProtectedRoute>} />
          <Route path="/reports" element={<ProtectedRoute><ReportsPage /></ProtectedRoute>} />
          <Route path="/wizard" element={<ProtectedRoute><WizardPage /></ProtectedRoute>} />
          <Route path="/batch" element={<ProtectedRoute><BatchPage /></ProtectedRoute>} />
          <Route path="/campaigns" element={<ProtectedRoute><CampaignsPage /></ProtectedRoute>} />
          <Route path="/sponsors" element={<ProtectedRoute><SponsorsPage /></ProtectedRoute>} />
          <Route path="/send-queue" element={<ProtectedRoute><SendQueuePage /></ProtectedRoute>} />
          <Route path="/donations" element={<ProtectedRoute><DonationsPage /></ProtectedRoute>} />
          <Route path="/tiktok-campaigns" element={<ProtectedRoute><TikTokCampaignsPage /></ProtectedRoute>} />
          <Route path="/grant-scanner" element={<ProtectedRoute><GrantScannerPage /></ProtectedRoute>} />
          <Route path="/email-drafts" element={<ProtectedRoute><EmailDraftsPage /></ProtectedRoute>} />
          <Route path="/donor-finder" element={<ProtectedRoute><DonorFinderPage /></ProtectedRoute>} />
          <Route path="/profile" element={<ProtectedRoute><ProfilePage /></ProtectedRoute>} />
          <Route path="/proposals" element={<ProtectedRoute><ProposalPage /></ProtectedRoute>} />
          <Route path="/proposals/:id" element={<ProtectedRoute><ProposalPage /></ProtectedRoute>} />
          <Route path="/sources" element={<ProtectedRoute><SourcesPage /></ProtectedRoute>} />
          <Route path="/deadlines" element={<ProtectedRoute><DeadlinesPage /></ProtectedRoute>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
      <Toaster position="top-right" richColors />
    </AuthProvider>
  );
}

export default App;
