import { motion, AnimatePresence } from "framer-motion";
import { Loader2 } from "lucide-react";

const STATUS_MESSAGES = [
  "Analyzing prompt...",
  "Detecting intent and scope...",
  "Matching workflow patterns...",
];

export { STATUS_MESSAGES };

export interface ClassifyingProgressProps {
  statusIndex: number;
}

export function ClassifyingProgress({ statusIndex }: ClassifyingProgressProps) {
  return (
    <motion.div
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: "auto" }}
      exit={{ opacity: 0, height: 0 }}
      className="overflow-hidden"
    >
      <div className="px-5 pb-4 space-y-3">
        <div className="h-1 rounded-full bg-muted overflow-hidden">
          <motion.div
            className="h-full bg-primary rounded-full"
            initial={{ width: "0%" }}
            animate={{ width: "90%" }}
            transition={{ duration: 3, ease: "easeOut" }}
          />
        </div>
        <AnimatePresence mode="wait">
          <motion.p
            key={statusIndex}
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            className="text-xs text-muted-foreground flex items-center gap-2"
          >
            <Loader2 className="h-3 w-3 animate-spin" />
            {STATUS_MESSAGES[statusIndex]}
          </motion.p>
        </AnimatePresence>
      </div>
    </motion.div>
  );
}
