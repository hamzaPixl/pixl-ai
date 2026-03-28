import { BatonAuditPanel } from '@/components/BatonAuditPanel';

interface BatonAuditTabProps {
  baton: any;
  batonHistory: any[];
  contextAudit: any[];
}

export function BatonAuditTab({ baton, batonHistory, contextAudit }: BatonAuditTabProps) {
  if (!baton) {
    return <p className="text-sm text-muted-foreground py-2">Not in baton mode</p>;
  }

  return (
    <BatonAuditPanel
      baton={baton}
      batonHistory={batonHistory}
      contextAudit={contextAudit}
    />
  );
}
