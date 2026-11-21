"""External data services: anime metadata, geocoding, and web search."""

from .anime_metadata import AnimeMetadata, AnimeMetadataService
from .geocoder import GeocodeResult, GeocoderService
from .search import SearchResult, WebPage, WebSearchService

__all__ = [
    "AnimeMetadata",
    "AnimeMetadataService",
    "GeocodeResult",
    "GeocoderService",
    "SearchResult",
    "WebPage",
    "WebSearchService",
]
