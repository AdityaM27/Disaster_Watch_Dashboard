/**
 * DisasterWatch Global — Main Frontend Application Logic
 * Integrates Leaflet.js, OpenStreetMap, Chart.js, GDACS, USGS, and FastAPI backend.
 * Strict No-Fake-Data Policy: Displays 100% verified real-time global telemetry.
 */

// Global State
const state = {
  currentView: 'dashboard',
  alerts: [],
  filteredAlerts: [],
  selectedAlertId: null,
  activeDisasterType: 'All',
  activeSeverity: 'All',
  activeRegion: 'all', // 'all' (global) or 'india'
  showRiskZones: true,
  officialAlertsOnly: false,
  searchQuery: '',
  activeChartTab: 'seismic',
  map: null,
  markersClusterGroup: null,
  zonesFeatureGroup: null,
  chartInstance: null
};

// ==========================================================================
// INITIALIZATION
// ==========================================================================

document.addEventListener('DOMContentLoaded', () => {
  initNavigation();
  initMap();
  initFilterListeners();
  initChartControls();
  
  // Initial live data load
  fetchDashboardData();
  fetchSourcesData();
});

// ==========================================================================
// NAVIGATION & VIEW SWITCHING
// ==========================================================================

function initNavigation() {
  const navTabs = document.querySelectorAll('.nav-tab');
  navTabs.forEach(tab => {
    tab.addEventListener('click', () => {
      const targetView = tab.getAttribute('data-view');
      switchView(targetView);
    });
  });

  // Back to dashboard button in alert details
  const backBtn = document.getElementById('btn-back-to-dashboard');
  if (backBtn) {
    backBtn.addEventListener('click', () => switchView('dashboard'));
  }
  const goToDashBtn = document.getElementById('btn-go-to-dashboard-from-details');
  if (goToDashBtn) {
    goToDashBtn.addEventListener('click', () => switchView('dashboard'));
  }

  // Reset map view button
  const resetMapBtn = document.getElementById('reset-map-view-btn');
  if (resetMapBtn) {
    resetMapBtn.addEventListener('click', resetMapView);
  }

  // Reset filters button
  const resetFiltersBtn = document.getElementById('btn-reset-filters');
  if (resetFiltersBtn) {
    resetFiltersBtn.addEventListener('click', resetAllFilters);
  }
}

function switchView(viewName) {
  state.currentView = viewName;

  // Update nav tabs
  document.querySelectorAll('.nav-tab').forEach(tab => {
    const isActive = tab.getAttribute('data-view') === viewName;
    tab.classList.toggle('active', isActive);
    tab.setAttribute('aria-selected', isActive ? 'true' : 'false');
  });

  // Update view panels
  document.querySelectorAll('.view-panel').forEach(panel => {
    panel.classList.remove('active');
  });
  const targetPanel = document.getElementById(`view-${viewName}`);
  if (targetPanel) {
    targetPanel.classList.add('active');
  }

  // Map resizing fix when switching back to dashboard
  if (viewName === 'dashboard' && state.map) {
    setTimeout(() => {
      state.map.invalidateSize();
    }, 200);
  }

  // If entering sources view, refresh sources table and logs
  if (viewName === 'data-sources') {
    fetchSourcesData();
  }
}

// ==========================================================================
// LEAFLET MAP INITIALIZATION & RENDERING (Global Center)
// ==========================================================================

function initMap() {
  // Global center: [20.0, 10.0], zoom 2.5
  state.map = L.map('disaster-map', {
    center: [20.0, 10.0],
    zoom: 2.5,
    minZoom: 2,
    maxZoom: 18,
    zoomControl: true
  });

  // OpenStreetMap Tiles
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    maxZoom: 18
  }).addTo(state.map);

  // Initialize Marker Cluster Group
  state.markersClusterGroup = L.markerClusterGroup({
    chunkedLoading: true,
    maxClusterRadius: 35,
    spiderfyOnMaxZoom: true,
    showCoverageOnHover: false
  });
  state.map.addLayer(state.markersClusterGroup);

  // Initialize Zones Feature Group
  state.zonesFeatureGroup = L.featureGroup();
  state.map.addLayer(state.zonesFeatureGroup);
}

function resetMapView() {
  if (state.map) {
    state.map.setView([20.0, 10.0], 2.5, { animate: true });
  }
}

