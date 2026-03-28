import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Loader2, RotateCcw } from "lucide-react";

export interface ModelRowInfo {
  effective_model?: string;
  has_override?: boolean;
}

interface GlobalModelRowProps {
  label: string;
  description?: string;
  modelInfo: ModelRowInfo | undefined;
  allowedModels: string[];
  disabled: boolean;
  isPending: boolean;
  onModelChange: (model: string) => void;
  onReset: () => void;
}

function GlobalModelRow({
  label,
  description,
  modelInfo,
  allowedModels,
  disabled,
  isPending,
  onModelChange,
  onReset,
}: GlobalModelRowProps) {
  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <span className="text-xs font-medium">{label}</span>
        {modelInfo?.has_override && (
          <Badge variant="default" className="text-[10px] px-1.5 py-0 h-4">
            override
          </Badge>
        )}
      </div>
      {description && (
        <p className="text-[11px] text-muted-foreground leading-relaxed">
          {description}
        </p>
      )}
      <div className="flex items-center gap-2">
        <Select
          value={modelInfo?.effective_model}
          onValueChange={onModelChange}
          disabled={disabled || allowedModels.length === 0}
        >
          <SelectTrigger className="flex-1 h-8 text-xs">
            <SelectValue placeholder="Select model" />
          </SelectTrigger>
          <SelectContent>
            {allowedModels.map((m) => (
              <SelectItem key={m} value={m}>
                {m}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        {isPending && (
          <Loader2 className="h-3.5 w-3.5 animate-spin text-muted-foreground shrink-0" />
        )}
        {modelInfo?.has_override && (
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8 shrink-0"
                onClick={onReset}
                disabled={disabled}
              >
                <RotateCcw className="h-3.5 w-3.5" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>Reset to default</TooltipContent>
          </Tooltip>
        )}
      </div>
    </div>
  );
}

// Re-export with the same prop shapes for backwards compat
export interface ClassifierModelRowProps {
  modelInfo: ModelRowInfo | undefined;
  allowedModels: string[];
  disabled: boolean;
  isPending: boolean;
  onModelChange: (model: string) => void;
  onReset: () => void;
}

export function ClassifierModelRow(props: ClassifierModelRowProps) {
  return <GlobalModelRow label="Classifier Model" {...props} />;
}

export interface SessionReportModelRowProps {
  modelInfo: ModelRowInfo | undefined;
  allowedModels: string[];
  disabled: boolean;
  isPending: boolean;
  onModelChange: (model: string) => void;
  onReset: () => void;
}

export function SessionReportModelRow(props: SessionReportModelRowProps) {
  return (
    <GlobalModelRow
      label="Session Report Model"
      description="Applies to manual Draft Report and daemon-generated terminal session reports."
      {...props}
    />
  );
}
