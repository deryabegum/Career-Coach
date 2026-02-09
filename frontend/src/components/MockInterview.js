import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Timer, ChevronLeft, ChevronRight, RefreshCw, Sparkles, CheckCircle2, Square } from "lucide-react";
import { api } from "../api"; 
import "./MockInterview.css";

const DEFAULT_SECONDS = 120;

const SAMPLE_QUESTIONS = [
  { id: "q1", prompt: "Tell me about yourself and why you're interested in this role.", tags: ["behavioral", "intro"] },
  { id: "q2", prompt: "Describe a challenging bug or issue you solved. What was your approach and outcome?", tags: ["problem-solving", "technical"] },
  { id: "q3", prompt: "Walk me through a project you are most proud of. What was your role?", tags: ["project", "leadership"] },
  { id: "q4", prompt: "How do you handle tight deadlines and conflicting priorities?", tags: ["behavioral", "time-management"] },
  { id: "q5", prompt: "Do you have any questions for us?", tags: ["reverse-interview"] },
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
    localStorage.setItem(key, JSON.stringify(state));
  }, [key, state]);
  return [state, setState];
}

export default function MockInterview() {
  // --- STATE MANAGEMENT ---
  const [started, setStarted] = useLocalStorage("mi_started", false);
  const [role, setRole] = useLocalStorage("mi_role", "Software Engineer");
  const [company, setCompany] = useLocalStorage("mi_company", "Tech Corp");
  const [secondsPerQ, setSecondsPerQ] = useLocalStorage("mi_secondsPerQ", DEFAULT_SECONDS);
  
  const [index, setIndex] = useLocalStorage("mi_index", 0);
  const [answers, setAnswers] = useLocalStorage("mi_answers", {});
  const [feedback, setFeedback] = useLocalStorage("mi_feedback", {});
  const [running, setRunning] = useLocalStorage("mi_running", false);
  const [remaining, setRemaining] = useLocalStorage("mi_remaining", secondsPerQ);
  const [reviewMode, setReviewMode] = useLocalStorage("mi_review", false);
  const [sessionId, setSessionId] = useLocalStorage("mi_sessionId", null);
  const [loading, setLoading] = useState(false);

  // --- VIDEO / AUDIO STATE ---
  const [stream, setStream] = useState(null);
  const [isRecording, setIsRecording] = useState(false);
  const [videoUrl, setVideoUrl] = useState(null);
  const videoRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);

  // --- SPEECH RECOGNITION REF ---
  const recognitionRef = useRef(null);

  const questions = useMemo(() => SAMPLE_QUESTIONS, []);
  const current = questions[index];
  const timerRef = useRef(null);
  const progressValue = Math.round(((index + 1) / questions.length) * 100);

  // --- RESET FUNCTION (FIXES THE LOOP ISSUE) ---
  const handleReset = () => {
    // 1. Reset all local storage states to default
    setStarted(false);
    setReviewMode(false);
    setAnswers({});
    setFeedback({});
    setIndex(0);
    setSessionId(null);
    setRunning(false);
    setRemaining(secondsPerQ);
    
    // 2. Stop any active media
    stopCamera();
  };

  // --- CAMERA FUNCTIONS ---
  const startCamera = async () => {
    try {
      const mediaStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
      setStream(mediaStream);
      if (videoRef.current) {
        videoRef.current.srcObject = mediaStream;
      }
    } catch (err) {
      console.error("Camera error:", err);
      alert("Could not access camera/microphone.");
    }
  };

  const stopCamera = () => {
    if (stream) {
      stream.getTracks().forEach(track => track.stop());
      setStream(null);
    }
  };

  const startRecording = () => {
    if (!stream) return;
    setIsRecording(true);
    chunksRef.current = [];
    
    // 1. Start Video Recording
    const recorder = new MediaRecorder(stream, { mimeType: 'video/webm' });
    mediaRecorderRef.current = recorder;

    recorder.ondataavailable = (e) => {
      if (e.data.size > 0) chunksRef.current.push(e.data);
    };

    recorder.onstop = () => {
      const blob = new Blob(chunksRef.current, { type: 'video/webm' });
      const url = URL.createObjectURL(blob);
      setVideoUrl(url);
    };

    recorder.start();

    // 2. Start Speech Recognition (if supported)
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      recognitionRef.current = new SpeechRecognition();
      recognitionRef.current.continuous = true; // Keep listening
      recognitionRef.current.interimResults = true; // Show results as they are spoken

      recognitionRef.current.onresult = (event) => {
        let finalTranscript = '';
        for (let i = event.resultIndex; i < event.results.length; ++i) {
          if (event.results[i].isFinal) {
            finalTranscript += event.results[i][0].transcript + ' ';
          }
        }
        
        // Append new text to existing answer
        if (finalTranscript) {
          setAnswers(prev => ({
            ...prev,
            [current.id]: (prev[current.id] || "") + finalTranscript
          }));
        }
      };

      recognitionRef.current.onerror = (event) => {
        console.error("Speech recognition error", event.error);
      };

      try {
        recognitionRef.current.start();
      } catch (e) {
        console.error("Failed to start speech recognition:", e);
      }
    } else {
      console.warn("Browser does not support Speech Recognition.");
    }
  };

  const stopRecording = () => {
    // 1. Stop Video
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }

    // 2. Stop Speech Recognition
    if (recognitionRef.current) {
      recognitionRef.current.stop();
      recognitionRef.current = null;
    }
  };

  // --- INTERVIEW LOGIC ---
  const startInterview = useCallback(async () => {
    setLoading(true);
    try {
      // 1. Create Backend Session
      const response = await api.createInterviewSession({ role, company });
      setSessionId(response.session_id);
      
      // 2. Initialize UI
      setStarted(true);
      setIndex(0);
      setRemaining(secondsPerQ);
      setRunning(true);
      
      // 3. Auto-start Camera
      await startCamera();
    } catch (error) {
      console.error("Failed to start:", error);
      // Fallback: start offline if backend fails
      setStarted(true);
      await startCamera();
    } finally {
      setLoading(false);
    }
  }, [role, company, secondsPerQ, setIndex, setRemaining, setRunning, setSessionId, setStarted]);

  // Timer logic
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
  }, [running, setRemaining]);

  // Reset logic when question changes
  useEffect(() => {
    if (!started) return;
    setRemaining(secondsPerQ);
    // Reset video for new question
    setVideoUrl(null);
    setIsRecording(false); 
  }, [index, secondsPerQ, started, setRemaining]);

  // Cleanup on unmount
  useEffect(() => {
    return () => stopCamera();
  }, []);

  const next = () => setIndex((i) => Math.min(i + 1, questions.length - 1));
  const prev = () => setIndex((i) => Math.max(i - 1, 0));
  const updateAnswer = (qid, text) => setAnswers((prev) => ({ ...prev, [qid]: text }));

  const requestFeedback = async () => {
    const a = (answers[current.id] || "").trim();
    if (!a) return;
    
    setLoading(true);
    // Clear old feedback so user sees something is happening
    setFeedback((prev) => {
      const newState = { ...prev };
      delete newState[current.id];
      return newState;
    });

    try {
      const data = await api.getInterviewFeedback({
        session_id: sessionId,
        qid: current.id,
        question_prompt: current.prompt,
        answer_text: a,
        role, company
      });
      setFeedback((prev) => ({ ...prev, [current.id]: data }));
    } catch (error) {
      console.error("Feedback error, falling back to local heuristic:", error);
      // Fallback to local heuristic if backend fails or is not implemented
      const localFeedback = generateHeuristicFeedback(current.prompt, a);
      setFeedback((prev) => ({ ...prev, [current.id]: localFeedback }));
    } finally {
      setLoading(false);
    }
  };

  const onSubmitInterview = async () => {
    setLoading(true);
    stopCamera(); // Stop camera on submit
    try {
      // Build answers object
      const answersWithPrompts = {};
      questions.forEach(q => {
        if (answers[q.id]) {
          answersWithPrompts[q.id] = { answer: answers[q.id], prompt: q.prompt };
        }
      });
      
      if (sessionId) {
        await api.submitInterview({
            session_id: sessionId,
            answers: answersWithPrompts,
            role, company
        });
      }
      setReviewMode(true);
    } catch (error) {
      console.error("Submit error:", error);
      setReviewMode(true);
    } finally {
      setLoading(false);
    }
  };

  const formatTime = (s) => {
    const m = Math.floor(s / 60);
    const ss = s % 60;
    return `${m}:${ss.toString().padStart(2, "0")}`;
  };

  // --- RENDER ---
  if (!started) {
    return (
      <div className="mock-interview-container">
        <div className="card start-card">
            <h1>Ready for your Interview?</h1>
            <p>We'll simulate a real interview environment with camera and timer.</p>
            
            <div className="input-group">
                <label>Target Role</label>
                <input className="input" value={role} onChange={e => setRole(e.target.value)} />
            </div>
            <div className="input-group">
                <label>Company</label>
                <input className="input" value={company} onChange={e => setCompany(e.target.value)} />
            </div>
            <div className="input-group">
                <label>Time per Question (sec)</label>
                <input className="input" type="number" value={secondsPerQ} onChange={e => setSecondsPerQ(Number(e.target.value))} />
            </div>

            <button className="button primary lg" onClick={startInterview} disabled={loading}>
                {loading ? "Setting up..." : "Start Interview Simulation"}
            </button>
        </div>
      </div>
    );
  }

  if (reviewMode) {
     return (
        <div className="mock-interview-container">
            <div className="card">
                <h2>Interview Complete! 🎉</h2>
                <p>Great job practicing. Here are your answers.</p>
                <div className="review-list">
                    {questions.map((q, i) => (
                        <div key={q.id} className="review-item">
                            <h4>Q{i+1}: {q.prompt}</h4>
                            <strong>Your Answer:</strong>
                            <p>{answers[q.id] || "No answer provided."}</p>
                            {feedback[q.id] && (
                                <div className="feedback-summary">
                                    <strong>AI Feedback:</strong> {feedback[q.id].summary}
                                </div>
                            )}
                        </div>
                    ))}
                </div>
                {/* UPDATED BUTTON: Calls handleReset instead of window.location.reload */}
                <button className="button outline" onClick={handleReset} style={{marginTop: '20px'}}>
                    Start New Session
                </button>
            </div>
        </div>
     )
  }

  return (
    <div className="mock-interview-container">
      {/* Header with Progress */}
      <header className="mi-header">
        <div className="progress-container">
            <div className="progress-bar">
                <div className="progress-fill" style={{ width: `${progressValue}%` }}></div>
            </div>
            <span>Question {index + 1} of {questions.length}</span>
        </div>
        <div className="timer-badge">
            <Timer size={16} /> {formatTime(remaining)}
        </div>
      </header>

      <div className="mi-grid">
        {/* LEFT COLUMN: Question & Video */}
        <div className="mi-col-left">
            <div className="card question-card">
                <h3>{current.prompt}</h3>
                <div className="tags">
                    {current.tags.map(t => <span key={t} className="badge">{t}</span>)}
                </div>
            </div>

            <div className="card video-card">
                <div className="video-wrapper">
                    {videoUrl ? (
                        <video src={videoUrl} controls className="live-video" />
                    ) : (
                        <video ref={videoRef} autoPlay muted className="live-video mirrored" />
                    )}
                    
                    {isRecording && <div className="recording-indicator">🔴 REC</div>}
                </div>
                
                <div className="video-controls">
                    {!isRecording ? (
                        <button className="button danger" onClick={startRecording} disabled={!!videoUrl}>
                            <div className="dot"></div> Record Answer
                        </button>
                    ) : (
                        <button className="button warning" onClick={stopRecording}>
                            <Square size={16} fill="currentColor"/> Stop
                        </button>
                    )}
                    
                    {videoUrl && (
                        <button className="button outline" onClick={() => setVideoUrl(null)}>
                            <RefreshCw size={16}/> Retake
                        </button>
                    )}
                </div>
            </div>
        </div>

        {/* RIGHT COLUMN: Text Answer & AI Feedback */}
        <div className="mi-col-right">
            <div className="card answer-card">
                <div className="card-header">
                    <h4>Notes & Transcript</h4>
                    <span className="hint">Type your answer for AI analysis</span>
                </div>
                <textarea 
                    className="textarea" 
                    placeholder="Type your main points here or paste your transcript..."
                    value={answers[current.id] || ""}
                    onChange={(e) => updateAnswer(current.id, e.target.value)}
                />
                <div className="action-row">
                    <button className="button secondary sm" onClick={requestFeedback} disabled={loading || !answers[current.id]}>
                        <Sparkles size={14} style={{ marginRight: 5 }}/> 
                        {loading ? "Analyzing..." : "Get AI Feedback"}
                    </button>
                </div>
            </div>

            {feedback[current.id] && (
                <div className="card feedback-card">
                    <h4>AI Analysis</h4>
                    <p className="summary">{feedback[current.id].summary}</p>
                    <div className="feedback-details">
                        <div className="good">👍 {feedback[current.id].strengths[0]}</div>
                        <div className="improve">💡 {feedback[current.id].suggestions[0]}</div>
                    </div>
                </div>
            )}

            <div className="nav-controls">
                <button className="button outline" onClick={prev} disabled={index === 0}>
                    <ChevronLeft size={16}/> Prev
                </button>
                
                {index === questions.length - 1 ? (
                    <button className="button primary" onClick={onSubmitInterview}>
                        Finish & Submit <CheckCircle2 size={16} style={{ marginLeft: 5 }}/>
                    </button>
                ) : (
                    <button className="button primary" onClick={next}>
                        Next <ChevronRight size={16} style={{ marginLeft: 5 }}/>
                    </button>
                )}
            </div>
        </div>
      </div>
    </div>
  );
}

