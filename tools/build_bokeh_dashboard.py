import argparse
import calendar
import json
import math
from datetime import datetime
from pathlib import Path

from bokeh.embed import json_item
from bokeh.layouts import column
from bokeh.models import (
    ColumnDataSource,
    CustomJS,
    FactorRange,
    HoverTool,
    LinearAxis,
    OpenURL,
    RadioButtonGroup,
    Range1d,
    Select,
    Span,
    TapTool,
)
from bokeh.plotting import figure
from bokeh.transform import dodge


PURPLE = "#7650c8"
PINK = "#c45a89"
GOLD = "#d69a2d"
TEXT = "#302b3b"
MUTED = "#777181"
GRID = "#e9e6ef"
PLOT_HEIGHT = 320


def style_plot(plot, *, height=PLOT_HEIGHT):
    plot.height = height
    plot.sizing_mode = "stretch_width"
    plot.background_fill_color = "#ffffff"
    plot.border_fill_color = "#ffffff"
    plot.outline_line_color = None
    plot.toolbar.logo = None
    plot.toolbar.autohide = True
    plot.min_border_left = 12
    plot.min_border_right = 12
    plot.min_border_top = 12
    plot.min_border_bottom = 12
    for axis in (*plot.xaxis, *plot.yaxis):
        axis.axis_line_color = "#d8d4df"
        axis.major_tick_line_color = None
        axis.minor_tick_line_color = None
        axis.major_label_text_color = MUTED
        axis.major_label_text_font_size = "10px"
        axis.axis_label_text_color = TEXT
        axis.axis_label_text_font_size = "11px"
        axis.axis_label_text_font_style = "normal"
    for grid in (*plot.xgrid, *plot.ygrid):
        grid.grid_line_color = GRID
        grid.grid_line_alpha = 0.8
    return plot


def monthly_rows(report):
    return [
        row
        for row in report["monthly"]
        if row["days_recorded"] == calendar.monthrange(
            datetime.fromisoformat(row["month"]).year,
            datetime.fromisoformat(row["month"]).month,
        )[1]
    ]


