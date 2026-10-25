const numberFormat = new Intl.NumberFormat('en-US');
const dateFormat = new Intl.DateTimeFormat('en-US', {
  month: 'short',
  day: 'numeric',
  year: 'numeric',
  timeZone: 'UTC',
});
const monthFormat = new Intl.DateTimeFormat('en-US', {
  month: 'short',
  year: '2-digit',
  timeZone: 'UTC',
});
const reportError = document.getElementById('report-error');
const embeddedReport = new URLSearchParams(location.search).has('embed');

function notifyParentOfHeight() {
  if (!embeddedReport || window.parent === window) return;
  window.parent.postMessage(
    { type: 'social-report-resize', height: document.documentElement.scrollHeight + 2 },
    window.location.protocol === 'file:' ? '*' : window.location.origin,
  );
}

function labelDate(value) {
  return dateFormat.format(new Date(`${value}T00:00:00Z`));
}

function monthLabel(value) {
  return monthFormat.format(new Date(`${value}T00:00:00Z`));
}

function loadScript(src) {
  return new Promise((resolve, reject) => {
    const script = document.createElement('script');
    script.src = src;
    script.onload = resolve;
    script.onerror = () => reject(new Error('Could not load BokehJS. Check your internet connection and reload the report.'));
    document.head.append(script);
  });
}

async function loadBokeh(version) {
  const release = `https://cdn.bokeh.org/bokeh/release/bokeh-${encodeURIComponent(version)}`;
  if (!window.Bokeh) await loadScript(`${release}.min.js`);
  await loadScript(`https://cdn.bokeh.org/bokeh/release/bokeh-widgets-${encodeURIComponent(version)}.min.js`);
}

async function loadReport() {
  const [reportResponse, chartsResponse] = await Promise.all([
    fetch('data/report.json', { cache: 'no-store' }),
    fetch('data/bokeh-dashboard.json', { cache: 'no-store' }),
  ]);
  if (!reportResponse.ok || !chartsResponse.ok) {
    throw new Error(`Could not load report data (report: HTTP ${reportResponse.status}, charts: HTTP ${chartsResponse.status}).`);
  }
  const [report, dashboard] = await Promise.all([
    reportResponse.json(),
    chartsResponse.json(),
  ]);
  if (!report.daily?.length || !report.monthly?.length || !dashboard.charts) {
    throw new Error('The report data is empty or incomplete.');
  }
  await loadBokeh(dashboard.bokeh_version);

  document.getElementById('report-period').textContent =
    `${labelDate(report.period.start)} — ${labelDate(report.period.end)}`;
  document.getElementById('kpi-impressions').textContent = numberFormat.format(report.summary.impressions);
  document.getElementById('kpi-engagements').textContent = numberFormat.format(report.summary.engagements);
  document.getElementById('kpi-engagement-rate').textContent = `${report.summary.engagement_rate.toFixed(2)}%`;
  document.getElementById('kpi-reach').textContent = numberFormat.format(report.summary.reach);
  document.getElementById('kpi-followers').textContent = numberFormat.format(report.summary.followers);
  document.getElementById('kpi-new-followers').textContent = `+${numberFormat.format(report.summary.new_followers)}`;

  const chartTargets = [
    'performance-chart',
    'followers-chart',
    'correlation-chart',
    'audience-map',
    'demographic-chart',
    'posts-chart',
  ];
  for (const target of chartTargets) {
    const model = dashboard.charts[target];
    if (!model) throw new Error(`The Bokeh dashboard is missing its ${target} chart.`);
    await Bokeh.embed.embed_item(model, target);
  }

  const finalMonth = report.monthly[report.monthly.length - 1];
  document.getElementById('follower-chart-note').textContent =
    `${numberFormat.format(report.summary.new_followers)} new followers · through ${monthLabel(finalMonth.month)}`;
  if (embeddedReport) {
    const heightObserver = new ResizeObserver(notifyParentOfHeight);
    heightObserver.observe(document.body);
    heightObserver.observe(document.querySelector('.report-main'));
    window.addEventListener('load', notifyParentOfHeight, { once: true });
  }
  notifyParentOfHeight();
}

loadReport().catch(error => {
  reportError.textContent = error.message;
  reportError.hidden = false;
  notifyParentOfHeight();
});
