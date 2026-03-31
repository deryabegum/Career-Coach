import React, { useCallback, useEffect, useState } from 'react';
import { api } from '../api';
import './Resume.css';

const MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024;
const MAX_FILE_SIZE_MB = 10;

const formatBytes = (bytes) => {
  if (!bytes) return 'Unknown size';
  return `${(bytes / 1024).toFixed(2)} KB`;
};

const formatDate = (value) => {
  if (!value) return 'Unknown date';
  return new Date(value).toLocaleString();
};

const Resume = () => {
  const [selectedFile, setSelectedFile] = useState(null);
  const [resumes, setResumes] = useState([]);
  const [activeResumeId, setActiveResumeId] = useState(null);
  const [resumeText, setResumeText] = useState('');
  const [activeResume, setActiveResume] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [loadingResumes, setLoadingResumes] = useState(true);
  const [fileError, setFileError] = useState('');
  const [uploadError, setUploadError] = useState('');
  const [saveMessage, setSaveMessage] = useState('');

  const allowedMimeTypes = [
    'application/pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
  ];
  const allowedExtensions = ['pdf', 'docx'];

  const loadResumes = useCallback(async (preferredResumeId = null) => {
    setLoadingResumes(true);
    try {
      const data = await api.listResumes();
      const items = data.resumes || [];
      setResumes(items);

      const targetId = preferredResumeId ?? activeResumeId ?? items[0]?.id ?? null;
      if (!targetId) {
        setActiveResumeId(null);
        setActiveResume(null);
        setResumeText('');
        return;
      }

      const selected = items.find((item) => item.id === targetId) || items[0];
      if (!selected) return;

      setActiveResumeId(selected.id);
      const detail = await api.getResume(selected.id);
      setActiveResume(detail);
      setResumeText(detail.resumeText || '');
    } catch (error) {
      setUploadError(error.message || 'Could not load resumes.');
    } finally {
      setLoadingResumes(false);
    }
  }, [activeResumeId]);

  useEffect(() => {
    loadResumes();
  }, [loadResumes]);


  const handleFileSelect = (event) => {
    const file = event.target.files[0];
    setFileError('');
    setUploadError('');
    setSaveMessage('');
    event.target.value = '';

    if (!file) return;

    const ext = file.name.split('.').pop()?.toLowerCase();
    if (!allowedExtensions.includes(ext) || !allowedMimeTypes.includes(file.type)) {
      setFileError('Please select a PDF or DOCX file.');
      setSelectedFile(null);
      return;
    }

    if (file.size === 0) {
      setFileError('File is empty. Please select a non-empty file.');
      setSelectedFile(null);
      return;
    }

    if (file.size > MAX_FILE_SIZE_BYTES) {
      setFileError(`File too large. Maximum size is ${MAX_FILE_SIZE_MB} MB.`);
      setSelectedFile(null);
      return;
    }

    setSelectedFile(file);
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      setUploadError('Please select a file first.');
      return;
    }

    setUploading(true);
    setUploadError('');
    setSaveMessage('');

    try {
      const data = await api.uploadResume(selectedFile);
      setSelectedFile(null);
      await loadResumes(data.resume_db_id);
      setSaveMessage(`Uploaded ${data.filename} with a resume score of ${data.resume_score}.`);
    } catch (error) {
      setUploadError(error.message || 'Upload failed.');
    } finally {
      setUploading(false);
    }
  };

  const handleSelectResume = async (resumeId) => {
    setUploadError('');
    setSaveMessage('');
    setActiveResumeId(resumeId);
    try {
      const detail = await api.getResume(resumeId);
      setActiveResume(detail);
      setResumeText(detail.resumeText || '');
    } catch (error) {
      setUploadError(error.message || 'Could not load this resume.');
    }
  };

  const handleSaveResumeText = async () => {
    if (!activeResumeId) return;
    setSaving(true);
    setUploadError('');
    setSaveMessage('');
    try {
      const updated = await api.updateResume(activeResumeId, { resumeText });
      setActiveResume(updated);
      setResumeText(updated.resumeText || '');
      setResumes((current) =>
        current.map((item) =>
          item.id === updated.id
            ? { ...item, resumeText: updated.resumeText, resumeScore: updated.resumeScore, resumeSummary: updated.resumeSummary }
            : item
        )
      );
      setSaveMessage(`Saved changes. New resume score: ${updated.resumeScore}.`);
    } catch (error) {
      setUploadError(error.message || 'Could not save resume text.');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (resumeId) => {
    try {
      await api.deleteResume(resumeId);
      const remaining = resumes.filter((item) => item.id !== resumeId);
      setResumes(remaining);
      if (activeResumeId === resumeId) {
        const nextResumeId = remaining[0]?.id ?? null;
        setActiveResumeId(nextResumeId);
        if (nextResumeId) {
          const detail = await api.getResume(nextResumeId);
          setActiveResume(detail);
          setResumeText(detail.resumeText || '');
        } else {
          setActiveResume(null);
          setResumeText('');
        }
      }
      setSaveMessage('Resume deleted.');
    } catch (error) {
      setUploadError(error.message || 'Could not delete resume.');
    }
  };

  return (
    <div className="resume-container">
      <h2>Resume Management</h2>
      <div className="resume-grid resume-grid-wide">
        <div className="upload-section">
          <h3>Upload New Resume</h3>
          <div className="upload-box">
            <input
              type="file"
              accept=".pdf, .docx, application/pdf, application/vnd.openxmlformats-officedocument.wordprocessingml.document"
              onChange={handleFileSelect}
              id="file-input"
              style={{ display: 'none' }}
            />
            <label htmlFor="file-input" className="file-label">
              <div className="upload-icon">
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M14 2H6C4.9 2 4 2.9 4 4V20C4 21.1 4.89 22 5.99 22H18C19.1 22 20 21.1 20 20V8L14 2Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                  <path d="M14 2V8H20" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                  <path d="M16 13H8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                  <path d="M16 17H8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                  <path d="M10 9H8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              </div>
              <p>Click to select PDF or DOCX file (max {MAX_FILE_SIZE_MB} MB)</p>
              {selectedFile && (
                <p className="selected-file">
                  Selected: {selectedFile.name} ({formatBytes(selectedFile.size)})
                </p>
              )}
            </label>
          </div>

          {fileError && <p className="resume-error" role="alert">{fileError}</p>}
          {uploadError && <p className="resume-error" role="alert">{uploadError}</p>}
          {saveMessage && <p className="resume-success" role="status">{saveMessage}</p>}

          <button
            className="upload-button"
            onClick={handleUpload}
            disabled={!selectedFile || uploading}
          >
            {uploading ? 'Uploading...' : 'Upload Resume'}
          </button>
        </div>

        <div className="resume-display">
          <h3>Your Resume Library</h3>
          {loadingResumes ? (
            <p className="resume-placeholder">Loading your resumes...</p>
          ) : resumes.length === 0 ? (
            <p className="resume-placeholder">Upload a resume to start building your history.</p>
          ) : (
            <div className="resume-history">
              {resumes.map((resume, index) => (
                <button
                  key={resume.id}
                  className={`resume-history-item${resume.id === activeResumeId ? ' active' : ''}`}
                  onClick={() => handleSelectResume(resume.id)}
                  type="button"
                >
                  <div className="resume-history-title">Resume {resumes.length - index}</div>
                  <div className="resume-history-name">{resume.filename}</div>
                  <div className="resume-history-meta">{formatDate(resume.uploadedAt)}</div>
                  <div className="resume-history-score">Score: {resume.resumeScore ?? 0}</div>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {activeResume && (
        <div className="resume-editor-panel">
          <div className="resume-editor-header">
            <div>
              <h3>{activeResume.filename}</h3>
              <p>{formatDate(activeResume.uploadedAt)}</p>
            </div>
            <div className="resume-badges">
              <span className="resume-score-badge">Resume score: {activeResume.resumeScore ?? 0}</span>
              <button
                className="view-button"
                onClick={() => window.open(activeResume.fileUrl, '_blank')}
                type="button"
              >
                Open Document
              </button>
              <button
                className="delete-button"
                onClick={() => handleDelete(activeResume.id)}
                type="button"
              >
                Delete
              </button>
            </div>
          </div>

          <div className="resume-info">
            <div className="info-row">
              <span className="label">Evaluation</span>
              <span>{activeResume.resumeSummary || 'No summary available yet.'}</span>
            </div>
          </div>

          <div className="resume-feedback-card">
            <h4>What&apos;s Lacking</h4>
            {(activeResume.resumeDetails?.suggestions || []).length > 0 ? (
              <ul className="resume-feedback-list">
                {activeResume.resumeDetails.suggestions.map((item, index) => (
                  <li key={`${activeResume.id}-suggestion-${index}`}>{item}</li>
                ))}
              </ul>
            ) : (
              <p className="resume-feedback-empty">
                No major gaps detected right now. Keep refining bullets and measurable impact.
              </p>
            )}
          </div>

          <div className="resume-editor-card">
            <label htmlFor="resume-text" className="resume-editor-label">
              Extracted Resume Text
            </label>
            <p className="resume-editor-help">
              Edit the extracted version of your resume here so you can refine wording inside the app.
            </p>
            <textarea
              id="resume-text"
              className="resume-editor-textarea"
              value={resumeText}
              onChange={(event) => setResumeText(event.target.value)}
            />
            <div className="resume-actions">
              <button
                className="upload-button"
                onClick={handleSaveResumeText}
                disabled={saving}
                type="button"
              >
                {saving ? 'Saving...' : 'Save Resume Text'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Resume;