def make_performance(report):
    def payload(rows, monthly):
        dates = [
            datetime.fromisoformat(row["month"] if monthly else row["date"])
            for row in rows
        ]
        widths = [19 * 24 * 60 * 60 * 1000 if monthly else 18 * 60 * 60 * 1000 for _ in rows]
        return {
            "date": [value.timestamp() * 1000 for value in dates],
            "month": [
                datetime.fromisoformat(row["month"] + "-01").strftime("%b %y")
                if monthly else datetime.fromisoformat(row["date"]).strftime("%b %d")
                for row in rows
            ],
            "impressions": [row["impressions"] for row in rows],
            "engagements": [row["engagements"] for row in rows],
            "complete": [
                not monthly or row["days_recorded"] == calendar.monthrange(
                    datetime.fromisoformat(row["month"]).year,
                    datetime.fromisoformat(row["month"]).month,
                )[1]
                for row in rows
            ],
            "rate": [
                round(row["engagements"] / row["impressions"] * 100, 3)
                if row["impressions"] else 0
                for row in rows
            ],
            "width": widths,
        }

    monthly = payload(report["monthly"], True)
    daily = payload(report["daily"], False)
    source = ColumnDataSource(monthly)
    plot = style_plot(figure(
        x_axis_type="datetime",
        height=350,
        y_axis_label="Impressions",
        tools="pan,wheel_zoom,box_zoom,reset,save",
        active_scroll="wheel_zoom",
    ))
    plot.extra_y_ranges = {"rate": Range1d(start=0, end=6)}
    plot.add_layout(LinearAxis(y_range_name="rate", axis_label="Engagement rate (%)"), "right")
    bars = plot.vbar(
        x="date",
        top="impressions",
        width="width",
        source=source,
        color=PURPLE,
        alpha=0.88,
    )
    line = plot.line(
        x="date",
        y="rate",
        source=source,
        y_range_name="rate",
        line_width=2.5,
        color=PINK,
    )
    points = plot.scatter(
        x="date",
        y="rate",
        source=source,
        y_range_name="rate",
        size=6,
        color=PINK,
        line_color="#ffffff",
        line_width=1,
    )
    complete_impressions = [
        value for value, complete in zip(monthly["impressions"], monthly["complete"])
        if complete
    ]
    avg_impressions = Span(
        location=sum(complete_impressions) / len(complete_impressions),
        dimension="width",
        line_color=PURPLE,
        line_dash="dashed",
        line_alpha=0.52,
    )
    full_months = monthly_rows(report)
    avg_rate = sum(
        row["engagements"] / row["impressions"] * 100
        for row in full_months if row["impressions"]
    ) / max(1, sum(bool(row["impressions"]) for row in full_months))
    avg_rate_span = Span(
        location=avg_rate,
        dimension="width",
        y_range_name="rate",
        line_color=PINK,
        line_dash="dotted",
        line_alpha=0.58,
    )
    plot.add_layout(avg_impressions)
    plot.add_layout(avg_rate_span)
    plot.add_tools(HoverTool(
        renderers=[bars, line, points],
        tooltips=[
            ("Period", "@month"),
            ("Impressions", "@impressions{0,0}"),
            ("Interactions", "@engagements{0,0}"),
            ("Engagement rate", "@rate{0.00}%"),
        ],
        mode="vline",
    ))
    controls = RadioButtonGroup(labels=["Monthly", "Daily"], active=0, width=180, height=34)
    controls.js_on_change("active", CustomJS(
        args={
            "source": source,
            "monthly": monthly,
            "daily": daily,
            "plot": plot,
            "avgImpressions": avg_impressions,
            "avgRate": avg_rate_span,
        },
        code="""
            const data = cb_obj.active === 0 ? monthly : daily;
            source.data = data;
            const values = data.date;
            plot.x_range.start = values[0];
            plot.x_range.end = values[values.length - 1];
            const full = data.rate.filter((value, index) => data.complete[index] && value > 0);
            const impressions = data.impressions.filter((value, index) => data.complete[index]);
            avgImpressions.location = impressions.reduce((a, b) => a + b, 0) / impressions.length;
            avgRate.location = full.reduce((a, b) => a + b, 0) / Math.max(1, full.length);
            const label = document.getElementById('average-reference-label');
            if (label) label.textContent = cb_obj.active === 0
              ? 'Dashed lines · complete-month averages'
              : 'Dashed lines · daily averages';
        """,
    ))
    return column(controls, plot, sizing_mode="stretch_width", spacing=8)


def make_followers(report):
    data = {
        "month": [
            datetime.fromisoformat(row["month"] + "-01").strftime("%b %y")
            for row in report["monthly"]
        ],
        "new_followers": [row["new_followers"] for row in report["monthly"]],
    }
    source = ColumnDataSource(data)
    plot = style_plot(figure(
        x_range=data["month"],
        height=230,
        y_axis_label="New followers",
        tools="pan,wheel_zoom,reset,save",
    ))
    line = plot.line(
        x="month", y="new_followers", source=source, color=PURPLE, line_width=2.5,
    )
    points = plot.scatter(
        x="month", y="new_followers", source=source, color=PURPLE,
        size=8, line_color="#ffffff", line_width=1.5,
    )
    complete = monthly_rows(report)
    average = sum(row["new_followers"] for row in complete) / max(len(complete), 1)
    plot.add_layout(Span(
        location=average,
        dimension="width",
        line_color=GOLD,
        line_dash="dashed",
        line_alpha=0.85,
    ))
    plot.add_tools(HoverTool(
        renderers=[line, points],
        tooltips=[("Month", "@month"), ("New followers", "@new_followers{0,0}")],
    ))
    return plot


