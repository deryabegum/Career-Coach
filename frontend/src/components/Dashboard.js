import React, {
  useEffect,
  useState,
  useCallback,
  useMemo,
  useRef,
  memo,
} from 'react';
import { api } from '../api';
import {
  readDashboardCache,
  writeDashboardCache,
} from '../utils/dashboardCache';
import './Dashboard.css';

function mapSummaryToStats(data) {
  const points = data.points ?? 0;
  const level = data.level ?? 1;
  const currentLevelStartPoints = data.currentLevelStartPoints ?? Math.max(0, (level - 1) * 50);
  const nextLevelPoints = data.nextLevelPoints ?? (level * 50);
  const levelSpan = Math.max(1, nextLevelPoints - currentLevelStartPoints);
  const derivedLevelProgressPct = Math.min(
    100,
    Math.max(0, Math.round(((points - currentLevelStartPoints) / levelSpan) * 100))
  );
  const derivedPointsToNextLevel = Math.max(0, nextLevelPoints - points);

  return {
    name: data.name ?? 'User',
    resumeScore: data.lastResumeScore ?? 0,
    interviewsCompleted: data.totals?.interviews ?? 0,
    jobMatches: data.totals?.matches ?? 0,
    resumeUploads: data.totals?.resumes ?? 0,
    points,
    level,
    nextLevelPoints,
    currentLevelStartPoints,
    levelProgressPct: data.levelProgressPct ?? derivedLevelProgressPct,
    pointsToNextLevel: data.pointsToNextLevel ?? derivedPointsToNextLevel,
    progressPct: data.progressPct ?? 0,
  };
}

function getInitialDashboardState() {
  const raw = readDashboardCache();
  if (!raw) {
    return { userStats: null, loading: true, hadBootstrapCache: false };
  }
  return {
    userStats: mapSummaryToStats(raw),
    loading: false,
    hadBootstrapCache: true,
  };
}

const StatCard = memo(function StatCard({
  title,
  number,
  label,
  onClick,
  clickable,
}) {
  return (
    <div
      className={clickable ? 'stat-card clickable' : 'stat-card'}
      onClick={onClick}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={
        onClick
          ? (e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                onClick();
              }
            }
          : undefined
      }
    >
      <div className="stat-icon" />
      <div className="stat-content">
        <h3>{title}</h3>
        <p className="stat-number">{number}</p>
        <p className="stat-label">{label}</p>
      </div>
    </div>
  );
});

function Dashboard({ setCurrentPage }) {
  const initial = useMemo(() => getInitialDashboardState(), []);
  const hadBootstrapCacheRef = useRef(initial.hadBootstrapCache);

  const [userStats, setUserStats] = useState(initial.userStats);
  const [loading, setLoading] = useState(initial.loading);
  const [err, setErr] = useState('');

  const goInterview = useCallback(
    () => setCurrentPage('interview'),
    [setCurrentPage]
  );
  const goJobMatch = useCallback(
    () => setCurrentPage('job-match'),
    [setCurrentPage]
  );
  const goResume = useCallback(
    () => setCurrentPage('resume'),
    [setCurrentPage]
  );

  useEffect(() => {
    let alive = true;

    (async () => {
      try {
        const token = localStorage.getItem('token');
        if (!token) {
          throw new Error('No token found. Please log in.');
        }

        const headers = new Headers();
        headers.append('Authorization', `Bearer ${token}`);

        const res = await fetch('/api/v1/dashboard/summary', {
          headers,
          method: 'GET',
          credentials: 'include',
        });

        if (res.status === 401 || res.status === 422) {
          let body = {};
          try {
            body = await res.json();
          } catch {
            body = {};
          }

          if (body.msg === 'token_expired' || body.error === 'Token has expired') {
            if (alive) setErr('Your session has expired. Please log in again.');
          } else {
            if (alive) setErr('Your session is invalid. Please log in again.');
          }

          localStorage.removeItem('token');
          localStorage.removeItem('refreshToken');
          window.dispatchEvent(new Event('auth:expired'));
          if (alive) {
            setLoading(false);
            setCurrentPage('login');
          }
          return;
        }

        if (!res.ok) throw new Error(`Server error: ${res.status}`);

        const data = await res.json();
        writeDashboardCache(data);
        if (alive) {
          setUserStats(mapSummaryToStats(data));
          setLoading(false);
        }
      } catch (e) {
        if (e.status === 401) {
          localStorage.removeItem('token');
          localStorage.removeItem('refreshToken');
          window.dispatchEvent(new Event('auth:expired'));
          if (alive) {
            setLoading(false);
            setCurrentPage('login');
          }
          return;
        }
        setLoading(false);
        if (hadBootstrapCacheRef.current) return;
        setErr(e.message || 'Failed to load dashboard');
      }
    })();

    return () => {
      alive = false;
    };
  }, [setCurrentPage]);

  if (loading) {
    return (
      <div className="dashboard-container">
        <p>Loading…</p>
      </div>
    );
  }

  if (err) {
    return (
      <div className="auth-container">
        <div className="auth-card">
          <div className="auth-error">{err}</div>
          <p
            style={{
              textAlign: 'center',
              color: 'white',
              marginTop: '1rem',
            }}
          >
            Your session may have expired.
          </p>
        </div>
      </div>
    );
  }

  if (!userStats) {
    return (
      <div className="dashboard-container">
        <p>Loading…</p>
      </div>
    );
  }

  return (
    <div className="dashboard-container">
      <div className="welcome-section">
        <h1>Welcome back, {userStats.name}!</h1>
        <p>
          Progress to Level {userStats.level + 1}: {userStats.levelProgressPct}%
        </p>
        <p>
          Level {userStats.level} · {userStats.points} points earned
        </p>
        <p>
          {userStats.pointsToNextLevel} more points to reach Level {userStats.level + 1}
        </p>
        <div className="progress-bar">
          <div
            className="progress-fill"
            style={{ width: `${userStats.levelProgressPct}%` }}
          />
        </div>
      </div>

      <div className="stats-grid">
        <StatCard
          title="Resume Score"
          number={`${userStats.resumeScore}%`}
          label="Above average"
        />
        <StatCard
          title="Mock Interviews"
          number={userStats.interviewsCompleted}
          label="Completed this month"
          clickable
          onClick={goInterview}
        />
        <StatCard
          title="Job Matches"
          number={userStats.jobMatches}
          label="New opportunities"
          clickable
          onClick={goJobMatch}
        />
        <StatCard
          title="Resume Uploads"
          number={userStats.resumeUploads}
          label="Uploaded to your account"
          clickable
          onClick={goResume}
        />
      </div>
    </div>
  );
}

export default memo(Dashboard);
