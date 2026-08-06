import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

/**
 * Generic bar chart. It has no knowledge of complaints, properties, or any
 * other domain concept — it just plots whatever `data` array is handed to
 * it, using `xKey` for the category axis and `yKey` for the bar value. This
 * is what lets a single component power both "Complaints by category" and
 * "Properties by status" without hardcoding either shape.
 *
 * Props:
 * - data: array of objects, e.g. [{ category: "Plumbing", count: 12 }, ...]
 * - xKey: field name to use for the x-axis label
 * - yKey: field name to use for the bar value
 * - color: bar fill color (defaults to the theme's primary color token)
 * - height: chart height in px (default 300)
 */

function formatKey(key) {
  if (!key) return "";
  return key.replace(/_/g, " ");
}

function ChartTooltip({ active, payload, label, yKey }) {
  if (!active || !payload?.length) return null;

  const value = payload[0]?.value;

  return (
    <div className="rounded-md border border-border bg-popover px-3 py-2 text-xs shadow-md">
      <p className="mb-1 font-medium text-popover-foreground">{label}</p>
      <p className="text-muted-foreground">
        {formatKey(yKey)}:{" "}
        <span className="font-semibold text-foreground">{value}</span>
      </p>
    </div>
  );
}

export default function OverviewChart({
  data,
  xKey,
  yKey,
  color = "var(--primary)",
  height = 300,
}) {
  const rotateLabels = Array.isArray(data) && data.length > 5;

  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart
        data={data}
        margin={{ top: 8, right: 8, left: -16, bottom: rotateLabels ? 16 : 4 }}
      >
        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
        <XAxis
          dataKey={xKey}
          tick={{ fill: "var(--muted-foreground)", fontSize: 12 }}
          tickLine={false}
          axisLine={{ stroke: "var(--border)" }}
          interval={0}
          angle={rotateLabels ? -25 : 0}
          textAnchor={rotateLabels ? "end" : "middle"}
          height={rotateLabels ? 50 : 30}
        />
        <YAxis
          tick={{ fill: "var(--muted-foreground)", fontSize: 12 }}
          tickLine={false}
          axisLine={false}
          allowDecimals={false}
          width={36}
        />
        <Tooltip
          cursor={{ fill: "var(--muted)", opacity: 0.4 }}
          content={<ChartTooltip yKey={yKey} />}
        />
        <Bar dataKey={yKey} fill={color} radius={[6, 6, 0, 0]} maxBarSize={48} />
      </BarChart>
    </ResponsiveContainer>
  );
}