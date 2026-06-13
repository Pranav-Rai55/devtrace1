import React, { useEffect, useMemo, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { BACKEND_API } from "../config/api";

// All analysis calls go through the Backend proxy at /api/v1/analyze
// which then forwards to the ML service. This keeps auth (JWT cookie) in one place.
const ANALYZE_BASE = `${BACKEND_API}/api/v1`;

const ALL_STEPS = [
  { key: "clone",     title: "Cloning repository...",             icon: "done"   },
  { key: "structure", title: "Analyzing code structure...",       icon: "active" },
  { key: "ml",        title: "Detecting patterns with Python/ML...", icon: "db"  },
  { key: "security",  title: "Scanning security vulnerabilities...", icon: "shield" },
  { key: "report",    title: "Generating final report...",        icon: "check"  },
];

const LOGS_BY_STEP = {
  clone:     ["Initializing git client...", "Resolving repository URL...", "Cloning into working directory..."],
  structure: ["Parsing source tree...", "Building dependency graph...", "Optimizing architecture map..."],
  ml:        ["Extracting code patterns...", "Running ML heuristics...", "Suggesting refactors based on hotspots..."],
  security:  ["Scanning for OWASP Top 10 vulnerabilities...", "Checking dependencies for known CVEs..."],
  report:    ["Aggregating results...", "Generating final report...", "Finalizing output…"],
};

function IconDone() {
  return (
    <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-emerald-500/15 border border-emerald-500/30">
      <svg viewBox="0 0 24 24" className="h-6 w-6 text-emerald-400" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M20 6L9 17l-5-5" />
      </svg>
    </div>
  );
}

function IconActive() {
  return (
    <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-indigo-500/20 border border-indigo-500/30">
      <svg className="h-6 w-6 text-indigo-400 animate-spin" viewBox="0 0 24 24" fill="none">
        <circle className="opacity-30" cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="3" />
        <path d="M21 12a9 9 0 0 0-9-9" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
      </svg>
    </div>
  );
}

function IconIdle({ variant }) {
  const common = "h-6 w-6 text-gray-500";
  return (
    <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-white/5 border border-white/10">
      {variant === "db" ? (
        <svg viewBox="0 0 24 24" className={common} fill="none" stroke="currentColor" strokeWidth="2">
          <ellipse cx="12" cy="5" rx="7" ry="3" />
          <path d="M5 5v6c0 1.7 3.1 3 7 3s7-1.3 7-3V5" />
          <path d="M5 11v6c0 1.7 3.1 3 7 3s7-1.3 7-3v-6" />
        </svg>
      ) : variant === "shield" ? (
        <svg viewBox="0 0 24 24" className={common} fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M12 2l7 4v6c0 5-3 9-7 10-4-1-7-5-7-10V6l7-4z" />
        </svg>
      ) : (
        <svg viewBox="0 0 24 24" className={common} fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="12" cy="12" r="9" />
          <path d="M8 12l2 2 6-6" />
        </svg>
      )}
    </div>
  );
}

function StepCard({ state, title, sub, iconVariant }) {
  const box =
    state === "done"
      ? "border-white/10 bg-white/[0.03]"
      : state === "active"
      ? "border-indigo-500/30 bg-indigo-500/[0.06]"
      : "border-white/10 bg-white/[0.02] opacity-55";

  return (
    <div className={`flex items-center gap-5 rounded-3xl border p-6 transition-all duration-500 ${box}`}>
      {state === "done" ? (
        <IconDone />
      ) : state === "active" ? (
        <IconActive />
      ) : (
        <IconIdle variant={iconVariant} />
      )}
      <div>
        <p className={`font-semibold ${state === "active" ? "text-indigo-300" : "text-white"}`}>
          {title}
        </p>
        {sub && <p className="mt-1 text-sm text-indigo-400/80">{sub}</p>}
      </div>
    </div>
  );
}

function Terminal({ logs, progress }) {
  return (
    <div className="relative rounded-3xl border border-white/10 bg-black shadow-[0_0_90px_rgba(99,102,241,0.25)] overflow-hidden">
      <div className="pointer-events-none absolute -inset-24 bg-indigo-500/20 blur-3xl" />
      <div className="relative">
        <div className="flex items-center justify-between px-6 py-4 border-b border-white/10 bg-white/[0.02]">
          <div className="flex items-center gap-2">
            <span className="h-3 w-3 rounded-full bg-red-500/40" />
            <span className="h-3 w-3 rounded-full bg-yellow-500/40" />
            <span className="h-3 w-3 rounded-full bg-green-500/40" />
          </div>
          <div className="text-xs text-gray-400 flex items-center gap-2">
            <span className="text-indigo-400">{">_"}</span> analysis-console.log
          </div>
        </div>
        <div className="px-6 py-6 h-[450px] overflow-y-auto">
          {logs.map((line, i) => (
            <div key={i} className="flex gap-3 py-2 text-sm text-gray-300">
              <span className="text-indigo-400">{">"}</span>
              <span className="font-mono">{line}</span>
            </div>
          ))}
          <div className="flex gap-3 py-2 text-sm text-gray-300">
            <span className="text-indigo-400">_</span>
            <span className="font-mono animate-pulse"> </span>
          </div>
        </div>
        <div className="px-6 pb-6">
          <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
            <div className="flex items-center justify-between text-xs text-gray-400">
              <span>ENGINE LOAD</span>
              <span className="text-indigo-300">{progress}%</span>
            </div>
            <div className="mt-3 h-2 w-full rounded-full bg-white/10 overflow-hidden">
              <div className="h-full rounded-full bg-indigo-500 transition-all duration-700" style={{ width: `${progress}%` }} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function ProcessingScreen({ repoName = "" }) {
  const location = useLocation();
  const navigate = useNavigate();
  const repoUrl = location.state?.repoUrl || repoName;
  const [taskId, setTaskId] = useState("");
  const [activeIndex, setActiveIndex] = useState(0);
  const [doneUpTo, setDoneUpTo] = useState(-1);
  const [progress, setProgress] = useState(0);
  const [logs, setLogs] = useState(["[...]: Waiting to start analysis..."]);
  const [error, setError] = useState("");

  const pollRef = useRef(null);

  const stepState = useMemo(() => {
    return ALL_STEPS.map((s, idx) => {
      if (idx <= doneUpTo) return "done";
      if (idx === activeIndex) return "active";
      return "idle";
    });
  }, [activeIndex, doneUpTo]);

  const pushLog = (message) => {
    setLogs((prev) => [...prev, message]);
  };

  const setAnalysisStep = (value) => {
    if (value < 25)       { setActiveIndex(0); setDoneUpTo(-1); }
    else if (value < 50)  { setActiveIndex(1); setDoneUpTo(0);  }
    else if (value < 70)  { setActiveIndex(2); setDoneUpTo(1);  }
    else if (value < 90)  { setActiveIndex(3); setDoneUpTo(2);  }
    else if (value < 100) { setActiveIndex(4); setDoneUpTo(3);  }
    else                  { setActiveIndex(-1); setDoneUpTo(4); }
  };

  const pollStatus = async (id) => {
    try {
      // Poll through the Backend proxy — keeps auth consistent
      const response = await fetch(`${ANALYZE_BASE}/analyze/${id}`, {
        credentials: "include",
      });
      let data;
      try {
        data = await response.json();
      } catch {
        throw new Error("Unable to parse analysis status response.");
      }
      if (!response.ok) {
        throw new Error(data.detail || "Unable to fetch analysis status.");
      }

      const nextProgress = data.progress ?? progress;
      setProgress(nextProgress);
      setAnalysisStep(nextProgress);

      if (data.message) {
        pushLog(`[${new Date().toLocaleTimeString()}] ${data.message}`);
      }

      if (data.status === "completed") {
        pushLog(`[${new Date().toLocaleTimeString()}] ✅ Analysis complete.`);
        setTimeout(() => {
          navigate("/dashboard", { state: { report: data.report } });
        }, 1800);
        return;
      }

      if (data.status === "failed") {
        throw new Error(data.error || "Analysis failed.");
      }

      pollRef.current = window.setTimeout(() => pollStatus(id), 1200);
    } catch (err) {
      setError(err.message);
      pushLog(`[${new Date().toLocaleTimeString()}] Error: ${err.message}`);
    }
  };

  const startAnalysis = async () => {
    if (!repoUrl) {
      navigate("/");
      return;
    }

    try {
      setLogs([`[${new Date().toLocaleTimeString()}] Starting analysis for ${repoUrl}...`]);
      setProgress(5);
      setAnalysisStep(0);

      // POST to Backend proxy — Backend forwards to ML service
      const response = await fetch(`${ANALYZE_BASE}/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ repo_url: repoUrl }),
      });

      let data;
      try {
        data = await response.json();
      } catch {
        throw new Error("Failed to parse analysis start response.");
      }
      if (!response.ok) {
        throw new Error(data.detail || "Failed to start analysis.");
      }

      setTaskId(data.task_id);
      pushLog(`[${new Date().toLocaleTimeString()}] Task created: ${data.task_id}`);
      pushLog("[...]: Waiting for backend status updates...");
      pollStatus(data.task_id);
    } catch (err) {
      setError(err.message);
      pushLog(`[${new Date().toLocaleTimeString()}] Error: ${err.message}`);
    }
  };

  useEffect(() => {
    startAnalysis();
    return () => {
      if (pollRef.current) window.clearTimeout(pollRef.current);
    };
  }, []);

  const iconVariantByIndex = ["", "", "db", "shield", "check"];

  return (
    <section className="min-h-screen bg-transparent text-white px-6 py-14">
      <div className="mx-auto max-w-7xl">
        <div className="grid grid-cols-1 gap-10 lg:grid-cols-2 lg:items-start">
          {/* LEFT */}
          <div>
            <div className="mb-3 flex items-center gap-2 text-indigo-400 text-sm font-semibold tracking-widest">
              <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-indigo-500/15 border border-indigo-500/25">
                <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M21 12a9 9 0 1 1-9-9" />
                  <path d="M22 2l-4 4" />
                </svg>
              </span>
              ACTIVE ANALYSIS
            </div>

            <h1 className="text-4xl sm:text-5xl font-extrabold">Processing Repo</h1>

            <input
              value={repoUrl}
              readOnly
              className="mt-4 w-full max-w-xl rounded-xl border border-white/10 bg-white/[0.03] px-4 py-3 text-gray-300 outline-none"
            />

            <div className="mt-4 max-w-xl text-sm text-gray-300">
              {error ? (
                <p className="text-red-400">{error}</p>
              ) : (
                <p>{taskId ? `Task ID: ${taskId}` : "Starting analysis..."}</p>
              )}
            </div>

            <div className="mt-10 space-y-5 max-w-xl">
              {ALL_STEPS.map((s, idx) => (
                <StepCard
                  key={s.key}
                  state={stepState[idx]}
                  title={s.title}
                  sub={
                    stepState[idx] === "active"
                      ? "Status: Processing..."
                      : stepState[idx] === "done"
                      ? "Status: Complete"
                      : null
                  }
                  iconVariant={iconVariantByIndex[idx]}
                />
              ))}
            </div>
          </div>

          {/* RIGHT */}
          <div className="lg:pt-16">
            <Terminal logs={logs} progress={progress} />
          </div>
        </div>
      </div>
    </section>
  );
}
