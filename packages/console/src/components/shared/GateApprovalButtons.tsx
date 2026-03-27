import { Button } from "@/components/ui/button";
import { Check, X } from "@/components/icons";

export interface GateApprovalButtonsProps {
  onApprove: () => void;
  onReject: () => void;
  size?: "sm" | "default";
}

export function GateApprovalButtons({
  onApprove,
  onReject,
  size = "sm",
}: GateApprovalButtonsProps) {
  return (
    <div className="flex items-center gap-2 shrink-0 ml-4">
      <Button
        size={size}
        variant="outline"
        className="text-destructive hover:bg-destructive hover:text-destructive-foreground"
        onClick={onReject}
      >
        <X className="h-4 w-4 mr-1" />
        Reject
      </Button>
      <Button
        size={size}
        className="bg-green-600 hover:bg-green-700 dark:bg-green-600 dark:hover:bg-green-700"
        onClick={onApprove}
      >
        <Check className="h-4 w-4 mr-1" />
        Approve
      </Button>
    </div>
  );
}
