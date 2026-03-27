import { StructuredOutputViewer } from '@/components/StructuredOutputViewer';

interface StructuredOutputsTabProps {
  structuredOutputs: Record<string, any> | undefined;
}

export function StructuredOutputsTab({ structuredOutputs }: StructuredOutputsTabProps) {
  if (!structuredOutputs || Object.keys(structuredOutputs).length === 0) {
    return <p className="text-sm text-muted-foreground py-2">No structured outputs</p>;
  }

  return (
    <div className="space-y-2 py-2">
      {Object.entries(structuredOutputs).map(([nodeId, output]) => (
        <StructuredOutputViewer key={nodeId} nodeId={nodeId} output={output} />
      ))}
    </div>
  );
}
