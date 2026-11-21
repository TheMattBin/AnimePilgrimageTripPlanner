import { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import type { DailyItinerary, PilgrimageLocation } from "../types/api";

interface PilgrimageMapProps {
  itineraries: DailyItinerary[];
  fallbackLocations: PilgrimageLocation[];
}

const DAY_COLORS = ["#e11d48", "#2563eb", "#059669", "#d97706", "#7c3aed", "#0891b2"];

function escapeHtml(raw: string): string {
  return raw
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function createPinIcon(label: string, color: string): L.DivIcon {
  return L.divIcon({
    className: "pilgrimage-pin-wrapper",
    html: `<div style="background:${color};color:#fff;width:28px;height:28px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:12px;border:2px solid #fff;box-shadow:0 2px 6px rgba(0,0,0,0.35);">${escapeHtml(label)}</div>`,
    iconSize: [28, 28],
    iconAnchor: [14, 14],
    popupAnchor: [0, -14],
  });
}

export function PilgrimageMap({ itineraries, fallbackLocations }: PilgrimageMapProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<L.Map | null>(null);
  const layerGroupRef = useRef<L.LayerGroup | null>(null);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    const map = L.map(containerRef.current, {
      center: [35.6812, 139.7671],
      zoom: 6,
      scrollWheelZoom: true,
    });
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "&copy; OpenStreetMap contributors",
      maxZoom: 19,
    }).addTo(map);

    mapRef.current = map;
    layerGroupRef.current = L.layerGroup().addTo(map);

    return () => {
      map.remove();
      mapRef.current = null;
      layerGroupRef.current = null;
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    const layer = layerGroupRef.current;
    if (!map || !layer) return;

    layer.clearLayers();
    const boundsPoints: L.LatLngExpression[] = [];

    if (itineraries.length > 0) {
      itineraries.forEach((day) => {
        const color = DAY_COLORS[(day.day - 1) % DAY_COLORS.length];
        const dayCoords: L.LatLngExpression[] = [];

        day.stops.forEach((stop) => {
          const coords = stop.location.coordinates;
          if (!coords) return;
          const latlng: L.LatLngExpression = [coords.lat, coords.lng];
          dayCoords.push(latlng);
          boundsPoints.push(latlng);

          const jp = stop.location.japanese_name
            ? ` <span style="color:#64748b">(${escapeHtml(stop.location.japanese_name)})</span>`
            : "";
          const scene = stop.location.scene_description
            ? `<div style="margin-top:4px;"><strong>Scene:</strong> ${escapeHtml(stop.location.scene_description)}</div>`
            : "";
          const time = stop.arrival_time
            ? `<div style="font-size:12px;color:#475569;">Day ${day.day} · ${escapeHtml(stop.arrival_time)}–${escapeHtml(stop.departure_time)}</div>`
            : "";

          L.marker(latlng, { icon: createPinIcon(`${day.day}.${stop.order}`, color) })
            .bindPopup(
              `<div style="min-width:190px;font-family:system-ui,sans-serif;">
                <div style="font-weight:700;font-size:14px;">${escapeHtml(stop.location.name)}${jp}</div>
                ${time}
                ${scene}
              </div>`
            )
            .addTo(layer);
        });

        if (dayCoords.length >= 2) {
          L.polyline(dayCoords, {
            color,
            weight: 3,
            opacity: 0.8,
            dashArray: "6 6",
          }).addTo(layer);
        }
      });
    } else {
      fallbackLocations.forEach((loc, idx) => {
        if (!loc.coordinates) return;
        const latlng: L.LatLngExpression = [loc.coordinates.lat, loc.coordinates.lng];
        boundsPoints.push(latlng);
        L.marker(latlng, { icon: createPinIcon(String(idx + 1), DAY_COLORS[0]) })
          .bindPopup(`<strong>${escapeHtml(loc.name)}</strong>`)
          .addTo(layer);
      });
    }

    if (boundsPoints.length === 1) {
      map.setView(boundsPoints[0], 14);
    } else if (boundsPoints.length > 1) {
      map.fitBounds(L.latLngBounds(boundsPoints), { padding: [36, 36], maxZoom: 15 });
    }
  }, [itineraries, fallbackLocations]);

  return (
    <div className="card map-card">
      <div className="map-header">
        <h2>Pilgrimage Route Map</h2>
        {itineraries.length > 0 && (
          <div className="legend">
            {itineraries.map((day) => (
              <span key={day.day} className="legend-item">
                <span
                  className="legend-dot"
                  style={{ background: DAY_COLORS[(day.day - 1) % DAY_COLORS.length] }}
                />
                Day {day.day}
              </span>
            ))}
          </div>
        )}
      </div>
      <div ref={containerRef} className="leaflet-container-box" />
    </div>
  );
}
