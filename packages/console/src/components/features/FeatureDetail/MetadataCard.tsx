import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { DollarSign, Clock, GitBranch, ExternalLink } from "lucide-react";

export interface FeatureData {
  description?: string;
  success_criteria: string[];
  assumptions: string[];
  total_cost_usd: number;
  total_tokens: number;
  estimated_hours?: number | null;
  actual_hours?: number | null;
  branch_name?: string | null;
  pr_url?: string | null;
  depends_on: string[];
  blocked_by?: string | null;
  blocked_reason?: string | null;
}

export interface MetadataCardProps {
  feature: FeatureData;
}

export function MetadataCard({ feature }: MetadataCardProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Details</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 text-sm">
          {feature.description && (
            <div className="col-span-full">
              <span className="text-muted-foreground font-medium">
                Description
              </span>
              <p className="mt-1">{feature.description}</p>
            </div>
          )}
          {feature.success_criteria.length > 0 && (
            <div className="col-span-full">
              <span className="text-muted-foreground font-medium">
                Success Criteria
              </span>
              <ul className="mt-1 list-disc list-inside">
                {feature.success_criteria.map((c, i) => (
                  <li key={i}>{c}</li>
                ))}
              </ul>
            </div>
          )}
          {feature.assumptions.length > 0 && (
            <div>
              <span className="text-muted-foreground font-medium">
                Assumptions
              </span>
              <ul className="mt-1 list-disc list-inside">
                {feature.assumptions.map((a, i) => (
                  <li key={i}>{a}</li>
                ))}
              </ul>
            </div>
          )}
          <div className="flex items-center gap-2">
            <DollarSign className="h-4 w-4 text-muted-foreground" />
            <span className="text-muted-foreground">Cost:</span>
            <span>${feature.total_cost_usd.toFixed(4)}</span>
            <span className="text-muted-foreground text-xs">
              ({feature.total_tokens.toLocaleString()} tokens)
            </span>
          </div>
          <div className="flex items-center gap-2">
            <Clock className="h-4 w-4 text-muted-foreground" />
            <span className="text-muted-foreground">Estimated:</span>
            <span>{feature.estimated_hours ?? "\u2014"}h</span>
            <span className="text-muted-foreground">/ Actual:</span>
            <span>{feature.actual_hours ?? "\u2014"}h</span>
          </div>
          {feature.branch_name && (
            <div className="flex items-center gap-2">
              <GitBranch className="h-4 w-4 text-muted-foreground" />
              <span className="font-mono text-xs">{feature.branch_name}</span>
            </div>
          )}
          {feature.pr_url && (
            <div className="flex items-center gap-2">
              <ExternalLink className="h-4 w-4 text-muted-foreground" />
              <a
                href={feature.pr_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary underline text-xs"
              >
                Pull Request
              </a>
            </div>
          )}
          {feature.depends_on.length > 0 && (
            <div>
              <span className="text-muted-foreground font-medium">
                Depends On
              </span>
              <div className="flex gap-1 mt-1 flex-wrap">
                {feature.depends_on.map((dep) => (
                  <Badge key={dep} variant="outline" className="text-xs">
                    {dep}
                  </Badge>
                ))}
              </div>
            </div>
          )}
          {feature.blocked_by && (
            <div>
              <span className="text-muted-foreground font-medium">
                Blocked By
              </span>
              <Badge variant="destructive" className="ml-2 text-xs">
                {feature.blocked_by}
              </Badge>
              {feature.blocked_reason && (
                <p className="text-xs text-muted-foreground mt-1">
                  {feature.blocked_reason}
                </p>
              )}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
