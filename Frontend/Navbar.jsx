import React from "react";

function Card({ icon, title, desc }) {
  return (
    <div className="relative rounded-3xl border border-white/10 bg-white/[0.03] p-10 shadow-[0_0_60px_rgba(0,0,0,0.6)]">
      {/* top fade */}
      <div className="pointer-events-none absolute inset-0 rounded-3xl bg-gradient-to-b from-white/5 to-transparent opacity-40" />

      {/* icon box */}
      <div className="relative mb-8 flex h-14 w-14 items-center justify-center rounded-2xl bg-white/5 border border-white/10">
        {icon}
      </div>

      <h3 className="relative text-2xl font-semibold">{title}</h3>
      <p className="relative mt-4 text-gray-400 leading-relaxed">{desc}</p>
    </div>
  );
}

export default function Features() {
  return (
    <section
      id="1"
      className="relative border-t border-white/[0.06] bg-transparent text-white py-20 px-6"
    >
      <div className="mx-auto max-w-7xl">
        <div className="grid grid-cols-1 gap-8 md:grid-cols-3">
          <Card
            title="Security Audit"
            desc="Deep scan for vulnerabilities, secret leaks, and insecure dependencies using ML models."
            icon={
              <svg
                viewBox="0 0 24 24"
                className="h-6 w-6 text-indigo-400"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <path d="M12 2l7 4v6c0 5-3 9-7 10-4-1-7-5-7-10V6l7-4z" />
              </svg>
            }
          />

          <Card
            title="Code Quality"
            desc="Detect code smells, maintainability issues, and technical debt with actionable refactors."
            icon={
              <svg
                viewBox="0 0 24 24"
                className="h-6 w-6 text-indigo-400"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <path d="M8 9l-3 3 3 3" />
                <path d="M16 9l3 3-3 3" />
                <path d="M10 19l4-14" />
              </svg>
            }
          />

          <Card
            title="Architecture Insights"
            desc="Visualize component dependencies and system architecture through automated mapping."
            icon={
              <svg
                viewBox="0 0 24 24"
                className="h-6 w-6 text-indigo-400"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <circle cx="11" cy="11" r="7" />
                <path d="M21 21l-4.3-4.3" />
              </svg>
            }
          />
        </div>
      </div>
    </section>
  );
}
