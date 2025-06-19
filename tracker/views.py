import os
import json
import time
import hashlib
import logging
from typing import Optional
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_GET
from django.core.cache import cache
from shapely.geometry import LineString, box
from django.conf import settings
import requests
from .road_graph import RoadGraph 
from django.shortcuts import render


logger = logging.getLogger(__name__)

_road_graph_instance = None

def _initialize_road_graph() -> Optional['RoadGraph']:
    global _road_graph_instance
    if _road_graph_instance is not None:
        return _road_graph_instance

    try:
        required_settings = ['ROAD_GRAPH_CACHE_PATH', 'OSM_FILE_PATH', 'NOMINATIM_URL', 'NOMINATIM_USER_AGENT', 'NOMINATIM_TIMEOUT', 'CAMBODIA_BOUNDS']
        missing_settings = [s for s in required_settings if not hasattr(settings, s)]
        if missing_settings:
            raise ValueError(f"Missing settings: {', '.join(missing_settings)}")

        os.makedirs(os.path.dirname(settings.ROAD_GRAPH_CACHE_PATH), exist_ok=True)
        from .road_graph import RoadGraph
        _road_graph_instance = RoadGraph(
            osm_file=settings.OSM_FILE_PATH,
            cache_file=settings.ROAD_GRAPH_CACHE_PATH
        )
        logger.info("RoadGraph initialized successfully.")
    except FileNotFoundError as e:
        logger.critical(f"OSM/cache file not found: {e}", exc_info=True)
        _road_graph_instance = None
    except Exception as e:
        logger.critical(f"Failed to initialize RoadGraph: {e}", exc_info=True)
        _road_graph_instance = None
    return _road_graph_instance

def _get_road_graph() -> Optional['RoadGraph']:
    if _road_graph_instance is None:
        logger.error("RoadGraph instance not available.")
    return _road_graph_instance

_initialize_road_graph()

def home(request):
    return render(request, 'map.html')

@require_GET
def get_roads(request) -> JsonResponse:
    start_time = time.time()
    # Log full request details
    logger.debug(f"/roads/ request: URL={request.get_full_path()}, Client={request.META.get('REMOTE_ADDR', 'unknown')}")

    road_graph = _get_road_graph()
    if not road_graph or not hasattr(road_graph, 'edge_index'):
        logger.error("RoadGraph or edge_index unavailable")
        return JsonResponse({'error': 'Service unavailable'}, status=503)

    try:
        params = {key: request.GET.get(key) for key in ['north', 'south', 'east', 'west']}
        if not all(params.values()):
            logger.warning(f"Missing parameters: {params}, URL={request.get_full_path()}, Client={request.META.get('REMOTE_ADDR', 'unknown')}")
            return JsonResponse({'error': 'Missing required parameters: north, south, east, west'}, status=400)

        north = float(params['north'])
        south = float(params['south'])
        east = float(params['east'])
        west = float(params['west'])

        bounds = settings.CAMBODIA_BOUNDS
        if not (bounds['min_lat'] <= south < north <= bounds['max_lat'] and
                bounds['min_lon'] <= west < east <= bounds['max_lon']):
            logger.warning(f"Invalid bbox: {north},{south},{east},{west}, URL={request.get_full_path()}")
            return JsonResponse({'error': 'Bounding box outside Cambodia (10–14.5°N, 102–108°E)'}, status=400)
        if (north - south > 0.2) or (east - west > 0.2):
            logger.warning(f"Bbox too large: {north},{south},{east},{west}, URL={request.get_full_path()}")
            return JsonResponse({'error': 'Bounding box too large (max 0.2°)'}, status=400)

        bbox = box(west, south, east, north)
        logger.debug(f"Processing bbox: {bbox.bounds}")
    except (ValueError, TypeError) as e:
        logger.error(f"Invalid bbox parameters: {e}, URL={request.get_full_path()}")
        return JsonResponse({'error': f'Invalid bounding box parameters: {e}'}, status=400)

    try:
        bbox_key = hashlib.md5(json.dumps([north, south, east, west], sort_keys=True).encode()).hexdigest()
        cache_key = f"roads:{bbox_key}"
        cached = cache.get(cache_key)
        if cached:
            logger.info(f"Cache hit for {cache_key}, took {time.time() - start_time:.2f}s")
            return JsonResponse(cached, safe=False)

        filtered_roads = []
        edge_ids = list(road_graph.edge_index.intersection(bbox.bounds))
        MAX_FEATURES = 100
        logger.debug(f"Found {len(edge_ids)} edges, processing up to {MAX_FEATURES}")

        for edge_id in edge_ids[:MAX_FEATURES]:
            try:
                from_node, to_node = road_graph.edge_map[edge_id]
                line = LineString([road_graph.nodes[from_node], road_graph.nodes[to_node]])
                clipped = line.intersection(bbox)
                if not clipped.is_empty:
                    if clipped.geom_type == 'LineString':
                        filtered_roads.append({'path': list(clipped.coords)})
                    elif clipped.geom_type == 'MultiLineString':
                        for segment in clipped.geoms:
                            filtered_roads.append({'path': list(segment.coords)})
            except (KeyError, ValueError) as e:
                logger.warning(f"Invalid edge {edge_id}: {e}")
                continue

        if len(filtered_roads) == MAX_FEATURES:
            logger.warning(f"Hit MAX_FEATURES limit, results may be incomplete")

        cache.set(cache_key, filtered_roads, timeout=3600)
        logger.info(f"Processed {len(filtered_roads)} roads, cached as {cache_key}, took {time.time() - start_time:.2f}s")
        return JsonResponse(filtered_roads, safe=False)
    except Exception as e:
        logger.error(f"Error filtering roads: {e}", exc_info=True)
        return JsonResponse({'error': f'Error loading roads: {str(e)}'}, status=500)

