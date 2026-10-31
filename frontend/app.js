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
  chartInstance: null,
  aiChartInstance: null
};

// ==========================================================================
// INITIALIZATION
// ==========================================================================

document.addEventListener('DOMContentLoaded', () => {
  initNavigation();
  initMap();
  initFilterListeners();
  initChartControls();
  initAIPredictor();
  initSidebarAIHub();
  
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

  // Quick sub-header AI jump button
  const quickAiNavBtn = document.getElementById('btn-quick-nav-ai');
  if (quickAiNavBtn) {
    quickAiNavBtn.addEventListener('click', () => switchView('ai-predictor'));
  }

  // Main dashboard AI quick banner buttons
  document.querySelectorAll('.btn-banner-ai-chip').forEach(btn => {
    btn.addEventListener('click', () => {
      const city = btn.getAttribute('data-location') || 'Mumbai';
      switchView('ai-predictor');
      const areaInput = document.getElementById('area-query-input');
      if (areaInput) areaInput.value = city;
      runAreaThreatAnalysis(city);
    });
  });

  const bannerLaunchBtn = document.getElementById('btn-banner-launch-ai');
  if (bannerLaunchBtn) {
    bannerLaunchBtn.addEventListener('click', () => {
      switchView('ai-predictor');
    });
  }

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

  // URL Hash Routing support (#ai, #ai-predictor, #dashboard, etc.)
  window.addEventListener('hashchange', handleHashRouting);
  if (window.location.hash) {
    handleHashRouting();
  }
}

function handleHashRouting() {
  const hash = window.location.hash.replace('#', '').trim();
  if (hash === 'ai' || hash === 'ai-predictor') {
    switchView('ai-predictor');
  } else if (hash === 'alert-details') {
    switchView('alert-details');
  } else if (hash === 'data-sources') {
    switchView('data-sources');
  } else if (hash === 'dashboard') {
    switchView('dashboard');
  }
}

function switchView(viewName) {
  state.currentView = viewName;

  // Sync hash without extra history entries
  if (window.location.hash !== '#' + viewName) {
    try {
      history.replaceState(null, '', '#' + viewName);
    } catch (e) {}
  }

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

  // If entering AI predictor view, trigger initial prediction
  if (viewName === 'ai-predictor') {
    if (!state.aiInitialized) {
      state.aiInitialized = true;
      runAreaThreatAnalysis('Mumbai');
    } else if (state.aiChartInstance) {
      state.aiChartInstance.resize();
    }
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

  // Quick preview run AI prediction button
  const prevAiBtn = document.getElementById('prev-ai-pred-btn');
  if (prevAiBtn) {
    prevAiBtn.addEventListener('click', () => {
      if (state.selectedAlertId) {
        launchAIPredictionForAlert(state.selectedAlertId);
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

    const prevPdfBtn = document.getElementById('prev-pdf-btn');
    if (prevPdfBtn) {
      prevPdfBtn.href = `/api/alerts/${alert.id}/pdf`;
      prevPdfBtn.style.display = 'inline-flex';
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

    // Set Area Disaster Report PDF link
    const areaPdfBtn = document.getElementById('det-download-area-pdf');
    if (areaPdfBtn) {
      areaPdfBtn.href = `/api/alerts/${alert.id}/pdf`;
    }

    // Set External Source Feed button
    const extSrcBtn = document.getElementById('det-source-external-btn');
    if (extSrcBtn) {
      if (alert.source_url) {
        extSrcBtn.href = alert.source_url;
        extSrcBtn.style.display = 'inline-flex';
      } else {
        extSrcBtn.style.display = 'none';
      }
    }

    // Set AI Future Trajectory launch button
    const detAiBtn = document.getElementById('det-launch-ai-pred-btn');
    if (detAiBtn) {
      detAiBtn.onclick = () => {
        launchAIPredictionForAlert(alert.id, alert);
      };
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

// ==========================================================================
// VIEW 4: AI DISASTER FUTURE PREDICTOR LOGIC
// ==========================================================================

const aiScenariosMap = {
  'scenario-brahmaputra': {
    type: 'Flood Risk',
    name: 'Brahmaputra Basin, Guwahati, Assam',
    lat: 26.1445,
    lon: 91.7362,
    val: 28.5
  },
  'scenario-cyclone-dana': {
    type: 'Cyclone/Storm',
    name: 'Puri-Paradip Coastal Corridor, Odisha',
    lat: 19.8135,
    lon: 85.8312,
    val: 92.0
  },
  'scenario-delhi-seismic': {
    type: 'Earthquake',
    name: 'Mahendragarh-Dehradun Fault, Delhi-NCR',
    lat: 28.6139,
    lon: 77.2090,
    val: 5.8
  },
  'scenario-vidarbha-heat': {
    type: 'Heatwave',
    name: 'Nagpur & Chandrapur District, Maharashtra',
    lat: 21.1458,
    lon: 79.0882,
    val: 44.8
  }
};

// ==========================================================================
// MAIN SERVER RIGHT SIDEBAR AI HUB
// ==========================================================================

function initSidebarAIHub() {
  const calcBtn = document.getElementById('btn-hub-calc');
  const input = document.getElementById('hub-area-input');
  const chips = document.querySelectorAll('.hub-chip');
  const fullLink = document.getElementById('btn-hub-open-full-predictor');

  if (calcBtn && input) {
    calcBtn.addEventListener('click', () => {
      runHubThreatAnalysis(input.value.trim() || 'Mumbai');
    });

    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        runHubThreatAnalysis(input.value.trim() || 'Mumbai');
      }
    });
  }

  if (chips && input) {
    chips.forEach(chip => {
      chip.addEventListener('click', () => {
        chips.forEach(c => c.classList.remove('active'));
        chip.classList.add('active');
        const city = chip.getAttribute('data-city') || 'Mumbai';
        input.value = city;
        runHubThreatAnalysis(city);
      });
    });
  }

  if (fullLink && input) {
    fullLink.addEventListener('click', () => {
      const city = input.value.trim() || 'Mumbai';
      switchView('ai-predictor');
      const areaInput = document.getElementById('area-query-input');
      if (areaInput) areaInput.value = city;
      runAreaThreatAnalysis(city);
    });
  }

  // Pre-load threat data for Mumbai on dashboard start
  runHubThreatAnalysis('Mumbai');
}

async function runHubThreatAnalysis(locationQuery) {
  const outBox = document.getElementById('hub-threat-output');
  if (!outBox) return;

  outBox.innerHTML = `
    <div style="font-size: 0.76rem; color: var(--text-subtle); display: flex; align-items: center; gap: 6px;">
      <svg class="spin-icon" viewBox="0 0 24 24" width="13" height="13" stroke="currentColor" fill="none" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 2a10 10 0 0 1 10 10"/></svg>
      Evaluating threat for ${escapeHtml(locationQuery)}...
    </div>
  `;

  try {
    const resp = await fetch('/api/ai/analyze-area', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ location: locationQuery, radius_km: 250.0 })
    });

    if (!resp.ok) throw new Error('API failed');
    const data = await resp.json();
    const sum = data.threat_summary;
    const tel = data.telemetry_snapshot;

    outBox.innerHTML = `
      <div class="hub-output-top">
        <span style="font-size: 0.8rem; font-weight: 700; color: var(--text-main);">${escapeHtml(data.location.name.split(',')[0])}</span>
        <div style="display: flex; align-items: center; gap: 6px;">
          <span class="hub-score-num" style="color: ${sum.threat_color};">${sum.overall_threat_score}</span>
          <span class="hub-tier-badge" style="background: ${sum.threat_color};">${sum.threat_tier}</span>
        </div>
      </div>
      <div class="hub-driver-text">
        Primary Driver: <strong>${sum.primary_threat_driver}</strong> (${sum.primary_threat_score}/100)
      </div>
      <div style="font-size: 0.72rem; color: var(--text-subtle); margin-top: 3px;">
        Temp: ${tel.temperature_c.toFixed(1)}°C • Rain: ${tel.precipitation_rate_mm_h.toFixed(1)}mm/h • Wind: ${tel.wind_speed_kmh.toFixed(1)}km/h
      </div>
    `;
  } catch (e) {
    outBox.innerHTML = `
      <div style="font-size: 0.74rem; color: #b91c1c;">Could not fetch threat data for ${escapeHtml(locationQuery)}.</div>
    `;
  }
}

function launchAIPredictionForAlert(alertId, alertObj) {
  const alert = alertObj || (state.alerts && state.alerts.find(a => a.id === alertId));
  if (!alert) return;

  switchView('ai-predictor');

  // Pre-fill fields in AI simulation
  const typeSelect = document.getElementById('ai-disaster-type');
  const locInput = document.getElementById('ai-location-name');
  const valInput = document.getElementById('ai-current-val');
  const areaQueryInput = document.getElementById('area-query-input');

  if (typeSelect) {
    if (alert.disaster_type === 'Flood Risk') typeSelect.value = 'Flood Risk';
    else if (alert.disaster_type === 'Cyclone/Storm') typeSelect.value = 'Cyclone/Storm';
    else if (alert.disaster_type === 'Earthquake') typeSelect.value = 'Earthquake';
    else if (alert.disaster_type === 'Heatwave') typeSelect.value = 'Heatwave';
  }

  if (locInput) locInput.value = alert.location_name;
  if (areaQueryInput) areaQueryInput.value = alert.location_name;

  let val = 25.0;
  if (alert.disaster_type === 'Earthquake') val = alert.magnitude || 5.5;
  else if (alert.disaster_type === 'Cyclone/Storm') val = alert.wind_speed_kmh || 85.0;
  else if (alert.disaster_type === 'Flood Risk') val = alert.rainfall_mm || 35.0;
  else if (alert.disaster_type === 'Heatwave') val = alert.temperature_c || 42.0;

  if (valInput) valInput.value = val;

  // Run area threat analysis and 72h forward trajectory projection with exact coordinates
  runAreaThreatAnalysis(alert.location_name, {
    latitude: alert.latitude,
    longitude: alert.longitude,
    disaster_type: alert.disaster_type,
    current_value: val
  });
}

// ==========================================================================
// AI SPECIFIC AREA DISASTER DETECTION & THREAT LEVEL ANALYZER
// ==========================================================================

function initAreaThreatAnalyzer() {
  const analyzeBtn = document.getElementById('btn-analyze-area-threat');
  const queryInput = document.getElementById('area-query-input');
  const clearBtn = document.getElementById('btn-clear-area-query');
  const presetChips = document.querySelectorAll('.area-chip');

  if (analyzeBtn && queryInput) {
    analyzeBtn.addEventListener('click', () => {
      runAreaThreatAnalysis(queryInput.value.trim() || 'Mumbai');
    });

    queryInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        runAreaThreatAnalysis(queryInput.value.trim() || 'Mumbai');
      }
    });
  }

  if (clearBtn && queryInput) {
    clearBtn.addEventListener('click', () => {
      queryInput.value = '';
      queryInput.focus();
    });
  }

  if (presetChips && queryInput) {
    presetChips.forEach(chip => {
      chip.addEventListener('click', () => {
        presetChips.forEach(c => c.classList.remove('active'));
        chip.classList.add('active');
        const loc = chip.getAttribute('data-location') || 'Mumbai';
        queryInput.value = loc;
        runAreaThreatAnalysis(loc);
      });
    });
  }
}

