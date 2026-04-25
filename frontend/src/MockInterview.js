// test
import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Timer, ChevronLeft, ChevronRight, Play, Pause, RefreshCw, Send, Sparkles, CheckCircle2, XCircle, BookOpenText, ListChecks, Download, Mic, MicOff, History, X } from "lucide-react";
import { api } from "./api";
import "./MockInterview.css";
import jsPDF from "jspdf";

/**
 * MockInterview.js (page-level component)
 *
 * Features
 * - Start screen with role/company fields and time-per-question
 * - Question viewer with tags, timer, progress
 * - Answer textarea with autosave (localStorage) + keyboard shortcuts
 * - Next/Prev navigation and quick-jump list
 * - Optional AI feedback hook (stubbed) with optimistic UI
 * - Review mode with per-question status and export
 *
 * Simple HTML/CSS with React
 */

const DEFAULT_SECONDS = 120;

const SAMPLE_QUESTIONS = [
  {
    id: "q1",
    prompt:
      "Tell me about yourself and why you're interested in this role.",
    tags: ["behavioral", "intro", "communication"],
  },
  {
    id: "q2",
    prompt:
      "Describe a challenging bug or issue you solved. What was your approach and outcome?",
    tags: ["problem-solving", "impact"],
  },
  {
    id: "q3",
    prompt:
      "Walk me through a project you are most proud of. What was your role and what did you learn?",
    tags: ["ownership", "learning"],
  },
  {
    id: "q4",
    prompt:
      "How do you handle tight deadlines and conflicting priorities?",
    tags: ["prioritization", "teamwork"],
  },
  {
    id: "q5",
    prompt: "Do you have any questions for us?",
    tags: ["reverse", "curiosity"],
  },
];

const DEFAULT_QUESTION_COUNT = 5;

function useLocalStorage(key, initialValue) {
  const [state, setState] = useState(() => {
    try {
      const raw = localStorage.getItem(key);
      return raw ? JSON.parse(raw) : initialValue;
    } catch {
      return initialValue;
    }
  });
  useEffect(() => {
    try {
      localStorage.setItem(key, JSON.stringify(state));
    } catch {}
  }, [key, state]);
  return [state, setState];
}

