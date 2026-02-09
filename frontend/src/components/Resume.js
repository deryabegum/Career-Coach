import React, { useEffect, useState } from 'react';
import './Resume.css';

const Resume = () => {
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploadedResume, setUploadedResume] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [resumeText, setResumeText] = useState('');
  const [loadingResume, setLoadingResume] = useState(false);
  const [savingResume, setSavingResume] = useState(false);

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        setLoadingResume(true);
        const token = localStorage.getItem('token');
        if (!token) return;
        const res = await fetch('/api/resume/latest', {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) return;
        const data = await res.json();
        if (alive) {
          setResumeText(data.content || '');
          if (data.file_path) {
            const name = data.file_path.split('/').pop();
            setUploadedResume({
              name,
              size: '—',
              uploadDate: data.created_at ? new Date(data.created_at).toLocaleDateString() : '—',
            });
          }
        }
      } finally {
        if (alive) setLoadingResume(false);
      }
    })();
    return () => { alive = false; };
  }, []);

  const handleFileSelect = (event) => {
    const file = event.target.files[0];
    const allowedMimeTypes = [
      'application/pdf',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document' // DOCX MIME type
    ];
    
    if (file && allowedMimeTypes.includes(file.type)) {
      setSelectedFile(file);
    } else {
      alert('Please select a PDF or DOCX file.'); 
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      alert('Please select a file first');
      return;
    }
    setUploading(true);
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
        headers: headers // <-- This is the new line
      });
      // --- END OF CHANGES ---

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

  const handleSaveEdits = async () => {
    if (!resumeText.trim()) {
      alert('Please enter resume content before saving.');
      return;
    }
    setSavingResume(true);
    try {
      const token = localStorage.getItem('token');
      if (!token) throw new Error('You are not logged in. Please log in first.');

      const res = await fetch('/api/resume/update', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ content: resumeText }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();

      if (data.file_path) {
        const name = data.file_path.split('/').pop();
        setUploadedResume((prev) => ({
          name,
          size: prev?.size ?? '—',
          uploadDate: new Date().toLocaleDateString(),
        }));
      }
      alert('Resume updated successfully.');
    } catch (e) {
      alert(`Save failed: ${e.message}`);
    } finally {
      setSavingResume(false);
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
              <p>Click to select PDF or DOCX file</p>
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
              <button className="delete-button" onClick={async () => {
                try {
                  const r = await fetch('/api/resume', { method: 'DELETE' });
                  if (!r.ok) throw new Error(`HTTP ${r.status}`);
                  setUploadedResume(null);
                } catch (e) { alert(`Delete failed: ${e.message}`); }
              }}>
                {/* ... delete button svg ... */}
                Delete
              </button>
            </div>
          </div>
        )}
      </div>

      <div className="resume-grid" style={{ marginTop: '2rem' }}>
        <div className="upload-section">
          <h3>Edit Resume</h3>
          {loadingResume ? (
            <p>Loading resume...</p>
          ) : (
            <>
              <textarea
                className="resume-editor"
                rows={12}
                value={resumeText}
                onChange={(e) => setResumeText(e.target.value)}
                placeholder="Paste or edit your resume text here..."
              />
              <button
                className="upload-button"
                onClick={handleSaveEdits}
                disabled={savingResume}
              >
                {savingResume ? 'Saving...' : 'Save Edited Resume'}
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default Resume;