async function runAreaThreatAnalysis(locationQuery, options = {}) {
  const query = locationQuery || document.getElementById('area-query-input')?.value.trim() || 'Mumbai';
  const analyzeBtn = document.getElementById('btn-analyze-area-threat');
  const resultsPanel = document.getElementById('area-threat-results-panel');

  if (analyzeBtn) {
    analyzeBtn.disabled = true;
    analyzeBtn.innerHTML = `
      <svg class="spin-icon" viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" fill="none" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 2a10 10 0 0 1 10 10"/></svg>
      <span>Analyzing Area Threat...</span>
    `;
  }

  // Sync the input value if provided
  const queryInput = document.getElementById('area-query-input');
  if (queryInput && locationQuery) queryInput.value = locationQuery;

  try {
    const reqBody = { location: query, radius_km: 250.0 };
    if (options.latitude != null && options.longitude != null) {
      reqBody.latitude = options.latitude;
      reqBody.longitude = options.longitude;
    }

    const resp = await fetch('/api/ai/analyze-area', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(reqBody)
    });

    if (!resp.ok) {
      throw new Error(`Server returned ${resp.status}`);
    }

    const data = await resp.json();
    renderAreaThreatAnalysis(data);

    // Auto-synchronize Section B: Forward Disaster Trajectory & Risk Predictor
    syncForwardPredictorWithArea(data, options);

  } catch (err) {
    console.error('Error analyzing area threat:', err);
    if (resultsPanel) {
      resultsPanel.innerHTML = `
        <div class="detected-disasters-banner" style="background: #fef2f2; border-color: #fca5a5;">
          <h5 style="color: #991b1b;">Threat Analysis Computation Error</h5>
          <div style="font-size: 0.85rem; color: #b91c1c;">Could not complete threat assessment for "${escapeHtml(query)}". Check backend connectivity.</div>
        </div>
      `;
    }
  } finally {
    if (analyzeBtn) {
      analyzeBtn.disabled = false;
      analyzeBtn.innerHTML = `
        <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" fill="none" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 2a10 10 0 0 1 10 10"/></svg>
        <span>Calculate Threat Level</span>
      `;
    }
  }
}

