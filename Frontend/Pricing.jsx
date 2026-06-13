import React, { useState } from "react";
import { useNavigate } from "react-router-dom";

export default function Hero() {
  const navigate = useNavigate();
  const [repoUrl, setRepoUrl] = useState("");
  const [error, setError] = useState("");

  const normalizeRepoUrl = (url) => {
    let value = url.trim();
    if (!value) return "";

    if (/^[a-zA-Z0-9_-]+\/[a-zA-Z0-9_-]+$/.test(value)) {
      value = `https://github.com/${value}`;
    }

    if (/^github\.com\//i.test(value)) {
      value = `https://${value}`;
    }

    if (/^http:\/\/github\.com\//i.test(value)) {
      value = value.replace(/^http:\/\//i, "https://");
    }

    value = value.replace(/\/$/, "");
    return value;
  };

  const validateRepoUrl = (url) => {
    const normalized = normalizeRepoUrl(url);
    const githubRegex = /^https:\/\/github\.com\/[a-zA-Z0-9_-]+\/[a-zA-Z0-9_-]+$/;
    return githubRegex.test(normalized);
  };

  const handleAnalyze = () => {
    if (!repoUrl.trim()) {
      setError("Please enter a GitHub repository URL.");
      return;
    }
    if (!validateRepoUrl(repoUrl)) {
      setError("Please enter a valid GitHub repository URL (e.g., github.com/username/repository).");
      return;
    }

    const normalizedUrl = normalizeRepoUrl(repoUrl);
    setError("");
    navigate("/loading", { state: { repoUrl: normalizedUrl } });
  };

  return (
    <section className="relative z-10 min-h-screen bg-transparent text-white flex flex-col items-center justify-center px-6 text-center">
      <div className="mb-6">
        <span className="rounded-full border border-indigo-500/40 bg-indigo-500/10 px-4 py-1 text-sm text-indigo-400">
          ⚡ AI-Powered Code Intelligence
        </span>
      </div>

      <h1 className="text-4xl md:text-6xl lg:text-7xl font-bold leading-tight max-w-4xl">
        Trace the Path to <br />
        <span className="bg-gradient-to-r from-indigo-400 to-purple-500 bg-clip-text text-transparent">
          Perfect Code
        </span>
      </h1>

      <p className="mt-6 max-w-2xl text-gray-400 text-lg">
        Analyze your GitHub repositories instantly. Get deep insights into
        quality, security, and complexity with AI-driven actionable fixes.
      </p>

      <div className="mt-10 flex w-full max-w-2xl flex-col items-center">
        <div className="flex w-full items-center rounded-2xl border border-white/10 bg-white/5 p-2 shadow-[0_0_40px_rgba(99,102,241,0.35)]">
          <div className="px-4 text-gray-400">
            <svg viewBox="0 0 24 24" className="h-5 w-5" fill="currentColor">
              <path d="M12 .5C5.73.5.75 5.48.75 11.75c0 4.98 3.24 9.2 7.73 10.69.56.1.77-.24.77-.54v-1.9c-3.14.68-3.8-1.34-3.8-1.34-.52-1.31-1.26-1.66-1.26-1.66-1.03-.7.08-.69.08-.69 1.14.08 1.74 1.17 1.74 1.17 1.01 1.73 2.65 1.23 3.29.94.1-.73.4-1.23.72-1.51-2.5-.28-5.13-1.25-5.13-5.57 0-1.23.44-2.24 1.17-3.03-.12-.28-.51-1.43.11-2.98 0 0 .96-.31 3.14 1.16.91-.25 1.88-.38 2.85-.38.97 0 1.94.13 2.85.38 2.18-1.47 3.14-1.16 3.14-1.16.62 1.55.23 2.7.11 2.98.73.79 1.17 1.8 1.17 3.03 0 4.33-2.63 5.28-5.14 5.56.41.36.77 1.06.77 2.14v3.18c0 .3.2.65.78.54 4.49-1.49 7.73-5.71 7.73-10.69C23.25 5.48 18.27.5 12 .5z" />
            </svg>
          </div>

          <input
            type="text"
            placeholder="github.com/username/repository"
            className="flex-1 bg-transparent text-gray-300 placeholder-gray-500 outline-none"
            value={repoUrl}
            onChange={(e) => setRepoUrl(e.target.value)}
          />

          <button
            className="rounded-xl bg-gradient-to-r from-indigo-500 to-purple-600 px-6 py-3 font-semibold hover:opacity-90 transition"
            onClick={handleAnalyze}
          >
            Analyze →
          </button>
        </div>
        {error && (
          <p className="mt-2 text-red-400 text-sm">{error}</p>
        )}
      </div>
    </section>
  );
}
