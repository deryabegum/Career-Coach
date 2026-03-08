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
        // 1. Get token
        const token = localStorage.getItem('token');
        if (!token) {
          throw new Error('No token found. Please log in.');
        }

        // 2. Build headers with Authorization
        const headers = new Headers();
        headers.append('Authorization', `Bearer ${token}`);

        // 3. Request dashboard summary with headers
        const res = await fetch('/api/v1/dashboard/summary', { 
          headers,
          method: 'GET',
          credentials: 'include',
        });

        // 4. Handle 401 / session expired with auto-logout
        if (res.status === 401) {
          let body = {};
          try {
            body = await res.json();
          } catch {
            body = {};
          }

          if (body.msg === 'token_expired') {
            if (alive) {
              setErr('Your session has expired. Please log in again.');
            }
          } else {
            if (alive) {
              setErr('You are not authorized. Please log in again.');
            }
          }

          localStorage.removeItem('token');
          localStorage.removeItem('refreshToken');

          if (alive) {
            setLoading(false);
            setCurrentPage('login');
          }
          return;
        }

        // 5. Handle other non-OK errors
        if (!res.ok) {
          let errorMessage = `HTTP ${res.status}`;
          try {
            const errorData = await res.json();
            errorMessage = errorData.message || errorData.error || errorMessage;
          } catch {
            errorMessage = res.statusText || errorMessage;
          }
          throw new Error(errorMessage);
        }

        // 6. Success: parse data and populate stats
        const data = await res.json();
        if (alive) {
          setUserStats({
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
        if (alive) { 
          setErr(e.message); 
          setLoading(false); 
        }
      }
    })();
    return () => { alive = false; };
  }, [setCurrentPage]);

  if (loading) return <div className="dashboard-container"><p>Loading…</p></div>;
  
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
        <div className="stat-card stat-card--orange">
          <div className="stat-icon">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#FF8C00" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <polyline points="14 2 14 8 20 8"/>
              <line x1="16" y1="13" x2="8" y2="13"/>
              <line x1="16" y1="17" x2="8" y2="17"/>
              <polyline points="10 9 9 9 8 9"/>
            </svg>
          </div>
          <div className="stat-content">
            <h3>Resume Score</h3>
            <p className="stat-number">{userStats.resumeScore}%</p>
            <p className="stat-label">Above average</p>
          </div>
        </div>

        {/* Mock Interviews Card */}
        <div
          className="stat-card stat-card--blue clickable"
          onClick={() => setCurrentPage('interview')}
        >
          <div className="stat-icon">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#4A9EFF" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
            </svg>
          </div>
          <div className="stat-content">
            <h3>Mock Interviews</h3>
            <p className="stat-number">{userStats.interviewsCompleted}</p>
            <p className="stat-label">Completed this month</p>
          </div>
        </div>

        {/* Job Matches Card */}
        <div
          className="stat-card stat-card--green clickable"
          onClick={() => setCurrentPage('job-match')}
        >
          <div className="stat-icon">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#4ADE80" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="2" y="7" width="20" height="14" rx="2" ry="2"/>
              <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/>
            </svg>
          </div>
          <div className="stat-content">
            <h3>Job Matches</h3>
            <p className="stat-number">{userStats.jobMatches}</p>
            <p className="stat-label">New opportunities</p>
          </div>
        </div>

        {/* Applications Card */}
        <div className="stat-card stat-card--purple">
          <div className="stat-icon">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#A78BFA" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="22" y1="2" x2="11" y2="13"/>
              <polygon points="22 2 15 22 11 13 2 9 22 2"/>
            </svg>
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
