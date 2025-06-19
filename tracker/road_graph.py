import math
import os
import pickle
from collections import defaultdict
import heapq
from scipy.spatial import KDTree
from rtree import index
from shapely.geometry import LineString
import logging
import shutil
import time
import errno

logger = logging.getLogger(__name__)

class RoadGraph:
    """
    The RoadGraph class is a Python implementation designed to process OpenStreetMap (OSM)
    data files in .osm (XML) format to construct a graph representation of a road network.
    It supports efficient graph construction, spatial indexing, caching, shortest path
    calculations, and nearest-node queries.
    """
    def __init__(self, osm_file, cache_file='road_graph_cache.pkl'):
        """
        Initializes the graph by loading from cache or building from the OSM file. Creates a local cache
        directory, attempts to load cached data, and builds a KD-tree for nearest-node queries. If the
        cache is missing or corrupted, it rebuilds the graph and saves it.
        """
        self.nodes = {}
        self.graph = defaultdict(list)
        self.edge_map = {}
        self.edge_index = None
        local_cache_dir = os.path.join(
            os.path.expanduser("~"),
            "OneDrive", "Desktop", "TUX", "Data Structure and Algorithm",
            "Final Project", "road_tracking_project", "caches")
        os.makedirs(local_cache_dir, exist_ok=True)
        self.cache_file = os.path.join(local_cache_dir, os.path.basename(cache_file))
        self.rtree_dir = os.path.join(local_cache_dir, 'rtree_data')

        os.makedirs(self.rtree_dir, exist_ok=True)

        try:
            # Try loading cache and R-tree index
            if os.path.exists(self.cache_file) and \
               os.path.exists(os.path.join(self.rtree_dir, 'index.dat')) and \
               os.path.exists(os.path.join(self.rtree_dir, 'index.idx')):
                logger.info(f"Loading cached graph and R-tree from {self.cache_file} and {self.rtree_dir}")
                self.load_cache()
            else:
                logger.info(f"Cache or index missing. Building graph from {osm_file}")
                self._build_graph(osm_file)
                self.save_cache()
                logger.info(f"Graph and R-tree cached to {self.cache_file} and {self.rtree_dir}")
        except Exception as e:
            logger.warning(f"Cache or R-tree corrupted or failed to load: {e}. Rebuilding graph and cache.")
            # Delete corrupted cache and index files before rebuilding
            self._clear_cache_and_index()
            self._build_graph(osm_file)
            self.save_cache()
            logger.info(f"Graph and R-tree rebuilt and cached to {self.cache_file} and {self.rtree_dir}")

        # Build KDTree for nearest node queries
        try:
            logger.info("Building KDTree for nearest node queries")
            coords = list(self.nodes.values())
            self.node_ids = list(self.nodes.keys())
            self.kd_tree = KDTree(coords)
            logger.info("KDTree ready")
        except Exception as e:
            logger.error(f"Failed to build KDTree: {e}", exc_info=True)
            raise

    def load_cache(self):
        """
        Loads the cached graph and R-tree index from disk. Reads the pickle file and initializes the
        R-tree with 2D properties. Handles errors by clearing corrupted files.
        """
        try:
            with open(self.cache_file, 'rb') as f:
                self.nodes, self.graph, self.edge_map = pickle.load(f)
            p = index.Property()
            p.dimension = 2
            p.dat_extension = 'dat'
            p.idx_extension = 'idx'

            # Load the existing R-tree index from disk
            self.edge_index = index.Index(os.path.join(self.rtree_dir, 'index'), properties=p)
            logger.info(f"Loaded cache from {self.cache_file}")
        except Exception as e:
            logger.error(f"Failed to load cache or R-tree index: {e}", exc_info=True)
            logger.warning("Deleting corrupted cache and R-tree files to rebuild...")
            # Close edge_index if it was opened
            if hasattr(self, 'edge_index') and self.edge_index is not None:
                try:
                    self.edge_index.close()
                    logger.info("Closed R-tree index before clearing cache")
                except Exception as e:
                    logger.error(f"Failed to close R-tree index: {e}")
                self.edge_index = None
            # Delete corrupted cache and R-tree files
            self._clear_cache_and_index()
            raise

    def _clear_cache_and_index(self):
        """
        Deletes corrupted cache and R-tree index files, retrying up to five times for permission errors.
        Recreates the R-tree directory.
        """
        # Close edge_index if it exists
        if hasattr(self, 'edge_index') and self.edge_index is not None:
            try:
                self.edge_index.close()
                logger.info("Closed R-tree index before clearing cache")
            except Exception as e:
                logger.error(f"Failed to close R-tree index: {e}")
            self.edge_index = None

        # Remove cache file
        if os.path.exists(self.cache_file):
            for _ in range(5):  # Retry up to 5 times
                try:
                    os.remove(self.cache_file)
                    logger.info(f"Deleted corrupted cache file {self.cache_file}")
                    break
                except OSError as e:
                    if e.errno == errno.EACCES:
                        logger.warning(f"Retrying deletion of cache file {self.cache_file}...")
                        time.sleep(1)
                    else:
                        logger.error(f"Failed to delete cache file {self.cache_file}: {e}")
                        break

        # Remove entire R-tree index directory
        if os.path.exists(self.rtree_dir):
            for _ in range(5):  # Retry up to 5 times
                try:
                    shutil.rmtree(self.rtree_dir)
                    logger.info(f"Deleted corrupted R-tree index directory {self.rtree_dir}")
                    break
                except OSError as e:
                    if e.errno == errno.EACCES:
                        logger.warning(f"Retrying deletion of R-tree directory {self.rtree_dir}...")
                        time.sleep(1)
                    else:
                        logger.error(f"Failed to delete R-tree directory {self.rtree_dir}: {e}")
                        break

        # Recreate the directory cleanly
        os.makedirs(self.rtree_dir, exist_ok=True)

    def _build_graph(self, osm_file):
        """
        Constructs the graph from the OSM file in .osm format.
        """
        if not os.path.exists(osm_file):
            raise FileNotFoundError(f"OSM file not found: {osm_file}")

        if not osm_file.endswith('.osm'):
            raise ValueError(f"Unsupported file format. Only .osm is supported: {osm_file}")

        self._build_graph_xml(osm_file)

    def _build_graph_xml(self, osm_file):
        """
        Parses .osm files using xml.etree.ElementTree. Processes nodes and ways with highway tags,
        computes distances, and indexes edges in the R-tree.
        """
        import xml.etree.ElementTree as ET
        tree = ET.parse(osm_file)
        root = tree.getroot()
        edge_id = 0

        for node in root.findall('node'):
            node_id = node.attrib['id']
            lat = float(node.attrib['lat'])
            lon = float(node.attrib['lon'])
            self.nodes[node_id] = (lat, lon)

        p = index.Property()
        p.dimension = 2
        p.dat_extension = 'dat'
        p.idx_extension = 'idx'

        # Close existing edge_index if it exists
        if hasattr(self, 'edge_index') and self.edge_index is not None:
            try:
                self.edge_index.close()
                logger.info("Closed existing R-tree index before creating new one")
            except Exception as e:
                logger.error(f"Failed to close existing R-tree index: {e}")
            self.edge_index = None

        # Clear existing index files if any (in case rebuild)
        if os.path.exists(self.rtree_dir):
            for _ in range(5):  # Retry up to 5 times
                try:
                    shutil.rmtree(self.rtree_dir)
                    logger.info(f"Deleted existing R-tree index directory {self.rtree_dir}")
                    break
                except OSError as e:
                    if e.errno == errno.EACCES:
                        logger.warning(f"Retrying deletion of R-tree directory {self.rtree_dir}...")
                        time.sleep(1)
                    else:
                        logger.error(f"Failed to delete R-tree directory {self.rtree_dir}: {e}")
                        break
        os.makedirs(self.rtree_dir, exist_ok=True)

        # Create a fresh R-tree index
        self.edge_index = index.Index(os.path.join(self.rtree_dir, 'index'), properties=p)

        for way in root.findall('way'):
            tags = {tag.attrib['k']: tag.attrib['v'] for tag in way.findall('tag')}
            if 'highway' not in tags:
                continue
            nd_refs = [nd.attrib['ref'] for nd in way.findall('nd')]
            oneway = tags.get('oneway') in ('yes', 'true', '1')
            for i in range(len(nd_refs) - 1):
                from_node = nd_refs[i]
                to_node = nd_refs[i + 1]
                if from_node not in self.nodes or to_node not in self.nodes:
                    continue
                distance = self._haversine_distance(
                    self.nodes[from_node][0], self.nodes[from_node][1],
                    self.nodes[to_node][0], self.nodes[to_node][1]
                )
                self.graph[from_node].append((to_node, distance))
                self.edge_map[edge_id] = (from_node, to_node)
                line = LineString([self.nodes[from_node], self.nodes[to_node]])
                self.edge_index.insert(edge_id, line.bounds)
                edge_id += 1
                if not oneway:
                    self.graph[to_node].append((from_node, distance))
                    self.edge_map[edge_id] = (to_node, from_node)
                    self.edge_index.insert(edge_id, line.bounds)
                    edge_id += 1

    def _haversine_distance(self, lat1, lon1, lat2, lon2):
        """
            The _haversine_distance method in the RoadGraph class is a key component used to calculate the great-circle 
            distance (shortest distance over the Earth's surface) between two geographic points defined by their latitude 
            and longitude coordinates.
        """
        R = 6371000  # Radius of the Earth in meters
        φ1 = math.radians(lat1)
        φ2 = math.radians(lat2)
        Δφ = math.radians(lat2 - lat1)
        Δλ = math.radians(lon2 - lon1)
        a = math.sin(Δφ / 2) ** 2 + math.cos(φ1) * math.cos(φ2) * math.sin(Δλ / 2) ** 2
        # central angle or angular distance (in radians) between two points on the Earth's surface
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c

    def save_cache(self):
        """
            Saves the graph's data structures (self.nodes, self.graph, and self.edge_map) to a file specified by 
            self.cache_file (e.g., road_graph_cache.pkl) using Python's pickle module. 
            The caching mechanism improves performance by enabling quick loading of precomputed data.
        """
        try:
            with open(self.cache_file, 'wb') as f:
                pickle.dump((self.nodes, self.graph, self.edge_map), f)
            logger.info(f"Saved cache to {self.cache_file}")
            # Close edge_index to ensure file handles are released
            if hasattr(self, 'edge_index') and self.edge_index is not None:
                try:
                    self.edge_index.close()
                    logger.info("Closed R-tree index after saving cache")
                except Exception as e:
                    logger.error(f"Failed to close R-tree index after saving cache: {e}")
                self.edge_index = None
        except Exception as e:
            logger.error(f"Failed to save cache: {e}", exc_info=True)

    def find_nearest_node(self, lat, lon):
        """ Finds the closest node to a given (lat, lon) using the KD-tree."""
        try:
            _, idx = self.kd_tree.query((lat, lon))
            return self.node_ids[idx]
        except Exception as e:
            logger.error(f"Failed to find nearest node: {e}", exc_info=True)
            return None

    def shortest_path_with_path(self, start_node, end_node):
        """ Computes the shortest path and distance using Dijkstra's algorithm."""
        try:
            distances = {node: float('inf') for node in self.nodes}
            previous = {node: None for node in self.nodes}
            distances[start_node] = 0
            heap = [(0, start_node)]

            while heap:
                current_distance, current_node = heapq.heappop(heap)
                if current_node == end_node:
                    break
                if current_distance > distances[current_node]:
                    continue
                for neighbor, weight in self.graph.get(current_node, []):
                    distance = current_distance + weight
                    if distance < distances[neighbor]:
                        distances[neighbor] = distance
                        previous[neighbor] = current_node
                        heapq.heappush(heap, (distance, neighbor))

            if distances[end_node] == float('inf'):
                return [], float('inf')

            path = []
            node = end_node
            while node is not None:
                path.append(node)
                node = previous[node]
            path.reverse()
            return path, distances[end_node]
        except Exception as e:
            logger.error(f"Failed to compute shortest path: {e}", exc_info=True)
            return [], float('inf')

    def shortest_path_distance(self, start_node, end_node):
        """Returns the shortest path distance by calling shortest_path_with_path."""
        return self.shortest_path_with_path(start_node, end_node)[1]