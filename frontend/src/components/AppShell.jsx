import React from 'react';

/**
 * Responsive device shell supporting both PC Workstation and Mobile views.
 * - In PC mode: Expands up to full desktop width (1440px) with workstation header.
 * - In Mobile mode: Centers inside a mobile device frame (~390-430px) with mobile topbar.
 * - Provides mode switcher: [ Auto (PC/Mob) ] [ 💻 PC ] [ 📱 Mobile ]
 */
export default function AppShell({
  children,
  backendStatus = 'connected',
  viewMode = 'VERIFY',
  onToggleViewMode,
  onResetToHome,
  modePreference = 'AUTO',
  effectiveMode = 'PC',
  onSetModePreference,
}) {
  return (
    <div
      className={`app-canvas mobile-canvas mode-${effectiveMode.toLowerCase()}`}
      data-device-mode={effectiveMode.toLowerCase()}
      data-mode-pref={modePreference.toLowerCase()}
    >
      <div
        className={`app-frame mobile-frame mode-${effectiveMode.toLowerCase()}`}
        id="app-root"
      >
        {/* Responsive Header Bar */}
        <header className="app-topbar mobile-topbar">
          <div className="topbar-left" onClick={onResetToHome} style={{ cursor: 'pointer' }}>
            <div className="brand-badge">
              <span className="brand-logo-icon" aria-hidden="true">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" />
                  <polyline points="3.27 6.96 12 12.01 20.73 6.96" />
                  <line x1="12" y1="22.08" x2="12" y2="12" />
                </svg>
              </span>
              <div className="brand-text-col">
                <h1 className="brand-title">PackCheck</h1>
                {effectiveMode === 'PC' && (
                  <span className="brand-sub-title">Legal Metrology Compliance</span>
                )}
              </div>
            </div>
            <span className="brand-tag">SIH26034</span>
          </div>

          {/* Mode Switcher Control: AUTO | PC | MOBILE */}
          <div className="topbar-center">
            <div
              className="mode-switcher"
              role="radiogroup"
              aria-label="Display layout mode"
              id="mode-switcher"
            >
              <button
                type="button"
                className={`mode-btn ${modePreference === 'AUTO' ? 'active' : ''}`}
                onClick={() => onSetModePreference && onSetModePreference('AUTO')}
                title={`Automatic layout based on screen width (currently ${
                  effectiveMode === 'PC' ? 'Desktop' : 'Mobile'
                })`}
                id="mode-btn-auto"
                aria-checked={modePreference === 'AUTO'}
                role="radio"
              >
                <span>Auto</span>
                <span className="mode-sub-pill">
                  {effectiveMode === 'PC' ? 'PC' : 'Mob'}
                </span>
              </button>
              <button
                type="button"
                className={`mode-btn ${modePreference === 'PC' ? 'active' : ''}`}
                onClick={() => onSetModePreference && onSetModePreference('PC')}
                title="Force full-width PC workstation layout"
                id="mode-btn-pc"
                aria-checked={modePreference === 'PC'}
                role="radio"
              >
                <svg className="mode-icon-svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <rect x="2" y="3" width="20" height="14" rx="2" ry="2" />
                  <line x1="8" y1="21" x2="16" y2="21" />
                  <line x1="12" y1="17" x2="12" y2="21" />
                </svg>
                <span className="mode-btn-label">PC</span>
              </button>
              <button
                type="button"
                className={`mode-btn ${modePreference === 'MOBILE' ? 'active' : ''}`}
                onClick={() => onSetModePreference && onSetModePreference('MOBILE')}
                title="Force mobile device layout"
                id="mode-btn-mobile"
                aria-checked={modePreference === 'MOBILE'}
                role="radio"
              >
                <svg className="mode-icon-svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <rect x="5" y="2" width="14" height="20" rx="2" ry="2" />
                  <line x1="12" y1="18" x2="12.01" y2="18" />
                </svg>
                <span className="mode-btn-label">Mobile</span>
              </button>
            </div>
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
              {viewMode === 'VERIFY' ? (
                <>
                  <svg className="dev-icon-svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                    <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" />
                  </svg>
                  <span>Dev</span>
                </>
              ) : (
                <>
                  <svg className="dev-icon-svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                  <span>Verify</span>
                </>
              )}
            </button>
          </div>
        </header>

        {/* Dynamic View Body */}
        <main className="app-scrollable-body mobile-scrollable-body">{children}</main>
      </div>
    </div>
  );
}