def make_monthly_comparison(report):
    rows = monthly_rows(report)
    months = [datetime.fromisoformat(row["month"] + "-01").strftime("%b %y") for row in rows]
    source = ColumnDataSource({
        "month": months,
        "interactions": [row["engagements"] for row in rows],
        "new_followers": [row["new_followers"] for row in rows],
    })
    plot = style_plot(figure(
        x_range=FactorRange(factors=months),
        height=300,
        y_axis_label="Monthly total",
        tools="pan,wheel_zoom,reset,save",
    ))
    interactions = plot.vbar(
        x=dodge("month", -0.18, range=plot.x_range),
        top="interactions",
        width=0.34,
        source=source,
        color=PURPLE,
    )
    followers = plot.vbar(
        x=dodge("month", 0.18, range=plot.x_range),
        top="new_followers",
        width=0.34,
        source=source,
        color=PINK,
    )
    plot.add_tools(HoverTool(
        renderers=[interactions, followers],
        tooltips=[
            ("Month", "@month"),
            ("Interactions", "@interactions{0,0}"),
            ("New followers", "@new_followers{0,0}"),
        ],
    ))
    return plot


def mercator(longitude, latitude):
    earth_radius = 6_378_137
    longitude = max(-180, min(180, longitude))
    latitude = max(-85, min(85, latitude))
    return (
        earth_radius * math.radians(longitude),
        earth_radius * math.log(math.tan(math.pi / 4 + math.radians(latitude) / 2)),
    )


def land_lines(geojson):
    xs, ys = [], []
    for feature in geojson.get("features", []):
        geometry = feature.get("geometry") or {}
        coordinates = geometry.get("coordinates", [])
        polygons = coordinates if geometry.get("type") == "MultiPolygon" else [coordinates]
        for polygon in polygons:
            for ring in polygon[:1]:
                projected = [mercator(*point[:2]) for point in ring[::3]]
                if len(projected) >= 2:
                    xs.append([point[0] for point in projected])
                    ys.append([point[1] for point in projected])
    if not xs:
        raise ValueError("The world map asset contains no drawable land boundaries.")
    return ColumnDataSource({"xs": xs, "ys": ys})


def location_data(audience):
    items = audience.get("locations", {}).get("items", [])
    locations = [
        item for item in items
        if isinstance(item.get("longitude"), (int, float))
        and isinstance(item.get("latitude"), (int, float))
    ]
    if not locations:
        raise ValueError("The audience location data contains no mapped metro areas.")
    projected = [mercator(item["longitude"], item["latitude"]) for item in locations]
    return {
        "x": [point[0] for point in projected],
        "y": [point[1] for point in projected],
        "name": [item["name"] for item in locations],
        "label": [item["label"] for item in locations],
        "size": [max(8, min(24, 7 + math.sqrt(item["value"]) * 1.5)) for item in locations],
    }


def make_map(report, geojson):
    follower_data = location_data(report["audiences"]["followers"])
    content_data = location_data(report["audiences"]["content"])
    source = ColumnDataSource(follower_data)
    land = land_lines(geojson)
    plot = style_plot(figure(
        x_range=(-20_000_000, 20_000_000),
        y_range=(-11_000_000, 18_000_000),
        height=300,
        tools="pan,wheel_zoom,reset,save",
        match_aspect=True,
    ))
    plot.xaxis.visible = False
    plot.yaxis.visible = False
    plot.xgrid.visible = False
    plot.ygrid.visible = False
    plot.background_fill_color = "#fcfbfe"
    plot.multi_line(
        xs="xs", ys="ys", source=land,
        line_color="#c9c3d1", line_alpha=0.95, line_width=0.75,
    )
    bubbles = plot.scatter(
        x="x", y="y", size="size", source=source,
        fill_color=PURPLE, fill_alpha=0.78,
        line_color="#ffffff", line_width=1.2,
    )
    plot.add_tools(HoverTool(
        renderers=[bubbles],
        tooltips=[("Metro area", "@name"), ("Audience share", "@label")],
    ))
    controls = RadioButtonGroup(
        labels=["Followers", "Content audience"], active=0, width=230, height=34,
    )
    controls.js_on_change("active", CustomJS(
        args={
            "source": source,
            "followers": follower_data,
            "content": content_data,
            "bubbles": bubbles,
            "title": "map-title",
        },
        code="""
            const isContent = cb_obj.active === 1;
            source.data = isContent ? content : followers;
            bubbles.glyph.fill_color = isContent ? '#c45a89' : '#7650c8';
            const heading = document.getElementById(title);
            if (heading) heading.textContent = isContent ? 'Content audience' : 'Follower audience';
        """,
    ))
    return column(controls, plot, sizing_mode="stretch_width", spacing=8)


