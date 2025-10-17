// frontend/src/api.js
const API_BASE = process.env.REACT_APP_API_URL || ''; 
// when using CRA "proxy" in package.json, keep API_BASE = '' and use relative URLs

async function request(path, options = {}) {
  const res = await fetch(API_BASE + path, {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
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
    return fetch(API_BASE + '/api/resume/upload', { // Use correct path
      method: 'POST', 
      body: form 
    }).then(async r => {
      if (!r.ok) throw new Error(`HTTP ${r.status}: ${r.statusText}`);
      return r.json();
    });
  },
  
  register: (data) => request('/api/register', { method: 'POST', body: JSON.stringify(data) }),
  login: (data) => request('/api/login', { method: 'POST', body: JSON.stringify(data) }),
};