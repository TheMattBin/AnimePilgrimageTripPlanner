"""Tests for TripPlanner multi-city clustering, pace limits, inter-city cost, and clock overflow."""

from anime_pilgrimage.components.trip_planner import TripPlanner
from anime_pilgrimage.models import (
    AnimeIdentification,
    Coordinates,
    PilgrimageLocation,
    QueryAnalysis,
    TripPreferences,
    UserQuery,
)


def _make_analysis(
    duration_days: int | None = 2,
    travel_style: str = "standard",
    pace: str = "balanced",
) -> QueryAnalysis:
    return QueryAnalysis(
        original_query=UserQuery(original_text="Your Name trip", normalized_text="Your Name trip"),
        identified_anime=[AnimeIdentification(anime_title="Your Name")],
        locations_mentioned=["Tokyo", "Hida"],
        trip_preferences=TripPreferences(
            duration_days=duration_days,
            travel_style=travel_style,  # type: ignore[arg-type]
            pace=pace,  # type: ignore[arg-type]
        ),
        analysis_confidence=0.9,
    )


def test_multi_city_clustering_and_no_dropped_unlocated_spots():
    locations = [
        PilgrimageLocation(
            name="Suga Shrine",
            anime_title="Your Name",
            city="Shinjuku",
            prefecture="Tokyo",
            coordinates=Coordinates(lat=35.6852, lng=139.7219),
        ),
        PilgrimageLocation(
            name="NTT Docomo Yoyogi Building",
            anime_title="Your Name",
            city="Shibuya",
            prefecture="Tokyo",
            coordinates=Coordinates(lat=35.6844, lng=139.7033),
        ),
        PilgrimageLocation(
            name="Cafe La Boheme Shinjuku",
            anime_title="Your Name",
            city="Shinjuku",
            prefecture="Tokyo",
            coordinates=None,  # Must NOT be dropped
        ),
        PilgrimageLocation(
            name="Hida-Furukawa Station",
            anime_title="Your Name",
            city="Hida",
            prefecture="Gifu",
            coordinates=Coordinates(lat=36.2367, lng=137.1897),
        ),
    ]

    planner = TripPlanner()
    plan = planner.generate_travel_plan(locations, _make_analysis(duration_days=2))

    assert plan.duration_days == 2
    assert plan.total_locations == 4
    day_sets = [set(day.locations) for day in plan.daily_itineraries]
    assert {"Suga Shrine", "NTT Docomo Yoyogi Building", "Cafe La Boheme Shinjuku"} in day_sets
    assert {"Hida-Furukawa Station"} in day_sets


def test_intercity_transfer_between_days_is_priced_and_noted():
    """Regression test for Bug 4 & transfer schedule timing: Tokyo -> Hida includes cost + morning travel."""
    locations = [
        PilgrimageLocation(
            name="Suga Shrine",
            anime_title="Your Name",
            city="Shinjuku",
            prefecture="Tokyo",
            coordinates=Coordinates(lat=35.6852, lng=139.7219),
        ),
        PilgrimageLocation(
            name="Hida-Furukawa Station",
            anime_title="Your Name",
            city="Hida",
            prefecture="Gifu",
            coordinates=Coordinates(lat=36.2367, lng=137.1897),
        ),
    ]

    planner = TripPlanner()
    plan = planner.generate_travel_plan(
        locations, _make_analysis(duration_days=2, travel_style="standard")
    )

    assert plan.duration_days == 2
    assert plan.total_estimated_cost["transportation"] >= 5000
    day2 = plan.daily_itineraries[1]
    assert any("Inter-city transfer" in note for note in day2.notes)
    # Realistic ~3h10m Tokyo->Toyama (Shinkansen) + Hida Express shifts Day 2's first stop past 11:00
    assert day2.total_travel_time >= 180
    first_arrival_hour = int(day2.stops[0].arrival_time.split(":")[0])
    assert first_arrival_hour >= 11


def test_two_city_trip_keeps_both_cities_even_when_one_has_more_spots():
    """Regression test: 2-day Tokyo & Hida trip with 8 Tokyo + 2 Hida spots must keep both cities."""
    tokyo_spots = [
        PilgrimageLocation(
            name=f"Tokyo Spot {i} Shrine",
            anime_title="Your Name",
            city="Shinjuku",
            prefecture="Tokyo",
            coordinates=Coordinates(lat=35.685 + i * 0.004, lng=139.710 + i * 0.004),
            confidence_score=0.80,
        )
        for i in range(8)
    ]
    hida_spots = [
        PilgrimageLocation(
            name=f"Hida Spot {i} Station",
            anime_title="Your Name",
            city="Hida",
            prefecture="Gifu",
            coordinates=Coordinates(lat=36.236 + i * 0.003, lng=137.189 + i * 0.003),
            confidence_score=0.95,
        )
        for i in range(2)
    ]

    planner = TripPlanner()
    plan = planner.generate_travel_plan(
        tokyo_spots + hida_spots,
        _make_analysis(duration_days=2, pace="balanced"),
    )

    assert plan.duration_days == 2
    prefectures_by_day = [
        {stop.location.prefecture for stop in day.stops} for day in plan.daily_itineraries
    ]
    assert {"Tokyo"} in prefectures_by_day
    assert {"Gifu"} in prefectures_by_day
    assert all(len(day.stops) <= 4 for day in plan.daily_itineraries)


