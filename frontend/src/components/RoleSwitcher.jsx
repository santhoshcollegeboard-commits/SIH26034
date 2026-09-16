/**
 * Modal or standalone banner for role selection.
 * Explicitly states this is an MVP role-based workflow simulation, not authentication.
 */
export default function RoleSwitcher({ activeRole, onSelectRole, onClose, isModal = true }) {
  function handleSelect(role) {
    onSelectRole(role);
    if (onClose) onClose();
  }

  const content = (
    <div className="role-selection-card" id="role-selection-card">
      <div className="role-card-header">
        <h2 className="role-title">Welcome to PackCheck</h2>
        <p className="role-subtitle">
          Legal Metrology statutory compliance platform for packaged commodities. Select your role to continue:
        </p>
      </div>

      <div className="role-options-grid">
        <div
          className={`role-option-box ${activeRole === 'inspector' ? 'selected' : ''}`}
          onClick={() => handleSelect('inspector')}
          id="role-option-inspector"
        >
          <div className="role-option-icon">👤</div>
          <div className="role-option-name">Inspector</div>
          <p className="role-option-desc">
            Capture package image, assess quality gate, extract declarations, review compliance evaluations, and submit inspections.
          </p>
          <button
            type="button"
            className={`btn ${activeRole === 'inspector' ? 'btn-primary' : 'btn-secondary'} btn-block mt-3`}
          >
            {activeRole === 'inspector' ? 'Active: Inspector' : 'Select Inspector'}
          </button>
        </div>

        <div
          className={`role-option-box ${activeRole === 'reviewer' ? 'selected' : ''}`}
          onClick={() => handleSelect('reviewer')}
          id="role-option-reviewer"
        >
          <div className="role-option-icon">🕵️</div>
          <div className="role-option-name">Reviewer</div>
          <p className="role-option-desc">
            Access inspections requiring human review, inspect uncertainty and source bounding boxes, confirm or correct observations, and finalize statutory dispositions.
          </p>
          <button
            type="button"
            className={`btn ${activeRole === 'reviewer' ? 'btn-primary' : 'btn-secondary'} btn-block mt-3`}
          >
            {activeRole === 'reviewer' ? 'Active: Reviewer' : 'Select Reviewer'}
          </button>
        </div>
      </div>

      <div className="role-disclaimer">
        <span className="disclaimer-icon">ℹ</span>
        <span>
          <strong>MVP role-based workflow simulation:</strong> Role selection customizes available UI actions and workflow stages for demonstration purposes. It does not represent secure authentication or RBAC.
        </span>
      </div>

      {isModal && onClose && (
        <div className="modal-footer-close">
          <button className="btn btn-outline btn-sm" onClick={onClose}>
            Close
          </button>
        </div>
      )}
    </div>
  );

  if (!isModal) {
    return content;
  }

  return (
    <div className="modal-backdrop" onClick={onClose} id="role-modal-backdrop">
      <div className="modal-content role-modal" onClick={(e) => e.stopPropagation()}>
        {content}
      </div>
    </div>
  );
}
