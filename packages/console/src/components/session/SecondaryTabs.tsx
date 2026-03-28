import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { ArtifactsTab } from './ArtifactsTab';
import { StructuredOutputsTab } from './StructuredOutputsTab';
import { BatonAuditTab } from './BatonAuditTab';
import type { ArtifactMetadata } from '@/types/api';

interface SecondaryTabsProps {
  artifacts: ArtifactMetadata[] | undefined;
  frozenArtifacts: Record<string, string> | undefined;
  structuredOutputs: Record<string, any> | undefined;
  baton: any;
  batonHistory: any[];
  contextAudit: any[];
  onArtifactClick: (artifact: ArtifactMetadata) => void;
}

export function SecondaryTabs({
  artifacts,
  frozenArtifacts,
  structuredOutputs,
  baton,
  batonHistory,
  contextAudit,
  onArtifactClick,
}: SecondaryTabsProps) {
  const hasStructuredOutputs = structuredOutputs && Object.keys(structuredOutputs).length > 0;
  const hasBaton = !!baton;

  return (
    <div className="border-t pt-3 mt-3 flex-shrink-0">
      <Tabs defaultValue="artifacts">
        <TabsList>
          <TabsTrigger value="artifacts" className="gap-1.5">
            Artifacts
            {artifacts && artifacts.length > 0 && (
              <Badge variant="secondary" className="text-[10px] px-1 h-4 min-w-[1rem]">
                {artifacts.length}
              </Badge>
            )}
          </TabsTrigger>
          {hasStructuredOutputs && (
            <TabsTrigger value="outputs" className="gap-1.5">
              Outputs
              <Badge variant="secondary" className="text-[10px] px-1 h-4 min-w-[1rem]">
                {Object.keys(structuredOutputs!).length}
              </Badge>
            </TabsTrigger>
          )}
          {hasBaton && (
            <TabsTrigger value="baton" className="gap-1.5">
              Baton Audit
            </TabsTrigger>
          )}
        </TabsList>

        <TabsContent value="artifacts">
          <ArtifactsTab
            artifacts={artifacts}
            frozenArtifacts={frozenArtifacts}
            onArtifactClick={onArtifactClick}
          />
        </TabsContent>

        {hasStructuredOutputs && (
          <TabsContent value="outputs">
            <StructuredOutputsTab structuredOutputs={structuredOutputs} />
          </TabsContent>
        )}

        {hasBaton && (
          <TabsContent value="baton">
            <BatonAuditTab
              baton={baton}
              batonHistory={batonHistory}
              contextAudit={contextAudit}
            />
          </TabsContent>
        )}
      </Tabs>
    </div>
  );
}
