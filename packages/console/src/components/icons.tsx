/**
 * Icon components using lucide-react.
 */

import type { SVGAttributes } from "react";

// Re-export all icons from lucide-react directly
export * from "lucide-react";

// CheckSquare alias
import { Square } from "lucide-react";
export const CheckSquare = Square;

// LayoutDashboard - create a custom icon that looks like a dashboard
export function LayoutDashboard({ className, ...props }: SVGAttributes<SVGSVGElement>) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      {...props}
    >
      <rect x="3" y="3" width="7" height="7" />
      <rect x="14" y="3" width="7" height="7" />
      <rect x="14" y="14" width="7" height="7" />
      <rect x="3" y="14" width="7" height="7" />
    </svg>
  );
}

// FolderKanban - create a custom icon
export function FolderKanban({ className, ...props }: SVGAttributes<SVGSVGElement>) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      {...props}
    >
      <path d="M6 20h12a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-2.93a2 2 0 0 1-1.664-.89l-.812-1.22A2 2 0 0 0 8.93 2H6a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2Z" />
      <path d="M10 12v4" />
      <path d="M14 12v4" />
    </svg>
  );
}

// Workflow alias for Layers
import { Layers } from "lucide-react";
export const Workflow = Layers;

// Coins - create a custom icon
export function Coins({ className, ...props }: SVGAttributes<SVGSVGElement>) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      {...props}
    >
      <circle cx="8" cy="8" r="6" />
      <path d="M18.09 10.37A6 6 0 1 1 10.34 18" />
      <path d="M7 6h1v4" />
      <path d="M16.5 13.5l2.5 2.5" />
    </svg>
  );
}

// Calendar - create a custom icon
export function Calendar({ className, ...props }: SVGAttributes<SVGSVGElement>) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      {...props}
    >
      <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
      <line x1="16" x2="16" y1="2" y2="6" />
      <line x1="8" x2="8" y1="2" y2="6" />
      <line x1="3" x2="21" y1="10" y2="10" />
    </svg>
  );
}

// Flag - create a custom icon
export function Flag({ className, ...props }: SVGAttributes<SVGSVGElement>) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      {...props}
    >
      <path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z" />
      <line x1="4" x2="4" y1="22" y2="15" />
    </svg>
  );
}

// FolderOpen - create a custom icon
export function FolderOpen({ className, ...props }: SVGAttributes<SVGSVGElement>) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      {...props}
    >
      <path d="m6 14 1.45-2.9A2 2 0 0 1 9.24 10H20a2 2 0 0 1 1.94 2.5l-1.55 6a2 2 0 0 1-1.94 1.5H4a2 2 0 0 1-2-2V5c0-1.1.9-2 2-2h3.93a2 2 0 0 1 1.66.9l.82 1.2a2 2 0 0 0 1.66.9H18a2 2 0 0 1 2 2v2" />
    </svg>
  );
}

// CheckCircle alias
import { CheckCircle2 } from "lucide-react";
export const CheckCircle = CheckCircle2;

// Custom app logo icon
export function PixlAppLogo({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      <rect x="2" y="2" width="9" height="9" rx="1" className="fill-current" />
      <rect x="13" y="2" width="9" height="9" rx="1" className="fill-current" opacity="0.6" />
      <rect x="2" y="13" width="9" height="9" rx="1" className="fill-current" opacity="0.8" />
      <rect x="13" y="13" width="9" height="9" rx="1" className="fill-current" opacity="0.4" />
    </svg>
  );
}