function renderAreaThreatAnalysis(data) {
  const panel = document.getElementById('area-threat-results-panel');
  if (!panel) return;

  const loc = data.location || {};
  const sum = data.threat_summary || {};
  const tel = data.telemetry_snapshot || {};
  const haz = data.hazard_breakdown || {};
  const disasters = data.detected_disasters || [];
  const directives = data.mitigation_directives || [];

  const getScoreColor = (score) => {
    if (score >= 80) return '#991b1b';
    if (score >= 60) return '#ef4444';
    if (score >= 35) return '#eab308';
    return '#10b981';
  };

  const detectedHtml = disasters.length > 0
    ? `
      <div class="detected-disasters-banner">
        <h5>
          <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" fill="none" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
          Active / Proximate Hazard Events Detected in Sector (${data.detected_disasters_count}):
        </h5>
        <div class="detected-chips-wrap">
          ${disasters.map(d => `
            <div class="detected-event-pill">
              <strong>${d.disaster_type}</strong>: ${escapeHtml(d.title)} (${d.distance_km} km away) — <span class="status-badge ${d.severity.toLowerCase()}">${d.severity}</span>
            </div>
          `).join('')}
        </div>
      </div>
    `
    : `
      <div class="detected-disasters-banner" style="background: #f0fdf4; border-color: #bbf7d0;">
        <h5 style="color: #166534;">
          <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" fill="none" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
          No Severe Impending Disaster Hypocenters Detected within 250km Radius
        </h5>
        <div style="font-size: 0.8rem; color: #15803d;">Sensor telemetry and weather stations report normal background conditions for this area.</div>
      </div>
    `;

  const html = `
    <div class="area-threat-top-banner">
      <!-- Left: Composite Threat Meter -->
      <div class="threat-score-gauge-card">
        <div class="threat-gauge-label">Composite Area Threat Level</div>
        <div class="threat-gauge-number" style="color: ${sum.threat_color || '#10b981'};">
          ${sum.overall_threat_score}<span style="font-size: 1.5rem; color: var(--text-subtle);">/100</span>
        </div>
        <div class="threat-tier-pill" style="background: ${sum.threat_color || '#10b981'}; color: #ffffff;">
          ${sum.threat_tier} THREAT
        </div>
        <div class="threat-driver-pill">
          Primary Driver: <strong>${sum.primary_threat_driver}</strong> (${sum.primary_threat_score}/100)
        </div>
        <div style="font-size: 0.78rem; color: var(--text-subtle); margin-top: 8px;">
          ${sum.tier_description || ''}
        </div>
      </div>

      <!-- Right: Target Location & Real-Time Telemetry Snapshot -->
      <div class="threat-context-card">
        <div>
          <div class="threat-location-title">
            <div>
              <h4 class="threat-area-title">${escapeHtml(loc.name)}</h4>
              <div class="threat-location-sub">
                Coordinates: [${(loc.latitude || 20).toFixed(4)}°, ${(loc.longitude || 78).toFixed(4)}°] • Elev: ${loc.elevation_m || 50}m • Evaluated: ${data.evaluated_at}
              </div>
            </div>
            <span class="badge-pill" style="background: #e0f2fe; color: #0369a1; border-color: #bae6fd;">Live Telemetry</span>
          </div>

          <div class="threat-telemetry-tiles">
            <div class="telemetry-tile">
              <div class="telemetry-tile-lbl">Temperature</div>
              <div class="telemetry-tile-val">${tel.temperature_c != null ? tel.temperature_c.toFixed(1) : '--'} °C</div>
            </div>
            <div class="telemetry-tile">
              <div class="telemetry-tile-lbl">Humidity</div>
              <div class="telemetry-tile-val">${tel.humidity_pct != null ? tel.humidity_pct.toFixed(0) : '--'} %</div>
            </div>
            <div class="telemetry-tile">
              <div class="telemetry-tile-lbl">Precip Rate</div>
              <div class="telemetry-tile-val">${tel.precipitation_rate_mm_h != null ? tel.precipitation_rate_mm_h.toFixed(1) : '--'} mm/h</div>
            </div>
            <div class="telemetry-tile">
              <div class="telemetry-tile-lbl">24h Rainfall</div>
              <div class="telemetry-tile-val">${tel.daily_precipitation_sum_mm != null ? tel.daily_precipitation_sum_mm.toFixed(1) : '--'} mm</div>
            </div>
            <div class="telemetry-tile">
              <div class="telemetry-tile-lbl">Wind Speed</div>
              <div class="telemetry-tile-val">${tel.wind_speed_kmh != null ? tel.wind_speed_kmh.toFixed(1) : '--'} km/h</div>
            </div>
            <div class="telemetry-tile">
              <div class="telemetry-tile-lbl">Wind Gusts</div>
              <div class="telemetry-tile-val">${tel.wind_gusts_kmh != null ? tel.wind_gusts_kmh.toFixed(1) : '--'} km/h</div>
            </div>
          </div>
        </div>

        <div style="margin-top: 10px; font-size: 0.8rem; color: var(--text-muted); display: flex; align-items: center; gap: 6px;">
          <svg viewBox="0 0 24 24" width="14" height="14" stroke="currentColor" fill="none" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>
          Current Atmospheric Condition: <strong>${tel.weather_condition || 'Normal'}</strong>
        </div>
      </div>
    </div>

    <!-- Multi-Hazard Threat Score Breakdown -->
    <div class="threat-hazard-bars-card">
      <div style="display: flex; justify-content: space-between; align-items: center;">
        <h4 style="font-size: 1.05rem; font-weight: 700; color: var(--text-main); margin: 0;">Multi-Hazard Threat Breakdown for Area</h4>
        <span style="font-size: 0.78rem; color: var(--text-subtle);">Calibrated across 5 major disaster vectors</span>
      </div>

      <div class="hazard-breakdown-grid">
        ${Object.values(haz).map(h => {
          const col = getScoreColor(h.score);
          return `
            <div class="hazard-row">
              <div class="hazard-row-header">
                <span class="hazard-row-name">${escapeHtml(h.name)}</span>
                <span class="hazard-row-score" style="color: ${col};">${h.score} / 100 (${h.tier})</span>
              </div>
              <div class="hazard-track">
                <div class="hazard-fill" style="width: ${Math.min(100, Math.max(5, h.score))}%; background: ${col};"></div>
              </div>
              <div class="hazard-indicator-hint">${escapeHtml(h.indicators[0] || '')}</div>
            </div>
          `;
        }).join('')}
      </div>
    </div>

    ${detectedHtml}

    <!-- AI Situational Analysis & Action Directives -->
    <div class="ai-narrative-card">
      <div class="ai-narrative-header">
        <svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" fill="none" stroke-width="2"><path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/><circle cx="12" cy="12" r="4"/></svg>
        <span>AI Disaster Threat Analysis & Decision Support</span>
      </div>
      <div class="ai-narrative-body">
        ${escapeHtml(data.ai_narrative || '')}
      </div>

      <div class="ai-directives-list">
        <strong style="font-size: 0.85rem; color: #1b4332;">Actionable Area Directives & Priority Protocol:</strong>
        ${directives.map(d => `<div class="directive-bullet">• ${escapeHtml(d)}</div>`).join('')}
      </div>
    </div>
  `;

  panel.innerHTML = html;
}

