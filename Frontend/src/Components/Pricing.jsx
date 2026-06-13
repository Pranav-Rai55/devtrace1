import React from "react";

const lightning = (
  <svg
    viewBox="0 0 24 24"
    className="h-5 w-5 text-indigo-400"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
  >
    <path d="M13 2L3 14h8l-1 8 11-14h-8l0-6z" />
  </svg>
);

function PricingCard({
  title,
  price,
  suffix,
  features,
  cta,
  highlighted = false,
}) {
  return (
    <div
      className={[
        "relative rounded-3xl border p-10 transition-transform duration-300 ease-out hover:scale-105",
        highlighted
          ? "border-indigo-500/80 bg-indigo-500/[0.06] shadow-[0_0_80px_rgba(99,102,241,0.18)]"
          : "border-white/10 bg-white/[0.03]",
      ].join(" ")}
    >
      {/* soft top gradient */}
      <div className="pointer-events-none absolute inset-0 rounded-3xl bg-gradient-to-b from-white/5 to-transparent opacity-40" />

      <div className="relative">
        <p className="text-xl font-semibold">{title}</p>

        <div className="mt-4 flex items-end gap-2">
          <p className="text-5xl font-extrabold">{price}</p>
          {suffix && <span className="pb-2 text-gray-400">{suffix}</span>}
        </div>

        <ul className="mt-8 space-y-4 text-gray-300">
          {features.map((f) => (
            <li key={f} className="flex items-center gap-3">
              <span>{lightning}</span>
              <span className="text-gray-300/90">{f}</span>
            </li>
          ))}
        </ul>

        <button
          className={[
            "mt-10 w-full rounded-2xl py-4 font-semibold transition",
            highlighted
              ? "bg-indigo-600 hover:bg-indigo-500 text-white"
              : "bg-white/5 hover:bg-white/10 text-white border border-white/10",
          ].join(" ")}
        >
          {cta}
        </button>
      </div>
    </div>
  );
}

export default function Pricing() {
  return (
    <section className="relative border-t border-white/[0.06] bg-transparent text-white py-20 px-6">
      <div className="mx-auto max-w-7xl">
        {/* heading */}
        <div className="text-center">
          <h2 className="text-4xl md:text-5xl font-bold">
            Simple, transparent pricing
          </h2>
          <p className="mt-3 text-gray-400">
            Choose the plan that&apos;s right for your team.
          </p>
        </div>

        {/* cards */}
        <div className="mt-14 grid grid-cols-1 gap-8 md:grid-cols-3 ">
          <PricingCard
            title="Starter"
            price="Free"
            
            features={[
              "3 Repositories",
              "Basic Security Scan",
              "Weekly Reports",
              "Public Repos only",
              "Best For beginner",
            ]}
            cta="Choose Starter"
          />

          <PricingCard
            title="Pro"
            price="$29"
            suffix="/mo"
            highlighted
            features={[
              "Unlimited Repositories",
              "AI Auto-fixes",
              "CI/CD Integration",
              "Private Repos",
              "Architecture Mapping",
            ]}
            cta="Choose Pro"
          />

          <PricingCard
            title="Enterprise"
            price="Custom"
            features={[
              "Self-hosted Option",
              "SAML SSO",
              "Custom ML Training",
              "Dedicated Support",
              "API Access",
            ]}
            cta="Choose Enterprise"
          />
        </div>
      </div>
    </section>
  );
}
