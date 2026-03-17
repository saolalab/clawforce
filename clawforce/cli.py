"""CLI for clawforce."""

import asyncio
import getpass
import os
import secrets as _secrets
import sys
from pathlib import Path

import typer
from rich.console import Console

from clawforce.auth import hash_password
from clawforce.core.database import get_database
from clawforce.core.storage import get_storage_backend
from clawforce.core.store.agent_variables import AgentVariablesStore, default_git_variables
from clawforce.core.store.agents import AgentStore
from clawforce.core.store.users import UserStore
from clawforce.deps import get_fernet

app = typer.Typer(name="clawforce", help="Multi-agent team admin", no_args_is_help=True)
console = Console()

agent_app = typer.Typer(help="Agent lifecycle")
app.add_typer(agent_app, name="agent")

user_app = typer.Typer(help="User management")
app.add_typer(user_app, name="user")


POOL_MODES = ["process", "docker"]

DEFAULT_DATA_DIR = str(Path.home() / ".clawforce-data")


@agent_app.command("create")
def agent_create(
    name: str = typer.Option(..., "--name", "-n", help="Agent display name"),
    template: str | None = typer.Option(
        None, "--template", "-t", help="Role template (e.g. sre, ceo, finance-controller)"
    ),
    mode: str | None = typer.Option(
        None,
        "--mode",
        "-m",
        help="Execution mode: process (subprocess) or docker (container). Default: use app runtime.",
    ),
    description: str = typer.Option("", "--description", "-d", help="Agent description"),
    show_token: bool = typer.Option(True, "--show-token/--no-token", help="Show connection info"),
):
    """Create a new agent. Use --template to provision from a role (e.g. sre, ceo)."""
    if mode is not None and mode.lower() not in POOL_MODES:
        console.print(f"[red]Invalid --mode. Choose from: {', '.join(POOL_MODES)}[/red]")
        raise typer.Exit(1)
    store = AgentStore(get_database(), get_storage_backend())
    agent = store.create_agent(
        name=name,
        owner_user_id="",
        description=description,
        provision=True,
        template=template,
        mode=(mode.lower() if mode else None),
    )
    AgentVariablesStore(get_database(), fernet=get_fernet()).upsert_variables(
        agent.id, default_git_variables(agent.name), secret_keys=frozenset()
    )
    console.print(f"[green]Agent created: {agent.name}[/green] (id={agent.id})")
    if template:
        console.print(f"[dim]Template: {template}[/dim]")
    if agent.mode:
        console.print(f"[dim]Mode: {agent.mode}[/dim]")
    if show_token:
        console.print("")
        console.print("[cyan]To connect a remote clawbot:[/cyan]")
        console.print(
            f"  clawbot run --admin-url <ADMIN_URL> --agent-id {agent.id} --token {agent.agent_token}"
        )


@agent_app.command("list")
def agent_list():
    """List all agents."""
    store = AgentStore(get_database(), get_storage_backend())
    agents = store.list_agents()
    if not agents:
        console.print("[dim]No agents found.[/dim]")
        return
    for agent in agents:
        status_color = "green" if agent.status == "running" else "dim"
        console.print(
            f"[{status_color}]{agent.status:8}[/{status_color}] "
            f"[bold]{agent.name}[/bold] (id={agent.id})"
        )
        if agent.description:
            console.print(f"         {agent.description}")


