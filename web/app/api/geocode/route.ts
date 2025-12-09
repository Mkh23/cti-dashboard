import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";

type RequestBody = {
  street?: string;
  city?: string;
  province?: string;
  postal_code?: string;
};

function loadApiKey(): string | null {
  if (process.env.OPENCAGE_API_KEY) {
    return process.env.OPENCAGE_API_KEY;
  }
  try {
    const keyPath = path.join(process.cwd(), "resources", "geofence", "opencage_api_key");
    return fs.readFileSync(keyPath, "utf-8").trim();
  } catch {
    return null;
  }
}

export async function POST(request: Request) {
  const apiKey = loadApiKey();
  if (!apiKey) {
    return NextResponse.json({ detail: "Geocoding API key not configured" }, { status: 500 });
  }

  let body: RequestBody;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ detail: "Invalid JSON body" }, { status: 400 });
  }

  const street = body.street?.trim() ?? "";
  const city = body.city?.trim() ?? "";
  const province = body.province?.trim() ?? "";
  const postal = body.postal_code?.trim().toUpperCase() ?? "";

  if (!street && !city && !postal) {
    return NextResponse.json({ detail: "Provide street, city, or postal_code" }, { status: 400 });
  }

  const queryParts = [street, city, province, postal, "Canada"].filter(Boolean);
  const query = queryParts.join(", ");
  const url = new URL("https://api.opencagedata.com/geocode/v1/json");
  url.searchParams.set("q", query);
  url.searchParams.set("key", apiKey);
  url.searchParams.set("limit", "1");
  url.searchParams.set("countrycode", "ca");

  const res = await fetch(url.toString(), { cache: "no-store" });
  if (!res.ok) {
    return NextResponse.json({ detail: "Geocoding lookup failed" }, { status: 502 });
  }
  const data = await res.json();
  const result = data?.results?.[0];
  if (!result?.geometry) {
    return NextResponse.json({ detail: "No results found" }, { status: 404 });
  }

  return NextResponse.json({
    lat: result.geometry.lat,
    lng: result.geometry.lng,
    formatted: result.formatted,
  });
}
