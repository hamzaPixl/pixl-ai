import { useState, useMemo } from "react";
import { Badge } from "@/components/ui/badge";
import {
  CheckCircle2,
  XCircle,
  ChevronDown,
  ChevronRight,
  FileText,
} from "lucide-react";
import type { StageOutputPayload, NodeInstance } from "@/types/api";

export function hasNodeOutput(inst: NodeInstance): boolean {
  const o = (inst as any).output;
  return o && typeof o === "object" && Object.keys(o).length > 0;
}

export function InlineOutput({ output }: { output: Record<string, unknown> }) {
  const entries = Object.entries(output);
  if (entries.length === 0) return null;

  return (
    <div className="space-y-1.5">
      {entries.map(([key, value]) => (
        <div key={key}>
          <span className="font-medium text-muted-foreground">{key}: </span>
          <OutputValue value={value} />
        </div>
      ))}
    </div>
  );
}

export function OutputValue({ value }: { value: unknown }): React.ReactNode {
  if (value === null || value === undefined) {
    return <span className="text-muted-foreground italic">null</span>;
  }
  if (typeof value === "boolean") {
    return (
      <span className={value ? "text-green-600" : "text-red-600"}>
        {String(value)}
      </span>
    );
  }
  if (typeof value === "number") {
    return <span className="font-mono">{value}</span>;
  }
  if (typeof value === "string") {
    if (value.length > 200) {
      return (
        <code className="block bg-muted p-1.5 rounded text-xs overflow-x-auto mt-0.5">
          {value}
        </code>
      );
    }
    return <span className="font-mono">{value}</span>;
  }
  if (Array.isArray(value)) {
    return (
      <div className="pl-3 border-l border-muted-foreground/20 mt-0.5 space-y-0.5">
        {value.map((item, i) => (
          <div key={i}>
            <OutputValue value={item} />
          </div>
        ))}
      </div>
    );
  }
  if (typeof value === "object") {
    return (
      <div className="pl-3 border-l border-muted-foreground/20 mt-0.5 space-y-0.5">
        {Object.entries(value as Record<string, unknown>).map(([k, v]) => (
          <div key={k}>
            <span className="font-medium text-muted-foreground">{k}: </span>
            <OutputValue value={v} />
          </div>
        ))}
      </div>
    );
  }
  return <span>{String(value)}</span>;
}

