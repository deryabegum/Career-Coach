// frontend/src/components/CareerHub.js
import React, { useEffect, useState } from 'react';
import { api } from '../api';          // <-- FIXED: named import
import ResourceCard from './ResourceCard';
import './CareerHub.css';

const FILTER_OPTIONS = [
  { value: 'all', label: 'All types' },
  { value: 'article', label: 'Articles' },
  { value: 'resume', label: 'Resume' },
  { value: 'interview', label: 'Interview Tips' },
];

export default function CareerHub() {
  const [allResources, setAllResources] = useState([]);
  const [recommended, setRecommended] = useState([]);
  const [filter, setFilter] = useState('all');
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState('');
  const [scores, setScores] = useState({
    resumeScore: 0,
    interviewAverage: 0,
  });

  useEffect(() => {
    let alive = true;

    (async () => {
      try {
        setLoading(true);
        const [allResp, recResp] = await Promise.all([
          api.getAllResources(),
          api.getRecommendedResources(),
        ]);

        if (!alive) return;

        setAllResources(allResp.resources || []);
        setRecommended(recResp.resources || []);
        setScores({
          resumeScore: recResp.resumeScore ?? 0,
          interviewAverage: recResp.interviewAverage ?? 0,
        });
      } catch (e) {
        if (!alive) return;
        setErr(e.message || 'Failed to load career resources.');
      } finally {
        if (alive) setLoading(false);
      }
    })();

    return () => {
      alive = false;
    };
  }, []);

  const filteredResources = allResources.filter((r) =>
    filter === 'all' ? true : r.type === filter
  );

  if (loading) {
    return (
      <div className="careerhub-container">
        <p className="careerhub-status">Loading career resources...</p>
      </div>
    );
  }

  if (err) {
    return (
      <div className="careerhub-container">
        <p className="careerhub-error">{err}</p>
      </div>
    );
  }

  return (
    <div className="careerhub-container">
      <header className="careerhub-header">
        <h1>Career Resource Hub</h1>
        <p>
          Explore curated articles, resume guides, and interview tips based on
          your current progress.
        </p>
      </header>

      <section className="careerhub-scores">
        <div className="score-card">
          <h3>Latest Resume Score</h3>
          <p className="score-number">{scores.resumeScore}</p>
        </div>
        <div className="score-card">
          <h3>Interview Average</h3>
          <p className="score-number">{scores.interviewAverage}</p>
        </div>
      </section>

      <section className="careerhub-section">
        <div className="careerhub-section-header">
          <h2>Recommended for You</h2>
        </div>
        {recommended.length === 0 ? (
          <p className="careerhub-status">
            No specific recommendations yet. Upload a resume or try a mock
            interview to get personalized tips.
          </p>
        ) : (
          <div className="careerhub-grid">
            {recommended.map((res) => (
              <ResourceCard key={res.id} resource={res} />
            ))}
          </div>
        )}
      </section>

      <section className="careerhub-section">
        <div className="careerhub-section-header">
          <h2>All Resources</h2>
          <select
            className="careerhub-filter"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
          >
            {FILTER_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
        {filteredResources.length === 0 ? (
          <p className="careerhub-status">No resources match this filter.</p>
        ) : (
          <div className="careerhub-grid">
            {filteredResources.map((res) => (
              <ResourceCard key={res.id} resource={res} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
