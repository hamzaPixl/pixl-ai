import { type ReactNode, useEffect, useRef } from "react";

function resolveColor(cssVar: string, fallback: string): string {
  if (typeof document === "undefined") return fallback;
  const raw = getComputedStyle(document.documentElement)
    .getPropertyValue(cssVar)
    .trim();
  if (!raw) return fallback;
  return `hsl(${raw})`;
}

interface InteractiveGridProps {
  gridGap?: number;
  dotSize?: number;
  radius?: number;
  children?: ReactNode;
}

function InteractiveGrid({
  gridGap = 40,
  dotSize = 1.5,
  radius = 300,
  children,
}: InteractiveGridProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const mouseRef = useRef({ x: -1000, y: -1000 });
  const requestRef = useRef<number | undefined>(undefined);

  useEffect(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const prefersReduced = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;

    const onMouseMove = (e: MouseEvent) => {
      if (prefersReduced) return;
      const rect = container.getBoundingClientRect();
      mouseRef.current = {
        x: e.clientX - rect.left,
        y: e.clientY - rect.top,
      };
    };

    const onMouseLeave = () => {
      mouseRef.current = { x: -1000, y: -1000 };
    };

    container.addEventListener("mousemove", onMouseMove);
    container.addEventListener("mouseleave", onMouseLeave);

    const resize = () => {
      canvas.width = container.clientWidth;
      canvas.height = container.clientHeight;
    };
    resize();
    window.addEventListener("resize", resize);

    const animate = () => {
      if (!ctx || !canvas) return;
      const width = canvas.width;
      const height = canvas.height;

      const color = resolveColor("--muted-foreground", "#737373");
      const highlightColor = resolveColor("--highlight", "#ef233c");

      ctx.clearRect(0, 0, width, height);

      for (let x = 0; x < width; x += gridGap) {
        for (let y = 0; y < height; y += gridGap) {
          const dx = x - mouseRef.current.x;
          const dy = y - mouseRef.current.y;
          const dist = Math.sqrt(dx * dx + dy * dy);

          let currentSize = dotSize;
          let currentAlpha = 0.3;
          let currentColor = color;

          if (dist < radius) {
            const ratio = 1 - dist / radius;
            currentSize = dotSize + ratio * 2.5;
            currentAlpha = 0.3 + ratio * 0.7;

            if (ratio > 0.4) {
              currentColor = highlightColor;
            }
          }

          ctx.beginPath();
          ctx.arc(x, y, currentSize, 0, Math.PI * 2);
          ctx.fillStyle = currentColor;
          ctx.globalAlpha = currentAlpha;
          ctx.fill();
          ctx.globalAlpha = 1.0;
        }
      }

      requestRef.current = requestAnimationFrame(animate);
    };

    animate();

    return () => {
      window.removeEventListener("resize", resize);
      container.removeEventListener("mousemove", onMouseMove);
      container.removeEventListener("mouseleave", onMouseLeave);
      if (requestRef.current) cancelAnimationFrame(requestRef.current);
    };
  }, [gridGap, dotSize, radius]);

  return (
    <div ref={containerRef} className="absolute inset-0">
      <canvas ref={canvasRef} className="absolute inset-0" />
      {children}
    </div>
  );
}

export function AuthBackground() {
  return (
    <div className="absolute inset-0 bg-background">
      <InteractiveGrid>
        {/* Radial glow */}
        <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 h-[250px] w-[250px] sm:h-[400px] sm:w-[400px] rounded-full bg-highlight/5 blur-[100px] pointer-events-none" />

        {/* Branding overlay — pointer-events-none so mouse reaches canvas */}
        <div className="absolute inset-0 z-10 flex flex-col items-center justify-center gap-4 pointer-events-none px-8">
          <img
            src="/logo.svg"
            alt="Pixl"
            className="h-12 w-12 drop-shadow-md"
          />
          <h2 className="text-3xl font-bold tracking-tight text-foreground">
            Pixl
          </h2>
          <p className="max-w-xs text-center text-muted-foreground text-sm leading-relaxed">
            AI-powered orchestration engine for software teams. Plan, build, and
            ship — autonomously.
          </p>
        </div>
      </InteractiveGrid>
    </div>
  );
}
