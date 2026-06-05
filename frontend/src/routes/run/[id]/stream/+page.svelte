<script lang="ts">
  import { onDestroy, tick } from "svelte";
  import { browser } from "$app/environment";
  import { Chart, LineController, LineElement, PointElement, LinearScale, CategoryScale, Filler } from "chart.js";

  Chart.register(LineController, LineElement, PointElement, LinearScale, CategoryScale, Filler);
  import { page } from "$app/stores";
  import { api, auth, streamUrl } from "$lib/api";
  import { goto } from "$app/navigation";

  $: runId = $page.params.id ?? "";

  interface StatusCounts {
    pass: number;
    fail: number;
    warn: number;
    skip: number;
  }

  interface StreamEvent {
    type: string;
    message?: string;
    current?: number;
    total?: number;
    current_endpoint?: string;
    status?: string;
    endpoint_kind?: string;
    category?: string;
    is_public?: boolean;
    response_time_ms?: number;
    error_message?: string;
    outcome?: string;
    expected?: string;
    response_valid?: boolean;
    status_counts?: StatusCounts;
    passed?: number;
    failed?: number;
    warnings?: number;
    skipped?: number;
    version?: string;
  }

  type ConnectionState = "connecting" | "live" | "complete" | "error";

  let events: StreamEvent[] = [];
  let activity: { time: string; text: string }[] = [];
  let statusCounts: StatusCounts = { pass: 0, fail: 0, warn: 0, skip: 0 };
  let completed = false;
  let total = 0;
  let currentEndpoint = "";
  let error = "";
  let eventSource: EventSource | null = null;
  let version = "";
  let phaseMessage = "Preparing test run…";
  let connectionState: ConnectionState = "connecting";
  let connectedRunId = "";
  let parseError = "";
  let runFinishedOffline = false;
  let pollTimer: ReturnType<typeof setInterval> | null = null;
  let latencySamples: number[] = [];
  let latencyCanvas: HTMLCanvasElement;
  let latencyChart: Chart | null = null;
  let lastResultCurrent = 0;

  function coerceCount(value: unknown): number {
    const n = Number(value);
    return Number.isFinite(n) ? n : 0;
  }

  type CountSource = Partial<StatusCounts> & {
    passed?: number;
    failed?: number;
    warnings?: number;
    skipped?: number;
    status_counts?: StatusCounts;
  };

  function normalizeStatusCounts(source?: CountSource | null): StatusCounts {
    if (!source) return { pass: 0, fail: 0, warn: 0, skip: 0 };
    const sc = source.status_counts ?? source;
    return {
      pass: coerceCount(sc.pass ?? source.passed),
      fail: coerceCount(sc.fail ?? source.failed),
      warn: coerceCount(sc.warn ?? source.warnings),
      skip: coerceCount(sc.skip ?? source.skipped),
    };
  }

  $: testedCount =
    statusCounts.pass + statusCounts.fail + statusCounts.warn + statusCounts.skip;
  $: avgLatency = latencySamples.length
    ? Math.round(latencySamples.reduce((a, b) => a + b, 0) / latencySamples.length)
    : 0;
  $: maxLatency = latencySamples.length ? Math.max(...latencySamples) : 0;
  $: progressPercent = !total
    ? completed
      ? 100
      : 0
    : Math.min(100, (testedCount / total) * 100);
  $: pageTitle = completed ? "Test Complete" : "Test in Progress";

  function pushActivity(text: string) {
    const time = new Date().toLocaleTimeString();
    activity = [{ time, text }, ...activity].slice(0, 30);
  }

  function handleStreamEvent(data: StreamEvent) {
    events = [...events.slice(-99), data];

    switch (data.type) {
      case "connected":
        connectionState = "live";
        pushActivity("Connected to live stream");
        break;
      case "progress":
        phaseMessage = data.message || phaseMessage;
        if (data.total) total = data.total;
        pushActivity(data.message || "Working…");
        break;
      case "version":
        version = data.version || "unknown";
        phaseMessage = `Saleor ${version} detected`;
        pushActivity(phaseMessage);
        break;
      case "schema_diff":
        phaseMessage = "Schema compared — running tests";
        pushActivity("Schema introspection complete");
        break;
      case "result":
        connectionState = "live";
        currentEndpoint = data.current_endpoint || "";
        if (data.total) total = data.total;
        if (data.current) lastResultCurrent = data.current;
        if (data.status_counts) statusCounts = normalizeStatusCounts(data);
        if (data.response_time_ms != null) {
          latencySamples = [...latencySamples, data.response_time_ms].slice(-20);
          updateLatencyChart();
        }
        phaseMessage = data.current_endpoint
          ? `Testing ${data.current_endpoint} (${data.response_time_ms ?? 0}ms)`
          : "Running tests…";
        break;
      case "complete":
        completed = true;
        connectionState = "complete";
        statusCounts = normalizeStatusCounts(data);
        if (data.total) total = data.total;
        if (testedCount === 0 && lastResultCurrent > 0) {
          /* replay may omit per-status tallies until complete */
        }
        if (testedCount === 0 && total > 0) {
          statusCounts = normalizeStatusCounts({
            passed: data.passed,
            failed: data.failed,
            warnings: data.warnings,
            skipped: data.skipped,
            status_counts: data.status_counts,
          });
        }
        phaseMessage = "Test run complete";
        pushActivity("All tests finished");
        closeStream();
        break;
    }
  }

  function destroyLatencyChart() {
    latencyChart?.destroy();
    latencyChart = null;
  }

  async function updateLatencyChart() {
    if (!browser || !latencyCanvas || latencySamples.length === 0) return;
    await tick();
    const labels = latencySamples.map((_, i) => String(i + 1));
    if (latencyChart) {
      latencyChart.data.labels = labels;
      latencyChart.data.datasets[0].data = [...latencySamples];
      latencyChart.update("none");
      return;
    }
    latencyChart = new Chart(latencyCanvas, {
      type: "line",
      data: {
        labels,
        datasets: [
          {
            label: "Response time (ms)",
            data: [...latencySamples],
            borderColor: "#6366f1",
            backgroundColor: "rgba(99, 102, 241, 0.15)",
            fill: true,
            tension: 0.25,
            pointRadius: 2,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { ticks: { color: "#94a3b8", maxTicksLimit: 10 }, grid: { color: "#2a2a3e" } },
          y: { ticks: { color: "#94a3b8" }, grid: { color: "#2a2a3e" }, beginAtZero: true },
        },
      },
    });
  }

  function closeStream() {
    eventSource?.close();
    eventSource = null;
  }

  function stopPolling() {
    if (pollTimer) {
      clearInterval(pollTimer);
      pollTimer = null;
    }
  }

  async function hydrateFromRun(id: string): Promise<boolean> {
    try {
      const run = await api.get(`/api/runs/${id}`);
      if (run.status === "completed" || run.status === "stopped" || run.status === "failed") {
        statusCounts = normalizeStatusCounts({
          passed: run.passed,
          failed: run.failed,
          warnings: run.warnings,
          skipped: run.skipped,
        });
        if (run.total_tests) total = run.total_tests;
        if (run.saleor_version) version = run.saleor_version;
        return true;
      }
    } catch {
      /* ignore */
    }
    return false;
  }

  async function checkRunStatus(id: string) {
    try {
      const run = await api.get(`/api/runs/${id}`);
      if (run.status === "completed" || run.status === "stopped" || run.status === "failed") {
        runFinishedOffline = true;
        if (!completed) {
          error = "";
          phaseMessage = "Test run finished — reconnecting to replay results…";
          await openStream(id, true);
        }
      }
    } catch {
      /* ignore poll errors */
    }
  }

  function startPolling(id: string) {
    stopPolling();
    pollTimer = setInterval(() => {
      if (!completed && connectionState === "error") {
        checkRunStatus(id);
      }
    }, 5000);
  }

  async function openStream(id: string, softReconnect = false) {
    closeStream();
    error = "";
    parseError = "";
    if (!softReconnect) runFinishedOffline = false;
    stopPolling();

    const finished = softReconnect || (await hydrateFromRun(id));
    if (!finished) {
      completed = false;
      connectionState = "connecting";
      phaseMessage = "Connecting to live stream…";
      events = [];
      activity = [];
      statusCounts = { pass: 0, fail: 0, warn: 0, skip: 0 };
      latencySamples = [];
      destroyLatencyChart();
      total = 0;
      version = "";
      currentEndpoint = "";
      lastResultCurrent = 0;
    } else {
      connectionState = "connecting";
      phaseMessage = "Loading replay…";
      if (!softReconnect) {
        events = [];
        activity = [];
        latencySamples = [];
        destroyLatencyChart();
        lastResultCurrent = 0;
      }
    }

    const token = auth.getAccessToken();
    if (!token) {
      goto("/login");
      return;
    }

    eventSource = new EventSource(streamUrl(id));

    eventSource.onopen = () => {
      if (!completed) connectionState = "live";
    };

    eventSource.onmessage = (e) => {
      parseError = "";
      try {
        const raw = e.data.trim();
        const jsonStr = raw.startsWith("data:") ? raw.replace(/^data:\s*/, "") : raw;
        handleStreamEvent(JSON.parse(jsonStr) as StreamEvent);
      } catch (err) {
        const msg = err instanceof Error ? err.message : "Invalid event data";
        parseError = `Could not read live update: ${msg}`;
        console.error("SSE parse error", err, e.data);
      }
    };

    eventSource.onerror = () => {
      if (completed) return;
      if (eventSource?.readyState === EventSource.CONNECTING) {
        phaseMessage = "Reconnecting…";
        connectionState = "connecting";
        return;
      }
      if (eventSource?.readyState === EventSource.CLOSED) {
        error = "Connection lost. Refresh the page or open the report when the run finishes.";
        connectionState = "error";
        closeStream();
        startPolling(id);
        checkRunStatus(id);
      }
    };

    startPolling(id);
  }

  $: if (browser && runId && runId !== connectedRunId) {
    connectedRunId = runId;
    void openStream(runId);
  }

  onDestroy(() => {
    stopPolling();
    destroyLatencyChart();
    closeStream();
  });
</script>

<svelte:head><title>{pageTitle} — Saleor Test Platform</title></svelte:head>

<div class="stream-page">
  <div class="page-header">
    <div>
      <h1>{pageTitle}</h1>
      <p class="subtitle">
        {#if version}<span class="version-tag">Saleor {version}</span>{/if}
        {phaseMessage}
      </p>
    </div>
    {#if completed}
      <a href="/run/{runId}/report" class="btn-primary">View Full Report →</a>
    {/if}
  </div>

  {#if connectionState === "connecting" && !error}
    <div class="status-banner connecting" role="status" aria-live="polite">
      <span class="spinner" aria-hidden="true"></span>
      <span>Connecting and waiting for the test worker…</span>
    </div>
  {/if}

  {#if error}
    <div class="error-banner">
      {error}
      {#if runFinishedOffline}
        <a href="/run/{runId}/report" class="btn-primary btn-sm" style="margin-top:0.5rem;display:inline-block;">View Report</a>
      {/if}
    </div>
  {/if}

  {#if parseError}
    <div class="error-banner parse-warning">{parseError}</div>
  {/if}

  <div class="stats-row">
    <div class="stat-card">
      <span class="stat-value">{testedCount}</span>
      <span class="stat-label">Tested</span>
    </div>
    <div class="stat-card">
      <span class="stat-value">{avgLatency}<span class="unit">ms</span></span>
      <span class="stat-label">Avg latency</span>
    </div>
    <div class="stat-card">
      <span class="stat-value">{maxLatency}<span class="unit">ms</span></span>
      <span class="stat-label">Max latency</span>
    </div>
    <div class="stat-card pass">
      <span class="stat-value">{statusCounts.pass}</span>
      <span class="stat-label">Passed</span>
    </div>
    <div class="stat-card fail">
      <span class="stat-value">{statusCounts.fail}</span>
      <span class="stat-label">Failed</span>
    </div>
    <div class="stat-card warn">
      <span class="stat-value">{statusCounts.warn}</span>
      <span class="stat-label">Warnings</span>
    </div>
  </div>

  <div class="progress-section card">
    <div class="progress-header">
      <span>Progress</span>
      <span>
        {#if total}
          {testedCount} / {total}
        {:else if !completed}
          Preparing…
        {:else}
          {testedCount} / {total || testedCount}
        {/if}
      </span>
    </div>
    <div class="progress-track" class:indeterminate={!total && !completed}>
      {#if total || completed}
        <div class="progress-fill" style="width:{progressPercent.toFixed(1)}%"></div>
      {:else}
        <div class="progress-fill indeterminate-bar"></div>
      {/if}
    </div>
    {#if currentEndpoint && !completed}
      <p class="current-endpoint">Current: <code>{currentEndpoint}</code></p>
    {/if}
    {#if latencySamples.length > 0}
      <div class="latency-chart-wrap">
        <span class="latency-chart-label">Recent response times (last {latencySamples.length})</span>
        <canvas bind:this={latencyCanvas}></canvas>
      </div>
    {/if}
  </div>

  <div class="panels">
    <div class="recent-results card">
      <h3>Recent Results</h3>
      <div class="results-list">
        {#each events.filter((ev) => ev.type === "result" && ev.current_endpoint).slice(-20).reverse() as ev}
          <div class="result-item">
            <span class="badge badge-{ev.status}" style="min-width:60px;text-align:center;">{ev.status}</span>
            <span class="endpoint-name">{ev.current_endpoint}</span>
            <span class="endpoint-meta">{ev.endpoint_kind} · {ev.category}{#if ev.outcome} · {ev.outcome}{/if}</span>
            <span class="response-time">{ev.response_time_ms ?? 0}ms</span>
          </div>
        {:else}
          <div class="empty">
            {#if connectionState === "connecting"}
              <span class="spinner small" aria-hidden="true"></span>
              Waiting for first results…
            {:else}
              {phaseMessage}
            {/if}
          </div>
        {/each}
      </div>
    </div>

    <div class="activity-log card">
      <h3>Activity</h3>
      <ul>
        {#each activity as item}
          <li><time>{item.time}</time> {item.text}</li>
        {:else}
          <li class="muted">Events will appear here as the run progresses.</li>
        {/each}
      </ul>
    </div>
  </div>

  {#if completed}
    <div class="complete-banner">
      <h3>✓ Test Complete</h3>
      <p>
        {statusCounts.pass} passed, {statusCounts.fail} failed, {statusCounts.warn} warnings
        {#if total}
          — {(statusCounts.pass / total * 100).toFixed(1)}% pass rate
        {/if}
      </p>
      <a href="/run/{runId}/report" class="btn-primary" style="margin-top:1rem;display:inline-block;">View Full Report</a>
    </div>
  {/if}
</div>

<style>
  .stream-page { max-width: 960px; }

  .page-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 1rem;
    margin-bottom: 1.5rem;
  }

  .page-header h1 { font-size: 1.5rem; font-weight: 700; }
  .subtitle {
    color: var(--text-secondary);
    font-size: 0.9rem;
    margin-top: 0.35rem;
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.5rem;
  }

  .version-tag {
    background: var(--bg-primary);
    border: 1px solid var(--border-color);
    border-radius: 6px;
    padding: 0.1rem 0.45rem;
    font-size: 0.8rem;
    color: var(--accent);
  }

  .status-banner {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.85rem 1rem;
    border-radius: 10px;
    margin-bottom: 1rem;
    font-size: 0.9rem;
  }

  .status-banner.connecting {
    background: var(--bg-card);
    border: 1px solid var(--accent);
    color: var(--text-primary);
  }

  .error-banner {
    background: var(--danger-bg);
    color: var(--danger);
    border-radius: 8px;
    padding: 0.75rem 1rem;
    margin-bottom: 1rem;
    font-size: 0.875rem;
  }

  .parse-warning {
    background: var(--bg-card);
    border: 1px solid var(--warning);
    color: var(--warning);
  }

  .spinner {
    width: 1.25rem;
    height: 1.25rem;
    border: 2px solid var(--border-color);
    border-top-color: var(--accent);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
    flex-shrink: 0;
  }

  .spinner.small {
    width: 1rem;
    height: 1rem;
    display: inline-block;
    vertical-align: middle;
    margin-right: 0.35rem;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  .stats-row {
    display: grid;
    grid-template-columns: repeat(6, 1fr);
    gap: 1rem;
    margin-bottom: 1.5rem;
  }

  .unit { font-size: 0.9rem; color: var(--text-muted); font-weight: 400; }

  @media (max-width: 640px) {
    .stats-row { grid-template-columns: repeat(2, 1fr); }
    .panels { grid-template-columns: 1fr; }
  }

  .stat-card {
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: 12px;
    padding: 1.25rem;
    text-align: center;
  }

  .stat-value {
    display: block;
    font-size: 2rem;
    font-weight: 700;
    color: var(--text-primary);
  }

  .stat-label {
    font-size: 0.8rem;
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .stat-card.pass .stat-value { color: var(--success); }
  .stat-card.fail .stat-value { color: var(--danger); }
  .stat-card.warn .stat-value { color: var(--warning); }

  .progress-section {
    margin-bottom: 1.5rem;
    overflow: hidden;
    isolation: isolate;
  }

  .progress-header {
    display: flex;
    justify-content: space-between;
    font-size: 0.875rem;
    margin-bottom: 0.5rem;
    color: var(--text-secondary);
  }

  .progress-track {
    height: 8px;
    background: var(--bg-primary);
    border-radius: 4px;
    overflow: hidden;
    position: relative;
  }

  .progress-fill {
    height: 100%;
    background: linear-gradient(90deg, var(--success), var(--accent));
    transition: width 0.3s ease;
  }

  .progress-track.indeterminate .indeterminate-bar {
    width: 40% !important;
    animation: indeterminate 1.4s ease-in-out infinite;
  }

  @keyframes indeterminate {
    0% { transform: translateX(-100%); }
    100% { transform: translateX(350%); }
  }

  .current-endpoint {
    margin-top: 0.5rem;
    font-size: 0.8rem;
    color: var(--text-muted);
  }

  .current-endpoint code {
    font-family: monospace;
    color: var(--text-secondary);
  }

  .latency-chart-wrap {
    margin-top: 1rem;
    position: relative;
    height: 100px;
    overflow: hidden;
  }

  .latency-chart-wrap canvas {
    display: block;
    max-height: 100px;
    width: 100% !important;
    height: 100px !important;
  }

  .latency-chart-label {
    display: block;
    font-size: 0.75rem;
    color: var(--text-muted);
    margin-bottom: 0.35rem;
  }

  .panels {
    display: grid;
    grid-template-columns: 1.4fr 1fr;
    gap: 1rem;
    position: relative;
    z-index: 1;
  }

  .recent-results h3,
  .activity-log h3 {
    font-size: 1rem;
    margin-bottom: 1rem;
  }

  .results-list { display: flex; flex-direction: column; gap: 0.5rem; }

  .result-item {
    display: grid;
    grid-template-columns: 70px 1fr 150px 80px;
    align-items: center;
    gap: 0.75rem;
    padding: 0.5rem 0.75rem;
    background: var(--bg-primary);
    border-radius: 8px;
    font-size: 0.875rem;
  }

  .endpoint-name { font-family: monospace; color: var(--text-primary); }
  .endpoint-meta { color: var(--text-muted); font-size: 0.8rem; }
  .response-time { color: var(--text-secondary); text-align: right; font-size: 0.8rem; }

  .empty {
    color: var(--text-muted);
    padding: 1.25rem;
    text-align: center;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.35rem;
  }

  .activity-log ul {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    max-height: 320px;
    overflow-y: auto;
  }

  .activity-log li {
    font-size: 0.85rem;
    color: var(--text-secondary);
    padding: 0.35rem 0;
    border-bottom: 1px solid var(--border-color);
  }

  .activity-log li:last-child { border-bottom: none; }

  .activity-log time {
    color: var(--text-muted);
    font-size: 0.75rem;
    margin-right: 0.5rem;
  }

  .activity-log .muted {
    color: var(--text-muted);
    font-style: italic;
    border: none;
  }

  .complete-banner {
    margin-top: 1.5rem;
    background: var(--success-bg);
    border: 1px solid var(--success);
    border-radius: 12px;
    padding: 1.5rem;
    text-align: center;
  }

  .complete-banner h3 { color: var(--success); margin-bottom: 0.5rem; }
  .complete-banner p { color: var(--text-secondary); }
</style>
