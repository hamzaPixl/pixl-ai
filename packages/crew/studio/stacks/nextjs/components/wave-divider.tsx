interface WaveDividerProps {
  variant?: "cream-to-teal" | "teal-to-cream";
  className?: string;
}

export function WaveDivider({
  variant = "cream-to-teal",
  className = "",
}: WaveDividerProps) {
  const fills: Record<string, { bg: string; wave: string }> = {
    "cream-to-teal": {
      bg: "bg-accent/40",
      wave: "text-primary",
    },
    "teal-to-cream": {
      bg: "bg-primary",
      wave: "text-background",
    },
  };

  const { bg, wave } = fills[variant];

  return (
    <div className={`relative w-full overflow-hidden leading-[0] ${bg} ${className}`} aria-hidden="true">
      <svg
        className={`relative block w-full h-[60px] sm:h-[80px] lg:h-[100px] ${wave}`}
        viewBox="0 0 1440 100"
        preserveAspectRatio="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <path
          d="M0,40 C360,100 1080,0 1440,60 L1440,100 L0,100 Z"
          fill="currentColor"
        />
      </svg>
    </div>
  );
}
