import React, { useState } from 'react';

const Login = ({ setToken, setCurrentPage }) => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    try {
      const response = await fetch('/api/v1/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email.toLowerCase(), password })
      });

      if (!response.ok) {
        const text = await response.text();
        let errMessage = 'Invalid email or password';
        try {
          const errData = JSON.parse(text);
          errMessage = errData.error || errMessage;
        } catch {
          if (text && text.length < 200) errMessage = text;
        }
        throw new Error(errMessage);
      }

      const data = await response.json();
      localStorage.setItem('token', data.accessToken);
      setToken(data.accessToken);
      setCurrentPage('dashboard');

    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div className="auth-container">
      <div className="auth-card">
        <h2>Login</h2>
        <form onSubmit={handleSubmit}>
          <div className="input-group">
            <label htmlFor="email">Email</label>
            <input
              id="email"
              className="auth-input"
              type="email"
              value={email}
              // --- THIS IS THE LINE I FIXED ---
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>
          <div className="input-group">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              className="auth-input"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>
          
          <button type="submit" className="auth-button">Login</button>
          
          {error && <div className="auth-error">{error}</div>}
        </form>
        
        <button 
          onClick={() => setCurrentPage('register')} 
          className="auth-toggle-link"
        >
          Don't have an account? Register
        </button>
      </div>
    </div>
  );
};

export default Login;