import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Timer, ChevronLeft, ChevronRight, Play, Pause, RefreshCw, Send, Sparkles, CheckCircle2, XCircle, BookOpenText, ListChecks } from "lucide-react";
import { api } from "./api";
import "./MockInterview.css";

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

  const questions = useMemo(() => SAMPLE_QUESTIONS, []);

  const [index, setIndex] = useLocalStorage("mi_index", 0);
  const [answers, setAnswers] = useLocalStorage("mi_answers", {});
  const [feedback, setFeedback] = useLocalStorage("mi_feedback", {});
  const [running, setRunning] = useLocalStorage("mi_running", false);
  const [remaining, setRemaining] = useLocalStorage("mi_remaining", secondsPerQ);
  const [reviewMode, setReviewMode] = useLocalStorage("mi_review", false);
  const [sessionId, setSessionId] = useLocalStorage("mi_sessionId", null);
  const [loading, setLoading] = useState(false);

  const timerRef = useRef(null);
  const current = questions[index];
  const progressValue = Math.round(((index + 1) / questions.length) * 100);

  const startInterview = useCallback(async () => {
    try {
      setLoading(true);
      // Create session on backend
      const response = await api.createInterviewSession({ role, company });
      setSessionId(response.session_id);
      setStarted(true);
      setIndex(0);
      setRemaining(secondsPerQ);
      setRunning(true);
    } catch (error) {
      console.error("Failed to create session:", error);
      // Still allow starting locally even if backend fails
      setStarted(true);
      setIndex(0);
      setRemaining(secondsPerQ);
      setRunning(true);
    } finally {
      setLoading(false);
    }
  }, [secondsPerQ, setIndex, setRemaining, setRunning, setStarted, role, company]);

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

  const next = () => setIndex((i) => Math.min(i + 1, questions.length - 1));
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
  };

  const answeredCount = useMemo(
    () => Object.values(answers).filter((v) => (v ?? "").trim().length > 0).length,
    [answers]
  );

  const unanswered = questions
    .map((q, i) => ({ i, q }))
    .filter(({ q }) => !answers[q.id] || !answers[q.id].trim());

  const onSubmitInterview = async () => {
    if (!sessionId) {
      // If no session, just show review mode
      setReviewMode(true);
      return;
    }
    
    try {
      setLoading(true);
      // Build answers with question prompts
      const answersWithPrompts = {};
      questions.forEach(q => {
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
      // Store final feedback if provided
      if (result.feedback) {
        setFeedback((prev) => ({ ...prev, ...result.feedback }));
      }
      console.log("Interview submitted:", result);
    } catch (error) {
      console.error("Failed to submit interview:", error);
      // Still show review mode even if submission fails
      setReviewMode(true);
    } finally {
      setLoading(false);
    }
  };

  const requestFeedback = async () => {
    const a = (answers[current.id] || "").trim();
    if (!a) return;
    
    try {
      setLoading(true);
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
      // Fallback to heuristic feedback if backend fails
      const fake = generateHeuristicFeedback(current.prompt, a);
      setFeedback((prev) => ({ ...prev, [current.id]: fake }));
    } finally {
      setLoading(false);
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

  return (
    <div className="mock-interview-container">
      <header className="mock-interview-header">
        <div>
          <h1>Mock Interview</h1>
          <p>Practice behavioral & role-specific questions with a timed flow and instant feedback.</p>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
          <span className="badge">{answeredCount}/{questions.length} answered</span>
          <span className={`badge ${reviewMode ? 'primary' : ''}`}>{reviewMode ? "Review" : "Practice"}</span>
        </div>
      </header>

      {!started ? (
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">Set up your session</h2>
            <p className="card-description">Customize context and pacing to get the most out of your practice.</p>
          </div>
          <div className="card-content" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
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
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.875rem', color: '#666' }}>
              <BookOpenText size={16}/> {questions.length} questions in this set
            </div>
            <button className="button primary lg" onClick={startInterview} disabled={loading}>
              <Play size={16} style={{ marginRight: '0.5rem' }} /> {loading ? "Starting..." : "Start practice"}
            </button>
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
                  <div style={{ marginTop: '0.5rem', fontSize: '0.75rem', color: '#666' }}>{progressValue}% complete</div>
                </div>
              </div>
            </div>

            <div className="card">
              <div className="card-header">
                <h3 className="card-title">Your answer</h3>
                <p className="card-description">Autosaves locally. Press <kbd style={{ padding: '0.125rem 0.25rem', borderRadius: '4px', background: '#f3f4f6' }}>Ctrl</kbd> + <kbd style={{ padding: '0.125rem 0.25rem', borderRadius: '4px', background: '#f3f4f6' }}>Enter</kbd> to go next.</p>
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
                  <Sparkles size={16} style={{ marginRight: '0.5rem' }} />{loading ? "Loading..." : "Get feedback"}
                </button>
                <div style={{ marginLeft: 'auto', display: 'flex', gap: '0.5rem' }}>
                  <button className="button outline" onClick={prev} disabled={index === 0}>
                    <ChevronLeft size={16} style={{ marginRight: '0.5rem' }} />Prev
                  </button>
                  <button className="button primary" onClick={next} disabled={index === questions.length - 1}>
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
                  <div style={{ fontSize: '0.875rem', color: '#666' }}>No feedback yet – write an answer and click <em>Get feedback</em>.</div>
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
                  {questions.map((q, i) => {
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
                <div style={{ fontSize: '0.75rem', color: '#666' }}>
                  {unanswered.length === 0 ? (
                    <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', color: '#059669' }}>
                      <CheckCircle2 size={14}/>All questions answered
                    </span>
                  ) : (
                    <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', color: '#d97706' }}>
                      <XCircle size={14}/>{unanswered.length} unanswered
                    </span>
                  )}
                </div>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <button className="button outline" onClick={exportJSON}>Export</button>
                  <button className="button primary" onClick={onSubmitInterview} disabled={loading}>
                    <Send size={16} style={{ marginRight: '0.5rem' }} />{loading ? "Submitting..." : "Submit"}
                  </button>
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
                  {questions.map((q, i) => (
                    <div key={q.id} className="review-item">
                      <h4>Q{i + 1}</h4>
                      <h5>{q.prompt}</h5>
                      <p>{answers[q.id] || <span style={{ color: '#666' }}>(no answer)</span>}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function formatTime(s) {
  const m = Math.floor(s / 60);
  const ss = s % 60;
  return `${m}:${ss.toString().padStart(2, "0")}`;
}

function FeedbackBox({ data }) {
  return (
    <div className="feedback-box">
      <div className="feedback-section">
        <h4>Summary</h4>
        <p style={{ fontSize: '0.875rem', lineHeight: '1.6' }}>{data.summary}</p>
      </div>
      <div className="feedback-section">
        <h4>Strengths</h4>
        <ul>
          {data.strengths.map((s, i) => (
            <li key={i}>{s}</li>
          ))}
        </ul>
      </div>
      <div className="feedback-section">
        <h4>Suggestions</h4>
        <ul>
          {data.suggestions.map((s, i) => (
            <li key={i}>{s}</li>
          ))}
        </ul>
      </div>
      <div style={{ fontSize: '0.75rem', color: '#666', marginTop: '1rem' }}>AI feedback from backend.</div>
    </div>
  );
}

// Very lightweight heuristic to mock AI feedback without a backend.
function generateHeuristicFeedback(question, answer) {
  const len = answer.split(/\s+/).filter(Boolean).length;
  const hasSTAR = /situation|task|action|result/i.test(answer);
  const mentionsImpact = /impact|result|metric|%|percent|reduced|improved|increased|decreased|saved/i.test(answer);

  const strengths = [];
  const suggestions = [];

  if (len > 120) strengths.push("Thorough explanation – strong depth.");
  if (hasSTAR) strengths.push("Uses STAR structure effectively.");
  if (mentionsImpact) strengths.push("Highlights measurable impact.");
  if (len <= 120) suggestions.push("Add depth with concise details (what, how, outcome). ");
  if (!hasSTAR) suggestions.push("Consider framing with STAR (Situation, Task, Action, Result).");
  if (!mentionsImpact) suggestions.push("Quantify results (metrics, % change, time saved).");

  return {
    summary: `~${len} words. ${hasSTAR ? "STAR detected." : "STAR not detected."} ${
      mentionsImpact ? "Impact signals detected." : "Add measurable results."
    }`,
    strengths: strengths.length ? strengths : ["Clear and direct communication."],
    suggestions: suggestions.length ? suggestions : ["Nice work – minor tightening could improve flow."],
  };
}
