<script lang="ts">
  import { onMount } from "svelte";
  import { page } from "$app/stores";
  import { api, exportUrl } from "$lib/api";
  import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from "recharts";

  let runId = "";
  page.subscribe(p => { runId = p.params.id ?? ""; });

  interface CategoryBreakdown {
    category: string;
    total: number;
    passed: number;
    failed: number;
    warn: number;
    skip: number;
  }

  interface ResponseTimeBucket {
    bucket: string;
    count: number;
  }

  interface ReportData {
    summary: {
      test_run_id: string;
      total: number;
      passed: number;
      failed: number;
      warnings: number;
      skipped: number;
      pass_rate: number;
      avg_response_time_ms: number;
      saleor_version: string;
      saleor_url: string;
      started_at: string;
      completed_at: string | null;
    };
    category_breakdown: CategoryBreakdown[];
    response_time_distribution: ResponseTimeBucket[];
    pass_rate: number;
    schema_diff?: Record<string, unknown> | null;
  }

  let report: ReportData | null = null;
  let loading = true;
  let error = "";

  const COLORS = ["#22c55e", "#ef4444", "#f59e0b", "#64748b"];

  onMount(async () => {
    if (!runId) return;
    try {
      report = await api.get(`/api/reports/${runId}`);
    } catch (e: any) {
      error = e.message;
    } finally {
      loading = false;
    }
  });

  function downloadUrl(format: string) {
    return exportUrl(runId, format);
  }

  let statusFilter = "all";
  let filteredResults: any[] = [];

  function getPassRateClass(rate: number) {
    if (rate >= 80) return "high";
    if (rate >= 50) return "mid";
    return "low";
  }

  function pieLabel(props: { name?: string; percent?: number }) {
    return `${props.name ?? ""} ${((props.percent ?? 0) * 100).toFixed(0)}%`;
  }
</script>

<svelte:head><title>Report — Saleor Test Platform</title></svelte:head>

