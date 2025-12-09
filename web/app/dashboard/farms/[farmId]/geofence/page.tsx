"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";

import { API_BASE } from "@/lib/api";

type LeafletModule = typeof import("leaflet");

type GeoFeature = {
  type: string;
  properties: Record<string, any>;
  geometry: any;
};

export default function FarmGeofenceBuilder() {
  const params = useParams<{ farmId: string }>();
  const farmId = params?.farmId;
  const [street, setStreet] = useState("");
  const [city, setCity] = useState("");
  const [province, setProvince] = useState("AB");
  const [postal, setPostal] = useState("");
  const [normalized, setNormalized] = useState("");
  const [lat, setLat] = useState<number | null>(null);
  const [lng, setLng] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [features, setFeatures] = useState<GeoFeature[]>([]);
  const [selectedIdx, setSelectedIdx] = useState<number | null>(null);
  const [searching, setSearching] = useState(false);

  const [leaflet, setLeaflet] = useState<LeafletModule | null>(null);
  const mapRef = useRef<LeafletModule["Map"] | null>(null);
  const layerRef = useRef<LeafletModule["LayerGroup"] | null>(null);
  const mapContainerRef = useRef<HTMLDivElement | null>(null);

  const center = useMemo(() => (lat != null && lng != null ? [lat, lng] as [number, number] : null), [lat, lng]);

  const handleLookup = async () => {
    setError(null);
    setNormalized("");
    setLat(null);
    setLng(null);

    if (!street.trim() || !city.trim() || !postal.trim()) {
      setError("Please fill street, city, and postal code.");
      return;
    }
    setLoading(true);
    try {
      const resp = await fetch(`${API_BASE}/geocode`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          street: street.trim(),
          city: city.trim(),
          province,
          postal_code: postal.trim(),
        }),
      });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new Error(err.detail || "Lookup failed");
      }
      const data = await resp.json();
      setLat(data.lat);
      setLng(data.lng);
      setNormalized(data.formatted || `${street}, ${city}, ${province} ${postal.trim()}`);
    } catch (err: any) {
      setError(err.message || "Failed to geocode");
    } finally {
      setLoading(false);
    }
  };

  const fetchPolygons = async () => {
    if (!center) {
      setError("Lookup coordinates first");
      return;
    }
    setSearching(true);
    setError(null);
    setFeatures([]);
    setSelectedIdx(null);
    try {
      const resp = await fetch(`${API_BASE}/geofence/search`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          lat: center[0],
          lng: center[1],
          province,
          radius_km: 10,
        }),
      });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new Error(err.detail || "Failed to find polygons");
      }
      const data = await resp.json();
      const items: GeoFeature[] = [];
      if (data.matched) items.push(data.matched);
      if (Array.isArray(data.candidates)) {
        data.candidates.forEach((c: GeoFeature) => {
          items.push(c);
        });
      }
      setFeatures(items);
      if (items.length) {
        setSelectedIdx(0);
      }
    } catch (err: any) {
      setError(err.message || "Failed to load polygons");
    } finally {
      setSearching(false);
    }
  };

  // init map once
  useEffect(() => {
    let cancelled = false;
    (async () => {
      if (leaflet) return;
      const L = await import("leaflet");
      await import("leaflet/dist/leaflet.css");
      // Fix default icon paths when bundled by Next.js
      delete (L.Icon.Default.prototype as any)._getIconUrl;
      L.Icon.Default.mergeOptions({
        iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
        iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
        shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
      });
      if (!cancelled) setLeaflet(L);
    })();
    return () => {
      cancelled = true;
    };
  }, [leaflet]);

  useEffect(() => {
    if (!leaflet || mapRef.current || !mapContainerRef.current) return;
    const L = leaflet;
    const map = L.map(mapContainerRef.current, {
      center: [53.5, -113.5],
      zoom: 11,
      preferCanvas: true,
    });
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: '© OpenStreetMap contributors',
    }).addTo(map);
    mapRef.current = map;
  }, [leaflet]);

  // update center & radius marker
  useEffect(() => {
    if (!leaflet || !mapRef.current || !center) return;
    const L = leaflet;
    const map = mapRef.current;
    const marker = L.marker(center).addTo(map);
    const circle = L.circle(center, { radius: 10_000, color: "#22c55e", fillColor: "#22c55e", fillOpacity: 0.08 }).addTo(map);
    map.setView(center, 12);
    return () => {
      map.removeLayer(marker);
      map.removeLayer(circle);
    };
  }, [center]);

  // render geojson
  useEffect(() => {
    if (!leaflet || !mapRef.current) return;
    const L = leaflet;
    const map = mapRef.current;
    if (!layerRef.current) {
      layerRef.current = L.layerGroup().addTo(map);
    }
    const layerGroup = layerRef.current;
    layerGroup.clearLayers();
    if (!features.length) return;

    features.forEach((feat, idx) => {
      const layer = L.geoJSON(feat, {
        style: {
          color: idx === selectedIdx ? "#38bdf8" : "#8b5cf6",
          weight: idx === selectedIdx ? 3 : 1.5,
          fillOpacity: 0.1,
        },
      });
      layer.on("click", () => setSelectedIdx(idx));
      layer.addTo(layerGroup);
    });

    const all = L.featureGroup(features.map((f) => L.geoJSON(f)));
    try {
      map.fitBounds(all.getBounds().pad(0.15));
    } catch {
      /* noop */
    }
  }, [features, selectedIdx]);

  return (
    <main className="mx-auto max-w-5xl px-6 py-10 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <Link href={`/dashboard/farms/${farmId}`} className="text-sm text-blue-400 hover:underline">
            ← Back to farm
          </Link>
          <h1 className="mt-2 text-3xl font-bold text-white">Geofence builder</h1>
          <p className="text-sm text-gray-400">
            Enter a farm address, select the province dataset (e.g., alberta.gpkg in /resources/geofence/), and pick a polygon.
          </p>
        </div>
      </div>

      <section className="card space-y-4">
        <div className="grid gap-3 md:grid-cols-3 md:items-end">
          <div className="md:col-span-2 grid gap-3 md:grid-cols-2">
            <div>
              <label className="text-sm text-gray-400" htmlFor="street">Street</label>
              <input
                id="street"
                type="text"
                value={street}
                onChange={(e) => setStreet(e.target.value)}
                placeholder="123 King St W"
                className="mt-1 w-full rounded-md border border-gray-700 bg-gray-900 px-4 py-2 text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="text-sm text-gray-400" htmlFor="city">City</label>
              <input
                id="city"
                type="text"
                value={city}
                onChange={(e) => setCity(e.target.value)}
                placeholder="Toronto"
                className="mt-1 w-full rounded-md border border-gray-700 bg-gray-900 px-4 py-2 text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          <div>
            <label className="text-sm text-gray-400" htmlFor="province">Province</label>
            <select
              id="province"
              value={province}
              onChange={(e) => setProvince(e.target.value)}
              className="mt-1 w-full rounded-md border border-gray-700 bg-gray-900 px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="AB">Alberta</option>
              <option value="BC">British Columbia</option>
              <option value="MB">Manitoba</option>
              <option value="NB">New Brunswick</option>
              <option value="NL">Newfoundland and Labrador</option>
              <option value="NS">Nova Scotia</option>
              <option value="NT">Northwest Territories</option>
              <option value="NU">Nunavut</option>
              <option value="ON">Ontario</option>
              <option value="PE">Prince Edward Island</option>
              <option value="QC">Quebec</option>
              <option value="SK">Saskatchewan</option>
              <option value="YT">Yukon</option>
            </select>
          </div>

          <div>
            <label className="text-sm text-gray-400" htmlFor="postal">Postal code</label>
            <input
              id="postal"
              type="text"
              value={postal}
              onChange={(e) => setPostal(e.target.value.toUpperCase())}
              placeholder="e.g. T5J 0N3"
              className="mt-1 w-full rounded-md border border-gray-700 bg-gray-900 px-4 py-2 text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div className="md:col-span-3 flex justify-end">
            <button
              type="button"
              onClick={handleLookup}
              disabled={loading}
              className="mt-6 rounded-md bg-blue-600 px-4 py-2 text-white hover:bg-blue-500 disabled:opacity-60"
            >
              {loading ? "Looking up..." : "Get coordinates"}
            </button>
          </div>
        </div>
        {error && <p className="text-sm text-red-400">{error}</p>}
        {lat != null && lng != null && (
          <div className="rounded-md border border-emerald-500 bg-emerald-900/20 p-3 text-sm text-emerald-100 space-y-1">
            <div>Latitude: {lat}</div>
            <div>Longitude: {lng}</div>
            {normalized && <div>Location: {normalized}</div>}
          </div>
        )}

        <div className="border-t border-gray-800 pt-4">
          <p className="text-sm text-gray-400 mb-2">Already know the coordinates? Enter them here.</p>
          <div className="grid gap-3 md:grid-cols-3 md:items-end">
            <div>
              <label className="text-sm text-gray-400" htmlFor="lat">Latitude</label>
              <input
                id="lat"
                type="number"
                value={lat ?? ""}
                onChange={(e) => setLat(e.target.value === "" ? null : Number(e.target.value))}
                placeholder="e.g. 52.0422"
                className="mt-1 w-full rounded-md border border-gray-700 bg-gray-900 px-4 py-2 text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="text-sm text-gray-400" htmlFor="lng">Longitude</label>
              <input
                id="lng"
                type="number"
                value={lng ?? ""}
                onChange={(e) => setLng(e.target.value === "" ? null : Number(e.target.value))}
                placeholder="e.g. -113.9455"
                className="mt-1 w-full rounded-md border border-gray-700 bg-gray-900 px-4 py-2 text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div className="md:col-span-1 flex justify-end">
              <button
                type="button"
                onClick={() => setNormalized("")}
                className="mt-6 rounded-md bg-slate-700 px-4 py-2 text-white hover:bg-slate-600"
              >
                Use coordinates
              </button>
            </div>
          </div>
        </div>
      </section>

      <section className="card space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold text-white">Map & polygon picker</h2>
            <p className="text-sm text-gray-400">
              We look up polygons within 10 km of the resolved point. Click a polygon to select it.
            </p>
          </div>
          <button
            type="button"
            onClick={fetchPolygons}
            disabled={!center || searching}
            className="rounded-md bg-blue-600 px-4 py-2 text-white hover:bg-blue-500 disabled:opacity-60"
          >
            {searching ? "Searching..." : "Find polygons (10 km)"}
          </button>
        </div>
        <p className="text-sm text-gray-400">
          Province dataset is loaded from <code>resources/geofence/{province.toLowerCase()}.gpkg</code>. Ensure that file is present on the server.
        </p>
        <div
          ref={mapContainerRef}
          className="h-96 rounded-lg border border-gray-800 bg-gray-900/60"
        />

        {features.length > 0 && (
          <div className="space-y-2 text-sm text-gray-200">
            <div className="font-semibold">Nearby polygons</div>
            <ul className="space-y-1">
              {features.map((f, idx) => (
                <li key={idx} className="flex items-center justify-between rounded-md border border-gray-800 bg-gray-900 px-3 py-2">
                  <div>
                    <div className="font-medium">Polygon {idx + 1}</div>
                    <div className="text-gray-400">
                      Distance: {Math.round((f.properties?.distance_m ?? 0))} m
                    </div>
                  </div>
                  <button
                    className={`rounded-md px-3 py-1 text-sm ${
                      selectedIdx === idx ? "bg-emerald-600 text-white" : "bg-white/10 text-white"
                    }`}
                    onClick={() => setSelectedIdx(idx)}
                  >
                    {selectedIdx === idx ? "Selected" : "Select"}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}
      </section>

      <section className="card space-y-3">
        <h2 className="text-xl font-semibold text-white">Selection summary</h2>
        <p className="text-sm text-gray-400">
          After integrating the map, capture the selected polygon geometry and POST it to the farm geofence endpoint to save.
        </p>
        <ul className="text-sm text-gray-300 list-disc pl-5 space-y-1">
          <li>Province dataset: {province}</li>
          <li>Address: {normalized || "Not set"}</li>
          <li>Selected polygon: {selectedIdx != null ? `Polygon ${selectedIdx + 1}` : "None yet"}</li>
        </ul>
      </section>
    </main>
  );
}
