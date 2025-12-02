import React, { useEffect, useState } from 'react';
import './Dashboard.css';

const Dashboard = ({ setCurrentPage }) => { 
  const [userStats, setUserStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState('');

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        // --- 1. GET THE TOKEN ---
        const token = localStorage.getItem('token');
        if (!token) {
          throw new Error('No token found. Please log in.');
        }

        // --- 2. CREATE HEADERS WITH THE TOKEN ---
        const headers = new Headers();
        headers.append('Authorization', `Bearer ${token}`);

        // --- 3. ADD HEADERS TO THE FETCH REQUEST ---
        const res = await fetch('/api/v1/dashboard/summary', { 
          headers: headers,
          method: 'GET',
          credentials: 'include'
        });
        
        if (!res.ok) {
          let errorMessage = `HTTP ${res.status}`;
          try {
            const errorData = await res.json();
            errorMessage = errorData.message || errorData.error || errorMessage;
          } catch (e) {
            // If response is not JSON, use status text
            errorMessage = res.statusText || errorMessage;
          }
          
          if (res.status === 401) {
            throw new Error('Session expired. Please log in again.');
          }
          throw new Error(errorMessage);
        }
        
        const data = await res.json();
        if (alive) {
          setUserStats({
            // 4. I've updated 'name' to try and get it from your backend data
            name: data.name ?? 'User', 
            resumeScore: data.lastResumeScore ?? 85,
            interviewsCompleted: data.totals?.interviews ?? 0, 
            jobMatches: data.totals?.matches ?? 0, 
            applicationsSent: 0,
            progressPct: 65,
          });
          setLoading(false);
        }
      } catch (e) {
        if (alive) { setErr(e.message); setLoading(false); }
      }
    })();
    return () => { alive = false; };
  }, []); // This empty array is correct, it should only run once.

  if (loading) return <div className="dashboard-container"><p>Loading…</p></div>;
  
  // Update the error display to be more prominent
  if (err) return (
    <div className="auth-container">
      <div className="auth-card">
        <div className="auth-error">{err}</div>
        <p style={{textAlign: 'center', color: 'white', marginTop: '1rem'}}>
          Your session may have expired.
        </p>
      </div>
    </div>
  );

  return (
    <div className="dashboard-container">
      {/* Welcome Section */}
      <div className="welcome-section">
        <h1>Welcome back, {userStats.name}!</h1>
        <p>Your career journey progress: {userStats.progressPct}%</p>
        <div className="progress-bar">
          <div className="progress-fill" style={{ width: `${userStats.progressPct}%` }}></div>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="stats-grid">
        
        {/* Resume Score Card */}
        <div className="stat-card"> 
          <div className="stat-icon">
            {/* ... icon unchanged ... */}
          </div>
          <div className="stat-content">
            <h3>Resume Score</h3>
            <p className="stat-number">{userStats.resumeScore}%</p>
            <p className="stat-label">Above average</p>
          </div>
        </div>

        {/* Mock Interviews Card */}
        <div 
          className="stat-card clickable"
          onClick={() => setCurrentPage('interview')}
        > 
          <div className="stat-icon">
            {/* ... icon unchanged ... */}
          </div>
          <div className="stat-content">
            <h3>Mock Interviews</h3>
            <p className="stat-number">{userStats.interviewsCompleted}</p>
            <p className="stat-label">Completed this month</p>
          </div>
        </div>

        {/* Job Matches Card */}
        <div 
          className="stat-card clickable"
          onClick={() => setCurrentPage('job-match')}
        >
          <div className="stat-icon">
            {/* ... icon unchanged ... */}
          </div>
          <div className="stat-content">
            <h3>Job Matches</h3>
            <p className="stat-number">{userStats.jobMatches}</p>
            <p className="stat-label">New opportunities</p>
          </div>
        </div>

        {/* Applications Card */}
        <div className="stat-card">
          <div className="stat-icon">
            {/* ... icon unchanged ... */}
          </div>
          <div className="stat-content">
            <h3>Applications</h3>
            <p className="stat-number">{userStats.applicationsSent}</p>
            <p className="stat-label">Sent this week</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;