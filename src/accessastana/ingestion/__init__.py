"""Ingestion module: one loader (Strategy) per data source."""

from __future__ import annotations

from accessastana.ingestion.base import BaseLoader


def available_loaders() -> dict[str, type[BaseLoader]]:
    """Name → loader class, in dependency order. Imported lazily so the API
    image (without osmium/osmnx) can still import the package."""
    from accessastana.ingestion.kontur import KonturLoader
    from accessastana.ingestion.open_meteo import OpenMeteoLoader

    loaders: dict[str, type[BaseLoader]] = {}
    try:
        from accessastana.ingestion.osm_boundary import OsmBoundaryLoader
        from accessastana.ingestion.osm_network import OsmNetworkLoader
        from accessastana.ingestion.osm_pois import OsmPoiLoader

        loaders |= {c.name: c for c in (OsmBoundaryLoader, OsmNetworkLoader, OsmPoiLoader)}
    except ImportError:  # osmium not installed (API image)
        pass
    loaders |= {c.name: c for c in (KonturLoader, OpenMeteoLoader)}
    return loaders
