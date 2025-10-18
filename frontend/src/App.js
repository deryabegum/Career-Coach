// frontend/src/App.js

import React, { useState } from 'react';
import './App.css';
import Dashboard from './components/Dashboard';
import Resume from './components/Resume';
// 💡 Import the new components
import MockInterview from './components/MockInterview'; 
import JobMatch from './components/JobMatch';       

function App() {
  const [currentPage, setCurrentPage] = useState('dashboard');

  // New function to handle conditional rendering
  const renderContent = () => {
    // Pass the setter function down to Dashboard so it can trigger navigation
    if (currentPage === 'dashboard') return <Dashboard setCurrentPage={setCurrentPage} />; 
    if (currentPage === 'resume') return <Resume />;
    if (currentPage === 'interview') return <MockInterview />;
    if (currentPage === 'job-match') return <JobMatch />;
    return <h2>404 Page Not Found</h2>;
  };

  return (
    <div className="App">
      <nav className="navbar">
        <h1 className="app-title">AI Career Coach</h1>
        <div className="nav-links">
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
          {/* 💡 Add the new navigation links to the navbar */}
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
        </div>
      </nav>

      <div className="content">
        {renderContent()}
      </div>
    </div>
  );
}

export default App;