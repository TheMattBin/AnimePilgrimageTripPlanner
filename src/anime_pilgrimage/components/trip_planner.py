"""Trip Planner & Route Optimizer with multi-city clustering, 2-opt TSP, and realistic budgets."""

from __future__ import annotations

import math
from collections import defaultdict

from anime_pilgrimage.models import (
    Coordinates,
    DailyItinerary,
    PilgrimageLocation,
    QueryAnalysis,
    ScheduledStop,
    TravelPlan,
)


class TripPlanner:
    """Generates multi-day anime pilgrimage itineraries with geographic clustering and routing."""

    # Realistic average door-to-door speeds (km/h).
    # - `regional_short_rail`: 35–100 km regional JR/private lines (e.g., Tokyo -> Kamakura)
    # - `shinkansen`: 100–800 km when both ends are near Shinkansen hubs
    # - `regional_rail`: 100–550 km off-Shinkansen routes (e.g., Tokyo -> Hida-Furukawa)
    # - `domestic_flight`: >=550 km off-Shinkansen or >800 km (e.g., Tokyo -> Hita / Sapporo)
    TRAVEL_SPEEDS_KMH: dict[str, float] = {
        "walking": 4.5,
        "subway": 25.0,
        "train": 45.0,
        "bus": 22.0,
        "taxi": 30.0,
        "mixed": 32.0,
        "regional_short_rail": 55.0,
        "shinkansen": 150.0,
        "regional_rail": 65.0,
        "domestic_flight": 700.0,
    }

    # Major Shinkansen station hubs (lat, lng) used to distinguish bullet-train corridors
    # from regional limited-express routes.
    SHINKANSEN_HUBS: tuple[tuple[str, float, float], ...] = (
        ("Tokyo", 35.6812, 139.7671),
        ("Shin-Yokohama", 35.5075, 139.6176),
        ("Odawara", 35.2562, 139.1558),
        ("Shizuoka", 34.9717, 138.3891),
        ("Hamamatsu", 34.7037, 137.7347),
        ("Nagoya", 35.1709, 136.8815),
        ("Kyoto", 34.9858, 135.7588),
        ("Shin-Osaka", 34.7335, 135.5003),
        ("Shin-Kobe", 34.7066, 135.1956),
        ("Himeji", 34.8273, 134.6908),
        ("Okayama", 34.6665, 133.9186),
        ("Hiroshima", 34.3977, 132.4754),
        ("Hakata", 33.5897, 130.4207),
        ("Kumamoto", 32.7900, 130.6889),
        ("Kagoshima-Chuo", 31.5838, 130.5419),
        ("Omiya", 35.9063, 139.6238),
        ("Sendai", 38.2601, 140.8824),
        ("Morioka", 39.7016, 141.1365),
        ("Shin-Aomori", 40.8274, 140.6935),
        ("Nagano", 36.6431, 138.1886),
        ("Kanazawa", 36.5781, 136.6481),
        ("Niigata", 37.9120, 139.0617),
    )
    SHINKANSEN_HUB_RADIUS_KM: float = 25.0

    VISIT_DURATIONS_MIN: dict[str, int] = {
        "temple": 45,
        "shrine": 40,
        "station": 25,
        "crossing": 20,
        "stairs": 25,
        "staircase": 25,
        "park": 60,
        "garden": 60,
        "tower": 75,
        "observatory": 75,
        "bridge": 25,
        "museum": 110,
        "cafe": 50,
        "library": 45,
        "beach": 50,
        "island": 90,
        "default": 50,
    }

    # Cost profile in JPY by travel style
    COST_PROFILES: dict[str, dict[str, float]] = {
        "backpacker": {
            "meal": 900.0,
            "attraction": 400.0,
            "accommodation": 4200.0,
            "transit_per_leg": 240.0,
            "intercity_per_km": 22.0,
            "domestic_flight": 12000.0,
        },
        "budget": {
            "meal": 1200.0,
            "attraction": 500.0,
            "accommodation": 6500.0,
            "transit_per_leg": 260.0,
            "intercity_per_km": 26.0,
            "domestic_flight": 15000.0,
        },
        "standard": {
            "meal": 2000.0,
            "attraction": 800.0,
            "accommodation": 13000.0,
            "transit_per_leg": 320.0,
            "intercity_per_km": 32.0,
            "domestic_flight": 22000.0,
        },
        "luxury": {
            "meal": 5000.0,
            "attraction": 1500.0,
            "accommodation": 32000.0,
            "transit_per_leg": 1600.0,
            "intercity_per_km": 42.0,
            "domestic_flight": 38000.0,
        },
    }

    PACE_MAX_STOPS_PER_DAY: dict[str, int] = {
        "relaxed": 3,
        "balanced": 4,
        "packed": 6,
    }

    INTERCITY_DISTANCE_KM: float = 35.0
    SHINKANSEN_MIN_DISTANCE_KM: float = 100.0
    FLIGHT_OFF_SHINKANSEN_KM: float = 550.0
    FLIGHT_ANY_CORRIDOR_KM: float = 800.0
    DAY_START_MINUTES: int = 9 * 60  # 09:00
    INTERCITY_DEPART_MINUTES: int = 8 * 60 + 30  # 08:30 departure on transfer mornings
    TRANSFER_LATE_ARRIVAL_MINUTES: int = 15 * 60  # 15:00 cutoff -> move transfer to prior evening
    DAY_LATE_WARNING_MINUTES: int = 21 * 60  # 21:00

    @staticmethod
    def calculate_distance(coord1: Coordinates | None, coord2: Coordinates | None) -> float:
        """Calculate Haversine distance in kilometers between two coordinates."""
        if coord1 is None or coord2 is None:
            return 0.0

        lat1, lon1 = math.radians(coord1.lat), math.radians(coord1.lng)
        lat2, lon2 = math.radians(coord2.lat), math.radians(coord2.lng)

        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        )
        c = 2 * math.asin(min(1.0, math.sqrt(a)))
        return 6371.0 * c

    def _is_near_shinkansen_hub(self, coord: Coordinates | None) -> bool:
        if coord is None:
            return False
        return any(
            self.calculate_distance(coord, Coordinates(lat=lat, lng=lng))
            <= self.SHINKANSEN_HUB_RADIUS_KM
            for _, lat, lng in self.SHINKANSEN_HUBS
        )

    def estimate_travel_leg(
        self,
        distance_km: float,
        preferred_mode: str = "mixed",
        *,
        start_coord: Coordinates | None = None,
        end_coord: Coordinates | None = None,
    ) -> tuple[int, str]:
        """Return (minutes, mode_label) for a leg between two stops."""
        if distance_km <= 0.05:
            return 5, "walking"
        if distance_km < 0.8:
            minutes = max(5, round(distance_km / self.TRAVEL_SPEEDS_KMH["walking"] * 60))
            return minutes, "walking"
        if distance_km > self.INTERCITY_DISTANCE_KM:
            if distance_km <= self.SHINKANSEN_MIN_DISTANCE_KM:
                minutes = (
                    round(distance_km / self.TRAVEL_SPEEDS_KMH["regional_short_rail"] * 60) + 10
                )
                return minutes, "rail"

            both_shinkansen = self._is_near_shinkansen_hub(
                start_coord
            ) and self._is_near_shinkansen_hub(end_coord)

            if distance_km > self.FLIGHT_ANY_CORRIDOR_KM or (
                distance_km >= self.FLIGHT_OFF_SHINKANSEN_KM and not both_shinkansen
            ):
                # ~1.2-1.5h flight + ~2h15m airports, security, and ground transfers
                minutes = round(distance_km / self.TRAVEL_SPEEDS_KMH["domestic_flight"] * 60) + 135
                return minutes, "domestic flight + airport transfer"

            if both_shinkansen:
                minutes = round(distance_km / self.TRAVEL_SPEEDS_KMH["shinkansen"] * 60) + 25
                return minutes, "shinkansen"

            minutes = round(distance_km / self.TRAVEL_SPEEDS_KMH["regional_rail"] * 60) + 35
            return minutes, "limited express / regional rail"

        mode = preferred_mode if preferred_mode in self.TRAVEL_SPEEDS_KMH else "mixed"
        speed = self.TRAVEL_SPEEDS_KMH[mode]
        transfer_buffer = 8 if mode in ("subway", "train", "bus", "mixed") else 5
        minutes = max(10, round(distance_km / speed * 60) + transfer_buffer)
        mode_label = "train / subway" if mode == "mixed" else mode
        return minutes, mode_label

    def estimate_visit_duration(self, location: PilgrimageLocation) -> int:
        """Estimate dwell time in minutes based on landmark type."""
        name_lower = location.name.lower()
        for keyword, duration in self.VISIT_DURATIONS_MIN.items():
            if keyword != "default" and keyword in name_lower:
                return duration
        return self.VISIT_DURATIONS_MIN["default"]

    @staticmethod
    def determine_optimal_visit_time(location: PilgrimageLocation) -> str:
        """Suggest preferred time of day for lighting and crowd avoidance."""
        hint = f"{location.name} {location.best_visit_time}".lower()
        if any(w in hint for w in ("sunset", "evening", "night", "tower", "observatory", "illumination")):
            return "evening"
        if any(w in hint for w in ("morning", "sunrise", "temple", "shrine", "stairs", "staircase")):
            return "morning"
        return "afternoon"

    @staticmethod
    def _region_label(location: PilgrimageLocation) -> str:
        if location.city and location.prefecture and location.city.lower() != location.prefecture.lower():
            return f"{location.city}, {location.prefecture}"
        return location.city or location.prefecture or "Japan"

    def _partition_regions(
        self, locations: list[PilgrimageLocation], region_radius_km: float = 35.0
    ) -> list[list[PilgrimageLocation]]:
        """Group locations into distinct metropolitan/regional zones without dropping un-geocoded spots."""
        with_coords = [loc for loc in locations if loc.coordinates is not None]
        without_coords = [loc for loc in locations if loc.coordinates is None]

        regions: list[list[PilgrimageLocation]] = []
        unassigned = list(range(len(with_coords)))

        while unassigned:
            seed_idx = unassigned.pop(0)
            region_indices = [seed_idx]
            changed = True
            while changed:
                changed = False
                for idx in list(unassigned):
                    if any(
                        self.calculate_distance(
                            with_coords[idx].coordinates,
                            with_coords[member].coordinates,
                        )
                        <= region_radius_km
                        for member in region_indices
                    ):
                        region_indices.append(idx)
                        unassigned.remove(idx)
                        changed = True
            regions.append([with_coords[i] for i in region_indices])

        orphan_by_city: dict[str, list[PilgrimageLocation]] = defaultdict(list)
        for loc in without_coords:
            loc_city = (loc.city or loc.prefecture or "").lower()
            matched_region: list[PilgrimageLocation] | None = None
            if loc_city:
                for region in regions:
                    if any(
                        loc_city in (member.city or "").lower()
                        or loc_city in (member.prefecture or "").lower()
                        for member in region
                    ):
                        matched_region = region
                        break
            if matched_region is not None:
                matched_region.append(loc)
            else:
                orphan_by_city[loc_city or "unlocated"].append(loc)

        for group in orphan_by_city.values():
            regions.append(group)

        regions.sort(key=len, reverse=True)
        return regions

    def _cluster_within_region(
        self,
        region: list[PilgrimageLocation],
        *,
        max_per_cluster: int = 4,
        daily_radius_km: float = 12.0,
    ) -> list[list[PilgrimageLocation]]:
        with_coords = sorted(
            (loc for loc in region if loc.coordinates is not None),
            key=lambda item: item.confidence_score,
            reverse=True,
        )
        without_coords = [loc for loc in region if loc.coordinates is None]

        region_clusters: list[list[PilgrimageLocation]] = []
        remaining = list(range(len(with_coords)))

        while remaining:
            center_idx = remaining.pop(0)
            group = [center_idx]
            center_coord = with_coords[center_idx].coordinates

            distances = sorted(
                (
                    self.calculate_distance(center_coord, with_coords[idx].coordinates),
                    idx,
                )
                for idx in remaining
            )
            for dist_km, idx in distances:
                if len(group) >= max_per_cluster:
                    break
                if dist_km <= daily_radius_km:
                    group.append(idx)
                    remaining.remove(idx)

            region_clusters.append([with_coords[i] for i in group])

        for loc in without_coords:
            placed = False
            for cl in region_clusters:
                if len(cl) < max_per_cluster:
                    cl.append(loc)
                    placed = True
                    break
            if not placed:
                region_clusters.append([loc])

        return region_clusters

    def cluster_locations_by_proximity(
        self,
        locations: list[PilgrimageLocation],
        *,
        max_per_cluster: int = 4,
        daily_radius_km: float = 12.0,
    ) -> list[list[PilgrimageLocation]]:
        """Cluster locations into flat region-coherent daily groups."""
        if not locations:
            return []
        clusters: list[list[PilgrimageLocation]] = []
        for region in self._partition_regions(locations):
            clusters.extend(
                self._cluster_within_region(
                    region,
                    max_per_cluster=max_per_cluster,
                    daily_radius_km=daily_radius_km,
                )
            )
        return clusters

    def optimize_route_within_cluster(
        self, locations: list[PilgrimageLocation]
    ) -> list[PilgrimageLocation]:
        """Order stops using nearest-neighbor TSP followed by 2-opt refinement."""
        if len(locations) <= 2:
            return list(locations)

        remaining = list(locations)
        morning_idx = next(
            (i for i, loc in enumerate(remaining) if self.determine_optimal_visit_time(loc) == "morning"),
            0,
        )
        ordered = [remaining.pop(morning_idx)]

        while remaining:
            current = ordered[-1]
            if current.coordinates is None:
                ordered.append(remaining.pop(0))
                continue

            best_idx = 0
            best_dist = float("inf")
            for idx, cand in enumerate(remaining):
                if cand.coordinates is not None:
                    dist = self.calculate_distance(current.coordinates, cand.coordinates)
                    if dist < best_dist:
                        best_dist = dist
                        best_idx = idx
            ordered.append(remaining.pop(best_idx))

        if len(ordered) >= 4 and all(loc.coordinates is not None for loc in ordered):
            ordered = self._two_opt(ordered)

        return ordered

    def _route_distance(self, route: list[PilgrimageLocation]) -> float:
        return sum(
            self.calculate_distance(route[i].coordinates, route[i + 1].coordinates)
            for i in range(len(route) - 1)
        )

    def _two_opt(self, route: list[PilgrimageLocation]) -> list[PilgrimageLocation]:
        best = list(route)
        best_dist = self._route_distance(best)
        improved = True
        while improved:
            improved = False
            for i in range(1, len(best) - 1):
                for j in range(i + 1, len(best)):
                    candidate = best[:i] + list(reversed(best[i : j + 1])) + best[j + 1 :]
                    cand_dist = self._route_distance(candidate)
                    if cand_dist + 1e-6 < best_dist:
                        best = candidate
                        best_dist = cand_dist
                        improved = True
        return best

    @staticmethod
    def _format_clock(minutes_from_midnight: int) -> str:
        """Format minutes since midnight without silently wrapping past 24:00."""
        day_offset, rem = divmod(minutes_from_midnight, 24 * 60)
        hours, mins = divmod(rem, 60)
        if day_offset > 0:
            return f"{hours:02d}:{mins:02d} (+{day_offset}d)"
        return f"{hours:02d}:{mins:02d}"

    def generate_daily_itinerary(
        self,
        locations: list[PilgrimageLocation],
        day_number: int,
        transportation_mode: str = "mixed",
        budget_level: str = "standard",
        start_time_minutes: int | None = None,
    ) -> DailyItinerary:
        """Build a timed `DailyItinerary` with realistic transit legs and budget estimates."""
        if not locations:
            return DailyItinerary(day=day_number, title=f"Day {day_number} - Free Exploration")

        ordered = self.optimize_route_within_cluster(locations)
        profile = self.COST_PROFILES.get(budget_level, self.COST_PROFILES["standard"])

        stops: list[ScheduledStop] = []
        travel_times: list[int] = []
        total_visit_time = 0
        total_travel_time = 0
        transport_cost = 0.0

        current_clock = (
            start_time_minutes if start_time_minutes is not None else self.DAY_START_MINUTES
        )
        lunch_taken = current_clock >= 13 * 60

        for idx, loc in enumerate(ordered):
            if not lunch_taken and current_clock >= 12 * 60 and idx > 0:
                current_clock += 45  # Built-in lunch break
                lunch_taken = True

            visit_min = self.estimate_visit_duration(loc)
            arrival = self._format_clock(current_clock)
            departure = self._format_clock(current_clock + visit_min)
            current_clock += visit_min
            total_visit_time += visit_min

            activity = f"Visit {loc.name}"
            if loc.scene_description:
                activity += f" — {loc.scene_description}"
            elif loc.anime_title:
                activity += f" (featured in {loc.anime_title})"

            leg_minutes: int | None = None
            leg_km: float | None = None
            leg_mode: str | None = None

            if idx < len(ordered) - 1:
                next_loc = ordered[idx + 1]
                if loc.coordinates is not None and next_loc.coordinates is not None:
                    dist_km = self.calculate_distance(loc.coordinates, next_loc.coordinates)
                    leg_km = round(dist_km, 2)
                    leg_minutes, leg_mode = self.estimate_travel_leg(
                        dist_km,
                        transportation_mode,
                        start_coord=loc.coordinates,
                        end_coord=next_loc.coordinates,
                    )
                    if leg_mode == "domestic flight + airport transfer":
                        transport_cost += profile["domestic_flight"]
                    elif dist_km > self.INTERCITY_DISTANCE_KM:
                        transport_cost += dist_km * profile["intercity_per_km"]
                    elif dist_km >= 0.8:
                        transport_cost += profile["transit_per_leg"]
                else:
                    leg_minutes, leg_mode = 25, "local transit (est.)"
                    transport_cost += profile["transit_per_leg"]

                travel_times.append(leg_minutes)
                total_travel_time += leg_minutes
                current_clock += leg_minutes

            stops.append(
                ScheduledStop(
                    order=idx + 1,
                    location=loc,
                    arrival_time=arrival,
                    departure_time=departure,
                    visit_duration_minutes=visit_min,
                    activity=activity,
                    travel_to_next_minutes=leg_minutes,
                    travel_to_next_km=leg_km,
                    travel_mode_to_next=leg_mode,
                )
            )

        meals_count = 3 if (total_visit_time + total_travel_time) >= 300 else 2
        food_cost = meals_count * profile["meal"]
        attraction_cost = sum(
            profile["attraction"]
            for loc in ordered
            if not any(free_kw in loc.name.lower() for free_kw in ("station", "crossing", "bridge", "street", "stairs"))
        )

        estimated_cost = {
            "transportation": round(transport_cost, 0),
            "food": round(food_cost, 0),
            "attractions": round(attraction_cost, 0),
            "total": round(transport_cost + food_cost + attraction_cost, 0),
        }

        city_counts: dict[str, int] = defaultdict(int)
        for loc in ordered:
            city_counts[self._region_label(loc)] += 1
        city_focus = max(city_counts, key=city_counts.get) if city_counts else "Japan"

        notes: list[str] = []
        if current_clock > self.DAY_LATE_WARNING_MINUTES:
            notes.append(
                f"Schedule runs late (ending around {self._format_clock(current_clock)}); "
                "consider starting earlier or dropping a lower-priority stop."
            )
        elif len(ordered) >= 5:
            notes.append("Full schedule today — consider starting around 08:30 to beat crowds.")

        if any(stop.travel_to_next_km and stop.travel_to_next_km > self.INTERCITY_DISTANCE_KM for stop in stops):
            notes.append(
                "Includes an inter-city rail transfer — reserve Shinkansen/limited express seats in advance."
            )
        morning_spots = [
            loc.name for loc in ordered if self.determine_optimal_visit_time(loc) == "morning"
        ]
        if morning_spots:
            notes.append(f"Best visited early for quiet photos: {', '.join(morning_spots[:2])}.")

        return DailyItinerary(
            day=day_number,
            title=f"Day {day_number}: {city_focus} Pilgrimage",
            city_focus=city_focus,
            stops=stops,
            locations=[stop.location.name for stop in stops],
            activities=[stop.activity for stop in stops],
            travel_times=travel_times,
            total_travel_time=total_travel_time,
            total_visit_time=total_visit_time,
            estimated_cost=estimated_cost,
            notes=notes,
        )

    @staticmethod
    def _avg_confidence(cluster: list[PilgrimageLocation]) -> float:
        if not cluster:
            return 0.0
        return sum(loc.confidence_score for loc in cluster) / len(cluster)

    @staticmethod
    def _region_matches_mentioned(
        region_clusters: list[list[PilgrimageLocation]], mentioned: list[str]
    ) -> int:
        """Return earliest index in `mentioned` matching this region (or a large sentinel)."""
        specific_mentions = [m.strip().lower() for m in mentioned if m.strip().lower() != "japan"]
        if not specific_mentions:
            return 999
        region_text = " ".join(
            f"{loc.city} {loc.prefecture} {loc.real_world_address} {loc.name}".lower()
            for cl in region_clusters
            for loc in cl
        )
        for idx, place in enumerate(specific_mentions):
            if place in region_text:
                return idx
        return 999

    def _fit_region_clusters_to_days(
        self,
        by_region: list[list[list[PilgrimageLocation]]],
        target_days: int,
        *,
        max_per_day: int,
        locations_mentioned: list[str] | None = None,
    ) -> tuple[list[list[PilgrimageLocation]], int]:
        """Fit region-grouped clusters into `target_days` with regional coverage + pace limits.

        When more clusters exist than `target_days`, keeps at least one cluster per distinct
        region first (prioritizing regions mentioned by the user), then fills any remaining
        days by cluster confidence. Preserves regional contiguity so days in the same city
        stay adjacent.
        """
        flat_clusters = [cl for region_cls in by_region for cl in region_cls]
        if not flat_clusters or target_days <= 0:
            return [], 0

        total_input = sum(len(c) for c in flat_clusters)

        if len(flat_clusters) == target_days:
            trimmed = [c[:max_per_day] for c in flat_clusters]
            return trimmed, max(0, total_input - sum(len(c) for c in trimmed))

        if len(flat_clusters) < target_days:
            working = [list(c) for c in flat_clusters]
            while len(working) < target_days:
                splittable = [
                    (len(c), idx) for idx, c in enumerate(working) if len(c) >= 2
                ]
                if not splittable:
                    break
                _, largest_idx = max(splittable)
                chunk = working[largest_idx]
                mid = len(chunk) // 2
                working[largest_idx : largest_idx + 1] = [chunk[:mid], chunk[mid:]]
            trimmed = [c[:max_per_day] for c in working]
            return trimmed, max(0, total_input - sum(len(c) for c in trimmed))

        # Order regions: explicitly mentioned regions first (in user's order), then
        # coordinate-bearing regions ahead of coordinate-less regions (so a single
        # un-geocoded spot cannot displace a real geocoded city), then confidence and size.
        mentions = locations_mentioned or []
        ordered_region_indices = sorted(
            range(len(by_region)),
            key=lambda r_idx: (
                self._region_matches_mentioned(by_region[r_idx], mentions),
                0
                if any(loc.coordinates is not None for cl in by_region[r_idx] for loc in cl)
                else 1,
                -max((self._avg_confidence(cl) for cl in by_region[r_idx]), default=0.0),
                -sum(len(cl) for cl in by_region[r_idx]),
            ),
        )

        selected: list[tuple[int, int, list[PilgrimageLocation]]] = []
        selected_keys: set[tuple[int, int]] = set()

        # Pass 1: Cover at least one best cluster per distinct region (up to target_days)
        for r_idx in ordered_region_indices:
            if len(selected) >= target_days:
                break
            best_c_idx = max(
                range(len(by_region[r_idx])),
                key=lambda c_idx: (
                    self._avg_confidence(by_region[r_idx][c_idx]),
                    len(by_region[r_idx][c_idx]),
                ),
            )
            selected.append((r_idx, best_c_idx, list(by_region[r_idx][best_c_idx][:max_per_day])))
            selected_keys.add((r_idx, best_c_idx))

        # Pass 2: Fill remaining days with highest-confidence remaining clusters
        if len(selected) < target_days:
            remaining_candidates = [
                (r_idx, c_idx, by_region[r_idx][c_idx])
                for r_idx in ordered_region_indices
                for c_idx in range(len(by_region[r_idx]))
                if (r_idx, c_idx) not in selected_keys
            ]
            remaining_candidates.sort(
                key=lambda item: (self._avg_confidence(item[2]), len(item[2])),
                reverse=True,
            )
            for r_idx, c_idx, cluster in remaining_candidates:
                if len(selected) >= target_days:
                    break
                selected.append((r_idx, c_idx, list(cluster[:max_per_day])))
                selected_keys.add((r_idx, c_idx))

        # Keep days grouped by region in user-mentioned order (no Tokyo -> Hida -> Tokyo ping-pong)
        region_rank = {r_idx: pos for pos, r_idx in enumerate(ordered_region_indices)}
        selected.sort(key=lambda item: (region_rank[item[0]], item[1]))

        # Top up spare slots in a day ONLY using omitted stops from the SAME region
        for r_idx, _, day_group in selected:
            if len(day_group) >= max_per_day:
                continue
            for c_idx, cluster in enumerate(by_region[r_idx]):
                if (r_idx, c_idx) in selected_keys:
                    continue
                for loc in cluster:
                    if len(day_group) >= max_per_day:
                        break
                    if loc not in day_group:
                        day_group.append(loc)

        daily_groups = [group for _, _, group in selected]
        kept = sum(len(c) for c in daily_groups)
        return daily_groups, max(0, total_input - kept)

    @staticmethod
    def _first_coord(locations: list[PilgrimageLocation]) -> Coordinates | None:
        return next((loc.coordinates for loc in locations if loc.coordinates), None)

    @staticmethod
    def _last_coord(day: DailyItinerary) -> Coordinates | None:
        return next(
            (s.location.coordinates for s in reversed(day.stops) if s.location.coordinates),
            None,
        )

    def generate_travel_plan(
        self,
        locations: list[PilgrimageLocation],
        query_analysis: QueryAnalysis,
        duration_days: int | None = None,
    ) -> TravelPlan:
        """Create an optimized multi-day `TravelPlan` from discovered locations."""
        if not locations:
            return TravelPlan(
                trip_title="Anime Pilgrimage Trip",
                destination="Japan",
                duration_days=0,
                total_locations=0,
            )

        prefs = query_analysis.trip_preferences
        budget_level = prefs.travel_style
        max_per_day = self.PACE_MAX_STOPS_PER_DAY.get(prefs.pace, 4)

        if prefs.transport_preference:
            transportation_mode = prefs.transport_preference
        elif budget_level == "luxury":
            transportation_mode = "taxi"
        elif budget_level in ("budget", "backpacker"):
            transportation_mode = "subway"
        else:
            transportation_mode = "mixed"

        regions_raw = self._partition_regions(locations)
        by_region = [
            self._cluster_within_region(region, max_per_cluster=max_per_day)
            for region in regions_raw
        ]
        total_clusters = sum(len(rc) for rc in by_region)

        requested_days = duration_days or prefs.duration_days
        if requested_days is None:
            requested_days = max(1, total_clusters)

        daily_groups, omitted_count = self._fit_region_clusters_to_days(
            by_region,
            requested_days,
            max_per_day=max_per_day,
            locations_mentioned=query_analysis.locations_mentioned,
        )

        profile = self.COST_PROFILES.get(budget_level, self.COST_PROFILES["standard"])
        daily_itineraries: list[DailyItinerary] = []
        total_cost: dict[str, float] = defaultdict(float)

        for day_idx, day_locations in enumerate(daily_groups, 1):
            # Check if this day requires an inter-city transfer from the previous day
            start_time_minutes = self.DAY_START_MINUTES
            transfer_info: tuple[str, float, int, str, float, int, bool] | None = None

            if daily_itineraries:
                prev_day = daily_itineraries[-1]
                prev_coord = self._last_coord(prev_day)
                ordered_preview = self.optimize_route_within_cluster(day_locations)
                next_coord = self._first_coord(ordered_preview)
                if prev_coord is not None and next_coord is not None:
                    dist_km = self.calculate_distance(prev_coord, next_coord)
                    if dist_km > self.INTERCITY_DISTANCE_KM:
                        transfer_min, transfer_mode = self.estimate_travel_leg(
                            dist_km,
                            transportation_mode,
                            start_coord=prev_coord,
                            end_coord=next_coord,
                        )
                        transfer_cost = (
                            profile["domestic_flight"]
                            if transfer_mode == "domestic flight + airport transfer"
                            else round(dist_km * profile["intercity_per_km"], 0)
                        )
                        depart_min = self.INTERCITY_DEPART_MINUTES
                        arrive_min = depart_min + transfer_min
                        rounded_start = math.ceil(arrive_min / 5) * 5
                        move_to_prior_evening = (
                            rounded_start >= self.TRANSFER_LATE_ARRIVAL_MINUTES
                        )
                        if not move_to_prior_evening:
                            start_time_minutes = rounded_start
                        transfer_info = (
                            prev_day.city_focus,
                            dist_km,
                            transfer_min,
                            transfer_mode,
                            transfer_cost,
                            depart_min,
                            move_to_prior_evening,
                        )

            itinerary = self.generate_daily_itinerary(
                day_locations,
                day_idx,
                transportation_mode=transportation_mode,
                budget_level=budget_level,
                start_time_minutes=start_time_minutes,
            )

            if transfer_info is not None:
                (
                    prev_city,
                    dist_km,
                    transfer_min,
                    transfer_mode,
                    transfer_cost,
                    depart_min,
                    move_to_prior_evening,
                ) = transfer_info

                if move_to_prior_evening:
                    # Shift very long (>6.5h) transfer to the prior evening so destination
                    # sightseeing starts fresh at 09:00 instead of late at night.
                    prev_day = daily_itineraries[-1]
                    prev_day.estimated_cost["transportation"] = round(
                        prev_day.estimated_cost.get("transportation", 0.0) + transfer_cost, 0
                    )
                    prev_day.estimated_cost["total"] = round(
                        prev_day.estimated_cost.get("total", 0.0) + transfer_cost, 0
                    )
                    prev_day.total_travel_time += transfer_min
                    prev_day.notes.append(
                        f"Evening inter-city transfer from {prev_city} to {itinerary.city_focus} "
                        f"(~{dist_km:.0f} km straight-line, ~{transfer_min} min via {transfer_mode}, "
                        f"est. ¥{transfer_cost:,.0f}) — travel overnight/evening so Day {day_idx} "
                        "sightseeing starts fresh at 09:00."
                    )
                else:
                    itinerary.estimated_cost["transportation"] = round(
                        itinerary.estimated_cost.get("transportation", 0.0) + transfer_cost, 0
                    )
                    itinerary.estimated_cost["total"] = round(
                        itinerary.estimated_cost.get("total", 0.0) + transfer_cost, 0
                    )
                    itinerary.total_travel_time += transfer_min
                    itinerary.notes.insert(
                        0,
                        f"{self._format_clock(depart_min)}–{self._format_clock(depart_min + transfer_min)}: "
                        f"Inter-city transfer from {prev_city} to {itinerary.city_focus} "
                        f"(~{dist_km:.0f} km straight-line, ~{transfer_min} min via {transfer_mode}, "
                        f"est. ¥{transfer_cost:,.0f}).",
                    )

            daily_itineraries.append(itinerary)

        for itinerary in daily_itineraries:
            for key, amount in itinerary.estimated_cost.items():
                if key != "total":
                    total_cost[key] += amount

        actual_days = len(daily_itineraries)
        nights = max(0, actual_days - 1)
        if nights > 0:
            total_cost["accommodation"] = round(nights * profile["accommodation"], 0)
        total_cost["total"] = round(sum(total_cost.values()), 0)

        anime_titles = [a.anime_title for a in query_analysis.identified_anime]
        trip_title = (
            f"{' & '.join(anime_titles[:2])} Pilgrimage Trip"
            if anime_titles
            else "Anime Pilgrimage Trip"
        )

        regions = list(
            dict.fromkeys(day.city_focus for day in daily_itineraries if day.city_focus)
        )
        if not regions and query_analysis.locations_mentioned:
            regions = list(query_analysis.locations_mentioned)
        destination = " & ".join(regions[:3]) if regions else "Japan"

        tips = self._general_tips(anime_titles, budget_level, len(regions) > 1)
        if omitted_count > 0:
            tips.insert(
                0,
                f"Focused on the top {sum(len(d.stops) for d in daily_itineraries)} stops to "
                f"respect your {prefs.pace} pace ({max_per_day} stops/day over {actual_days} "
                f"day(s)); {omitted_count} additional spot(s) were omitted.",
            )

        return TravelPlan(
            trip_title=trip_title,
            destination=destination,
            regions=regions,
            duration_days=actual_days,
            total_locations=sum(len(day.stops) for day in daily_itineraries),
            daily_itineraries=daily_itineraries,
            total_estimated_cost=dict(total_cost),
            budget_level=budget_level,
            transportation_mode=transportation_mode,
            accommodation_suggestions=self._accommodation_suggestions(budget_level, destination),
            general_tips=tips,
            emergency_contacts={
                "police": "110",
                "ambulance_fire": "119",
                "japan_visitor_hotline": "+81-50-3816-2787",
            },
        )

    @staticmethod
    def _accommodation_suggestions(budget_level: str, destination: str) -> list[str]:
        if budget_level in ("budget", "backpacker"):
            return [
                f"Hostels, guesthouses, or capsule hotels near major stations in {destination}",
                "Business hotel chains (Toyoko Inn, APA, Sotetsu Fresa) booked 3-4 weeks ahead",
            ]
        if budget_level == "luxury":
            return [
                f"Upscale city hotels or traditional ryokans with onsen in {destination}",
                "Consider luggage forwarding (Takkyubin) between cities for hands-free sightseeing",
            ]
        return [
            f"Mid-range business or boutique hotels near JR/subway hubs in {destination}",
            "Stay near a main transit line so early-morning pilgrimage visits are effortless",
        ]

    @staticmethod
    def _general_tips(
        anime_titles: list[str], budget_level: str, multi_city: bool
    ) -> list[str]:
        focus = anime_titles[0] if anime_titles else "your chosen anime"
        tips = [
            f"Save reference screenshots from {focus} on your phone to line up real-world camera angles.",
            "Load a Suica, PASMO, or ICOCA IC card (or Apple Wallet transit card) for seamless rail/bus rides.",
            "Keep voices low and respect residential neighborhoods and shrine photography signs.",
            "Carry some Japanese yen in cash for smaller shrines, local cafes, and coin lockers.",
        ]
        if multi_city:
            tips.append(
                "Compare point-to-point Shinkansen/regional rail passes (e.g., JR East/West/Takayama-Hokuriku) before buying a nationwide JR Pass."
            )
        if budget_level in ("budget", "backpacker"):
            tips.append("Use convenience stores (7-Eleven, Lawson, FamilyMart) and set-lunch specials to keep meal costs low.")
        return tips
