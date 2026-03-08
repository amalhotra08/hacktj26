"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import DeckGL from "@deck.gl/react";
import type { PickingInfo, MapViewState } from "@deck.gl/core";
import { AmbientLight, LightingEffect, PointLight } from "@deck.gl/core";
import { ArcLayer, ColumnLayer, ScatterplotLayer, TextLayer } from "@deck.gl/layers";

type InterventionType =
  | "bike_lane"
  | "bus_lane"
  | "tree_planting"
  | "pedestrianization"
  | "street_redesign"
  | "solar_panel"
  | "flood_mitigation";

type ZoneSnapshot = {
  id: number;
  name: string;
  position: [number, number];
  baseline_score: number;
  proposal_score: number;
  change: number;
};

type FlowSnapshot = {
  source: [number, number];
  target: [number, number];
  weight: number;
};

type SimulationResponse = {
  metadata: {
    city?: string;
    latitude: number;
    longitude: number;
    generated_at: string;
    intervention_count: number;
  };
  baseline_metrics: Record<string, number>;
  proposal_metrics: Record<string, number>;
  deltas: Record<string, number>;
  zones: ZoneSnapshot[];
  flows: FlowSnapshot[];
  intervention_summary: Array<{
    type: InterventionType;
    intensity: number;
    metric_contribution: Record<string, number>;
  }>;
};

const API_BASE = process.env.NEXT_PUBLIC_SIM_API ?? "http://localhost:8000";

const INTERVENTION_CATALOG: Array<{ key: InterventionType; label: string }> = [
  { key: "bike_lane", label: "Bike Lanes" },
  { key: "bus_lane", label: "Bus Priority" },
  { key: "tree_planting", label: "Tree Planting" },
  { key: "pedestrianization", label: "Pedestrian Streets" },
  { key: "street_redesign", label: "Street Redesign" },
  { key: "solar_panel", label: "Solar Install" },
  { key: "flood_mitigation", label: "Flood Mitigation" },
];

const METRIC_LABELS: Record<string, string> = {
  traffic_flow: "Traffic",
  carbon: "Carbon",
  safety: "Safety",
  urban_heat: "Heat",
  resilience: "Resilience",
};

const DEFAULT_VIEW: MapViewState = {
  longitude: -73.98,
  latitude: 40.74,
  zoom: 11.1,
  pitch: 52,
  bearing: 24,
};

function formatMetric(value: number) {
  return Number.isFinite(value) ? value.toFixed(1) : "-";
}

