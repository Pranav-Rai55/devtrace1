import React from "react";
import computer from "../assets/computer.jpg";

export default function Heroimage() {
  return (
    <div className="relative w-full flex justify-center px-4 bg-transparent">
      {/* margin-top applied here instead */}
      
      <div className="relative w-full max-w-5xl rounded-2xl overflow-hidden shadow-2xl">

        {/* Glow Layer */}
        <div className="pointer-events-none absolute inset-0 bg-gradient-to-tr from-indigo-500/20 via-blue-500/10 to-purple-500/20 item-center justify-center" />

        {/* Image */}
        <img
          src={computer}
          alt="DevTrace Code Analysis Preview"
          className="w-full h-auto block object-cover animate-floatSlow transition-all duration-500 hover:scale-105 hover:shadow-blue-500/40 border border-blue-500/40 shadow-[0_0_40px_rgba(59,130,246,0.4)]"
          loading="lazy"
        />
      </div>
    </div>
  );
}