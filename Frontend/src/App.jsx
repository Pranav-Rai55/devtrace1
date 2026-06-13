import "./App.css";
import AppRoutes from "./Route/AppRoutes";
import React, { Suspense, lazy } from "react";

const AnimatedBackground3D = lazy(() => import("./Components/AnimatedBackground3D"));

function App() {
  return (
    <>
      <Suspense fallback={<div></div>}>
        <AnimatedBackground3D />
      </Suspense>
      <div className="relative z-10 min-h-[100dvh] w-full">
        <AppRoutes />
      </div>
    </>
  );
}
export default App;
