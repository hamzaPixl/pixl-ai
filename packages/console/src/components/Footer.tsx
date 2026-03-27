/**
 * Footer component with version information.
 */

import { useVersion } from "@/hooks/use-version";

export function Footer() {
  const { data: version } = useVersion();

  if (!version) {
    return null;
  }

  return (
    <footer className="shrink-0 border-t bg-muted/30 px-4 py-1">
      <div className="flex items-center justify-between text-[10px] text-muted-foreground/60">
        <div className="flex items-center gap-2">
          <span>Pixl v{version.version}</span>
          <span title={`Build: ${version.build_hash}`}>({version.build_hash.slice(0, 8)})</span>
          {version.api_version && <span>API {version.api_version}</span>}
        </div>
        <div className="flex items-center gap-2">
          <span>Python {version.python_version}</span>
          {version.build_date && (
            <span title="Build date">{new Date(version.build_date).toLocaleDateString()}</span>
          )}
        </div>
      </div>
    </footer>
  );
}