// --- LOCAL HEURISTIC FEEDBACK GENERATOR (ENHANCED) ---
// This acts as a robust fallback if the backend API fails.
// It detects the specific question topic and checks for relevant keywords.
function generateHeuristicFeedback(questionPrompt, answer) {
  const answerLower = answer.toLowerCase();
  const words = answer.split(/\s+/).filter(Boolean).length;
  const promptLower = questionPrompt.toLowerCase();
  
  const strengths = [];
  const suggestions = [];
  let score = 70; // Base score

  // 1. TOPIC DETECTION
  const isIntro = promptLower.includes("tell me about yourself") || promptLower.includes("introduce");
  const isConflict = promptLower.includes("conflict") || promptLower.includes("difficult") || promptLower.includes("disagreement");
  const isProject = promptLower.includes("project") || promptLower.includes("proud");
  const isTechnical = promptLower.includes("bug") || promptLower.includes("technical") || promptLower.includes("solved");

  // 2. CONTEXT-AWARE CHECKS
  if (isIntro) {
    if (answerLower.includes("background") || answerLower.includes("experience") || answerLower.includes("years")) {
      strengths.push("Good overview of experience.");
      score += 10;
    } else {
      suggestions.push("Try to mention your years of experience or background early on.");
    }
    if (answerLower.includes("hobby") || answerLower.includes("interest") || answerLower.includes("outside")) {
      strengths.push("Nice personal touch with interests.");
    }
  }

  if (isConflict || isProject) {
    if (answerLower.includes("situation") || answerLower.includes("task") || answerLower.includes("action") || answerLower.includes("result")) {
      strengths.push("Excellent use of STAR structure terminology.");
      score += 15;
    } else if (!answerLower.includes("result") && !answerLower.includes("outcome")) {
      suggestions.push("Ensure you clearly state the Result/Outcome of your actions.");
      score -= 5;
    }
  }

  if (isTechnical) {
    if (answerLower.includes("debug") || answerLower.includes("log") || answerLower.includes("test") || answerLower.includes("researched")) {
      strengths.push("Demonstrated a logical debugging process.");
    } else {
      suggestions.push("Be specific about the steps you took to solve the issue.");
    }
  }

  // 3. UNIVERSAL CHECKS
  // Length Check
  if (words < 40) {
    suggestions.push("The answer feels a bit brief. Elaborate on your specific contributions.");
    score -= 10;
  } else if (words > 300) {
    suggestions.push("This is quite detailed. Ensure you stay focused on the key points to keep the interviewer engaged.");
  } else {
    strengths.push("Good answer length, detailed but concise.");
  }

  // Metric Check
  const hasMetrics = /\d+%|\d+ percent|\d+ users|\d+ dollars|saved|reduced|increased/i.test(answerLower);
  if (hasMetrics) {
    strengths.push("Great job quantifying your impact with metrics.");
    score += 10;
  } else if (isProject || isTechnical) {
    suggestions.push("Try to add a quantifiable metric (e.g., 'reduced load time by 20%').");
  }

  // Sentiment / Confidence Words
  if (answerLower.includes("i believe") || answerLower.includes("maybe") || answerLower.includes("i think")) {
     suggestions.push("Avoid weak language like 'I think' or 'maybe'. Use 'I decided', 'I implemented', 'I ensured'.");
  }

  // Default Fallbacks
  if (strengths.length === 0) strengths.push("Answer is relevant to the question.");
  if (suggestions.length === 0) suggestions.push("Consider structuring your answer with a clear beginning, middle, and end.");

  // Construct Summary
  let summary = `This answer is ${words} words long. `;
  if (score > 85) summary += "Strong response with good structure and detail. ";
  else if (score > 70) summary += "Solid response, but could be sharpened with more specific examples. ";
  else summary += "A good start, but focuses too much on generalities. ";

  if (hasMetrics) summary += "The use of data points helps anchor your achievements.";

  return {
    summary: summary,
    strengths: strengths,
    suggestions: suggestions
  };
}
