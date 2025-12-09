import os
from typing import Optional

import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from pathlib import Path

router = APIRouter()


class GeocodeRequest(BaseModel):
    street: Optional[str] = Field(None, description="Street line, e.g., 123 King St W")
    city: Optional[str] = Field(None, description="City name, e.g., Toronto")
    province: Optional[str] = Field(None, description="Province code or name (optional)")
    postal_code: Optional[str] = Field(None, description="Canadian postal code, e.g., T5J 0N3")


class GeocodeResponse(BaseModel):
    lat: float
    lng: float
    formatted: Optional[str] = None


class GeofenceSearchRequest(BaseModel):
    lat: float
    lng: float
    province: str = Field(..., description="Province code, e.g., AB")
    radius_km: float = Field(10.0, ge=0.1, le=50.0, description="Search radius in km (default 10)")


class GeoJSONFeature(BaseModel):
    type: str
    properties: dict
    geometry: dict


class GeofenceSearchResponse(BaseModel):
    center: dict
    matched: Optional[GeoJSONFeature] = None
    candidates: list[GeoJSONFeature] = Field(default_factory=list)

def get_api_key() -> str:
    key = os.getenv("OPENCAGE_API_KEY")
    if not key:
        raise HTTPException(status_code=500, detail="OPENCAGE_API_KEY is not configured")
    return key


@router.post("/geocode", response_model=GeocodeResponse)
def geocode(req: GeocodeRequest):
    api_key = get_api_key()
    street = (req.street or "").strip()
    city = (req.city or "").strip()
    province = (req.province or "").strip()
    postal = (req.postal_code or "").strip().upper()

    if not street and not city and not postal:
        raise HTTPException(status_code=400, detail="Provide at least street/city/postal_code")

    query_parts = [street, city, province, postal, "Canada"]
    query = ", ".join([p for p in query_parts if p])

    url = "https://api.opencagedata.com/geocode/v1/json"
    params = {"key": api_key, "q": query, "limit": 1, "countrycode": "ca"}

    try:
        r = requests.get(url, params=params, timeout=5)
    except requests.RequestException:
        raise HTTPException(status_code=502, detail="Error contacting geocoding service")

    if r.status_code != 200:
        raise HTTPException(status_code=502, detail="Error from geocoding service")

    data = r.json()
    if not data.get("results"):
        raise HTTPException(status_code=404, detail="No location found for given postal code")

    result = data["results"][0]
    coords = result.get("geometry", {})
    if "lat" not in coords or "lng" not in coords:
        raise HTTPException(status_code=502, detail="Malformed response from geocoding service")

    return GeocodeResponse(lat=coords["lat"], lng=coords["lng"], formatted=result.get("formatted"))


def _load_gpkg(province_code: str) -> Path:
    """Locate a province GPKG under resources/geofence/{province}.gpkg."""
    code = province_code.strip().lower()
    # common province mappings
    canonical_map = {
        "ab": "alberta",
        "bc": "britishcolumbia",
        "mb": "manitoba",
        "nb": "newbrunswick",
        "nl": "newfoundlandandlabrador",
        "ns": "novascotia",
        "nt": "northwestterritories",
        "nu": "nunavut",
        "on": "ontario",
        "pe": "princeedwardisland",
        "qc": "quebec",
        "sk": "saskatchewan",
        "yt": "yukon",
    }
    # possible base roots: repo root (../..), api root (..), and optional env override
    here = Path(__file__).resolve()
    repo_root = here.parents[3]  # project/
    api_root = here.parents[2]   # project/api
    base_roots = [repo_root, api_root]
    env_root = os.getenv("GEOFENCE_DATA_ROOT")
    if env_root:
        base_roots.insert(0, Path(env_root))

    candidates: list[Path] = []
    for base in base_roots:
        candidates.append(base / "resources" / "geofence" / f"{code}.gpkg")
    # mapped canonical name
    if code in canonical_map:
        for base in base_roots:
            candidates.append(base / "resources" / "geofence" / f"{canonical_map[code]}.gpkg")
    # also allow full names directly
    if code not in canonical_map:
        for base in base_roots:
            candidates.append(base / "resources" / "geofence" / f"{code.replace(' ', '')}.gpkg")

    for gpkg in candidates:
        if gpkg.exists():
            return gpkg

    raise HTTPException(
        status_code=404,
        detail=f"Province dataset not found for '{province_code}'. Tried: {[str(p) for p in candidates]}",
    )


@router.post("/geofence/search", response_model=GeofenceSearchResponse)
def geofence_search(req: GeofenceSearchRequest):
    """
    Given lat/lng + province, return the containing polygon (if any) and nearby polygons within radius_km.
    """
    try:
        import fiona
        from shapely.geometry import Point, shape, mapping
        from shapely.ops import transform as shp_transform
        from pyproj import CRS, Transformer
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=f"Geospatial dependencies missing: {exc}")

    gpkg_path = _load_gpkg(req.province)
    try:
        layer_name = fiona.listlayers(gpkg_path)[0]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to read {gpkg_path.name}: {exc}")

    # Set up CRSs and transformers
    src_crs = None
    matched_feature = None
    candidates: list[GeoJSONFeature] = []

    try:
        with fiona.open(gpkg_path, layer=layer_name) as src:
            src_crs = CRS.from_user_input(src.crs or src.crs_wkt or "EPSG:4326")
            pt4326 = Point(req.lng, req.lat)

            to_src = Transformer.from_crs("EPSG:4326", src_crs, always_xy=True).transform
            to_4326 = Transformer.from_crs(src_crs, "EPSG:4326", always_xy=True).transform

            pt_in_src = shp_transform(to_src, pt4326)

            aeqd = CRS.from_proj4(
                f"+proj=aeqd +lat_0={req.lat} +lon_0={req.lng} +datum=WGS84 +units=m +no_defs"
            )
            to_aeqd = Transformer.from_crs(src_crs, aeqd, always_xy=True).transform
            pt_aeqd = shp_transform(to_aeqd, pt_in_src)
            radius_m = req.radius_km * 1000.0

            for feat in src:
                geom = feat.get("geometry")
                if not geom:
                    continue
                try:
                    g_src = shape(geom)
                except Exception:
                    continue
                if g_src.is_empty:
                    continue

                # exact containment
                if g_src.covers(pt_in_src) and matched_feature is None:
                    g4326 = shp_transform(to_4326, g_src)
                    matched_feature = {
                        "type": "Feature",
                        "properties": {**(feat.get("properties") or {}), "distance_m": 0.0},
                        "geometry": mapping(g4326),
                    }

                # distance / nearby
                g_aeqd = shp_transform(to_aeqd, g_src)
                dist = float(g_aeqd.centroid.distance(pt_aeqd))
                if dist <= radius_m:
                    g4326 = shp_transform(to_4326, g_src)
                    candidates.append(
                        {
                            "type": "Feature",
                            "properties": {**(feat.get("properties") or {}), "distance_m": dist},
                            "geometry": mapping(g4326),
                        }
                    )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to read {gpkg_path.name}: {exc}")

    candidates = sorted(candidates, key=lambda f: f["properties"].get("distance_m", 0))

    return GeofenceSearchResponse(
        center={"lat": req.lat, "lng": req.lng},
        matched=matched_feature,
        candidates=candidates,
    )
