import tzLookup from "tz-lookup";

import type { Farm } from "@/lib/api";

export const DEFAULT_FARM_TIME_ZONE = "America/Edmonton";

function isFiniteNumber(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

export function inferTimeZone(lat?: number | null, lon?: number | null): string | undefined {
  if (!isFiniteNumber(lat) || !isFiniteNumber(lon)) return undefined;
  try {
    return tzLookup(lat, lon);
  } catch {
    return undefined;
  }
}

export function deriveFarmTimeZone(farm?: Pick<Farm, "centroid"> | null): string | undefined {
  if (!farm?.centroid) return undefined;
  return inferTimeZone(farm.centroid.lat, farm.centroid.lon);
}

export function buildFarmTimeZoneMap(
  farms: Farm[],
  fallbackTimeZone: string | undefined = DEFAULT_FARM_TIME_ZONE
): Record<string, string> {
  const map: Record<string, string> = {};
  farms.forEach((farm) => {
    const tz = deriveFarmTimeZone(farm) ?? fallbackTimeZone;
    if (tz) {
      map[farm.id] = tz;
    }
  });
  return map;
}

export function formatDateTime(
  value?: string | null,
  options: { timeZone?: string; fallbackTimeZone?: string } = {}
): string {
  if (!value) return "—";

  const hasTimeZoneInfo = (iso: string) =>
    /[zZ]|[+-]\d{2}:?\d{2}$/.test(iso.trim());

  const normalizedValue =
    typeof value === "string" && !hasTimeZoneInfo(value) ? `${value}Z` : value;

  const timeZone = options.timeZone ?? options.fallbackTimeZone;
  const formatterOptions: Intl.DateTimeFormatOptions = {
    year: "numeric",
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    ...(timeZone ? { timeZone, timeZoneName: "short" } : {}),
  };

  try {
    return new Intl.DateTimeFormat("en-CA", formatterOptions).format(new Date(normalizedValue));
  } catch {
    return new Date(normalizedValue).toLocaleString();
  }
}