@agent_app.command("token")
def agent_token(
    agent_id: str = typer.Argument(..., help="Agent ID"),
    regenerate: bool = typer.Option(False, "--regenerate", "-r", help="Generate a new token"),
    admin_url: str = typer.Option(
        "", "--admin-url", "-u", help="Admin URL (for connection string)"
    ),
):
    """Show or regenerate an agent's connection token."""
    store = AgentStore(get_database(), get_storage_backend())
    agent = store.get_agent(agent_id)
    if not agent:
        console.print(f"[red]Agent not found: {agent_id}[/red]")
        raise typer.Exit(1)

    if regenerate:
        new_token = _secrets.token_urlsafe(32)
        store.update_agent(agent_id, agent_token=new_token)
        agent.agent_token = new_token
        console.print(f"[green]Token regenerated for {agent.name}[/green]")
    else:
        console.print(f"[bold]{agent.name}[/bold] (id={agent.id})")

    console.print("")
    console.print(f"[cyan]Agent ID:[/cyan]    {agent.id}")
    console.print(f"[cyan]Agent Token:[/cyan] {agent.agent_token}")

    url = admin_url or os.environ.get("ADMIN_PUBLIC_URL", "http://localhost:8080")
    console.print("")
    console.print("[cyan]To connect a remote clawbot:[/cyan]")
    console.print(
        f"  clawbot run --admin-url {url} --agent-id {agent.id} --token {agent.agent_token}"
    )
    console.print("")
    console.print("[dim]Or set environment variables:[/dim]")
    console.print(f"  export CLAWBOT_CONTROL_PLANE__ADMIN_URL={url}")
    console.print(f"  export CLAWBOT_CONTROL_PLANE__AGENT_ID={agent.id}")
    console.print(f"  export CLAWBOT_CONTROL_PLANE__AGENT_TOKEN={agent.agent_token}")


@agent_app.command("start")
def agent_start(
    agent_id: str = typer.Argument(..., help="Agent ID to start"),
):
    """Start an agent (managed by the runtime)."""
    from clawforce.core.runtimes.factory import get_runtime_backend

    runtime = get_runtime_backend()
    store = AgentStore(get_database(), get_storage_backend())
    agent = store.get_agent(agent_id)
    if not agent:
        console.print(f"[red]Agent not found: {agent_id}[/red]")
        raise typer.Exit(1)
    asyncio.run(runtime.start_agent(agent_id))
    console.print(f"[green]Agent started: {agent.name}[/green]")


@agent_app.command("stop")
def agent_stop(
    agent_id: str = typer.Argument(..., help="Agent ID to stop"),
):
    """Stop a running agent."""
    from clawforce.core.runtimes.factory import get_runtime_backend

    runtime = get_runtime_backend()
    store = AgentStore(get_database(), get_storage_backend())
    agent = store.get_agent(agent_id)
    if not agent:
        console.print(f"[red]Agent not found: {agent_id}[/red]")
        raise typer.Exit(1)
    asyncio.run(runtime.stop_agent(agent_id))
    console.print(f"[yellow]Agent stopped: {agent.name}[/yellow]")


@app.command()
def setup(
    data_dir: str = typer.Option(
        DEFAULT_DATA_DIR, "--data-dir", "-d", help="Data directory for storage"
    ),
):
    """Initialize Clawforce and create the first admin user.

    Set ADMIN_SETUP_USERNAME and ADMIN_SETUP_PASSWORD for non-interactive setup.
    When both env vars are set, ensures that user exists with that password
    (creates or updates), so login works after container restart.
    """
    data_path = Path(data_dir).resolve()
    data_path.mkdir(parents=True, exist_ok=True)
    os.environ["ADMIN_STORAGE_ROOT"] = str(data_path)

    store = UserStore(get_database())
    username = os.environ.get("ADMIN_SETUP_USERNAME")
    password = os.environ.get("ADMIN_SETUP_PASSWORD")
    env_mode = bool(username and password)

    if env_mode:
        console.print("[cyan]Ensuring admin user from environment[/cyan]")
        existing = store.get_user_by_username(username)
        if existing:
            store.update_user(existing.id, password_hash=hash_password(password))
            console.print("[green]Admin user password updated.[/green]")
        else:
            store.create_user(
                username=username, password_hash=hash_password(password), role="admin"
            )
            console.print("[green]Admin user created.[/green]")
    else:
        users = store.list_users()
        if users:
            console.print("[yellow]Users already exist. Use the web login.[/yellow]")
            return
        console.print("[cyan]Create first admin user[/cyan]")
        username = typer.prompt("Username")
        password = getpass.getpass("Password: ")
        if not username or not password:
            console.print("[red]Username and password required.[/red]")
            raise typer.Exit(1)
        store.create_user(username=username, password_hash=hash_password(password), role="admin")
        console.print("[green]Admin user created.[/green]")

    console.print(f"[dim]Data directory: {data_path}[/dim]")
    console.print("")
    console.print("Start the server with:")
    console.print(f"  [cyan]clawforce serve --data-dir {data_dir}[/cyan]")


