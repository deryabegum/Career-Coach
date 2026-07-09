import React, { useEffect, useState, useCallback } from 'react';
import { api } from '../api';
import './CareerAgent.css';

const STEP_LABELS = {
  load_resume: 'Load resume',
  score_resume: 'Score resume',
  gap_analysis: 'Analyze job fit',
  plan_adjustment: 'Adapt the plan',
  draft_cover_letter: 'Draft cover letter',
  build_interview_prep: 'Build interview prep',
};

const CareerAgent = () => {
  const [role, setRole] = useState('');
  const [company, setCompany] = useState('');
  const [jobDescription, setJobDescription] = useState('');
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState(null);
  const [copied, setCopied] = useState(false);
  const [runs, setRuns] = useState([]);
  const [runsLoading, setRunsLoading] = useState(true);

  const loadRuns = useCallback(async () => {
    try {
      setRunsLoading(true);
      const data = await api.getCareerAgentRuns();
      setRuns(data.runs || []);
    } catch (err) {
      // Recent-runs history is a nice-to-have; ignore load errors here.
    } finally {
      setRunsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadRuns();
  }, [loadRuns]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsRunning(true);
    setError('');
    setResult(null);
    setCopied(false);

    try {
      const data = await api.runCareerAgent({
        role,
        company,
        job_description: jobDescription,
      });
      setResult(data);
      loadRuns();
    } catch (err) {
      setError(err.message || 'The career agent run failed.');
    } finally {
      setIsRunning(false);
    }
  };

  const openPastRun = async (runId) => {
    setError('');
    setResult(null);
    setCopied(false);
    try {
      const data = await api.getCareerAgentRun(runId);
      setRole(data.role || '');
      setCompany(data.company || '');
      setJobDescription(data.job_description || '');
      setResult(data);
    } catch (err) {
      setError(err.message || 'Could not load that run.');
    }
  };

  const copyCoverLetter = async () => {
    if (!result?.cover_letter?.cover_letter) return;
    try {
      await navigator.clipboard.writeText(result.cover_letter.cover_letter);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      // Clipboard access can be blocked by the browser; nothing actionable to do.
    }
  };

  return (
    <div className="career-agent-page">
      <div className="auth-container career-agent-form" style={{ minHeight: 'unset' }}>
        <div className="auth-card" style={{ maxWidth: '900px' }}>
          <h2>Career Agent</h2>
          <p style={{ color: '#AAAAAA', marginTop: '-1rem', marginBottom: '2rem', textAlign: 'center' }}>
            One autonomous run: analyzes your latest resume, finds the gaps against a job
            description, then drafts a tailored cover letter and interview prep plan.
          </p>

          <form onSubmit={handleSubmit} noValidate>
            <div className="career-agent-inline-inputs">
              <div className="input-group">
                <label htmlFor="agent-role">Role</label>
                <input
                  id="agent-role"
                  className="auth-input"
                  value={role}
                  onChange={(e) => setRole(e.target.value)}
                  placeholder="e.g. Data Analyst"
                />
              </div>
              <div className="input-group">
                <label htmlFor="agent-company">Company</label>
                <input
                  id="agent-company"
                  className="auth-input"
                  value={company}
                  onChange={(e) => setCompany(e.target.value)}
                  placeholder="e.g. Gauge Capital"
                />
              </div>
            </div>

            <div className="input-group">
              <label htmlFor="agent-job-description">Job Description</label>
              <textarea
                id="agent-job-description"
                className="auth-textarea"
                value={jobDescription}
                onChange={(e) => setJobDescription(e.target.value)}
                placeholder="Paste the full job description here..."
                required
              />
            </div>

            <div style={{ marginTop: '1.5rem' }}>
              <button type="submit" className="auth-button" disabled={isRunning}>
                {isRunning ? 'Running agent...' : 'Run Career Agent'}
              </button>
            </div>
          </form>

          {error && <div className="auth-error">{error}</div>}

          {result && (
            <div className="results-container agent-results">
              {result.steps?.length > 0 && (
                <ol className="agent-trace">
                  {result.steps.map((step) => (
                    <li key={step.step} className="agent-trace-item">
                      <span className="agent-trace-check">✓</span>
                      <div>
                        <div className="agent-trace-label">
                          {STEP_LABELS[step.step] || step.step}
                        </div>
                        <div className="agent-trace-detail">{step.detail}</div>
                      </div>
                    </li>
                  ))}
                </ol>
              )}

              {result.decisions?.length > 0 && (
                <div className="agent-decisions">
                  <span className="match-metric-label">Agent Decisions</span>
                  <ul className="results-list">
                    {result.decisions.map((decision, i) => (
                      <li key={`decision-${i}`} className="results-list-item">
                        {decision}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              <div className="match-metrics-grid agent-metrics-grid">
                <div className="match-metric-card">
                  <span className="match-metric-label">Resume Score</span>
                  <strong>{result.resume_analysis?.score ?? 0}/100</strong>
                  <p>{result.resume_analysis?.summary}</p>
                </div>
                <div className="match-metric-card">
                  <span className="match-metric-label">Job Fit</span>
                  <strong>{Math.round((result.match_analysis?.score || 0) * 100)}%</strong>
                  <p>Semantic and keyword overlap against the pasted job description.</p>
                </div>
                <div className="match-metric-card">
                  <span className="match-metric-label">Missing Keywords</span>
                  <strong>{result.match_analysis?.missing_keywords?.length || 0}</strong>
                  <p>Keywords in the job description not yet reflected in the resume.</p>
                </div>
              </div>

              <div className="agent-panel">
                <div className="agent-panel-header">
                  <h5>Tailored Cover Letter</h5>
                  <button type="button" className="auth-button job-secondary-button agent-copy-button" onClick={copyCoverLetter}>
                    {copied ? 'Copied!' : 'Copy'}
                  </button>
                </div>
                <p className="agent-cover-letter">{result.cover_letter?.cover_letter}</p>
              </div>

              <div className="agent-panel">
                <h5>Interview Prep Plan</h5>
                {result.interview_prep?.focus_areas?.length > 0 && (
                  <div className="agent-focus-areas">
                    {result.interview_prep.focus_areas.map((area, i) => (
                      <div className="match-highlight-card" key={`focus-${i}`}>
                        <div className="match-highlight-score">{area.keyword}</div>
                        <p style={{ margin: '0 0 0.5rem' }}>{area.why_it_matters}</p>
                        <p style={{ margin: 0, color: '#FFB347' }}>{area.how_to_prepare}</p>
                      </div>
                    ))}
                  </div>
                )}
                <ul className="results-list agent-question-list">
                  {(result.interview_prep?.questions || []).map((q) => (
                    <li key={q.id} className="results-list-item">
                      {q.prompt}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="auth-container career-agent-history" style={{ minHeight: 'unset', paddingTop: 0 }}>
        <div className="auth-card" style={{ maxWidth: '900px' }}>
          <h2>Recent Runs</h2>
          {runsLoading ? (
            <p style={{ color: '#AAAAAA', textAlign: 'center' }}>Loading history...</p>
          ) : runs.length === 0 ? (
            <p style={{ color: '#AAAAAA', textAlign: 'center' }}>No career agent runs yet.</p>
          ) : (
            <div className="job-grid">
              {runs.map((run) => (
                <button
                  type="button"
                  key={run.id}
                  className="job-card agent-run-card"
                  onClick={() => openPastRun(run.id)}
                >
                  <div className="job-card-top">
                    <div>
                      <div className="job-card-company">{run.company || 'Unnamed company'}</div>
                      <h3>{run.role || 'Unnamed role'}</h3>
                    </div>
                    <span className="job-chip">{run.fit_score != null ? `${Math.round(run.fit_score * 100)}% fit` : '—'}</span>
                  </div>
                  <div className="job-card-meta">
                    <span>Resume score: {run.resume_score ?? '—'}</span>
                    <span>{run.created_at}</span>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default CareerAgent;
