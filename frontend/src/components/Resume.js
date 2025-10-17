import React, { useState } from 'react';
import './Resume.css';

const Resume = () => {
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploadedResume, setUploadedResume] = useState(null);
  const [uploading, setUploading] = useState(false);

  const handleFileSelect = (event) => {
    const file = event.target.files[0];
    if (file && file.type === 'application/pdf') {
      setSelectedFile(file);
    } else {
      alert('Please select a PDF file');
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      alert('Please select a file first');
      return;
    }
    setUploading(true);
    try {
      const form = new FormData();
      form.append('file', selectedFile);
      const res = await fetch('/api/resume/upload', { method: 'POST', body: form });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setUploadedResume({
        name: data.name ?? selectedFile.name,
        size: data.size ?? ((selectedFile.size / 1024).toFixed(2) + ' KB'),
        uploadDate: data.uploadDate ?? new Date().toLocaleDateString()
      });
      setSelectedFile(null);
    } catch (e) {
      alert(`Upload failed: ${e.message}`);
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
              accept=".pdf"
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
              <p>Click to select PDF file</p>
              {selectedFile && <p className="selected-file">Selected: {selectedFile.name}</p>}
            </label>
          </div>

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
                {/* icon unchanged */}
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M1 12S5 4 12 4S23 12 23 12S19 20 12 20S1 12 1 12Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                  <circle cx="12" cy="12" r="3" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
                View Resume
              </button>
              <button className="delete-button" onClick={async () => {
                try {
                  const r = await fetch('/api/resume', { method: 'DELETE' });
                  if (!r.ok) throw new Error(`HTTP ${r.status}`);
                  setUploadedResume(null);
                } catch (e) { alert(`Delete failed: ${e.message}`); }
              }}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M3 6H5H21" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                  <path d="M8 6V4C8 3.46957 8.21071 2.96086 8.58579 2.58579C8.96086 2.21071 9.46957 2 10 2H14C14.5304 2 15.0391 2.21071 15.4142 2.58579C15.7893 2.96086 16 3.46957 16 4V6M19 6V20C19 20.5304 18.7893 21.0391 18.4142 21.4142C18.0391 21.7893 17.5304 22 17 22H7C6.46957 22 5.96086 21.7893 5.58579 21.4142C5.21071 21.0391 5 20.5304 5 20V6H19Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                  <path d="M10 11V17" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                  <path d="M14 11V17" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
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