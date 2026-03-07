import React, { useState } from 'react';

const Register = ({ setCurrentPage }) => {
  const [name, setName] = useState(''); // <-- 1. Add name state
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    try {
      const response = await fetch('/api/v1/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        // 2. Add name to the request body
        body: JSON.stringify({ name, email: email.toLowerCase(), password })
      });

      if (!response.ok) {
        const text = await response.text();
        let errMessage = 'Registration failed';
        try {
          const errData = JSON.parse(text);
          errMessage = errData.error || errMessage;
        } catch {
          if (text && text.length < 200) errMessage = text;
        }
        throw new Error(errMessage);
      }

      setSuccess('Registration successful! Please log in.');
      
      setTimeout(() => {
        setCurrentPage('login');
      }, 2000);

    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div className="auth-container">
      <div className="auth-card">
        <h2>Register</h2>
        
        <form onSubmit={handleSubmit} noValidate>
          
          {/* --- 3. Add the Name Input Field --- */}
          <div className="input-group">
            <label htmlFor="name">Name</label>
            <input
              id="name"
              className="auth-input"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              autoComplete="off"
            />
          </div>
          {/* --- End of new field --- */}

          <div className="input-group">
            <label htmlFor="email">Email</label>
            <input
              id="email"
              className="auth-input"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="off"
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
              autoComplete="off"
            />
          </div>
          
          <button type="submit" className="auth-button">Register</button>

          {error && <div className="auth-error">{error}</div>}
          {success && <div className="auth-success">{success}</div>}
        </form>
        
        <button 
          onClick={() => setCurrentPage('login')} 
          className="auth-toggle-link"
        >
          Already have an account? Login
        </button>
      </div>
    </div>
  );
};

export default Register;