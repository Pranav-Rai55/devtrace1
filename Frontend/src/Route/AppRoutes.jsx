import { Routes, Route, Navigate } from "react-router-dom";
import React, { Suspense, lazy } from "react";
import Landing from "../Pages/Landing";

const Login = lazy(() => import("../Pages/Login"));
const Signup = lazy(() => import("../Pages/Signup"));
const AuthCallback = lazy(() => import("../Pages/AuthCallback"));
const Dashboard = lazy(() => import("../Pages/Dashboard"));
const Loading = lazy(() => import("../Pages/Loading"));

function AppRoutes() {
  return (
    <Suspense fallback={<Loading />}>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/login" element={<Login />} />
        <Route path="/signup" element={<Signup />} />
        <Route path="/auth/callback" element={<AuthCallback />} />
        {/* Loading/processing screen shown while ML analysis runs */}
        <Route path="/loading" element={<Loading />} />
        <Route path="/dashboard" element={<Dashboard />} />
        {/* Catch-all redirect */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  );
}

export default AppRoutes;