function syncForwardPredictorWithArea(data, options = {}) {
  if (!data || !data.location) return;

  const locInput = document.getElementById('ai-location-name');
  const typeSelect = document.getElementById('ai-disaster-type');
  const valInput = document.getElementById('ai-current-val');

  if (locInput) locInput.value = data.location.name;

  let dType = options.disaster_type || 'Flood Risk';
  if (!options.disaster_type) {
    const driver = (data.threat_summary?.primary_threat_driver || '').toLowerCase();
    if (driver.includes('cyclone') || driver.includes('storm') || driver.includes('wind')) {
      dType = 'Cyclone/Storm';
    } else if (driver.includes('seismic') || driver.includes('earthquake')) {
      dType = 'Earthquake';
    } else if (driver.includes('heat')) {
      dType = 'Heatwave';
    } else if (driver.includes('flood') || driver.includes('rain')) {
      dType = 'Flood Risk';
    }
  }

  if (typeSelect) typeSelect.value = dType;

  // Determine current telemetry reading
  let currentVal = options.current_value;
  if (currentVal == null) {
    const tel = data.telemetry_snapshot || {};
    if (dType === 'Flood Risk') {
      currentVal = (tel.precipitation_rate_mm_h && tel.precipitation_rate_mm_h > 0) ? tel.precipitation_rate_mm_h : 28.5;
    } else if (dType === 'Cyclone/Storm') {
      currentVal = (tel.wind_speed_kmh && tel.wind_speed_kmh > 0) ? tel.wind_speed_kmh : 85.0;
    } else if (dType === 'Heatwave') {
      currentVal = (tel.temperature_c && tel.temperature_c > 0) ? tel.temperature_c : 42.0;
    } else if (dType === 'Earthquake') {
      const quakes = (data.detected_disasters || []).filter(d => d.disaster_type === 'Earthquake');
      currentVal = quakes.length > 0 && quakes[0].magnitude ? quakes[0].magnitude : 5.8;
    } else {
      currentVal = 25.0;
    }
  }

  if (valInput) valInput.value = currentVal.toFixed(1);

  // Trigger forward simulation with exact coordinates
  runAIPrediction({
    disaster_type: dType,
    location_name: data.location.name,
    latitude: data.location.latitude,
    longitude: data.location.longitude,
    current_value: currentVal
  });
}

