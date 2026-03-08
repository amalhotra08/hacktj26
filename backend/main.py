from __future__ import annotations

import math
import os
import random
import json
import requests
from datetime import datetime, timezone
from json import JSONDecodeError
from typing import Literal
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from final_api import LocationIntelligenceAnalyzer

env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(env_path)


MetricKey = Literal[
    "traffic_flow",
    "carbon",
    "safety",
    "urban_heat",
    "resilience",
]


class Intervention(BaseModel):
    type: Literal[
        "bike_lane",
        "bus_lane",
        "tree_planting",
        "pedestrianization",
        "street_redesign",
        "solar_panel",
        "flood_mitigation",
    ]
    intensity: float = Field(default=1.0, ge=0.0, le=5.0)


class SimulateRequest(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    city: str | None = None
    interventions: list[Intervention] = Field(default_factory=list)
    include_raw_report: bool = False


class ZoneSnapshot(BaseModel):
    id: int
    name: str
    position: tuple[float, float]
    baseline_score: float
    proposal_score: float
    change: float


class FlowSnapshot(BaseModel):
    source: tuple[float, float]
    target: tuple[float, float]
    weight: float


class SimulateResponse(BaseModel):
    metadata: dict
    baseline_metrics: dict[str, float]
    proposal_metrics: dict[str, float]
    deltas: dict[str, float]
    zones: list[ZoneSnapshot]
    flows: list[FlowSnapshot]
    intervention_summary: list[dict]
    raw_report: dict | None = None


class ParseActionRequest(BaseModel):
    city: str
    user_text: str
    history: list[dict] = Field(default_factory=list)


class ParseActionResponse(BaseModel):
    action: Literal["add", "clarify", "unknown"]
    feature: str | None = None
    start: str | None = None
    end: str | None = None
    location: str | None = None
    message: str | None = None


BASE_INTERVENTION_EFFECTS: dict[str, dict[MetricKey, float]] = {
    "bike_lane": {
        "traffic_flow": 3.4,
        "carbon": 4.2,
        "safety": 2.6,
        "urban_heat": 0.7,
        "resilience": 0.9,
    },
    "bus_lane": {
        "traffic_flow": 5.1,
        "carbon": 3.8,
        "safety": 1.8,
        "urban_heat": 0.5,
        "resilience": 0.8,
    },
    "tree_planting": {
        "traffic_flow": 0.8,
        "carbon": 3.6,
        "safety": 1.5,
        "urban_heat": 5.1,
        "resilience": 4.0,
    },
    "pedestrianization": {
        "traffic_flow": 2.6,
        "carbon": 4.5,
        "safety": 4.0,
        "urban_heat": 2.8,
        "resilience": 1.2,
    },
    "street_redesign": {
        "traffic_flow": 2.2,
        "carbon": 2.0,
        "safety": 5.4,
        "urban_heat": 1.4,
        "resilience": 1.1,
    },
    "solar_panel": {
        "traffic_flow": 0.5,
        "carbon": 5.0,
        "safety": 0.7,
        "urban_heat": 2.0,
        "resilience": 1.8,
    },
    "flood_mitigation": {
        "traffic_flow": 0.9,
        "carbon": 0.6,
        "safety": 2.4,
        "urban_heat": 0.8,
        "resilience": 6.4,
    },
}

INTERACTION_EFFECTS: dict[tuple[str, str], dict[MetricKey, float]] = {
    ("bike_lane", "bus_lane"): {
        "traffic_flow": 1.4,
        "carbon": 1.2,
    },
    ("tree_planting", "flood_mitigation"): {
        "resilience": 2.4,
        "urban_heat": 1.0,
    },
    ("pedestrianization", "street_redesign"): {
        "safety": 2.2,
        "carbon": 1.1,
    },
    ("tree_planting", "solar_panel"): {
        "carbon": 1.5,
        "urban_heat": 0.8,
    },
}


def clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


def risk_rating_to_score(value: str | None) -> float:
    mapping = {
        "Very Low": 95.0,
        "Relatively Low": 82.0,
        "Relatively Moderate": 64.0,
        "Relatively High": 45.0,
        "Very High": 26.0,
    }
    if not value:
        return 60.0
    return mapping.get(value, 60.0)


def _safe_float(value, fallback: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def _context_multiplier(metric: MetricKey, current_score: float) -> float:
    deficit = (100.0 - clamp(current_score)) / 100.0
    base = 0.65 + 0.9 * deficit

    # Slight extra sensitivity for compounded urban climate risks.
    if metric in {"urban_heat", "resilience"}:
        base += 0.08 * deficit

    return clamp(base, 0.55, 1.65)


def build_baseline_metrics(raw_report: dict) -> dict[str, float]:
    data = raw_report.get("data", {})

    traffic = data.get("traffic") or {}
    current_speed = _safe_float(traffic.get("currentSpeed"), 24.0)
    free_speed = max(1.0, _safe_float(traffic.get("freeFlowSpeed"), 36.0))
    traffic_flow_score = clamp((current_speed / free_speed) * 100)

    air = data.get("air_quality") or {}
    pm25 = _safe_float(air.get("pm2_5"), 14.0)
    co = _safe_float(air.get("carbon_monoxide"), 300.0)
    air_penalty = pm25 * 1.3 + co * 0.01
    carbon_score = clamp(100.0 - air_penalty)

    env = data.get("environmental_risks") or {}
    if isinstance(env, dict) and "error" not in env:
        hazard_scores = [risk_rating_to_score(v) for v in env.values()]
        safety_score = clamp(sum(hazard_scores) / len(hazard_scores)) if hazard_scores else 60.0
    else:
        safety_score = 60.0

    uhi = data.get("urban_heat_island") or {}
    uhi_delta = _safe_float(uhi.get("uhi_delta"), 1.5)
    weather = data.get("weather") or {}
    temp = _safe_float(weather.get("temperature_2m"), 74.0)
    urban_heat_score = clamp(100.0 - (max(0.0, uhi_delta) * 15.0 + max(0.0, temp - 78.0) * 1.1))

    tree = data.get("tree_coverage") or {}
    tree_pct = _safe_float(tree.get("tree_cover_percent"), 18.0)
    flood = data.get("flood_risk") or []
    discharge_vals = [
        _safe_float(entry.get("discharge_m3_s"), 0.0)
        for entry in flood
        if isinstance(entry, dict) and entry.get("discharge_m3_s") is not None
    ]
    flood_peak = max(discharge_vals) if discharge_vals else 25.0
    resilience_score = clamp(35.0 + tree_pct * 1.5 - flood_peak * 0.18)

    return {
        "traffic_flow": round(traffic_flow_score, 2),
        "carbon": round(carbon_score, 2),
        "safety": round(safety_score, 2),
        "urban_heat": round(urban_heat_score, 2),
        "resilience": round(resilience_score, 2),
    }


def _parse_iso_timestamp(value: str | None) -> datetime | None:
    if not value or not isinstance(value, str):
        return None
    try:
        if value.endswith("Z"):
            value = value.replace("Z", "+00:00")
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        return None


def _freshness_label(hours_old: float | None) -> str:
    if hours_old is None:
        return "Unknown"
    if hours_old <= 6:
        return "Fresh"
    if hours_old <= 24:
        return "Aging"
    return "Stale"


def _source_is_ok(payload) -> bool:
    if payload is None:
        return False
    if isinstance(payload, dict):
        return "error" not in payload and bool(payload)
    if isinstance(payload, list):
        return len(payload) > 0
    return True


def build_source_health(raw_report: dict) -> tuple[dict, dict[str, bool]]:
    data = raw_report.get("data", {})
    source_status: dict[str, bool] = {}
    ok = 0
    missing = 0
    fallback = 0

    for source_name, payload in data.items():
        is_ok = _source_is_ok(payload)
        source_status[source_name] = is_ok
        if is_ok:
            ok += 1
        else:
            missing += 1
            fallback += 1

    return {
        "ok": ok,
        "missing": missing,
        "fallback": fallback,
    }, source_status


def build_freshness(raw_report: dict) -> dict[str, str]:
    now = datetime.now(timezone.utc)
    data = raw_report.get("data", {})

    air_time = _parse_iso_timestamp((data.get("air_quality") or {}).get("time"))
    weather_time = _parse_iso_timestamp((data.get("weather") or {}).get("time"))
    flood_dates = (data.get("flood_risk") or [])
    flood_time = None
    if flood_dates and isinstance(flood_dates, list):
        first_date = flood_dates[0].get("date") if isinstance(flood_dates[0], dict) else None
        flood_time = _parse_iso_timestamp(first_date + "T00:00:00+00:00" if first_date else None)

    traffic_time = weather_time  # traffic payload lacks stable timestamp in current adapter
    safety_time = None
    heat_time = weather_time
    resilience_time = flood_time

    def hours_old(dt: datetime | None) -> float | None:
        if dt is None:
            return None
        return max(0.0, (now - dt).total_seconds() / 3600.0)

    return {
        "traffic_flow": _freshness_label(hours_old(traffic_time)),
        "carbon": _freshness_label(hours_old(air_time)),
        "safety": _freshness_label(hours_old(safety_time)),
        "urban_heat": _freshness_label(hours_old(heat_time)),
        "resilience": _freshness_label(hours_old(resilience_time)),
    }


def build_confidence(
    raw_report: dict,
    interventions: list[Intervention],
    freshness: dict[str, str],
    source_status: dict[str, bool],
) -> dict[str, float]:
    intervention_complexity = sum(item.intensity for item in interventions)
    complexity_penalty = min(24.0, intervention_complexity * 2.8)
    interaction_penalty = 0.8 * max(0, len(interventions) - 1)

    metric_sources = {
        "traffic_flow": ["traffic"],
        "carbon": ["air_quality"],
        "safety": ["environmental_risks"],
        "urban_heat": ["urban_heat_island", "weather"],
        "resilience": ["flood_risk", "tree_coverage"],
    }

    freshness_score = {"Fresh": 12.0, "Aging": 6.0, "Stale": -4.0, "Unknown": -9.0}
    confidence: dict[str, float] = {}

    for metric, sources in metric_sources.items():
        available = sum(1 for source in sources if source_status.get(source, False))
        source_ratio = available / len(sources)
        source_component = 38.0 + source_ratio * 40.0
        freshness_component = freshness_score.get(freshness.get(metric, "Unknown"), -9.0)
        conf = source_component + freshness_component - complexity_penalty - interaction_penalty
        confidence[metric] = round(clamp(conf, 10.0, 99.0), 1)

    return confidence


def apply_interventions(
    baseline: dict[str, float], interventions: list[Intervention]
) -> tuple[dict[str, float], dict[str, float], list[dict]]:
    running_scores: dict[str, float] = {k: float(v) for k, v in baseline.items()}
    total_intensity = 0.0
    type_intensity: dict[str, float] = {}
    summary: list[dict] = []

    for intervention in interventions:
        effects = BASE_INTERVENTION_EFFECTS.get(intervention.type, {})
        prior_same_type = type_intensity.get(intervention.type, 0.0)

        # Diminishing returns: same type and crowded scenarios decay impact.
        intensity_scale = math.log1p(intervention.intensity * 1.6) / math.log1p(1.6)
        type_decay = 1.0 / (1.0 + 0.35 * prior_same_type)
        network_decay = 1.0 / (1.0 + 0.09 * total_intensity)
        effective_scale = intensity_scale * type_decay * network_decay

        contribution: dict[str, float] = {}
        for metric, base_delta in effects.items():
            context = _context_multiplier(metric, running_scores[metric])
            delta = base_delta * effective_scale * context
            running_scores[metric] = clamp(running_scores[metric] + delta)
            contribution[metric] = round(delta, 2)

        summary.append(
            {
                "type": intervention.type,
                "intensity": intervention.intensity,
                "metric_contribution": contribution,
                "modifiers": {
                    "effective_scale": round(effective_scale, 3),
                    "type_decay": round(type_decay, 3),
                    "network_decay": round(network_decay, 3),
                },
            }
        )
        type_intensity[intervention.type] = prior_same_type + intervention.intensity
        total_intensity += intervention.intensity

    # Pairwise interactions add realistic synergies/tradeoffs.
    for a, b in INTERACTION_EFFECTS.keys():
        if a not in type_intensity or b not in type_intensity:
            continue
        pair_strength = min(type_intensity[a], type_intensity[b])
        pair_scale = min(1.8, math.log1p(pair_strength))
        pair_contribution: dict[str, float] = {}
        for metric, base_delta in INTERACTION_EFFECTS[(a, b)].items():
            context = _context_multiplier(metric, running_scores[metric])
            delta = base_delta * pair_scale * context
            running_scores[metric] = clamp(running_scores[metric] + delta)
            pair_contribution[metric] = round(delta, 2)

        summary.append(
            {
                "type": f"{a}+{b}",
                "intensity": round(pair_strength, 2),
                "metric_contribution": pair_contribution,
                "interaction": True,
            }
        )

    proposal = {metric: round(clamp(score), 2) for metric, score in running_scores.items()}
    deltas = {metric: round(proposal[metric] - baseline[metric], 2) for metric in baseline.keys()}
    return proposal, deltas, summary


def _scenario_seed(latitude: float, longitude: float, interventions: list[Intervention]) -> int:
    token = f"{latitude:.5f}|{longitude:.5f}|" + ",".join(
        f"{item.type}:{item.intensity:.2f}" for item in interventions
    )
    return abs(hash(token)) % (2**31)


def build_spatial_snapshot(
    latitude: float,
    longitude: float,
    baseline_metrics: dict[str, float],
    proposal_metrics: dict[str, float],
    interventions: list[Intervention],
) -> tuple[list[ZoneSnapshot], list[FlowSnapshot]]:
    seed = _scenario_seed(latitude, longitude, interventions)
    rng = random.Random(seed)

    baseline_composite = sum(baseline_metrics.values()) / len(baseline_metrics)
    proposal_composite = sum(proposal_metrics.values()) / len(proposal_metrics)
    composite_delta = proposal_composite - baseline_composite

    zones: list[ZoneSnapshot] = []
    zone_count = 72
    for idx in range(zone_count):
        theta = rng.random() * math.pi * 2
        radius = 0.22 * math.sqrt(rng.random())
        lng = longitude + radius * math.cos(theta)
        lat = latitude + radius * math.sin(theta) * 0.65

        local_base = clamp(baseline_composite + rng.uniform(-16, 16))
        local_boost = composite_delta * (0.6 + rng.random() * 0.9)
        local_proposal = clamp(local_base + local_boost)
        zones.append(
            ZoneSnapshot(
                id=idx,
                name=f"Grid-{idx:03d}",
                position=(round(lng, 6), round(lat, 6)),
                baseline_score=round(local_base, 2),
                proposal_score=round(local_proposal, 2),
                change=round(local_proposal - local_base, 2),
            )
        )

    top = sorted(zones, key=lambda z: z.change, reverse=True)[:20]
    flows: list[FlowSnapshot] = []
    for source in top:
        for _ in range(2):
            target = top[rng.randrange(len(top))]
            if target.id == source.id:
                continue
            flows.append(
                FlowSnapshot(
                    source=source.position,
                    target=target.position,
                    weight=round(max(1.5, source.change * (0.6 + rng.random() * 0.6)), 2),
                )
            )

    return zones, flows


app = FastAPI(title="City Digital Twin API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check() -> dict:
    return {
        "status": "ok",
        "time_utc": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/llm/parse", response_model=ParseActionResponse)
def parse_user_action(payload: ParseActionRequest) -> ParseActionResponse:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return ParseActionResponse(
            action="unknown",
            message="LLM parser unavailable: missing GROQ_API_KEY on backend.",
        )

    system_prompt = f"""
You are an urban infrastructure map assistant for {payload.city}.
Parse user requests to add features to a map. Always respond with valid JSON only.

Supported features:
  Route features (need "start" AND "end" locations in {payload.city}):
    bike_lane, bus_lane, pedestrian_street, flood_mitigation
  Point/area features (need a single "location" in {payload.city}):
    bus_stop, park, tree, solar_panel

Response formats:
  If all info present and it is a route feature:
    {{"action":"add","feature":"<type>","start":"<location>","end":"<location>"}}
  If all info present and it is a point feature:
    {{"action":"add","feature":"<type>","location":"<location>"}}
  If required location info is missing:
    {{"action":"clarify","message":"<question asking specifically what is missing>"}}
  If request is unclear or unsupported:
    {{"action":"unknown","message":"<brief helpful response>"}}

For "location", "start", and "end" values, always output specific address-level place text in {payload.city}.
""".strip()

    messages = [{"role": "system", "content": system_prompt}] + payload.history + [
        {"role": "user", "content": payload.user_text}
    ]

    try:
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": messages,
                "response_format": {"type": "json_object"},
            },
            timeout=30,
        )
        resp.raise_for_status()
        raw = (
            resp.json()
            .get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
            .strip()
        )
        parsed = json.loads(raw)
    except (requests.RequestException, JSONDecodeError, KeyError, ValueError) as exc:
        return ParseActionResponse(
            action="unknown",
            message=f"LLM parser error: {exc}",
        )

    action = parsed.get("action")
    if action not in {"add", "clarify", "unknown"}:
        return ParseActionResponse(
            action="unknown",
            message="Parser returned unsupported action.",
        )

    return ParseActionResponse(
        action=action,
        feature=parsed.get("feature"),
        start=parsed.get("start"),
        end=parsed.get("end"),
        location=parsed.get("location"),
        message=parsed.get("message"),
    )


@app.post("/simulate", response_model=SimulateResponse)
def simulate_city_change(payload: SimulateRequest) -> SimulateResponse:
    analyzer = LocationIntelligenceAnalyzer(tomtom_api_key=os.getenv("TOMTOM_KEY"))
    raw_report = analyzer.generate_full_report(payload.latitude, payload.longitude)

    baseline_metrics = build_baseline_metrics(raw_report)
    proposal_metrics, deltas, intervention_summary = apply_interventions(
        baseline_metrics, payload.interventions
    )
    source_health, source_status = build_source_health(raw_report)
    freshness = build_freshness(raw_report)
    confidence = build_confidence(raw_report, payload.interventions, freshness, source_status)
    zones, flows = build_spatial_snapshot(
        payload.latitude,
        payload.longitude,
        baseline_metrics,
        proposal_metrics,
        payload.interventions,
    )

    return SimulateResponse(
        metadata={
            "city": payload.city,
            "latitude": payload.latitude,
            "longitude": payload.longitude,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "intervention_count": len(payload.interventions),
            "confidence": confidence,
            "freshness": freshness,
            "source_health": source_health,
        },
        baseline_metrics=baseline_metrics,
        proposal_metrics=proposal_metrics,
        deltas=deltas,
        zones=zones,
        flows=flows,
        intervention_summary=intervention_summary,
        raw_report=raw_report if payload.include_raw_report else None,
    )