export default function MockInterviewPage() {
  const [started, setStarted] = useLocalStorage("mi_started", false);
  const [role, setRole] = useLocalStorage("mi_role", "Software / Data / Intern");
  const [company, setCompany] = useLocalStorage("mi_company", "Company");
  const [secondsPerQ, setSecondsPerQ] = useLocalStorage("mi_secondsPerQ", DEFAULT_SECONDS);

  const [questions, setQuestions] = useLocalStorage("mi_questions", SAMPLE_QUESTIONS);

  const [index, setIndex] = useLocalStorage("mi_index", 0);
  const [answers, setAnswers] = useLocalStorage("mi_answers", {});
  const [feedback, setFeedback] = useLocalStorage("mi_feedback", {});
  const [running, setRunning] = useLocalStorage("mi_running", false);
  const [remaining, setRemaining] = useLocalStorage("mi_remaining", secondsPerQ);
  const [reviewMode, setReviewMode] = useLocalStorage("mi_review", false);
  const [sessionId, setSessionId] = useLocalStorage("mi_sessionId", null);
  const [loading, setLoading] = useState(false);
  const [loadingPhase, setLoadingPhase] = useState(""); // '', 'starting' | 'feedback' | 'submitting'
  const [apiError, setApiError] = useState(null);
  const [micPermissionStatus, setMicPermissionStatus] = useState(null); // null, 'granted', 'denied', 'prompt'
  const [micError, setMicError] = useState(null);

  const [historyOpen, setHistoryOpen] = useState(false);
  const [historySessions, setHistorySessions] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState(null);
  const [historyDetail, setHistoryDetail] = useState(null);
  const [historyDetailLoading, setHistoryDetailLoading] = useState(false);

  const timerRef = useRef(null);
  const activeQuestions = Array.isArray(questions) && questions.length ? questions : SAMPLE_QUESTIONS;
  const current = activeQuestions[index] || activeQuestions[0];
  const progressValue = Math.round(((index + 1) / activeQuestions.length) * 100);

  const MIC_DENIED_MESSAGE = "Please allow microphone access to start interview";

  // Check microphone permission status (no getUserMedia on mount - prompt only when user clicks Start)
  const checkMicrophonePermission = useCallback(async () => {
    try {
      if (navigator.permissions && navigator.permissions.query) {
        const result = await navigator.permissions.query({ name: 'microphone' });
        setMicPermissionStatus(result.state);
        if (result.state === 'denied') {
          setMicError(MIC_DENIED_MESSAGE);
        } else {
          setMicError(null);
        }
        result.onchange = () => {
          setMicPermissionStatus(result.state);
          if (result.state === 'granted') {
            setMicError(null);
          } else if (result.state === 'denied') {
            setMicError(MIC_DENIED_MESSAGE);
          }
        };
      } else {
        // Permissions API not available - don't prompt on mount; defer to Start practice click
        setMicPermissionStatus('prompt');
        setMicError(null);
      }
    } catch (error) {
      console.error('Microphone permission check failed:', error);
      setMicPermissionStatus('denied');
      if (error.name === 'NotFoundError' || error.name === 'DevicesNotFoundError') {
        setMicError('No microphone found. Please connect a microphone to start the interview.');
      } else {
        setMicError(MIC_DENIED_MESSAGE);
      }
    }
  }, []);

  // Request microphone permission (called when user clicks Start practice)
  const requestMicrophonePermission = useCallback(async () => {
    try {
      setLoading(true);
      setMicError(null);
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      setMicPermissionStatus('granted');
      stream.getTracks().forEach(track => track.stop());
      setMicError(null);
      return true;
    } catch (error) {
      console.error('Microphone permission request failed:', error);
      setMicPermissionStatus('denied');
      if (error.name === 'NotFoundError' || error.name === 'DevicesNotFoundError') {
        setMicError('No microphone found. Please connect a microphone to start the interview.');
      } else {
        setMicError(MIC_DENIED_MESSAGE);
      }
      return false;
    } finally {
      setLoading(false);
    }
  }, []);

  // Check microphone permission on component mount
  useEffect(() => {
    if (!started) {
      checkMicrophonePermission();
    }
  }, [started, checkMicrophonePermission]);

  const startInterview = useCallback(async () => {
    // Request microphone permission but don't block if unavailable
    if (micPermissionStatus !== 'granted') {
      const permissionGranted = await requestMicrophonePermission();
      if (!permissionGranted) {
        setMicError("Microphone not available — voice features disabled.");
        // continue anyway
      }
    }

    try {
      setLoading(true);
      setLoadingPhase("starting");
      setMicError(null);
      setApiError(null);
      const response = await api.createInterviewSession({ role, company });
      setSessionId(response.session_id);
      setQuestions(Array.isArray(response.questions) && response.questions.length ? response.questions : SAMPLE_QUESTIONS);
      setStarted(true);
      setIndex(0);
      setRemaining(secondsPerQ);
      setRunning(true);
    } catch (error) {
      console.error("Failed to create session:", error);
      setApiError(error.message || "Could not start session. Please check your connection and try again.");
      // Still allow starting locally even if backend fails
      setQuestions(generateLocalQuestionSet(role, company, DEFAULT_QUESTION_COUNT));
      setStarted(true);
      setIndex(0);
      setRemaining(secondsPerQ);
      setRunning(true);
    } finally {
      setLoading(false);
      setLoadingPhase("");
    }
  }, [secondsPerQ, setIndex, setQuestions, setRemaining, setRunning, setStarted, role, company, micPermissionStatus, requestMicrophonePermission, setSessionId]);

  // Timer
  useEffect(() => {
    if (!running) return;
    timerRef.current = setInterval(() => {
      setRemaining((r) => {
        if (r <= 1) {
          clearInterval(timerRef.current);
          setRunning(false);
          return 0;
        }
        return r - 1;
      });
    }, 1000);
    return () => clearInterval(timerRef.current);
  }, [running, setRemaining, setRunning]);

  // Reset timer when question changes
  useEffect(() => {
    if (!started) return;
    setRemaining(secondsPerQ);
  }, [index, secondsPerQ, setRemaining, started]);

  const updateAnswer = (qid, text) => {
    setAnswers((prev) => ({ ...prev, [qid]: text }));
  };

  const next = () => setIndex((i) => Math.min(i + 1, activeQuestions.length - 1));
  const prev = () => setIndex((i) => Math.max(i - 1, 0));

  const jumpTo = (i) => {
    setIndex(i);
  };

  const resetAll = () => {
    setStarted(false);
    setReviewMode(false);
    setIndex(0);
    setAnswers({});
    setFeedback({});
    setRunning(false);
    setRemaining(secondsPerQ);
    setSessionId(null);
    setQuestions(generateLocalQuestionSet(role, company, DEFAULT_QUESTION_COUNT));
  };

  const closeHistory = useCallback(() => {
    setHistoryOpen(false);
    setHistoryDetail(null);
    setHistoryError(null);
  }, []);

  const loadPastSessions = useCallback(async () => {
    setHistoryLoading(true);
    setHistoryError(null);
    setHistoryDetail(null);
    try {
      const data = await api.getUserSessions();
      setHistorySessions(Array.isArray(data.sessions) ? data.sessions : []);
    } catch (e) {
      setHistorySessions([]);
      setHistoryError(e.message || "Could not load past sessions.");
    } finally {
      setHistoryLoading(false);
    }
  }, []);

  const openHistory = useCallback(() => {
    setHistoryOpen(true);
    loadPastSessions();
  }, [loadPastSessions]);

  const openHistorySession = useCallback(async (sessionId) => {
    setHistoryDetailLoading(true);
    setHistoryError(null);
    try {
      const detail = await api.getInterviewSession(sessionId);
      setHistoryDetail(detail);
    } catch (e) {
      setHistoryDetail(null);
      setHistoryError(e.message || "Could not load this session.");
    } finally {
      setHistoryDetailLoading(false);
    }
  }, []);

  const answeredCount = useMemo(
    () => Object.values(answers).filter((v) => (v ?? "").trim().length > 0).length,
    [answers]
  );

  const unanswered = activeQuestions
    .map((q, i) => ({ i, q }))
    .filter(({ q }) => !answers[q.id] || !answers[q.id].trim());

  const onSubmitInterview = async () => {
    if (!sessionId) {
      setReviewMode(true);
      return;
    }

    setApiError(null);
    try {
      setLoading(true);
      setLoadingPhase("submitting");
      const answersWithPrompts = {};
      activeQuestions.forEach(q => {
        if (answers[q.id]) {
          answersWithPrompts[q.id] = {
            answer: answers[q.id],
            prompt: q.prompt
          };
        }
      });
      const result = await api.submitInterview({
        session_id: sessionId,
        answers: answersWithPrompts,
        role,
        company
      });
      setReviewMode(true);
      if (result.feedback) {
        setFeedback((prev) => ({ ...prev, ...result.feedback }));
      }
    } catch (error) {
      console.error("Failed to submit interview:", error);
      setApiError(error.message || "Could not submit interview. Your answers were not evaluated. Please check your connection and try again.");
      setReviewMode(true);
    } finally {
      setLoading(false);
      setLoadingPhase("");
    }
  };

  const requestFeedback = async () => {
    const a = (answers[current.id] || "").trim();
    if (!a) return;

    setApiError(null);
    try {
      setLoading(true);
      setLoadingPhase("feedback");
      const data = await api.getInterviewFeedback({
        session_id: sessionId,
        question_prompt: current.prompt,
        answer_text: a,
        role,
        company
      });
      setFeedback((prev) => ({ ...prev, [current.id]: data }));
    } catch (error) {
      console.error("Failed to get feedback:", error);
      setApiError(error.message || "Could not load AI feedback. Showing local feedback instead.");
      const fake = generateHeuristicFeedback(current.prompt, a);
      setFeedback((prev) => ({ ...prev, [current.id]: fake }));
    } finally {
      setLoading(false);
      setLoadingPhase("");
    }
  };

  const exportJSON = () => {
    const blob = new Blob([JSON.stringify({ role, company, answers, feedback }, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `mock-interview-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const downloadPDF = () => {
    const doc = new jsPDF();
    const pageWidth = doc.internal.pageSize.getWidth();
    const pageHeight = doc.internal.pageSize.getHeight();
    const margin = 20;
    const maxWidth = pageWidth - 2 * margin;
    let yPosition = margin;

    const resumeData = JSON.parse(localStorage.getItem("uploadedResume") || "null");

    // Helper function to add a new page if needed
    const checkNewPage = (requiredHeight) => {
      if (yPosition + requiredHeight > pageHeight - margin) {
        doc.addPage();
        yPosition = margin;
        return true;
      }
      return false;
    };

    // Helper function to add text with word wrapping
    const addWrappedText = (text, fontSize, isBold = false, color = [0, 0, 0]) => {
      const str = String(text ?? "");
      doc.setFontSize(fontSize);
      doc.setTextColor(color[0], color[1], color[2]);
      if (isBold) {
        doc.setFont(undefined, "bold");
      } else {
        doc.setFont(undefined, "normal");
      }
      const lines = doc.splitTextToSize(str, maxWidth);
      lines.forEach((line) => {
        checkNewPage(7);
        doc.text(line, margin, yPosition);
        yPosition += 7;
      });
      doc.setFont(undefined, "normal");
    };

    // Title
    doc.setFontSize(20);
    doc.setTextColor(59, 130, 246);
    doc.setFont(undefined, "bold");
    doc.text("Career Coach Report", margin, yPosition);
    yPosition += 15;

    // Interview details
    doc.setFontSize(12);
    doc.setTextColor(0, 0, 0);
    doc.setFont(undefined, "normal");
    doc.text(`Role: ${role}`, margin, yPosition);
    yPosition += 7;
    doc.text(`Company: ${company}`, margin, yPosition);
    yPosition += 7;
    doc.text(`Date: ${new Date().toLocaleDateString()}`, margin, yPosition);
    yPosition += 12;

    // Resume section
    doc.setFontSize(14);
    doc.setTextColor(26, 26, 26);
    doc.setFont(undefined, "bold");
    doc.text("Resume Information", margin, yPosition);
    yPosition += 8;

    doc.setFont(undefined, "normal");
    doc.setFontSize(10);
    doc.setTextColor(55, 65, 81);

    if (resumeData) {
      addWrappedText(`File Name: ${resumeData.name || "N/A"}`, 10, false, [55, 65, 81]);
      addWrappedText(`Size: ${resumeData.size || "N/A"}`, 10, false, [55, 65, 81]);
      addWrappedText(`Uploaded: ${resumeData.uploadDate || "N/A"}`, 10, false, [55, 65, 81]);
    } else {
      addWrappedText("No resume uploaded.", 10, false, [55, 65, 81]);
    }

    yPosition += 10;

    // Interview results section title
    doc.setFontSize(14);
    doc.setTextColor(26, 26, 26);
    doc.setFont(undefined, "bold");
    doc.text("Mock Interview Results", margin, yPosition);
    yPosition += 10;

    // Questions and Answers
    activeQuestions.forEach((q, index) => {
      checkNewPage(20);
      
      // Question number and prompt
      addWrappedText(`Question ${index + 1}`, 14, true, [26, 26, 26]);
      yPosition += 3;
      addWrappedText(q.prompt, 11, true, [55, 65, 81]);
      yPosition += 5;

      // Tags if available
      if (q.tags && q.tags.length > 0) {
        doc.setFontSize(9);
        doc.setTextColor(107, 114, 128);
        const tagsText = `Tags: ${q.tags.join(", ")}`;
        doc.text(tagsText, margin, yPosition);
        yPosition += 6;
      }

      // Answer
      const answer = answers[q.id] || "(No answer provided)";
      doc.setFontSize(10);
      doc.setTextColor(0, 0, 0);
      doc.setFont(undefined, "bold");
      doc.text("Your Answer:", margin, yPosition);
      yPosition += 6;
      doc.setFont(undefined, "normal");
      addWrappedText(answer, 10, false, [55, 65, 81]);
      yPosition += 5;

      // Feedback if available
      if (feedback[q.id]) {
        yPosition += 3;
        doc.setFontSize(10);
        doc.setFont(undefined, "bold");
        doc.setTextColor(59, 130, 246);
        doc.text("AI Feedback:", margin, yPosition);
        yPosition += 6;
        doc.setFont(undefined, "normal");
        doc.setTextColor(0, 0, 0);

        if (feedback[q.id].summary != null && feedback[q.id].summary !== "") {
          doc.setFont(undefined, "bold");
          doc.text("Summary:", margin, yPosition);
          yPosition += 6;
          doc.setFont(undefined, "normal");
          addWrappedText(feedback[q.id].summary, 9, false, [55, 65, 81]);
          yPosition += 3;
        }

        const strengths = Array.isArray(feedback[q.id].strengths) ? feedback[q.id].strengths : [];
        if (strengths.length > 0) {
          doc.setFont(undefined, "bold");
          doc.setTextColor(5, 150, 105);
          doc.text("Strengths:", margin, yPosition);
          yPosition += 6;
          doc.setFont(undefined, "normal");
          doc.setTextColor(0, 0, 0);
          strengths.forEach((strength) => {
            addWrappedText(`• ${strength}`, 9, false, [55, 65, 81]);
            yPosition += 1;
          });
          yPosition += 3;
        }

        const suggestions = Array.isArray(feedback[q.id].suggestions) ? feedback[q.id].suggestions : [];
        if (suggestions.length > 0) {
          doc.setFont(undefined, "bold");
          doc.setTextColor(217, 119, 6);
          doc.text("Suggestions:", margin, yPosition);
          yPosition += 6;
          doc.setFont(undefined, "normal");
          doc.setTextColor(0, 0, 0);
          suggestions.forEach((suggestion) => {
            addWrappedText(`• ${suggestion}`, 9, false, [55, 65, 81]);
            yPosition += 1;
          });
          yPosition += 3;
        }
      }

      // Add spacing between questions
      yPosition += 10;
    });

    // Footer
    const totalPages = doc.internal.pages.length - 1;
    for (let i = 1; i <= totalPages; i++) {
      doc.setPage(i);
      doc.setFontSize(8);
      doc.setTextColor(128, 128, 128);
      doc.text(
        `Page ${i} of ${totalPages}`,
        pageWidth - margin - 20,
        pageHeight - 10
      );
    }

    // Save the PDF
    const fileName = `career-coach-report-${role.replace(/\s+/g, "-")}-${Date.now()}.pdf`;
    doc.save(fileName);
  };

  // Keyboard shortcuts
  useEffect(() => {
    const onKey = (e) => {
      if (e.ctrlKey && e.key.toLowerCase() === "enter") {
        e.preventDefault();
        next();
      } else if (e.altKey && e.key === "ArrowLeft") {
        e.preventDefault();
        prev();
      } else if (e.altKey && e.key === "ArrowRight") {
        e.preventDefault();
        next();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const loadingLabel = loadingPhase === "starting"
    ? "Starting session..."
    : loadingPhase === "submitting"
      ? "Submitting & generating evaluation..."
      : loadingPhase === "feedback"
        ? "Getting feedback..."
        : "Loading...";

  return (
    <div className="mock-interview-container">
      {apiError && (
        <div
          className="mock-interview-api-error"
          role="alert"
          style={{
            marginBottom: "1rem",
            padding: "1rem 1.25rem",
            background: "#fef2f2",
            border: "1px solid #fecaca",
            borderRadius: "8px",
            color: "#b91c1c",
            display: "flex",
            alignItems: "flex-start",
            gap: "0.75rem",
          }}
        >
          <XCircle size={20} style={{ flexShrink: 0, marginTop: "2px" }} />
          <div style={{ flex: 1 }}>
            <strong style={{ display: "block", marginBottom: "0.25rem" }}>Something went wrong</strong>
            <p style={{ margin: 0, fontSize: "0.875rem" }}>{apiError}</p>
          </div>
          <button
            type="button"
            onClick={() => setApiError(null)}
            aria-label="Dismiss error"
            style={{
              background: "none",
              border: "none",
              color: "#b91c1c",
              cursor: "pointer",
              padding: "0.25rem 0.5rem",
              fontSize: "0.875rem",
              fontWeight: 600,
            }}
          >
            Dismiss
          </button>
        </div>
      )}
      <header className="mock-interview-header">
        <div>
          <h1>Mock Interview</h1>
          <p>Practice behavioral & role-specific questions with a timed flow and instant feedback.</p>
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', alignItems: 'center', justifyContent: 'flex-end' }}>
          <button type="button" className="button outline" onClick={openHistory} style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}>
            <History size={16} /> Past sessions
          </button>
          <span className="badge">{answeredCount}/{activeQuestions.length} answered</span>
          <span className={`badge ${reviewMode ? 'primary' : ''}`}>{reviewMode ? "Review" : "Practice"}</span>
        </div>
      </header>

      {!started ? (
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">Set up your session</h2>
            <p className="card-description">Customize context and pacing to get the most out of your practice.</p>
          </div>
          <div className="card-content setup-grid">
            <div className="input-group">
              <label>Role / Track</label>
              <input className="input" value={role} onChange={(e) => setRole(e.target.value)} placeholder="Software Engineer Intern" />
            </div>
            <div className="input-group">
              <label>Company</label>
              <input className="input" value={company} onChange={(e) => setCompany(e.target.value)} placeholder="Nutanix, AA, UTSW" />
            </div>
            <div className="input-group">
              <label>Seconds per question</label>
              <input
                className="input"
                type="number"
                min={30}
                max={600}
                value={secondsPerQ}
                onChange={(e) => setSecondsPerQ(Number(e.target.value) || DEFAULT_SECONDS)}
              />
            </div>
          </div>
          <div className="card-footer">
            <div className="meta-inline">
              <BookOpenText size={16}/> {activeQuestions.length} questions in this set
            </div>
            <button className="button primary lg" onClick={startInterview} disabled={loading}>
              <Play size={16} style={{ marginRight: '0.5rem' }} /> {loading ? loadingLabel : "Start practice"}
            </button>
          </div>
          {micError && (
            <div className="status-panel error">
              <MicOff size={20} style={{ flexShrink: 0 }} />
              <div style={{ flex: 1 }}>
                <strong className="status-title">Microphone Access Required</strong>
                <p className="status-copy">{micError}</p>
                {micPermissionStatus === 'denied' && (
                  <p className="status-hint">
                    Please check your browser settings and allow microphone access for this site.
                  </p>
                )}
              </div>
            </div>
          )}
          {micPermissionStatus === 'granted' && !micError && (
            <div className="status-panel success compact">
              <Mic size={18} style={{ flexShrink: 0 }} />
              <span>Microphone access granted</span>
            </div>
          )}
          <div className="card" style={{ marginTop: '1.25rem' }}>
            <div className="card-header">
              <h3 className="card-title" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <History size={18} /> Past sessions
              </h3>
              <p className="card-description">
                Reopen transcripts and AI feedback from interviews you submitted (saved on your account).
              </p>
            </div>
            <div className="card-footer" style={{ justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.75rem' }}>
              <p style={{ margin: 0, fontSize: '0.875rem', color: 'var(--mi-text-soft, #aaa)' }}>
                Sessions are listed after you use &quot;Submit for evaluation&quot; while logged in.
              </p>
              <button type="button" className="button secondary" onClick={openHistory}>
                <History size={16} style={{ marginRight: '0.5rem' }} />
                View history
              </button>
            </div>
          </div>
        </div>
      ) : (
        <div className="grid-2-col">
          {/* Left: question & nav */}
          <div>
            <div className="card">
              <div className="card-header">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <h3 className="card-title">Question {index + 1}</h3>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <Timer size={18} />
                    <span className={`timer-display ${remaining <= 10 ? 'warning' : ''}`}>{formatTime(remaining)}</span>
                    <button className="icon-button" onClick={() => setRunning((r) => !r)} aria-label="Toggle timer">
                      {running ? <Pause size={18} /> : <Play size={18} />}
                    </button>
                    <button className="icon-button" onClick={() => { setRemaining(secondsPerQ); setRunning(true); }} aria-label="Reset timer">
                      <RefreshCw size={18} />
                    </button>
                  </div>
                </div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginTop: '0.5rem' }}>
                  {current.tags?.map((t) => (
                    <span key={t} className="badge">{t}</span>
                  ))}
                </div>
              </div>
              <div className="card-content">
                <p style={{ fontSize: '1rem', lineHeight: '1.6' }}>{current.prompt}</p>
              </div>
              <div className="card-footer">
                <div style={{ width: '100%' }}>
                  <div className="progress-bar">
                    <div className="progress-fill" style={{ width: `${progressValue}%` }}></div>
                  </div>
                  <div className="progress-label">{progressValue}% complete</div>
                </div>
              </div>
            </div>

            <div className="card">
              <div className="card-header">
                <h3 className="card-title">Your answer</h3>
                <p className="card-description">Autosaves locally. Press <kbd className="shortcut-key">Ctrl</kbd> + <kbd className="shortcut-key">Enter</kbd> to go next.</p>
              </div>
              <div className="card-content">
                <textarea
                  className="textarea"
                  value={answers[current.id] || ""}
                  onChange={(e) => updateAnswer(current.id, e.target.value)}
                  placeholder="Structure with STAR: Situation, Task, Action, Result..."
                />
              </div>
              <div className="card-footer" style={{ flexWrap: 'wrap', gap: '0.5rem' }}>
                <button className="button secondary" onClick={requestFeedback} disabled={loading}>
                  <Sparkles size={16} style={{ marginRight: '0.5rem' }} />{loading ? loadingLabel : "Get feedback"}
                </button>
                <div style={{ marginLeft: 'auto', display: 'flex', gap: '0.5rem' }}>
                  <button className="button outline" onClick={prev} disabled={index === 0}>
                    <ChevronLeft size={16} style={{ marginRight: '0.5rem' }} />Prev
                  </button>
                  <button className="button primary" onClick={next} disabled={index === activeQuestions.length - 1}>
                    Next<ChevronRight size={16} style={{ marginLeft: '0.5rem' }} />
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* Right: feedback & quick nav */}
          <div>
            <div className="card">
              <div className="card-header">
                <h3 className="card-title">AI feedback</h3>
                <p className="card-description">Get instant feedback on your answers.</p>
              </div>
              <div className="card-content">
                {feedback[current.id] ? (
                  <FeedbackBox data={feedback[current.id]} />
                ) : (
                  <div className="empty-state-note">No feedback yet - write an answer and click <em>Get feedback</em>.</div>
                )}
              </div>
            </div>

            <div className="card">
              <div className="card-header">
                <h3 className="card-title" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <ListChecks size={18}/> Quick navigator
                </h3>
                <p className="card-description">Jump to any question and see which ones need attention.</p>
              </div>
              <div className="card-content">
                <div className="question-grid">
                  {activeQuestions.map((q, i) => {
                    const done = (answers[q.id] || "").trim().length > 0;
                    return (
                      <button
                        key={q.id}
                        onClick={() => jumpTo(i)}
                        className={`question-button ${i === index ? 'active' : ''} ${done ? 'answered' : ''}`}
                        title={q.prompt}
                      >
                        {i + 1}
                      </button>
                    );
                  })}
                </div>
              </div>
              <div className="card-footer">
                <div className="footer-status-text">
                  {unanswered.length === 0 ? (
                    <span className="status-inline success">
                      <CheckCircle2 size={14}/>All questions answered
                    </span>
                  ) : (
                    <span className="status-inline warning">
                      <XCircle size={14}/>{unanswered.length} unanswered
                    </span>
                  )}
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  {loadingPhase === "submitting" && (
                    <p style={{ margin: 0, fontSize: "0.8125rem", color: "#6b7280" }}>
                      Analyzing your answers and generating AI feedback. This may take a moment…
                    </p>
                  )}
                  <div style={{ display: 'flex', gap: '0.5rem' }}>
                    <button className="button outline" onClick={exportJSON}>Export</button>
                    <button className="button primary" onClick={onSubmitInterview} disabled={loading}>
                      <Send size={16} style={{ marginRight: '0.5rem' }} />{loading ? loadingLabel : "Submit for evaluation"}
                    </button>
                  </div>
                </div>
              </div>
            </div>

            {reviewMode && (
              <div className="card">
                <div className="card-header">
                  <h3 className="card-title">Review</h3>
                  <p className="card-description">Spot-check answers before finalizing.</p>
                </div>
                <div className="card-content" style={{ maxHeight: '300px', overflow: 'auto', paddingRight: '0.5rem' }}>
                  {activeQuestions.map((q, i) => (
                    <div key={q.id} className="review-item">
                      <h4>Q{i + 1}</h4>
                      <h5>{q.prompt}</h5>
                      <p>{answers[q.id] || <span className="muted-copy">(no answer)</span>}</p>
                    </div>
                  ))}
                </div>
                <div className="card-footer">
                  <button className="button secondary" onClick={resetAll}>
                    <RefreshCw size={16} style={{ marginRight: '0.5rem' }} />Start over
                  </button>
                  <button className="button primary" onClick={downloadPDF}>
                    <Download size={16} style={{ marginRight: '0.5rem' }} />Download Report
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {historyOpen && (
        <div
          className="mi-history-overlay"
          role="dialog"
          aria-modal="true"
          aria-labelledby="mi-history-title"
        >
          <button
            type="button"
            className="mi-history-backdrop"
            aria-label="Close history"
            onClick={closeHistory}
          />
          <div className="mi-history-panel">
            <div className="mi-history-panel-header">
              <h2 id="mi-history-title" className="mi-history-title">
                {historyDetail ? "Session detail" : "Past interview sessions"}
              </h2>
              <button
                type="button"
                className="icon-button"
                onClick={closeHistory}
                aria-label="Close"
              >
                <X size={22} />
              </button>
            </div>

            {historyDetailLoading && (
              <p className="mi-history-muted">Loading session…</p>
            )}

            {!historyDetailLoading && historyDetail && (
              <div className="mi-history-detail">
                <button
                  type="button"
                  className="button outline"
                  style={{ marginBottom: "1rem", display: "inline-flex", alignItems: "center", gap: "0.35rem" }}
                  onClick={() => {
                    setHistoryDetail(null);
                    setHistoryError(null);
                  }}
                >
                  <ChevronLeft size={16} /> Back to list
                </button>
                <div className="mi-history-meta">
                  <p><strong>Role</strong> · {historyDetail.role}</p>
                  <p><strong>Company</strong> · {historyDetail.company}</p>
                  <p><strong>Started</strong> · {formatSessionWhen(historyDetail.created_at)}</p>
                  {historyDetail.submitted_at && (
                    <p><strong>Submitted</strong> · {formatSessionWhen(historyDetail.submitted_at)}</p>
                  )}
                  {historyDetail.average_score != null && (
                    <p><strong>Average score</strong> · {Math.round(Number(historyDetail.average_score))}/100</p>
                  )}
                </div>
                {(!historyDetail.items || historyDetail.items.length === 0) && (
                  <p className="mi-history-muted">No answers were saved for this session yet.</p>
                )}
                <div className="mi-history-items">
                  {(historyDetail.items || []).map((row, idx) => (
                    <div key={`${row.qid}-${idx}`} className="mi-history-item card">
                      <div className="card-header">
                        <h3 className="card-title">Question {idx + 1}</h3>
                      </div>
                      <div className="card-content">
                        <p style={{ fontSize: "0.95rem", lineHeight: 1.6, marginBottom: "0.75rem" }}>{row.prompt}</p>
                        <p style={{ fontSize: "0.8125rem", color: "var(--mi-text-soft, #aaa)", marginBottom: "0.35rem" }}>Your answer</p>
                        <p style={{ fontSize: "0.9rem", lineHeight: 1.55, whiteSpace: "pre-wrap" }}>{row.answer || "(No answer)"}</p>
                      </div>
                      {row.feedback && Object.keys(row.feedback).length > 0 && (
                        <div className="card-content" style={{ borderTop: "1px solid var(--mi-border, rgba(255,255,255,0.1))" }}>
                          <FeedbackBox data={row.feedback} />
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {!historyDetailLoading && !historyDetail && (
              <>
                {historyLoading && <p className="mi-history-muted">Loading your sessions…</p>}
                {historyError && (
                  <div className="mi-history-error" role="alert">{historyError}</div>
                )}
                {!historyLoading && !historyError && historySessions.length === 0 && (
                  <p className="mi-history-muted">
                    No sessions yet. Start a practice run, answer the questions, then choose <strong>Submit for evaluation</strong> while logged in to save transcripts and feedback here.
                  </p>
                )}
                {!historyLoading && historySessions.length > 0 && (
                  <ul className="mi-history-list">
                    {historySessions.map((s) => (
                      <li key={s.id}>
                        <button
                          type="button"
                          className="mi-history-row"
                          onClick={() => openHistorySession(s.id)}
                        >
                          <div className="mi-history-row-main">
                            <span className="mi-history-row-title">{s.role} · {s.company}</span>
                            <span className="mi-history-row-sub">
                              {formatSessionWhen(s.created_at)}
                              {s.submitted_at ? " · Evaluated" : s.answer_count ? ` · ${s.answer_count} answer(s) saved` : ""}
                            </span>
                          </div>
                          {s.average_score != null && (
                            <span className="mi-history-row-score">{Math.round(Number(s.average_score))}/100</span>
                          )}
                          <ChevronRight size={18} className="mi-history-row-chevron" aria-hidden />
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function formatSessionWhen(iso) {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return String(iso);
    return d.toLocaleString(undefined, {
      dateStyle: "medium",
      timeStyle: "short",
    });
  } catch {
    return String(iso);
  }
}

function formatTime(s) {
  const m = Math.floor(s / 60);
  const ss = s % 60;
  return `${m}:${ss.toString().padStart(2, "0")}`;
}

function FeedbackBox({ data }) {
  const metrics = data.metrics || {};
  const metricEntries = [
    { key: "accuracy", label: "Accuracy" },
    { key: "clearness", label: "Clearness" },
    { key: "confidence", label: "Confidence" },
  ];

  return (
    <div className="feedback-box">
      <div className="metric-summary-card">
        <div>
          <div className="metric-summary-label">Overall score</div>
          <div className="metric-summary-value">{Math.round(data.overall_score ?? 0)}/100</div>
        </div>
        {data.evaluator?.provider ? (
          <span className="badge">{data.evaluator.provider}</span>
        ) : null}
      </div>

      <div className="metrics-grid">
        {metricEntries.map(({ key, label }) => {
          const metric = metrics[key];
          return (
            <div key={key} className="metric-card">
              <div className="metric-card-header">
                <span>{label}</span>
                <span className="metric-score">{metric?.score ?? "-"}/5</span>
              </div>
              <div className="metric-label">{metric?.label || "Not scored"}</div>
              <p className="metric-reason">{metric?.reason || "No evaluation available yet."}</p>
            </div>
          );
        })}
      </div>

      <div className="feedback-section">
        <h4>Summary</h4>
        <p style={{ fontSize: '0.875rem', lineHeight: '1.6' }}>{data.summary ?? ''}</p>
      </div>
      <div className="feedback-section">
        <h4>Strengths</h4>
        <ul>
          {(Array.isArray(data.strengths) ? data.strengths : []).map((s, i) => (
            <li key={i}>{s}</li>
          ))}
        </ul>
      </div>
      <div className="feedback-section">
        <h4>Suggestions</h4>
        <ul>
          {(Array.isArray(data.suggestions) ? data.suggestions : []).map((s, i) => (
            <li key={i}>{s}</li>
          ))}
        </ul>
      </div>
      <div className="feedback-caption">Interview feedback summary.</div>
    </div>
  );
}

function generateLocalQuestionSet(role, company, count = DEFAULT_QUESTION_COUNT) {
  const roleText = role || "Software / Data / Intern";
  const companyText = company || "the company";
  const roleLower = roleText.toLowerCase();

  const behavioral = [
    "Tell me about a time you had to adapt quickly when priorities changed.",
    "Describe a situation where you had to balance speed and quality.",
    "Tell me about a time you received constructive feedback and what you changed.",
    "Describe a challenge where you had to work through ambiguity.",
  ];

  const technical = [
    `Walk me through a project that best prepared you for this ${roleText} role.`,
    "Describe a bug or technical issue you diagnosed. How did you find the root cause?",
    "How do you approach debugging when the problem is not obvious at first?",
    "Tell me about a time you improved performance, reliability, or maintainability.",
  ];

  const data = [
    "Tell me about a time you used data to influence a decision.",
    "How do you validate that your analysis or model is reliable?",
    "Describe a project where you had to explain a technical insight to a non-technical audience.",
    "How do you handle messy, missing, or conflicting data?",
  ];

  const closing = [
    `Why are you interested in working at ${companyText}?`,
    `What would success look like in your first 90 days at ${companyText}?`,
    "What questions would you ask the interviewer about the team or role?",
  ];

  const pool = [
    ...behavioral,
    ...(roleLower.includes("data") || roleLower.includes("analyst") || roleLower.includes("ml") ? data : technical),
    ...closing,
  ];

  const seed = `${roleText}|${companyText}|${Date.now()}`;
  const ordered = [...pool].sort((a, b) => {
    const av = (a.length + seed.length + a.charCodeAt(0)) % 13;
    const bv = (b.length + seed.length + b.charCodeAt(0)) % 13;
    return av - bv;
  });

  return ordered.slice(0, count).map((prompt, index) => ({
    id: `q${index + 1}`,
    prompt,
    tags: inferQuestionTags(prompt),
  }));
}

function inferQuestionTags(prompt) {
  const lowered = prompt.toLowerCase();
  const tags = [];
  if (/time|situation|feedback|ambiguity|balance/.test(lowered)) tags.push("behavioral");
  if (/debug|performance|technical|project|reliability/.test(lowered)) tags.push("technical");
  if (/data|analysis|model|insight/.test(lowered)) tags.push("data");
  if (/90 days|why are you interested|questions would you ask/.test(lowered)) tags.push("strategy");
  if (tags.length === 0) tags.push("general");
  return tags.slice(0, 3);
}

function generateHeuristicFeedback(question, answer) {
  const len = answer.split(/\s+/).filter(Boolean).length;
  const lowerAnswer = answer.toLowerCase();
  const lowerQuestion = question.toLowerCase();
  const hasSTAR = /situation|task|action|result|first|then|finally/i.test(answer);
  const mentionsImpact = /impact|result|metric|%|percent|reduced|improved|increased|decreased|saved|delivered/i.test(answer);
  const hasExample = /for example|for instance|specifically|when i|i handled|i led|i built|i implemented/i.test(answer);
  const hedging = /maybe|i guess|kind of|sort of|probably|i think/i.test(answer);

  const questionTerms = new Set(
    lowerQuestion
      .split(/\s+/)
      .map((token) => token.replace(/[^a-z]/g, ""))
      .filter((token) => token.length > 3)
  );
  const overlap = lowerAnswer
    .split(/\s+/)
    .map((token) => token.replace(/[^a-z]/g, ""))
    .filter((token) => questionTerms.has(token)).length;

  const strengths = [];
  const suggestions = [];

  let accuracy = 1;
  if (overlap >= 2) accuracy += 1;
  if (hasExample) accuracy += 1;
  if (mentionsImpact) accuracy += 1;
  if (len >= 45 && !hedging) accuracy += 1;
  if (len < 20) accuracy = Math.max(1, accuracy - 1);
  accuracy = Math.min(5, accuracy);

  let clearness = 1;
  if (len >= 35 && len <= 180) clearness += 1;
  if (hasSTAR) clearness += 2;
  if (hasExample) clearness += 1;
  if (len > 240) clearness -= 1;
  clearness = Math.max(1, Math.min(5, clearness));

  let confidence = 1;
  if (/\bi\b/.test(lowerAnswer)) confidence += 1;
  if (/i led|i owned|i built|i implemented|i drove|i resolved|i delivered/.test(lowerAnswer)) confidence += 2;
  if (!hedging) confidence += 1;
  if (mentionsImpact) confidence += 1;
  if (len < 20) confidence -= 1;
  confidence = Math.max(1, Math.min(5, confidence));

  const overallScore = Math.round((((accuracy * 0.5) + (clearness * 0.3) + (confidence * 0.2)) / 5) * 100);

  if (accuracy >= 4) strengths.push("The answer stays on-topic and supports the point with relevant detail.");
  if (clearness >= 4) strengths.push("The response is structured clearly and is easy to follow.");
  if (confidence >= 4) strengths.push("The answer sounds direct, professional, and ownership-oriented.");

  if (accuracy <= 3) suggestions.push("Answer the question more directly and add one concrete example.");
  if (clearness <= 3) suggestions.push("Use a clearer STAR-style structure so the response flows better.");
  if (confidence <= 3) suggestions.push("Use more direct ownership language and reduce hesitant phrasing.");
  if (!mentionsImpact) suggestions.push("Add a measurable outcome or result to make the answer more convincing.");

  const scoreLabel = (score) => {
    if (score <= 1) return "Needs work";
    if (score === 2) return "Developing";
    if (score === 3) return "Solid";
    if (score === 4) return "Strong";
    return "Excellent";
  };

  const summary =
    overallScore >= 80
      ? "This answer is strong overall: it is relevant, clear, and sounds credible."
      : overallScore >= 60
        ? "This answer is reasonably solid, but it would benefit from sharper detail or structure."
        : overallScore >= 40
          ? "This answer is on the right track, but it needs more structure and stronger support."
          : "This answer needs more development to feel complete, clear, and convincing.";

  return {
    summary,
    strengths: strengths.length ? strengths : ["The answer addresses the general topic of the question."],
    suggestions: suggestions.length ? suggestions : ["Nice work – minor tightening could improve flow."],
    metrics: {
      accuracy: {
        score: accuracy,
        label: scoreLabel(accuracy),
        reason: "Scored from question relevance, specificity, and internal support.",
      },
      clearness: {
        score: clearness,
        label: scoreLabel(clearness),
        reason: "Scored from structure, readability, and how easy the response is to follow.",
      },
      confidence: {
        score: confidence,
        label: scoreLabel(confidence),
        reason: "Scored from ownership language, directness, and level of hesitation.",
      },
    },
    overall_score: overallScore,
    evaluator: {
      provider: "local",
      method: "rubric_fallback",
    },
  };
}