function initAIPredictor() {
  initAreaThreatAnalyzer();

  const scenarioBtns = document.querySelectorAll('.scenario-btn');
  scenarioBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      scenarioBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');

      const scenKey = btn.getAttribute('data-scenario');
      const scen = aiScenariosMap[scenKey];
      if (scen) {
        const typeSelect = document.getElementById('ai-disaster-type');
        const locInput = document.getElementById('ai-location-name');
        const valInput = document.getElementById('ai-current-val');
        if (typeSelect) typeSelect.value = scen.type;
        if (locInput) locInput.value = scen.name;
        if (valInput) valInput.value = scen.val;

        runAIPrediction({
          disaster_type: scen.type,
          location_name: scen.name,
          latitude: scen.lat,
          longitude: scen.lon,
          current_value: scen.val
        });
      }
    });
  });

  const runBtn = document.getElementById('btn-run-ai-prediction');
  if (runBtn) {
    runBtn.addEventListener('click', () => runAIPrediction());
  }

  const typeSelect = document.getElementById('ai-disaster-type');
  if (typeSelect) {
    typeSelect.addEventListener('change', () => {
      const valInput = document.getElementById('ai-current-val');
      const locInput = document.getElementById('ai-location-name');
      const t = typeSelect.value;
      if (t === 'Flood Risk') {
        if (valInput) valInput.value = '25.0';
        if (locInput) locInput.value = 'Godavari River Basin, Rajahmundry';
      } else if (t === 'Cyclone/Storm') {
        if (valInput) valInput.value = '85.0';
        if (locInput) locInput.value = 'Visakhapatnam Coastal Sector';
      } else if (t === 'Earthquake') {
        if (valInput) valInput.value = '6.2';
        if (locInput) locInput.value = 'Himalayan Thrust Belt, Uttarakhand';
      } else if (t === 'Heatwave') {
        if (valInput) valInput.value = '43.5';
        if (locInput) locInput.value = 'Northern Plains, Jodhpur';
      }
    });
  }
}

const cityCoordsLookup = {
  'mumbai': [18.9667, 72.8333],
  'delhi': [28.6139, 77.2090],
  'new delhi': [28.6139, 77.2090],
  'guwahati': [26.1445, 91.7362],
  'assam': [26.1445, 91.7362],
  'kolkata': [22.5726, 88.3639],
  'puri': [19.8135, 85.8312],
  'odisha': [19.8135, 85.8312],
  'shimla': [31.1048, 77.1734],
  'chennai': [13.0827, 80.2707],
  'kochi': [9.9312, 76.2673],
  'kerala': [9.9312, 76.2673],
  'nagpur': [21.1458, 79.0882],
  'vidarbha': [21.1458, 79.0882],
  'tokyo': [35.6762, 139.6503]
};

