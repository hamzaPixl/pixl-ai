/**
 * Usage & Cost Analytics page.
 *
 * Shows project-wide cost and token usage with breakdowns by model, agent,
 * and feature.
 */

import { createFileRoute, Link } from '@tanstack/react-router';
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { usage } from '@/lib/api';
import { queryKeys } from '@/lib/query-keys';
import { useBudget, useCosts, useUpdateBudget, useUnpauseBudget } from '@/hooks/queries';
import { BudgetBar } from '@/components/budget/BudgetBar';
import { CostBreakdownTable } from '@/components/budget/CostBreakdownTable';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
import { PageHeader } from '@/components/page-header';
import { EmptyState } from '@/components/empty-state';
import { DollarSign, Coins, ArrowUpDown, Play } from 'lucide-react';
import type {
  UsageByModel,
  UsageByAgent,
  UsageByFeature,
} from '@/types/api';

export const Route = createFileRoute('/project/$projectId/usage')({
  component: UsagePage,
});

function UsagePage() {
  const { projectId } = Route.useParams();
  const [editingBudget, setEditingBudget] = useState(false);
  const [budgetInput, setBudgetInput] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.usage.summary(projectId),
    queryFn: () => usage.summary(),
    enabled: !!projectId,
  });

  const { data: budgetData } = useBudget(projectId);
  const { data: costsData } = useCosts(projectId);
  const updateBudget = useUpdateBudget(projectId);
  const unpauseBudget = useUnpauseBudget(projectId);

  const handleBudgetSave = () => {
    const val = parseFloat(budgetInput);
    if (!isNaN(val) && val > 0) {
      updateBudget.mutate(val);
      setEditingBudget(false);
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-48" />
        <div className="grid grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-24" />
          ))}
        </div>
        <Skeleton className="h-64" />
      </div>
    );
  }

  const totals = data?.totals;

  return (
    <div className="space-y-6">
      <PageHeader title="Usage & Costs" description="Budget management, token usage, and cost breakdowns" />

      {/* Budget section */}
      {budgetData && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-lg">Monthly Budget</CardTitle>
              <div className="flex items-center gap-2">
                {budgetData.is_exceeded && (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => unpauseBudget.mutate()}
                    disabled={unpauseBudget.isPending}
                    className="gap-1.5"
                  >
                    <Play className="h-3 w-3" />
                    Unpause Sessions
                  </Button>
                )}
                {editingBudget ? (
                  <div className="flex items-center gap-1.5">
                    <Input
                      type="number"
                      step="0.01"
                      value={budgetInput}
                      onChange={(e) => setBudgetInput(e.target.value)}
                      className="h-7 w-24 text-xs"
                      placeholder="USD"
                    />
                    <Button size="sm" className="h-7 text-xs" onClick={handleBudgetSave}>Save</Button>
                    <Button size="sm" variant="ghost" className="h-7 text-xs" onClick={() => setEditingBudget(false)}>Cancel</Button>
                  </div>
                ) : (
                  <Button
                    size="sm"
                    variant="outline"
                    className="h-7 text-xs"
                    onClick={() => {
                      setBudgetInput(String(budgetData.monthly_usd));
                      setEditingBudget(true);
                    }}
                  >
                    Edit Limit
                  </Button>
                )}
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <BudgetBar spent={budgetData.spent_monthly_usd} limit={budgetData.monthly_usd} />
          </CardContent>
        </Card>
      )}

      {/* Cost breakdown by adapter */}
      {costsData?.breakdown && costsData.breakdown.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Cost Breakdown by Adapter</CardTitle>
          </CardHeader>
          <CardContent>
            <CostBreakdownTable breakdown={costsData.breakdown} />
          </CardContent>
        </Card>
      )}

      {/* KPI strip */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KpiCard
          label="Total Cost"
          value={totals ? `$${totals.cost_usd.toFixed(4)}` : '—'}
          icon={<DollarSign className="h-4 w-4" />}
        />
        <KpiCard
          label="Total Tokens"
          value={totals ? totals.total_tokens.toLocaleString() : '—'}
          icon={<Coins className="h-4 w-4" />}
        />
        <KpiCard
          label="Input Tokens"
          value={totals ? totals.input_tokens.toLocaleString() : '—'}
          icon={<ArrowUpDown className="h-4 w-4" />}
        />
        <KpiCard
          label="Output Tokens"
          value={totals ? totals.output_tokens.toLocaleString() : '—'}
          icon={<ArrowUpDown className="h-4 w-4" />}
        />
      </div>

      {/* By Model */}
      {data?.by_model && data.by_model.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">By Model</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Model</TableHead>
                  <TableHead className="text-right">Cost</TableHead>
                  <TableHead className="text-right">Tokens</TableHead>
                  <TableHead className="text-right">Executions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.by_model.map((m: UsageByModel) => (
                  <TableRow key={m.model}>
                    <TableCell className="font-mono text-xs">
                      {m.model}
                    </TableCell>
                    <TableCell className="text-right">
                      ${m.cost_usd.toFixed(4)}
                    </TableCell>
                    <TableCell className="text-right">
                      {m.total_tokens.toLocaleString()}
                    </TableCell>
                    <TableCell className="text-right">
                      {m.executions}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* By Agent */}
      {data?.by_agent && data.by_agent.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">By Agent</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Agent</TableHead>
                  <TableHead className="text-right">Cost</TableHead>
                  <TableHead className="text-right">Tokens</TableHead>
                  <TableHead className="text-right">Executions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.by_agent.map((a: UsageByAgent) => (
                  <TableRow key={a.agent}>
                    <TableCell>
                      <Badge variant="outline">{a.agent}</Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      ${a.cost_usd.toFixed(4)}
                    </TableCell>
                    <TableCell className="text-right">
                      {a.total_tokens.toLocaleString()}
                    </TableCell>
                    <TableCell className="text-right">
                      {a.executions}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* By Feature */}
      {data?.by_feature && data.by_feature.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">By Feature</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Feature</TableHead>
                  <TableHead className="text-right">Cost</TableHead>
                  <TableHead className="text-right">Tokens</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.by_feature.map((f: UsageByFeature) => (
                  <TableRow key={f.feature_id}>
                    <TableCell>
                      <div>
                        <Link
                          to="/project/$projectId/features/$featureId"
                          params={{ projectId, featureId: f.feature_id }}
                          className="text-sm hover:underline"
                        >
                          {f.feature_title}
                        </Link>
                        <span className="text-xs text-muted-foreground ml-2">
                          {f.feature_id}
                        </span>
                      </div>
                    </TableCell>
                    <TableCell className="text-right">
                      ${f.cost_usd.toFixed(4)}
                    </TableCell>
                    <TableCell className="text-right">
                      {f.total_tokens.toLocaleString()}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* Empty state */}
      {!data && !isLoading && (
        <EmptyState icon={DollarSign} title="No usage data available yet. Run some workflows to see cost analytics." />
      )}
    </div>
  );
}

function KpiCard({
  label,
  value,
  icon,
}: {
  label: string;
  value: string;
  icon: React.ReactNode;
}) {
  return (
    <Card>
      <CardContent className="pt-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs text-muted-foreground">{label}</p>
            <p className="text-2xl font-bold mt-1">{value}</p>
          </div>
          <div className="text-muted-foreground">{icon}</div>
        </div>
      </CardContent>
    </Card>
  );
}
