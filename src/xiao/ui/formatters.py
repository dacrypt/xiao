"""Rich formatters for vacuum data display."""

from __future__ import annotations

from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


def _battery_bar(level: int) -> str:
    filled = int(level / 5)
    empty = 20 - filled
    bar = "█" * filled + "░" * empty
    color = "green" if level > 50 else "yellow" if level > 20 else "red"
    return f"[{color}]{bar}[/{color}] {level}%"


def _format_time(minutes: int | float | None) -> str:
    if minutes is None:
        return "—"
    m = int(minutes)
    if m >= 60:
        return f"{m // 60}h {m % 60}m"
    return f"{m}m"


def _format_area(area: float | None) -> str:
    if area is None:
        return "—"
    return f"{area / 1_000_000:.1f} m²" if area > 10_000 else f"{area:.1f} m²"


def _consumable_bar(remaining_str: str) -> str:
    """Create a colored remaining string."""
    if not remaining_str or not remaining_str.endswith("%"):
        return remaining_str or "—"
    pct = int(remaining_str.rstrip("%"))
    color = "green" if pct > 50 else "yellow" if pct > 20 else "red"
    warn = " ⚠ REPLACE" if pct <= 10 else ""
    return f"[{color}]{remaining_str}{warn}[/{color}]"


def render_status(data: dict[str, Any]) -> None:
    lines = []

    state = data.get("state", "Unknown")
    lines.append(f"  [bold]State:[/bold]    {state}")

    battery = data.get("battery")
    if battery is not None:
        lines.append(f"  [bold]Battery:[/bold]  {_battery_bar(battery)}")

    fan = data.get("fan_speed")
    if fan is not None:
        lines.append(f"  [bold]Fan:[/bold]      {fan}")

    area = data.get("clean_area")
    if area is not None:
        lines.append(f"  [bold]Area:[/bold]     {_format_area(area)}")

    time_ = data.get("clean_time")
    if time_ is not None:
        lines.append(f"  [bold]Time:[/bold]     {_format_time(time_)}")

    error = data.get("error")
    if error and str(error) != "0" and str(error).lower() != "none":
        lines.append(f"  [bold red]Error:[/bold red]    {error}")

    mode = data.get("mode")
    if mode is not None:
        lines.append(f"  [bold]Mode:[/bold]     {mode}")

    charging = data.get("charging")
    if charging is not None:
        lines.append(f"  [bold]Charging:[/bold] {charging}")

    dry_left = data.get("dry_left_time_min")
    if dry_left is not None:
        lines.append(f"  [bold]Dry Left:[/bold] {_format_time(dry_left)}")

    # Show any extra properties not already displayed
    shown = {
        "state",
        "battery",
        "fan_speed",
        "clean_area",
        "clean_time",
        "error",
        "is_on",
        "mode",
        "charging",
        "dry_left_time_min",
        "fan_level_raw",
        "dnd",
        "water",
        "consumables",
        "last_clean",
        "schedules_total",
        "schedules_active",
    }
    for k, v in data.items():
        if k not in shown and v is not None:
            lines.append(f"  [bold]{k}:[/bold]  {v}")

    content = "\n".join(lines)
    console.print(Panel(content, title="Vacuum Status", border_style="cyan"))


def render_full_status(data: dict[str, Any]) -> None:
    """Render comprehensive status with all sections."""
    lines = []

    # Main status
    state = data.get("state", "Unknown")
    lines.append(f"  [bold]State:[/bold]      {state}")

    battery = data.get("battery")
    if battery is not None:
        lines.append(f"  [bold]Battery:[/bold]    {_battery_bar(battery)}")

    fan = data.get("fan_speed")
    if fan is not None:
        lines.append(f"  [bold]Fan:[/bold]        {fan}")

    mode = data.get("mode")
    if mode is not None:
        lines.append(f"  [bold]Mode:[/bold]       {mode}")

    charging = data.get("charging")
    if charging is not None:
        lines.append(f"  [bold]Charging:[/bold]   {charging}")

    dry_left = data.get("dry_left_time_min")
    if dry_left is not None:
        lines.append(f"  [bold]Dry Left:[/bold]   {_format_time(dry_left)}")

    # Water level
    water = data.get("water", {})
    if water:
        wl = water.get("water_level", "Unknown")
        lines.append(f"  [bold]Water:[/bold]      {wl}")

    # DND
    dnd = data.get("dnd", {})
    if dnd:
        dnd_en = "On" if dnd.get("enabled") else "Off"
        dnd_start = dnd.get("start", "")
        dnd_end = dnd.get("end", "")
        if dnd_start and dnd_end:
            lines.append(f"  [bold]DND:[/bold]        {dnd_en} ({dnd_start}–{dnd_end})")
        else:
            lines.append(f"  [bold]DND:[/bold]        {dnd_en}")

    # Schedules
    sched_total = data.get("schedules_total")
    sched_active = data.get("schedules_active")
    if sched_total is not None:
        lines.append(f"  [bold]Schedules:[/bold]  {sched_active}/{sched_total} active")

    # Consumables
    cons = data.get("consumables", {})
    if cons:
        lines.append("")
        lines.append("  [bold underline]Consumables[/bold underline]")
        for label, key in [("Main Brush", "main_brush"), ("Side Brush", "side_brush"), ("Filter", "filter")]:
            rem = cons.get(f"{key}_remaining", "—")
            lines.append(f"    {label}: {_consumable_bar(rem)}")

    # Last clean
    last = data.get("last_clean", {})
    if last:
        lines.append("")
        lines.append("  [bold underline]Last Clean[/bold underline]")
        if last.get("last_clean_date"):
            lines.append(f"    Date:     {last['last_clean_date']}")
        if last.get("last_clean_area") is not None:
            lines.append(f"    Area:     {_format_area(last['last_clean_area'])}")
        if last.get("last_clean_duration") is not None:
            lines.append(f"    Duration: {_format_time(last['last_clean_duration'])}")

    content = "\n".join(lines)
    console.print(Panel(content, title="◈ Full Status — Xiaomi X20+", border_style="cyan"))


