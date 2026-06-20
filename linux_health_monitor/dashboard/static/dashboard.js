const REFRESH_MS = (window.DASHBOARD_REFRESH_SECONDS || 5) * 1000;

function gaugeColor(value) {
  if (value > 90) return '#f76e6e';
  if (value >= 70) return '#f6c85f';
  return '#36d399';
}

function renderGauge(target, title, value) {
  const color = gaugeColor(value);
  Plotly.react(
    target,
    [{
      type: 'indicator',
      mode: 'gauge+number',
      value,
      title: { text: title, font: { color: '#dbe6f2' } },
      gauge: {
        axis: { range: [0, 100], tickcolor: '#8ea0b6' },
        bar: { color },
        bgcolor: '#1b2430',
        bordercolor: '#304053',
        steps: [
          { range: [0, 80], color: '#1f3a30' },
          { range: [80, 95], color: '#3c3521' },
          { range: [95, 100], color: '#442728' }
        ]
      },
      number: { suffix: '%', font: { color: '#dbe6f2' } }
    }],
    {
      margin: { t: 40, r: 25, l: 25, b: 10 },
      paper_bgcolor: 'rgba(0,0,0,0)',
      plot_bgcolor: 'rgba(0,0,0,0)',
      font: { color: '#dbe6f2' }
    },
    { displayModeBar: false, responsive: true }
  );
}

function renderDiskChart(disks) {
  const labels = disks.map(item => item.label || item.mount);
  const values = disks.map(item => item.usage_percent);
  const colors = values.map(gaugeColor);
  const text = values.map(value => `${value.toFixed(1)}%`);
  const tickAngle = disks.length <= 6 ? 0 : -20;

  Plotly.react(
    'disk-chart',
    [{
      type: 'bar',
      x: labels,
      y: values,
      marker: { color: colors },
      text,
      textposition: 'outside',
      cliponaxis: false,
      customdata: disks.map(item => item.mount),
      hovertemplate: '<b>%{x}</b><br>Usage: %{y:.1f}%<br>Mount: %{customdata}<extra></extra>'
    }],
    {
      yaxis: { title: 'Usage %', range: [0, 100], gridcolor: '#304053' },
      xaxis: { tickangle: tickAngle },
      margin: { t: 10, r: 10, l: 45, b: 60 },
      paper_bgcolor: 'rgba(0,0,0,0)',
      plot_bgcolor: 'rgba(0,0,0,0)',
      font: { color: '#dbe6f2' }
    },
    { displayModeBar: false, responsive: true }
  );
}

function renderNetworkChart(network) {
  Plotly.react(
    'network-chart',
    [
      {
        type: 'scatter',
        mode: 'lines+markers',
        name: 'Bytes Sent',
        x: network.timestamps,
        y: network.bytes_sent,
        line: { color: '#53b6ff' }
      },
      {
        type: 'scatter',
        mode: 'lines+markers',
        name: 'Bytes Received',
        x: network.timestamps,
        y: network.bytes_recv,
        line: { color: '#36d399' }
      }
    ],
    {
      yaxis: { title: 'Cumulative Bytes', gridcolor: '#304053' },
      xaxis: { title: 'Collected At' },
      margin: { t: 10, r: 10, l: 50, b: 45 },
      paper_bgcolor: 'rgba(0,0,0,0)',
      plot_bgcolor: 'rgba(0,0,0,0)',
      font: { color: '#dbe6f2' }
    },
    { displayModeBar: false, responsive: true }
  );
}

function renderProcessTable(bodyId, rows) {
  const body = document.getElementById(bodyId);
  body.innerHTML = '';

  rows.forEach(item => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${item.pid}</td>
      <td>${item.name}</td>
      <td>${item.cpu_percent.toFixed(1)}</td>
      <td>${item.memory_percent.toFixed(1)}</td>
    `;
    body.appendChild(tr);
  });

  if (!rows.length) {
    const tr = document.createElement('tr');
    tr.innerHTML = '<td colspan="4" class="empty">No process data yet.</td>';
    body.appendChild(tr);
  }
}

function renderList(containerId, items, formatter, emptyText) {
  const container = document.getElementById(containerId);
  container.innerHTML = '';

  if (!items.length) {
    const empty = document.createElement('div');
    empty.className = 'empty';
    empty.textContent = emptyText;
    container.appendChild(empty);
    return;
  }

  items.forEach(item => {
    const card = document.createElement('div');
    card.className = `item ${String(item.severity || 'ok').toLowerCase()}`;
    card.innerHTML = formatter(item);
    container.appendChild(card);
  });
}

function renderSystemInfo(systemInfo) {
  const badge = document.getElementById('platform-badge');
  const grid = document.getElementById('system-info-grid');
  if (!badge || !grid || !systemInfo) return;

  badge.textContent = systemInfo.platform || 'Unknown';
  badge.className = `platform-badge ${String(systemInfo.platform || 'unknown').toLowerCase()}`;

  const fields = [
    ['Operating System', systemInfo.operating_system || 'Unavailable'],
    ['Hostname', systemInfo.hostname || 'Unavailable'],
    ['Python Version', systemInfo.python_version || 'Unavailable'],
    ['CPU Architecture', systemInfo.cpu_architecture || 'Unavailable'],
    ['CPU Cores', `${systemInfo.physical_cores || 'Unavailable'} physical / ${systemInfo.logical_cores || 'Unavailable'} logical`],
    ['Total RAM', systemInfo.total_ram_gb || 'Unavailable'],
    ['Log Source', systemInfo.log_source && systemInfo.log_source.available ? systemInfo.log_source.value : 'No accessible system log on this device'],
  ];

  grid.innerHTML = '';
  fields.forEach(([label, value]) => {
    const item = document.createElement('div');
    item.className = 'system-info-item';
    item.innerHTML = `<span class="system-info-label">${label}</span><span class="system-info-value">${value}</span>`;
    grid.appendChild(item);
  });
}

async function refreshDashboard() {
  try {
    const response = await fetch('/api/latest');
    const payload = await response.json();

    const updated = document.getElementById('last-updated');
    updated.textContent = `Last update: ${new Date(payload.generated_at).toLocaleString()}`;

    renderSystemInfo(payload.system_info);

    if (!payload.has_data) {
      renderList('anomalies', [], () => '', payload.message || 'Waiting for data...');
      return;
    }

    renderGauge('cpu-gauge', 'CPU', payload.cpu_percent);
    renderGauge('memory-gauge', 'Memory', payload.memory_percent);
    renderDiskChart(payload.disk_usage);
    const diskNote = document.getElementById('disk-chart-note');
    if (diskNote && payload.disk_chart_note) {
      diskNote.textContent = payload.disk_chart_note;
    }
    renderNetworkChart(payload.network);

    renderProcessTable('top-cpu-body', payload.top_cpu_processes);
    renderProcessTable('top-memory-body', payload.top_memory_processes);

    renderList(
      'anomalies',
      payload.active_anomalies,
      item => `<strong>${item.severity.toUpperCase()}</strong> - ${item.message}`,
      'No active anomalies in recent cycles.'
    );

    renderList(
      'recent-logs',
      payload.recent_logs,
      item => `<strong>${item.severity}</strong> [${item.source}]<br>${item.message}`,
      payload.recent_logs_message || 'No recent log errors found.'
    );
  } catch (error) {
    renderList('anomalies', [], () => '', 'Failed to load dashboard data.');
  }
}

refreshDashboard();
setInterval(refreshDashboard, REFRESH_MS);
