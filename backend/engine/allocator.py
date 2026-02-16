"""
Effort-balanced production allocation across factories.

Uses binary search to find a balanced effort level where total production = target rate.
Effort model: local extraction = 1x, train import = train_penalty, water = water_penalty.
"""


def _compute_effort(
    demands_per_unit: dict[str, float],
    local_capacity: dict[str, float],
    rate: float,
    train_penalty: float,
    water_penalty: float,
) -> float:
    total = 0.0
    for resource, per_unit in demands_per_unit.items():
        demand = per_unit * rate
        local_cap = local_capacity.get(resource, 0.0)
        local_used = min(demand, local_cap)
        train_needed = max(0, demand - local_cap)

        if resource == "Water":
            total += demand * water_penalty
        else:
            total += local_used * 1.0 + train_needed * train_penalty
    return total


def _max_rate_for_effort(
    demands_per_unit: dict[str, float],
    local_capacity: dict[str, float],
    target_effort: float,
    train_penalty: float,
    water_penalty: float,
) -> float:
    lo, hi = 0.0, 10000.0
    for _ in range(100):
        mid = (lo + hi) / 2
        if _compute_effort(demands_per_unit, local_capacity, mid, train_penalty, water_penalty) <= target_effort:
            lo = mid
        else:
            hi = mid
    return lo


def allocate_production(
    factories: list[dict],
    target_rate: float,
    train_penalty: float,
    water_penalty: float,
) -> list[dict]:
    """
    Allocate target_rate across factories using effort-balanced model.

    Each factory dict: {theme_id, demands_per_unit, local_capacity}
    Returns: [{theme_id, allocated_rate, effort}, ...]
    """
    if len(factories) == 1:
        f = factories[0]
        effort = _compute_effort(
            f["demands_per_unit"], f["local_capacity"],
            target_rate, train_penalty, water_penalty
        )
        return [{
            "theme_id": f["theme_id"],
            "allocated_rate": target_rate,
            "effort": effort,
        }]

    lo_effort, hi_effort = 0.0, 1e9
    for _ in range(100):
        mid_effort = (lo_effort + hi_effort) / 2
        total = sum(
            _max_rate_for_effort(
                f["demands_per_unit"], f["local_capacity"],
                mid_effort, train_penalty, water_penalty
            )
            for f in factories
        )
        if total >= target_rate:
            hi_effort = mid_effort
        else:
            lo_effort = mid_effort

    balanced_effort = hi_effort

    results = []
    raw_rates = []
    for f in factories:
        rate = _max_rate_for_effort(
            f["demands_per_unit"], f["local_capacity"],
            balanced_effort, train_penalty, water_penalty
        )
        raw_rates.append(rate)
        results.append({
            "theme_id": f["theme_id"],
            "allocated_rate": rate,
            "effort": _compute_effort(
                f["demands_per_unit"], f["local_capacity"],
                rate, train_penalty, water_penalty
            ),
        })

    total_raw = sum(raw_rates)
    if total_raw > 0:
        scale = target_rate / total_raw
        for i, r in enumerate(results):
            r["allocated_rate"] = raw_rates[i] * scale
            r["effort"] = _compute_effort(
                factories[i]["demands_per_unit"],
                factories[i]["local_capacity"],
                r["allocated_rate"], train_penalty, water_penalty
            )

    return results
