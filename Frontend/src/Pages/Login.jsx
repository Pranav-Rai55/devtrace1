import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { FaGithub } from "react-icons/fa";
import { FcGoogle } from "react-icons/fc";
import { API_BASE } from "../config/api";
import { AiOutlineClose } from "react-icons/ai";
import { FiEye, FiEyeOff } from "react-icons/fi";

export default function LoginModal({ open = true, onClose = () => {} }) {
  const [showPass, setShowPass] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const navigate = useNavigate();

  useEffect(() => {
    if (!open) return;
    const onKeyDown = (e) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open, onClose]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const response = await fetch(`${API_BASE}/api/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ email, password }),
      });

      const data = await response.json();

      if (response.ok) {
        localStorage.setItem("accessToken", data.accessToken);
        onClose();
        navigate("/dashboard");
      } else {
        setError(data.message || "Login failed. Please try again.");
      }
    } catch (err) {
      setError("Login failed. Please try again.");
      console.error("Login error:", err);
    } finally {
      setLoading(false);
    }
  };

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/22 p-3 sm:p-6 backdrop-blur-none"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
    >
      <div
        className="w-full sm:max-w-md rounded-3xl border border-white/15 bg-[#0b0b0f]/92 text-white shadow-[0_0_80px_rgba(0,0,0,0.55)] backdrop-blur-xl max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-5 sm:p-7">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-indigo-600 font-bold">
              DT
            </div>
            <h2 className="text-xl sm:text-2xl font-semibold">Welcome Back</h2>
          </div>
          <button
            onClick={() => { onClose(); navigate("/"); }}
            className="rounded-full p-2 text-gray-300 hover:bg-white/5 hover:text-white transition"
            aria-label="Close"
            type="button"
          >
            <AiOutlineClose className="h-5 w-5" />
          </button>
        </div>

        {/* Body */}
        <div className="px-5 sm:px-7 pb-6 sm:pb-7">
          <div className="flex flex-col gap-3">
            <button
              type="button"
              className="w-full rounded-xl bg-white text-black py-3 font-semibold flex items-center justify-center gap-2 hover:bg-gray-200 transition"
              onClick={() => { window.location.href = `${API_BASE}/api/auth/google`; }}
            >
              <FcGoogle className="h-5 w-5" />
              Continue with Google
            </button>
            <button
              type="button"
              className="w-full rounded-xl border border-white/15 bg-white/5 text-white py-3 font-semibold flex items-center justify-center gap-2 hover:bg-white/10 transition"
              onClick={() => { window.location.href = `${API_BASE}/api/auth/github`; }}
            >
              <FaGithub className="h-5 w-5" />
              Continue with GitHub
            </button>
          </div>

          <div className="my-6 flex items-center gap-3">
            <div className="h-px flex-1 bg-white/10" />
            <span className="text-xs text-gray-500">OR CONTINUE WITH EMAIL</span>
            <div className="h-px flex-1 bg-white/10" />
          </div>

          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <div>
              <label className="block text-sm text-gray-300">Email Address</label>
              <input
                type="email"
                placeholder="name@company.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="mt-2 w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-gray-200 placeholder:text-gray-500 outline-none focus:border-indigo-500/60"
                required
              />
            </div>

            <div>
              <label className="block text-sm text-gray-300">Password</label>
              <div className="mt-2 relative">
                <input
                  type={showPass ? "text" : "password"}
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 pr-12 text-gray-200 placeholder:text-gray-500 outline-none focus:border-indigo-500/60"
                  required
                  minLength={6}
                />
                <button
                  type="button"
                  onClick={() => setShowPass((s) => !s)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white transition"
                  aria-label="Toggle password"
                >
                  {showPass ? <FiEye className="h-5 w-5" /> : <FiEyeOff className="h-5 w-5" />}
                </button>
              </div>
            </div>

            {error && <p className="text-red-400 text-sm">{error}</p>}

            <button
              type="submit"
              disabled={loading}
              className="mt-2 w-full rounded-2xl bg-indigo-600 py-4 font-semibold hover:bg-indigo-500 transition disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? "Signing in..." : "Sign In"} <span className="ml-1">→</span>
            </button>
          </form>

          <p className="mt-6 text-center text-gray-400 text-sm">
            Don&apos;t have an account?{" "}
            <button
              type="button"
              onClick={() => { onClose(); navigate("/signup"); }}
              className="text-indigo-400 hover:text-indigo-300 font-semibold"
            >
              Sign up
            </button>
          </p>
        </div>

        <div className="border-t border-white/10 px-5 sm:px-7 py-4 text-center text-xs text-gray-500">
          🔒 SECURE ENTERPRISE ENCRYPTION
        </div>
      </div>
    </div>
  );
}
