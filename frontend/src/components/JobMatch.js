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
      // Get the JWT token from storage
      const token = localStorage.getItem('token'); 
      if (!token) {
        throw new Error('You are not logged in. Please log in to use this feature.');
      }

      // This API route matches the backend blueprint
      const response = await fetch('/api/keywords/match', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}` // Send the auth token
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
    <div className="page-container" style={{ maxWidth: '800px', margin: 'auto' }}>
      <h2>Job Keyword Match</h2>
      <p>Paste a job description below to compare it against your most recent resume.</p>

      {/* --- Form for Input --- */}
      <form onSubmit={handleSubmit} style={{ marginTop: '1rem' }}>
        <textarea
          rows="15"
          value={jobDescription}
          onChange={(e) => setJobDescription(e.target.value)}
          placeholder="Paste the full job description here..."
          required
          style={{ width: '100%', padding: '10px', fontSize: '1rem', borderRadius: '5px' }}
        />
        <div style={{ marginTop: '1rem' }}>
          <button type="submit" disabled={isLoading} style={{ padding: '10px 20px', fontSize: '1rem' }}>
            {isLoading ? 'Analyzing...' : 'Analyze Match'}
          </button>
        </div>
      </form>

      {/* --- Error Display --- */}
      {error && <div style={{ color: 'red', marginTop: '1rem', fontWeight: 'bold' }}>{error}</div>}

      {/* --- Results Display --- */}
      {matchResult && (
        <div className="results-container" style={{ marginTop: '2rem' }}>
          <h3>Analysis Complete</h3>
          <h4 style={{ color: '#007bff', fontSize: '1.5rem', marginBottom: '1rem' }}>
            {/* Format score as a percentage */}
            Match Score: {Math.round(matchResult.score * 100)}%
          </h4>
          
          <div style={{ display: 'flex', gap: '2rem' }}>
            {/* Matched Keywords */}
            <div style={{ flex: 1 }}>
              <h5 style={{ borderBottom: '2px solid #28a745', paddingBottom: '5px' }}>
                Keywords You Have
              </h5>
              <ul style={{ listStyleType: 'none', paddingLeft: 0 }}>
                {matchResult.matched_keywords.map((keyword, i) => (
                  <li key={`matched-${i}`} style={{ background: '#eaf6ec', padding: '5px', marginBottom: '5px', borderRadius: '3px' }}>
                    {keyword}
                  </li>
                ))}
              </ul>
            </div>

            {/* Missing Keywords */}
            <div style={{ flex: 1 }}>
              <h5 style={{ borderBottom: '2px solid #dc3545', paddingBottom: '5px' }}>
                Missing Keywords
              </h5>
              <ul style={{ listStyleType: 'none', paddingLeft: 0 }}>
                {matchResult.missing_keywords.map((keyword, i) => (
                  <li key={`missing-${i}`} style={{ background: '#fbeeee', padding: '5px', marginBottom: '5px', borderRadius: '3px' }}>
                    {keyword}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default JobMatch;