# 🌐 Cambodia Road Router

**Cambodia Road Router** is a web-based application for visualizing road networks, calculating shortest paths, and searching locations within Cambodia using **OpenStreetMap (OSM)** data. It integrates:

- **Python** (`RoadGraph` class) for graph processing.
- **Django** backend for API services.
- **Leaflet.js** frontend for interactive mapping.

The application supports multiple travel modes (car, motorcycle, bicycle, walking) with realistic travel time estimates.

---

## 🚀 Features

1. **Road Network Visualization**  
   - Displays road segments within a bounding box using **RoadGraph**’s R-tree index.
   - Interactive map supports zooming and panning.

2. **Shortest Path Routing**  
   - Computes optimal routes using **Dijkstra’s algorithm**.
   - Distance and travel time are adjusted based on road types and congestion levels.

3. **Location Search**  
   - Integrates **Nominatim API** for geocoding.
   - Results are filtered to Cambodia (`10–14.5°N, 102–108°E`).

4. **Interactive Map**  
   - Leaflet-based frontend with draggable markers.
   - Real-time search suggestions and animated route rendering.

5. **Caching**  
   - **Django cache** for API responses.  
   - **RoadGraph cache** for graph data to reduce load time.

6. **Robust Error Handling**  
   - Input validation and API error handling.
   - User-friendly feedback messages.

---

## 🛠 Prerequisites

- **Python 3.8+**
- **Django 4.0+**
- **PostgreSQL** (optional; SQLite used by default)
- **Node.js** (optional, for frontend npm extensions)
- **OSM file** for Cambodia (`data/cambodia.osm`)
- Internet access for **OpenStreetMap tiles** and **Nominatim API**

---

## ⚡ Installation

### 1. Clone the Repository
```bash
git clone https://github.com/JACKAS5/Road_Distance_Tracking.git
cd cambodia-road-router/ROAD_TRACKING_PROJECT
```

### 2. Set Up Virtual Environment
```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
```

### 3. Install Python Dependencies
```bash
pip install -r requirements.txt
```
### 4. Configure Django Settings
Update ```ROAD_TRACKING_PROJECT/settings.py```:
```python
ROAD_GRAPH_CACHE_PATH = 'caches/road_graph_cache.pkl'
OSM_FILE_PATH = 'data/cambodia.osm'
NOMINATIM_URL = 'https://nominatim.openstreetmap.org/search'
NOMINATIM_USER_AGENT = 'CambodiaRoadRouter/1.0'
NOMINATIM_TIMEOUT = 10
CAMBODIA_BOUNDS = {
    'min_lat': 10.0, 'max_lat': 14.5,
    'min_lon': 102.0, 'max_lon': 108.0
}
```
Ensure ```data/cambodia.osm``` exists in the ```data/``` directory.

### 5. Run Migrations
```bash
python manage.py migrate
```

### 6. Start the Server
```bash
python manage.py runserver
```

Open http://localhost:8000/ to access the map interface ```(templates/map.html)```.

---

### 🗺 Usage
### 1. ** View Roads **

    - Map loads road segments from RoadGraph within Cambodia bounds.

    - Explore by zooming and panning.

2. ** Search Locations **

- Enter queries (e.g., "Phnom Penh") in the search bar.

- Select suggestions to place markers (start or end points).

3. ** Set Route Points **

- Click map to set start (A) and end (B) points.

- Drag markers to adjust positions.

4. ** Calculate Route **

- Click Get Route to compute the shortest path.

- View distance and travel times for all travel modes.

5. ** Reset Map **

- Click Reset to clear markers, routes, and inputs.

---

### 📂 Project Structure

```text
ROAD_TRACKING_PROJECT/
├── cache/                  # Django cache
├── caches/                 # RoadGraph cache files
│   ├── rtree_data/         # R-tree index
│   └── road_graph_cache.pkl
├── data/                   # OSM files
│   └── cambodia.osm
├── logs/                   # Log files
├── templates/              # Frontend templates
│   └── map.html
├── static/                 # Static files (if any)
├── road_graph.py           # RoadGraph class for graph processing
├── views.py                # API endpoints
├── urls.py                 # URL routing
├── logging_config.py       # Logging configuration
├── manage.py               # Django management script
├── venv/                   # Virtual environment
└── db.sqlite3              # SQLite database
```
---

### ⚙ Technical Details

- ### RoadGraph Class 

  - Parses ```cambodia.osm``` to build a graph using the Haversine formula for edge distances.

  - Uses KDTree for nearest-node queries and R-tree for spatial indexing.

  - Generates cache files on initial build ```(caches/road_graph_cache.pkl, rtree_data/)```.

- ### Django Backend

  - APIs: /roads/, /distance/, /search/

  - Input validation, caching, and Nominatim integration for geocoding.

- ### JavaScript Frontend

  - Leaflet map with draggable markers and animated routes.

  - Travel times adjusted dynamically based on road type and congestion.

- ### Initial Build

  - On first run, RoadGraph parses cambodia.osm and creates cache files to speed up subsequent runs.
