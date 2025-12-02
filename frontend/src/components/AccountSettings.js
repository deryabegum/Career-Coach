import React, { useState, useEffect } from 'react';
import './AccountSettings.css';

const AccountSettings = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('••••••••');

  useEffect(() => {
    // Email'i localStorage'dan al veya placeholder göster
    // Gerçek uygulamada backend'den alınacak
    const storedEmail = localStorage.getItem('userEmail') || 'user@example.com';
    setEmail(storedEmail);
  }, []);

  return (
    <div className="account-settings-container">
      <div className="account-settings-card">
        <h2>Account Settings</h2>
        
        <div className="settings-section">
          <div className="input-group">
            <label htmlFor="email">Email</label>
            <input
              id="email"
              className="settings-input"
              type="email"
              value={email}
              readOnly
              disabled
            />
          </div>

          <div className="input-group">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              className="settings-input"
              type="text"
              value={password}
              readOnly
              disabled
            />
            <p className="settings-note">
              Password is hidden for security reasons
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AccountSettings;

