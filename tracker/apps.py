from django.apps import AppConfig
import logging

"""
    serves as a critical configuration and initialization
    point for the ”ROAD TRACKING PROJECT”. By leveraging the 'ready()' method, it
    ensures the 'RoadGraph' is preloaded, enhancing the application's readiness and efficiency
    for routing tasks.
"""

logger = logging.getLogger(__name__)

class TrackerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'tracker'

    def ready(self):
        logger.info("Initializing RoadGraph on app ready...")
        # Import here to avoid circular imports
        from .views import _initialize_road_graph
        _initialize_road_graph()
        logger.info("RoadGraph initialization triggered.")
