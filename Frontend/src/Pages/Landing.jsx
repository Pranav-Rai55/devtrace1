import Navbar from "../Components/Navbar";
import Hero from "../Components/Hero";
import Features from "../Components/Feature";
import Pricing from "../Components/Pricing";
import React from "react";

function Landing() {
  return (
    <div className="flex min-h-screen flex-col">
      <Navbar />
      <Hero />
      <Features />
      <Pricing />
    </div>
  );
}

export default Landing