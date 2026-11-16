/**
 * Builds the list of deck.gl layers from the current data.
 * Kept as a plain function (no React) so it is easy to read and test.
 * Layer order = drawing order: later layers are drawn on top.
 */
import type { LayersList } from '@deck.gl/core';
import { GeoJsonLayer, ScatterplotLayer, TextLayer } from '@deck.gl/layers';
import { H3HexagonLayer } from '@deck.gl/geo-layers';
import type { Feature, Point } from 'geojson';
import type {
  AccessibilityResponse,
  ChangedCell,
  DistrictsGeoJSON,
  OptimizeLocation,
  PoisGeoJSON,
} from '../api/client';
import type { ProposedFacility } from '../state/appState';
import { colorFor, hexToRgba, type Metric } from '../lib/colors';

export type PoiFeature = PoisGeoJSON['features'][number];

export interface LayerInput {
  accessibility?: AccessibilityResponse;
  districts?: DistrictsGeoJSON;
  pois?: PoisGeoJSON;
  removeIds?: number[];
  proposed?: ProposedFacility[];
  changedCells?: ChangedCell[];
  optimized?: OptimizeLocation[];
}

const BLUE = hexToRgba('#2563eb');
const ORANGE = hexToRgba('#f97316');
const RED = hexToRgba('#dc2626');
const WHITE = hexToRgba('#ffffff');
const DARK = hexToRgba('#111827');

export function buildLayers(input: LayerInput): LayersList {
  const layers: LayersList = [];
  const acc = input.accessibility;
  const metric: Metric = acc?.metric ?? 'minutes';
  const maxMinutes = acc?.max_minutes ?? 15;

  if (acc) {
    layers.push(
      new H3HexagonLayer({
        id: 'access',
        data: acc.cells,
        getHexagon: (d) => d.h3,
        getFillColor: (d) => colorFor(d.value, metric, maxMinutes, 170),
        extruded: false,
        stroked: false,
        pickable: true,
        // Colours depend on these values, not only on the data array.
        updateTriggers: { getFillColor: [metric, maxMinutes] },
      }),
    );
  }

  if (input.districts) {
    layers.push(
      new GeoJsonLayer({
        id: 'districts',
        data: input.districts,
        filled: false,
        stroked: true,
        getLineColor: [55, 65, 81, 220],
        lineWidthMinPixels: 1.5,
        pickable: false,
      }),
    );
  }

  // Scenario result: cells whose time changed, filled with the AFTER value and outlined.
  if (input.changedCells?.length) {
    layers.push(
      new H3HexagonLayer({
        id: 'changed',
        data: input.changedCells,
        getHexagon: (d) => d.h3,
        getFillColor: (d) => colorFor(d.after, 'minutes', maxMinutes, 235),
        stroked: true,
        getLineColor: DARK,
        lineWidthUnits: 'pixels',
        getLineWidth: 2,
        extruded: false,
        pickable: true,
        updateTriggers: { getFillColor: [maxMinutes] },
      }),
    );
  }

  if (input.pois) {
    const removeIds = input.removeIds ?? [];
    layers.push(
      new ScatterplotLayer<PoiFeature>({
        id: 'pois',
        data: input.pois.features,
        getPosition: (f: Feature<Point>) => f.geometry.coordinates as [number, number],
        radiusUnits: 'pixels',
        getRadius: (f) => (removeIds.includes(f.properties.id) ? 7 : 4),
        getFillColor: (f) => (removeIds.includes(f.properties.id) ? RED : DARK),
        stroked: true,
        getLineColor: WHITE,
        lineWidthMinPixels: 1,
        pickable: true,
        updateTriggers: { getRadius: [removeIds], getFillColor: [removeIds] },
      }),
    );
  }

  if (input.proposed?.length) {
    layers.push(
      new ScatterplotLayer<ProposedFacility>({
        id: 'proposed',
        data: input.proposed,
        getPosition: (d) => [d.lon, d.lat],
        radiusUnits: 'pixels',
        getRadius: 8,
        getFillColor: BLUE,
        stroked: true,
        getLineColor: WHITE,
        lineWidthMinPixels: 2,
        pickable: true,
      }),
    );
  }

  if (input.optimized?.length) {
    const located = input.optimized.map((d, i) => ({ ...d, rank: i + 1 }));
    layers.push(
      new ScatterplotLayer<(typeof located)[number]>({
        id: 'optimized',
        data: located,
        getPosition: (d) => [d.lon, d.lat],
        radiusUnits: 'pixels',
        getRadius: 10,
        getFillColor: ORANGE,
        stroked: true,
        getLineColor: WHITE,
        lineWidthMinPixels: 2,
        pickable: true,
      }),
      new TextLayer<(typeof located)[number]>({
        id: 'optimized-labels',
        data: located,
        getPosition: (d) => [d.lon, d.lat],
        getText: (d) => String(d.rank),
        getSize: 12,
        getColor: WHITE,
        fontWeight: 700,
      }),
    );
  }

  return layers;
}
