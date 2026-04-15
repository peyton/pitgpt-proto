import { useMemo, useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { useApp } from "../lib/AppContext";
import { LogoMark } from "./Logo";

const navItems = [
  {
    to: "/",
    label: "New Experiment",
    icon: (
      <svg viewBox="0 0 20 20" fill="none">
        <circle cx="10" cy="10" r="7" stroke="currentColor" strokeWidth="1.5" />
        <path d="M10 7v6M7 10h6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      </svg>
    ),
  },
  {
    to: "/protocol",
    label: "Protocol Review",
    icon: (
      <svg viewBox="0 0 20 20" fill="none">
        <path d="M4 4h12v12H4z" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M7 8h6M7 11h4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      </svg>
    ),
  },
  {
    to: "/trial",
    label: "Active Trial",
    icon: (
      <svg viewBox="0 0 20 20" fill="none">
        <path d="M3 10l5 5L17 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    ),
  },
  {
    to: "/results",
    label: "Results",
    icon: (
      <svg viewBox="0 0 20 20" fill="none">
        <path d="M3 17V10M8 17V6M13 17V8M18 17V3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      </svg>
    ),
  },
];

export function Layout() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const { state, ingestionResult, markExperimentRead } = useApp();
  const conversations = useMemo(
    () =>
      [...state.experiments].sort(
        (a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime(),
      ),
    [state.experiments],
  );
  const primaryNav = navItems.slice(0, 1);
  const hasProtocol = Boolean(ingestionResult);
  const hasTrial = Boolean(state.trial);
  const hasResults = state.completedResults.length > 0;
  const workflowNav = navItems.slice(1).filter((item) => {
    if (item.to === "/protocol" && !hasProtocol) return false;
    if (item.to === "/trial" && !hasTrial) return false;
    if (item.to === "/results" && !hasResults) return false;
    return true;
  });

  return (
    <>
      <div className="mobile-header">
        <button className="hamburger" onClick={() => setSidebarOpen(!sidebarOpen)} aria-label="Menu">
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
            <path d="M3 5h14M3 10h14M3 15h14" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
          </svg>
        </button>
        <div className="sidebar-logo">
          <LogoMark size={26} />
          <span style={{ fontSize: 18, fontWeight: 700, letterSpacing: 0 }}>
            Pit<em style={{ fontStyle: "normal", color: "var(--pink-500)" }}>GPT</em>
          </span>
        </div>
      </div>
      <div
        className={`mobile-overlay${sidebarOpen ? " open" : ""}`}
        onClick={() => setSidebarOpen(false)}
      />
      <div className="app">
        <aside className={`sidebar${sidebarOpen ? " open" : ""}`}>
          <div className="sidebar-header">
            <div className="sidebar-logo">
              <LogoMark size={30} />
              <span>
                Pit<em>GPT</em>
              </span>
            </div>
          </div>
          <nav className="sidebar-nav">
            {primaryNav.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === "/"}
                className={({ isActive }) => `nav-item${isActive ? " active" : ""}`}
                onClick={() => setSidebarOpen(false)}
              >
                {item.icon}
                {item.label}
              </NavLink>
            ))}
            {conversations.length > 0 && (
              <div className="conversation-nav" aria-label="Experiment conversations">
                <div className="conversation-nav-label">Experiments</div>
                {conversations.map((experiment) => (
                  <NavLink
                    key={experiment.id}
                    to={`/experiments/${experiment.id}`}
                    className={({ isActive }) => `conversation-item${isActive ? " active" : ""}`}
                    onClick={() => {
                      markExperimentRead(experiment.id);
                      setSidebarOpen(false);
                    }}
                  >
                    <span className={`conversation-status-dot status-${experiment.status}`} />
                    <span className="conversation-title">{experiment.title}</span>
                    {experiment.unread && <span className="conversation-unread-dot" aria-label="Unread updates" />}
                  </NavLink>
                ))}
              </div>
            )}
            <div className="nav-divider" />
            {workflowNav.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === "/"}
                className={({ isActive }) => `nav-item${isActive ? " active" : ""}`}
                onClick={() => setSidebarOpen(false)}
              >
                {item.icon}
                {item.label}
              </NavLink>
            ))}
            <NavLink
              to="/settings"
              className={({ isActive }) => `nav-item${isActive ? " active" : ""}`}
              onClick={() => setSidebarOpen(false)}
            >
              <svg viewBox="0 0 20 20" fill="none">
                <circle cx="10" cy="10" r="3" stroke="currentColor" strokeWidth="1.5" />
                <path
                  d="M10 2v3M10 15v3M2 10h3M15 10h3M4.2 4.2l2.1 2.1M13.7 13.7l2.1 2.1M15.8 4.2l-2.1 2.1M6.3 13.7l-2.1 2.1"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                />
              </svg>
              Settings
            </NavLink>
          </nav>
          <div className="sidebar-footer">v0.1.0 · Private</div>
        </aside>
        <main className="main">
          <Outlet />
        </main>
      </div>
    </>
  );
}
