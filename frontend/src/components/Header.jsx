/**
 * Application Header with live API ping, role selector, and role-based navigation.
 */
export default function Header({
  backendStatus,
  activeRole,
  currentView,
  onNavigate,
  onOpenRoleSwitcher,
  reviewQueueCount = 0,
}) {
  return (
    <header className="app-header" id="app-header">
      <div className="header-left">
        <div className="brand-group" onClick={() => onNavigate('home')} style={{ cursor: 'pointer' }}>
          <h1 className="app-title" id="project-title">PackCheck</h1>
          <div className="header-badge">
            <span className="badge-dot" />
            <span>SIH26034</span>
          </div>
        </div>

        {/* Role-specific Navigation Tabs */}
        <nav className="header-nav">
          {activeRole === 'inspector' && (
            <>
              <button
                className={`nav-tab ${currentView === 'new-inspection' ? 'active' : ''}`}
                onClick={() => onNavigate('new-inspection')}
                id="tab-new-inspection"
              >
                📸 New Inspection
              </button>
              <button
                className={`nav-tab ${currentView === 'history' ? 'active' : ''}`}
                onClick={() => onNavigate('history')}
                id="tab-history"
              >
                📁 Inspection History
              </button>
            </>
          )}

          {activeRole === 'reviewer' && (
            <>
              <button
                className={`nav-tab ${currentView === 'review-queue' ? 'active' : ''}`}
                onClick={() => onNavigate('review-queue')}
                id="tab-review-queue"
              >
                🔍 Review Queue
                {reviewQueueCount > 0 && (
                  <span className="badge-count" id="review-queue-badge">
                    {reviewQueueCount}
                  </span>
                )}
              </button>
              <button
                className={`nav-tab ${currentView === 'history' ? 'active' : ''}`}
                onClick={() => onNavigate('history')}
                id="tab-history"
              >
                📁 Inspection History
              </button>
            </>
          )}
        </nav>
      </div>

      <div className="header-right">
        {/* Role Pill & Switcher */}
        <div className="role-indicator-box">
          <span className="role-prefix text-muted">Role:</span>
          <span className={`role-badge role-${activeRole}`} id="active-role-badge">
            {activeRole === 'inspector' ? '👤 Inspector' : '🕵️ Reviewer'}
          </span>
          <button
            className="btn btn-xs btn-outline btn-switch-role"
            onClick={onOpenRoleSwitcher}
            id="btn-switch-role"
            title="Switch user role (simulation)"
          >
            Switch Role
          </button>
        </div>

        {/* Live Backend Connection Ping */}
        <div className="live-ping" id="backend-ping">
          <span
            className={`ping-dot ${
              backendStatus === 'connected'
                ? 'ping-ok'
                : backendStatus === 'checking'
                ? 'ping-checking'
                : 'ping-offline'
            }`}
          />
          <span className="ping-label">
            {backendStatus === 'connected'
              ? 'API Live'
              : backendStatus === 'checking'
              ? 'Checking...'
              : 'API Offline'}
          </span>
        </div>
      </div>
    </header>
  );
}
