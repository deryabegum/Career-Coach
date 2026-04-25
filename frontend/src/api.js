// frontend/src/api.js
const API_BASE = process.env.REACT_APP_API_URL || '';
// when using CRA "proxy" in package.json, keep API_BASE = '' and use relative URLs

async function request(path, options = {}) {
  const token = localStorage.getItem('token');

  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(API_BASE + path, {
    headers,
    ...options,
  });

  if (!res.ok) {
    const text = await res.text();
    let message = res.statusText || `Request failed (${res.status})`;
    try {
      const data = JSON.parse(text);
      message = data.error || data.message || message;
    } catch {
      const trimmed = (text || '').trim();
      if (trimmed && !trimmed.startsWith('<') && trimmed.length < 300) {
        message = trimmed;
      } else if (res.status === 404) {
        message = 'This feature is temporarily unavailable. Please refresh and try again.';
      } else if (res.status >= 500) {
        message = 'The server hit an error while processing your request.';
      }
    }

    if (res.status === 401 || res.status === 422) {
      localStorage.removeItem('token');
      window.dispatchEvent(new CustomEvent('auth:expired', { detail: { status: res.status } }));
    }

    const err = new Error(message);
    err.status = res.status;
    throw err;
  }

  // Try JSON, fall back to text
  const ct = res.headers.get('content-type') || '';
  return ct.includes('application/json') ? res.json() : res.text();
}

export const api = {
  // Dashboard
  getDashboardSummary: () => request('/api/v1/dashboard/summary'),

  // Resume upload
  uploadResume: (file) => {
    const form = new FormData();
    form.append('file', file);

    const token = localStorage.getItem('token');
    const headers = {};
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    return fetch(API_BASE + '/api/resume/upload', {
      method: 'POST',
      headers,
      body: form,
    }).then(async (r) => {
      if (!r.ok) throw new Error(`HTTP ${r.status}: ${r.statusText}`);
      return r.json();
    });
  },
  listResumes: () => request('/api/resume'),
  getResume: (resumeId) => request(`/api/resume/${resumeId}`),
  updateResume: (resumeId, data) =>
    request(`/api/resume/${resumeId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),
  deleteResume: (resumeId) =>
    request(`/api/resume/${resumeId}`, {
      method: 'DELETE',
    }),
  updateResumeFields: (resumeId, extractedData) =>
    request(`/api/resume/${resumeId}/fields`, {
      method: 'PATCH',
      body: JSON.stringify({ extracted_data: extractedData }),
    }),

  // Auth
  register: (data) =>
    request('/api/register', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  login: (data) =>
    request('/api/login', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  // Mock Interview endpoints
  createInterviewSession: (data) =>
    request('/api/v1/mock-interview/sessions', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  getInterviewFeedback: (data) =>
    request('/api/v1/mock-interview/feedback', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  submitInterview: (data) =>
    request('/api/v1/mock-interview/submit', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  getUserSessions: () => request('/api/v1/mock-interview/sessions'),
  matchKeywords: (data) =>
    request('/api/keywords/match', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  getNewGradJobs: ({ limit = 40, category = 'all', search = '' } = {}) =>
    request(
      `/api/keywords/jobs/new-grad?limit=${encodeURIComponent(limit)}&category=${encodeURIComponent(category)}&search=${encodeURIComponent(search)}`
    ),
  getJobDetails: (simplifyUrl) =>
    request(`/api/keywords/jobs/details?simplify_url=${encodeURIComponent(simplifyUrl)}`),

  getInterviewSession: (sessionId) =>
    request(`/api/v1/mock-interview/sessions/${sessionId}`),

  // Job Applications endpoints
  getApplications: () => request('/api/v1/applications/'),
  createApplication: (data) =>
    request('/api/v1/applications/', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  updateApplication: (id, data) =>
    request(`/api/v1/applications/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),
  deleteApplication: (id) =>
    request(`/api/v1/applications/${id}`, {
      method: 'DELETE',
    }),

  // Career Resources endpoints
  getAllResources: () => request('/api/v1/resources'),

  // IMPORTANT: do NOT send Authorization header here
  getRecommendedResources: async () => {
    const res = await fetch(API_BASE + '/api/v1/resources/recommended');
    if (!res.ok) {
      const text = await res.text();
      throw new Error(`HTTP ${res.status}: ${text || res.statusText}`);
    }
    const ct = res.headers.get('content-type') || '';
    return ct.includes('application/json') ? res.json() : res.text();
  },
};
