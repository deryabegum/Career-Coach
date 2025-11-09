// frontend/src/api.js
const API_BASE = process.env.REACT_APP_API_URL || ''; 
// when using CRA "proxy" in package.json, keep API_BASE = '' and use relative URLs

async function request(path, options = {}) {
  const token = localStorage.getItem('token');
  const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  const res = await fetch(API_BASE + path, {
    headers,
    ...options,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`HTTP ${res.status}: ${text || res.statusText}`);
  }
  // try JSON, fall back to text
  const ct = res.headers.get('content-type') || '';
  return ct.includes('application/json') ? res.json() : res.text();
}

export const api = {
  getDashboardSummary: () => request('/api/v1/dashboard/summary'), 
  
uploadResume: (file) => { 
    const form = new FormData();
    form.append('file', file);
    const token = localStorage.getItem('token');
    const headers = {};
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    return fetch(API_BASE + '/api/resume/upload', { // Use correct path
      method: 'POST',
      headers,
      body: form 
    }).then(async r => {
      if (!r.ok) throw new Error(`HTTP ${r.status}: ${r.statusText}`);
      return r.json();
    });
  },
  
  register: (data) => request('/api/register', { method: 'POST', body: JSON.stringify(data) }),
  login: (data) => request('/api/login', { method: 'POST', body: JSON.stringify(data) }),
  
  // Mock Interview endpoints
  createInterviewSession: (data) => request('/api/v1/mock-interview/sessions', { 
    method: 'POST', 
    body: JSON.stringify(data) 
  }),
  getInterviewFeedback: (data) => request('/api/v1/mock-interview/feedback', { 
    method: 'POST', 
    body: JSON.stringify(data) 
  }),
  submitInterview: (data) => request('/api/v1/mock-interview/submit', { 
    method: 'POST', 
    body: JSON.stringify(data) 
  }),
  getUserSessions: () => request('/api/v1/mock-interview/sessions'),
};