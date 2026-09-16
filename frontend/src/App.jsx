import React, { useState, useEffect } from 'react';
import AppShell from './components/AppShell';
import HomeScreen from './components/HomeScreen';
import ImagePreview from './components/ImagePreview';
import VerificationLoader from './components/VerificationLoader';
import ResultScreen from './components/ResultScreen';
import ErrorBanner from './components/ErrorBanner';
import ExtractTest from './ExtractTest';
import { useDeviceMode } from './hooks/useDeviceMode';

const API_BASE = 'http://127.0.0.1:8000';
const MAX_UPLOAD_BYTES = 10 * 1024 * 1024; // 10 MB per file
const MAX_PANELS = 10;

const DEFAULT_PANEL_LABELS = [
  'Front Panel',
  'Back Panel',
  'Side Panel (Left)',
  'Side Panel (Right)',
  'Top Panel',
  'Bottom Panel',
  'Other / Detail View',
];

export default function App() {
  const { modePreference, setModePreference, effectiveMode, isPC, isMobile } = useDeviceMode();
  const [viewMode, setViewMode] = useState('VERIFY'); // 'VERIFY' | 'DEV_EXTRACT'
  const [screen, setScreen] = useState('HOME'); // 'HOME' | 'PREVIEW' | 'VERIFYING' | 'RESULT'
  const [panels, setPanels] = useState([]); // [{ id, file, previewUrl, panelLabel }]
  const [verificationResponse, setVerificationResponse] = useState(null);
  const [error, setError] = useState(null);
  const [backendStatus, setBackendStatus] = useState('checking');
  const [recentChecks, setRecentChecks] = useState([]);

  // Check backend health on mount
  useEffect(() => {
    fetch(`${API_BASE}/health`)
      .then((res) => {
        if (res.ok) return res.json();
        throw new Error('Health check failed');
      })
      .then((data) => {
        if (data.status === 'ok') setBackendStatus('connected');
        else setBackendStatus('offline');
      })
      .catch(() => setBackendStatus('offline'));
  }, []);

  // Validate a list of files against constraints
  const validateFile = (selectedFile) => {
    const allowedTypes = ['image/jpeg', 'image/png', 'image/webp'];
    if (!allowedTypes.includes(selectedFile.type)) {
      return `"${selectedFile.name}" is not a supported format (JPEG, PNG, or WEBP only).`;
    }
    if (selectedFile.size === 0) {
      return `"${selectedFile.name}" is empty (0 bytes).`;
    }
    if (selectedFile.size > MAX_UPLOAD_BYTES) {
      const sizeMb = (selectedFile.size / (1024 * 1024)).toFixed(1);
      return `"${selectedFile.name}" is too large (${sizeMb} MB). Maximum allowed size is 10 MB.`;
    }
    return null;
  };

  // Handle initial batch of files from Home screen
  const handleSelectFiles = (incomingFiles) => {
    if (!incomingFiles || incomingFiles.length === 0) return;

    setError(null);
    const filesArray = Array.from(incomingFiles);

    if (filesArray.length > MAX_PANELS) {
      setError(`A maximum of ${MAX_PANELS} package panels can be verified at once.`);
      return;
    }

    // Validate each file
    for (const f of filesArray) {
      const valError = validateFile(f);
      if (valError) {
        setError(valError);
        return;
      }
    }

    // Revoke previous URLs
    panels.forEach((p) => {
      if (p.previewUrl) URL.revokeObjectURL(p.previewUrl);
    });

    // Deduplicate incoming files by name and size to ensure single entry per file
    const uniqueFiles = filesArray.filter(
      (file, index, self) =>
        index === self.findIndex((f) => f.name === file.name && f.size === file.size)
    );

    const newPanels = uniqueFiles.map((file, idx) => ({
      id: `panel-${Date.now()}-${Math.random().toString(36).slice(2, 7)}-${idx}`,
      file,
      previewUrl: URL.createObjectURL(file),
      panelLabel: DEFAULT_PANEL_LABELS[Math.min(idx, DEFAULT_PANEL_LABELS.length - 1)],
    }));

    setPanels(newPanels);
    setVerificationResponse(null);
    setScreen('PREVIEW');
  };

  // Single-file fallback compatibility
  const handleSelectFile = (file) => {
    if (file) handleSelectFiles([file]);
  };

  // Add more panels while on Preview screen
  const handleAddMoreFiles = (moreFiles) => {
    if (!moreFiles || moreFiles.length === 0) return;

    setError(null);
    const filesArray = Array.from(moreFiles);

    // Prevent adding duplicate files that already exist in panels
    const nonDuplicateFiles = filesArray.filter(
      (file) => !panels.some((p) => p.file.name === file.name && p.file.size === file.size)
    );

    if (nonDuplicateFiles.length === 0) return;

    if (panels.length + nonDuplicateFiles.length > MAX_PANELS) {
      setError(`Cannot add more than ${MAX_PANELS} panels in total. Currently have ${panels.length}.`);
      return;
    }

    for (const f of nonDuplicateFiles) {
      const valError = validateFile(f);
      if (valError) {
        setError(valError);
        return;
      }
    }

    const nextPanels = nonDuplicateFiles.map((file, idx) => {
      const totalIdx = panels.length + idx;
      return {
        id: `panel-${Date.now()}-${Math.random().toString(36).slice(2, 7)}-${totalIdx}`,
        file,
        previewUrl: URL.createObjectURL(file),
        panelLabel: DEFAULT_PANEL_LABELS[Math.min(totalIdx, DEFAULT_PANEL_LABELS.length - 1)],
      };
    });

    setPanels((prev) => [...prev, ...nextPanels]);
  };

  // Remove a single panel
  const handleRemovePanel = (panelId) => {
    setPanels((prev) => {
      const target = prev.find((p) => p.id === panelId);
      if (target?.previewUrl) {
        URL.revokeObjectURL(target.previewUrl);
      }
      const filtered = prev.filter((p) => p.id !== panelId);
      if (filtered.length === 0) {
        setVerificationResponse(null);
        setError(null);
        setScreen('HOME');
      }
      return filtered;
    });
  };

  // Update a panel's descriptive label (e.g. Front -> Back)
  const handleUpdatePanelLabel = (panelId, newLabel) => {
    setPanels((prev) =>
      prev.map((p) => (p.id === panelId ? { ...p, panelLabel: newLabel } : p))
    );
  };

  // Start verification API request across all package panels
  const handleStartVerification = async () => {
    if (!panels || panels.length === 0) return;

    setScreen('VERIFYING');
    setError(null);

    try {
      const formData = new FormData();
      panels.forEach((p) => {
        formData.append('images', p.file);
        formData.append('panel_labels', p.panelLabel || 'Panel');
      });
      // Backward compatibility: provide first image in 'image' field
      formData.append('image', panels[0].file);

      const response = await fetch(`${API_BASE}/api/verify`, {
        method: 'POST',
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        setError(data.detail || 'Verification request failed.');
        setScreen('PREVIEW');
        return;
      }

      if (!data.success) {
        setError(data.error || 'Verification encountered an error.');
        setScreen('PREVIEW');
        return;
      }

      setVerificationResponse(data);
      setScreen('RESULT');

      // Add to recent checks
      const productName =
        data.extraction?.common_or_generic_name?.value ||
        data.extraction?.product_name?.value ||
        panels[0].file.name;
      const verdict = data.compliance?.overall_verdict || 'REVIEW';
      const newEntry = {
        id: Date.now(),
        productName,
        verdict,
        timestamp: 'Just now',
        data,
        previewUrl: panels[0]?.previewUrl,
        panels: panels.map((p) => ({
          previewUrl: p.previewUrl,
          panelLabel: p.panelLabel,
        })),
      };
      setRecentChecks((prev) => [newEntry, ...prev.slice(0, 4)]);
    } catch (err) {
      setError(`Network error: ${err.message}. Please check that the PackCheck API is running.`);
      setScreen('PREVIEW');
    }
  };

  // Reset workflow to Home
  const handleResetToHome = () => {
    panels.forEach((p) => {
      if (p.previewUrl) URL.revokeObjectURL(p.previewUrl);
    });
    setPanels([]);
    setVerificationResponse(null);
    setError(null);
    setScreen('HOME');
  };

  // Load a recent check into result screen
  const handleSelectRecent = (recentItem) => {
    if (recentItem?.data) {
      setVerificationResponse(recentItem.data);
      if (recentItem.panels && recentItem.panels.length > 0) {
        setPanels(
          recentItem.panels.map((p, idx) => ({
            id: `recent-${idx}`,
            previewUrl: p.previewUrl,
            panelLabel: p.panelLabel,
          }))
        );
      }
      setScreen('RESULT');
    }
  };

  // Switch between primary Verification App and preserved Extraction Dev tool
  const handleToggleViewMode = () => {
    setViewMode((prev) => (prev === 'VERIFY' ? 'DEV_EXTRACT' : 'VERIFY'));
    setError(null);
  };

  return (
    <AppShell
      backendStatus={backendStatus}
      viewMode={viewMode}
      onToggleViewMode={handleToggleViewMode}
      onResetToHome={handleResetToHome}
      modePreference={modePreference}
      effectiveMode={effectiveMode}
      onSetModePreference={setModePreference}
    >
      {/* Dev Mode View: Preserved /api/extract component */}
      {viewMode === 'DEV_EXTRACT' ? (
        <div className="dev-mode-wrapper">
          <div className="dev-banner">
            <span className="dev-tag">Developer Mode</span>
            <p className="dev-desc">
              Testing raw AI/OCR extraction endpoint (POST /api/extract) without statutory rule evaluation.
            </p>
          </div>
          <ExtractTest />
        </div>
      ) : (
        /* Primary Verification Workflow */
        <div className={`verify-flow-container mode-${effectiveMode.toLowerCase()}`}>
          {error && (
            <ErrorBanner
              error={error}
              onDismiss={() => setError(null)}
              onRetry={screen === 'PREVIEW' ? handleStartVerification : null}
            />
          )}

          {screen === 'HOME' && (
            <HomeScreen
              onSelectFiles={handleSelectFiles}
              onSelectFile={handleSelectFile}
              recentChecks={recentChecks}
              onSelectRecent={handleSelectRecent}
              isPC={isPC}
              isMobile={isMobile}
              effectiveMode={effectiveMode}
            />
          )}

          {screen === 'PREVIEW' && (
            <ImagePreview
              panels={panels}
              onVerify={handleStartVerification}
              onReset={handleResetToHome}
              onRemovePanel={handleRemovePanel}
              onUpdatePanelLabel={handleUpdatePanelLabel}
              onAddMoreFiles={handleAddMoreFiles}
              isPC={isPC}
              isMobile={isMobile}
              effectiveMode={effectiveMode}
            />
          )}

          {screen === 'VERIFYING' && (
            <VerificationLoader
              previewUrl={panels[0]?.previewUrl}
              previewUrls={panels.map((p) => p.previewUrl)}
              panelCount={panels.length}
              isPC={isPC}
              isMobile={isMobile}
              effectiveMode={effectiveMode}
            />
          )}

          {screen === 'RESULT' && (
            <ResultScreen
              verificationResponse={verificationResponse}
              previewUrl={panels[0]?.previewUrl}
              previewUrls={panels.map((p) => p.previewUrl)}
              panels={panels}
              onReset={handleResetToHome}
              isPC={isPC}
              isMobile={isMobile}
              effectiveMode={effectiveMode}
            />
          )}
        </div>
      )}
    </AppShell>
  );
}
