import React, { useState } from 'react';

const JobMatch = () => {
  const [jobDescription, setJobDescription] = useState('');
  const [matchResult, setMatchResult] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');
    setMatchResult(null);

    try {
      const token = localStorage.getItem('token'); 
      if (!token) {
        throw new Error('You are not logged in. Please log in to use this feature.');
      }

      const response = await fetch('/api/keywords/match', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ job_description: jobDescription })
      });

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.message || 'Failed to analyze job description.');
      }

      const data = await response.json();
      setMatchResult(data);

    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="auth-container">
      <div className="auth-card" style={{ maxWidth: '800px' }}>
        <h2>Job Keyword Match</h2>
        <p style={{ color: 'rgba(255, 255, 255, 0.6)', marginTop: '-1rem', marginBottom: '2rem', textAlign: 'center' }}>
          Paste a job description below to compare it against your most recent resume.
        </p>

        {/* --- Form for Input --- */}
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

        {/* --- Error Display --- */}
        {error && <div className="auth-error">{error}</div>}

        {/* --- Results Display --- */}
        {matchResult && (
          <div className="results-container">
            <h4 className="results-score">
              {Math.round(matchResult.score * 100)}% Match
            </h4>
            
            <div className="results-columns">
              {/* Matched Keywords */}
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

              {/* Missing Keywords */}
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
  );
};

export default JobMatch;