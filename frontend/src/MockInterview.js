import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { motion } from "framer-motion";
import { Timer, ChevronLeft, ChevronRight, Play, Pause, RefreshCw, Send, Sparkles, CheckCircle2, XCircle, BookOpenText, ListChecks } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";

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
 * Tailwind + shadcn/ui + framer-motion
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

  const timerRef = useRef(null);
  const current = questions[index];
  const progressValue = Math.round(((index + 1) / questions.length) * 100);

  const startInterview = useCallback(() => {
    setStarted(true);
    setIndex(0);
    setRemaining(secondsPerQ);
    setRunning(true);
  }, [secondsPerQ, setIndex, setRemaining, setRunning, setStarted]);

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
  };

  const answeredCount = useMemo(
    () => Object.values(answers).filter((v) => (v ?? "").trim().length > 0).length,
    [answers]
  );

  const unanswered = questions
    .map((q, i) => ({ i, q }))
    .filter(({ q }) => !answers[q.id] || !answers[q.id].trim());

  const onSubmitInterview = async () => {
    setReviewMode(true);
    // Optional: send all answers to backend for AI scoring/feedback
    // await fetch("/api/interview/submit", { method: "POST", body: JSON.stringify({ role, company, answers }) })
  };

  const requestFeedback = async () => {
    const a = (answers[current.id] || "").trim();
    if (!a) return;
    // Stubbed feedback request – replace with your backend call
    // const res = await fetch("/api/feedback", { method: "POST", body: JSON.stringify({ question: current.prompt, answer: a, role, company }) });
    // const data = await res.json();
    const fake = generateHeuristicFeedback(current.prompt, a);
    setFeedback((prev) => ({ ...prev, [current.id]: fake }));
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
    <div className="mx-auto max-w-6xl p-4 md:p-8 space-y-6">
      <header className="flex items-center justify-between">
        <div className="space-y-1">
          <h1 className="text-2xl md:text-3xl font-semibold tracking-tight">Mock Interview</h1>
          <p className="text-sm text-muted-foreground">Practice behavioral & role-specific questions with a timed flow and instant feedback.</p>
        </div>
        <div className="hidden md:flex items-center gap-2">
          <Badge variant="secondary" className="text-xs">{answeredCount}/{questions.length} answered</Badge>
          <Badge className="text-xs" variant={reviewMode ? "default" : "outline"}>{reviewMode ? "Review" : "Practice"}</Badge>
        </div>
      </header>

      {!started ? (
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
          <Card className="rounded-2xl">
            <CardHeader>
              <CardTitle>Set up your session</CardTitle>
              <CardDescription>Customize context and pacing to get the most out of your practice.</CardDescription>
            </CardHeader>
            <CardContent className="grid md:grid-cols-3 gap-4">
              <div>
                <label className="text-sm font-medium">Role / Track</label>
                <Input value={role} onChange={(e) => setRole(e.target.value)} placeholder="Software Engineer Intern" />
              </div>
              <div>
                <label className="text-sm font-medium">Company</label>
                <Input value={company} onChange={(e) => setCompany(e.target.value)} placeholder="Nutanix, AA, UTSW" />
              </div>
              <div>
                <label className="text-sm font-medium">Seconds per question</label>
                <Input
                  type="number"
                  min={30}
                  max={600}
                  value={secondsPerQ}
                  onChange={(e) => setSecondsPerQ(Number(e.target.value) || DEFAULT_SECONDS)}
                />
              </div>
            </CardContent>
            <CardFooter className="flex items-center justify-between">
              <div className="text-sm text-muted-foreground flex items-center gap-2"><BookOpenText size={16}/> {questions.length} questions in this set</div>
              <Button size="lg" onClick={startInterview}>
                <Play className="mr-2 h-4 w-4" /> Start practice
              </Button>
            </CardFooter>
          </Card>
        </motion.div>
      ) : (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="grid lg:grid-cols-[2fr_3fr] gap-6">
          {/* Left: question & nav */}
          <div className="space-y-4">
            <Card className="rounded-2xl">
              <CardHeader className="space-y-2">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-xl">Question {index + 1}</CardTitle>
                  <div className="flex items-center gap-2">
                    <Timer size={18} />
                    <span className={"tabular-nums font-mono " + (remaining <= 10 ? "text-red-600" : "")}>{formatTime(remaining)}</span>
                    <Button size="icon" variant="ghost" onClick={() => setRunning((r) => !r)} aria-label="Toggle timer">
                      {running ? <Pause size={18} /> : <Play size={18} />}
                    </Button>
                    <Button size="icon" variant="ghost" onClick={() => { setRemaining(secondsPerQ); setRunning(true); }} aria-label="Reset timer">
                      <RefreshCw size={18} />
                    </Button>
                  </div>
                </div>
                <CardDescription className="flex flex-wrap gap-2">
                  {current.tags?.map((t) => (
                    <Badge key={t} variant="outline" className="rounded-full">{t}</Badge>
                  ))}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-base leading-relaxed">{current.prompt}</p>
              </CardContent>
              <CardFooter className="flex items-center justify-between">
                <div className="w-full">
                  <Progress value={progressValue} className="h-2" />
                  <div className="mt-2 text-xs text-muted-foreground">{progressValue}% complete</div>
                </div>
              </CardFooter>
            </Card>

            <Card className="rounded-2xl">
              <CardHeader>
                <CardTitle>Your answer</CardTitle>
                <CardDescription>Autosaves locally. Press <kbd className="px-1 py-0.5 rounded bg-muted">Ctrl</kbd> + <kbd className="px-1 py-0.5 rounded bg-muted">Enter</kbd> to go next.</CardDescription>
              </CardHeader>
              <CardContent>
                <Textarea
                  className="min-h-[200px]"
                  value={answers[current.id] || ""}
                  onChange={(e) => updateAnswer(current.id, e.target.value)}
                  placeholder="Structure with STAR: Situation, Task, Action, Result..."
                />
              </CardContent>
              <CardFooter className="flex flex-wrap gap-2">
                <Button variant="secondary" onClick={requestFeedback}><Sparkles className="mr-2 h-4 w-4"/>Get feedback</Button>
                <div className="ml-auto flex gap-2">
                  <Button variant="outline" onClick={prev} disabled={index === 0}><ChevronLeft className="mr-2 h-4 w-4"/>Prev</Button>
                  <Button onClick={next} disabled={index === questions.length - 1}>Next<ChevronRight className="ml-2 h-4 w-4"/></Button>
                </div>
              </CardFooter>
            </Card>
          </div>

          {/* Right: feedback & quick nav */}
          <div className="space-y-4">
            <Card className="rounded-2xl">
              <CardHeader>
                <CardTitle>AI feedback</CardTitle>
                <CardDescription>Heuristic demo – replace with your backend for real-time scoring.</CardDescription>
              </CardHeader>
              <CardContent>
                {feedback[current.id] ? (
                  <FeedbackBox data={feedback[current.id]} />
                ) : (
                  <div className="text-sm text-muted-foreground">No feedback yet – write an answer and click <em>Get feedback</em>.</div>
                )}
              </CardContent>
            </Card>

            <Card className="rounded-2xl">
              <CardHeader>
                <CardTitle className="flex items-center gap-2"><ListChecks size={18}/> Quick navigator</CardTitle>
                <CardDescription>Jump to any question and see which ones need attention.</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-5 gap-2">
                  {questions.map((q, i) => {
                    const done = (answers[q.id] || "").trim().length > 0;
                    return (
                      <button
                        key={q.id}
                        onClick={() => jumpTo(i)}
                        className={`rounded-xl border text-sm py-2 transition ${
                          i === index ? "border-primary ring-2 ring-primary/30" : "border-muted"
                        } ${done ? "bg-green-50" : "bg-muted/30"}`}
                        title={q.prompt}
                      >
                        {i + 1}
                      </button>
                    );
                  })}
                </div>
              </CardContent>
              <CardFooter className="flex items-center justify-between">
                <div className="text-xs text-muted-foreground">
                  {unanswered.length === 0 ? (
                    <span className="flex items-center gap-1 text-emerald-700"><CheckCircle2 size={14}/>All questions answered</span>
                  ) : (
                    <span className="flex items-center gap-1 text-amber-700"><XCircle size={14}/>{unanswered.length} unanswered</span>
                  )}
                </div>
                <div className="flex gap-2">
                  <Button variant="outline" onClick={exportJSON}>Export</Button>
                  <Button onClick={onSubmitInterview}><Send className="mr-2 h-4 w-4"/>Submit</Button>
                </div>
              </CardFooter>
            </Card>

            {reviewMode && (
              <Card className="rounded-2xl">
                <CardHeader>
                  <CardTitle>Review</CardTitle>
                  <CardDescription>Spot-check answers before finalizing.</CardDescription>
                </CardHeader>
                <CardContent className="space-y-3 max-h-[300px] overflow-auto pr-2">
                  {questions.map((q, i) => (
                    <div key={q.id} className="rounded-xl border p-3">
                      <div className="text-xs text-muted-foreground mb-1">Q{i + 1}</div>
                      <div className="font-medium mb-1">{q.prompt}</div>
                      <div className="text-sm whitespace-pre-wrap">{answers[q.id] || <span className="text-muted-foreground">(no answer)</span>}</div>
                    </div>
                  ))}
                </CardContent>
              </Card>
            )}
          </div>
        </motion.div>
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
    <div className="space-y-3">
      <div>
        <div className="text-xs uppercase text-muted-foreground mb-1">Summary</div>
        <p className="text-sm leading-relaxed">{data.summary}</p>
      </div>
      <div>
        <div className="text-xs uppercase text-muted-foreground mb-1">Strengths</div>
        <ul className="list-disc pl-5 text-sm space-y-1">
          {data.strengths.map((s, i) => (
            <li key={i}>{s}</li>
          ))}
        </ul>
      </div>
      <div>
        <div className="text-xs uppercase text-muted-foreground mb-1">Suggestions</div>
        <ul className="list-disc pl-5 text-sm space-y-1">
          {data.suggestions.map((s, i) => (
            <li key={i}>{s}</li>
          ))}
        </ul>
      </div>
      <div className="text-xs text-muted-foreground">Heuristic feedback – demo only.</div>
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