def make_demographics(report):
    audiences = report["audiences"]
    categories = [
        (key, value["label"])
        for key, value in audiences["followers"].items()
        if value.get("items")
    ]
    if not categories:
        raise ValueError("No audience profile categories are available for the demographic chart.")
    category_options = [{"id": key, "label": label} for key, label in categories]
    initial_category = next(
        (item["id"] for item in category_options if item["id"] == "industries"),
        category_options[0]["id"],
    )
    source_data = demographic_payload(audiences["followers"][initial_category]["items"])
    source = ColumnDataSource(source_data)
    plot = style_plot(figure(
        y_range=FactorRange(factors=list(reversed(source_data["display_name"]))),
        height=300,
        x_axis_label="Share of audience (%)",
        tools="pan,wheel_zoom,reset,save",
    ))
    bars = plot.hbar(
        y="display_name", right="value", height=0.68, source=source,
        color=PURPLE, line_color=None,
    )
    plot.yaxis.major_label_text_font_size = "9px"
    plot.add_tools(HoverTool(
        renderers=[bars],
        tooltips=[("Category", "@name"), ("Reported share", "@label")],
    ))
    plot.x_range.start = 0
    plot.x_range.end = max(5, max(source_data["value"], default=0) * 1.2)
    profile = Select(
        title="Audience",
        value="Followers",
        options=["Followers", "Content audience"],
        width=220,
    )
    select = Select(
        title="Breakdown",
        value=next(item["label"] for item in category_options if item["id"] == initial_category),
        options=[item["label"] for item in category_options],
        width=220,
    )
    callback = CustomJS(
        args={
            "source": source,
            "plot": plot,
            "audiences": audiences,
            "categories": category_options,
            "select": select,
            "profile": profile,
            "title": "demographic-title",
            "bar": bars,
        },
        code="""
            const profileKey = profile.value === 'Followers' ? 'followers' : 'content';
            const category = categories.find(item => item.label === select.value);
            const data = category ? audiences[profileKey][category.id] : null;
            if (!data || !data.items || data.items.length === 0) {
              source.data = {name: [], display_name: [], value: [], label: []};
              plot.y_range.factors = [];
              return;
            }
            const items = data.items.slice(0, 10);
            source.data = {
              name: items.map(item => item.name),
              display_name: items.map(item => item.name.length <= 24 ? item.name : item.name.slice(0, 21).trimEnd() + '…'),
              value: items.map(item => item.value),
              label: items.map(item => item.label)
            };
            plot.y_range.factors = source.data.display_name.slice().reverse();
            plot.x_range.end = Math.max(5, ...items.map(item => item.value)) * 1.2;
            bar.glyph.fill_color = profileKey === 'followers' ? '#7650c8' : '#c45a89';
            const heading = document.getElementById(title);
            if (heading) heading.textContent =
              (profileKey === 'followers' ? 'Follower audience' : 'Content audience')
              + ' · ' + select.value;
        """,
    )
    profile.js_on_change("value", callback)
    select.js_on_change("value", callback)
    controls = column(profile, select, sizing_mode="stretch_width", spacing=6)
    return column(controls, plot, sizing_mode="stretch_width", spacing=8)


def demographic_payload(items):
    selected = items[:10]
    return {
        "name": [item["name"] for item in selected],
        "display_name": [
            item["name"] if len(item["name"]) <= 24 else item["name"][:21].rstrip() + "…"
            for item in selected
        ],
        "value": [item["value"] for item in selected],
        "label": [item["label"] for item in selected],
    }


