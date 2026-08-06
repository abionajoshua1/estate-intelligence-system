import { useState } from "react";
import {
  Loader2,
  AlertCircle,
  Inbox,
  Users,
  Building2,
  AlertTriangle,
  Landmark,
  RefreshCw,
  Sparkles,
  SlidersHorizontal,
} from "lucide-react";

import {
  useDashboardOverview,
  useComplaintsByCategory,
  usePropertiesByStatus,
  useTopResidents,
  useTopProperties,
  useRecentComplaints,
} from "@/hooks/useDashboard";

import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/components/ui/table";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

// Generic bar chart — driven entirely by xKey/yKey, no domain knowledge of
// complaints/properties baked in. See OverviewChart.jsx for details.
import OverviewChart from "@/components/OverviewChart";

/**
 * Summary card config. Real field names for /dashboard/overview/ weren't
 * confirmed, so each card tries a few common conventions and falls back to
 * whichever one the API actually returns.
 */
const SUMMARY_CARDS = [
  {
    key: "residents",
    label: "Residents",
    icon: Users,
    valueKeys: ["residents", "residents_count", "total_residents"],
    description: "Total residents registered across all properties.",
    accent: "text-blue-600 bg-blue-500/10 dark:text-blue-400",
  },
  {
    key: "properties",
    label: "Properties",
    icon: Building2,
    valueKeys: ["properties", "properties_count", "total_properties"],
    description: "Total properties currently managed on the platform.",
    accent: "text-violet-600 bg-violet-500/10 dark:text-violet-400",
  },
  {
    key: "complaints",
    label: "Complaints",
    icon: AlertTriangle,
    valueKeys: ["complaints", "complaints_count", "total_complaints"],
    description: "Total complaints filed across all properties.",
    accent: "text-amber-600 bg-amber-500/10 dark:text-amber-400",
  },
  {
    key: "estates",
    label: "Estates",
    icon: Landmark,
    valueKeys: ["estates", "estates_count", "total_estates"],
    description: "Total estates under management.",
    accent: "text-emerald-600 bg-emerald-500/10 dark:text-emerald-400",
  },
];

function pickValue(source, keys) {
  if (!source) return undefined;
  for (const key of keys) {
    if (source[key] !== undefined && source[key] !== null) return source[key];
  }
  return undefined;
}

/** Inline loading indicator used inside a section/card. */
function SectionLoading() {
  return (
    <div className="flex items-center justify-center gap-2 py-10 text-sm text-muted-foreground">
      <Loader2 className="h-4 w-4 animate-spin" />
      Loading...
    </div>
  );
}

/** Inline error indicator used inside a section/card. */
function SectionError({ error }) {
  return (
    <div className="flex items-center gap-2 rounded-md border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive">
      <AlertCircle className="h-4 w-4 shrink-0" />
      {error?.message || "Something went wrong while loading this data."}
    </div>
  );
}

/** Inline empty-state indicator used inside a section/card. */
function SectionEmpty({ label = "No data available yet." }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 py-10 text-center text-muted-foreground">
      <Inbox className="h-6 w-6" />
      <p className="text-sm">{label}</p>
    </div>
  );
}

/**
 * Wraps a React Query result with consistent loading / error / empty
 * handling so every section on the page behaves the same way.
 */
function QuerySection({ query, isEmpty, emptyLabel, children }) {
  if (query.isLoading) return <SectionLoading />;
  if (query.isError) return <SectionError error={query.error} />;
  if (isEmpty?.(query.data)) return <SectionEmpty label={emptyLabel} />;
  return children(query.data);
}

