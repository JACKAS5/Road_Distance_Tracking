Cambodia Road Router
The Cambodia Road Router is a web-based application for visualizing road networks, calculating shortest paths, and searching locations within Cambodia using OpenStreetMap (OSM) data. It integrates a Python-based RoadGraph class for graph processing, a Django backend for API services, and a Leaflet-based JavaScript frontend for interactive mapping. The application supports routing for various travel modes (car, motorcycle, bicycle, walking) with realistic travel time estimates.
Features

Road Network Visualization: Displays road segments within a bounding box using RoadGraph’s R-tree index.
Shortest Path Routing: Computes optimal routes using Dijkstra’s algorithm, with distances and travel times adjusted for road types and congestion.
Location Search: Integrates Nominatim API for searching locations, filtered to Cambodia (10–14.5°N, 102–108°E).
Interactive Map: Leaflet-based frontend with draggable markers, real-time suggestions, and animated route rendering.
Caching: Optimizes performance with Django cache for API responses and RoadGraph cache for graph data.
Robust Error Handling: Validates inputs, handles API errors, and provides user-friendly feedback.

Prerequisites

Python 3.8+
Django 4.0+
PostgreSQL (optional, for production; SQLite used by default)
Node.js (optional, if extending frontend with npm)
OSM file for Cambodia (.osm format, provided as data/cambodia.osm)
Internet access for OpenStreetMap tiles and Nominatim API

Installation

Clone the Repository:
git clone https://github.com/JACKAS5/Road_Distance_Tracking.git
cd cambodia-road-router/ROAD_TRACKING_PROJECT


Set Up Virtual Environment:
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate


Install Python Dependencies:
pip install -r requirements.txt

Example requirements.txt (to be created if not present):
django==4.2
requests==2.31.0
scipy==1.10.1
rtree==1.0.1
shapely==2.0.1


Configure Django Settings:

Update ROAD_TRACKING_PROJECT/settings.py with:ROAD_GRAPH_CACHE_PATH = 'caches/road_graph_cache.pkl'
OSM_FILE_PATH = 'data/cambodia.osm'
NOMINATIM_URL = 'https://nominatim.openstreetmap.org/search'
NOMINATIM_USER_AGENT = 'CambodiaRoadRouter/1.0'
NOMINATIM_TIMEOUT = 10
CAMBODIA_BOUNDS = {
    'min_lat': 10.0, 'max_lat': 14.5,
    'min_lon': 102.0, 'max_lon': 108.0
}


Ensure data/cambodia.osm exists (already included in the repo).


Run Django Migrations:
python manage.py migrate


Start the Django Server:
python manage.py runserver


Access the Application:

Open http://localhost:8000 in a browser to view the map interface at templates/map.html.



Usage

View Roads:

The map loads road segments within Cambodia’s bounds (10–14.5°N, 102–108°E) from the initial RoadGraph build.
Zoom/pan to explore the network.


Search Locations:

Enter a query (e.g., "Phnom Penh") in the search bar on the map page.
Select suggestions or click "Search" to place a marker (start or end point).


Set Route Points:

Click the map to set start (A) and end (B) points, or enter coordinates manually.
Drag markers to adjust positions.


Calculate Route:

Click "Get Route" to compute the shortest path using the backend API.
View distance and travel times (car, motorcycle, bicycle, walking) in the info box.


Reset Map:

Click "Reset" to clear markers, routes, and inputs.



Project Structure
ROAD_TRACKING_PROJECT/
├── cache/                      # Django cache (generated, ignored)
├── caches/                     # RoadGraph cache (generated, ignored)
│   ├── rtree_data/             # R-tree index files
│   └── road_graph_cache.pkl    # Serialized graph data
├── data/                       # Data files
│   └── cambodia.osm            # OSM file for Cambodia
├── logs/                       # Log files (generated, ignored)
│   └── road_tracking_project   # Project logs
├── tracker/                    # Tracker directory (purpose unclear, ignored if unused)
├── __pycache__/                # Python bytecode (ignored)
├── migrations/                 # Django migrations
├── static/                     # Static files (if any, ignored if unused)
├── templates/                  # HTML templates
│   └── map.html                # Leaflet-based frontend
├── __init__.py                 # Python package initializer
├── admin.py                    # Django admin configuration
├── apps.py                     # Django app configuration
├── models.py                   # Django models (if any)
├── road_graph.py               # RoadGraph class for graph processing
├── tests.py                    # Test cases (if any)
├── urls.py                     # URL routing
├── views.py                    # API endpoints (get_roads, calculate_distance, search_location)
├── venv/                       # Virtual environment (ignored)
├── db.sqlite3                  # SQLite database (generated, ignored)
├── logging_config.py           # Logging configuration
├── manage.py                   # Django management script
├── .gitignore                  # Git ignore file
└── Cambodia_Road_Router_Te...  # README (this file)

Technical Details

RoadGraph Class: Processes data/cambodia.osm to build a road network graph using the Haversine formula for edge distances, KDTree for nearest-node queries, and R-tree for spatial indexing. Generates cache files (caches/road_graph_cache.pkl, rtree_data/) on the initial build.
Django Backend: Provides APIs (/roads/, /distance/, /search/) with caching and input validation. Integrates Nominatim for geocoding via views.py.
JavaScript Frontend: Uses Leaflet in templates/map.html for mapping, with draggable markers, animated routes, and real-time search suggestions. Adjusts travel times based on road types and congestion.
Initial Build: On first run, RoadGraph parses cambodia.osm, generating cache files in caches/, which are ignored by .gitignore.

