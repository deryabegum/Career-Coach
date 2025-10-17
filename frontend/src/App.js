import React, { useState } from 'react';
import './App.css';
import Dashboard from './components/Dashboard';
import Resume from './components/Resume';

function App() {
  const [currentPage, setCurrentPage] = useState('dashboard');

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
        </div>
      </nav>

      <div className="content">
        {currentPage === 'dashboard' && <Dashboard />}
        {currentPage === 'resume' && <Resume />}
      </div>
    </div>
  );
}

export default App;