<div class="report-page">
  {#if loading}
    <div class="loading">Loading report...</div>
  {:else if error}
    <div class="error-banner">{error}</div>
  {:else if report}
    <div class="page-header">
      <div>
        <h1>Test Report</h1>
        <p class="subtitle">{report.summary.saleor_url}</p>
        <p class="meta">
          {#if report.summary.saleor_version}Saleor {report.summary.saleor_version} · {/if}
          {new Date(report.summary.started_at).toLocaleString()}
        </p>
      </div>
      <div class="export-btns">
        <a href={downloadUrl("csv")} class="btn-secondary btn-sm" download>⬇ CSV</a>
        <a href={downloadUrl("json")} class="btn-secondary btn-sm" download>⬇ JSON</a>
        <a href={downloadUrl("pdf")} class="btn-secondary btn-sm" download>⬇ PDF</a>
      </div>
    </div>

    {#if report.schema_diff}
      <div class="card schema-diff">
        <h2>Schema analysis</h2>
        <pre>{JSON.stringify(report.schema_diff, null, 2)}</pre>
      </div>
    {/if}

    <!-- Summary cards -->
    <div class="summary-row">
      <div class="summary-card big">
        <span class="summary-label">Pass Rate</span>
        <span class="summary-value {getPassRateClass(report.summary.pass_rate)}">{report.summary.pass_rate}%</span>
      </div>
      <div class="summary-card">
        <span class="summary-label">Total Tests</span>
        <span class="summary-value">{report.summary.total}</span>
      </div>
      <div class="summary-card pass">
        <span class="summary-label">Passed</span>
        <span class="summary-value">{report.summary.passed}</span>
      </div>
      <div class="summary-card fail">
        <span class="summary-label">Failed</span>
        <span class="summary-value">{report.summary.failed}</span>
      </div>
      <div class="summary-card warn">
        <span class="summary-label">Warnings</span>
        <span class="summary-value">{report.summary.warnings}</span>
      </div>
      <div class="summary-card">
        <span class="summary-label">Avg Response</span>
        <span class="summary-value">{report.summary.avg_response_time_ms}ms</span>
      </div>
    </div>

    <!-- Charts -->
    {#if report.category_breakdown.length > 0}
      <div class="charts-row">
        <div class="chart-card card">
          <h3>Pass/Fail by Category</h3>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={report.category_breakdown.map(c => ({
              name: c.category,
              Pass: c.passed,
              Fail: c.failed,
              Warn: c.warn,
            }))}>
              <CartesianGrid strokeDasharray="3 3" stroke="#2a2a3e" />
              <XAxis dataKey="name" tick={{ fill: "#94a3b8", fontSize: 12 }} />
              <YAxis tick={{ fill: "#94a3b8", fontSize: 12 }} />
              <Tooltip contentStyle={{ background: "#1a1a27", border: "1px solid #2a2a3e", borderRadius: "8px", color: "#e2e8f0" }} />
              <Bar dataKey="Pass" fill="#22c55e" radius={[4,4,0,0]} />
              <Bar dataKey="Fail" fill="#ef4444" radius={[4,4,0,0]} />
              <Bar dataKey="Warn" fill="#f59e0b" radius={[4,4,0,0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div class="chart-card card">
          <h3>Overall Result Distribution</h3>
          <div class="pie-wrap">
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie
                  data={[
                    { name: "Passed", value: report.summary.passed },
                    { name: "Failed", value: report.summary.failed },
                    { name: "Warnings", value: report.summary.warnings },
                    { name: "Skipped", value: report.summary.skipped },
                  ]}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={90}
                  dataKey="value"
                  label={pieLabel}
                  labelLine={false}
                >
                  {#each [0, 1, 2, 3] as i}
                    <Cell fill={COLORS[i]} />
                  {/each}
                </Pie>
                <Tooltip contentStyle={{ background: "#1a1a27", border: "1px solid #2a2a3e", borderRadius: "8px", color: "#e2e8f0" }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <!-- Response time distribution -->
      {#if report.response_time_distribution.length > 0}
        <div class="chart-card card" style="max-width:500px;">
          <h3>Response Time Distribution</h3>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={report.response_time_distribution.map(r => ({ name: r.bucket, count: r.count }))}>
              <CartesianGrid strokeDasharray="3 3" stroke="#2a2a3e" />
              <XAxis dataKey="name" tick={{ fill: "#94a3b8", fontSize: 12 }} />
              <YAxis tick={{ fill: "#94a3b8", fontSize: 12 }} />
              <Tooltip contentStyle={{ background: "#1a1a27", border: "1px solid #2a2a3e", borderRadius: "8px", color: "#e2e8f0" }} />
              <Bar dataKey="count" fill="#6366f1" radius={[4,4,0,0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      {/if}
    {/if}

    <!-- Category table -->
    <div class="category-table card">
      <h3>Category Breakdown</h3>
      <table>
        <thead>
          <tr>
            <th>Category</th>
            <th>Total</th>
            <th>Passed</th>
            <th>Failed</th>
            <th>Warnings</th>
            <th>Skipped</th>
            <th>Rate</th>
          </tr>
        </thead>
        <tbody>
          {#each report.category_breakdown as cat}
            <tr>
              <td class="cat-name">{cat.category}</td>
              <td>{cat.total}</td>
              <td class="text-success">{cat.passed}</td>
              <td class="text-danger">{cat.failed}</td>
              <td class="text-warning">{cat.warn}</td>
              <td class="text-muted">{cat.skip}</td>
              <td>
                {#if cat.total > 0}
                  <span class="rate {getPassRateClass((cat.passed / cat.total) * 100)}">
                    {((cat.passed / cat.total) * 100).toFixed(0)}%
                  </span>
                {:else}—{/if}
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {/if}
</div>

<style>
  .report-page { max-width: 1000px; }

  .loading { color: var(--text-secondary); padding: 2rem; text-align: center; }

  .error-banner {
    background: var(--danger-bg);
    color: var(--danger);
    border-radius: 8px;
    padding: 0.75rem 1rem;
    font-size: 0.875rem;
  }

  .page-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    margin-bottom: 1.5rem;
  }

  .page-header h1 { font-size: 1.5rem; font-weight: 700; }
  .subtitle { font-family: monospace; font-size: 0.875rem; color: var(--text-secondary); margin-top: 0.25rem; }
  .meta { font-size: 0.8rem; color: var(--text-muted); margin-top: 0.25rem; }

  .export-btns { display: flex; gap: 0.5rem; }

  .summary-row {
    display: grid;
    grid-template-columns: repeat(6, 1fr);
    gap: 1rem;
    margin-bottom: 1.5rem;
  }

  .summary-card {
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: 12px;
    padding: 1rem;
    text-align: center;
  }

  .summary-card.big {
    grid-column: span 1;
    background: var(--bg-secondary);
  }

  .summary-label {
    display: block;
    font-size: 0.75rem;
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 0.25rem;
  }

  .summary-value {
    display: block;
    font-size: 1.5rem;
    font-weight: 700;
    color: var(--text-primary);
  }

  .summary-value.high { color: var(--success); }
  .summary-value.mid { color: var(--warning); }
  .summary-value.low { color: var(--danger); }
  .summary-card.pass .summary-value { color: var(--success); }
  .summary-card.fail .summary-value { color: var(--danger); }
  .summary-card.warn .summary-value { color: var(--warning); }

  .charts-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1rem;
    margin-bottom: 1.5rem;
  }

  .chart-card h3 { font-size: 1rem; margin-bottom: 1rem; }

  .pie-wrap { display: flex; align-items: center; justify-content: center; }

  .category-table h3 { font-size: 1rem; margin-bottom: 1rem; }

  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.875rem;
  }

  table th {
    text-align: left;
    padding: 0.625rem 0.875rem;
    background: var(--bg-secondary);
    border-bottom: 1px solid var(--border-color);
    color: var(--text-secondary);
    font-weight: 600;
  }

  table td {
    padding: 0.625rem 0.875rem;
    border-bottom: 1px solid var(--border-color);
  }

  table tr:hover td { background: var(--bg-card); }

  .cat-name { text-transform: capitalize; font-weight: 500; }

  .text-success { color: var(--success); }
  .text-danger { color: var(--danger); }
  .text-warning { color: var(--warning); }
  .text-muted { color: var(--text-muted); }

  .rate { font-weight: 700; }
  .rate.high { color: var(--success); }
  .rate.mid { color: var(--warning); }
  .rate.low { color: var(--danger); }
</style>