function renderMapAlerts(alerts) {
  if (!state.map || !state.markersClusterGroup || !state.zonesFeatureGroup) return;

  // Clear previous layers
  state.markersClusterGroup.clearLayers();
  state.zonesFeatureGroup.clearLayers();

  const emptyOverlay = document.getElementById('map-empty-overlay');
  const countLabel = document.getElementById('map-events-count-label');

  if (!alerts || alerts.length === 0) {
    if (emptyOverlay) emptyOverlay.style.display = 'flex';
    if (countLabel) countLabel.textContent = '0 events matching filters';
    return;
  }

  if (emptyOverlay) emptyOverlay.style.display = 'none';
  if (countLabel) countLabel.textContent = `${alerts.length} live global disaster events displayed`;

  alerts.forEach(alert => {
    const lat = alert.latitude;
    const lon = alert.longitude;
    if (lat == null || lon == null) return;

    const disasterType = alert.disaster_type;
    const severity = alert.severity;
    const isEstimatedZone = alert.is_estimated_zone;
    const isOfficial = alert.is_official_alert;

    // Determine colors
    const colors = getDisasterColors(disasterType, severity);

    // Build Leaflet Marker
    if (disasterType === 'Earthquake') {
      const mag = alert.magnitude || 4.0;
      const radius = Math.max(7, Math.pow(mag, 1.7) * 0.85);

      const marker = L.circleMarker([lat, lon], {
        radius: radius,
        fillColor: colors.fill,
        color: colors.stroke,
        weight: 2,
        opacity: 0.95,
        fillOpacity: 0.8
      });

      marker.bindPopup(buildPopupHtml(alert));
      marker.on('click', () => handleAlertSelection(alert));
      state.markersClusterGroup.addLayer(marker);

    } else if (isEstimatedZone) {
      // Estimated Risk Zone (Dashed outline circle)
      if (state.showRiskZones) {
        const radiusMeters = (alert.zone_radius_km || 40) * 1000;
        const zoneCircle = L.circle([lat, lon], {
          radius: radiusMeters,
          color: colors.stroke,
          weight: 2,
          dashArray: '6, 6', // Dashed outline
          fillColor: colors.fill,
          fillOpacity: 0.25
        });

        zoneCircle.bindPopup(buildPopupHtml(alert));
        zoneCircle.on('click', () => handleAlertSelection(alert));
        state.zonesFeatureGroup.addLayer(zoneCircle);

        // Center marker
        const centerMarker = L.circleMarker([lat, lon], {
          radius: 5,
          color: colors.stroke,
          weight: 2,
          fillColor: '#ffffff',
          fillOpacity: 0.95
        });
        centerMarker.bindPopup(buildPopupHtml(alert));
        centerMarker.on('click', () => handleAlertSelection(alert));
        state.markersClusterGroup.addLayer(centerMarker);
      }
    } else {
      // Solid Marker (Cyclone, Fire, Official Alert, etc.)
      const solidMarker = L.circleMarker([lat, lon], {
        radius: isOfficial ? 9 : 8,
        fillColor: colors.fill,
        color: colors.stroke,
        weight: isOfficial ? 3 : 2,
        opacity: 1,
        fillOpacity: 0.85
      });

      solidMarker.bindPopup(buildPopupHtml(alert));
      solidMarker.on('click', () => handleAlertSelection(alert));
      state.markersClusterGroup.addLayer(solidMarker);
    }
  });
}

function getDisasterColors(disasterType, severity) {
  let fill = '#e76f51';
  let stroke = '#1b4332';

  switch (disasterType) {
    case 'Earthquake':
      fill = severity === 'Critical' ? '#e63946' : severity === 'High' ? '#e76f51' : severity === 'Medium' ? '#f4a261' : '#52b788';
      stroke = '#1b4332';
      break;
    case 'Flood Risk':
      fill = '#4ea8de';
      stroke = '#0077b6';
      break;
    case 'Cyclone/Storm':
      fill = '#9d8df1';
      stroke = '#5e503f';
      break;
    case 'Fire':
      fill = '#f28482';
      stroke = '#b7094c';
      break;
    case 'Heatwave':
      fill = '#f6bd60';
      stroke = '#bc6c25';
      break;
  }
  return { fill, stroke };
}

