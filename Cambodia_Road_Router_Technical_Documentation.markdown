# Cambodia Road Router Technical Documentation

## Overview
The Cambodia Road Router is a web application built with Django and Leaflet to visualize Cambodia’s road network, enable location search, and calculate shortest paths between points. The backend processes `cambodia.osm` using the `RoadGraph` class, serving road data via `/api/roads/`, distances via `/distance/`, and location searches via `/api/search/`. The frontend (`map.html`) renders roads as polylines, supports interactive markers, and fetches data based on map bounds and zoom level to optimize performance.

This document details all functions in `views.py` (backend) and `map.html` (frontend JavaScript), explaining their purpose, parameters, return values, and optimizations to address performance concerns (e.g., large road datasets slowing the computer) and UI rendering issues.

## Backend: `views.py`

Located in `road_router/views.py`, this module defines Django views to handle HTTP requests. It uses `RoadGraph` to process `cambodia.osm` and Nominatim for geocoding.

### Module-Level Setup
- **Imports**:
  - `requests`: For HTTP requests to Nominatim.
  - `django.shortcuts.render`: Renders HTML templates.
  - `django.http.JsonResponse`: Returns JSON responses.
  - `road_graph.RoadGraph`: Custom class to parse `cambodia.osm` into a graph.
  - `os`: For file path operations.
  - `logging`: For debugging and error tracking.
- **Constants**:
  - `BASE_DIR`: Root directory (`os.path.dirname(os.path.dirname(os.path.abspath(__file__)))`).
  - `osm_path`: Path to `data/cambodia.osm`.
  - `cache_path`: Path to `data/road_graph_cache.pkl` for `RoadGraph` caching.
- **Logger**:
  - `logger = logging.getLogger(__name__)`: Logs messages with module namespace.
- **RoadGraph Initialization**:
  - `road_graph = RoadGraph(osm_path, cache_file=cache_path)`: Creates a graph from `cambodia.osm`, cached in `road_graph_cache.pkl`.
  - Wrapped in `try-except` to log and raise initialization errors.

### Functions

#### `home(request)`
- **Purpose**: Serves the main page (`map.html`) for the web application.
- **Parameters**:
  - `request`: Django `HttpRequest` object.
- **Behavior**:
  - Renders `api/templates/map.html` using `render`.
  - Logs errors if template rendering fails.
- **Return Value**:
  - `HttpResponse`: HTML content of `map.html`.
  - `JsonResponse`: Error message with status 500 if rendering fails.
- **Example**:
  - Request: `GET /`
  - Response: HTML page or `{"error": "Failed to load UI"}`.
- **Optimizations**:
  - Error handling prevents server crashes if `map.html` is missing.

#### `get_roads(request)`
- **Purpose**: Returns road segments within a specified bounding box, filtered by road type and paginated for performance.
- **Parameters**:
  - `request`: Django `HttpRequest` with optional query parameters:
    - `min_lat`, `max_lat`, `min_lon`, `max_lon`: Bounding box (defaults: 10, 14.5, 102, 108).
    - `page`: Page number (default: 1).
    - `per_page`: Roads per page (default: 1000).
    - `road_types`: Comma-separated highway types (default: `motorway,trunk,primary`).
- **Behavior**:
  - Parses query parameters with defaults.
  - Iterates over `road_graph.graph` nodes and edges.
  - Validates coordinates (`from_coord`, `to_coord`) as lists/tuples of two numbers.
  - Filters roads by:
    - Bounding box: `min_lat ≤ lat ≤ max_lat`, `min_lon ≤ lon ≤ max_lon`.
    - Road type: `edge_data.get('highway')` in `road_types`.
  - Paginates output: Returns roads from index `(page-1)*per_page` to `page*per_page`.
  - Logs invalid coordinates, road count, and errors.
- **Return Value**:
  - `JsonResponse`: `{"roads": [{"path": [[lat1, lon1], [lat2, lon2]], "highway": type}, ...], "total": N, "page": X, "per_page": Y}`.
  - `JsonResponse`: Error message with status 500 if processing fails.
- **Example**:
  - Request: `GET /api/roads/?page=1&per_page=10&road_types=primary&min_lat=11&max_lat=12`
  - Response: `{"roads": [{"path": [[11.5, 104.9], [11.51, 104.91]], "highway": "primary"}, ...], "total": 500, "page": 1, "per_page": 10}`.
