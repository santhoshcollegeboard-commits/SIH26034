import { useState, useEffect, useCallback } from 'react';

const STORAGE_KEY = 'packcheck_device_mode_preference';
export const BREAKPOINT = 992; // Breakpoint between mobile/tablet and desktop workstation

/**
 * Hook to manage device mode: AUTO | PC | MOBILE
 * - 'AUTO': Automatically switches between PC and Mobile based on viewport width (>= 992px)
 * - 'PC': Forces full-width desktop workstation layout
 * - 'MOBILE': Forces mobile layout (centered mobile frame on desktop)
 *
 * Persists selection in localStorage and responds dynamically to browser resizing.
 */
export function useDeviceMode() {
  // 1. Initial preference from localStorage or 'AUTO'
  const [modePreference, setModePreferenceState] = useState(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved === 'PC' || saved === 'MOBILE' || saved === 'AUTO') {
        return saved;
      }
    } catch {
      // Ignore storage access errors in restricted contexts
    }
    return 'AUTO';
  });

  // 2. Viewport detection state
  const [detectedMode, setDetectedMode] = useState(() => {
    if (typeof window !== 'undefined') {
      return window.innerWidth >= BREAKPOINT ? 'PC' : 'MOBILE';
    }
    return 'PC';
  });

  // 3. Listen to resize events
  useEffect(() => {
    const handleResize = () => {
      const nextDetected = window.innerWidth >= BREAKPOINT ? 'PC' : 'MOBILE';
      setDetectedMode(nextDetected);
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // 4. Update preference with persistence
  const setModePreference = useCallback((newPref) => {
    if (newPref !== 'AUTO' && newPref !== 'PC' && newPref !== 'MOBILE') return;
    setModePreferenceState(newPref);
    try {
      localStorage.setItem(STORAGE_KEY, newPref);
    } catch {
      // Ignore storage access errors
    }
  }, []);

  // 5. Compute effective mode
  const effectiveMode = modePreference === 'AUTO' ? detectedMode : modePreference;

  return {
    modePreference,
    setModePreference,
    detectedMode,
    effectiveMode,
    isPC: effectiveMode === 'PC',
    isMobile: effectiveMode === 'MOBILE',
  };
}
