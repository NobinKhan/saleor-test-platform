<script lang="ts">
  import { browser } from "$app/environment";
  import { page } from "$app/stores";
  import { goto } from "$app/navigation";
  import { onDestroy } from "svelte";
  import { api, auth, exportUrl } from "$lib/api";
  import {
    Chart,
    BarController,
    BarElement,
    CategoryScale,
    LinearScale,
    Legend,
    Tooltip,
  } from "chart.js";

  Chart.register(BarController, BarElement, CategoryScale, LinearScale, Legend, Tooltip);

  $: runId = $page.params.id ?? "";

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

  interface TestResultRow {
    id: string;
    endpoint_name: string;
    endpoint_kind: string;
    category: string;
    status: string;
    outcome: string | null;
    response_valid: boolean | null;
    expected: string | null;
    expected_response: string | null;
    match_status: string | null;
    diff_summary: string | null;
    client_parity_note: string | null;
    items: {
      item_key: string;
      item_status: string;
      expected_type: string | null;
      actual_type: string | null;
    }[];
    input_sent: string | null;
    actual_response: string | null;
    error_message: string | null;
    response_time_ms: number | null;
    is_public: boolean;
  }

  interface LatencySummary {
    avg: number;
    min: number;
    max: number;
    p50: number;
    p95: number;
    sample_count: number;
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
      saleor_email: string | null;
      saleor_password_masked: string;
      test_scope: string;
      public_only: boolean;
      concurrency: number;
      timeout_seconds: number;
      reference_baseline_version: string | null;
      reference_baseline_source: string | null;
      reference_catalog_queries: number;
      reference_catalog_mutations: number;
      golden_corpus_version: string | null;
      golden_corpus_url: string | null;
      golden_probe_count: number;
      golden_match_rate: number | null;
      compatibility_score: number | null;
      golden_matched: number;
      golden_mismatched: number;
      golden_missing: number;
      client_parity_gaps: number;
      client_bundle_count: number;
      tier2_gate_enabled: boolean;
      upgrade_hint: string | null;
      probe_outcome_rate: number | null;
      probe_success_count: number;
      schema_gate_pass: boolean | null;
      schema_gate_source: string | null;
      schema_score: number | null;
      certified: boolean | null;
      test_mode: string | null;
    };
    category_breakdown: CategoryBreakdown[];
    response_time_distribution: ResponseTimeBucket[];
    latency_summary: LatencySummary;
    slowest_endpoints: {
      endpoint_name: string;
      endpoint_kind: string;
      category: string;
      status: string;
      response_time_ms: number;
      outcome: string | null;
    }[];
    results: TestResultRow[];
    pass_rate: number;
    schema_diff?: Record<string, unknown> | null;
  }

  let report: ReportData | null = null;
  let loading = false;
  let error = "";
  let loadToken = 0;
  let resultFilter: "all" | "fail" | "warn" | "slow" = "all";
  let expandedId: string | null = null;
  let showSchemaDiffRaw = false;

  interface SchemaDiffSection {
    key: string;
    label: string;
    items: string[];
  }

  function schemaDiffSections(diff: Record<string, unknown> | null | undefined): SchemaDiffSection[] {
    if (!diff) return [];
    const labels: Record<string, string> = {
      version_warning: "Version compatibility",
      missing_queries: "Missing queries (in baseline, not on target)",
      missing_mutations: "Missing mutations (in baseline, not on target)",
      extra_queries: "Extra queries (on target, not in baseline)",
      extra_mutations: "Extra mutations (on target, not in baseline)",
    };
    const sections: SchemaDiffSection[] = [];
    if (typeof diff.version_warning === "string" && diff.version_warning) {
      sections.push({ key: "version_warning", label: labels.version_warning, items: [diff.version_warning] });
    }
    for (const [key, label] of Object.entries(labels)) {
      if (key === "version_warning") continue;
      const items = Array.isArray(diff[key]) ? (diff[key] as string[]) : [];
      if (items.length) sections.push({ key, label, items });
    }
    return sections;
  }

  let responseCanvas: HTMLCanvasElement | undefined;
  let responseChart: Chart | null = null;
  let copyAiMessage = "";
  const SCHEMA_TAG_LIMIT = 15;
  let expandedSchemaSections: Record<string, boolean> = {};

  const chartDefaults = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { labels: { color: "#94a3b8" } },
    },
  };

  async function loadReport(id: string) {
    const token = ++loadToken;
    loading = true;
    error = "";
    report = null;
    destroyCharts();

    try {
      const data = await api.get(`/api/reports/${id}`);
      if (token !== loadToken) return;
      report = data;
    } catch (e: unknown) {
      if (token !== loadToken) return;
      error = e instanceof Error ? e.message : "Failed to load report";
    } finally {
      if (token === loadToken) loading = false;
    }
  }

  function destroyCharts() {
    responseChart?.destroy();
    responseChart = null;
  }

  function renderCharts() {
    if (!report || !browser || !responseCanvas) return;
    destroyCharts();

    if (report.response_time_distribution.some((r) => r.count > 0)) {
      responseChart = new Chart(responseCanvas, {
        type: "bar",
        data: {
          labels: report.response_time_distribution.map((r) => r.bucket),
          datasets: [
            {
              label: "Count",
              data: report.response_time_distribution.map((r) => r.count),
              backgroundColor: "#6366f1",
            },
          ],
        },
        options: {
          ...chartDefaults,
          plugins: { legend: { display: false } },
          scales: {
            x: { ticks: { color: "#94a3b8" }, grid: { color: "#2a2a3e" } },
            y: { ticks: { color: "#94a3b8" }, grid: { color: "#2a2a3e" } },
          },
        },
      });
    }
  }

  $: if (browser && report && responseCanvas) {
    renderCharts();
  }

  $: if (browser && runId) {
    loadReport(runId);
  }

  function downloadUrl(format: string) {
    return exportUrl(runId, format);
  }

  async function copyForAi() {
    copyAiMessage = "";
    try {
      const token = auth.getAccessToken();
      const url = exportUrl(runId, "ai");
      const res = await fetch(url, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!res.ok) throw new Error("Export failed");
      const text = await res.text();
      await navigator.clipboard.writeText(text);
      copyAiMessage = "Copied to clipboard";
      setTimeout(() => (copyAiMessage = ""), 3000);
    } catch (e: unknown) {
      copyAiMessage = e instanceof Error ? e.message : "Copy failed";
    }
  }

  function getPassRateClass(rate: number) {
    if (rate >= 80) return "high";
    if (rate >= 50) return "mid";
    return "low";
  }

  function matchBadgeClass(status: string | null): string {
    if (status === "match") return "pass";
    if (status === "parity_gap") return "warn";
    if (status === "tier2_fail") return "fail";
    if (status === "missing_golden") return "skip";
    if (status === "shape_drift") return "warn";
    return "fail";
  }

  function parityGapResults(): TestResultRow[] {
    if (!report) return [];
    return report.results.filter(
      (r) => r.match_status === "parity_gap" || r.client_parity_note
    );
  }

  function filteredResults(): TestResultRow[] {
    if (!report) return [];
    const rows = report.results;
    if (resultFilter === "fail") return rows.filter((r) => r.status === "fail");
    if (resultFilter === "warn") return rows.filter((r) => r.status === "warn");
    if (resultFilter === "slow") return rows.filter((r) => (r.response_time_ms ?? 0) >= 500);
    return rows;
  }

  function prettyJson(raw: string | null): string {
    if (!raw) return "";
    try {
      return JSON.stringify(JSON.parse(raw), null, 2);
    } catch {
      return raw;
    }
  }

  function retest() {
    if (!runId) return;
    goto(`/run/new?from=${runId}`);
  }

  onDestroy(() => {
    destroyCharts();
  });
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
      <div class="header-actions">
        <button class="btn-primary btn-sm" on:click={retest}>Retest</button>
        <a href={downloadUrl("csv")} class="btn-secondary btn-sm" download>CSV</a>
        <a href={downloadUrl("json")} class="btn-secondary btn-sm" download>JSON</a>
        <a href={downloadUrl("pdf")} class="btn-secondary btn-sm" download>PDF</a>
        <button type="button" class="btn-secondary btn-sm" on:click={copyForAi}>Copy for AI</button>
        <a href={downloadUrl("ai")} class="btn-secondary btn-sm" download>Download .md</a>
        {#if copyAiMessage}
          <span class="copy-toast">{copyAiMessage}</span>
        {/if}
      </div>
    </div>

    <div class="card baseline-banner compatibility-context">
      <h2>Compatibility context</h2>
      <table class="glossary-table">
        <tbody>
          <tr>
            <th>Target under test</th>
            <td><strong>{report.summary.saleor_version}</strong> @ {report.summary.saleor_url}</td>
          </tr>
          <tr>
            <th>Catalog (names only)</th>
            <td>
              {report.summary.reference_baseline_source ?? "saleor-dashboard"}
              {report.summary.reference_baseline_version ?? "3.23.6"}
              — {report.summary.reference_catalog_queries} queries, {report.summary.reference_catalog_mutations} mutations
            </td>
          </tr>
          <tr>
            <th>Golden reference</th>
            <td>
              Recorded from official Saleor <strong>{report.summary.golden_corpus_version ?? "3.23.7"}</strong>
              {#if report.summary.golden_corpus_url}
                @ {report.summary.golden_corpus_url}
              {/if}
              {#if report.summary.golden_probe_count}
                ({report.summary.golden_probe_count} probes)
              {/if}
            </td>
          </tr>
          <tr>
            <th>Golden match</th>
            <td>
              {#if report.summary.compatibility_score != null}
                <strong>{report.summary.compatibility_score}%</strong>
                ({report.summary.golden_matched} matched, {report.summary.golden_mismatched} mismatched, {report.summary.golden_missing} no golden)
              {:else if report.summary.golden_missing > 0}
                No golden corpus — run <code>just record-reference</code>
              {:else}
                —
              {/if}
            </td>
          </tr>
          <tr>
            <th>Test mode</th>
            <td>{report.summary.test_mode ?? "compatibility"} — replays exact golden inputs</td>
          </tr>
          <tr>
            <th>Certification scope</th>
            <td>Full + L3 Dashboard (798 endpoints)</td>
          </tr>
        </tbody>
      </table>
      {#if report.summary.upgrade_hint}
        <p class="upgrade-hint">{report.summary.upgrade_hint}</p>
      {/if}
    </div>

    <div class="card credentials-card">
      <h2>Run configuration</h2>
      <dl class="cred-grid">
        <div><dt>URL</dt><dd class="mono">{report.summary.saleor_url}</dd></div>
        <div><dt>Admin email</dt><dd>{report.summary.saleor_email ?? "—"}</dd></div>
        <div><dt>Password</dt><dd>{report.summary.saleor_password_masked}</dd></div>
        <div><dt>Concurrency</dt><dd>{report.summary.concurrency}</dd></div>
        <div><dt>Timeout</dt><dd>{report.summary.timeout_seconds}s</dd></div>
      </dl>
    </div>

    {#if report.schema_diff}
      <div class="card schema-diff">
        <h2>Schema analysis</h2>
        {#each schemaDiffSections(report.schema_diff) as section}
          <div class="diff-section">
            <h3>{section.label} ({section.items.length})</h3>
            <div class="diff-tags">
              {#each (expandedSchemaSections[section.key] ? section.items : section.items.slice(0, SCHEMA_TAG_LIMIT)) as name}
                <code class="diff-tag">{name}</code>
              {/each}
            </div>
            {#if section.items.length > SCHEMA_TAG_LIMIT}
              <button
                type="button"
                class="btn-secondary btn-sm expand-tags-btn"
                on:click={() =>
                  (expandedSchemaSections = {
                    ...expandedSchemaSections,
                    [section.key]: !expandedSchemaSections[section.key],
                  })}
              >
                {expandedSchemaSections[section.key]
                  ? "Show fewer"
                  : `Show all ${section.items.length} (${section.items.length - SCHEMA_TAG_LIMIT} more)`}
              </button>
            {/if}
          </div>
        {:else}
          <p class="text-muted">No catalog drift detected in structured diff fields.</p>
        {/each}
        <button type="button" class="btn-secondary btn-sm raw-toggle" on:click={() => (showSchemaDiffRaw = !showSchemaDiffRaw)}>
          {showSchemaDiffRaw ? "Hide" : "Show"} raw JSON
        </button>
        {#if showSchemaDiffRaw}
          <pre class="raw-diff">{JSON.stringify(report.schema_diff, null, 2)}</pre>
        {/if}
      </div>
    {/if}

    <div class="summary-row">
      {#if report.summary.compatibility_score != null}
        <div class="summary-card big">
          <span class="summary-label">Compatibility</span>
          <span class="summary-value {getPassRateClass(report.summary.compatibility_score)}">{report.summary.compatibility_score}%</span>
        </div>
      {/if}
      {#if report.summary.schema_gate_pass != null}
        <div class="summary-card {report.summary.schema_gate_pass ? 'pass' : 'fail'}">
          <span class="summary-label">Schema gate ({report.summary.schema_gate_source ?? "dashboard catalog"})</span>
          <span class="summary-value">{report.summary.schema_gate_pass ? "PASS" : "FAIL"}</span>
        </div>
      {/if}
      {#if report.summary.certified != null}
        <div class="summary-card {report.summary.certified ? 'pass' : 'warn'}">
          <span class="summary-label">Certified (100% + schema pass)</span>
          <span class="summary-value">{report.summary.certified ? "YES" : "NO"}</span>
        </div>
      {/if}
      <div class="summary-card">
        <span class="summary-label">Total probes</span>
        <span class="summary-value">{report.summary.total}</span>
      </div>
      <div class="summary-card">
        <span class="summary-label">L1 corpus probes</span>
        <span class="summary-value">{report.summary.golden_probe_count}</span>
      </div>
      <div class="summary-card">
        <span class="summary-label">L2 catalog ops</span>
        <span class="summary-value" title="Dashboard catalog query + mutation count">
          {(report.summary.reference_catalog_queries ?? 0) + (report.summary.reference_catalog_mutations ?? 0)}
        </span>
      </div>
      {#if report.summary.client_parity_gaps != null && report.summary.client_parity_gaps > 0}
        <div class="summary-card warn">
          <span class="summary-label">Tier 2 parity gaps</span>
          <span class="summary-value">{report.summary.client_parity_gaps}</span>
        </div>
      {/if}
      <div class="summary-card">
        <span class="summary-label">L3 dashboard bundles</span>
        <span class="summary-value">{report.summary.client_bundle_count ?? 0}</span>
      </div>
      {#if report.summary.tier2_gate_enabled}
        <div class="summary-card warn" title="SGRC Tier 2 is a hard certification gate">
          <span class="summary-label">Tier 2 gate</span>
          <span class="summary-value">ON</span>
        </div>
      {/if}
      <div class="summary-card pass">
        <span class="summary-label">Compatible</span>
        <span class="summary-value">{report.summary.passed}</span>
      </div>
      <div class="summary-card fail">
        <span class="summary-label">Incompatible</span>
        <span class="summary-value">{report.summary.failed}</span>
      </div>
      {#if report.summary.probe_outcome_rate != null}
        <div class="summary-card">
          <span class="summary-label">Probe success rate</span>
          <span class="summary-value" title="Informational: probes that returned success-class data (not compatibility)">{report.summary.probe_outcome_rate}%</span>
        </div>
      {/if}
      <div class="summary-card">
        <span class="summary-label">Avg Response</span>
        <span class="summary-value">{report.summary.avg_response_time_ms}ms</span>
      </div>
    </div>

    {#if parityGapResults().length > 0}
      <div class="card parity-panel">
        <h3>Client parity gaps (SGRC Tier 2)</h3>
        <p class="text-muted">
          Certified = SGRC Tier 1 pass. Parity gaps are recommended fixes for Dashboard/Storefront — they do not block certification.
        </p>
        <ul class="parity-list">
          {#each parityGapResults() as row}
            <li>
              <code>{row.endpoint_name}</code>
              <span class="text-muted">{row.endpoint_kind}</span>
              <span class="parity-note">{row.client_parity_note ?? row.diff_summary}</span>
            </li>
          {/each}
        </ul>
      </div>
    {/if}

    <div class="card latency-panel">
      <h3>Response time</h3>
      {#if report.latency_summary.sample_count > 0}
        <div class="latency-stats">
          <span>Avg <strong>{report.latency_summary.avg}ms</strong></span>
          <span>Min <strong>{report.latency_summary.min}ms</strong></span>
          <span>Max <strong>{report.latency_summary.max}ms</strong></span>
          <span>p50 <strong>{report.latency_summary.p50}ms</strong></span>
          <span>p95 <strong>{report.latency_summary.p95}ms</strong></span>
        </div>
        {#if report.response_time_distribution.some((r) => r.count > 0)}
          <div class="chart-wrap chart-wrap-sm">
            <canvas bind:this={responseCanvas}></canvas>
          </div>
        {/if}
        {#if report.slowest_endpoints.length > 0}
          <h4>Slowest endpoints</h4>
          <ul class="slow-list">
            {#each report.slowest_endpoints as s}
              <li>
                <code>{s.endpoint_name}</code>
                <span class="text-muted">{s.endpoint_kind}</span>
                <strong>{s.response_time_ms}ms</strong>
                <span class="badge badge-{s.status}">{s.status}</span>
              </li>
            {/each}
          </ul>
        {/if}
      {:else}
        <p class="text-muted">No timing samples recorded for this run.</p>
      {/if}
    </div>

    <div class="card results-explorer">
      <div class="results-header">
        <h3>Endpoint results ({filteredResults().length})</h3>
        <div class="filter-tabs">
          <button type="button" class:active={resultFilter === "all"} on:click={() => (resultFilter = "all")}>All</button>
          <button type="button" class:active={resultFilter === "fail"} on:click={() => (resultFilter = "fail")}>Failed</button>
          <button type="button" class:active={resultFilter === "warn"} on:click={() => (resultFilter = "warn")}>Warnings</button>
          <button type="button" class:active={resultFilter === "slow"} on:click={() => (resultFilter = "slow")}>Slow (&gt;500ms)</button>
        </div>
      </div>
      <div class="results-table-wrap">
        <table class="results-table">
          <thead>
            <tr>
              <th></th>
              <th>Status</th>
              <th>Endpoint</th>
              <th>Kind</th>
              <th>Outcome</th>
              <th>Match</th>
              <th>Valid</th>
              <th>ms</th>
            </tr>
          </thead>
          <tbody>
            {#each filteredResults() as row}
              <tr class="result-row" class:expanded={expandedId === row.id}>
                <td>
                  <button type="button" class="expand-btn" on:click={() => (expandedId = expandedId === row.id ? null : row.id)}>
                    {expandedId === row.id ? "−" : "+"}
                  </button>
                </td>
                <td><span class="badge badge-{row.status}">{row.status}</span></td>
                <td class="mono">{row.endpoint_name}</td>
                <td>{row.endpoint_kind}</td>
                <td class="outcome-cell">{row.outcome ?? "—"}</td>
                <td>
                  {#if row.match_status}
                    <span class="badge badge-{matchBadgeClass(row.match_status)}">{row.match_status}</span>
                  {:else}—{/if}
                </td>
                <td>
                  {#if row.response_valid === true}<span class="text-success">yes</span>
                  {:else if row.response_valid === false}<span class="text-danger">no</span>
                  {:else}—{/if}
                </td>
                <td>{row.response_time_ms ?? "—"}</td>
              </tr>
              {#if expandedId === row.id}
                <tr class="detail-row">
                  <td colspan="8">
                    <div class="detail-grid">
                      <div>
                        <h4>Expected response</h4>
                        {#if row.expected_response}
                          <pre>{prettyJson(row.expected_response)}</pre>
                        {:else}
                          <p class="text-muted">{row.expected ?? "No golden reference recorded"}</p>
                        {/if}
                        {#if row.diff_summary}<p class="text-warning diff-note">{row.diff_summary}</p>{/if}
                        {#if row.client_parity_note}<p class="text-muted parity-note">{row.client_parity_note}</p>{/if}
                      </div>
                      <div>
                        <h4>Actual response</h4>
                        <pre>{prettyJson(row.actual_response)}</pre>
                        {#if row.error_message}<p class="text-danger">{row.error_message}</p>{/if}
                      </div>
                      <div>
                        <h4>Match</h4>
                        {#if row.match_status}
                          <span class="badge badge-{matchBadgeClass(row.match_status)}">{row.match_status}</span>
                          <p class="text-muted">{row.expected ?? "—"}</p>
                        {:else}—{/if}
                      </div>
                      <div>
                        <h4>Request</h4>
                        <pre>{row.input_sent ?? ""}</pre>
                      </div>
                    </div>
                    {#if row.items && row.items.length > 0}
                      <div class="field-items">
                        <h4>Field-level comparison</h4>
                        <table class="field-table">
                          <thead>
                            <tr><th>Path</th><th>Status</th><th>Expected</th><th>Actual</th></tr>
                          </thead>
                          <tbody>
                            {#each row.items as item}
                              <tr class:field-mismatch={item.item_status !== "match"}>
                                <td class="mono">{item.item_key}</td>
                                <td>{item.item_status}</td>
                                <td>{item.expected_type ?? "—"}</td>
                                <td>{item.actual_type ?? "—"}</td>
                              </tr>
                            {/each}
                          </tbody>
                        </table>
                      </div>
                    {/if}
                  </td>
                </tr>
              {/if}
            {:else}
              <tr><td colspan="8" class="text-muted">No results match this filter.</td></tr>
            {/each}
          </tbody>
        </table>
      </div>
    </div>

    {#if report.category_breakdown.length > 0}
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
  {:else if !loading && runId}
    <div class="error-banner">No report data for this run.</div>
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

  .header-actions { display: flex; gap: 0.5rem; flex-wrap: wrap; align-items: center; }

  .schema-diff h2 { font-size: 1rem; margin-bottom: 0.75rem; }
  .diff-section { margin-bottom: 1rem; }
  .diff-section h3 { font-size: 0.85rem; color: var(--text-secondary); margin-bottom: 0.5rem; }
  .diff-tags { display: flex; flex-wrap: wrap; gap: 0.35rem; }
  .diff-tag {
    font-size: 0.75rem;
    background: var(--bg-primary);
    border: 1px solid var(--border-color);
    border-radius: 4px;
    padding: 0.15rem 0.4rem;
  }
  .raw-toggle { margin-top: 0.75rem; }
  .raw-diff {
    margin-top: 0.75rem;
    font-size: 0.7rem;
    max-height: 240px;
    overflow: auto;
    background: var(--bg-primary);
    padding: 0.75rem;
    border-radius: 6px;
  }

  .baseline-banner h2, .credentials-card h2 { font-size: 1rem; margin-bottom: 0.5rem; }
  .baseline-banner p { font-size: 0.875rem; color: var(--text-secondary); margin-bottom: 0.35rem; }
  .baseline-banner { margin-bottom: 1rem; }
  .glossary-table { width: 100%; font-size: 0.875rem; border-collapse: collapse; }
  .glossary-table th {
    text-align: left;
    color: var(--text-secondary);
    font-weight: 500;
    padding: 0.35rem 0.75rem 0.35rem 0;
    vertical-align: top;
    white-space: nowrap;
    width: 1%;
  }
  .glossary-table td { padding: 0.35rem 0; color: var(--text-primary); }
  .upgrade-hint {
    margin-top: 0.75rem;
    padding: 0.5rem 0.75rem;
    background: rgba(234, 179, 8, 0.12);
    border-radius: 6px;
    font-size: 0.8125rem;
    color: #fbbf24;
  }
  .copy-toast { font-size: 0.75rem; color: var(--accent); align-self: center; }
  .credentials-card { margin-bottom: 1.5rem; }
  .cred-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 0.75rem 1.25rem;
    font-size: 0.875rem;
  }
  .cred-grid dt { color: var(--text-muted); font-size: 0.75rem; text-transform: uppercase; }
  .cred-grid dd { margin: 0.15rem 0 0; color: var(--text-primary); }
  .mono { font-family: monospace; font-size: 0.8rem; word-break: break-all; }

  .latency-panel { margin-bottom: 1.5rem; }
  .latency-panel h3 { font-size: 1rem; margin-bottom: 0.75rem; }
  .latency-stats {
    display: flex;
    flex-wrap: wrap;
    gap: 1rem;
    font-size: 0.875rem;
    color: var(--text-secondary);
    margin-bottom: 1rem;
  }
  .slow-list { list-style: none; padding: 0; margin: 0.75rem 0 0; font-size: 0.85rem; }
  .parity-list { list-style: none; padding: 0; margin: 0.75rem 0 0; font-size: 0.85rem; }
  .parity-list li {
    display: flex; flex-wrap: wrap; gap: 0.5rem; align-items: baseline;
    padding: 0.35rem 0; border-bottom: 1px solid var(--border, #eee);
  }
  .parity-note { flex: 1 1 100%; color: var(--muted, #666); font-size: 0.8rem; }
  .slow-list li {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.35rem 0;
    border-bottom: 1px solid var(--border-color);
  }

  .results-explorer { margin-bottom: 1.5rem; }
  .results-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 0.75rem;
    margin-bottom: 1rem;
  }
  .filter-tabs { display: flex; gap: 0.35rem; }
  .filter-tabs button {
    background: var(--bg-primary);
    border: 1px solid var(--border-color);
    color: var(--text-secondary);
    padding: 0.25rem 0.6rem;
    border-radius: 6px;
    font-size: 0.8rem;
    cursor: pointer;
  }
  .filter-tabs button.active {
    border-color: var(--accent);
    color: var(--text-primary);
  }
  .results-table-wrap { overflow-x: auto; }
  .results-table { font-size: 0.8rem; }
  .outcome-cell { max-width: 140px; font-size: 0.75rem; color: var(--text-muted); }
  .expand-btn {
    background: transparent;
    border: 1px solid var(--border-color);
    color: var(--text-primary);
    width: 1.5rem;
    height: 1.5rem;
    border-radius: 4px;
    cursor: pointer;
  }
  .detail-row td { background: var(--bg-primary); padding: 1rem !important; }
  .golden-meta { margin-top: 0.5rem; }
  .diff-note { font-size: 0.8rem; margin-top: 0.5rem; }

  .field-items { margin-top: 1rem; }
  .field-items h4 { font-size: 0.8rem; color: var(--text-secondary); margin-bottom: 0.5rem; }
  .field-table { font-size: 0.75rem; width: 100%; }
  .field-table td, .field-table th { padding: 0.35rem 0.5rem; }
  .field-mismatch td { color: var(--warning); }

  .detail-grid {
    display: grid;
    grid-template-columns: 1.2fr 1.2fr 0.8fr 1fr;
    gap: 1rem;
  }
  @media (max-width: 900px) {
    .detail-grid { grid-template-columns: 1fr; }
  }
  .detail-grid h4 { font-size: 0.8rem; color: var(--text-secondary); margin-bottom: 0.35rem; }
  .detail-grid pre {
    font-size: 0.7rem;
    max-height: 220px;
    overflow: auto;
    background: var(--bg-secondary);
    padding: 0.5rem;
    border-radius: 6px;
    white-space: pre-wrap;
    word-break: break-word;
  }

  .summary-row {
    display: grid;
    grid-template-columns: repeat(6, 1fr);
    gap: 1rem;
    margin-bottom: 1.5rem;
  }

  @media (max-width: 900px) {
    .summary-row { grid-template-columns: repeat(3, 1fr); }
  }

  .summary-card {
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: 12px;
    padding: 1rem;
    text-align: center;
  }

  .summary-card.big { background: var(--bg-secondary); }

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

  .expand-tags-btn { margin-top: 0.5rem; }

  .chart-wrap {
    position: relative;
    height: 250px;
    width: 100%;
  }

  .chart-wrap-sm { height: 200px; max-width: 500px; }

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
