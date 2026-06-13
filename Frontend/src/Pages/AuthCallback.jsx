import { useEffect } from "react";
import { useNavigate } from "react-router-dom";

export default function AuthCallback() {
  const navigate = useNavigate();

  const getMessage = () => {
    const search = new URLSearchParams(window.location.search);
    const qErr = search.get("error");

    const hash = window.location.hash.startsWith("#")
      ? window.location.hash.slice(1)
      : window.location.hash;
    const hashParams = new URLSearchParams(hash);
    const token = hashParams.get("access_token");

    if (qErr) {
      return qErr === "db"
        ? "The server could not reach the database (MongoDB). In Atlas: Network Access → add your IP or 0.0.0.0/0 for local testing, then restart the backend."
        : qErr === "no_email"
        ? "We could not read an email from your GitHub account. Try making a primary email visible or use Google."
        : "Sign-in was cancelled or failed. Try again.";
    }

    if (token) return "Sign-in successful! Redirecting to dashboard...";
    return "Missing token. Redirecting…";
  };

  const message = getMessage();

  useEffect(() => {
    const search = new URLSearchParams(window.location.search);
    const qErr = search.get("error");

    const hash = window.location.hash.startsWith("#")
      ? window.location.hash.slice(1)
      : window.location.hash;
    const hashParams = new URLSearchParams(hash);
    const token = hashParams.get("access_token");

    if (qErr) {
      const t = setTimeout(() => navigate("/login", { replace: true }), 2800);
      return () => clearTimeout(t);
    }

    if (token) {
      localStorage.setItem("accessToken", token);
      // Redirect to dashboard after OAuth login (not landing page)
      const t = setTimeout(() => navigate("/dashboard", { replace: true }), 1000);
      return () => clearTimeout(t);
    }

    const t = setTimeout(() => navigate("/login", { replace: true }), 1500);
    return () => clearTimeout(t);
  }, [navigate]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-transparent text-white">
      <p className="text-gray-300">{message}</p>
    </div>
  );
}