@require_GET
def calculate_distance(request) -> JsonResponse:
    road_graph = _get_road_graph()
    if not road_graph:
        return JsonResponse({'error': 'Service unavailable'}, status=503)

    try:
        params = {key: request.GET.get(key) for key in ['start_lat', 'start_lon', 'end_lat', 'end_lon']}
        if not all(params.values()):
            return JsonResponse({'error': 'Missing coordinate parameters'}, status=400)

        start_lat = float(params['start_lat'])
        start_lon = float(params['start_lon'])
        end_lat = float(params['end_lat'])
        end_lon = float(params['end_lon'])

        bounds = settings.CAMBODIA_BOUNDS
        if not (bounds['min_lat'] <= start_lat <= bounds['max_lat'] and
                bounds['min_lon'] <= start_lon <= bounds['max_lon'] and
                bounds['min_lat'] <= end_lat <= bounds['max_lat'] and
                bounds['min_lon'] <= end_lon <= bounds['max_lon']):
            return JsonResponse({'error': 'Coordinates outside Cambodia bounds'}, status=400)
    except (ValueError, TypeError) as e:
        return JsonResponse({'error': f'Invalid coordinates: {e}'}, status=400)

    key_data = json.dumps({
        'start_lat': start_lat, 'start_lon': start_lon,
        'end_lat': end_lat, 'end_lon': end_lon
    }, sort_keys=True)
    cache_key = f'dist:{hashlib.md5(key_data.encode()).hexdigest()}'

    cached_result = cache.get(cache_key)
    if cached_result:
        return JsonResponse(cached_result)

    try:
        start_node = road_graph.find_nearest_node(start_lat, start_lon)
        end_node = road_graph.find_nearest_node(end_lat, end_lon)

        if start_node is None or end_node is None:
            return JsonResponse({'message': 'One or both points are too far from the road network.'}, status=400)

        path_nodes, distance = road_graph.shortest_path_with_path(start_node, end_node)

        if distance == float('inf') or not path_nodes:
            return JsonResponse({'message': 'No path found between the given points.'}, status=404)

        path_coords = [list(road_graph.nodes[n]) for n in path_nodes]

        distance_km = distance / 1000

        # Define average speeds in km/h for different vehicle types
        speeds_kmh = {
            'car': 60,
            'motorcycle': 50,
            'bicycle': 15,
            'walking': 5
        }

        travel_times = {}
        for vehicle, speed in speeds_kmh.items():
            travel_time_min = (distance_km / speed) * 60  # minutes
            travel_times[vehicle] = round(travel_time_min, 1)

        result = {
            'distance_meters': round(distance, 2),
            'distance_kilometers': round(distance_km, 2),
            'travel_times_minutes': travel_times,
            'path': path_coords,
            'start_node_id': start_node,
            'end_node_id': end_node
        }
        cache.set(cache_key, result, timeout=3600)
        return JsonResponse(result)
    except Exception as e:
        logger.error(f"Distance calculation error: {e}", exc_info=True)
        return JsonResponse({'error': 'Failed to calculate route.'}, status=500)


@require_GET
def search_location(request) -> JsonResponse:
    query = request.GET.get('q', '').strip()
    if not query:
        return JsonResponse({'error': 'Missing search query (parameter "q").'}, status=400)

    try:
        limit = int(request.GET.get('limit', 1))
        if limit <= 0 or limit > 50:
            return JsonResponse({'error': 'Limit must be between 1 and 50.'}, status=400)
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Invalid limit parameter.'}, status=400)

    cache_key = f'search:{hashlib.md5(query.encode()).hexdigest()}:{limit}'
    cached = cache.get(cache_key)
    if cached:
        return JsonResponse(cached, safe=False)

    url = f"https://nominatim.openstreetmap.org/search?q={requests.utils.quote(query)}&format=json&limit={limit}"
    headers = {'User-Agent': settings.NOMINATIM_USER_AGENT}

    try:
        response = requests.get(url, headers=headers, timeout=settings.NOMINATIM_TIMEOUT)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {e}")
        return JsonResponse({'error': 'Request failed'}, status=500)

    results = []
    for item in data:
        try:
            lat = float(item.get('lat'))
            lon = float(item.get('lon'))
            if (settings.CAMBODIA_BOUNDS['min_lat'] <= lat <= settings.CAMBODIA_BOUNDS['max_lat'] and
                settings.CAMBODIA_BOUNDS['min_lon'] <= lon <= settings.CAMBODIA_BOUNDS['max_lon']):
                results.append({
                    'display_name': item.get('display_name', ''),
                    'lat': lat,
                    'lon': lon
                })
        except (ValueError, TypeError):
            continue

    cache.set(cache_key, results, timeout=86400)
    return JsonResponse(results, safe=False)