def render_report(sections: dict[str, Any]) -> None:
    """Render the all-in-one report."""
    console.print()
    console.print("[bold cyan]═══════════════════════════════════════════════════[/bold cyan]")
    console.print("[bold cyan]  🤖 XIAOMI X20+ — FULL REPORT[/bold cyan]")
    console.print("[bold cyan]═══════════════════════════════════════════════════[/bold cyan]")
    console.print()

    # ── Status ──
    status = sections.get("status", {})
    if "error" not in status:
        lines = []
        state = status.get("state", "Unknown")
        battery = status.get("battery")
        fan = status.get("fan_speed", "—")
        mode = status.get("mode", "—")
        charging = status.get("charging", "")

        lines.append(f"  State:    [bold]{state}[/bold]")
        if battery is not None:
            lines.append(f"  Battery:  {_battery_bar(battery)}")
        lines.append(f"  Mode:     {mode}")
        lines.append(f"  Fan:      {fan}")
        if charging:
            lines.append(f"  Charging: {charging}")

        console.print(Panel("\n".join(lines), title="◈ Status", border_style="cyan"))

    # ── Device Info ──
    device = sections.get("device", {})
    if device and "error" not in device:
        lines = []
        for key in ("model", "firmware", "serial_number", "did", "country"):
            val = device.get(key)
            if val:
                label = key.replace("_", " ").title()
                lines.append(f"  {label}: {val}")
        if lines:
            console.print(Panel("\n".join(lines), title="📡 Device", border_style="blue"))

    # ── Water ──
    water = sections.get("water", {})
    if water:
        wl = water.get("water_level", "Unknown")
        raw = water.get("water_level_raw", "")
        console.print(f"  [bold]💧 Water Level:[/bold] {wl} (raw: {raw})")
        console.print()

    # ── DND ──
    dnd = sections.get("dnd", {})
    if dnd and "error" not in dnd:
        en = "✅ On" if dnd.get("enabled") else "❌ Off"
        start = dnd.get("start", "")
        end = dnd.get("end", "")
        time_range = f" ({start}–{end})" if start and end else ""
        console.print(f"  [bold]🌙 DND:[/bold] {en}{time_range}")
        console.print()

    # ── Consumables ──
    cons = sections.get("consumables", {})
    if cons and "error" not in cons:
        table = Table(title="🔧 Consumables", border_style="cyan")
        table.add_column("Component", style="bold")
        table.add_column("Used", justify="right")
        table.add_column("Lifetime", justify="right")
        table.add_column("Remaining", justify="right")

        for label, key in [("Main Brush", "main_brush"), ("Side Brush", "side_brush"), ("Filter", "filter")]:
            used = cons.get(f"{key}_used")
            life = cons.get(f"{key}_life")
            remaining = cons.get(f"{key}_remaining", "—")
            used_str = f"{used}h" if isinstance(used, (int, float)) else "—"
            life_str = f"{life}h" if isinstance(life, (int, float)) else "—"
            table.add_row(label, used_str, life_str, _consumable_bar(remaining))

        console.print(table)

    # ── History ──
    hist = sections.get("history", {})
    if hist and "error" not in hist:
        lines = []
        if hist.get("total_clean_count") is not None:
            lines.append(f"  Total Cleans:   {hist['total_clean_count']}")
        if hist.get("total_clean_duration") is not None:
            lines.append(f"  Total Time:     {_format_time(hist['total_clean_duration'])}")
        if hist.get("total_clean_area") is not None:
            lines.append(f"  Total Area:     {_format_area(hist['total_clean_area'])}")
        if hist.get("last_clean_date"):
            lines.append(f"  Last Clean:     {hist['last_clean_date']}")
        if hist.get("last_clean_area") is not None:
            lines.append(f"  Last Area:      {_format_area(hist['last_clean_area'])}")
        if hist.get("last_clean_duration") is not None:
            lines.append(f"  Last Duration:  {_format_time(hist['last_clean_duration'])}")

        if lines:
            console.print(Panel("\n".join(lines), title="📊 Cleaning History", border_style="green"))

    # ── Schedules ──
    scheds = sections.get("schedules", [])
    if scheds:
        if isinstance(scheds, list) and scheds and isinstance(scheds[0], dict):
            table = Table(title="📅 Schedules", border_style="yellow")
            table.add_column("#", style="bold", justify="right")
            table.add_column("Status", justify="center")
            table.add_column("Time", style="bold cyan")
            table.add_column("Days")
            table.add_column("Mode")
            table.add_column("Water")
            table.add_column("Rooms")

            for s in scheds:
                if s.get("parse_error"):
                    table.add_row("?", "?", s.get("raw", ""), "", "", "", "")
                    continue

                st = "[green]●[/green]" if s.get("enabled") else "[red]○[/red]"
                rooms_str = ", ".join(s.get("rooms_display", []))

                table.add_row(
                    str(s.get("id", "?")),
                    st,
                    s.get("time", ""),
                    s.get("days_display", ""),
                    s.get("mode", ""),
                    s.get("water", ""),
                    rooms_str,
                )

            console.print(table)
        else:
            console.print(f"  [dim]Schedules (raw): {scheds}[/dim]")

    console.print()
    console.print("[bold cyan]═══════════════════════════════════════════════════[/bold cyan]")


