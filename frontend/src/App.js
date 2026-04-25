import React, { useEffect, useState } from 'react';
import React, { useState, useMemo, useCallback } from 'react';
import './App.css';
import { clearDashboardCache } from './utils/dashboardCache';
import Dashboard from './components/Dashboard';
import Resume from './components/Resume';
import MockInterview from './MockInterview';
import JobMatch from './components/JobMatch';
import './Auth.css';
import Login from './components/Login';
import Register from './components/Register';
import AccountSettings from './components/AccountSettings';
import CareerHub from './components/CareerHub';
import Applications from './components/Applications';

function App() {
  // Add state for the token
  const [token, setToken] = useState(localStorage.getItem('token'));

  // Default page is 'login' if no token, 'dashboard' if there is one
  const [currentPage, setCurrentPage] = useState(token ? 'dashboard' : 'login');

  const handleLogout = useCallback(() => {
    clearDashboardCache();
    localStorage.removeItem('token');
    localStorage.removeItem('refreshToken');
    setToken(null);
    setCurrentPage('login');
  }, []);

  useEffect(() => {
    const handleAuthExpired = () => {
      localStorage.removeItem('token');
      localStorage.removeItem('refreshToken');
      setToken(null);
      setCurrentPage('login');
    };

    window.addEventListener('auth:expired', handleAuthExpired);
    return () => window.removeEventListener('auth:expired', handleAuthExpired);
  }, []);

  const renderContent = () => {
    // If user is not logged in, only show login/register
  const mainContent = useMemo(() => {
    if (!token) {
      if (currentPage === 'login') {
        return <Login setToken={setToken} setCurrentPage={setCurrentPage} />;
      }
      if (currentPage === 'register') {
        return <Register setCurrentPage={setCurrentPage} />;
      }
      return <Login setToken={setToken} setCurrentPage={setCurrentPage} />;
    }

    if (currentPage === 'dashboard') {
      return <Dashboard setCurrentPage={setCurrentPage} />;
    }
    if (currentPage === 'resume') return <Resume />;
    if (currentPage === 'interview') return <MockInterview />;
    if (currentPage === 'job-match') return <JobMatch />;
    if (currentPage === 'career-hub') return <CareerHub />;
    if (currentPage === 'applications') return <Applications />;
    if (currentPage === 'account-settings') return <AccountSettings />;

    return <Dashboard setCurrentPage={setCurrentPage} />;
  }, [token, currentPage]);

  return (
    <div className="App">
      <nav className="navbar">
        <h1 className="app-title">AI Career Coach</h1>
        <div className="nav-links">
          {/* Use conditional rendering for nav links */}
          {token ? (
            <>
              {/* --- LOGGED-IN LINKS --- */}
              <button
                className={
                  currentPage === 'dashboard' ? 'nav-link active' : 'nav-link'
                }
                onClick={() => setCurrentPage('dashboard')}
              >
                Dashboard
              </button>
              <button
                className={
                  currentPage === 'resume' ? 'nav-link active' : 'nav-link'
                }
                onClick={() => setCurrentPage('resume')}
              >
                Resume
              </button>
              <button
                className={
                  currentPage === 'interview' ? 'nav-link active' : 'nav-link'
                }
                onClick={() => setCurrentPage('interview')}
              >
                Mock Interview
              </button>
              <button
                className={
                  currentPage === 'job-match' ? 'nav-link active' : 'nav-link'
                }
                onClick={() => setCurrentPage('job-match')}
              >
                Job Match
              </button>
              <button
                className={
                  currentPage === 'career-hub' ? 'nav-link active' : 'nav-link'
                }
                onClick={() => setCurrentPage('career-hub')}
              >
                Career Hub
              </button>
              <button
                className={
                  currentPage === 'applications' ? 'nav-link active' : 'nav-link'
                }
                onClick={() => setCurrentPage('applications')}
              >
                Applications
              </button>
              <button
                className={
                  currentPage === 'account-settings'
                    ? 'nav-link active'
                    : 'nav-link'
                }
                onClick={() => setCurrentPage('account-settings')}
              >
                Account Settings
              </button>
              <button className="nav-link" onClick={handleLogout}>
                Logout
              </button>
            </>
          ) : (
            <>
              {/* --- LOGGED-OUT LINKS --- */}
              <button
                className={
                  currentPage === 'login' ? 'nav-link active' : 'nav-link'
                }
                onClick={() => setCurrentPage('login')}
              >
                Login
              </button>
              <button
                className={
                  currentPage === 'register' ? 'nav-link active' : 'nav-link'
                }
                onClick={() => setCurrentPage('register')}
              >
                Register
              </button>
            </>
          )}
        </div>
      </nav>

      <div className="content">{mainContent}</div>
    </div>
  );
}

export default App;