- **Optimizations**:
  - Pagination reduces response size (e.g., 1000 roads vs. all).
  - Bounding box limits roads to visible map area.
  - Road type filter (e.g., `primary`) excludes minor paths.
  - Coordinate validation skips invalid data.

#### `calculate_distance(request)`
- **Purpose**: Computes the shortest path and distance between two points using `RoadGraph`.
- **Parameters**:
  - `request`: Django `HttpRequest` with query parameters:
    - `start_lat`, `start_lon`: Starting coordinates.
    - `end_lat`, `end_lon`: Ending coordinates.
- **Behavior**:
  - Converts query parameters to floats, validating input.
  - Finds nearest graph nodes using `road_graph.find_nearest_node`.
  - Computes shortest path and distance using `road_graph.shortest_path_with_path`.
  - Logs path details or no-path warnings.
  - Returns distance in meters and kilometers, with the path as node coordinates.
- **Return Value**:
  - `JsonResponse`: `{"distance_meters": X, "distance_kilometers": Y, "path": [[lat1, lon1], ...], "start_node": ID, "end_node": ID}`.
  - `JsonResponse`: Error message with status 400 (invalid coords) or 404 (no path).
- **Example**:
  - Request: `GET /distance/?start_lat=11.5621&start_lon=104.9160&end_lat=13.3621&end_lon=103.8597`
  - Response: `{"distance_meters": 123456.78, "distance_kilometers": 123.46, "path": [[11.5621, 104.9160], ...], "start_node": "N1", "end_node": "N2"}`.
- **Optimizations**:
  - Efficient pathfinding via `RoadGraph` (assumed Dijkstra’s algorithm).
  - Error handling avoids crashes on invalid inputs.

#### `search_location(request)`
- **Purpose**: Searches for locations in Cambodia using Nominatim’s geocoding API.
- **Parameters**:
  - `request`: Django `HttpRequest` with query parameters:
    - `q`: Search query (e.g., "Phnom Penh").
    - `limit`: Max results (default: 1).
- **Behavior**:
  - Validates query presence.
  - Sends HTTP GET to Nominatim with URL-encoded query and custom User-Agent.
  - Filters results to Cambodia (10–14.5°N, 102–108°E).
  - Logs request URL, result count, and errors.
- **Return Value**:
  - `JsonResponse`: Array of results, e.g., `[{"lat": "11.562108", "lon": "104.916009", "display_name": "Phnom Penh, Cambodia"}]`.
  - `JsonResponse`: Error message with status 400 (empty query) or 500 (API failure).
- **Example**:
  - Request: `GET /api/search/?q=Phnom+Penh&limit=1`
  - Response: `[{"lat": "11.562108", "lon": "104.916009", "display_name": "Phnom Penh, Cambodia"}]`.
- **Optimizations**:
  - Limits results to reduce response size.
  - Filters by Cambodia bounds to exclude irrelevant locations.
  - Timeout (5s) prevents hanging on slow API responses.

## Frontend: `map.html`

Located in `api/templates/map.html`, this file defines the web interface using HTML, CSS, and JavaScript with Leaflet. It renders a map, displays roads as polylines, allows location search, and computes routes.

### HTML Structure
- **Elements**:
  - `<div id="map">`: Container for Leaflet map.
  - `<div class="controls">`: Search bar and coordinate inputs.
  - `<div id="error-box">`: Displays errors (e.g., map init failure).
  - `<div id="info">`: Shows info (e.g., route distance, road count).
  - `<div id="loading">`: Loading indicator during road fetch.
- **CSS**:
  - `#map`: Full viewport height (`calc(100vh - 80px)`), `min-height: 400px`.
  - `.controls`: Centered, responsive flexbox layout.
  - Media queries for mobile (`max-width: 600px`).
- **Dependencies**:
  - Leaflet 1.9.3 (CSS/JS via CDN).

### JavaScript Functions

#### Initialization
- **Variables**:
  - `map`, `startMarker`, `endMarker`, `routeLayer`, `roadLayer`: Leaflet objects.
  - `currentPage`: Tracks pagination (starts at 1).
  - `totalRoads`: Total road segments available.
  - `isLoading`: Prevents concurrent road fetches.
