import React from 'react';

/**
 * Mobile-first device shell.
 * Centers on desktop inside a premium mobile frame (~390-430px)
 * and fills 100% on mobile devices with appropriate safe area padding.
 */
export default function AppShell({
  children,
  backendStatus = 'connected',
  viewMode = 'VERIFY',
  onToggleViewMode,
  onResetToHome,
}) {
  return (
    <div className="mobile-canvas">
      <div className="mobile-frame" id="mobile-app-root">
        {/* Mobile Header Bar */}
        <header className="mobile-topbar">
          <div className="topbar-left" onClick={onResetToHome} style={{ cursor: 'pointer' }}>
            <div className="brand-badge">
              <span className="brand-logo-icon">📦</span>
              <h1 className="brand-title">PackCheck</h1>
            </div>
            <span className="brand-tag">SIH26034</span>
          </div>

          <div className="topbar-right">
            {/* Live API Health Status indicator */}
            <div
              className={`api-status-pill status-${backendStatus}`}
              title={`API Backend: ${backendStatus}`}
            >
              <span className="status-dot" />
              <span className="status-label">
                {backendStatus === 'connected'
                  ? 'Live'
                  : backendStatus === 'checking'
                  ? 'Checking'
                  : 'Offline'}
              </span>
            </div>

            {/* Dev Mode toggle to access preserved /api/extract test tool */}
            <button
              type="button"
              className="dev-mode-btn"
              onClick={onToggleViewMode}
              title={viewMode === 'VERIFY' ? 'Switch to Raw Extraction Dev Tool' : 'Switch to Verification App'}
              id="btn-toggle-dev-mode"
            >
              {viewMode === 'VERIFY' ? '🛠️ Dev' : '✓ Verify'}
            </button>
          </div>
        </header>

        {/* Dynamic Mobile View Body */}
        <main className="mobile-scrollable-body">{children}</main>
      </div>
    </div>
  );
}
