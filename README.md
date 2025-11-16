# Munich Transit Reachability Map

Interactive web application that visualizes how far you can travel on Munich's public transit system (MVV) within a specified time limit, with animated visualization of expanding reachability over time.

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![Python](https://img.shields.io/badge/python-3.11-blue)
![License](https://img.shields.io/badge/license-MIT-green)

## Features

- **Interactive Map**: Click any transit stop in Munich to set as starting point
- **Time-Based Reachability**: Calculate how far you can travel in 15, 30, 45, or 60 minutes
- **Animated Visualization**: Watch reachability expand over time with play/pause/stop controls
- **Time-of-Day Awareness**: Different results for different departure times
- **Day Type Support**: Separate calculations for weekdays, Saturdays, and Sundays
- **Automatic Updates**: Daily checks for new GTFS data from MVV
- **Legal Attribution**: Proper display of MVV data source and licensing

## Screenshots

### Main Interface
![Munich Transit Reachability Map - Main Interface](docs/screenshots/main-interface.png)

*Interactive map showing Munich transit stops with controls panel on the left*

### Reachability Visualization
![Reachability Visualization](docs/screenshots/reachability-visualization.png)

*Color-coded stops showing 30-minute reachability from Marienplatz (0-15min: green, 15-30min: light green, origin: blue)*

### Animation Controls
![Animation Controls](docs/screenshots/animation-controls.png)

*Timeline animation with play/pause/stop controls and progress bar*

### Key Features
- Searchable stop selector with autocomplete
- Interactive Leaflet map with all ~4,000 Munich transit stops
- Color-coded visualization (green → yellow → orange by travel time)
- Animation controls with progress bar and time display
- Responsive design suitable for desktop and tablet

> **Note**: To add screenshots, run the application and capture images, then save them to `docs/screenshots/` directory.

## Architecture

### Backend
- **Framework**: FastAPI (Python)
- **Transit Network**: NetworkX directed graphs with time-dependent edges
- **GTFS Processing**: pandas, gtfs-kit
- **Algorithm**: Time-dependent Dijkstra's algorithm for reachability

### Frontend
- **Map**: Leaflet.js with OpenStreetMap tiles
- **UI**: Vanilla JavaScript, responsive CSS
- **Animation**: Timeline-based frame interpolation

### Deployment
- **Container**: Docker
- **Platform**: Google Cloud Run
- **Storage**: Google Cloud Storage (for GTFS data and graphs)
- **Scheduling**: Cloud Scheduler (daily update checks)

## Project Structure

```
MVV_Analytics/
├── backend/
│   ├── api/
│   │   ├── app.py          # FastAPI application
│   │   └── models.py       # Pydantic models
│   ├── data/
│   │   └── gtfs_downloader.py  # GTFS download and validation
│   ├── graph/
│   │   ├── graph_builder.py    # Build transit network graphs
│   │   └── reachability.py     # Reachability calculations
│   └── config.py           # Configuration settings
├── frontend/
│   └── index.html          # Main application page
├── static/
│   ├── app.js              # Frontend JavaScript
│   └── data/               # GTFS data and graphs
├── scripts/
│   ├── init_data.py        # Initialize GTFS data
│   └── update_scheduler.py # Update checker for Cloud Scheduler
├── .gcp/
│   ├── cloudbuild.yaml     # Cloud Build configuration
│   └── setup-gcp.sh        # GCP setup script
├── Dockerfile
├── requirements.txt
└── README.md
```

## Installation & Setup

### Local Development

#### 1. Prerequisites

- Python 3.11+
- pip
- ~2GB disk space for GTFS data and graphs

#### 2. Clone Repository

```bash
git clone https://github.com/JuMaD/MVV_Analytics.git
cd MVV_Analytics
```

#### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

#### 4. Initialize Data

Download GTFS data and build transit graphs (~5-10 minutes):

```bash
python scripts/init_data.py
```

This will:
- Download GTFS data from MVV (~50MB)
- Validate data structure
- Build time-dependent transit graphs for weekday/saturday/sunday
- Save graphs as pickle files

#### 5. Run Application

```bash
uvicorn backend.api.app:app --reload
```

Open browser to: http://localhost:8000

### Docker

#### Build and Run

```bash
# Build image
docker build -t munich-transit-map .

# Run container
docker run -p 8000:8000 -v $(pwd)/static/data:/app/static/data munich-transit-map
```

Note: You still need to initialize data first (run `scripts/init_data.py` before building the image or mount a volume with existing data).

## Google Cloud Deployment

### 🚀 Quick Start (One Command)

```bash
./scripts/setup.sh
```

That's it! The script will:
1. Check prerequisites (gcloud, terraform, docker)
2. Authenticate with GCP
3. Create all infrastructure using Terraform
4. Build and deploy the Docker image
5. Initialize GTFS data
6. Provide you with the live application URL

**Total time**: ~10-15 minutes

### Prerequisites

- Google Cloud Project with billing enabled
- [gcloud CLI](https://cloud.google.com/sdk/docs/install) installed
- [Terraform](https://www.terraform.io/downloads) installed (v1.0+)
- [Docker](https://docs.docker.com/get-docker/) installed

### What Gets Created

The Terraform configuration automatically creates:

- ✅ **Cloud Run service** - Auto-scaling web application
- ✅ **Cloud Storage buckets** - GTFS data and graph storage
- ✅ **Cloud Scheduler job** - Daily GTFS updates at 6 AM CET
- ✅ **Artifact Registry** - Docker image repository
- ✅ **Service Accounts** - With appropriate IAM permissions
- ✅ **Public HTTPS endpoint** - Your application URL

**See [DEPLOYMENT.md](docs/DEPLOYMENT.md) for detailed deployment guide, manual setup, troubleshooting, and more.**

### Updating the Application

Deploy code changes:
```bash
./scripts/deploy.sh
```

Update infrastructure:
```bash
cd terraform
terraform apply
```

### Teardown

Remove all GCP resources:
```bash
./scripts/teardown.sh  # WARNING: Deletes everything!
```

## API Documentation

### Endpoints

#### `GET /api/stops`

Get all transit stops.

**Query Parameters:**
- `day_type` (optional): `weekday`, `saturday`, or `sunday` (default: `weekday`)

**Response:**
```json
[
  {
    "stop_id": "de:09162:1",
    "stop_name": "Marienplatz",
    "lat": 48.1374,
    "lon": 11.5755
  },
  ...
]
```

#### `GET /api/metadata`

Get GTFS data metadata for attribution.

**Response:**
```json
{
  "source": "Münchner Verkehrs- und Tarifverbund GmbH (MVV)",
  "download_date": "2025-11-14",
  "feed_version": "2025.11",
  "last_updated": "2025-11-14T06:00:00Z"
}
```

#### `POST /api/reachability`

Calculate reachable stops from an origin.

**Request:**
```json
{
  "origin_stop_id": "de:09162:1",
  "max_time_minutes": 30,
  "departure_time": "09:00",
  "day_type": "weekday"
}
```

**Response:**
```json
{
  "origin": {
    "stop_id": "de:09162:1",
    "stop_name": "Marienplatz",
    "lat": 48.1374,
    "lon": 11.5755
  },
  "reachable_stops": [
    {
      "stop_id": "...",
      "stop_name": "...",
      "lat": 48.xxx,
      "lon": 11.xxx,
      "travel_time_minutes": 15.5,
      "num_transfers": 1
    },
    ...
  ]
}
```

#### `POST /api/reachability-timeline`

Calculate reachability timeline for animation.

**Request:**
```json
{
  "origin_stop_id": "de:09162:1",
  "max_time_minutes": 30,
  "time_step_minutes": 5,
  "departure_time": "09:00",
  "day_type": "weekday"
}
```

**Response:**
```json
{
  "origin": { ... },
  "timeline": [
    {
      "elapsed_minutes": 5,
      "reachable_stops": [ ... ]
    },
    {
      "elapsed_minutes": 10,
      "reachable_stops": [ ... ]
    },
    ...
  ]
}
```

#### `POST /api/admin/update-gtfs`

Check for GTFS updates and rebuild graphs if needed.

**Headers:**
- `Authorization: Bearer YOUR_ADMIN_TOKEN`

**Response:**
```json
{
  "updated": true,
  "message": "GTFS data updated and graphs rebuilt",
  "metadata": { ... }
}
```

## Data Attribution

**IMPORTANT**: This application uses GTFS data from:

> **Münchner Verkehrs- und Tarifverbund GmbH (MVV)**

As required by the data license, attribution is displayed in the application footer with:
- Data source: MVV
- Download date
- Feed version (if available)

**Data URL**: https://www.mvv-muenchen.de/fileadmin/mediapool/02-Fahrplanauskunft/03-Downloads/openData/gesamt_gtfs.zip

**License Information**: https://www.mvv-muenchen.de/fahrplanauskunft/fuer-entwickler/opendata/index.html

## How It Works

### 1. GTFS Data Processing

The application downloads GTFS (General Transit Feed Specification) data from MVV, which includes:
- `stops.txt`: All transit stops with coordinates
- `stop_times.txt`: Scheduled arrival/departure times for each trip
- `trips.txt`: Trip information
- `routes.txt`: Route information
- `calendar.txt`: Service schedules (weekday/weekend)

### 2. Graph Building

For each day type (weekday/saturday/sunday), the application builds a directed graph where:
- **Nodes**: Transit stops (with lat/lon attributes)
- **Edges**: Scheduled connections between consecutive stops on each trip
- **Edge Attributes**: departure_time, arrival_time, trip_id, route_name, duration

Example edge:
```
Marienplatz → Odeonsplatz
  departure_time: 32400 (09:00:00)
  arrival_time: 32520 (09:02:00)
  trip_id: "1234"
  route_name: "U3"
```

### 3. Reachability Algorithm

Uses a time-dependent Dijkstra's algorithm:

1. Start at origin stop at specified departure time
2. Track earliest arrival time at each stop
3. Explore outgoing edges (only take connections that depart after arrival)
4. Stop when travel time exceeds maximum
5. Return all reached stops with travel times

Key insight: Unlike standard shortest-path, this considers **when** you arrive at each stop, as you can only take connections that depart after your arrival.

### 4. Timeline Calculation

For animation, instead of running the algorithm multiple times (once per frame), we:
1. Run a single reachability calculation for max time
2. Group results by time intervals (e.g., 5 minutes)
3. Return timeline frames for smooth animation

### 5. Frontend Animation

The frontend:
1. Fetches complete timeline from API
2. Displays frames sequentially (1 second per frame)
3. Updates map markers and progress bar
4. Allows play/pause/stop control

## Configuration

### Environment Variables

Create a `.env` file (see `.env.example`):

```bash
# GCP Configuration (optional for local)
GCP_PROJECT_ID=your-project-id
GCS_BUCKET_NAME=your-bucket-name

# Admin token
ADMIN_TOKEN=your-secure-token

# Optional: Override GTFS URL
GTFS_URL=https://custom-url/gtfs.zip
```

### Configuration Options

See `backend/config.py` for all configuration options:

- `GTFS_URL`: URL to download GTFS data
- `DEFAULT_TRANSFER_TIME`: Default transfer time between stops (180 seconds)
- `MAX_CALCULATION_TIME`: Maximum reachability time (3600 seconds = 60 minutes)
- `DEFAULT_TIME_STEP_MINUTES`: Animation frame interval (5 minutes)
- `MAP_CENTER_LAT/LON`: Map center coordinates

## Performance

- **GTFS Data Size**: ~50MB (zip), ~200MB (extracted)
- **Graph Size**: ~1-2MB per day type (pickled)
- **Stops**: ~4,000 transit stops
- **Edges**: ~500,000+ scheduled connections
- **Calculation Time**: 2-5 seconds for 30-minute reachability
- **Memory Usage**: ~500MB-1GB (with loaded graphs)

### Optimization Tips

1. **Cache Graphs**: Graphs are pickled and loaded at startup (faster than rebuilding)
2. **Timeline API**: Single calculation for all animation frames
3. **Frontend Caching**: Timeline data cached client-side for replay
4. **Cloud Run**: Auto-scales based on traffic, scales to zero when idle

## Known Limitations

### Out of Scope (Iteration 1)

- **Walking connections**: No walking between stops or to/from addresses
- **GPS location**: Cannot use current location as starting point
- **Real-time data**: Uses scheduled data only (GTFS static, not GTFS-RT)
- **Multi-modal**: Transit only (no bikes, cars, etc.)
- **Route optimization**: Shows reachability, not fastest routes

### Future Enhancements (Iteration 2+)

- Walking connections with configurable walk speed
- Address geocoding (start from any address)
- Real-time vehicle positions and delays (GTFS-RT)
- Convex/concave hull around reachable area
- Statistics during animation (X stops, Y km² coverage)
- Variable animation speed control
- Export reachability data (GeoJSON, CSV)
- Comparison mode (compare different times/days)

## Troubleshooting

### "Calculator not initialized" error

**Cause**: Graphs haven't been built yet.

**Solution**:
```bash
python scripts/init_data.py
```

### Slow calculation times

**Cause**: Large time windows or many stops.

**Solution**:
- Reduce max time (30 min instead of 60 min)
- Check graph size (should be ~1-2MB per day type)
- Ensure graphs are loaded at startup (not rebuilt each time)

### GTFS download fails

**Cause**: MVV URL changed or network issues.

**Solution**:
- Check MVV website for new URL
- Update `GTFS_URL` in config or `.env`
- Try manual download and place in `static/data/gtfs.zip`

### Memory errors

**Cause**: Insufficient memory for large graphs.

**Solution**:
- Increase Cloud Run memory (2Gi → 4Gi)
- Check for memory leaks in calculation
- Consider graph compression or on-demand loading

## Development

### Run Tests

```bash
pytest tests/
```

### Code Style

```bash
# Format code
black backend/

# Lint
flake8 backend/
```

### Local Development with Hot Reload

```bash
uvicorn backend.api.app:app --reload --host 0.0.0.0 --port 8000
```

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- **MVV (Münchner Verkehrs- und Tarifverbund GmbH)** for providing open GTFS data
- **OpenStreetMap** contributors for map tiles
- **Leaflet.js** for interactive mapping
- **NetworkX** for graph algorithms
- **FastAPI** for the excellent web framework

## Contact

- **Project Repository**: https://github.com/JuMaD/MVV_Analytics
- **Issues**: https://github.com/JuMaD/MVV_Analytics/issues

---

**Note**: This application is not affiliated with or endorsed by MVV. It is an independent project using publicly available open data.