- **Map Setup**:
  - Initializes Leaflet map on `#map` with center `[11.5449, 104.8922]` (Phnom Penh) and zoom 7.
  - Adds OpenStreetMap tiles with attribution.
  - Logs init steps (`UI: Starting`, `UI: Map ready`).
  - Catches errors (e.g., missing `#map`) and displays via `showError`.

#### `loadRoads()`
- **Purpose**: Fetches and renders road segments within the current map bounds.
- **Parameters**: None (uses global `map`, `currentPage`, `isLoading`).
- **Behavior**:
  - Skips if `isLoading` is true.
  - Shows loading indicator (`#loading`).
  - Gets map bounds (`getSouth`, `getNorth`, `getWest`, `getEast`).
  - Fetches `/api/roads/` with bounds, `page`, `per_page=1000`, and `road_types=primary`.
  - Validates response as array (`data.roads`).
  - Creates or updates `roadLayer` (L.layerGroup).
  - Renders each road as a polyline (color: `#666`, weight: 2).
  - Validates coordinates, skipping invalid ones.
  - Logs road count and errors.
  - Increments `currentPage` and fetches more if available and zoom ≥10.
- **Return Value**: None.
- **Example**:
  - Fetches: `/api/roads/?min_lat=11&max_lat=12&min_lon=104&max_lon=105&page=1&per_page=1000&road_types=primary`
  - Renders: Gray polylines for primary roads.
- **Optimizations**:
  - Pagination limits to 1000 roads per fetch.
  - Bounds-based fetching reduces irrelevant data.
  - Zoom-based loading (≥10) prevents rendering at low zoom.
  - Coordinate validation avoids rendering errors.
  - Clears old layers on reload.

#### `placeMarker(latlng, type)`
- **Purpose**: Places a draggable marker (start or end) on the map and updates inputs.
- **Parameters**:
  - `latlng`: Leaflet `L.LatLng` object (e.g., `{lat: 11.5621, lng: 104.9160}`).
  - `type`: String (`"start"` or `"end"`).
- **Behavior**:
  - Validates `latlng` (numeric `lat`, `lng`).
  - Updates inputs (`#start-lat`, `#start-lon` or `#end-lat`, `#end-lon`) with coordinates.
  - Creates draggable Leaflet marker.
  - Adds dragend handler to update inputs and trigger `getRoute`.
  - Replaces existing marker if present.
  - Logs placement and errors.
- **Return Value**: None.
- **Example**:
  - Input: `latlng={lat: 11.5621, lng: 104.9160}`, `type="start"`
  - Output: Marker at `[11.5621, 104.9160]`, inputs updated to `11.562100`, `104.916000`.
- **Optimizations**:
  - Reuses markers to minimize DOM updates.
  - Validates inputs to prevent errors.

#### `searchLocation()`
- **Purpose**: Searches for a location via `/api/search/` and places a marker.
- **Parameters**: None (reads `#search-input`).
- **Behavior**:
  - Gets query from `#search-input`.
  - Validates non-empty query.
  - Fetches `/api/search/?q=<query>&limit=1`.
  - Parses response, validates `lat`, `lon`.
  - Calls `placeMarker` for start (if no `startMarker`) or end.
  - Zooms map to location (zoom 12).
  - Clears search input.
  - Logs request, response, and errors.
- **Return Value**: None.
- **Example**:
  - Input: `#search-input="Phnom Penh"`
  - Fetches: `/api/search/?q=Phnom+Penh&limit=1`
  - Output: Marker at `[11.562108, 104.916009]`.
- **Optimizations**:
  - Limits to 1 result.
  - Error handling prevents crashes on API failure.

#### `getRoute()`
- **Purpose**: Computes and displays the shortest path between start and end points.
- **Parameters**: None (reads `#start-lat`, `#start-lon`, `#end-lat`, `#end-lon`).
- **Behavior**:
  - Parses input coordinates as floats.
  - Validates all coordinates are numeric.
  - Fetches `/distance/?start_lat=X&start_lon=Y&end_lat=Z&end_lon=W`.
  - Renders path as red polyline (`routeLayer`).
  - Fits map to path bounds.
  - Displays distance in `#info`.
  - Logs request, response, and errors.
- **Return Value**: None.
- **Example**:
  - Inputs: `#start-lat=11.5621`, `#start-lon=104.9160`, `#end-lat=13.3621`, `#end-lon=103.8597`
  - Fetches: `/distance/?start_lat=11.5621&start_lon=104.9160&end_lat=13.3621&end_lon=103.8597`
  - Output: Red polyline, `#info="123.46 km (123456.78 m)"`.
