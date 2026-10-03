"""Reference geography for the demo: LGAs in Nigeria's farmer-herder conflict belt,
plus generated farmland blocks, grazing reserves, water points and a stock route.

Coordinates are approximate LGA headquarters positions for demonstration only.
For a real deployment, replace them with official boundaries (for example the
GRID3 Nigeria or OCHA administrative boundary shapefiles) loaded into PostGIS.
"""
import math
import random

# name, state, lat, lon, historical baseline (0..1, higher = more past violence)
LGAS = [
    ("Makurdi", "Benue", 7.733, 8.521, 0.80),
    ("Guma", "Benue", 7.850, 8.830, 0.90),
    ("Agatu", "Benue", 7.930, 7.900, 0.85),
    ("Gboko", "Benue", 7.324, 9.004, 0.45),
    ("Otukpo", "Benue", 7.191, 8.130, 0.55),
    ("Katsina-Ala", "Benue", 7.167, 9.283, 0.60),
    ("Lafia", "Nasarawa", 8.494, 8.515, 0.50),
    ("Keana", "Nasarawa", 8.150, 8.800, 0.60),
    ("Doma", "Nasarawa", 8.383, 8.350, 0.55),
    ("Awe", "Nasarawa", 8.100, 9.130, 0.50),
    ("Bokkos", "Plateau", 9.300, 9.000, 0.85),
    ("Barkin Ladi", "Plateau", 9.533, 8.900, 0.80),
    ("Mangu", "Plateau", 9.520, 9.100, 0.75),
    ("Riyom", "Plateau", 9.630, 8.770, 0.70),
    ("Jema'a (Kafanchan)", "Kaduna", 9.583, 8.300, 0.60),
    ("Kachia", "Kaduna", 9.870, 7.950, 0.50),
    ("Wukari", "Taraba", 7.871, 9.779, 0.65),
    ("Takum", "Taraba", 7.267, 9.983, 0.55),
    ("Jalingo", "Taraba", 8.883, 11.367, 0.35),
    ("Numan", "Adamawa", 9.467, 12.033, 0.50),
    ("Demsa", "Adamawa", 9.450, 12.150, 0.55),
    ("Mokwa", "Niger", 9.295, 5.055, 0.40),
    ("Saki West", "Oyo", 8.668, 3.394, 0.35),
    ("Uzo-Uwani", "Enugu", 6.880, 7.200, 0.45),
]

# A north-to-south transhumance corridor (Plateau -> Nasarawa -> Benue), simplified.
STOCK_ROUTE = [(9.75, 8.85), (9.45, 8.95), (9.10, 8.90), (8.70, 8.70), (8.45, 8.55),
               (8.15, 8.60), (7.95, 8.70), (7.75, 8.60), (7.40, 8.40), (7.15, 8.20)]

GRAZING_RESERVES = [
    ("Wase Grazing Reserve (illustrative)", 9.10, 9.55, 0.12),
    ("Kawaji Grazing Reserve (illustrative)", 8.30, 8.75, 0.08),
    ("Bobi Grazing Reserve (illustrative)", 9.40, 5.30, 0.12),
]

WATER_POINTS = [("Benue River crossing", 7.76, 8.55), ("Lake Doma dam", 8.40, 8.36),
                ("Mada River", 8.55, 8.62), ("Katsina-Ala River", 7.20, 9.30)]


def square(lat, lon, half_km):
    dlat = half_km / 111.0
    dlon = half_km / (111.0 * math.cos(math.radians(lat)))
    return [[lon - dlon, lat - dlat], [lon + dlon, lat - dlat], [lon + dlon, lat + dlat],
            [lon - dlon, lat + dlat], [lon - dlon, lat - dlat]]


def build_zones(seed=7):
    """Return (kind, name, lga, geometry) tuples. Geometry is GeoJSON."""
    rnd = random.Random(seed)
    zones = []
    for name, state, lat, lon, _ in LGAS:
        for i in range(3):  # three farmland clusters per LGA
            flat = lat + rnd.uniform(-0.08, 0.08)
            flon = lon + rnd.uniform(-0.08, 0.08)
            crop = rnd.choice(["yam", "maize", "rice", "cassava", "sorghum", "soybean"])
            zones.append(("farmland", f"{name} {crop} farms #{i + 1}", name,
                          {"type": "Polygon", "coordinates": [square(flat, flon, rnd.uniform(1.0, 2.2))]}))
    for rname, lat, lon, half_deg in GRAZING_RESERVES:
        zones.append(("grazing_reserve", rname, None,
                      {"type": "Polygon", "coordinates": [square(lat, lon, half_deg * 111)]}))
    for wname, lat, lon in WATER_POINTS:
        zones.append(("water", wname, None, {"type": "Point", "coordinates": [lon, lat]}))
    zones.append(("stock_route", "North-South transhumance corridor (illustrative)", None,
                  {"type": "LineString", "coordinates": [[lo, la] for la, lo in STOCK_ROUTE]}))
    return zones