export default function ChaosDeckScene() {
  const [city, setCity] = useState("New York");
  const [latitude, setLatitude] = useState("40.7400");
  const [longitude, setLongitude] = useState("-73.9800");
  const [viewState, setViewState] = useState<MapViewState>(DEFAULT_VIEW);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [simulation, setSimulation] = useState<SimulationResponse | null>(null);
  const [interventions, setInterventions] = useState<Record<InterventionType, number>>({
    bike_lane: 2,
    bus_lane: 1,
    tree_planting: 2,
    pedestrianization: 0,
    street_redesign: 1,
    solar_panel: 0,
    flood_mitigation: 0,
  });

  const runSimulation = useCallback(async () => {
    const lat = Number(latitude);
    const lon = Number(longitude);

    if (!Number.isFinite(lat) || !Number.isFinite(lon)) {
      setError("Latitude and longitude must be valid numbers.");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const selected = INTERVENTION_CATALOG.filter(({ key }) => interventions[key] > 0).map(
        ({ key }) => ({
          type: key,
          intensity: interventions[key],
        })
      );

      const response = await fetch(`${API_BASE}/simulate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          city,
          latitude: lat,
          longitude: lon,
          interventions: selected,
          include_raw_report: false,
        }),
      });

      if (!response.ok) {
        throw new Error(`Simulation API returned ${response.status}`);
      }

      const data: SimulationResponse = await response.json();
      setSimulation(data);
      setViewState((prev) => ({
        ...prev,
        latitude: data.metadata.latitude,
        longitude: data.metadata.longitude,
      }));
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unknown request failure";
      setError(`Failed to run simulation: ${message}`);
    } finally {
      setLoading(false);
    }
  }, [city, interventions, latitude, longitude]);

  useEffect(() => {
    void runSimulation();
  }, [runSimulation]);

  const effects = useMemo(() => {
    const ambientLight = new AmbientLight({ color: [245, 210, 170], intensity: 1.0 });
    const hotLight = new PointLight({ color: [255, 85, 30], intensity: 2.2, position: [-73.95, 40.78, 6000] });
    const coolLight = new PointLight({ color: [30, 190, 255], intensity: 1.2, position: [-74.08, 40.67, 5000] });
    return [new LightingEffect({ ambientLight, hotLight, coolLight })];
  }, []);

  const zones = simulation?.zones ?? [];
  const flows = simulation?.flows ?? [];

  const layers = useMemo(() => {
    const topLabels = [...zones].sort((a, b) => b.change - a.change).slice(0, 14);

    return [
      new ColumnLayer<ZoneSnapshot>({
        id: "baseline-columns",
        data: zones,
        pickable: false,
        extruded: true,
        diskResolution: 16,
        radius: 250,
        getPosition: (d) => d.position,
        getElevation: (d) => d.baseline_score * 42,
        getFillColor: [72, 132, 255, 140],
        material: {
          ambient: 0.24,
          diffuse: 0.72,
          shininess: 40,
          specularColor: [130, 180, 255],
        },
      }),
      new ColumnLayer<ZoneSnapshot>({
        id: "proposal-columns",
        data: zones,
        pickable: true,
        extruded: true,
        diskResolution: 16,
        radius: 160,
        getPosition: (d) => d.position,
        getElevation: (d) => d.proposal_score * 42,
        getFillColor: (d) => (d.change >= 0 ? [255, 145, 75, 220] : [255, 75, 90, 220]),
        material: {
          ambient: 0.3,
          diffuse: 0.65,
          shininess: 60,
          specularColor: [255, 210, 160],
        },
      }),
      new ArcLayer<FlowSnapshot>({
        id: "impact-flows",
        data: flows,
        pickable: false,
        getSourcePosition: (d) => d.source,
        getTargetPosition: (d) => d.target,
        getSourceColor: [255, 255, 255, 70],
        getTargetColor: [255, 155, 85, 230],
        getWidth: (d) => 1 + d.weight * 0.4,
      }),
      new ScatterplotLayer<ZoneSnapshot>({
        id: "delta-halo",
        data: zones,
        pickable: false,
        stroked: false,
        filled: true,
        radiusScale: 1,
        getPosition: (d) => d.position,
        getFillColor: (d) => (d.change >= 0 ? [255, 200, 120, 90] : [255, 90, 90, 90]),
        getRadius: (d) => 75 + Math.abs(d.change) * 9,
      }),
      new TextLayer<ZoneSnapshot>({
        id: "top-impact-labels",
        data: topLabels,
        getPosition: (d) => d.position,
        getText: (d) => d.name,
        getColor: [255, 242, 220, 190],
        getSize: 14,
        sizeUnits: "meters",
        billboard: true,
        getTextAnchor: "middle",
        getAlignmentBaseline: "center",
      }),
    ];
  }, [flows, zones]);

  const metricRows = useMemo(() => {
    if (!simulation) return [];
    return Object.keys(simulation.baseline_metrics).map((key) => {
      const baseline = simulation.baseline_metrics[key] ?? 0;
      const proposal = simulation.proposal_metrics[key] ?? 0;
      const delta = simulation.deltas[key] ?? 0;
      return {
        key,
        label: METRIC_LABELS[key] ?? key,
        baseline,
        proposal,
        delta,
      };
    });
  }, [simulation]);

  return (
    <main className="scene-shell">
      <DeckGL
        viewState={viewState}
        controller={true}
        onViewStateChange={({ viewState: next }) => setViewState(next as MapViewState)}
        effects={effects}
        layers={layers}
        getTooltip={(info: PickingInfo<ZoneSnapshot>) => {
          if (!info.object) return null;
          const z = info.object;
          return {
            text: `${z.name}\nBaseline ${formatMetric(z.baseline_score)}\nProposal ${formatMetric(z.proposal_score)}\nChange ${z.change >= 0 ? "+" : ""}${formatMetric(z.change)}`,
          };
        }}
      />

      <section className="scene-panel">
        <p className="scene-kicker">AI City Twin Simulator</p>
        <h1>Baseline vs Proposal Impact</h1>

        <div className="control-grid">
          <label>
            City
            <input value={city} onChange={(e) => setCity(e.target.value)} />
          </label>
          <label>
            Latitude
            <input value={latitude} onChange={(e) => setLatitude(e.target.value)} />
          </label>
          <label>
            Longitude
            <input value={longitude} onChange={(e) => setLongitude(e.target.value)} />
          </label>
        </div>

        <div className="intervention-list">
          {INTERVENTION_CATALOG.map(({ key, label }) => (
            <label key={key} className="intervention-row">
              <span>{label}</span>
              <input
                type="range"
                min={0}
                max={5}
                step={0.5}
                value={interventions[key]}
                onChange={(e) =>
                  setInterventions((prev) => ({
                    ...prev,
                    [key]: Number(e.target.value),
                  }))
                }
              />
              <em>{interventions[key].toFixed(1)}</em>
            </label>
          ))}
        </div>

        <button className="run-btn" onClick={() => void runSimulation()} disabled={loading}>
          {loading ? "Simulating..." : "Run Simulation"}
        </button>

        {error ? <p className="error-text">{error}</p> : null}

        <div className="kpi-grid">
          {metricRows.map((row) => (
            <article key={row.key} className="kpi-card">
              <h3>{row.label}</h3>
              <p>
                {formatMetric(row.baseline)} -> {formatMetric(row.proposal)}
              </p>
              <strong className={row.delta >= 0 ? "delta-up" : "delta-down"}>
                {row.delta >= 0 ? "+" : ""}
                {formatMetric(row.delta)}
              </strong>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}
