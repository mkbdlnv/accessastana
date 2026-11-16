import { useEffect, useRef, useState, type ReactNode } from 'react';
import { AttributionControl, Map as MapLibreMap, NavigationControl, ScaleControl, setWorkerUrl } from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
// Vite emits the worker file as a separate asset and gives us its URL.
// MapLibre would otherwise look for the worker next to its own module,
// which does not exist after bundling.
import maplibreWorkerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?url';
import { MapboxOverlay } from '@deck.gl/mapbox';
import type { LayersList, PickingInfo } from '@deck.gl/core';

setWorkerUrl(new URL(maplibreWorkerUrl, window.location.href).href);

/** Free, keyless vector basemap built from OpenStreetMap data. */
const BASEMAP_STYLE = 'https://tiles.openfreemap.org/styles/positron';
const DEFAULT_CENTER: [number, number] = [71.43, 51.13]; // Astana, used until /cities answers
const DEFAULT_ZOOM = 10.5;

interface Props {
  center: [number, number] | null;
  layers: LayersList;
  /** Called for every click on the map; `info.object` is set if a deck.gl object was hit. */
  onClick?: (info: PickingInfo) => void;
  renderTooltip: (info: PickingInfo) => ReactNode;
  /** CSS cursor over the map, e.g. "crosshair" in scenario edit mode */
  cursor?: string;
  children?: ReactNode;
}

/**
 * MapLibre basemap + deck.gl layers.
 *
 * deck.gl is attached as a MapLibre "control" (MapboxOverlay). In overlaid mode
 * (interleaved: false) deck.gl draws on its own canvas on top of the map and
 * its camera is kept in sync with the map automatically. Mouse events are
 * forwarded from the map to deck.gl, so picking (hover/click) works.
 */
export function MapView({ center, layers, onClick, renderTooltip, cursor, children }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const overlayRef = useRef<MapboxOverlay | null>(null);
  const [hover, setHover] = useState<PickingInfo | null>(null);
  const [mapError, setMapError] = useState<string | null>(null);

  // Keep the latest click handler in a ref so the overlay callback never goes stale.
  const onClickRef = useRef(onClick);
  useEffect(() => {
    onClickRef.current = onClick;
  });

  // Create the map once.
  useEffect(() => {
    if (!containerRef.current) return;
    let map: MapLibreMap;
    try {
      map = new MapLibreMap({
        container: containerRef.current,
        style: BASEMAP_STYLE,
        center: DEFAULT_CENTER,
        zoom: DEFAULT_ZOOM,
        attributionControl: false, // added below with our own strings
      });
    } catch (e) {
      // e.g. WebGL not available
      queueMicrotask(() => setMapError(e instanceof Error ? e.message : String(e)));
      return;
    }
    map.addControl(
      new AttributionControl({
        compact: false,
        customAttribution: [
          '<a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">© OpenStreetMap contributors</a>',
          '<a href="https://openfreemap.org" target="_blank" rel="noopener">© OpenFreeMap</a>',
        ],
      }),
      'bottom-right',
    );
    map.addControl(new NavigationControl({ showCompass: false }), 'top-right');
    map.addControl(new ScaleControl({ unit: 'metric' }), 'bottom-left');

    const overlay = new MapboxOverlay({
      interleaved: false,
      layers: [],
      onHover: (info) => setHover(info.object ? info : null),
      onClick: (info) => onClickRef.current?.(info),
    });
    map.addControl(overlay);

    mapRef.current = map;
    overlayRef.current = overlay;
    return () => {
      overlayRef.current = null;
      mapRef.current = null;
      map.remove(); // also removes the overlay control
    };
  }, []);

  // Fly to the selected city.
  const lon = center?.[0];
  const lat = center?.[1];
  useEffect(() => {
    if (lon === undefined || lat === undefined) return;
    mapRef.current?.jumpTo({ center: [lon, lat] });
  }, [lon, lat]);

  // Push new layers to deck.gl. Layers are cheap descriptors; deck.gl diffs them by id.
  useEffect(() => {
    overlayRef.current?.setProps({ layers });
  }, [layers]);

  useEffect(() => {
    const canvas = mapRef.current?.getCanvas();
    if (canvas) canvas.style.cursor = cursor ?? (hover ? 'pointer' : '');
  }, [cursor, hover]);

  const tooltip = hover ? renderTooltip(hover) : null;

  return (
    <div className="map-wrap">
      <div ref={containerRef} className="map" />
      {mapError && <div className="map-error">Map error: {mapError}</div>}
      {hover && tooltip && (
        <div className="tooltip" style={{ left: hover.x + 12, top: hover.y + 12 }}>
          {tooltip}
        </div>
      )}
      {children}
    </div>
  );
}
