"""Standalone CLI for clawbot: run worker, init agent root, show config."""

import os
from pathlib import Path

import typer

app = typer.Typer(help="Clawbot — lightweight AI agent worker.")


@app.command()
def run(
    agent_root: str | None = typer.Option(
        None,
        "--agent-root",
        "-r",
        help="Path to agent root directory (else AGENT_ROOT env)",
    ),
    admin_url: str = typer.Option(
        "",
        "--admin-url",
        help="Admin control plane URL (merged into config)",
    ),
    token: str = typer.Option(
        "",
        "--token",
        "-t",
        help="Agent token for admin auth (merged into config)",
    ),
    agent_id: str = typer.Option(
        "",
        "--agent-id",
        help="Agent ID (default: agent root directory name)",
    ),
) -> None:
    """Start the agent worker. Uses AGENT_ROOT or --agent-root."""
    root = agent_root or os.environ.get("AGENT_ROOT")
    if not root and not os.environ.get("AGENT_ID"):
        typer.echo("Error: Set AGENT_ROOT or --agent-root, or AGENT_ID.", err=True)
        raise typer.Exit(1)
    path = Path(root).resolve() if root else None
    if path and not path.is_dir() and path.exists():
        typer.echo(f"Error: Not a directory: {path}", err=True)
        raise typer.Exit(1)

    if path:
        os.environ["AGENT_ROOT"] = str(path)
    if agent_id:
        os.environ["AGENT_ID"] = agent_id

    if admin_url or token or agent_id:
        from clawbot.worker.resolve import resolve_agent_root
        from clawlib.config.loader import deep_merge, load_config, save_config

        try:
            _, config_path, _resolved_id, _ = resolve_agent_root()
            cfg = load_config(config_path)
            overrides: dict = {}
            if admin_url:
                overrides["admin_url"] = admin_url
            if token:
                overrides["agent_token"] = token
            if agent_id:
                overrides["agent_id"] = agent_id
            if overrides:
                merged = deep_merge(
                    cfg.model_dump(),
                    {"control_plane": overrides},
                )
                save_config(merged, config_path)
        except Exception as e:
            typer.echo(f"Warning: Could not merge control plane config: {e}", err=True)

    from clawbot.core.logging import configure_logging
    from clawbot.worker.app import main

    configure_logging("INFO")
    main()


@app.command()
def init(
    agent_root: str = typer.Argument(..., help="Path to create as agent root"),
    agent_id: str = typer.Option(
        "",
        "--agent-id",
        help="Agent ID (default: directory name)",
    ),
    role: str = typer.Option(
        "default",
        "--role",
        "-r",
        help="Template role (default only for now)",
    ),
) -> None:
    """Provision a new agent root with minimal layout."""
    path = Path(agent_root).resolve()
    path.mkdir(parents=True, exist_ok=True)
    aid = agent_id or path.name
    from clawbot.worker.provision import provision_agent_root

    provision_agent_root(path, aid, role=role)
    typer.echo(f"Initialized agent root at {path} (agent_id={aid}, role={role})")


@app.command()
def config(
    agent_root: str | None = typer.Option(
        None,
        "--agent-root",
        "-r",
        help="Path to agent root (else AGENT_ROOT)",
    ),
    show: bool = typer.Option(True, "--show/--no-show", help="Print current config"),
    edit: bool = typer.Option(False, "--edit", "-e", help="Open config in editor"),
) -> None:
    """Show or edit agent config."""
    root = agent_root or os.environ.get("AGENT_ROOT")
    if not root:
        typer.echo("Error: Set AGENT_ROOT or --agent-root.", err=True)
        raise typer.Exit(1)
    path = Path(root).resolve()
    config_file = path / ".config" / "agent.json"
    if not config_file.exists():
        config_file = path / ".config" / "agent.yaml"
    if not config_file.exists():
        typer.echo("Error: No .config/agent.json or agent.yaml found.", err=True)
        raise typer.Exit(1)
    if show:
        typer.echo(config_file.read_text(encoding="utf-8"))
    if edit:
        editor = os.environ.get("EDITOR", "nano")
        os.execvp(editor, [editor, str(config_file)])


@app.command()
def version() -> None:
    """Show version information."""
    from clawbot import __version__

    typer.echo(f"Clawbot v{__version__}")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