function buildPopupHtml(alert) {
  const sevBadgeClass = `badge-sev-${alert.severity.toLowerCase().slice(0, 4)}`;
  const statusBadge = alert.status === 'Confirmed Event' 
    ? '<span class="status-label-small confirmed">Confirmed Event</span>'
    : alert.status === 'Official Alert'
    ? '<span class="status-label-small confirmed" style="background: #e0e7ff; color: #3730a3;">Official Alert</span>'
    : '<span class="status-label-small estimated">Estimated Risk</span>';

  return `
    <div class="popup-container">
      <div class="popup-header">
        <span class="badge-severity ${sevBadgeClass}">${alert.severity}</span>
        ${statusBadge}
      </div>
      <h4 class="popup-title">${escapeHtml(alert.title)}</h4>
      <div class="popup-meta-row">
        <span class="popup-meta-label">Location:</span>
        <span>${escapeHtml(alert.location_name)}</span>
      </div>
      <div class="popup-meta-row">
        <span class="popup-meta-label">Source:</span>
        <span>${escapeHtml(alert.source_name)}</span>
      </div>
      <div class="popup-meta-row">
        <span class="popup-meta-label">Time:</span>
        <span>${formatTimeAgo(alert.event_time)}</span>
      </div>
      <div class="popup-rule-box">
        <strong>Telemetry:</strong> ${escapeHtml(alert.risk_rule_triggered)}
      </div>
      <button class="popup-btn" onclick="openAlertDetailsView('${alert.id}')">Inspect Full Analysis &rarr;</button>
    </div>
  `;
}

// ==========================================================================
// FILTERS & SEARCH
// ==========================================================================

function initFilterListeners() {
  // Search input
  const searchInput = document.getElementById('search-input');
  const clearBtn = document.getElementById('search-clear-btn');
  
  if (searchInput) {
    searchInput.addEventListener('input', (e) => {
      state.searchQuery = e.target.value.trim().toLowerCase();
      if (clearBtn) clearBtn.style.display = state.searchQuery ? 'block' : 'none';
      applyActiveFilters();
    });
  }

  if (clearBtn) {
    clearBtn.addEventListener('click', () => {
      if (searchInput) searchInput.value = '';
      state.searchQuery = '';
      clearBtn.style.display = 'none';
      applyActiveFilters();
    });
  }

  // Quick jump chips
  document.querySelectorAll('.chip').forEach(chip => {
    chip.addEventListener('click', () => {
      document.querySelectorAll('.chip').forEach(c => c.classList.remove('active-chip'));
      chip.classList.add('active-chip');
      const coords = chip.getAttribute('data-coords');
      const zoom = parseInt(chip.getAttribute('data-zoom') || '4', 10);
      if (coords && state.map) {
        const [lat, lon] = coords.split(',').map(Number);
        state.map.setView([lat, lon], zoom, { animate: true });
      }
    });
  });

  // Region Toggle Group (Global vs India)
  document.querySelectorAll('#region-toggle-group .btn-toggle').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('#region-toggle-group .btn-toggle').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      state.activeRegion = btn.getAttribute('data-region');
      applyActiveFilters();
    });
  });

  // Disaster Type Radios
  document.querySelectorAll('input[name="disaster_type"]').forEach(radio => {
    radio.addEventListener('change', (e) => {
      state.activeDisasterType = e.target.value;
      applyActiveFilters();
    });
  });

  // Severity Buttons
  document.querySelectorAll('#severity-filters .severity-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('#severity-filters .severity-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      state.activeSeverity = btn.getAttribute('data-severity');
      applyActiveFilters();
    });
  });

  // Display Toggles
  const riskToggle = document.getElementById('toggle-risk-zones');
  if (riskToggle) {
    riskToggle.addEventListener('change', (e) => {
      state.showRiskZones = e.target.checked;
      applyActiveFilters();
    });
  }

  const officialToggle = document.getElementById('toggle-official-only');
  if (officialToggle) {
    officialToggle.addEventListener('change', (e) => {
      state.officialAlertsOnly = e.target.checked;
      applyActiveFilters();
    });
  }

  // Quick preview close button
  const prevCloseBtn = document.getElementById('prev-close-btn');
  if (prevCloseBtn) {
    prevCloseBtn.addEventListener('click', () => {
      const prevEl = document.getElementById('selected-alert-preview');
      if (prevEl) prevEl.style.display = 'none';
      state.selectedAlertId = null;
    });
  }

  // Quick preview view full details button
  const prevDetailsBtn = document.getElementById('prev-view-details-btn');
  if (prevDetailsBtn) {
    prevDetailsBtn.addEventListener('click', () => {
      if (state.selectedAlertId) {
        openAlertDetailsView(state.selectedAlertId);
      }
    });
  }
}

