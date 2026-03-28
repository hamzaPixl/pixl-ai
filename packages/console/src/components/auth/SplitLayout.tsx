import type { ReactNode } from "react";

interface SplitLayoutProps {
  left: ReactNode;
  right: ReactNode;
}

export function SplitLayout({ left, right }: SplitLayoutProps) {
  return (
    <div className="grid min-h-svh grid-cols-1 lg:grid-cols-2">
      <div className="flex items-center justify-center overflow-y-auto px-6 py-12 md:px-10">
        <div className="w-full max-w-md">{left}</div>
      </div>
      <div className="hidden lg:block relative overflow-hidden">{right}</div>
    </div>
  );
}
