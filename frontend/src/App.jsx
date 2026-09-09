import React, { useState, useEffect } from 'react';
import AppShell from './components/AppShell';
import HomeScreen from './components/HomeScreen';
import ImagePreview from './components/ImagePreview';
import VerificationLoader from './components/VerificationLoader';
import ResultScreen from './components/ResultScreen';
import ErrorBanner from './components/ErrorBanner';
import ExtractTest from './ExtractTest';

const API_BASE = 'http://127.0.0.1:8000';
const MAX_UPLOAD_BYTES = 10 * 1024 * 1024; // 10 MB

export default function App() {
  const [viewMode, setViewMode] = useState('VERIFY'); // 'VERIFY' | 'DEV_EXTRACT'
  const [screen, setScreen] = useState('HOME'); // 'HOME' | 'PREVIEW' | 'VERIFYING' | 'RESULT'
  const [file, setFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
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

  // Handle image file selection
  const handleSelectFile = (selectedFile) => {
    if (!selectedFile) return;

    setError(null);

    // Validate MIME type
    const allowedTypes = ['image/jpeg', 'image/png', 'image/webp'];
    if (!allowedTypes.includes(selectedFile.type)) {
      setError('Please select a valid package image (JPEG, PNG, or WEBP).');
      return;
    }

    // Validate empty file
    if (selectedFile.size === 0) {
      setError('The selected file is empty (0 bytes). Please choose a valid image.');
      return;
    }

    // Validate file size limit
    if (selectedFile.size > MAX_UPLOAD_BYTES) {
      const sizeMb = (selectedFile.size / (1024 * 1024)).toFixed(1);
      setError(`Image too large (${sizeMb} MB). Maximum allowed size is 10 MB.`);
      return;
    }

    // Revoke previous object URL if existing
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
    }

    const objectUrl = URL.createObjectURL(selectedFile);
    setFile(selectedFile);
    setPreviewUrl(objectUrl);
    setVerificationResponse(null);
    setScreen('PREVIEW');
  };

  // Start verification API request
  const handleStartVerification = async () => {
    if (!file) return;

    setScreen('VERIFYING');
    setError(null);

    try {
      const formData = new FormData();
      formData.append('image', file);

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
        file.name;
      const verdict = data.compliance?.overall_verdict || 'REVIEW';
      const newEntry = {
        id: Date.now(),
        productName,
        verdict,
        timestamp: 'Just now',
        data,
        previewUrl,
      };
      setRecentChecks((prev) => [newEntry, ...prev.slice(0, 4)]);
    } catch (err) {
      setError(`Network error: ${err.message}. Please check that the PackCheck API is running.`);
      setScreen('PREVIEW');
    }
  };

  // Reset workflow to Home
  const handleResetToHome = () => {
    setFile(null);
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
    }
    setPreviewUrl(null);
    setVerificationResponse(null);
    setError(null);
    setScreen('HOME');
  };

  // Load a recent check into result screen
  const handleSelectRecent = (recentItem) => {
    if (recentItem?.data) {
      setVerificationResponse(recentItem.data);
      setPreviewUrl(recentItem.previewUrl || null);
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
        <div className="verify-flow-container">
          {error && (
            <ErrorBanner
              error={error}
              onDismiss={() => setError(null)}
              onRetry={screen === 'PREVIEW' ? handleStartVerification : null}
            />
          )}

          {screen === 'HOME' && (
            <HomeScreen
              onSelectFile={handleSelectFile}
              recentChecks={recentChecks}
              onSelectRecent={handleSelectRecent}
            />
          )}

          {screen === 'PREVIEW' && (
            <ImagePreview
              file={file}
              previewUrl={previewUrl}
              onVerify={handleStartVerification}
              onReset={handleResetToHome}
            />
          )}

          {screen === 'VERIFYING' && <VerificationLoader previewUrl={previewUrl} />}

          {screen === 'RESULT' && (
            <ResultScreen
              verificationResponse={verificationResponse}
              previewUrl={previewUrl}
              onReset={handleResetToHome}
            />
          )}
        </div>
      )}
    </AppShell>
  );
}