export function PayloadField({
  name,
  value,
}: {
  name: string;
  value: unknown;
}) {
  const [expanded, setExpanded] = useState(false);

  if (value === null || value === undefined) {
    return (
      <div className="flex items-baseline gap-2">
        <span className="text-[10px] font-medium text-muted-foreground">
          {name}
        </span>
        <span className="text-[10px] italic text-muted-foreground/60">
          null
        </span>
      </div>
    );
  }

  if (typeof value === "boolean") {
    return (
      <div className="flex items-baseline gap-2">
        <span className="text-[10px] font-medium text-muted-foreground">
          {name}
        </span>
        <span
          className={`text-[10px] font-medium ${value ? "text-green-600" : "text-red-600"}`}
        >
          {String(value)}
        </span>
      </div>
    );
  }

  if (typeof value === "number") {
    return (
      <div className="flex items-baseline gap-2">
        <span className="text-[10px] font-medium text-muted-foreground">
          {name}
        </span>
        <span className="text-[10px] font-mono">{value}</span>
      </div>
    );
  }

  if (typeof value === "string") {
    if (value.length <= 120) {
      return (
        <div className="flex items-baseline gap-2">
          <span className="text-[10px] font-medium text-muted-foreground shrink-0">
            {name}
          </span>
          <span className="text-xs break-words">{value}</span>
        </div>
      );
    }
    return (
      <div>
        <button
          className="flex items-center gap-1 text-[10px] font-medium text-muted-foreground hover:text-foreground"
          onClick={() => setExpanded((v) => !v)}
        >
          {expanded ? (
            <ChevronDown className="h-3 w-3" />
          ) : (
            <ChevronRight className="h-3 w-3" />
          )}
          {name}
          <span className="text-muted-foreground/50 font-normal">
            ({value.length} chars)
          </span>
        </button>
        {expanded && (
          <div className="mt-1 ml-4 p-2 bg-muted rounded text-xs break-words max-h-48 overflow-y-auto">
            {value}
          </div>
        )}
      </div>
    );
  }

  if (Array.isArray(value)) {
    if (
      value.length <= 10 &&
      value.every((v) => typeof v === "string" && v.length < 200)
    ) {
      return (
        <div>
          <span className="text-[10px] font-medium text-muted-foreground">
            {name}
          </span>
          <ul className="ml-4 mt-0.5 space-y-0.5">
            {value.map((item, i) => (
              <li key={i} className="text-xs flex items-start gap-1">
                <span className="text-muted-foreground/50">-</span>
                <span>{String(item)}</span>
              </li>
            ))}
          </ul>
        </div>
      );
    }
    return (
      <div>
        <button
          className="flex items-center gap-1 text-[10px] font-medium text-muted-foreground hover:text-foreground"
          onClick={() => setExpanded((v) => !v)}
        >
          {expanded ? (
            <ChevronDown className="h-3 w-3" />
          ) : (
            <ChevronRight className="h-3 w-3" />
          )}
          {name}
          <span className="text-muted-foreground/50 font-normal">
            [{value.length} items]
          </span>
        </button>
        {expanded && (
          <div className="mt-1 ml-4 space-y-1">
            {value.map((item, i) => (
              <div key={i} className="p-1.5 bg-muted rounded text-[10px]">
                {typeof item === "object" && item !== null ? (
                  <div className="space-y-0.5">
                    {Object.entries(item as Record<string, unknown>).map(
                      ([k, v]) => (
                        <div key={k} className="flex items-baseline gap-1.5">
                          <span className="font-medium text-muted-foreground shrink-0">
                            {k}:
                          </span>
                          <span className="break-words">
                            {typeof v === "string" ? v : JSON.stringify(v)}
                          </span>
                        </div>
                      ),
                    )}
                  </div>
                ) : (
                  <span>{String(item)}</span>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }

  if (typeof value === "object") {
    const entries = Object.entries(value as Record<string, unknown>);
    return (
      <div>
        <button
          className="flex items-center gap-1 text-[10px] font-medium text-muted-foreground hover:text-foreground"
          onClick={() => setExpanded((v) => !v)}
        >
          {expanded ? (
            <ChevronDown className="h-3 w-3" />
          ) : (
            <ChevronRight className="h-3 w-3" />
          )}
          {name}
          <span className="text-muted-foreground/50 font-normal">{`{${entries.length} keys}`}</span>
        </button>
        {expanded && (
          <div className="mt-1 ml-4 space-y-1">
            {entries.map(([k, v]) => (
              <PayloadField key={k} name={k} value={v} />
            ))}
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="flex items-baseline gap-2">
      <span className="text-[10px] font-medium text-muted-foreground">
        {name}
      </span>
      <span className="text-xs">{String(value)}</span>
    </div>
  );
}

export function NodeStructuredOutput({
  output,
}: {
  output: StageOutputPayload;
}) {
  const [showRawPayload, setShowRawPayload] = useState(false);

  const displayPayload = useMemo(() => {
    const filtered: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(output.payload)) {
      if (k !== "baton_patch") filtered[k] = v;
    }
    return filtered;
  }, [output.payload]);

  const payloadKeys = Object.keys(displayPayload);

  return (
    <div className="rounded-md border bg-muted/20 p-3 text-xs space-y-3">
      {output.summary.length > 0 && (
        <div>
          <span className="text-[10px] font-medium text-muted-foreground uppercase block mb-1">
            Summary
          </span>
          <ul className="space-y-0.5">
            {output.summary.map((bullet, i) => (
              <li key={i} className="flex items-start gap-1.5">
                <CheckCircle2 className="h-3 w-3 mt-0.5 text-green-500 flex-shrink-0" />
                <span>{bullet}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {output.error && (
        <div className="p-2 rounded bg-red-500/10 border border-red-500/30">
          <div className="flex items-center gap-1.5 text-red-500">
            <XCircle className="h-3 w-3 flex-shrink-0" />
            <span className="font-medium">{output.error.code}</span>
            {output.error.recoverable && (
              <Badge
                variant="outline"
                className="text-[9px] px-1 h-3.5 border-red-500/50"
              >
                recoverable
              </Badge>
            )}
          </div>
          <p className="text-xs text-red-500/80 mt-1 pl-[18px]">
            {output.error.message}
          </p>
        </div>
      )}

      {output.artifacts_written.length > 0 && (
        <div>
          <span className="text-[10px] font-medium text-muted-foreground uppercase block mb-1">
            Artifacts Written
          </span>
          <div className="space-y-1">
            {output.artifacts_written.map((art, i) => (
              <div
                key={i}
                className="flex items-center gap-2 px-2 py-1 rounded bg-muted border"
              >
                <FileText className="h-3 w-3 text-muted-foreground flex-shrink-0" />
                <span className="font-mono text-[10px] truncate flex-1">
                  {art.path}
                </span>
                {art.purpose && (
                  <span className="text-[10px] text-muted-foreground truncate max-w-[200px]">
                    {art.purpose}
                  </span>
                )}
                {art.sha256 && (
                  <span className="text-[9px] font-mono text-muted-foreground/60">
                    {art.sha256.slice(0, 8)}
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {output.included_sources.length > 0 && (
        <div>
          <span className="text-[10px] font-medium text-muted-foreground uppercase block mb-1">
            Sources Used
          </span>
          <div className="flex flex-wrap gap-1.5">
            {output.included_sources.map((s, i) => (
              <span
                key={i}
                className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-muted border text-[10px]"
              >
                <span className="font-mono">{s.artifact_id}</span>
                {s.reason && (
                  <span className="text-muted-foreground/70">({s.reason})</span>
                )}
              </span>
            ))}
          </div>
        </div>
      )}

      {output.next && (
        <div className="flex items-center gap-2 px-2 py-1.5 rounded bg-blue-500/10 border border-blue-500/20">
          <ChevronRight className="h-3 w-3 text-blue-500 flex-shrink-0" />
          <span className="text-[10px] text-muted-foreground">Next:</span>
          <span className="font-medium text-foreground text-xs">
            {output.next.recommended_stage}
          </span>
          {output.next.inputs_needed.length > 0 && (
            <span className="text-[10px] text-muted-foreground">
              (needs: {output.next.inputs_needed.join(", ")})
            </span>
          )}
        </div>
      )}

      {payloadKeys.length > 0 && (
        <div className="border-t pt-2">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[10px] font-medium text-muted-foreground uppercase">
              Payload ({payloadKeys.length} keys)
            </span>
            <button
              className="text-[10px] text-muted-foreground hover:text-foreground px-1.5 py-0.5 rounded hover:bg-muted"
              onClick={() => setShowRawPayload((v) => !v)}
            >
              {showRawPayload ? "Structured" : "Raw"}
            </button>
          </div>
          {showRawPayload ? (
            <pre className="p-2 bg-muted rounded text-[10px] font-mono overflow-x-auto max-h-64 overflow-y-auto">
              {JSON.stringify(displayPayload, null, 2)}
            </pre>
          ) : (
            <div className="space-y-1.5">
              {payloadKeys.map((key) => (
                <PayloadField
                  key={key}
                  name={key}
                  value={displayPayload[key]}
                />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