function resetAllFilters() {
  state.activeDisasterType = 'All';
  state.activeSeverity = 'All';
  state.activeRegion = 'all';
  state.searchQuery = '';
  state.showRiskZones = true;
  state.officialAlertsOnly = false;

  // Reset inputs in DOM
  const allRadio = document.querySelector('input[name="disaster_type"][value="All"]');
  if (allRadio) allRadio.checked = true;

  document.querySelectorAll('#region-toggle-group .btn-toggle').forEach(b => {
    b.classList.toggle('active', b.getAttribute('data-region') === 'all');
  });

  document.querySelectorAll('#severity-filters .severity-btn').forEach(b => {
    b.classList.toggle('active', b.getAttribute('data-severity') === 'All');
  });

  const searchInput = document.getElementById('search-input');
  if (searchInput) searchInput.value = '';
  const clearBtn = document.getElementById('search-clear-btn');
  if (clearBtn) clearBtn.style.display = 'none';

  const riskToggle = document.getElementById('toggle-risk-zones');
  if (riskToggle) riskToggle.checked = true;

  const officialToggle = document.getElementById('toggle-official-only');
  if (officialToggle) officialToggle.checked = false;

  applyActiveFilters();
  resetMapView();
}

function applyActiveFilters() {
  let list = state.alerts.slice();

  // Region filter: if 'india', only show events in and around Indian subcontinent
  if (state.activeRegion === 'india') {
    list = list.filter(a => a.latitude >= 0.0 && a.latitude <= 40.0 && a.longitude >= 60.0 && a.longitude <= 100.0);
  }

  // Disaster Type filter
  if (state.activeDisasterType !== 'All') {
    list = list.filter(a => a.disaster_type.toLowerCase() === state.activeDisasterType.toLowerCase());
  }

  // Severity filter
  if (state.activeSeverity !== 'All') {
    list = list.filter(a => a.severity.toLowerCase() === state.activeSeverity.toLowerCase());
  }

  // Official Alerts Only
  if (state.officialAlertsOnly) {
    list = list.filter(a => a.is_official_alert);
  }

  // Show Estimated Risk Zones
  if (!state.showRiskZones) {
    list = list.filter(a => !a.is_estimated_zone);
  }

  // Search Query filter
  if (state.searchQuery) {
    const q = state.searchQuery;
    list = list.filter(a => 
      (a.location_name && a.location_name.toLowerCase().includes(q)) ||
      (a.title && a.title.toLowerCase().includes(q)) ||
      (a.risk_rule_triggered && a.risk_rule_triggered.toLowerCase().includes(q))
    );
  }

  state.filteredAlerts = list;

  // Re-render map, list, and chart
  renderMapAlerts(list);
  renderAlertsList(list);
  updateCounts();
  updateChart(list);
}

// ==========================================================================
// DATA FETCHING & SYNCHRONIZATION
// ==========================================================================

async function fetchDashboardData() {
  const loadingOverlay = document.getElementById('map-loading-overlay');
  if (loadingOverlay) loadingOverlay.style.display = 'flex';

  try {
    // 1. Fetch Summary
    const summaryRes = await fetch('/api/summary');
    if (summaryRes.ok) {
      const summary = await summaryRes.json();
      updateSummaryMetrics(summary);
    }

    // 2. Fetch Alerts (worldwide)
    const alertsRes = await fetch('/api/alerts?limit=500');
    if (alertsRes.ok) {
      const data = await alertsRes.json();
      state.alerts = data.alerts || [];
      if (data.last_refreshed) {
        updateLastRefreshedTime(data.last_refreshed);
      }
      applyActiveFilters();
    }
  } catch (err) {
    console.error('Error fetching live dashboard data:', err);
  } finally {
    if (loadingOverlay) loadingOverlay.style.display = 'none';
  }
}

function updateLastRefreshedTime(isoString) {
  const el = document.getElementById('last-refreshed-time');
  if (!el || !isoString) return;

  const dt = new Date(isoString);
  const options = { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false };
  el.textContent = `${dt.toLocaleTimeString([], options)} (${formatTimeAgo(isoString)})`;
}

function updateSummaryMetrics(summary) {
  const activeEl = document.getElementById('metric-active-events');
  const highEl = document.getElementById('metric-high-critical');
  const quakesEl = document.getElementById('metric-recent-quakes');
  const sourcesEl = document.getElementById('metric-sources-online');

  if (activeEl) activeEl.textContent = summary.active_events;
  if (highEl) highEl.textContent = summary.high_critical_events;
  if (quakesEl) quakesEl.textContent = summary.recent_earthquakes;
  if (sourcesEl) sourcesEl.textContent = `${summary.sources_online} / ${summary.total_sources}`;
}

