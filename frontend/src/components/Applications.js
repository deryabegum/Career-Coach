import React, { useEffect, useMemo, useState } from 'react';
import { api } from '../api';
import './Applications.css';

const STAGES = [
  { value: 'applied', label: 'Applied' },
  { value: 'phone_screen', label: 'Phone Screen' },
  { value: 'interview', label: 'Interview' },
  { value: 'offer', label: 'Offer' },
  { value: 'rejected', label: 'Rejected' },
];

const STAGE_COLORS = {
  applied: '#6366f1',
  phone_screen: '#fbbf24',
  interview: '#FF8C00',
  offer: '#22c55e',
  rejected: '#ef4444',
};

const EMPTY_FORM = {
  company_name: '',
  applied_date: '',
  stage: 'applied',
  field: '',
};

export default function Applications() {
  const [apps, setApps] = useState([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [formErr, setFormErr] = useState('');
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    let alive = true;

    (async () => {
      try {
        setLoading(true);
        const data = await api.getApplications();
        if (!alive) return;
        setApps(data.applications || []);
      } catch (e) {
        if (!alive) return;
        setErr(e.message || 'Failed to load applications.');
      } finally {
        if (alive) setLoading(false);
      }
    })();

    return () => {
      alive = false;
    };
  }, []);

  const handleFormChange = (e) => {
    setForm((prev) => ({
      ...prev,
      [e.target.name]: e.target.value,
    }));
  };

  const handleAdd = async (e) => {
    e.preventDefault();
    setFormErr('');

    if (!form.company_name.trim()) {
      setFormErr('Company name is required.');
      return;
    }

    if (!form.applied_date) {
      setFormErr('Application date is required.');
      return;
    }

    setSaving(true);

    try {
      const res = await api.createApplication(form);

      setApps((prev) => [
        { id: res.id, ...form, created_at: new Date().toISOString() },
        ...prev,
      ]);

      setForm(EMPTY_FORM);
      setShowForm(false);
    } catch (e) {
      setFormErr(e.message || 'Failed to save.');
    } finally {
      setSaving(false);
    }
  };

  const handleStageChange = async (app, newStage) => {
    try {
      await api.updateApplication(app.id, { ...app, stage: newStage });
      setApps((prev) =>
        prev.map((a) => (a.id === app.id ? { ...a, stage: newStage } : a))
      );
    } catch (e) {
      alert('Could not update stage: ' + e.message);
    }
  };

  const handleDelete = async (id) => {
    try {
      await api.deleteApplication(id);
      setApps((prev) => prev.filter((a) => a.id !== id));
    } catch (e) {
      alert('Could not delete: ' + e.message);
    }
  };

  const filteredApps = useMemo(() => {
    const term = searchTerm.trim().toLowerCase();

    if (!term) return apps;

    return apps.filter((app) => {
      const stageLabel =
        STAGES.find((s) => s.value === app.stage)?.label.toLowerCase() || '';

      return (
        (app.company_name || '').toLowerCase().includes(term) ||
        (app.field || '').toLowerCase().includes(term) ||
        stageLabel.includes(term)
      );
    });
  }, [apps, searchTerm]);

  return (
    <div className="apps-container">
      <header className="apps-header">
        <div>
          <h1>My Applications</h1>
          <p>Track every job application in one place.</p>
        </div>
        <button
          className="apps-add-btn"
          onClick={() => {
            setShowForm((v) => !v);
            setFormErr('');
          }}
        >
          {showForm ? '✕ Cancel' : '+ New Application'}
        </button>
      </header>

      <div className="apps-search-bar">
        <input
          type="text"
          placeholder="Search by company, field, or stage..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="apps-search-input"
        />
      </div>

      {showForm && (
        <form className="apps-form" onSubmit={handleAdd}>
          <div className="apps-form-grid">
            <div className="apps-field">
              <label>Company Name *</label>
              <input
                name="company_name"
                value={form.company_name}
                onChange={handleFormChange}
                placeholder="e.g. Google"
              />
            </div>

            <div className="apps-field">
              <label>Date Applied *</label>
              <input
                type="date"
                name="applied_date"
                value={form.applied_date}
                onChange={handleFormChange}
              />
            </div>

            <div className="apps-field">
              <label>Stage</label>
              <select
                name="stage"
                value={form.stage}
                onChange={handleFormChange}
              >
                {STAGES.map((s) => (
                  <option key={s.value} value={s.value}>
                    {s.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="apps-field">
              <label>Field / Area</label>
              <input
                name="field"
                value={form.field}
                onChange={handleFormChange}
                placeholder="e.g. Software Engineering"
              />
            </div>
          </div>

          {formErr && <p className="apps-form-err">{formErr}</p>}

          <button type="submit" className="apps-submit-btn" disabled={saving}>
            {saving ? 'Saving…' : 'Save Application'}
          </button>
        </form>
      )}

      {loading && <p className="apps-status">Loading applications…</p>}
      {err && <p className="apps-error">{err}</p>}

      {!loading && !err && apps.length === 0 && (
        <div className="apps-empty">
          <p>No applications yet. Add your first one above!</p>
        </div>
      )}

      {!loading && !err && apps.length > 0 && filteredApps.length === 0 && (
        <div className="apps-empty">
          <p>No applications match your search.</p>
        </div>
      )}

      {!loading && filteredApps.length > 0 && (
        <div className="apps-groups">
          {STAGES.map((stage) => {
            const group = filteredApps.filter((a) => a.stage === stage.value);
            if (group.length === 0) return null;

            return (
              <div key={stage.value} className="apps-group">
                <div className="apps-group-header">
                  <span
                    className="apps-group-dot"
                    style={{ background: STAGE_COLORS[stage.value] }}
                  />
                  <h2 className="apps-group-title">{stage.label}</h2>
                  <span className="apps-group-count">{group.length}</span>
                </div>

                <div className="apps-grid">
                  {group.map((app) => (
                    <div key={app.id} className="apps-card">
                      <div className="apps-card-top">
                        <h3 className="apps-company">{app.company_name}</h3>
                        <button
                          className="apps-delete-btn"
                          onClick={() => handleDelete(app.id)}
                          title="Delete"
                        >
                          ✕
                        </button>
                      </div>

                      {app.field && (
                        <span className="apps-field-badge">{app.field}</span>
                      )}

                      <div className="apps-card-meta">
                        <span className="apps-date">
                          {new Date(app.applied_date).toLocaleDateString(
                            'en-US',
                            {
                              year: 'numeric',
                              month: 'short',
                              day: 'numeric',
                            }
                          )}
                        </span>
                      </div>

                      <div className="apps-stage-row">
                        <select
                          className="apps-stage-select"
                          value={app.stage}
                          onChange={(e) =>
                            handleStageChange(app, e.target.value)
                          }
                        >
                          {STAGES.map((s) => (
                            <option key={s.value} value={s.value}>
                              {s.label}
                            </option>
                          ))}
                        </select>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}