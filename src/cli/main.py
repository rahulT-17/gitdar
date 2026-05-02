"""
CLI entrypoint.
`gitdar` command is registered here via pyproject.toml [project.scripts].
All command logic lives in cli/commands/*.py — this file only wires them up.
"""
import typer

from cli.commands import init
app = typer.Typer(
    name="gitdar",
    help="Your AI standup teammate. Reads GitHub, writes your standup.",
    add_completion=False,
    no_args_is_help=True,
)

app.command(name="init")(init.run)



if __name__ == "__main__":
    app()
