import { Suspense, useRef } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { Float, Sparkles, Stars } from "@react-three/drei";
import { useLocation } from "react-router-dom";

function SceneContent({ boost }) {
  const groupRef = useRef(null);

  useFrame((_, delta) => {
    if (groupRef.current) {
      groupRef.current.rotation.y += delta * 0.055;
      groupRef.current.rotation.x += delta * 0.018;
    }
  });

  return (
    <>
      <color attach="background" args={["#020204"]} />
      <fog attach="fog" args={["#020204", boost ? 9 : 7, boost ? 32 : 26]} />

      <ambientLight intensity={boost ? 0.5 : 0.32} />
      <pointLight position={[8, 6, 10]} intensity={boost ? 1.75 : 1.15} color="#818cf8" />
      <pointLight position={[-8, -4, -6]} intensity={boost ? 1.05 : 0.65} color="#c4b5fd" />
      <directionalLight position={[0, 10, 5]} intensity={boost ? 0.4 : 0.22} color="#f5f3ff" />

      <Stars
        radius={90}
        depth={45}
        count={3200}
        factor={3.2}
        saturation={boost ? 0.35 : 0.15}
        fade
        speed={0.45}
      />

      <Sparkles
        count={boost ? 140 : 100}
        scale={[24, 14, 10]}
        size={boost ? 3.4 : 2.8}
        speed={0.32}
        opacity={boost ? 0.88 : 0.6}
        color="#c7d2fe"
      />

      <group ref={groupRef}>
        <Float speed={1.75} rotationIntensity={0.42} floatIntensity={0.55}>
          <mesh>
            <icosahedronGeometry args={[2.35, 1]} />
            <meshStandardMaterial
              color="#120a22"
              wireframe
              emissive="#6366f1"
              emissiveIntensity={0.48 * (boost ? 1.7 : 1)}
              metalness={0.85}
              roughness={0.25}
            />
          </mesh>
        </Float>

        <Float speed={2.1} rotationIntensity={0.48} floatIntensity={0.38}>
          <mesh position={[4.1, -1.9, -3.2]} rotation={[0.85, 0.35, 0.15]}>
            <torusKnotGeometry args={[0.92, 0.26, 120, 16]} />
            <meshStandardMaterial
              color="#140818"
              wireframe
              emissive="#a78bfa"
              emissiveIntensity={0.38 * (boost ? 1.65 : 1)}
            />
          </mesh>
        </Float>

        <Float speed={1.35} rotationIntensity={0.28} floatIntensity={0.52}>
          <mesh position={[-4.2, 1.25, -2.4]} rotation={[-0.45, 1.15, 0.1]}>
            <octahedronGeometry args={[1.1, 0]} />
            <meshStandardMaterial
              color="#0a1520"
              wireframe
              emissive="#67e8f9"
              emissiveIntensity={0.28 * (boost ? 1.75 : 1)}
            />
          </mesh>
        </Float>
      </group>
    </>
  );
}

export default function AnimatedBackground3D() {
  const { pathname } = useLocation();
  const boost = pathname === "/login" || pathname === "/signup";

  return (
    <div
      className="pointer-events-none fixed inset-0 z-0 min-h-[100dvh] w-full"
      aria-hidden="true"
    >
      <Canvas
        className="!h-[100dvh] !w-full"
        style={{ width: "100%", height: "100%" }}
        camera={{ position: [0, 0, 11], fov: 40 }}
        gl={{
          alpha: false,
          antialias: true,
          powerPreference: "high-performance",
        }}
        dpr={[1, 2]}
      >
        <Suspense fallback={null}>
          <SceneContent boost={boost} />
        </Suspense>
      </Canvas>
      <div
        className={
          boost
            ? "pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_100%_90%_at_50%_45%,transparent_0%,rgba(0,0,0,0.15)_50%,rgba(0,0,0,0.28)_100%)]"
            : "pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_120%_100%_at_50%_0%,transparent_0%,rgba(0,0,0,0.35)_55%,rgba(0,0,0,0.55)_100%)]"
        }
        aria-hidden="true"
      />
    </div>
  );
}
