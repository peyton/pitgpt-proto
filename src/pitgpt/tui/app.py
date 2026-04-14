import asyncio
from pathlib import Path

from textual import on, work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
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
from pitgpt.core.io import load_analysis_protocol, parse_observations_csv
from pitgpt.core.llm import LLMClient
from pitgpt.core.settings import load_settings

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
            placeholder="Is CeraVe or La Roche-Posay better for my dry skin?",
            id="ingest-query",
        )
        yield Label("Optional source text paths (one per line):", classes="field-label")
        yield TextArea(id="ingest-docs")
        yield Label("Model:", classes="field-label")
        yield Select(MODELS, value=MODELS[0][1], id="ingest-model")
        yield Button("Run Ingestion", variant="primary", id="ingest-run")
        yield Label("Result:", classes="field-label")
        yield VerticalScroll(
            Static("Waiting for input...", id="ingest-result", markup=True),
            classes="result-area",
        )


class AnalyzePane(Vertical):
    def compose(self) -> ComposeResult:
        yield Label("Protocol JSON file:", classes="field-label")
        yield Input(placeholder="/path/to/protocol.json", id="analyze-protocol")
        yield Label("Observations CSV file:", classes="field-label")
        yield Input(placeholder="/path/to/observations.csv", id="analyze-observations")
        with Horizontal(classes="bench-row"):
            yield Button("Use Example Files", id="analyze-example")
            yield Button("Run Analysis", variant="primary", id="analyze-run")
        yield Label("Result:", classes="field-label")
        yield VerticalScroll(
            Static("Waiting for input...", id="analyze-result", markup=True),
            classes="result-area",
        )


class BenchmarkPane(Vertical):
    def compose(self) -> ComposeResult:
        yield Label("Model:", classes="field-label")
        yield Select(MODELS, value=MODELS[0][1], id="bench-model")
        with Horizontal(classes="bench-row"):
            with Vertical(classes="bench-field"):
                yield Label("Track:", classes="field-label")
                yield Select(
                    [("All", "all"), ("Ingestion", "ingestion"), ("Analysis", "analysis")],
                    value="all",
                    id="bench-track",
                )
            with Vertical(classes="bench-field"):
                yield Label("Cases (comma-separated, blank=all):", classes="field-label")
                yield Input(placeholder="ING-001,RES-001", id="bench-cases")
        yield Button("Run Benchmark", variant="primary", id="bench-run")
        yield Label("Results:", classes="field-label")
        yield VerticalScroll(
            Static("Waiting for input...", id="bench-result", markup=True),
            classes="result-area",
        )


