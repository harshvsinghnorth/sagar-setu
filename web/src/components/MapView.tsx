import { useEffect, useRef } from "react";
import * as maplibregl from "maplibre-gl";
import type { Map as MLMap, LngLatBoundsLike } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import type { AskResult, StaticGeo } from "../api";

// Free OSM raster tiles: no token, nothing to fail in a demo (CLAUDE.md).
const STYLE: maplibregl.StyleSpecification = {
  version: 8,
  sources: {
    osm: {
      type: "raster",
      tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
      tileSize: 256,
      attribution: "© OpenStreetMap contributors",
    },
  },
  layers: [{ id: "osm", type: "raster", source: "osm" }],
};

const EMPTY: GeoJSON.FeatureCollection = { type: "FeatureCollection", features: [] };
let markers: maplibregl.Marker[] = [];

function label(map: MLMap, lngLat: [number, number], text: string, cls: string) {
  const el = document.createElement("div");
  el.className = `mlabel ${cls}`;
  el.textContent = text;
  markers.push(new maplibregl.Marker({ element: el, anchor: "bottom", offset: [0, -10] }).setLngLat(lngLat).addTo(map));
}

function setData(map: MLMap, id: string, data: GeoJSON.FeatureCollection | GeoJSON.Feature) {
  const src = map.getSource(id) as maplibregl.GeoJSONSource | undefined;
  if (src) src.setData(data);
}

export default function MapView({ geo, result }: { geo: StaticGeo | null; result: AskResult | null }) {
  const el = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MLMap | null>(null);
  const ready = useRef(false);

  useEffect(() => {
    if (!el.current || mapRef.current) return;
    const map = new maplibregl.Map({ container: el.current, style: STYLE, center: [78, 14], zoom: 4.2, attributionControl: { compact: true } });
    map.addControl(new maplibregl.NavigationControl({ showCompass: true }), "top-right");
    map.on("load", () => {
      const add = (id: string, data: GeoJSON.FeatureCollection | GeoJSON.Feature = EMPTY) => map.addSource(id, { type: "geojson", data });
      add("eez"); add("imbl"); add("harbours"); add("pfz"); add("bearings"); add("track"); add("crossing"); add("location"); add("imbl-closest"); add("route"); add("route-direct");
      map.addLayer({ id: "eez-line", type: "line", source: "eez", paint: { "line-color": "#52514e", "line-width": 1, "line-opacity": 0.7 } });
      map.addLayer({ id: "imbl-line", type: "line", source: "imbl", paint: { "line-color": "#eb6834", "line-width": 2, "line-dasharray": [3, 2] } });
      map.addLayer({ id: "harbours-pt", type: "circle", source: "harbours", paint: { "circle-radius": 4, "circle-color": "#2a78d6", "circle-stroke-color": "#fff", "circle-stroke-width": 1 } });
      map.addLayer({ id: "pfz-line", type: "line", source: "pfz", paint: { "line-color": "#1baf7a", "line-width": 4, "line-opacity": 0.9 } });
      map.addLayer({ id: "bearing-line", type: "line", source: "bearings", paint: { "line-color": "#1baf7a", "line-width": 1.5, "line-dasharray": [2, 2] } });
      map.addLayer({ id: "imbl-closest-line", type: "line", source: "imbl-closest", paint: { "line-color": "#eb6834", "line-width": 1.5, "line-dasharray": [1, 2] } });
      map.addLayer({ id: "track-line", type: "line", source: "track", paint: { "line-color": "#2a78d6", "line-width": 3 } });
      // The straight line for comparison (red when it would cross the IMBL), then the route over it.
      map.addLayer({ id: "route-direct-line", type: "line", source: "route-direct", paint: { "line-color": ["case", ["get", "crosses"], "#e34948", "#8a8984"], "line-width": 1.5, "line-dasharray": [2, 3] } });
      map.addLayer({ id: "route-casing", type: "line", source: "route", layout: { "line-join": "round", "line-cap": "round" }, paint: { "line-color": "#ffffff", "line-width": 7 } });
      map.addLayer({ id: "route-line", type: "line", source: "route", layout: { "line-join": "round", "line-cap": "round" }, paint: { "line-color": "#7a3ccf", "line-width": 4 } });
      map.addLayer({ id: "crossing-pt", type: "circle", source: "crossing", paint: { "circle-radius": 8, "circle-color": "#e34948", "circle-stroke-color": "#fff", "circle-stroke-width": 2 } });
      map.addLayer({ id: "location-pt", type: "circle", source: "location", paint: { "circle-radius": 7, "circle-color": "#2a78d6", "circle-stroke-color": "#fff", "circle-stroke-width": 2 } });
      ready.current = true;
      if (geo) applyStatic(map, geo);
    });
    mapRef.current = map;
    return () => { map.remove(); mapRef.current = null; ready.current = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (map && ready.current && geo) applyStatic(map, geo);
  }, [geo]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready.current) return;
    applyResult(map, result);
  }, [result]);

  return <div ref={el} className="map" />;
}