def test_pace_limit_enforced_when_merging_many_spots_into_day_trip():
    """Regression test for Bug 3: 12 spots in a 1-day trip must obey pace cap and stay coherent."""
    tokyo_spots = [
        PilgrimageLocation(
            name=f"Tokyo Spot {i} Shrine",
            anime_title="Your Name",
            city="Shinjuku",
            prefecture="Tokyo",
            coordinates=Coordinates(lat=35.685 + i * 0.005, lng=139.710 + i * 0.005),
            confidence_score=0.95 - i * 0.01,
        )
        for i in range(8)
    ]
    hida_spots = [
        PilgrimageLocation(
            name=f"Hida Spot {i} Temple",
            anime_title="Your Name",
            city="Hida",
            prefecture="Gifu",
            coordinates=Coordinates(lat=36.236 + i * 0.003, lng=137.189 + i * 0.003),
            confidence_score=0.85,
        )
        for i in range(4)
    ]

    planner = TripPlanner()
    plan = planner.generate_travel_plan(
        tokyo_spots + hida_spots,
        _make_analysis(duration_days=1, pace="balanced"),
    )

    assert plan.duration_days == 1
    assert len(plan.daily_itineraries[0].stops) <= TripPlanner.PACE_MAX_STOPS_PER_DAY["balanced"]
    # Should stay in Tokyo rather than teleporting to Hida inside a day trip
    assert all("Tokyo" in stop.location.prefecture for stop in plan.daily_itineraries[0].stops)
    # Schedule should finish well before late evening
    last_dep = plan.daily_itineraries[0].stops[-1].departure_time
    assert int(last_dep.split(":")[0]) < 19
    assert any("omitted" in tip for tip in plan.general_tips)


def test_format_clock_flags_midnight_overflow_instead_of_wrapping():
    assert TripPlanner._format_clock(23 * 60 + 30) == "23:30"
    assert TripPlanner._format_clock(24 * 60 + 15) == "00:15 (+1d)"


def test_shinkansen_corridors_use_fast_speed_and_uji_starts_before_noon():
    """Regression test: Shinkansen corridors (Tokyo->Kyoto/Uji/Nagoya/Sendai) use ~150 km/h, not 65 km/h."""
    planner = TripPlanner()
    tokyo = Coordinates(lat=35.6812, lng=139.7671)
    nagoya = Coordinates(lat=35.1709, lng=136.8815)
    kyoto = Coordinates(lat=34.9858, lng=135.7588)
    sendai = Coordinates(lat=38.2601, lng=140.8824)
    hida = Coordinates(lat=36.2367, lng=137.1897)

    nagoya_min, nagoya_mode = planner.estimate_travel_leg(
        planner.calculate_distance(tokyo, nagoya), start_coord=tokyo, end_coord=nagoya
    )
    kyoto_min, kyoto_mode = planner.estimate_travel_leg(
        planner.calculate_distance(tokyo, kyoto), start_coord=tokyo, end_coord=kyoto
    )
    sendai_min, sendai_mode = planner.estimate_travel_leg(
        planner.calculate_distance(tokyo, sendai), start_coord=tokyo, end_coord=sendai
    )
    hida_min, hida_mode = planner.estimate_travel_leg(
        planner.calculate_distance(tokyo, hida), start_coord=tokyo, end_coord=hida
    )

    assert nagoya_mode == "shinkansen"
    assert kyoto_mode == "shinkansen"
    assert sendai_mode == "shinkansen"
    assert hida_mode == "shinkansen + limited express"
    assert nagoya_min < 150  # ~2h08m door-to-door
    assert kyoto_min < 190  # ~2h53m door-to-door
    assert sendai_min < 165  # ~2h27m door-to-door
    assert 175 <= hida_min <= 260  # ~3h09m via Toyama Hokuriku Shinkansen + Hida Express

    # Full 2-day Tokyo -> Uji trip starts Day 2 before noon (not 14:00)
    spots = [
        PilgrimageLocation(
            name="Tokyo Station",
            anime_title="Sound! Euphonium",
            city="Chiyoda",
            prefecture="Tokyo",
            coordinates=tokyo,
        ),
        PilgrimageLocation(
            name="Uji Bridge",
            anime_title="Sound! Euphonium",
            city="Uji",
            prefecture="Kyoto",
            coordinates=Coordinates(lat=34.8927, lng=135.8063),
        ),
    ]
    analysis = QueryAnalysis(
        original_query=UserQuery(original_text="Tokyo and Uji", normalized_text="Tokyo and Uji"),
        identified_anime=[AnimeIdentification(anime_title="Sound! Euphonium")],
        locations_mentioned=["Tokyo", "Uji"],
        trip_preferences=TripPreferences(duration_days=2, travel_style="standard"),
        analysis_confidence=0.9,
    )
    plan = planner.generate_travel_plan(spots, analysis)
    day2_first_hour = int(plan.daily_itineraries[1].stops[0].arrival_time.split(":")[0])
    assert day2_first_hour < 12


