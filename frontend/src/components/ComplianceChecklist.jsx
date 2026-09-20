import React, { useState } from 'react';
import ComplianceRuleCard from './ComplianceRuleCard';

/**
 * Filterable mobile checklist of statutory rule evaluations.
 */
export default function ComplianceChecklist({ evaluations = [], extraction = {} }) {
  const [filter, setFilter] = useState('ALL');

  // Map rule_id to primary extracted field in extraction result
  const fieldMapping = {
    'LM-PC-06-1-A': extraction?.common_or_generic_name || extraction?.product_name,
    'LM-PC-06-1-B': extraction?.manufacturer_address || extraction?.manufacturer_name,
    'LM-PC-06-1-B-ORIGIN': extraction?.country_of_origin || extraction?.importer_name,
    'LM-PC-06-1-C': extraction?.net_quantity,
    'LM-PC-11-UNITS': extraction?.net_quantity,
    'LM-PC-06-1-D': extraction?.month_year_of_manufacture,
    'LM-PC-06-1-E': extraction?.mrp,
    'LM-PC-06-1-F': extraction?.consumer_care_details,
    'LM-PC-06-1-H-USP': extraction?.mrp,
  };

  const counts = {
    ALL: evaluations.length,
    FAIL: evaluations.filter((e) => e.status === 'FAIL').length,
    NOT_VERIFIABLE: evaluations.filter((e) => e.status === 'NOT_VERIFIABLE').length,
    PASS: evaluations.filter((e) => e.status === 'PASS').length,
    NOT_APPLICABLE: evaluations.filter((e) => e.status === 'NOT_APPLICABLE').length,
  };

  const filteredEvaluations = evaluations.filter((e) => {
    if (filter === 'ALL') return true;
    return e.status === filter;
  });

  return (
    <section className="checklist-container">
      <div className="checklist-header">
        <h3 className="checklist-heading">Statutory Declarations</h3>
        <span className="checklist-subtitle">
          {evaluations.length} Legal Metrology rules evaluated
        </span>
      </div>

      {/* Filter Tabs */}
      <div className="filter-scroll" role="tablist" aria-label="Filter rules by status">
        <button
          type="button"
          role="tab"
          aria-selected={filter === 'ALL'}
          className={`filter-chip ${filter === 'ALL' ? 'active' : ''}`}
          onClick={() => setFilter('ALL')}
        >
          All ({counts.ALL})
        </button>

        {counts.FAIL > 0 && (
          <button
            type="button"
            role="tab"
            aria-selected={filter === 'FAIL'}
            className={`filter-chip chip-fail ${filter === 'FAIL' ? 'active' : ''}`}
            onClick={() => setFilter('FAIL')}
          >
            Failed ({counts.FAIL})
          </button>
        )}

        {counts.NOT_VERIFIABLE > 0 && (
          <button
            type="button"
            role="tab"
            aria-selected={filter === 'NOT_VERIFIABLE'}
            className={`filter-chip chip-review ${filter === 'NOT_VERIFIABLE' ? 'active' : ''}`}
            onClick={() => setFilter('NOT_VERIFIABLE')}
          >
            Needs Review ({counts.NOT_VERIFIABLE})
          </button>
        )}

        {counts.PASS > 0 && (
          <button
            type="button"
            role="tab"
            aria-selected={filter === 'PASS'}
            className={`filter-chip chip-pass ${filter === 'PASS' ? 'active' : ''}`}
            onClick={() => setFilter('PASS')}
          >
            Passed ({counts.PASS})
          </button>
        )}

        {counts.NOT_APPLICABLE > 0 && (
          <button
            type="button"
            role="tab"
            aria-selected={filter === 'NOT_APPLICABLE'}
            className={`filter-chip chip-na ${filter === 'NOT_APPLICABLE' ? 'active' : ''}`}
            onClick={() => setFilter('NOT_APPLICABLE')}
          >
            Exempt ({counts.NOT_APPLICABLE})
          </button>
        )}
      </div>

      {/* Cards List */}
      <div className="cards-list">
        {filteredEvaluations.length > 0 ? (
          filteredEvaluations.map((ev) => (
            <ComplianceRuleCard
              key={ev.rule_id}
              evaluation={ev}
              extractedField={fieldMapping[ev.rule_id]}
            />
          ))
        ) : (
          <div className="empty-filter-state">
            <span className="empty-icon">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <polyline points="20 6 9 17 4 12" />
              </svg>
            </span>
            <p className="empty-text">No rules match the selected filter</p>
          </div>
        )}
      </div>
    </section>
  );
}
