DROP TABLE IF EXISTS resources;
DROP TABLE IF EXISTS answers;
DROP TABLE IF EXISTS interviews;
DROP TABLE IF EXISTS interview_answers;
DROP TABLE IF EXISTS interview_questions;
DROP TABLE IF EXISTS interview_sessions;
DROP TABLE IF EXISTS keyword_analyses;
DROP TABLE IF EXISTS feedback_reports;
DROP TABLE IF EXISTS resumes;
DROP TABLE IF EXISTS users;

CREATE TABLE users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  email TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  name TEXT NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE resumes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  file_path TEXT NOT NULL,
  parsed_json TEXT,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users (id)
);

CREATE TABLE feedback_reports (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  resume_id INTEGER NOT NULL,
  score INTEGER,
  summary TEXT,
  details_json TEXT,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (resume_id) REFERENCES resumes (id)
);

CREATE TABLE keyword_analyses (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  resume_id INTEGER NOT NULL,
  job_text TEXT,
  match_score REAL,
  missing_keywords_json TEXT,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (resume_id) REFERENCES resumes (id)
);

CREATE TABLE interview_sessions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users (id)
);

CREATE TABLE interview_questions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  text TEXT NOT NULL,
  category TEXT,
  difficulty TEXT
);

CREATE TABLE interview_answers (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id INTEGER NOT NULL,
  question_id INTEGER NOT NULL,
  answer_text TEXT NOT NULL,
  score INTEGER,
  FOREIGN KEY (session_id) REFERENCES interview_sessions (id),
  FOREIGN KEY (question_id) REFERENCES interview_questions (id)
);

CREATE TABLE interviews (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  role TEXT NOT NULL,
  company TEXT NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Career resources (articles, resume guides, interview tips)
CREATE TABLE resources (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  link  TEXT NOT NULL,
  type  TEXT NOT NULL CHECK (type IN ('article','resume','interview'))
);

-- Sample career resources
INSERT INTO resources (title, link, type) VALUES
  ('How to Write a Strong Tech Resume', 'https://www.coursera.org/articles/software-engineer-resume', 'resume'),
  ('Resume Checklist for CS Students', 'https://www.themuse.com/advice/your-resume-is-never-finished-checklist', 'resume'),
  ('Behavioral Interview: STAR Method Guide', 'https://www.indeed.com/career-advice/interviewing/star-interview-method', 'interview'),
  ('Common CS Interview Questions & Tips', 'https://www.interviewcake.com/article/python/coding-interview-tips', 'interview'),
  ('Career Planning for New Grads', 'https://www.princetonreview.com/career-advice/career-planning-for-college-students', 'article'),
  ('Networking Tips for Students', 'https://www.linkedin.com/pulse/networking-tips-college-students', 'article');

CREATE TABLE answers (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  interview_id INTEGER NOT NULL,
  qid TEXT NOT NULL,
  prompt TEXT NOT NULL,
  answer TEXT NOT NULL,
  feedback_json TEXT,
  FOREIGN KEY (interview_id) REFERENCES interviews (id)
);