def make_posts(report):
    impressions = sorted(report["top_impressions"], key=lambda item: item["value"], reverse=True)[:8]
    engagements = sorted(report["top_engagement"], key=lambda item: item["value"], reverse=True)[:8]

    def post_payload(posts):
        return {
            "title": [post["title"] for post in posts],
            "display_title": [
                post["title"] if len(post["title"]) <= 27 else post["title"][:24].rstrip() + "…"
                for post in posts
            ],
            "date": [post["date"] for post in posts],
            "value": [post["value"] for post in posts],
            "url": [post["url"] for post in posts],
        }

    impressions_data = post_payload(impressions)
    engagements_data = post_payload(engagements)
    source = ColumnDataSource(impressions_data)
    plot = style_plot(figure(
        y_range=FactorRange(factors=list(reversed(impressions_data["display_title"]))),
        height=360,
        x_axis_label="Impressions",
        tools="pan,wheel_zoom,reset,save",
    ))
    bars = plot.hbar(
        y="display_title", right="value", height=0.62, source=source,
        color=PURPLE, line_color=None,
    )
    plot.yaxis.major_label_text_font_size = "9px"
    plot.add_tools(HoverTool(
        renderers=[bars],
        tooltips=[
            ("Post", "@title"),
            ("Published", "@date"),
            ("Value", "@value{0,0}"),
            ("Action", "Tap a bar to open the post"),
        ],
    ))
    plot.add_tools(TapTool(callback=OpenURL(url="@url"), renderers=[bars]))
    mode = RadioButtonGroup(labels=["Impressions", "Engagements"], active=0, width=220, height=34)
    mode.js_on_change("active", CustomJS(
        args={
            "source": source,
            "impressions": impressions_data,
            "engagements": engagements_data,
            "plot": plot,
            "bar": bars,
            "axis": plot.xaxis[0],
            "title": "posts-chart-title",
            "deck": "posts-chart-deck",
        },
        code="""
            const engagementMode = cb_obj.active === 1;
            const data = engagementMode ? engagements : impressions;
            source.data = data;
            plot.y_range.factors = data.display_title.slice().reverse();
            axis.axis_label = engagementMode ? 'Engagements' : 'Impressions';
            bar.glyph.fill_color = engagementMode ? '#c45a89' : '#7650c8';
            const heading = document.getElementById(title);
            const note = document.getElementById(deck);
            if (heading) heading.textContent = engagementMode
              ? 'Posts that earned the most interactions'
              : 'Posts with the most impressions';
            if (note) note.textContent = 'Hover for details · select a bar to open the LinkedIn post';
        """,
    ))
    return column(mode, plot, sizing_mode="stretch_width", spacing=8)


def build_dashboard(report_path, map_path, output_path):
    report = json.loads(report_path.read_text(encoding="utf-8"))
    geojson = json.loads(map_path.read_text(encoding="utf-8"))
    models = {
        "performance-chart": make_performance(report),
        "followers-chart": make_followers(report),
        "correlation-chart": make_monthly_comparison(report),
        "audience-map": make_map(report, geojson),
        "demographic-chart": make_demographics(report),
        "posts-chart": make_posts(report),
    }
    output = {
        "bokeh_version": __import__("bokeh").__version__,
        "charts": {target: json_item(model) for target, model in models.items()},
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"Built {output_path} with {len(models)} interactive Bokeh charts.")


def main():
    parser = argparse.ArgumentParser(description="Build standalone Bokeh charts for the static report.")
    root = Path(__file__).resolve().parents[1]
    parser.add_argument("--report", type=Path, default=root / "social-media" / "data" / "report.json")
    parser.add_argument("--map", type=Path, default=root / "social-media" / "data" / "world-land.geojson")
    parser.add_argument("--output", type=Path, default=root / "social-media" / "data" / "bokeh-dashboard.json")
    args = parser.parse_args()
    for asset in (args.report, args.map):
        if not asset.is_file():
            parser.error(f"Required input does not exist: {asset}")
    build_dashboard(args.report, args.map, args.output)


if __name__ == "__main__":
    main()
