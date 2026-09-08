import { useState, useEffect } from 'react';
import ExtractTest from './ExtractTest';

function App() {
  const [backendStatus, setBackendStatus] = useState('checking');

  useEffect(() => {
    fetch('http://127.0.0.1:8000/health')
      .then((res) => {
        if (res.ok) return res.json();
        throw new Error('Health check failed');
      })
      .then((data) => {
        if (data.status === 'ok') setBackendStatus('connected');
        else setBackendStatus('unhealthy');
      })
      .catch(() => setBackendStatus('offline'));
  }, []);

  return (
    <div className="app-wrapper" id="packcheck-app">
      {/* Header */}
      <header className="app-header">
        <div className="header-left">
          <h1 className="app-title" id="project-title">PackCheck</h1>
          <div className="header-badge">
            <span className="badge-dot"></span>
            <span>SIH26034</span>
          </div>
        </div>
        <div className="header-right">
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
            <span>
              {backendStatus === 'connected'
                ? 'API Connected'
                : backendStatus === 'checking'
                ? 'Connecting...'
                : 'API Offline'}
            </span>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="app-main">
        <div className="section-header">
          <h2 className="section-title">Field Extraction Test</h2>
          <p className="section-sub">
            Upload a packaged commodity image to extract Legal Metrology declarations via Gemini Vision.
          </p>
        </div>
        <ExtractTest />
      </main>

      {/* Footer */}
      <footer className="app-footer">
        <span>PackCheck · SIH26034 · Milestone 2</span>
        <span>Extraction only — no compliance judgment</span>
      </footer>
    </div>
  );
}

export default App;