function applyStatic(map: MLMap, geo: StaticGeo) {
  setData(map, "eez", geo.eez);
  setData(map, "imbl", geo.imbl);
  setData(map, "harbours", geo.harbours);
}

function applyResult(map: MLMap, r: AskResult | null) {
  for (const mk of markers) mk.remove();
  markers = [];
  const m = r?.map;
  if (!m || !m.location) {
    for (const id of ["pfz", "bearings", "track", "crossing", "location", "imbl-closest", "route", "route-direct"]) setData(map, id, EMPTY);
    return;
  }
  const route = m.route?.found && m.route.points.length > 1 ? m.route : null;
  const here: [number, number] = [m.location.lon, m.location.lat];
  setData(map, "location", { type: "FeatureCollection", features: [{ type: "Feature", properties: { name: m.location.name }, geometry: { type: "Point", coordinates: here } }] });
  setData(map, "pfz", m.pfz ?? EMPTY);
  setData(map, "bearings", {
    type: "FeatureCollection",
    features: (m.pfz_bearings ?? []).map((b) => ({ type: "Feature", properties: { rank: b.rank }, geometry: { type: "LineString", coordinates: [here, b.to] } })),
  });
  setData(map, "imbl-closest", m.nearest_imbl && m.nearest_imbl.distance_km < 120
    ? { type: "FeatureCollection", features: [{ type: "Feature", properties: {}, geometry: { type: "LineString", coordinates: [here, m.nearest_imbl.closest] } }] }
    : EMPTY);
  setData(map, "track", m.track ? { type: "FeatureCollection", features: [{ type: "Feature", properties: {}, geometry: { type: "LineString", coordinates: m.track.points } }] } : EMPTY);
  setData(map, "route", route
    ? { type: "FeatureCollection", features: [{ type: "Feature", properties: {}, geometry: { type: "LineString", coordinates: route.points } }] }
    : EMPTY);
  setData(map, "route-direct", m.route
    ? { type: "FeatureCollection", features: [{ type: "Feature", properties: { crosses: m.route.direct_crosses_border }, geometry: { type: "LineString", coordinates: [here, m.route.dest] } }] }
    : EMPTY);
  setData(map, "crossing", m.track?.crossing
    ? { type: "FeatureCollection", features: [{ type: "Feature", properties: { label: `${m.track.boundary} · ${m.track.minutes} min` }, geometry: { type: "Point", coordinates: m.track.crossing } }] }
    : EMPTY);

  label(map, here, m.location.name, "loc");
  for (const b of m.pfz_bearings ?? []) label(map, b.to, `PFZ #${b.rank} · ${b.distance_km} km ${b.compass}`, "pfz");
  if (m.track?.crossing) label(map, m.track.crossing, `${m.track.boundary} · ${m.track.minutes} min`, "cross");
  if (m.nearest_imbl && m.nearest_imbl.distance_km < 120 && !m.track?.crossing) label(map, m.nearest_imbl.closest, `${m.nearest_imbl.name} · ${m.nearest_imbl.distance_km} km ${m.nearest_imbl.compass}`, "cross");
  if (m.route) {
    const h = Math.floor(m.route.eta_min / 60), mins = Math.round(m.route.eta_min % 60);
    label(map, m.route.dest, route
      ? `Route to ${m.route.destination} · ${m.route.distance_km} km · ${h} h ${mins} min`
      : `${m.route.destination} · no route: ${m.route.reason}`, route ? "route" : "cross");
  }

  // Fit to everything drawn for this answer.
  const pts: [number, number][] = [here];
  for (const p of route?.points ?? []) pts.push(p);
  if (m.route) pts.push(m.route.dest);
  for (const b of m.pfz_bearings ?? []) pts.push(b.to);
  for (const p of m.track?.points ?? []) pts.push(p);
  if (m.track?.crossing) pts.push(m.track.crossing);
  if (m.nearest_imbl && m.nearest_imbl.distance_km < 120) pts.push(m.nearest_imbl.closest);
  if (pts.length === 1) {
    map.easeTo({ center: here, zoom: 8.5, duration: 800 });
    return;
  }
  const lons = pts.map((p) => p[0]);
  const lats = pts.map((p) => p[1]);
  const bounds: LngLatBoundsLike = [[Math.min(...lons), Math.min(...lats)], [Math.max(...lons), Math.max(...lats)]];
  map.fitBounds(bounds, { padding: 70, maxZoom: 10, duration: 800 });
}
