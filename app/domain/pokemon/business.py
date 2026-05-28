def stats_by_name(payload: dict) -> dict[str, int]:
    return {
        stat["stat"]["name"].replace("-", "_"): stat["base_stat"]
        for stat in payload.get("stats", [])
    }


def collect_evolution_names(node: dict | None) -> set[str]:
    if not node:
        return set()
    names = {node["species"]["name"]}
    for child in node.get("evolves_to", []):
        names.update(collect_evolution_names(child))
    return names
