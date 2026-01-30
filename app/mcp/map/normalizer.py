def normalize_pois(pois, max_results: int, category: str="unknown"):
    results = []

    for poi in pois[:max_results]:
        results.append(
            {
                "name": poi.get("name"),
                "address": poi.get("address"),
                "location": poi.get("location"),
                "distance_m": int(poi.get("distance", 0)),
                "category": category,
                "tel": poi.get("tel"),
            }
        )

    return results