class PitGPTApp(App):
    TITLE = "PitGPT"
    SUB_TITLE = "Personal Clinical Trial Machine"

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
    .section-header {
        color: $accent;
        text-style: bold;
        margin-top: 1;
    }
    .bench-row {
        height: auto;
    }
    .bench-field {
        width: 1fr;
        padding-right: 1;
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

        settings = load_settings()
        api_key = settings.openrouter_api_key
        if not api_key:
            result_widget.update(
                "[red]OPENROUTER_API_KEY not set. Export it in your shell or mise.toml.[/red]"
            )
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

        client = LLMClient(
            model=str(model),
            api_key=api_key,
            base_url=settings.llm_base_url,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
            timeout_s=settings.llm_timeout_s,
        )
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

        proto_p = Path(proto_path)
        obs_p = Path(obs_path)
        if not proto_p.exists():
            result_widget.update(f"[red]Protocol file not found: {proto_path}[/red]")
            return
        if not obs_p.exists():
            result_widget.update(f"[red]Observations file not found: {obs_path}[/red]")
            return

        try:
            proto_data = load_analysis_protocol(proto_p)
            obs_data = parse_observations_csv(obs_p.read_text())
            r = analyze(proto_data, obs_data)
            result_widget.update(_format_result_card(r))
        except Exception as e:
            result_widget.update(f"[red]Error: {e}[/red]")

    @on(Button.Pressed, "#analyze-example")
    def use_example_analysis_files(self):
        root = Path(__file__).resolve().parents[3]
        self.query_one("#analyze-protocol", Input).value = str(root / "examples" / "protocol.json")
        self.query_one("#analyze-observations", Input).value = str(
            root / "examples" / "observations.csv"
        )

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
            from pitgpt.benchmarks.runner import run_benchmark

            results = asyncio.run(run_benchmark(model, track, case_filter))
            result_widget.update(_format_benchmark(results))
        except Exception as e:
            result_widget.update(f"[red]Error: {e}[/red]")


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

_VERDICT_DISPLAY = {
    "favors_a": "[green]Favors A[/green]",
    "favors_b": "[green]Favors B[/green]",
    "inconclusive": "[yellow]Inconclusive[/yellow]",
    "insufficient_data": "[red]Insufficient Data[/red]",
}

_GRADE_COLORS = {"A": "green", "B": "cyan", "C": "yellow", "D": "red"}
_TIER_COLORS = {"GREEN": "green", "YELLOW": "yellow", "RED": "red"}


def _format_ingestion(r) -> str:
    color = _TIER_COLORS.get(r.safety_tier.value, "white")
    lines = [
        f"[bold]Decision:[/bold]  {r.decision.value}",
        f"[bold]Safety:[/bold]    [{color}]{r.safety_tier.value}[/{color}]",
        f"[bold]Risk:[/bold]      {r.risk_level.value}",
        f"[bold]Evidence:[/bold]  {r.evidence_quality.value} (conflict: {r.evidence_conflict})",
    ]
    if r.risk_rationale:
        lines.append(f"[bold]Why:[/bold]       {r.risk_rationale}")
    if r.clinician_note:
        lines.append(f"[bold]Clinician:[/bold] {r.clinician_note}")
    if r.protocol:
        p = r.protocol
        lines.append("")
        lines.append("[bold underline]Protocol[/bold underline]")
        lines.append(f"  Template:  {p.template}")
        lines.append(f"  Duration:  {p.duration_weeks} weeks, {p.block_length_days}-day blocks")
        lines.append(f"  Cadence:   {p.cadence}")
        lines.append(f"  Washout:   {p.washout}")
        lines.append(f"  Outcome:   {p.primary_outcome_question}")
        if p.screening:
            lines.append(f"  Screening: {p.screening}")
        if p.warnings:
            lines.append(f"  [yellow]Warnings:  {p.warnings}[/yellow]")
        if p.clinician_note:
            lines.append(f"  Clinician: {p.clinician_note}")
        if p.suggested_confounders:
            lines.append(f"  Context:   {', '.join(p.suggested_confounders)}")
    if r.block_reason:
        lines.append(f"\n[red bold]Blocked:[/red bold] {r.block_reason}")
    lines.append(f"\n[italic]{r.user_message}[/italic]")
    return "\n".join(lines)


def _format_result_card(r) -> str:
    color = _GRADE_COLORS.get(r.quality_grade.value, "white")
    verdict_text = _VERDICT_DISPLAY.get(r.verdict, r.verdict)

    lines = [
        "[bold underline]Result Card[/bold underline]",
        "",
        f"  [bold]Grade:[/bold]    [{color}]{r.quality_grade.value}[/{color}]",
        f"  [bold]Verdict:[/bold]  {verdict_text}",
    ]

    if r.mean_a is not None:
        lines.append("")
        lines.append("[bold underline]Statistics[/bold underline]")
        lines.append(
            f"  [bold]Mean A:[/bold]  {r.mean_a:.2f}    [bold]Mean B:[/bold]  {r.mean_b:.2f}"
        )
        lines.append(f"  [bold]Diff:[/bold]    {r.difference:+.2f}")
        lines.append(f"  [bold]95% CI:[/bold] [{r.ci_lower:.2f}, {r.ci_upper:.2f}]")
        if r.cohens_d is not None:
            d_abs = abs(r.cohens_d)
            if d_abs < 0.2:
                d_label = "negligible"
            elif d_abs < 0.5:
                d_label = "small"
            elif d_abs < 0.8:
                d_label = "medium"
            else:
                d_label = "large"
            lines.append(f"  [bold]Cohen's d:[/bold] {r.cohens_d:+.2f} ({d_label})")

    lines.append("")
    lines.append("[bold underline]Data Quality[/bold underline]")
    lines.append(f"  [bold]N:[/bold]         A={r.n_used_a}, B={r.n_used_b}")
    lines.append(f"  [bold]Adherence:[/bold] {r.adherence_rate:.1%}")
    lines.append(f"  [bold]Logged:[/bold]    {r.days_logged_pct:.1%}")
    if r.early_stop:
        lines.append("  [bold]Early Stop:[/bold] [yellow]yes[/yellow]")
    if r.late_backfill_excluded > 0:
        lines.append(f"  [bold]Late Backfills Excluded:[/bold] {r.late_backfill_excluded}")
    if r.planned_days_defaulted:
        lines.append("  [yellow]planned_days missing — defaulted to 42[/yellow]")

    if r.block_breakdown:
        lines.append("")
        lines.append("[bold underline]Block Breakdown[/bold underline]")
        prev_block = -1
        for b in r.block_breakdown:
            if b.block_index != prev_block:
                lines.append(f"  Block {b.block_index}:")
                prev_block = b.block_index
            lines.append(f"    {b.condition}: mean={b.mean:.2f} (n={b.n})")

    if r.sensitivity_excluding_partial is not None:
        s = r.sensitivity_excluding_partial
        lines.append("")
        lines.append("[bold underline]Sensitivity (excluding partial adherence)[/bold underline]")
        if s.difference is not None:
            lines.append(
                f"  [bold]Diff:[/bold]  {s.difference:+.2f}   [bold]CI:[/bold] [{s.ci_lower:.2f}, {s.ci_upper:.2f}]"
            )
            lines.append(f"  [bold]N:[/bold]     A={s.n_used_a}, B={s.n_used_b}")
        else:
            lines.append(f"  Insufficient data (A={s.n_used_a}, B={s.n_used_b})")

    lines.append("")
    lines.append("[bold underline]Summary[/bold underline]")
    lines.append(f"  [italic]{r.summary}[/italic]")

    if r.caveats:
        lines.append("")
        lines.append("[bold underline]Caveats[/bold underline]")
        for caveat in r.caveats.split(". "):
            caveat = caveat.strip().rstrip(".")
            if caveat:
                lines.append(f"  [dim]- {caveat}.[/dim]")

    return "\n".join(lines)


def _format_benchmark(results: dict) -> str:
    model = results.get("model", "?")
    track = results.get("track", "all")
    lines = [
        "[bold underline]Benchmark Results[/bold underline]",
        "",
        f"  [bold]Model:[/bold] {model}",
        f"  [bold]Track:[/bold] {track}",
        "",
    ]

    cases = results.get("cases", [])
    if not cases:
        lines.append("  [dim]No cases matched.[/dim]")
        return "\n".join(lines)

    max_id_len = max(len(c["case_id"]) for c in cases)

    for case in cases:
        score = case.get("score", 0)
        color = "green" if score >= 0.8 else "yellow" if score >= 0.5 else "red"
        case_id = case["case_id"].ljust(max_id_len)
        details = case.get("details", "")
        elapsed = case.get("elapsed_s", 0)
        error = case.get("error")

        if error:
            lines.append(f"  [red]{case_id}  ERROR  {error}[/red]")
        else:
            time_str = f"{elapsed:.2f}s" if elapsed >= 0.01 else "<0.01s"
            lines.append(f"  [{color}]{case_id}  {score:.3f}[/{color}]  {time_str:>7}  {details}")

    s = results.get("summary", {})
    total = s.get("total", 0)
    passed = s.get("pass_count", 0)
    mean = s.get("mean_score", 0)
    mean_color = "green" if mean >= 0.9 else "yellow" if mean >= 0.7 else "red"

    lines.append("")
    lines.append(
        f"  [bold]Score:[/bold] [{mean_color}]{mean:.4f}[/{mean_color}]  ({passed}/{total} passed)"
    )

    return "\n".join(lines)


def main():
    app = PitGPTApp()
    app.run()


if __name__ == "__main__":
    main()
