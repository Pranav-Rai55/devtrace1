import React from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { API_BASE } from "../config/api";

export default function Navbar() {
  const navigate = useNavigate();
  const location = useLocation();

  function scrollToSection() {
    if (location.pathname === "/") {
      document.getElementById("about")?.scrollIntoView({ behavior: "smooth" });
    } else {
      navigate("/#about");
    }
  }

  return (
    <nav className="relative z-20 w-full border-b border-white/5 bg-black/35 text-white backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-6">
        {/* Left: Logo */}
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-[#3b2cff] text-sm font-bold">
            DT
          </div>
          <span className="text-lg font-semibold">DevTrace</span>
        </div>

        {/* Center: Links */}
        <div className="hidden md:flex items-center gap-10 text-sm text-gray-300">
          <ul className="flex gap-10">
            {["Features", "Enterprise", "Docs", "Pricing"].map((label) => (
              <li
                key={label}
                className="hover:text-white transition cursor-pointer"
                onClick={scrollToSection}
              >
                {label}
              </li>
            ))}
          </ul>
        </div>

        {/* Right: Actions */}
        <div className="flex items-center gap-5">
          <button
            className="text-gray-300 hover:text-white transition"
            onClick={() => { window.location.href = `${API_BASE}/api/auth/github`; }}
            aria-label="Sign in with GitHub"
          >
            <svg viewBox="0 0 24 24" className="h-5 w-5" fill="currentColor" aria-hidden="true">
              <path d="M12 .5C5.73.5.75 5.48.75 11.75c0 4.98 3.24 9.2 7.73 10.69.56.1.77-.24.77-.54v-1.9c-3.14.68-3.8-1.34-3.8-1.34-.52-1.31-1.26-1.66-1.26-1.66-1.03-.7.08-.69.08-.69 1.14.08 1.74 1.17 1.74 1.17 1.01 1.73 2.65 1.23 3.29.94.1-.73.4-1.23.72-1.51-2.5-.28-5.13-1.25-5.13-5.57 0-1.23.44-2.24 1.17-3.03-.12-.28-.51-1.43.11-2.98 0 0 .96-.31 3.14 1.16.91-.25 1.88-.38 2.85-.38.97 0 1.94.13 2.85.38 2.18-1.47 3.14-1.16 3.14-1.16.62 1.55.23 2.7.11 2.98.73.79 1.17 1.8 1.17 3.03 0 4.33-2.63 5.28-5.14 5.56.41.36.77 1.06.77 2.14v3.18c0 .3.2.65.78.54 4.49-1.49 7.73-5.71 7.73-10.69C23.25 5.48 18.27.5 12 .5z" />
            </svg>
          </button>

          <button
            onClick={() => navigate("/signup")}
            className="flex items-center gap-2 text-sm text-gray-300 hover:text-white transition"
          >
            <span className="text-base">🐙</span>
            Sign In
          </button>

          <button
            onClick={() => navigate("/login")}
            className="rounded-lg bg-white px-5 py-2 text-sm font-semibold text-black hover:bg-gray-200 transition"
          >
            Get Started
          </button>
        </div>
      </div>

      <div className="h-px w-full bg-white/10" />
    </nav>
  );
}
