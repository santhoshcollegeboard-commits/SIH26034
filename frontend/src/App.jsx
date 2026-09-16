import { useState, useEffect } from 'react';
import Header from './components/Header';
import RoleSwitcher from './components/RoleSwitcher';
import InspectorWorkflow from './pages/InspectorWorkflow';
import ReviewerQueue from './pages/ReviewerQueue';
import InspectionHistory from './pages/InspectionHistory';
import ResultView from './pages/ResultView';
import { api } from './services/api';

function App() {
  // Roles: 'inspector' | 'reviewer'
  const [activeRole, setActiveRole] = useState('inspector');
  const [hasSelectedRole, setHasSelectedRole] = useState(false);
  const [showRoleModal, setShowRoleModal] = useState(false);

  // Views: 'new-inspection' | 'history' | 'review-queue' | 'result-view'
  const [currentView, setCurrentView] = useState('new-inspection');
  const [selectedInspectionId, setSelectedInspectionId] = useState(null);

  // Backend connectivity & queue count
  const [backendStatus, setBackendStatus] = useState('checking');
  const [reviewQueueCount, setReviewQueueCount] = useState(0);

  // Check health periodically
  useEffect(() => {
    let isMounted = true;
    async function ping() {
      const isAlive = await api.checkHealth();
      if (isMounted) {
        setBackendStatus(isAlive ? 'connected' : 'offline');
      }
    }
    ping();
    const interval = setInterval(ping, 10000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  // Update review queue count
  useEffect(() => {
    let isMounted = true;
    async function fetchQueueCount() {
      try {
        const list = await api.listInspections(100, 0);
        if (isMounted && list) {
          const count = list.filter((i) => i.overall_disposition === 'REVIEW_REQUIRED').length;
          setReviewQueueCount(count);
        }
      } catch {
        // Silently fail queue count on error
      }
    }
    fetchQueueCount();
    const interval = setInterval(fetchQueueCount, 15000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [currentView]);

  function handleRoleChange(newRole) {
    setActiveRole(newRole);
    setHasSelectedRole(true);
    if (newRole === 'inspector') {
      setCurrentView('new-inspection');
    } else {
      setCurrentView('review-queue');
    }
  }

  function handleNavigate(view, inspectionId = null) {
    if (inspectionId) {
      setSelectedInspectionId(inspectionId);
    }
    if (view === 'home') {
      setCurrentView(activeRole === 'inspector' ? 'new-inspection' : 'review-queue');
    } else {
      setCurrentView(view);
    }
  }

  function handleInspectionCompleted(inspectionId) {
    setSelectedInspectionId(inspectionId);
    setCurrentView('result-view');
  }

  function handleSwitchToReviewer(inspectionId) {
    setActiveRole('reviewer');
    setSelectedInspectionId(inspectionId);
    setCurrentView('review-queue');
  }

  return (
    <div className="app-wrapper" id="packcheck-app">
      {/* App Header with role switcher and navigation */}
      <Header
        backendStatus={backendStatus}
        activeRole={activeRole}
        currentView={currentView}
        onNavigate={(v) => handleNavigate(v)}
        onOpenRoleSwitcher={() => setShowRoleModal(true)}
        reviewQueueCount={reviewQueueCount}
      />

      {/* Main Page Area */}
      <main className="app-main">
        {!hasSelectedRole ? (
          <div className="welcome-role-container">
            <RoleSwitcher
              activeRole={activeRole}
              onSelectRole={(r) => handleRoleChange(r)}
              isModal={false}
            />
          </div>
        ) : (
          <>
            {currentView === 'new-inspection' && (
              <InspectorWorkflow
                onInspectionCompleted={handleInspectionCompleted}
                onSwitchToReviewer={handleSwitchToReviewer}
              />
            )}

            {currentView === 'review-queue' && (
              <ReviewerQueue
                initialInspectionId={selectedInspectionId}
                onReviewCompleted={(id) => {
                  setSelectedInspectionId(id);
                  setCurrentView('result-view');
                }}
              />
            )}

            {currentView === 'history' && (
              <InspectionHistory
                onSelectInspection={(id) => {
                  setSelectedInspectionId(id);
                  setCurrentView('result-view');
                }}
              />
            )}

            {currentView === 'result-view' && (
              <ResultView
                inspectionId={selectedInspectionId}
                onBack={() => {
                  setCurrentView(activeRole === 'inspector' ? 'new-inspection' : 'review-queue');
                }}
                onNewInspection={() => {
                  setActiveRole('inspector');
                  setCurrentView('new-inspection');
                }}
              />
            )}
          </>
        )}
      </main>

      {/* Footer */}
      <footer className="app-footer">
        <span>PackCheck · Legal Metrology Inspection Platform · SIH26034</span>
        <span>Deterministic Rule Engine · Standards of Weights &amp; Measures Act</span>
      </footer>

      {/* Role Switcher Modal */}
      {showRoleModal && (
        <RoleSwitcher
          activeRole={activeRole}
          onSelectRole={handleRoleChange}
          onClose={() => setShowRoleModal(false)}
          isModal={true}
        />
      )}
    </div>
  );
}

export default App;