def render_consumables(data: dict[str, Any]) -> None:
    table = Table(title="Consumables", border_style="cyan")
    table.add_column("Component", style="bold")
    table.add_column("Life", justify="right")
    table.add_column("Hours Left", justify="right")
    table.add_column("Status", justify="right")

    # MIoT mapping:
    # siid 9,10 (brushes): piid1=left_time(h), piid2=life_level(%)
    # siid 11 (filter): piid1=life_level(%), piid2=left_time(h)
    # siid 18 (mop): piid1=life_level(%), piid2=left_time(h)
    components = [
        ("Main Brush", "main_brush_life", "main_brush_used"),  # life=%, used=hours_left
        ("Side Brush", "side_brush_life", "side_brush_used"),  # life=%, used=hours_left
        ("Filter", "filter_used", "filter_life"),  # used=life_level%, life=hours_left
        ("Mop Pad", "mop_life_level", "mop_left_time"),  # life_level=%, left_time=hours
    ]

    for label, pct_key, hours_key in components:
        pct = data.get(pct_key)
        hours = data.get(hours_key)
        pct_str = f"{pct}%" if pct is not None else "—"
        hours_str = f"{hours}h" if hours is not None else "—"
        table.add_row(label, _consumable_bar(pct_str), hours_str, "")

    console.print(table)


def render_device_info(data: dict[str, Any]) -> None:
    lines = []
    for key, value in data.items():
        if value is not None:
            label = key.replace("_", " ").title()
            lines.append(f"  [bold]{label}:[/bold]  {value}")

    content = "\n".join(lines) if lines else "  No info available."
    console.print(Panel(content, title="Device Info", border_style="cyan"))


def render_rooms(rooms: list) -> None:
    if not rooms:
        console.print("[yellow]No rooms found.[/yellow]")
        return

    table = Table(title="Rooms", border_style="cyan")
    table.add_column("ID", style="bold")
    table.add_column("Name")

    for room in rooms:
        if isinstance(room, (list, tuple)) and len(room) >= 2:
            table.add_row(str(room[0]), str(room[1]))
        else:
            table.add_row(str(room), "—")

    console.print(table)


def render_history(data: dict[str, Any]) -> None:
    lines = []
    for key, value in data.items():
        label = key.replace("_", " ").title()
        if "area" in key:
            lines.append(f"  [bold]{label}:[/bold]  {_format_area(value)}")
        elif "duration" in key:
            lines.append(f"  [bold]{label}:[/bold]  {_format_time(value)}")
        elif "count" in key or "date" in key:
            lines.append(f"  [bold]{label}:[/bold]  {value}")
        elif "remaining" in key:
            lines.append(f"  [bold]{label}:[/bold]  {_consumable_bar(value)}")
        else:
            lines.append(f"  [bold]{label}:[/bold]  {value}")

    content = "\n".join(lines) if lines else "  No history available."
    console.print(Panel(content, title="Cleaning History", border_style="cyan"))


def render_schedules(timers: list) -> None:
    if not timers:
        console.print("[yellow]No schedules found.[/yellow]")
        return

    table = Table(title="Schedules", border_style="cyan")
    table.add_column("ID", style="bold")
    table.add_column("Schedule")
    table.add_column("Enabled")

    for t in timers:
        tid = str(getattr(t, "id", "—"))
        cron = str(getattr(t, "cron", "—"))
        enabled = "Yes" if getattr(t, "enabled", False) else "No"
        table.add_row(tid, cron, enabled)

    console.print(table)