function formatCellValue(value) {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function getInitials(value) {
  if (typeof value !== "string" || !value.trim()) return "?";
  const parts = value.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

/**
 * Renders a table with columns derived from the shape of the data itself,
 * rather than hardcoded field names — the exact response shape for
 * top-residents / top-properties / recent-complaints wasn't available, so
 * this avoids silently guessing wrong keys.
 *
 * Adds a couple of enterprise-dashboard touches on top of the raw data:
 * - a rank badge when `showRank` is set (Top Residents / Top Properties)
 * - an avatar + initials next to the first column that looks like a name
 * - a "Columns" menu to show/hide fields — purely a client-side view
 *   preference, it doesn't call anything or change the underlying data
 */
function DataTable({ rows, showRank = false }) {
  const columns = Object.keys(rows[0]);
  const nameColumn = columns.find((column) => /name/i.test(column));
  const [hiddenColumns, setHiddenColumns] = useState(() => new Set());
  const visibleColumns = columns.filter((column) => !hiddenColumns.has(column));

  function toggleColumn(column) {
    setHiddenColumns((prev) => {
      const next = new Set(prev);
      if (next.has(column)) next.delete(column);
      else next.add(column);
      return next;
    });
  }

  return (
    <div className="space-y-3">
      {columns.length > 1 && (
        <div className="flex justify-end">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="sm" className="gap-1.5">
                <SlidersHorizontal className="h-3.5 w-3.5" />
                Columns
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuLabel>Toggle columns</DropdownMenuLabel>
              <DropdownMenuSeparator />
              {columns.map((column) => (
                <DropdownMenuCheckboxItem
                  key={column}
                  checked={!hiddenColumns.has(column)}
                  onCheckedChange={() => toggleColumn(column)}
                  className="capitalize"
                >
                  {column.replace(/_/g, " ")}
                </DropdownMenuCheckboxItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      )}

      <Table>
        <TableHeader>
          <TableRow>
            {showRank && <TableHead className="w-12">#</TableHead>}
            {visibleColumns.map((column) => (
              <TableHead key={column} className="whitespace-nowrap capitalize">
                {column.replace(/_/g, " ")}
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.map((row, index) => (
            <TableRow key={row.id ?? index}>
              {showRank && (
                <TableCell>
                  <Badge
                    variant={index < 3 ? "default" : "secondary"}
                    className="flex h-6 w-6 items-center justify-center rounded-full p-0 text-xs"
                  >
                    {index + 1}
                  </Badge>
                </TableCell>
              )}
              {visibleColumns.map((column) => {
                const value = row[column];
                const isStatusLike =
                  typeof value === "string" && /status|priority|severity/i.test(column);

                if (column === nameColumn && typeof value === "string") {
                  return (
                    <TableCell key={column} className="whitespace-nowrap">
                      <div className="flex items-center gap-2">
                        <Avatar className="h-7 w-7">
                          <AvatarFallback className="text-xs">
                            {getInitials(value)}
                          </AvatarFallback>
                        </Avatar>
                        <span className="font-medium text-foreground">{value}</span>
                      </div>
                    </TableCell>
                  );
                }

                return (
                  <TableCell key={column} className="whitespace-nowrap">
                    {isStatusLike ? (
                      <Badge variant="secondary">{formatCellValue(value)}</Badge>
                    ) : (
                      formatCellValue(value)
                    )}
                  </TableCell>
                );
              })}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

/**
 * Computes a handful of plain-language observations purely from data the
 * existing hooks already returned — no separate "AI insight" endpoint
 * exists, so nothing here is fetched, invented, or hardcoded. Each insight
 * is only added if the fields it depends on are actually present.
 */
function computeInsights({ overview, categories, statuses, recentComplaints }) {
  const insights = [];

  if (Array.isArray(categories) && categories.length > 0) {
    const top = [...categories].sort((a, b) => (b.count ?? 0) - (a.count ?? 0))[0];
    if (top?.category !== undefined && top?.count !== undefined) {
      insights.push({
        id: "top-category",
        text: `"${top.category}" is the most reported complaint category, with ${top.count} complaint${
          top.count === 1 ? "" : "s"
        }.`,
      });
    }
  }

  if (Array.isArray(statuses) && statuses.length > 0) {
    const top = [...statuses].sort((a, b) => (b.count ?? 0) - (a.count ?? 0))[0];
    if (top?.status !== undefined && top?.count !== undefined) {
      insights.push({
        id: "top-status",
        text: `Most properties are currently "${top.status}" (${top.count} propert${
          top.count === 1 ? "y" : "ies"
        }).`,
      });
    }
  }

  const complaintsTotal = pickValue(overview, ["complaints", "complaints_count", "total_complaints"]);
  const propertiesTotal = pickValue(overview, ["properties", "properties_count", "total_properties"]);
  if (typeof complaintsTotal === "number" && typeof propertiesTotal === "number" && propertiesTotal > 0) {
    insights.push({
      id: "ratio",
      text: `On average, there are ${(complaintsTotal / propertiesTotal).toFixed(
        2
      )} complaints per property across the portfolio.`,
    });
  }

  if (Array.isArray(recentComplaints)) {
    insights.push({
      id: "recent-volume",
      text: `${recentComplaints.length} complaint${
        recentComplaints.length === 1 ? "" : "s"
      } currently showing in the recent activity feed.`,
    });
  }

  return insights;
}

export default function Dashboard() {
  const overviewQuery = useDashboardOverview();
  const complaintsByCategoryQuery = useComplaintsByCategory();
  const propertiesByStatusQuery = usePropertiesByStatus();
  const topResidentsQuery = useTopResidents();
  const topPropertiesQuery = useTopProperties();
  const recentComplaintsQuery = useRecentComplaints();

  const isRefreshing =
    overviewQuery.isFetching ||
    complaintsByCategoryQuery.isFetching ||
    propertiesByStatusQuery.isFetching ||
    topResidentsQuery.isFetching ||
    topPropertiesQuery.isFetching ||
    recentComplaintsQuery.isFetching;

  function handleRefreshAll() {
    overviewQuery.refetch();
    complaintsByCategoryQuery.refetch();
    propertiesByStatusQuery.refetch();
    topResidentsQuery.refetch();
    topPropertiesQuery.refetch();
    recentComplaintsQuery.refetch();
  }

  const categoryTotal = Array.isArray(complaintsByCategoryQuery.data)
    ? complaintsByCategoryQuery.data.reduce((sum, row) => sum + (Number(row.count) || 0), 0)
    : undefined;
  const statusTotal = Array.isArray(propertiesByStatusQuery.data)
    ? propertiesByStatusQuery.data.reduce((sum, row) => sum + (Number(row.count) || 0), 0)
    : undefined;

  const insightsLoading =
    overviewQuery.isLoading || complaintsByCategoryQuery.isLoading || propertiesByStatusQuery.isLoading;
  const insights = computeInsights({
    overview: overviewQuery.data,
    categories: complaintsByCategoryQuery.data,
    statuses: propertiesByStatusQuery.data,
    recentComplaints: recentComplaintsQuery.data,
  });

  return (
    <TooltipProvider delayDuration={200}>
      <div className="flex flex-col gap-6 pb-10">
        {/* Header */}
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight text-foreground">
              Estate Overview
            </h1>
            <p className="text-sm text-muted-foreground">
              A live snapshot of residents, properties, and complaint activity.
            </p>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={handleRefreshAll}
            disabled={isRefreshing}
            className="gap-2 self-start sm:self-auto"
          >
            <RefreshCw className={`h-4 w-4 ${isRefreshing ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        </div>

        {/* Summary cards */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {SUMMARY_CARDS.map(({ key, label, icon: Icon, valueKeys, description, accent }) => (
            <Card key={key} className="transition-shadow hover:shadow-md">
              <CardContent className="flex items-center justify-between gap-4 p-6">
                <div className="min-w-0">
                  <p className="text-sm text-muted-foreground">{label}</p>
                  <div className="mt-1 truncate text-2xl font-semibold text-foreground">
                    {overviewQuery.isLoading ? (
                      <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                    ) : overviewQuery.isError ? (
                      "—"
                    ) : (
                      formatCellValue(pickValue(overviewQuery.data, valueKeys))
                    )}
                  </div>
                </div>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <div
                      className={`flex h-10 w-10 shrink-0 cursor-default items-center justify-center rounded-lg ${accent}`}
                    >
                      <Icon className="h-5 w-5" strokeWidth={1.75} />
                    </div>
                  </TooltipTrigger>
                  <TooltipContent>{description}</TooltipContent>
                </Tooltip>
              </CardContent>
            </Card>
          ))}
        </div>
        {overviewQuery.isError && <SectionError error={overviewQuery.error} />}

        {/* AI insight panel */}
        <Card className="border-primary/20 bg-primary/[0.03]">
          <CardHeader className="flex flex-row items-center gap-2 space-y-0">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <Sparkles className="h-4 w-4" />
            </div>
            <div>
              <CardTitle className="text-base">Insights</CardTitle>
              <CardDescription>Automatically generated from your current dashboard data.</CardDescription>
            </div>
          </CardHeader>
          <CardContent>
            {insightsLoading ? (
              <SectionLoading />
            ) : insights.length === 0 ? (
              <SectionEmpty label="Not enough data yet to generate insights." />
            ) : (
              <ul className="grid grid-cols-1 gap-2 md:grid-cols-2">
                {insights.map((insight) => (
                  <li
                    key={insight.id}
                    className="flex items-start gap-2 rounded-md border border-border/60 bg-background px-3 py-2 text-sm text-foreground"
                  >
                    <Sparkles className="mt-0.5 h-3.5 w-3.5 shrink-0 text-primary" />
                    <span>{insight.text}</span>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>

        {/* Charts */}
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
          <Card>
            <CardHeader className="flex flex-row items-start justify-between space-y-0">
              <div>
                <CardTitle>Complaints by category</CardTitle>
                <CardDescription>Distribution of complaints across categories.</CardDescription>
              </div>
              {categoryTotal !== undefined && (
                <Badge variant="secondary" className="shrink-0">
                  {categoryTotal} total
                </Badge>
              )}
            </CardHeader>
            <CardContent>
              <QuerySection
                query={complaintsByCategoryQuery}
                isEmpty={(data) => !data || data.length === 0}
                emptyLabel="No complaint data yet."
              >
                {(data) => (
                  <OverviewChart data={data} xKey="category" yKey="count" color="#f59e0b" />
                )}
              </QuerySection>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-start justify-between space-y-0">
              <div>
                <CardTitle>Properties by status</CardTitle>
                <CardDescription>Breakdown of properties by current status.</CardDescription>
              </div>
              {statusTotal !== undefined && (
                <Badge variant="secondary" className="shrink-0">
                  {statusTotal} total
                </Badge>
              )}
            </CardHeader>
            <CardContent>
              <QuerySection
                query={propertiesByStatusQuery}
                isEmpty={(data) => !data || data.length === 0}
                emptyLabel="No property data yet."
              >
                {(data) => (
                  <OverviewChart data={data} xKey="status" yKey="count" color="#8b5cf6" />
                )}
              </QuerySection>
            </CardContent>
          </Card>
        </div>

        {/* Top lists */}
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>Top residents</CardTitle>
              <CardDescription>Most active residents on the platform.</CardDescription>
            </CardHeader>
            <CardContent className="overflow-x-auto">
              <QuerySection
                query={topResidentsQuery}
                isEmpty={(data) => !data || data.length === 0}
                emptyLabel="No resident activity yet."
              >
                {(data) => <DataTable rows={data} showRank />}
              </QuerySection>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Top properties</CardTitle>
              <CardDescription>Properties with the most activity.</CardDescription>
            </CardHeader>
            <CardContent className="overflow-x-auto">
              <QuerySection
                query={topPropertiesQuery}
                isEmpty={(data) => !data || data.length === 0}
                emptyLabel="No property activity yet."
              >
                {(data) => <DataTable rows={data} showRank />}
              </QuerySection>
            </CardContent>
          </Card>
        </div>

        {/* Recent complaints */}
        <Card>
          <CardHeader>
            <CardTitle>Recent complaints</CardTitle>
            <CardDescription>The latest complaints filed across all properties.</CardDescription>
          </CardHeader>
          <CardContent className="overflow-x-auto">
            <QuerySection
              query={recentComplaintsQuery}
              isEmpty={(data) => !data || data.length === 0}
              emptyLabel="No complaints have been filed yet."
            >
              {(data) => <DataTable rows={data} />}
            </QuerySection>
          </CardContent>
        </Card>
      </div>
    </TooltipProvider>
  );
}