def test_ungeocoded_single_spot_does_not_displace_geocoded_region():
    """Regression test: un-geocoded regions rank behind geocoded regions when unmentioned."""
    tokyo_spots = [
        PilgrimageLocation(
            name=f"Tokyo Spot {i} Shrine",
            anime_title="Your Name",
            city="Shinjuku",
            prefecture="Tokyo",
            coordinates=Coordinates(lat=35.685 + i * 0.004, lng=139.710 + i * 0.004),
            confidence_score=0.85,
        )
        for i in range(4)
    ]
    hida_spots = [
        PilgrimageLocation(
            name=f"Hida Spot {i} Station",
            anime_title="Your Name",
            city="Hida",
            prefecture="Gifu",
            coordinates=Coordinates(lat=36.236 + i * 0.003, lng=137.189 + i * 0.003),
            confidence_score=0.90,
        )
        for i in range(2)
    ]
    ungeocoded_kamakura = PilgrimageLocation(
        name="Kamakura Mystery Spot",
        anime_title="Your Name",
        city="Kamakura",
        prefecture="Kanagawa",
        coordinates=None,
        confidence_score=0.95,  # Higher confidence, but no coordinates!
    )

    analysis = QueryAnalysis(
        original_query=UserQuery(original_text="Your Name 2 days", normalized_text="Your Name 2 days"),
        identified_anime=[AnimeIdentification(anime_title="Your Name")],
        locations_mentioned=[],  # No specific region mentioned
        trip_preferences=TripPreferences(duration_days=2, travel_style="standard"),
        analysis_confidence=0.9,
    )
    plan = TripPlanner().generate_travel_plan(
        tokyo_spots + hida_spots + [ungeocoded_kamakura], analysis
    )

    assert plan.duration_days == 2
    prefectures = {
        stop.location.prefecture
        for day in plan.daily_itineraries
        for stop in day.stops
    }
    assert prefectures == {"Tokyo", "Gifu"}


def test_long_distance_routes_use_domestic_flight_and_avoid_midnight_visits():
    """Regression test: Tokyo->Hita and Tokyo->Sapporo use domestic flight (~3.5h), not 13h rail."""
    planner = TripPlanner()
    tokyo = Coordinates(lat=35.6812, lng=139.7671)
    hita = Coordinates(lat=33.3213, lng=130.9410)
    sapporo = Coordinates(lat=43.0618, lng=141.3545)

    hita_min, hita_mode = planner.estimate_travel_leg(
        planner.calculate_distance(tokyo, hita), start_coord=tokyo, end_coord=hita
    )
    sapporo_min, sapporo_mode = planner.estimate_travel_leg(
        planner.calculate_distance(tokyo, sapporo), start_coord=tokyo, end_coord=sapporo
    )

    assert hita_mode == "domestic flight + airport transfer"
    assert sapporo_mode == "domestic flight + airport transfer"
    assert 180 <= hita_min <= 260
    assert 180 <= sapporo_min <= 260

    spots = [
        PilgrimageLocation(
            name="Tokyo Station",
            anime_title="Attack on Titan",
            city="Chiyoda",
            prefecture="Tokyo",
            coordinates=tokyo,
        ),
        PilgrimageLocation(
            name="Oyama Dam",
            anime_title="Attack on Titan",
            city="Hita",
            prefecture="Oita",
            coordinates=hita,
        ),
        PilgrimageLocation(
            name="Hita Station Statue",
            anime_title="Attack on Titan",
            city="Hita",
            prefecture="Oita",
            coordinates=Coordinates(lat=33.3168, lng=130.9383),
        ),
    ]
    analysis = QueryAnalysis(
        original_query=UserQuery(
            original_text="Attack on Titan in Tokyo and Hita",
            normalized_text="Attack on Titan in Tokyo and Hita",
        ),
        identified_anime=[AnimeIdentification(anime_title="Attack on Titan")],
        locations_mentioned=["Tokyo", "Hita"],
        trip_preferences=TripPreferences(duration_days=2, travel_style="standard"),
        analysis_confidence=0.9,
    )
    plan = planner.generate_travel_plan(spots, analysis)
    day2 = plan.daily_itineraries[1]
    assert int(day2.stops[0].arrival_time.split(":")[0]) <= 13
    assert int(day2.stops[-1].departure_time.split(":")[0]) < 18
    assert plan.total_estimated_cost["transportation"] >= 20000


