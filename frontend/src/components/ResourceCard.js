// frontend/src/components/ResourceCard.js
import React from 'react';
import './ResourceCard.css';

const TYPE_LABELS = {
  article: 'Article',
  resume: 'Resume Resource',
  interview: 'Interview Tips',
};

export default function ResourceCard({ resource }) {
  if (!resource) return null;

  return (
    <div className="resource-card">
      <div className="resource-card-header">
        <span className={`resource-pill resource-pill-${resource.type}`}>
          {TYPE_LABELS[resource.type] || resource.type}
        </span>
      </div>

      <h3 className="resource-card-title">{resource.title}</h3>

      <a
        href={resource.link}
        target="_blank"
        rel="noreferrer"
        className="resource-card-link"
      >
        Open resource
      </a>
    </div>
  );
}
