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

  const badgeText = (resource.badgeInitials || 'BC').slice(0, 2).toUpperCase();

  return (
    <div className="resource-card">
      <p className="resource-card-type">
        {TYPE_LABELS[resource.type] || resource.type}
      </p>
      <h3 className="resource-card-title">{resource.title}</h3>

      <a
        href={resource.link}
        target="_blank"
        rel="noreferrer"
        className="resource-card-link"
      >
        Open resource
      </a>

      <span className="resource-card-badge" aria-hidden="true">
        {badgeText}
      </span>
    </div>
  );
}
