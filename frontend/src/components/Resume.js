import React, { useState } from 'react';
import './Resume.css';

const MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024; // 10 MB
const MAX_FILE_SIZE_MB = 10;

const Resume = () => {
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploadedResume, setUploadedResume] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [fileError, setFileError] = useState('');
  const [uploadError, setUploadError] = useState('');

  const allowedMimeTypes = [
    'application/pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
  ];
  const allowedExtensions = ['pdf', 'docx'];

  const handleFileSelect = (event) => {
    const file = event.target.files[0];
    setFileError('');
    setUploadError('');
    event.target.value = '';

    if (!file) return;

    // Unsupported format: check extension and MIME type
    const ext = file.name.split('.').pop()?.toLowerCase();
    if (!allowedExtensions.includes(ext) || !allowedMimeTypes.includes(file.type)) {
      setFileError('Please select a PDF or DOCX file.');
      setSelectedFile(null);
      return;
    }

    // Empty file
    if (file.size === 0) {
      setFileError('File is empty. Please select a non-empty file.');
      setSelectedFile(null);
      return;
    }

    // Oversized file
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
    try {
      // --- 1. GET THE TOKEN ---
      const token = localStorage.getItem('token');
      if (!token) {
        throw new Error('You are not logged in. Please log in first.');
      }

      const form = new FormData();
      form.append('file', selectedFile);

      const headers = new Headers();
      headers.append('Authorization', `Bearer ${token}`);

      // --- 3. ADD HEADERS TO THE FETCH REQUEST ---
      const res = await fetch('/api/resume/upload', {
        method: 'POST',
        body: form,
        headers
      });

      if (!res.ok) {
        const text = await res.text();
        let errMessage = `Upload failed (${res.status})`;
        try {
          const errData = JSON.parse(text);
          errMessage = errData.error || errMessage;
        } catch {
          if (text && text.length < 200) errMessage = text;
        }
        throw new Error(errMessage);
      }
      const data = await res.json();
      setUploadedResume({
        name: data.filename ?? selectedFile.name,
        size: data.size ? `${(data.size / 1024).toFixed(2)} KB` : `${(selectedFile.size / 1024).toFixed(2)} KB`,
        uploadDate: new Date().toLocaleDateString()
      });
      setSelectedFile(null);
      setUploadError('');
    } catch (e) {
      setUploadError(e.message || 'Upload failed.');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="resume-container">
      <h2>Resume Management</h2>
      <div className="resume-grid">
        {/* Upload Section */}
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
                {/* icon unchanged */}
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M14 2H6C4.9 2 4 2.9 4 4V20C4 21.1 4.89 22 5.99 22H18C19.1 22 20 21.1 20 20V8L14 2Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                  <path d="M14 2V8H20" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                  <path d="M16 13H8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                  <path d="M16 17H8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                  <path d="M10 9H8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              </div>
              <p>Click to select PDF or DOCX file (max {MAX_FILE_SIZE_MB} MB)</p>
              {selectedFile && <p className="selected-file">Selected: {selectedFile.name} ({(selectedFile.size / 1024).toFixed(1)} KB)</p>}
            </label>
          </div>
          {fileError && <p className="resume-error" role="alert">{fileError}</p>}
          {uploadError && <p className="resume-error" role="alert">{uploadError}</p>}

          <button
            className="upload-button"
            onClick={handleUpload}
            disabled={!selectedFile || uploading}
          >
            {uploading ? 'Uploading...' : 'Upload Resume'}
          </button>
        </div>

        {/* Display Section */}
        {uploadedResume && (
          <div className="resume-display">
            <h3>Current Resume</h3>
            <div className="resume-info">
              <div className="info-row"><span className="label">File Name:</span><span>{uploadedResume.name}</span></div>
              <div className="info-row"><span className="label">Size:</span><span>{uploadedResume.size}</span></div>
              <div className="info-row"><span className="label">Uploaded:</span><span>{uploadedResume.uploadDate}</span></div>
            </div>
            <div className="resume-actions">
              <button className="view-button" onClick={() => window.open('/api/resume/view', '_blank')}>
                {/* ... view button svg ... */}
                View Resume
              </button>
              <button className="delete-button" onClick={async () => {
                try {
                  const r = await fetch('/api/resume', { method: 'DELETE' });
                  if (!r.ok) throw new Error(`HTTP ${r.status}`);
                  setUploadedResume(null);
                } catch (e) { alert(`Delete failed: ${e.message}`); }
              }}>
                Delete
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Resume;