function updateCounts() {
  const total = state.alerts.length;
  const quakes = state.alerts.filter(a => a.disaster_type === 'Earthquake').length;
  const cyclone = state.alerts.filter(a => a.disaster_type === 'Cyclone/Storm').length;
  const flood = state.alerts.filter(a => a.disaster_type === 'Flood Risk').length;
  const fire = state.alerts.filter(a => a.disaster_type === 'Fire').length;
  const heatwave = state.alerts.filter(a => a.disaster_type === 'Heatwave').length;

  setText('count-all', total);
  setText('count-earthquake', quakes);
  setText('count-cyclone', cyclone);
  setText('count-flood', flood);
  setText('count-fire', fire);
  setText('count-heatwave', heatwave);
}

function setText(id, text) {
  const el = document.getElementById(id);
  if (el) el.textContent = text;
}

// ==========================================================================
// ALERTS FEED & QUICK PREVIEW
// ==========================================================================

function renderAlertsList(alerts) {
  const listContainer = document.getElementById('alerts-list');
  const countBadge = document.getElementById('feed-items-count');
  if (!listContainer) return;

  listContainer.innerHTML = '';
  if (countBadge) countBadge.textContent = `${alerts.length} Events`;

  if (!alerts || alerts.length === 0) {
    listContainer.innerHTML = `
      <div class="empty-feed-placeholder" style="text-align: center; padding: 2rem 1rem; color: var(--text-subtle);">
        <p style="font-size: 0.85rem;">No live events matching the active filter.</p>
      </div>
    `;
    return;
  }

  alerts.forEach(alert => {
    const item = document.createElement('div');
    item.className = 'alert-feed-item';
    if (state.selectedAlertId === alert.id) item.classList.add('selected');

    const icon = getDisasterIcon(alert.disaster_type);
    const sevBadgeClass = `badge-sev-${alert.severity.toLowerCase().slice(0, 4)}`;
    const statusClass = alert.status === 'Confirmed Event' ? 'confirmed' : 'estimated';

    item.innerHTML = `
      <div class="feed-item-top">
        <span class="item-disaster-tag">${icon} ${escapeHtml(alert.disaster_type)}</span>
        <span class="badge-severity ${sevBadgeClass}">${alert.severity}</span>
      </div>
      <div class="feed-item-title">${escapeHtml(alert.title)}</div>
      <div class="feed-item-footer">
        <span class="status-label-small ${statusClass}">${escapeHtml(alert.status)}</span>
        <span>${formatTimeAgo(alert.event_time)}</span>
      </div>
    `;

    item.addEventListener('click', () => {
      handleAlertSelection(alert);
      if (state.map && alert.latitude != null && alert.longitude != null) {
        state.map.setView([alert.latitude, alert.longitude], 6, { animate: true });
      }
    });

    listContainer.appendChild(item);
  });
}

function handleAlertSelection(alert) {
  state.selectedAlertId = alert.id;

  // Highlight in alerts list
  document.querySelectorAll('.alert-feed-item').forEach(el => el.classList.remove('selected'));

  // Update quick preview box in right sidebar
  const prevBox = document.getElementById('selected-alert-preview');
  if (prevBox) {
    prevBox.style.display = 'block';
    setText('prev-type-badge', `${alert.disaster_type} • ${alert.status}`);
    setText('prev-title', alert.title);
    setText('prev-location', alert.location_name);
    setText('prev-status', alert.status);
    setText('prev-source', alert.source_name);
    setText('prev-rule', alert.risk_rule_triggered);

    const sevEl = document.getElementById('prev-severity-badge');
    if (sevEl) {
      sevEl.className = `badge-severity badge-sev-${alert.severity.toLowerCase().slice(0, 4)}`;
      sevEl.textContent = alert.severity;
    }

    const srcLink = document.getElementById('prev-source-link');
    if (srcLink) {
      if (alert.source_url) {
        srcLink.href = alert.source_url;
        srcLink.style.display = 'inline-flex';
      } else {
        srcLink.style.display = 'none';
      }
    }
  }
}

function getDisasterIcon(type) {
  switch (type) {
    case 'Earthquake': return '⚡';
    case 'Cyclone/Storm': return '🌀';
    case 'Flood Risk': return '🌊';
    case 'Fire': return '🔥';
    case 'Heatwave': return '☀️';
    default: return '⚠️';
  }
}

// ==========================================================================
// VIEW 2: ALERT DETAILS VIEW
// ==========================================================================

window.openAlertDetailsView = async function(alertId) {
  switchView('alert-details');
  loadAlertDetails(alertId);
};

