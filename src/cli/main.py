"""
CLI entrypoint.
`gitdar` command is registered here via pyproject.toml [project.scripts].
All command logic lives in cli/commands/*.py — this file only wires them up.
"""
import typer
from src.cli.commands import init, standup, prs

app = typer.Typer(
    name="gitdar",
    help="Your AI standup teammate. Reads GitHub, writes your standup.",
    add_completion=False,
    no_args_is_help=True,
)

app.command(name="init")(init.run)
app.command(name="standup")(standup.run)
app.command(name="prs")(prs.run)

if __name__ == "__main__":
    app()