- **Optimizations**:
  - Reuses `routeLayer` to minimize DOM updates.
  - Validates inputs to avoid invalid requests.

#### `showInfo(message)`
- **Purpose**: Displays a message in the info box.
- **Parameters**:
  - `message`: String to display.
- **Behavior**:
  - Sets `#info` text to `message`.
  - Toggles visibility (`block` if message, `none` if empty).
  - Logs message.
- **Return Value**: None.
- **Example**:
  - Input: `message="Loaded 500 roads"`
  - Output: `#info` shows "Loaded 500 roads".
- **Optimizations**:
  - Minimal DOM updates.

#### `showError(message)`
- **Purpose**: Displays an error message for 5 seconds.
- **Parameters**:
  - `message`: String to display.
- **Behavior**:
  - Sets `#error-box` text to `message`.
  - Shows `#error-box` and hides after 5000ms.
  - Logs error.
- **Return Value**: None.
- **Example**:
  - Input: `message="Map failed"`
  - Output: `#error-box` shows "Map failed" for 5s.
- **Optimizations**:
  - Auto-hides to avoid clutter.

### Event Handlers
- **Map `moveend zoomend`**:
  - Triggers `loadRoads` at zoom ≥10, resetting `currentPage` and clearing `roadLayer`.
- **Map `click`**:
  - Places start marker if none exists, else end marker and calls `getRoute`.
- **Button `onclick`**:
  - `#search-input` button: Calls `searchLocation`.
  - Route button: Calls `getRoute`.

## Performance Optimizations
- **Backend**:
  - Pagination (`per_page=1000`) reduces JSON size.
  - Bounding box filters roads to visible area.
  - Road type filter (`primary`) excludes minor paths.
  - Coordinate validation skips invalid data.
- **Frontend**:
  - Lazy loading fetches roads only at zoom ≥10.
  - Pagination limits rendering to 1000 polylines per fetch.
  - Clears old layers on zoom/move to free memory.
  - Loading indicator improves user experience.
  - Minimal CSS avoids heavy frameworks like TailwindCSS.
- **General**:
  - Logging (`views.py`, `map.html`) aids debugging without performance overhead.
  - Error handling prevents crashes from invalid data or API failures.

## Dependencies
- **Backend**:
  - Django: Web framework.
  - `requests`: For Nominatim API.
  - `RoadGraph`: Custom class (assumed to parse OSM and compute paths).
  - `cambodia.osm`: OSM data file.
- **Frontend**:
  - Leaflet 1.9.3: Map rendering.
  - OpenStreetMap: Tile provider.

## Testing Instructions
1. **Backend**:
   - Save `views.py` in `road_router/views.py`.
   - Ensure `data/cambodia.osm` exists.
   - Add logging to `road_router/settings.py`:
     ```python
     LOGGING = {
         'version': 1,
         'disable_existing_loggers': False,
         'handlers': {'console': {'class': 'logging.StreamHandler'}},
         'loggers': {'': {'handlers': ['console'], 'level': 'INFO'}}
     }
     ```
   - Run `python manage.py runserver`.
   - Test APIs:
     ```bash
     curl "http://localhost:8000/api/roads/?page=1&per_page=10&road_types=primary"
     curl "http://localhost:8000/api/search/?q=Phnom+Penh&limit=1"
     ```
2. **Frontend**:
   - Save `map.html` in `api/templates/`.
   - Open `http://localhost:8000/`.
   - Verify map, controls, and roads (zoom to 10+).
   - Check DevTools Console for logs/errors.
3. **RoadGraph**:
   - If roads fail, verify `RoadGraph` stores `highway` in `edge_data`.

## Limitations
- **RoadGraph**: Assumed to support `highway` tags and efficient pathfinding. Share implementation if issues arise.
- **Nominatim**: Rate-limited; may fail under heavy load. Consider local Nominatim or OpenCage.
- **Performance**: Large `cambodia.osm` datasets may still slow rendering at high zoom with many roads. Adjust `per_page` or `road_types`.

## Future Improvements
- Cache `/api/roads/` responses in Django.
- Use vector tiles for road rendering.
- Add road type selector in UI.
- Store roads in a database for faster queries.