import React, { useState } from 'react';
import './App.css';
import Dashboard from './components/Dashboard';
import Resume from './components/Resume';
import MockInterview from './MockInterview'; 
import JobMatch from './components/JobMatch';       
import './Auth.css';
import Login from './components/Login';
import Register from './components/Register';

function App() {
  // Add state for the token
  const [token, setToken] = useState(localStorage.getItem('token'));
  
  //  Default page is 'login' if no token, 'dashboard' if there is one
  const [currentPage, setCurrentPage] = useState(token ? 'dashboard' : 'login');

  //  New logout function
  const handleLogout = () => {
    localStorage.removeItem('token');
    setToken(null);
    setCurrentPage('login');
  };

  //  Updated render function
  const renderContent = () => {
    // If user is not logged in, only show login/register
    if (!token) {
      if (currentPage === 'login') {
        return <Login setToken={setToken} setCurrentPage={setCurrentPage} />;
      }
      if (currentPage === 'register') {
        return <Register setCurrentPage={setCurrentPage} />;
      }
      // Fallback for any weird state
      return <Login setToken={setToken} setCurrentPage={setCurrentPage} />;
    }

    // If user IS logged in, show app pages
    if (currentPage === 'dashboard') return <Dashboard setCurrentPage={setCurrentPage} />; 
    if (currentPage === 'resume') return <Resume />;
    if (currentPage === 'interview') return <MockInterview />;
    if (currentPage === 'job-match') return <JobMatch />;
    
    // Fallback if logged in but page state is weird
    return <Dashboard setCurrentPage={setCurrentPage} />;
  };

  return (
    <div className="App">
      <nav className="navbar">
        <h1 className="app-title">AI Career Coach</h1>
        <div className="nav-links">
          
          {/*  Use conditional rendering for nav links */}
          {token ? (
            <>
              {/* --- LOGGED-IN LINKS --- */}
              <button 
                className={currentPage === 'dashboard' ? 'nav-link active' : 'nav-link'}
                onClick={() => setCurrentPage('dashboard')}
              >
                Dashboard
              </button>
              <button 
                className={currentPage === 'resume' ? 'nav-link active' : 'nav-link'}
                onClick={() => setCurrentPage('resume')}
              >
                Resume
              </button>
              <button 
                className={currentPage === 'interview' ? 'nav-link active' : 'nav-link'}
                onClick={() => setCurrentPage('interview')}
              >
                Mock Interview
              </button>
              <button 
                className={currentPage === 'job-match' ? 'nav-link active' : 'nav-link'}
                onClick={() => setCurrentPage('job-match')}
              >
                Job Match
              </button>
              <button 
                className='nav-link'
                onClick={handleLogout}
              >
                Logout
              </button>
            </>
          ) : (
            <>
              {/* --- LOGGED-OUT LINKS --- */}
              <button 
                className={currentPage === 'login' ? 'nav-link active' : 'nav-link'}
                onClick={() => setCurrentPage('login')}
              >
                Login
              </button>
              <button 
                className={currentPage === 'register' ? 'nav-link active' : 'nav-link'}
                onClick={() => setCurrentPage('register')}
              >
                Register
              </button>
            </>
          )}

        </div>
      </nav>

      <div className="content">
        {renderContent()}
      </div>
    </div>
  );
}

export default App;