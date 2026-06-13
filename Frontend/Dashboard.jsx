// Backend API (Authentication, User data)
export const BACKEND_API = import.meta.env.VITE_BACKEND_URL || "http://localhost:5000";

// ML API (Analysis, insights)
export const ML_API = import.meta.env.VITE_ML_API_URL || "http://localhost:8000";

// Legacy support
export const API_BASE = BACKEND_API;
