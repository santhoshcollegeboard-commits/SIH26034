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
              <span className="brand-logo-icon">📦</span>
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
                💻 <span className="mode-btn-label">PC</span>
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
                📱 <span className="mode-btn-label">Mobile</span>
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
              {viewMode === 'VERIFY' ? '🛠️ Dev' : '✓ Verify'}
            </button>
          </div>
        </header>

        {/* Dynamic View Body */}
        <main className="app-scrollable-body mobile-scrollable-body">{children}</main>
      </div>
    </div>
  );
}
