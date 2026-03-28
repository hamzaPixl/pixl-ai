/**
 * Linear-style graduated status indicator for workflow pipeline nodes.
 *
 * Maps execution states to lucide-react icons with state-driven coloring
 * and subtle animations (spin for running, pulse for waiting).
 */

import {
  Circle,
  Loader2,
  ShieldQuestion,
  CheckCircle2,
  XCircle,
  MinusCircle,
} from 'lucide-react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';

export type ExecutionState = 'pending' | 'running' | 'completed' | 'failed' | 'waiting' | 'skipped';

export interface NodeExecutionState {
  state: ExecutionState;
  attempt?: number;
  progress?: number;
}

interface WorkflowStatusIconProps {
  state: ExecutionState;
  size?: 'sm' | 'md';
  className?: string;
}

const SIZE_MAP = { sm: 'h-3.5 w-3.5', md: 'h-4.5 w-4.5' } as const;

export function WorkflowStatusIcon({ state, size = 'sm', className }: WorkflowStatusIconProps) {
  const s = SIZE_MAP[size];

  switch (state) {
    case 'pending':
      return <Circle className={cn(s, 'text-muted-foreground opacity-40', className)} strokeDasharray="3 2" />;
    case 'running':
      return <Loader2 className={cn(s, 'text-blue-500 animate-spin', className)} />;
    case 'waiting':
      return (
        <motion.div
          animate={{ opacity: [0.5, 1, 0.5] }}
          transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
          className="inline-flex"
        >
          <ShieldQuestion className={cn(s, 'text-amber-500', className)} />
        </motion.div>
      );
    case 'completed':
      return <CheckCircle2 className={cn(s, 'text-green-500', className)} />;
    case 'failed':
      return <XCircle className={cn(s, 'text-red-500', className)} />;
    case 'skipped':
      return <MinusCircle className={cn(s, 'text-muted-foreground opacity-40', className)} />;
  }
}