def _user_store(data_dir: str) -> UserStore:
    """Resolve data dir and return UserStore."""
    data_path = Path(data_dir).resolve()
    data_path.mkdir(parents=True, exist_ok=True)
    os.environ["ADMIN_STORAGE_ROOT"] = str(data_path)
    return UserStore(get_database())


@user_app.command("create")
def user_create(
    username: str = typer.Argument(..., help="Username to create"),
    password: str = typer.Option(None, "--password", "-p", help="Password (prompt if not set)"),
    role: str = typer.Option("admin", "--role", "-r", help="User role (admin)"),
    data_dir: str = typer.Option(
        DEFAULT_DATA_DIR, "--data-dir", "-d", help="Data directory (same as serve)"
    ),
):
    """Create a new admin user."""
    store = _user_store(data_dir)
    if store.get_user_by_username(username):
        console.print(f"[red]User already exists: {username}[/red]")
        raise typer.Exit(1)
    pwd = password or getpass.getpass("Password: ")
    if not pwd:
        console.print("[red]Password cannot be empty.[/red]")
        raise typer.Exit(1)
    store.create_user(username=username, password_hash=hash_password(pwd), role=role)
    console.print(f"[green]User created: {username}[/green] (role={role})")


@user_app.command("update")
def user_update(
    username: str = typer.Argument(..., help="Username to update"),
    password: str = typer.Option(None, "--password", "-p", help="New password"),
    role: str | None = typer.Option(None, "--role", "-r", help="New role"),
    data_dir: str = typer.Option(
        DEFAULT_DATA_DIR, "--data-dir", "-d", help="Data directory (same as serve)"
    ),
):
    """Update an existing user (role and/or password)."""
    store = _user_store(data_dir)
    user = store.get_user_by_username(username)
    if not user:
        console.print(f"[red]User not found: {username}[/red]")
        raise typer.Exit(1)
    pwd_hash = hash_password(password) if password else None
    if pwd_hash is None and role is None:
        pwd = getpass.getpass("New password (leave empty to keep current): ")
        pwd_hash = hash_password(pwd) if pwd else None
    changes = []
    if pwd_hash:
        changes.append("password")
    if role is not None:
        changes.append(f"role={role}")
    if not changes:
        console.print("[yellow]No changes specified.[/yellow]")
        return
    store.update_user(user.id, password_hash=pwd_hash, role=role)
    console.print(f"[green]User updated: {username}[/green] ({', '.join(changes)})")


@user_app.command("list")
def user_list(
    data_dir: str = typer.Option(
        DEFAULT_DATA_DIR, "--data-dir", "-d", help="Data directory (same as serve)"
    ),
):
    """List existing usernames. Use when you forget which account to log in with."""
    store = _user_store(data_dir)
    users = store.list_users()
    if not users:
        console.print("[dim]No users found. Run 'clawforce setup' first.[/dim]")
        return
    for u in users:
        console.print(f"  [bold]{u.username}[/bold] (role={u.role})")


def _user_reset_impl(username: str, data_dir: str) -> None:
    """Reset password for an existing user."""
    store = _user_store(data_dir)
    user = store.get_user_by_username(username)
    if not user:
        console.print(f"[red]User not found: {username}[/red]")
        console.print("Use 'clawforce user list' to see existing usernames.")
        raise typer.Exit(1)
    password = getpass.getpass("New password: ")
    if not password:
        console.print("[red]Password cannot be empty.[/red]")
        raise typer.Exit(1)
    store.update_user(user.id, password_hash=hash_password(password))
    console.print(f"[green]Password updated for {username}[/green]")