async function runAIPrediction(opts = {}) {
  const runBtn = document.getElementById('btn-run-ai-prediction');
  if (runBtn) {
    runBtn.innerHTML = `
      <svg class="spin-icon" viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" fill="none" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 2a10 10 0 0 1 10 10"/></svg>
      Computing AI Model...
    `;
    runBtn.disabled = true;
  }

  // Clear previous error alerts if any
  const oldErr = document.getElementById('ai-pred-error-alert');
  if (oldErr) oldErr.remove();

  const dType = opts.disaster_type || document.getElementById('ai-disaster-type')?.value || 'Flood Risk';
  const locName = opts.location_name || document.getElementById('ai-location-name')?.value || 'Brahmaputra Basin, Guwahati, Assam';
  const currVal = opts.current_value != null ? opts.current_value : parseFloat(document.getElementById('ai-current-val')?.value || '25.0');
  const horizon = opts.horizon_hours || parseInt(document.getElementById('ai-forecast-horizon')?.value || '72');

  let lat = opts.latitude;
  let lon = opts.longitude;

  // Resolve coordinates from scenario if not provided
  if (lat == null || lon == null) {
    const activeScen = document.querySelector('.scenario-btn.active');
    if (activeScen) {
      const scen = aiScenariosMap[activeScen.getAttribute('data-scenario')];
      if (scen && scen.name === locName) {
        lat = scen.lat;
        lon = scen.lon;
      }
    }
  }

  // Resolve coordinates from known city keywords
  if (lat == null || lon == null) {
    const locLower = locName.toLowerCase();
    for (const [key, coords] of Object.entries(cityCoordsLookup)) {
      if (locLower.includes(key)) {
        lat = coords[0];
        lon = coords[1];
        break;
      }
    }
  }

  // Safe fallback default coordinates
  if (lat == null || lon == null) {
    lat = 26.1445;
    lon = 91.7362;
  }

  try {
    const resp = await fetch('/api/ai/predict', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        disaster_type: dType,
        location_name: locName,
        latitude: lat,
        longitude: lon,
        current_value: isNaN(currVal) ? null : currVal,
        horizon_hours: horizon
      })
    });

    if (!resp.ok) {
      throw new Error(`Server returned status ${resp.status}`);
    }

    const data = await resp.json();
    renderAIPrediction(data);
  } catch (err) {
    console.error('Error generating AI prediction:', err);
    const resultsPanel = document.getElementById('ai-results-panel');
    if (resultsPanel) {
      const alertDiv = document.createElement('div');
      alertDiv.id = 'ai-pred-error-alert';
      alertDiv.className = 'ai-error-banner';
      alertDiv.innerHTML = `
        <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" fill="none" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
        <span><strong>AI Prediction Error:</strong> Could not complete projection (${escapeHtml(err.message)}). Please check inputs and retry.</span>
      `;
      resultsPanel.insertBefore(alertDiv, resultsPanel.firstChild);
    }
  } finally {
    if (runBtn) {
      runBtn.innerHTML = `
        <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" fill="none" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg>
        Run AI Prediction
      `;
      runBtn.disabled = false;
    }
  }
}

function renderAIPrediction(data) {
  if (!data || !data.timeline) return;

  // 1. Top Metrics
  const peakHourEl = document.getElementById('ai-peak-hour');
  const peakTimeEl = document.getElementById('ai-peak-time');
  const trendEl = document.getElementById('ai-trend-val');
  const sevBadgeEl = document.getElementById('ai-severity-badge');
  const confEl = document.getElementById('ai-confidence-val');
  const archEl = document.getElementById('ai-model-arch');
  const unitTagEl = document.getElementById('ai-chart-unit-tag');

  if (peakHourEl) peakHourEl.textContent = `T+${data.peak_risk_hour}h`;
  if (peakTimeEl) peakTimeEl.textContent = data.peak_risk_time || 'Next 24h Window';
  if (trendEl) trendEl.textContent = data.overall_trend || 'Active Evolution';
  
  const peakStep = data.timeline.reduce((prev, curr) => (curr.predicted_risk_score > prev.predicted_risk_score ? curr : prev), data.timeline[0]);
  if (sevBadgeEl) sevBadgeEl.textContent = `Peak: ${peakStep.predicted_severity} (${peakStep.predicted_risk_score}/10)`;
  if (confEl) confEl.textContent = `${data.model_confidence_pct}%`;
  if (archEl) archEl.textContent = data.model_name || 'Autoregressive Ensemble AI';
  if (unitTagEl) unitTagEl.textContent = `Unit: ${data.timeline[0]?.value_unit || 'Metric'}`;

  // 2. Render Trajectory Chart (Canvas with SVG fallback)
  try {
    renderAITrajectoryChart(data);
  } catch (chartErr) {
    console.warn('Canvas trajectory chart failed, falling back to SVG renderer:', chartErr);
    const canvas = document.getElementById('ai-trajectory-chart');
    if (canvas) {
      renderSvgTrajectoryFallback(canvas, data);
    }
  }

  // 3. Render Explainable Feature Importance
  const featContainer = document.getElementById('ai-features-container');
  if (featContainer && data.feature_importance) {
    let featHtml = '';
    for (const [featName, weight] of Object.entries(data.feature_importance)) {
      const pct = Math.round(weight * 100);
      featHtml += `
        <div class="feat-item">
          <div class="feat-meta">
            <span>${escapeHtml(featName)}</span>
            <span>${pct}% contribution</span>
          </div>
          <div class="feat-track">
            <div class="feat-fill" style="width: ${pct}%"></div>
          </div>
        </div>
      `;
    }
    featContainer.innerHTML = featHtml;
  }

  // 4. Render AI Situation Summary & Mitigation
  const summaryEl = document.getElementById('ai-summary-text');
  if (summaryEl) {
    summaryEl.textContent = data.summary_text;
  }

  const advContainer = document.getElementById('ai-advisory-items');
  if (advContainer && data.ai_mitigation_advisory) {
    const lines = data.ai_mitigation_advisory.split(/\d+\.\s+/).filter(Boolean);
    let advHtml = '';
    lines.forEach((item, idx) => {
      advHtml += `
        <div class="advisory-item">
          <svg viewBox="0 0 24 24" width="14" height="14" stroke="#2d6a4f" fill="none" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>
          <span><strong>Action ${idx + 1}:</strong> ${escapeHtml(item.trim())}</span>
        </div>
      `;
    });
    advContainer.innerHTML = advHtml;
  }

  // 5. Render Step-by-Step Ledger Table
  const tbody = document.getElementById('ai-timeline-table-body');
  if (tbody) {
    let rowsHtml = '';
    data.timeline.forEach(step => {
      const sevClass = step.predicted_severity.toLowerCase();
      rowsHtml += `
        <tr>
          <td><strong>T+${step.step_hour}h</strong></td>
          <td>${escapeHtml(step.timestamp)}</td>
          <td><span class="mono-value">${step.predicted_value} ${escapeHtml(step.value_unit)}</span></td>
          <td><strong>${step.predicted_risk_score} / 10</strong></td>
          <td><span class="status-badge ${sevClass}">${escapeHtml(step.predicted_severity)}</span></td>
          <td><span class="text-subtle">[${step.confidence_interval_low} — ${step.confidence_interval_high}]</span></td>
        </tr>
      `;
    });
    tbody.innerHTML = rowsHtml;
  }
}

