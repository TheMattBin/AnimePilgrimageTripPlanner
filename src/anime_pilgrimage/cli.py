"""CLI entry point for the Anime Pilgrimage Trip Planner."""

from __future__ import annotations

import argparse
import asyncio
import json
import re
from pathlib import Path

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from anime_pilgrimage.config import configure_logging, get_settings
from anime_pilgrimage.models import GeneratedResponse
from anime_pilgrimage.planner import AnimePilgrimagePlanner

console = Console()


def _sanitize_filename(name: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", name).strip("_")
    return slug[:60] or "pilgrimage_plan"


def _render_response(response: GeneratedResponse) -> None:
    style = {
        "itinerary": "green",
        "clarification": "yellow",
        "error": "red",
    }[response.response_type]

    console.print(
        Panel.fit(
            f"[bold]{response.title}[/bold]\nConfidence: {response.confidence:.2f}",
            border_style=style,
        )
    )
    console.print(Markdown(response.main_content))


def _save_outputs(
    response: GeneratedResponse,
    *,
    json_path: str | None = None,
    markdown_path: str | None = None,
) -> None:
    if json_path:
        target = Path(json_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(response.model_dump(mode="json"), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        console.print(f"[green]Saved JSON response:[/green] {target}")

    if markdown_path:
        target = Path(markdown_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(response.markdown_content or response.main_content, encoding="utf-8")
        console.print(f"[green]Saved Markdown guide:[/green] {target}")


async def _interactive_loop(planner: AnimePilgrimagePlanner) -> None:
    console.print(
        Panel.fit(
            "[bold cyan]Anime Pilgrimage Trip Planner[/bold cyan]\n"
            "Enter a natural language request (type [bold]quit[/bold] to exit).\n"
            "Example: [italic]Plan a 3-day Your Name pilgrimage in Tokyo and Hida Takayama[/italic]",
            border_style="cyan",
        )
    )

    while True:
        try:
            user_input = console.input("\n[bold cyan]Request>[/bold cyan] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\nGoodbye! Safe travels.")
            break

        if user_input.lower() in {"quit", "exit", "q"}:
            console.print("Goodbye! Safe travels.")
            break
        if not user_input:
            continue

        with console.status("Planning your anime pilgrimage..."):
            response = await planner.process_query(user_input)

        _render_response(response)


async def _run_cli(args: argparse.Namespace) -> int:
    settings = get_settings()
    configure_logging(args.log_level or settings.log_level)

    if not settings.has_openrouter_key:
        console.print(
            "[yellow]Notice:[/yellow] OPENROUTER_API_KEY is not set; "
            "running in rule-based/heuristic fallback mode."
        )

    async with AnimePilgrimagePlanner(settings=settings) as planner:
        if args.query:
            with console.status("Planning your anime pilgrimage..."):
                response = await planner.process_query(args.query)

            _render_response(response)

            md_target = args.markdown
            if args.save_md and not md_target and response.travel_plan:
                slug = _sanitize_filename(response.travel_plan.trip_title)
                md_target = f"outputs/{slug}_{response.travel_plan.duration_days}d.md"

            _save_outputs(response, json_path=args.output, markdown_path=md_target)
            return 0 if response.response_type != "error" else 1

        await _interactive_loop(planner)
        return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pilgrimage",
        description="Anime Pilgrimage Trip Planner powered by LangGraph & OpenRouter.",
    )
    parser.add_argument(
        "-q",
        "--query",
        type=str,
        help="Single pilgrimage query to process non-interactively.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        help="Write structured JSON response to this file path.",
    )
    parser.add_argument(
        "-m",
        "--markdown",
        type=str,
        help="Write the generated Markdown travel guide to this file path.",
    )
    parser.add_argument(
        "--save-md",
        action="store_true",
        help="Auto-save the Markdown guide under outputs/ when running with -q.",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Override logging verbosity.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    raise SystemExit(asyncio.run(_run_cli(args)))


if __name__ == "__main__":
    main()
