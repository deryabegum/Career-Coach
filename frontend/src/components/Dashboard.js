import React, { useEffect, useState } from 'react';
import './Dashboard.css';

const Dashboard = () => {
  const [userStats, setUserStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState('');

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const res = await fetch('/api/v1/dashboard/summary');
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        if (alive) {
          setUserStats({
            resumeScore: data.resumeScore,
            interviewsCompleted: data.interviewsCompleted,
            jobMatches: data.jobMatches,
            applicationsSent: data.applicationsSent,
            progressPct: data.progressPct ?? 65,
            name: data.name ?? 'User'
          });
          setLoading(false);
        }
      } catch (e) {
        if (alive) { setErr(e.message); setLoading(false); }
      }
    })();
    return () => { alive = false; };
  }, []);

  if (loading) return <div className="dashboard-container"><p>Loading…</p></div>;
  if (err)     return <div className="dashboard-container"><p style={{color:'crimson'}}>Error: {err}</p></div>;

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
        <div className="stat-card">
          <div className="stat-icon">
            {/* (icons unchanged) */}
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M14 2H6C4.9 2 4 2.9 4 4V20C4 21.1 4.89 22 5.99 22H18C19.1 22 20 21.1 20 20V8L14 2Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              <path d="M14 2V8H20" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              <path d="M16 13H8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              <path d="M16 17H8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              <path d="M10 9H8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
          <div className="stat-content">
            <h3>Resume Score</h3>
            <p className="stat-number">{userStats.resumeScore}%</p>
            <p className="stat-label">Above average</p>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon">
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M12 2C13.1 2 14 2.9 14 4C14 5.1 13.1 6 12 6C10.9 6 10 5.1 10 4C10 2.9 10.9 2 12 2ZM21 9V7L15 1H5C3.89 1 3 1.89 3 3V21C3 22.11 3.89 23 5 23H19C20.11 23 21 22.11 21 21V9M19 9H14V4H19V9Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
          <div className="stat-content">
            <h3>Mock Interviews</h3>
            <p className="stat-number">{userStats.interviewsCompleted}</p>
            <p className="stat-label">Completed this month</p>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon">
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M20 6L9 17L4 12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              <path d="M16 6H20V10" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
          <div className="stat-content">
            <h3>Job Matches</h3>
            <p className="stat-number">{userStats.jobMatches}</p>
            <p className="stat-label">New opportunities</p>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon">
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M21 15V19C21 19.5304 20.7893 20.0391 20.4142 20.4142C20.0391 20.7893 19.5304 21 19 21H5C4.46957 21 3.96086 20.7893 3.58579 20.4142C3.21071 20.0391 3 19.5304 3 19V15" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              <path d="M17 8L12 3L7 8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              <path d="M12 3V15" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
          <div className="stat-content">
            <h3>Applications</h3>
            <p className="stat-number">{userStats.applicationsSent}</p>
            <p className="stat-label">Sent this week</p>
          </div>
        </div>
      </div>

      {/* Quick Actions + Recent Activity remain unchanged */}
      {/* … your existing JSX … */}
    </div>
  );
};

export default Dashboard;