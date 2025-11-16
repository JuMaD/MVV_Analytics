/**
 * Munich Transit Reachability Map - Frontend Application
 */

// API configuration
const API_BASE = '/api';

// Map instance
let map = null;

// Layers
let allStopsLayer = null;
let reachableStopsLayer = null;
let originMarker = null;

// Data
let allStops = [];
let selectedStop = null;
let timelineData = null;

// Animation state
const animationState = {
    timeline: [],
    currentIndex: 0,
    isPlaying: false,
    intervalId: null,
    frameDuration: 1000  // 1 second per frame
};

// Color scheme for travel time bands
const COLOR_SCHEME = {
    '0-15': '#2e7d32',    // Dark green
    '15-30': '#66bb6a',   // Light green
    '30-45': '#ffeb3b',   // Yellow
    '45-60': '#ff9800',   // Orange
    'origin': '#2196f3'   // Blue
};

/**
 * Initialize the application
 */
async function init() {
    // Initialize map
    initMap();

    // Load metadata
    await loadMetadata();

    // Load all stops
    await loadStops();

    // Setup event listeners
    setupEventListeners();

    console.log('Application initialized');
}

/**
 * Initialize Leaflet map
 */
function initMap() {
    // Create map centered on Munich
    map = L.map('map').setView([48.1351, 11.5820], 11);

    // Add tile layer
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors',
        maxZoom: 19
    }).addTo(map);

    // Create layer groups
    allStopsLayer = L.layerGroup().addTo(map);
    reachableStopsLayer = L.layerGroup().addTo(map);

    // Map click handler for selecting stops
    map.on('click', onMapClick);

    console.log('Map initialized');
}

/**
 * Load metadata from API
 */
async function loadMetadata() {
    try {
        const response = await fetch(`${API_BASE}/metadata`);
        const metadata = await response.json();

        // Update footer
        document.getElementById('data-source').textContent = metadata.source;
        document.getElementById('download-date').textContent = metadata.download_date || '-';
        document.getElementById('feed-version').textContent = metadata.feed_version || '-';

    } catch (error) {
        console.error('Error loading metadata:', error);
    }
}

/**
 * Load all transit stops
 */
async function loadStops() {
    try {
        const dayType = document.getElementById('day-type').value;
        const response = await fetch(`${API_BASE}/stops?day_type=${dayType}`);
        allStops = await response.json();

        // Display stops on map as small gray markers
        displayAllStops();

        console.log(`Loaded ${allStops.length} stops`);

    } catch (error) {
        console.error('Error loading stops:', error);
        showError('Failed to load transit stops');
    }
}

/**
 * Display all stops on map as small gray markers
 */
function displayAllStops() {
    allStopsLayer.clearLayers();

    allStops.forEach(stop => {
        const marker = L.circleMarker([stop.lat, stop.lon], {
            radius: 3,
            fillColor: '#999',
            color: '#666',
            weight: 1,
            fillOpacity: 0.6
        });

        marker.bindTooltip(stop.stop_name, {
            permanent: false,
            direction: 'top'
        });

        marker.on('click', () => selectStop(stop));

        marker.addTo(allStopsLayer);
    });
}

/**
 * Setup event listeners
 */
function setupEventListeners() {
    // Max time slider
    const maxTimeSlider = document.getElementById('max-time');
    const maxTimeValue = document.getElementById('max-time-value');

    maxTimeSlider.addEventListener('input', (e) => {
        maxTimeValue.textContent = `${e.target.value} minutes`;
    });

    // Stop search
    const stopSearch = document.getElementById('stop-search');
    stopSearch.addEventListener('input', onStopSearchInput);
    stopSearch.addEventListener('focus', onStopSearchInput);

    // Click outside to close suggestions
    document.addEventListener('click', (e) => {
        if (!document.getElementById('stop-search-container').contains(e.target)) {
            hideSuggestions();
        }
    });

    // Calculate button
    document.getElementById('calculate-btn').addEventListener('click', calculateReachability);

    // Animation controls
    document.getElementById('play-btn').addEventListener('click', playAnimation);
    document.getElementById('pause-btn').addEventListener('click', pauseAnimation);
    document.getElementById('stop-btn').addEventListener('click', stopAnimation);

    // Day type change - reload stops
    document.getElementById('day-type').addEventListener('change', loadStops);
}