@user_app.command("set-password")
def user_set_password(
    username: str = typer.Argument(..., help="Username to reset password for"),
    data_dir: str = typer.Option(
        DEFAULT_DATA_DIR, "--data-dir", "-d", help="Data directory (same as serve)"
    ),
):
    """Reset password for an existing user. Use when login fails with correct username."""
    _user_reset_impl(username, data_dir)


@user_app.command("reset")
def user_reset(
    username: str = typer.Argument(..., help="Username to reset password for"),
    data_dir: str = typer.Option(
        DEFAULT_DATA_DIR, "--data-dir", "-d", help="Data directory (same as serve)"
    ),
):
    """Reset password for an existing user (alias for set-password)."""
    _user_reset_impl(username, data_dir)


@app.command()
def serve(
    port: int = typer.Option(8080, "--port", "-p", help="Port to listen on"),
    host: str = typer.Option("0.0.0.0", "--host", help="Host to bind to"),
    data_dir: str = typer.Option(
        DEFAULT_DATA_DIR, "--data-dir", "-d", help="Data directory for storage"
    ),
    workers: int = typer.Option(1, "--workers", "-w", help="Number of worker processes"),
    reload: bool = typer.Option(False, "--reload", help="Enable auto-reload (dev mode)"),
    log_level: str = typer.Option("info", "--log-level", help="Log level"),
):
    """Start the Clawforce server (API + dashboard).

    This is the main command for running Clawforce in production.
    The server includes both the REST API and the admin dashboard.

    Examples:
        clawforce serve                          # Start on port 8080
        clawforce serve --port 3000              # Custom port
        clawforce serve --data-dir /var/clawforce  # Custom data directory
        clawforce serve --workers 4              # Multi-process (production)
    """
    import uvicorn

    data_path = Path(data_dir).resolve()
    data_path.mkdir(parents=True, exist_ok=True)
    os.environ["ADMIN_STORAGE_ROOT"] = str(data_path)

    console.print("[cyan]Starting Clawforce server[/cyan]")
    console.print(
        f"  [dim]Dashboard:[/dim] http://{host if host != '0.0.0.0' else 'localhost'}:{port}"
    )
    console.print(
        f"  [dim]API:[/dim]       http://{host if host != '0.0.0.0' else 'localhost'}:{port}/api"
    )
    console.print(f"  [dim]Data:[/dim]      {data_path}")
    console.print("")

    if workers > 1 or reload:
        uvicorn.run(
            "clawforce.app:app",
            host=host,
            port=port,
            workers=workers if workers > 1 else 1,
            reload=reload,
            log_level=log_level,
        )
    else:
        from clawforce.app import app as fastapi_app

        uvicorn.run(
            fastapi_app,
            host=host,
            port=port,
            log_level=log_level,
        )


@app.command()
def web(
    port: int = typer.Option(8080, "--port", "-p"),
    host: str = typer.Option("0.0.0.0", "--host"),
    daemon: bool = typer.Option(False, "--daemon"),
):
    """Start the admin web server (alias for 'serve')."""
    data_dir = os.environ.get("ADMIN_STORAGE_ROOT", DEFAULT_DATA_DIR)

    if daemon:
        import subprocess

        cmd = [sys.executable, "-m", "clawforce.cli", "serve", "--port", str(port), "--host", host]
        subprocess.Popen(
            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True
        )
        console.print(f"[green]Server started in background on http://{host}:{port}[/green]")
        return

    serve(port=port, host=host, data_dir=data_dir, workers=1, reload=False, log_level="info")


@app.command()
def version():
    """Show version information."""
    from clawforce import __version__

    console.print(f"Clawforce v{__version__}")


if __name__ == "__main__":
    app()