def test_short_intercity_leg_uses_plain_rail_not_shinkansen():
    """Regression test: Tokyo->Kamakura (<100 km) uses plain rail (~60 min), not shinkansen."""
    planner = TripPlanner()
    tokyo = Coordinates(lat=35.6812, lng=139.7671)
    kamakura = Coordinates(lat=35.3192, lng=139.5467)
    minutes, mode = planner.estimate_travel_leg(
        planner.calculate_distance(tokyo, kamakura), start_coord=tokyo, end_coord=kamakura
    )
    assert mode == "rail"
    assert 50 <= minutes <= 75


def test_very_long_regional_transfer_arriving_after_1500_moves_to_prior_evening():
    """Off-Shinkansen transfers arriving >= 15:00 move to prior evening so Day 2 starts at 09:00."""
    # ~460 km off-Shinkansen (Hida-Furukawa -> Matsue, Shimane): ~460/65*60 + 35 = 460 min -> 16:10 arrival
    spots = [
        PilgrimageLocation(
            name="Hida-Furukawa Station",
            anime_title="Demo",
            city="Hida",
            prefecture="Gifu",
            coordinates=Coordinates(lat=36.2367, lng=137.1897),
        ),
        PilgrimageLocation(
            name="Matsue Castle",
            anime_title="Demo",
            city="Matsue",
            prefecture="Shimane",
            coordinates=Coordinates(lat=35.4751, lng=133.0507),
        ),
    ]
    analysis = QueryAnalysis(
        original_query=UserQuery(original_text="Hida and Matsue", normalized_text="Hida and Matsue"),
        identified_anime=[AnimeIdentification(anime_title="Demo")],
        locations_mentioned=["Hida", "Matsue"],
        trip_preferences=TripPreferences(duration_days=2, travel_style="standard"),
        analysis_confidence=0.9,
    )
    plan = TripPlanner().generate_travel_plan(spots, analysis)
    assert plan.daily_itineraries[1].stops[0].arrival_time == "09:00"
    assert any("Evening inter-city transfer" in note for note in plan.daily_itineraries[0].notes)


def test_one_shinkansen_end_uses_hybrid_shinkansen_plus_limited_express():
    """Kyoto->Hita (~480 km, Kyoto on Shinkansen, Hita 57 km from Hakata) takes ~4.5-5h, not 8h."""
    planner = TripPlanner()
    kyoto = Coordinates(lat=34.9858, lng=135.7588)
    hita = Coordinates(lat=33.3213, lng=130.9410)
    minutes, mode = planner.estimate_travel_leg(
        planner.calculate_distance(kyoto, hita), start_coord=kyoto, end_coord=hita
    )
    assert mode == "shinkansen + limited express"
    assert 240 <= minutes <= 320  # ~4h44m vs ~8h pure regional rail


def test_budget_levels_change_estimated_cost_and_include_lodging():
    locations = [
        PilgrimageLocation(
            name="Suga Shrine",
            anime_title="Your Name",
            city="Shinjuku",
            prefecture="Tokyo",
            coordinates=Coordinates(lat=35.6852, lng=139.7219),
        ),
        PilgrimageLocation(
            name="National Art Center Tokyo",
            anime_title="Your Name",
            city="Minato",
            prefecture="Tokyo",
            coordinates=Coordinates(lat=35.6653, lng=139.7264),
        ),
    ]

    planner = TripPlanner()
    budget_plan = planner.generate_travel_plan(
        locations, _make_analysis(duration_days=2, travel_style="budget")
    )
    luxury_plan = planner.generate_travel_plan(
        locations, _make_analysis(duration_days=2, travel_style="luxury")
    )

    assert "accommodation" in budget_plan.total_estimated_cost
    assert budget_plan.total_estimated_cost["accommodation"] > 0
    assert luxury_plan.total_estimated_cost["total"] > budget_plan.total_estimated_cost["total"]
