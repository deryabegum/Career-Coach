import React, { useEffect, useMemo, useRef, useState } from 'react';
import { api } from '../api';

const JobMatch = () => {
  const analyzerRef = useRef(null);
  const [jobDescription, setJobDescription] = useState('');
  const [matchResult, setMatchResult] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [jobsLoading, setJobsLoading] = useState(true);
  const [error, setError] = useState('');
  const [jobsError, setJobsError] = useState('');
  const [jobs, setJobs] = useState([]);
  const [categories, setCategories] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [search, setSearch] = useState('');
  const [selectedJobId, setSelectedJobId] = useState(null);

  useEffect(() => {
    let alive = true;

    const loadJobs = async () => {
      try {
        setJobsLoading(true);
        setJobsError('');
        const data = await api.getNewGradJobs({
          limit: 48,
          category: selectedCategory,
          search,
        });

        if (!alive) return;
        setJobs(data.jobs || []);
        setCategories(data.categories || []);
      } catch (err) {
        if (!alive) return;
        setJobsError(err.message || 'Could not load live job listings.');
      } finally {
        if (alive) setJobsLoading(false);
      }
    };

    loadJobs();
    return () => {
      alive = false;
    };
  }, [selectedCategory, search]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');
    setMatchResult(null);

    try {
      const data = await api.matchKeywords({ job_description: jobDescription });
      setMatchResult(data);
    } catch (err) {
      setError(err.message || 'Failed to analyze job description.');
    } finally {
      setIsLoading(false);
    }
  };

  const categoryOptions = useMemo(
    () => ['all', ...categories],
    [categories]
  );

  const scrollToAnalyzer = () => {
    analyzerRef.current?.scrollIntoView({
      behavior: 'smooth',
      block: 'start',
    });
  };

  const fillJobForMatch = async (job) => {
    setSelectedJobId(job.id);
    setMatchResult(null);
    setError('');

    const fallbackText = [
      `Company: ${job.company}`,
      `Role: ${job.role}`,
      `Category: ${job.category}`,
      `Location: ${job.location}`,
      `Listing Age: ${job.age}`,
      '',
      `Job Seed: ${job.description_seed}`,
      '',
      'Paste the full job description below this line for a more accurate match result.',
    ].join('\n');

    try {
      if (!job.simplify_url) {
        setJobDescription(fallbackText);
        setTimeout(scrollToAnalyzer, 50);
        return;
      }

      setJobDescription('Loading full job description...');
      scrollToAnalyzer();
      const details = await api.getJobDetails(job.simplify_url);
      setJobDescription(
        [
          `Company: ${details.company || job.company}`,
          `Role: ${details.title || job.role}`,
          `Category: ${job.category}`,
          `Location: ${details.location || job.location}`,
          `Employment Type: ${details.employment_type || 'Not listed'}`,
          `Date Posted: ${details.date_posted || job.age}`,
          ...(details.salary ? [`Salary: ${details.salary}`] : []),
          '',
          details.description || fallbackText,
        ].join('\n')
      );
      setTimeout(scrollToAnalyzer, 50);
    } catch (err) {
      setJobDescription(fallbackText);
      setError(err.message || 'Could not load the full job description. Using listing summary instead.');
      setTimeout(scrollToAnalyzer, 50);
    } finally {
      setSelectedJobId(null);
    }
  };

  return (
    <div className="job-match-page">
      <div className="job-feed-card">
        <div className="job-feed-header">
          <div>
            <h2>Live New-Grad Job Feed</h2>
            <p>
              Pulling current listings from Simplify&apos;s{' '}
              <a
                href="https://github.com/SimplifyJobs/New-Grad-Positions"
                target="_blank"
                rel="noreferrer"
              >
                New-Grad-Positions
              </a>{' '}
              repo.
            </p>
          </div>
          <span className="job-feed-badge">{jobs.length} shown</span>
        </div>

        <div className="job-feed-controls">
          <input
            className="auth-input"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search company, role, location..."
          />
          <select
            className="auth-input job-filter-select"
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
          >
            {categoryOptions.map((option) => (
              <option key={option} value={option}>
                {option === 'all' ? 'All categories' : option}
              </option>
            ))}
          </select>
        </div>

        {jobsError && <div className="auth-error">{jobsError}</div>}

        {jobsLoading ? (
          <div className="job-feed-empty">Loading live job listings...</div>
        ) : jobs.length === 0 ? (
          <div className="job-feed-empty">No jobs matched your current filters.</div>
        ) : (
          <div className="job-grid">
            {jobs.map((job) => (
              <div className="job-card" key={job.id}>
                <div className="job-card-top">
                  <div>
                    <div className="job-card-company">
                      {job.company}
                      {job.is_featured ? <span className="job-chip featured">Featured</span> : null}
                    </div>
                    <h3>{job.role}</h3>
                  </div>
                  <span className="job-chip">{job.age}</span>
                </div>

                <div className="job-card-meta">
                  <span>{job.location}</span>
                  <span>{job.category}</span>
                </div>

                <div className="job-card-actions">
                  <button
                    type="button"
                    className="auth-button job-secondary-button"
                    onClick={() => fillJobForMatch(job)}
                    disabled={selectedJobId === job.id}
                  >
                    {selectedJobId === job.id ? 'Loading...' : 'Use for Match'}
                  </button>
                  <a
                    className="auth-button job-link-button"
                    href={job.apply_url || job.simplify_url || job.company_url || '#'}
                    target="_blank"
                    rel="noreferrer"
                  >
                    Open Application
                  </a>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="auth-container job-match-analyzer" ref={analyzerRef}>
        <div className="auth-card" style={{ maxWidth: '900px' }}>
          <h2>Resume Keyword Match</h2>
          <p style={{ color: '#AAAAAA', marginTop: '-1rem', marginBottom: '2rem', textAlign: 'center' }}>
            Paste a full job description below to compare it against your most recent resume.
          </p>

          <form onSubmit={handleSubmit} noValidate>
            <div className="input-group">
              <label htmlFor="job-description">Job Description</label>
              <textarea
                id="job-description"
                className="auth-textarea"
                value={jobDescription}
                onChange={(e) => setJobDescription(e.target.value)}
                placeholder="Paste the full job description here..."
                required
              />
            </div>
            <div style={{ marginTop: '1.5rem' }}>
              <button type="submit" className="auth-button" disabled={isLoading}>
                {isLoading ? 'Analyzing...' : 'Analyze Match'}
              </button>
            </div>
          </form>

          {error && <div className="auth-error">{error}</div>}

          {matchResult && (
            <div className="results-container">
              <h4 className="results-score">
                {Math.round(matchResult.score * 100)}% Match
              </h4>

              <div className="results-columns">
                <div className="results-column results-column-matched">
                  <h5>Keywords You Have</h5>
                  <ul className="results-list">
                    {matchResult.matched_keywords.map((keyword, i) => (
                      <li key={`matched-${i}`} className="results-list-item">
                        {keyword}
                      </li>
                    ))}
                    {matchResult.matched_keywords.length === 0 && (
                      <li className="results-list-item">No strong keywords matched.</li>
                    )}
                  </ul>
                </div>

                <div className="results-column results-column-missing">
                  <h5>Missing Keywords</h5>
                  <ul className="results-list">
                    {matchResult.missing_keywords.map((keyword, i) => (
                      <li key={`missing-${i}`} className="results-list-item">
                        {keyword}
                      </li>
                    ))}
                    {matchResult.missing_keywords.length === 0 && (
                      <li className="results-list-item">No missing keywords found!</li>
                    )}
                  </ul>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default JobMatch;