async function loadAlertDetails(alertId) {
  const emptyState = document.getElementById('empty-details-state');
  const fullWrapper = document.getElementById('full-details-wrapper');

  try {
    const res = await fetch(`/api/alerts/${alertId}`);
    if (!res.ok) throw new Error('Alert not found');
    const alert = await res.json();

    if (emptyState) emptyState.style.display = 'none';
    if (fullWrapper) fullWrapper.style.display = 'block';

    // Header tags
    setText('det-disaster-type', alert.disaster_type);
    setText('det-severity', alert.severity);
    setText('det-status', alert.status);
    setText('det-title', alert.title);
    setText('det-location', `${alert.location_name} [${alert.latitude.toFixed(4)}°, ${alert.longitude.toFixed(4)}°]`);

    // Severity badge styling
    const sevBadge = document.getElementById('det-severity');
    if (sevBadge) {
      sevBadge.className = `badge-severity badge-sev-${alert.severity.toLowerCase().slice(0, 4)}`;
    }

    // Status badge styling
    const statusBadge = document.getElementById('det-status');
    if (statusBadge) {
      statusBadge.className = `badge-status ${alert.is_official_alert ? 'badge-solid' : 'badge-dashed'}`;
    }

    // Populate Key Metrics Grid
    const metricsGrid = document.getElementById('det-metrics-grid');
    if (metricsGrid) {
      metricsGrid.innerHTML = '';
      if (alert.disaster_type === 'Earthquake') {
        metricsGrid.innerHTML += `
          <div class="metric-tile">
            <div class="metric-tile-label">Magnitude</div>
            <div class="metric-tile-value">${alert.magnitude != null ? alert.magnitude.toFixed(1) : '--'}</div>
            <div class="metric-tile-note">Richter / Moment Scale</div>
          </div>
          <div class="metric-tile">
            <div class="metric-tile-label">Hypocentral Depth</div>
            <div class="metric-tile-value">${alert.depth_km != null ? alert.depth_km.toFixed(1) : '--'} km</div>
            <div class="metric-tile-note">${alert.depth_km <= 30 ? 'Shallow (<30km)' : 'Intermediate/Deep'}</div>
          </div>
        `;
      } else if (alert.disaster_type === 'Cyclone/Storm') {
        metricsGrid.innerHTML += `
          <div class="metric-tile">
            <div class="metric-tile-label">Wind Velocity</div>
            <div class="metric-tile-value">${alert.wind_speed_kmh != null ? alert.wind_speed_kmh.toFixed(1) : 'Gale Wind'} km/h</div>
            <div class="metric-tile-note">10-meter sustained velocity</div>
          </div>
          <div class="metric-tile">
            <div class="metric-tile-label">Risk Category</div>
            <div class="metric-tile-value">${alert.severity}</div>
            <div class="metric-tile-note">IMD / Saffir-Simpson Scale</div>
          </div>
        `;
      } else if (alert.disaster_type === 'Flood Risk' || alert.disaster_type === 'Heatwave') {
        metricsGrid.innerHTML += `
          <div class="metric-tile">
            <div class="metric-tile-label">Rainfall Accumulation</div>
            <div class="metric-tile-value">${alert.rainfall_mm != null ? alert.rainfall_mm.toFixed(1) : '0.0'} mm</div>
            <div class="metric-tile-note">24-hour total telemetry</div>
          </div>
          <div class="metric-tile">
            <div class="metric-tile-label">Temperature</div>
            <div class="metric-tile-value">${alert.temperature_c != null ? alert.temperature_c.toFixed(1) : '--'} °C</div>
            <div class="metric-tile-note">Ambient surface temperature</div>
          </div>
        `;
      }
    }

    // Risk Engine Rule banner
    setText('det-rule', alert.risk_rule_triggered);

    // Benchmarks table
    const tableEl = document.getElementById('det-benchmarks-table');
    if (tableEl) {
      tableEl.innerHTML = `
        <thead>
          <tr>
            <th>Severity Tier</th>
            <th>Trigger Benchmark Rule</th>
            <th>Observed Status</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td><span class="badge-severity badge-sev-low">Low</span></td>
            <td>Baseline telemetry or minor localized readings</td>
            <td>${alert.severity === 'Low' ? '<strong>MATCHED</strong>' : 'Passed'}</td>
          </tr>
          <tr>
            <td><span class="badge-severity badge-sev-med">Medium</span></td>
            <td>Moderate threshold exceeded; heightened attention</td>
            <td>${alert.severity === 'Medium' ? '<strong>MATCHED</strong>' : 'Passed'}</td>
          </tr>
          <tr>
            <td><span class="badge-severity badge-sev-high">High</span></td>
            <td>Warning threshold exceeded; substantial hazard exposure</td>
            <td>${alert.severity === 'High' ? '<strong>MATCHED</strong>' : 'Passed'}</td>
          </tr>
          <tr>
            <td><span class="badge-severity badge-sev-crit">Critical</span></td>
            <td>Severe emergency threshold exceeded; immediate safety action</td>
            <td>${alert.severity === 'Critical' ? '<strong>MATCHED</strong>' : 'Passed'}</td>
          </tr>
        </tbody>
      `;
    }

    // Safety Guidance
    setText('det-safety-guidance', alert.safety_guidance);

    // Lineage details
    setText('det-source-name', alert.source_name);
    setText('det-event-time', alert.event_time);
    setText('det-updated-time', alert.updated_time);
    const linkEl = document.getElementById('det-source-url');
    if (linkEl) {
      if (alert.source_url) {
        linkEl.href = alert.source_url;
        linkEl.style.display = 'inline';
      } else {
        linkEl.style.display = 'none';
      }
    }

  } catch (err) {
    console.error('Failed to load alert details:', err);
    if (emptyState) emptyState.style.display = 'block';
    if (fullWrapper) fullWrapper.style.display = 'none';
  }
}