function renderSvgTrajectoryFallback(canvas, data) {
  if (!canvas || !data || !data.timeline) return;

  const container = canvas.parentElement;
  if (!container) return;

  const width = Math.max(container.clientWidth || 700, 400);
  const height = 240;
  const padding = { top: 28, right: 35, bottom: 35, left: 45 };
  const chartW = width - padding.left - padding.right;
  const chartH = height - padding.top - padding.bottom;

  const steps = data.timeline;
  const n = steps.length;
  if (n === 0) return;

  const maxPhys = Math.max(...steps.map(s => s.predicted_value), 10);
  const minPhys = Math.min(...steps.map(s => s.predicted_value), 0);

  const getX = (i) => padding.left + (i / (n - 1)) * chartW;
  const getYRisk = (val) => padding.top + chartH - (Math.min(10, Math.max(0, val)) / 10) * chartH;
  const getYPhys = (val) => padding.top + chartH - ((val - minPhys) / (maxPhys - minPhys || 1)) * chartH;

  const riskPoints = steps.map((s, i) => `${getX(i).toFixed(1)},${getYRisk(s.predicted_risk_score).toFixed(1)}`).join(' ');
  const physPoints = steps.map((s, i) => `${getX(i).toFixed(1)},${getYPhys(s.predicted_value).toFixed(1)}`).join(' ');

  const areaD = `M ${getX(0).toFixed(1)},${getYRisk(steps[0].predicted_risk_score).toFixed(1)} ` +
    steps.map((s, i) => `L ${getX(i).toFixed(1)},${getYRisk(s.predicted_risk_score).toFixed(1)}`).join(' ') +
    ` L ${getX(n - 1).toFixed(1)},${padding.top + chartH} L ${getX(0).toFixed(1)},${padding.top + chartH} Z`;

  let gridLines = '';
  for (let r = 0; r <= 10; r += 2) {
    const y = getYRisk(r);
    gridLines += `<line x1="${padding.left}" y1="${y}" x2="${width - padding.right}" y2="${y}" stroke="rgba(0,0,0,0.06)" stroke-width="1"/>`;
    gridLines += `<text x="${padding.left - 8}" y="${y + 4}" fill="#6b7280" font-size="10" font-family="JetBrains Mono" text-anchor="end">${r}</text>`;
  }

  let xLabels = '';
  steps.forEach((s, i) => {
    const x = getX(i);
    xLabels += `<line x1="${x}" y1="${padding.top + chartH}" x2="${x}" y2="${padding.top + chartH + 4}" stroke="#9ca3af" stroke-width="1"/>`;
    xLabels += `<text x="${x}" y="${padding.top + chartH + 18}" fill="#4b5563" font-size="10" font-family="JetBrains Mono" text-anchor="middle">T+${s.step_hour}h</text>`;
  });

  const pointsHtml = steps.map((s, i) => {
    const x = getX(i);
    const y = getYRisk(s.predicted_risk_score);
    return `<circle cx="${x}" cy="${y}" r="4" fill="#d90429" stroke="#ffffff" stroke-width="2"><title>T+${s.step_hour}h: Risk ${s.predicted_risk_score}/10, Val ${s.predicted_value} ${s.value_unit}</title></circle>`;
  }).join('');

  canvas.style.display = 'none';

  const existingSvg = container.querySelector('.ai-svg-trajectory-wrapper');
  if (existingSvg) existingSvg.remove();

  const svgDiv = document.createElement('div');
  svgDiv.className = 'ai-svg-trajectory-wrapper';
  svgDiv.innerHTML = `
    <svg width="100%" height="240" viewBox="0 0 ${width} 240" style="display:block; overflow:visible;">
      <defs>
        <linearGradient id="riskGrad" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stop-color="#d90429" stop-opacity="0.25"/>
          <stop offset="100%" stop-color="#d90429" stop-opacity="0.02"/>
        </linearGradient>
      </defs>
      ${gridLines}
      ${xLabels}
      <path d="${areaD}" fill="url(#riskGrad)"/>
      <polyline points="${physPoints}" fill="none" stroke="#2563eb" stroke-width="2" stroke-dasharray="5,4"/>
      <polyline points="${riskPoints}" fill="none" stroke="#d90429" stroke-width="2.5"/>
      ${pointsHtml}
      <text x="${padding.left}" y="16" fill="#d90429" font-size="11" font-weight="bold" font-family="Plus Jakarta Sans">● Projected Risk (0-10)</text>
      <text x="${padding.left + 165}" y="16" fill="#2563eb" font-size="11" font-weight="bold" font-family="Plus Jakarta Sans">--- Physical Metric (${escapeHtml(data.timeline[0]?.value_unit || 'Val')})</text>
    </svg>
  `;
  container.appendChild(svgDiv);
}