/**
 * Handle stop search input
 */
function onStopSearchInput(e) {
    const query = e.target.value.toLowerCase().trim();

    if (query.length < 2) {
        hideSuggestions();
        return;
    }

    // Filter stops
    const matches = allStops.filter(stop =>
        stop.stop_name.toLowerCase().includes(query)
    ).slice(0, 10);  // Limit to 10 results

    displaySuggestions(matches);
}

/**
 * Display search suggestions
 */
function displaySuggestions(stops) {
    const container = document.getElementById('stop-suggestions');
    container.innerHTML = '';

    if (stops.length === 0) {
        hideSuggestions();
        return;
    }

    stops.forEach(stop => {
        const item = document.createElement('div');
        item.className = 'suggestion-item';
        item.textContent = stop.stop_name;
        item.addEventListener('click', () => {
            selectStop(stop);
            hideSuggestions();
        });
        container.appendChild(item);
    });

    container.classList.add('visible');
}

/**
 * Hide search suggestions
 */
function hideSuggestions() {
    document.getElementById('stop-suggestions').classList.remove('visible');
}

/**
 * Handle map click
 */
function onMapClick(e) {
    // Find nearest stop to click location
    const clickLat = e.latlng.lat;
    const clickLon = e.latlng.lng;

    let nearestStop = null;
    let minDistance = Infinity;

    allStops.forEach(stop => {
        const distance = Math.sqrt(
            Math.pow(stop.lat - clickLat, 2) +
            Math.pow(stop.lon - clickLon, 2)
        );

        if (distance < minDistance) {
            minDistance = distance;
            nearestStop = stop;
        }
    });

    // Only select if reasonably close (within ~500m at zoom 11)
    if (nearestStop && minDistance < 0.005) {
        selectStop(nearestStop);
    }
}

/**
 * Select a stop as origin
 */
function selectStop(stop) {
    selectedStop = stop;

    // Update UI
    document.getElementById('stop-search').value = stop.stop_name;
    document.getElementById('selected-stop').textContent = stop.stop_name;

    // Update origin marker
    if (originMarker) {
        map.removeLayer(originMarker);
    }

    originMarker = L.circleMarker([stop.lat, stop.lon], {
        radius: 8,
        fillColor: COLOR_SCHEME.origin,
        color: '#fff',
        weight: 3,
        fillOpacity: 1
    });

    originMarker.bindTooltip(`Origin: ${stop.stop_name}`, {
        permanent: true,
        direction: 'top'
    });

    originMarker.addTo(map);

    // Center map on stop
    map.setView([stop.lat, stop.lon], 12);

    console.log('Selected stop:', stop.stop_name);
}

/**
 * Calculate reachability
 */
async function calculateReachability() {
    if (!selectedStop) {
        showError('Please select a starting stop');
        return;
    }

    // Get parameters
    const maxTime = parseInt(document.getElementById('max-time').value);
    const departureTime = document.getElementById('departure-time').value;
    const dayType = document.getElementById('day-type').value;

    // Show loading
    showLoading(true);
    hideError();
    hideAnimationControls();

    try {
        // Call timeline API
        const response = await fetch(`${API_BASE}/reachability-timeline`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                origin_stop_id: selectedStop.stop_id,
                max_time_minutes: maxTime,
                time_step_minutes: 5,
                departure_time: departureTime,
                day_type: dayType
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Calculation failed');
        }

        const data = await response.json();
        timelineData = data;

        // Setup animation
        setupAnimation(data.timeline);

        // Show first frame
        displayTimelineFrame(0);

        // Show animation controls
        showAnimationControls();

        console.log('Reachability calculated:', data.timeline.length, 'frames');

    } catch (error) {
        console.error('Error calculating reachability:', error);
        showError(error.message || 'Failed to calculate reachability');
    } finally {
        showLoading(false);
    }
}