// ==========================================================================
// VIEW 3: DATA SOURCES VIEW
// ==========================================================================

async function fetchSourcesData() {
  try {
    const res = await fetch('/api/sources');
    if (res.ok) {
      const data = await res.json();
      renderSourcesTable(data.sources);
    }

    const histRes = await fetch('/api/refresh-history?limit=15');
    if (histRes.ok) {
      const histData = await histRes.json();
      renderRefreshHistoryTable(histData.logs);
    }
  } catch (err) {
    console.error('Error fetching data sources:', err);
  }
}

function renderSourcesTable(sources) {
  const tbody = document.getElementById('sources-table-body');
  if (!tbody || !sources) return;

  tbody.innerHTML = '';
  sources.forEach(src => {
    const isConn = src.connection_status === 'Connected';
    const statusBadge = isConn 
      ? '<span class="status-badge-connected"><span class="status-dot"></span> Connected</span>'
      : '<span class="status-badge-unconnected">Not connected yet</span>';

    const lastSync = src.last_successful_update 
      ? formatTimeAgo(src.last_successful_update)
      : 'Never';

    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td><strong>${escapeHtml(src.name)}</strong></td>
      <td>${escapeHtml(src.disaster_type)}</td>
      <td>${statusBadge}</td>
      <td><span style="font-family: monospace; font-size: 0.78rem;">${lastSync}</span></td>
      <td>${escapeHtml(src.update_frequency)}</td>
      <td>${escapeHtml(src.description)}</td>
      <td><a href="${src.website_url}" target="_blank" rel="noopener noreferrer" class="link-external">Official Portal &rarr;</a></td>
    `;
    tbody.appendChild(tr);
  });
}

function renderRefreshHistoryTable(logs) {
  const tbody = document.getElementById('refresh-history-body');
  if (!tbody || !logs) return;

  tbody.innerHTML = '';
  logs.forEach(log => {
    const isSuccess = log.status === 'SUCCESS';
    const statusTag = isSuccess
      ? '<span style="color: #2d6a4f; font-weight: 700;">SUCCESS</span>'
      : `<span style="color: #b91c1c; font-weight: 700;">${log.status}</span>`;

    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td><span style="font-family: monospace; font-size: 0.75rem;">${log.timestamp.slice(0, 19).replace('T', ' ')}</span></td>
      <td><strong>${escapeHtml(log.source)}</strong></td>
      <td>${statusTag}</td>
      <td>${log.events_count}</td>
      <td>${log.duration_ms.toFixed(1)} ms</td>
      <td>${escapeHtml(log.message || '')}</td>
    `;
    tbody.appendChild(tr);
  });
}

// ==========================================================================
// CHART.JS TELEMETRY VISUALIZATION
// ==========================================================================

function initChartControls() {
  document.querySelectorAll('.btn-chart-tab').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.btn-chart-tab').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      state.activeChartTab = btn.getAttribute('data-chart');
      updateChart(state.filteredAlerts);
    });
  });
}