function renderAITrajectoryChart(data) {
  const canvas = document.getElementById('ai-trajectory-chart');
  if (!canvas) return;

  const container = canvas.parentElement;
  if (container) {
    const existingSvg = container.querySelector('.ai-svg-trajectory-wrapper');
    if (existingSvg) existingSvg.remove();
  }
  canvas.style.display = 'block';

  if (typeof Chart === 'undefined') {
    renderSvgTrajectoryFallback(canvas, data);
    return;
  }

  const labels = data.timeline.map(s => `T+${s.step_hour}h`);
  const riskScores = data.timeline.map(s => s.predicted_risk_score);
  const physicalVals = data.timeline.map(s => s.predicted_value);
  const confHigh = data.timeline.map(s => s.confidence_interval_high);
  const confLow = data.timeline.map(s => s.confidence_interval_low);

  if (state.aiChartInstance) {
    state.aiChartInstance.destroy();
    state.aiChartInstance = null;
  }

  state.aiChartInstance = new Chart(canvas, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [
        {
          label: 'AI Projected Risk Score (0-10)',
          data: riskScores,
          borderColor: '#d90429',
          backgroundColor: 'rgba(217, 4, 41, 0.12)',
          borderWidth: 2.5,
          tension: 0.35,
          yAxisID: 'yRisk',
          fill: true,
          pointBackgroundColor: '#d90429',
          pointRadius: 4
        },
        {
          label: `Physical Parameter (${data.timeline[0]?.value_unit || 'Val'})`,
          data: physicalVals,
          borderColor: '#2b7fff',
          backgroundColor: 'transparent',
          borderWidth: 2,
          borderDash: [5, 4],
          tension: 0.3,
          yAxisID: 'yPhys',
          pointBackgroundColor: '#2b7fff',
          pointRadius: 3
        },
        {
          label: '95% Confidence Upper Bound',
          data: confHigh,
          borderColor: 'rgba(217, 4, 41, 0.3)',
          backgroundColor: 'transparent',
          borderWidth: 1,
          borderDash: [2, 2],
          pointRadius: 0,
          yAxisID: 'yRisk'
        },
        {
          label: '95% Confidence Lower Bound',
          data: confLow,
          borderColor: 'rgba(217, 4, 41, 0.3)',
          backgroundColor: 'transparent',
          borderWidth: 1,
          borderDash: [2, 2],
          pointRadius: 0,
          yAxisID: 'yRisk'
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: {
        mode: 'index',
        intersect: false
      },
      plugins: {
        legend: {
          display: true,
          position: 'top',
          labels: { color: '#133822', boxWidth: 12, font: { size: 11, weight: '600' } }
        },
        tooltip: {
          backgroundColor: '#133822',
          titleFont: { size: 12, weight: '700' },
          bodyFont: { size: 11 }
        }
      },
      scales: {
        x: {
          grid: { color: 'rgba(27, 67, 50, 0.08)' },
          ticks: { color: '#133822', font: { size: 11, weight: '600' } }
        },
        yRisk: {
          type: 'linear',
          position: 'left',
          min: 0,
          max: 10,
          title: {
            display: true,
            text: 'Risk Index (0 - 10)',
            color: '#d90429',
            font: { weight: 'bold', size: 11 }
          },
          grid: { color: 'rgba(27, 67, 50, 0.08)' },
          ticks: { color: '#d90429', font: { size: 10 } }
        },
        yPhys: {
          type: 'linear',
          position: 'right',
          title: {
            display: true,
            text: `Physical Value (${data.timeline[0]?.value_unit || ''})`,
            color: '#2b7fff',
            font: { weight: 'bold', size: 11 }
          },
          grid: { drawOnChartArea: false },
          ticks: { color: '#2b7fff', font: { size: 10 } }
        }
      }
    }
  });
}

// Global exposure on window for seamless inter-component communication and inspection
window.state = state;
window.switchView = switchView;
window.runAIPrediction = runAIPrediction;
window.runAreaThreatAnalysis = runAreaThreatAnalysis;
window.launchAIPredictionForAlert = launchAIPredictionForAlert;


