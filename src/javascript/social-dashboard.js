const socialDashboardError = document.getElementById('social-dashboard-error');
const socialNumberFormat = new Intl.NumberFormat('en-US');
const socialMonthFormat = new Intl.DateTimeFormat('en-US', {
  month: 'short',
  year: '2-digit',
  timeZone: 'UTC',
});

function loadDashboardScript(src) {
  return new Promise((resolve, reject) => {
    const script = document.createElement('script');
    script.src = src;
    script.onload = resolve;
    script.onerror = () => reject(new Error('Could not load BokehJS. Check your internet connection and reload the page.'));
    document.head.append(script);
  });
}

async function loadDashboardBokeh(version) {
  const release = `https://cdn.bokeh.org/bokeh/release/bokeh-${encodeURIComponent(version)}`;
  if (!window.Bokeh) await loadDashboardScript(`${release}.min.js`);
  await loadDashboardScript(`https://cdn.bokeh.org/bokeh/release/bokeh-widgets-${encodeURIComponent(version)}.min.js`);
}

async function loadSocialDashboard() {
  const [reportResponse, chartsResponse] = await Promise.all([
    fetch('social-media/data/report.json', { cache: 'no-store' }),
    fetch('social-media/data/bokeh-dashboard.json', { cache: 'no-store' }),
  ]);
  if (!reportResponse.ok || !chartsResponse.ok) {
    throw new Error(`Could not load dashboard data (report: HTTP ${reportResponse.status}, charts: HTTP ${chartsResponse.status}).`);
  }

  const [report, dashboard] = await Promise.all([
    reportResponse.json(),
    chartsResponse.json(),
  ]);
  if (!report.daily?.length || !report.monthly?.length || !dashboard.charts) {
    throw new Error('The dashboard data is empty or incomplete.');
  }

  await loadDashboardBokeh(dashboard.bokeh_version);

  const summary = report.summary;
  document.getElementById('social-kpi-impressions').textContent = socialNumberFormat.format(summary.impressions);
  document.getElementById('social-kpi-engagements').textContent = socialNumberFormat.format(summary.engagements);
  document.getElementById('social-kpi-rate').textContent = `${summary.engagement_rate.toFixed(2)}%`;
  document.getElementById('social-kpi-reach').textContent = socialNumberFormat.format(summary.reach);
  document.getElementById('social-kpi-followers').textContent = socialNumberFormat.format(summary.followers);
  document.getElementById('social-kpi-new-followers').textContent = `+${socialNumberFormat.format(summary.new_followers)}`;

  const chartTargets = [
    'performance-chart',
    'followers-chart',
    'correlation-chart',
    'audience-map',
    'demographic-chart',
    'posts-chart',
  ];
  await Promise.all(chartTargets.map(async target => {
    const model = dashboard.charts[target];
    if (!model) throw new Error(`The dashboard is missing its ${target} chart.`);
    await Bokeh.embed.embed_item(model, target);
  }));

  const finalMonth = report.monthly[report.monthly.length - 1];
  const monthLabel = socialMonthFormat.format(new Date(`${finalMonth.month}T00:00:00Z`));
  document.getElementById('follower-chart-note').textContent =
    `${socialNumberFormat.format(summary.new_followers)} new followers · through ${monthLabel}`;
}

loadSocialDashboard().catch(error => {
  socialDashboardError.textContent = `LinkedIn charts could not be loaded: ${error.message}`;
  socialDashboardError.hidden = false;
});
