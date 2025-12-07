// frontend/src/components/Dashboard.js

import React, { useEffect, useState } from 'react';
import './Dashboard.css';

//  Accept setCurrentPage as a prop
const Dashboard = ({ setCurrentPage }) => { 
  const [userStats, setUserStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState('');

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const token = localStorage.getItem('token');

        const res = await fetch('/api/v1/dashboard/summary', {
          headers: token
            ? { Authorization: `Bearer ${token}` }
            : {},
        });

        // Handle expired/invalid token
        if (res.status === 401) {
          let body = {};
          try {
            body = await res.json();
          } catch {
            body = {};
          }

          // Backend expired_token_loader returns { msg: "token_expired" }
          if (body.msg === 'token_expired') {
            if (alive) {
              setErr('Your session has expired. Please log in again.');
            }
          } else {
            if (alive) {
              setErr('You are not authorized. Please log in again.');
            }
          }

          // Clear auth data and send user back to login
          localStorage.removeItem('token');
          localStorage.removeItem('refreshToken');
          if (alive) {
            setLoading(false);
            setCurrentPage('login');
          }
          return;
        }

        if (!res.ok) throw new Error(`HTTP ${res.status}`);

        const data = await res.json();
        if (alive) {
          setUserStats({
            resumeScore: data.lastResumeScore ?? 85,
            interviewsCompleted: data.totals?.interviews ?? 0, 
            jobMatches: data.totals?.matches ?? 0, 
            applicationsSent: 0,
            progressPct: 65,
            name: 'User'
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

        {/* Mock Interviews Card (MADE CLICKABLE) */}
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

        {/* Job Matches Card (MADE CLICKABLE) */}
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
      {/* … your existing JSX … */}
    </div>
  );
};

export default Dashboard;
