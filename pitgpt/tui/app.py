import asyncio
import json
import os
from pathlib import Path

from textual import on, work
from textual.app import App, ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    Label,
    Select,
    Static,
    TabbedContent,
    TabPane,
    TextArea,
)

from pitgpt.core.analysis import analyze
from pitgpt.core.ingestion import ingest
from pitgpt.core.llm import LLMClient
from pitgpt.core.models import Observation

MODELS = [
    ("Claude Sonnet 4", "anthropic/claude-sonnet-4"),
    ("GPT-4o", "openai/gpt-4o"),
    ("Gemini 2.5 Pro", "google/gemini-2.5-pro-preview-03-25"),
    ("Llama 4 Maverick", "meta-llama/llama-4-maverick"),
    ("DeepSeek V3", "deepseek/deepseek-chat-v3-0324"),
]


class IngestPane(Vertical):
    def compose(self) -> ComposeResult:
        yield Label("Query:", classes="field-label")
        yield Input(
            placeholder="Is CeraVe or La Roche-Posay better for my dry skin?", id="ingest-query"
        )
        yield Label("Document paths (one per line):", classes="field-label")
        yield TextArea(id="ingest-docs")
        yield Label("Model:", classes="field-label")
        yield Select(MODELS, value=MODELS[0][1], id="ingest-model")
        yield Button("Run Ingestion", variant="primary", id="ingest-run")
        yield Label("Result:", classes="field-label")
        yield VerticalScroll(Static("", id="ingest-result", markup=True), classes="result-area")


class AnalyzePane(Vertical):
    def compose(self) -> ComposeResult:
        yield Label("Protocol JSON file:", classes="field-label")
        yield Input(placeholder="/path/to/protocol.json", id="analyze-protocol")
        yield Label("Observations CSV file:", classes="field-label")
        yield Input(placeholder="/path/to/observations.csv", id="analyze-observations")
        yield Button("Run Analysis", variant="primary", id="analyze-run")
        yield Label("Result:", classes="field-label")
        yield VerticalScroll(Static("", id="analyze-result", markup=True), classes="result-area")


class BenchmarkPane(Vertical):
    def compose(self) -> ComposeResult:
        yield Label("Model:", classes="field-label")
        yield Select(MODELS, value=MODELS[0][1], id="bench-model")
        yield Label("Track:", classes="field-label")
        yield Select(
            [("All", "all"), ("Ingestion", "ingestion"), ("Analysis", "analysis")],
            value="all",
            id="bench-track",
        )
        yield Label("Cases (comma-separated, blank=all):", classes="field-label")
        yield Input(placeholder="ING-001,RES-001", id="bench-cases")
        yield Button("Run Benchmark", variant="primary", id="bench-run")
        yield Label("Results:", classes="field-label")
        yield VerticalScroll(Static("", id="bench-result", markup=True), classes="result-area")