function updateChart(alerts) {
  const canvas = document.getElementById('live-telemetry-chart');
  const emptyState = document.getElementById('chart-empty-state');
  const chartTitle = document.getElementById('chart-title');
  if (!canvas) return;

  if (state.activeChartTab === 'seismic') {
    if (chartTitle) chartTitle.textContent = 'USGS Earthquakes: Verified Magnitude Distribution Worldwide';
    const quakes = alerts.filter(a => a.disaster_type === 'Earthquake' && a.magnitude != null);

    if (quakes.length === 0) {
      if (emptyState) emptyState.style.display = 'flex';
      canvas.style.display = 'none';
      return;
    }

    if (emptyState) emptyState.style.display = 'none';
    canvas.style.display = 'block';

    const bins = { '< 3.0': 0, '3.0 - 3.9': 0, '4.0 - 4.9': 0, '5.0 - 5.9': 0, '6.0+': 0 };
    quakes.forEach(q => {
      const m = q.magnitude;
      if (m < 3.0) bins['< 3.0']++;
      else if (m < 4.0) bins['3.0 - 3.9']++;
      else if (m < 5.0) bins['4.0 - 4.9']++;
      else if (m < 6.0) bins['5.0 - 5.9']++;
      else bins['6.0+']++;
    });

    renderBarChart(Object.keys(bins), Object.values(bins), 'Global Events Count', '#e76f51');

  } else {
    if (chartTitle) chartTitle.textContent = 'Observation Stations: Live Rainfall (mm) & Wind Speed (km/h)';
    const weatherAlerts = alerts.filter(a => a.rainfall_mm != null || a.wind_speed_kmh != null);

    if (weatherAlerts.length === 0) {
      if (emptyState) emptyState.style.display = 'flex';
      canvas.style.display = 'none';
      return;
    }

    if (emptyState) emptyState.style.display = 'none';
    canvas.style.display = 'block';

    const labels = weatherAlerts.slice(0, 10).map(a => a.location_name.split(',')[0].slice(0, 14));
    const rainData = weatherAlerts.slice(0, 10).map(a => a.rainfall_mm || 0.0);
    const windData = weatherAlerts.slice(0, 10).map(a => a.wind_speed_kmh || 0.0);

    renderDualBarChart(labels, rainData, windData);
  }
}

function renderBarChart(labels, data, label, color) {
  const canvas = document.getElementById('live-telemetry-chart');
  if (!canvas) return;

  if (state.chartInstance) {
    state.chartInstance.destroy();
  }

  const ctx = canvas.getContext('2d');
  state.chartInstance = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [{
        label: label,
        data: data,
        backgroundColor: color,
        borderRadius: 6,
        maxBarThickness: 38
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false }
      },
      scales: {
        x: {
          grid: { color: 'rgba(27, 67, 50, 0.06)' },
          ticks: { color: '#385d46', font: { size: 10 } }
        },
        y: {
          beginAtZero: true,
          grid: { color: 'rgba(27, 67, 50, 0.06)' },
          ticks: { color: '#385d46', font: { size: 10 }, stepSize: 1 }
        }
      }
    }
  });
}

function renderDualBarChart(labels, rainData, windData) {
  const canvas = document.getElementById('live-telemetry-chart');
  if (!canvas) return;

  if (state.chartInstance) {
    state.chartInstance.destroy();
  }

  const ctx = canvas.getContext('2d');
  state.chartInstance = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [
        {
          label: 'Rainfall (mm)',
          data: rainData,
          backgroundColor: '#4ea8de',
          borderRadius: 6,
          maxBarThickness: 24
        },
        {
          label: 'Wind Speed (km/h)',
          data: windData,
          backgroundColor: '#9d8df1',
          borderRadius: 6,
          maxBarThickness: 24
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: true,
          labels: { color: '#385d46', boxWidth: 10, font: { size: 10 } }
        }
      },
      scales: {
        x: {
          grid: { color: 'rgba(27, 67, 50, 0.06)' },
          ticks: { color: '#385d46', font: { size: 10 } }
        },
        y: {
          beginAtZero: true,
          grid: { color: 'rgba(27, 67, 50, 0.06)' },
          ticks: { color: '#385d46', font: { size: 10 } }
        }
      }
    }
  });
}

// ==========================================================================
// UTILITY FUNCTIONS
// ==========================================================================

function formatTimeAgo(isoString) {
  if (!isoString) return '--';
  const past = new Date(isoString).getTime();
  const now = Date.now();
  const diffSec = Math.floor((now - past) / 1000);

  if (diffSec < 60) return `${diffSec}s ago`;
  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHour = Math.floor(diffMin / 60);
  if (diffHour < 24) return `${diffHour}h ago`;
  const diffDay = Math.floor(diffHour / 24);
  return `${diffDay}d ago`;
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
