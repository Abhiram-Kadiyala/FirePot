import math
import folium


def build_map(neighborhoods_df, roads_df, coverage, stations, route=None, height=620):
    center = [neighborhoods_df["latitude"].mean(), neighborhoods_df["longitude"].mean()]

    # Use OpenStreetMap as the default basemap. It requires no API key.
    # A tile-free schematic layer is also available from the layer control,
    # which means the road graph and markers can still be inspected even if
    # external map tiles are unavailable on a restricted/offline network.
    m = folium.Map(
        location=center,
        zoom_start=13,
        tiles=None,
        control_scale=True,
        prefer_canvas=True,
    )

    folium.TileLayer(
        tiles="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
        attr='&copy; OpenStreetMap contributors',
        name="OpenStreetMap (No API Key)",
        overlay=False,
        control=True,
        show=True,
        max_zoom=19,
    ).add_to(m)

    # This feature group contains the actual FIREOPT graph. It does not depend
    # on any map API or API key.
    network_layer = folium.FeatureGroup(name="FIREOPT Road Network", overlay=True, show=True)
    network_layer.add_to(m)

    coords = {str(r.id): (r.latitude, r.longitude) for _, r in neighborhoods_df.iterrows()}

    route_edges = set()
    if route and len(route) > 1:
        route_edges = {tuple(sorted((route[i], route[i + 1]))) for i in range(len(route) - 1)}

    for _, r in roads_df.iterrows():
        u, v = str(r["from"]), str(r["to"])
        if u not in coords or v not in coords:
            continue
        on_route = tuple(sorted((u, v))) in route_edges
        folium.PolyLine(
            [coords[u], coords[v]],
            color="#16a34a" if on_route else "#64748b",
            weight=7 if on_route else 3,
            opacity=1.0 if on_route else 0.75,
            tooltip=f"{u} ↔ {v}: {float(r['time']):.1f} min",
        ).add_to(network_layer)

    for _, r in neighborhoods_df.iterrows():
        nid = str(r["id"])
        d = coverage["details"].get(nid, {})
        covered = bool(d.get("covered", False))
        t = d.get("time", math.inf)
        closest = d.get("closest_station", "-")

        if nid in stations:
            color, icon, prefix = "red", "fire", "fa"
        else:
            color, icon, prefix = ("blue" if covered else "darkred"), "home", "fa"

        status = "Covered" if covered else "Uncovered"
        time_text = "Unreachable" if not math.isfinite(t) else f"{t:.1f} min"
        popup = (
            f"<b>{nid} - {r['name']}</b><br>"
            f"Status: {status}<br>"
            f"Closest Station: {closest}<br>"
            f"Response Time: {time_text}"
        )

        folium.Marker(
            location=(r["latitude"], r["longitude"]),
            popup=folium.Popup(popup, max_width=260),
            tooltip=f"{nid} - {r['name']}",
            icon=folium.Icon(color=color, icon=icon, prefix=prefix),
        ).add_to(network_layer)

    folium.LayerControl(collapsed=False).add_to(m)

    # Keep all demo-city nodes in view.
    if coords:
        lats = [p[0] for p in coords.values()]
        lons = [p[1] for p in coords.values()]
        m.fit_bounds([[min(lats), min(lons)], [max(lats), max(lons)]], padding=(20, 20))

    return m