class PitGPTApp(App):
    CSS = """
    .field-label {
        margin-top: 1;
        color: $text-muted;
    }
    .result-area {
        height: 1fr;
        border: solid $primary;
        margin-top: 1;
        padding: 1;
    }
    #ingest-docs {
        height: 4;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("1", "tab_ingest", "Ingest"),
        ("2", "tab_analyze", "Analyze"),
        ("3", "tab_bench", "Benchmark"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with TabbedContent():
            with TabPane("Ingest", id="tab-ingest"):
                yield IngestPane()
            with TabPane("Analyze", id="tab-analyze"):
                yield AnalyzePane()
            with TabPane("Benchmark", id="tab-bench"):
                yield BenchmarkPane()
        yield Footer()

    def action_tab_ingest(self):
        self.query_one(TabbedContent).active = "tab-ingest"

    def action_tab_analyze(self):
        self.query_one(TabbedContent).active = "tab-analyze"

    def action_tab_bench(self):
        self.query_one(TabbedContent).active = "tab-bench"

    @on(Button.Pressed, "#ingest-run")
    @work(exclusive=True, thread=True)
    def run_ingestion(self):
        result_widget = self.query_one("#ingest-result", Static)
        result_widget.update("[bold]Running...[/bold]")

        query = self.query_one("#ingest-query", Input).value
        docs_text = self.query_one("#ingest-docs", TextArea).text
        model = self.query_one("#ingest-model", Select).value

        if not query.strip():
            result_widget.update("[red]Please enter a query[/red]")
            return

        api_key = os.environ.get("OPENROUTER_API_KEY", "")
        if not api_key:
            result_widget.update("[red]OPENROUTER_API_KEY not set[/red]")
            return

        documents = []
        for line in docs_text.strip().split("\n"):
            line = line.strip()
            if line:
                p = Path(line)
                if p.exists():
                    documents.append(p.read_text())
                else:
                    result_widget.update(f"[red]File not found: {line}[/red]")
                    return

        client = LLMClient(model=model, api_key=api_key)
        try:
            r = asyncio.run(ingest(query, documents, client))
            result_widget.update(_format_ingestion(r))
        except Exception as e:
            result_widget.update(f"[red]Error: {e}[/red]")

    @on(Button.Pressed, "#analyze-run")
    @work(exclusive=True, thread=True)
    def run_analysis(self):
        result_widget = self.query_one("#analyze-result", Static)
        result_widget.update("[bold]Running...[/bold]")

        proto_path = self.query_one("#analyze-protocol", Input).value
        obs_path = self.query_one("#analyze-observations", Input).value

        if not proto_path or not obs_path:
            result_widget.update("[red]Please provide both file paths[/red]")
            return

        try:
            proto_data = json.loads(Path(proto_path).read_text())
            obs_data = _parse_csv(Path(obs_path).read_text())
            r = analyze(proto_data, obs_data)
            result_widget.update(_format_result_card(r))
        except Exception as e:
            result_widget.update(f"[red]Error: {e}[/red]")

    @on(Button.Pressed, "#bench-run")
    @work(exclusive=True, thread=True)
    def run_benchmark(self):
        result_widget = self.query_one("#bench-result", Static)
        result_widget.update("[bold]Running benchmark...[/bold]")

        model = self.query_one("#bench-model", Select).value
        track = self.query_one("#bench-track", Select).value
        cases_text = self.query_one("#bench-cases", Input).value

        case_filter = [c.strip() for c in cases_text.split(",") if c.strip()] or None

        try:
            from benchmarks.runner import run_benchmark

            results = asyncio.run(run_benchmark(model, track, case_filter))
            result_widget.update(_format_benchmark(results))
        except Exception as e:
            result_widget.update(f"[red]Error: {e}[/red]")


def _format_ingestion(r) -> str:
    tier_colors = {"GREEN": "green", "YELLOW": "yellow", "RED": "red"}
    color = tier_colors.get(r.safety_tier.value, "white")
    lines = [
        f"[bold]Decision:[/bold] {r.decision.value}",
        f"[bold]Safety Tier:[/bold] [{color}]{r.safety_tier.value}[/{color}]",
        f"[bold]Evidence:[/bold] {r.evidence_quality.value} (conflict: {r.evidence_conflict})",
    ]
    if r.protocol:
        p = r.protocol
        lines.extend(
            [
                "",
                f"[bold]Template:[/bold] {p.template}",
                f"[bold]Duration:[/bold] {p.duration_weeks}wk / {p.block_length_days}d blocks",
                f"[bold]Cadence:[/bold] {p.cadence} | Washout: {p.washout}",
                f"[bold]Outcome:[/bold] {p.primary_outcome_question}",
            ]
        )
        if p.screening:
            lines.append(f"[bold]Screening:[/bold] {p.screening}")
        if p.warnings:
            lines.append(f"[bold]Warnings:[/bold] {p.warnings}")
    if r.block_reason:
        lines.append(f"\n[red]{r.block_reason}[/red]")
    lines.append(f"\n[italic]{r.user_message}[/italic]")
    return "\n".join(lines)


def _format_result_card(r) -> str:
    grade_colors = {"A": "green", "B": "cyan", "C": "yellow", "D": "red"}
    color = grade_colors.get(r.quality_grade.value, "white")
    lines = [f"[bold]Grade:[/bold] [{color}]{r.quality_grade.value}[/{color}]"]
    if r.mean_a is not None:
        lines.extend(
            [
                f"[bold]Mean A:[/bold] {r.mean_a:.2f}  [bold]Mean B:[/bold] {r.mean_b:.2f}",
                f"[bold]Diff:[/bold] {r.difference:+.2f}  [bold]CI:[/bold] [{r.ci_lower:.2f}, {r.ci_upper:.2f}]",
            ]
        )
    lines.extend(
        [
            f"[bold]N:[/bold] A={r.n_used_a}, B={r.n_used_b}",
            f"[bold]Adherence:[/bold] {r.adherence_rate:.1%} | [bold]Logged:[/bold] {r.days_logged_pct:.1%}",
            f"[bold]Early Stop:[/bold] {r.early_stop}",
            "",
            f"[italic]{r.summary}[/italic]",
            f"[dim]{r.caveats}[/dim]",
        ]
    )
    return "\n".join(lines)


def _format_benchmark(results: dict) -> str:
    lines = [f"[bold]Model:[/bold] {results.get('model', '?')}"]
    for case in results.get("cases", []):
        score = case.get("score", 0)
        color = "green" if score >= 0.8 else "yellow" if score >= 0.5 else "red"
        lines.append(
            f"  [{color}]{case['case_id']:10} {score:.2f}[/{color}]  {case.get('details', '')}"
        )
    s = results.get("summary", {})
    lines.append(
        f"\n[bold]Overall: {s.get('mean_score', 0):.2f} ({s.get('pass_count', 0)}/{s.get('total', 0)})[/bold]"
    )
    return "\n".join(lines)


def _parse_csv(content: str) -> list[Observation]:
    lines = content.strip().split("\n")
    if not lines:
        return []
    header = [h.strip() for h in lines[0].split(",")]
    observations = []
    for line in lines[1:]:
        if not line.strip():
            continue
        values = [v.strip() for v in line.split(",")]
        row = dict(zip(header, values, strict=False))
        observations.append(
            Observation(
                day_index=int(row.get("day_index", 0)),
                date=row.get("date", ""),
                condition=row.get("condition", ""),
                primary_score=float(row["primary_score"]) if row.get("primary_score") else None,
                irritation=row.get("irritation", "no"),
                adherence=row.get("adherence", "yes"),
                note=row.get("note", ""),
                is_backfill=row.get("is_backfill", "no"),
                backfill_days=float(row["backfill_days"]) if row.get("backfill_days") else None,
            )
        )
    return observations


def main():
    app = PitGPTApp()
    app.run()


if __name__ == "__main__":
    main()