/**
 * Setup animation with timeline data
 */
function setupAnimation(timeline) {
    animationState.timeline = timeline;
    animationState.currentIndex = 0;
    animationState.isPlaying = false;

    if (animationState.intervalId) {
        clearInterval(animationState.intervalId);
        animationState.intervalId = null;
    }
}

/**
 * Display a specific timeline frame
 */
function displayTimelineFrame(index) {
    if (!animationState.timeline || index >= animationState.timeline.length) {
        return;
    }

    const frame = animationState.timeline[index];

    // Clear previous reachable stops
    reachableStopsLayer.clearLayers();

    // Display reachable stops
    frame.reachable_stops.forEach(stop => {
        const color = getColorForTravelTime(stop.travel_time_minutes);

        const marker = L.circleMarker([stop.lat, stop.lon], {
            radius: 5,
            fillColor: color,
            color: '#333',
            weight: 2,
            fillOpacity: 0.8
        });

        marker.bindTooltip(
            `<strong>${stop.stop_name}</strong><br>` +
            `Travel time: ${stop.travel_time_minutes.toFixed(1)} min<br>` +
            `Transfers: ${stop.num_transfers}`,
            {
                permanent: false,
                direction: 'top'
            }
        );

        marker.addTo(reachableStopsLayer);
    });

    // Update time display
    document.getElementById('time-display').textContent = `${frame.elapsed_minutes} minutes`;

    // Update progress bar
    const progress = ((index + 1) / animationState.timeline.length) * 100;
    document.getElementById('progress-bar').style.width = `${progress}%`;

    animationState.currentIndex = index;
}

/**
 * Get color for travel time
 */
function getColorForTravelTime(minutes) {
    if (minutes <= 15) return COLOR_SCHEME['0-15'];
    if (minutes <= 30) return COLOR_SCHEME['15-30'];
    if (minutes <= 45) return COLOR_SCHEME['30-45'];
    return COLOR_SCHEME['45-60'];
}

/**
 * Play animation
 */
function playAnimation() {
    if (animationState.isPlaying) return;

    animationState.isPlaying = true;

    // Start from current index
    animationState.intervalId = setInterval(() => {
        if (animationState.currentIndex >= animationState.timeline.length - 1) {
            // End of animation
            pauseAnimation();
            return;
        }

        animationState.currentIndex++;
        displayTimelineFrame(animationState.currentIndex);

    }, animationState.frameDuration);

    console.log('Animation started');
}

/**
 * Pause animation
 */
function pauseAnimation() {
    if (!animationState.isPlaying) return;

    animationState.isPlaying = false;

    if (animationState.intervalId) {
        clearInterval(animationState.intervalId);
        animationState.intervalId = null;
    }

    console.log('Animation paused');
}

/**
 * Stop animation (reset to beginning)
 */
function stopAnimation() {
    pauseAnimation();

    animationState.currentIndex = 0;
    displayTimelineFrame(0);

    console.log('Animation stopped');
}

/**
 * Show/hide loading indicator
 */
function showLoading(show) {
    const loading = document.getElementById('loading');
    const calculateBtn = document.getElementById('calculate-btn');

    if (show) {
        loading.classList.add('visible');
        calculateBtn.disabled = true;
    } else {
        loading.classList.remove('visible');
        calculateBtn.disabled = false;
    }
}

/**
 * Show animation controls
 */
function showAnimationControls() {
    document.getElementById('animation-controls').classList.add('visible');
}

/**
 * Hide animation controls
 */
function hideAnimationControls() {
    document.getElementById('animation-controls').classList.remove('visible');
}

/**
 * Show error message
 */
function showError(message) {
    const errorDiv = document.getElementById('error');
    errorDiv.textContent = message;
    errorDiv.classList.add('visible');
}

/**
 * Hide error message
 */
function hideError() {
    document.getElementById('error').classList.remove('visible');
}

// Initialize app when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}
