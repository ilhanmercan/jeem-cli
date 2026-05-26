from __future__ import annotations

import asyncio

import click
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.text import Text

from jeem.client import stream_chat
from jeem.models import TextDelta, DataFollowups, Finish, Session
from jeem.session import (
    create_message,
    load,
    save,
    delete,
    list_all,
    new_chat_id,
)

console = Console()


# ── Shared query logic ────────────────────────────────────────

def _run_query(query_text: str, no_stream: bool, session: str | None, as_json: bool) -> None:
    sess = None
    if session:
        sess = load(session)
        if sess is None:
            sess = Session(name=session, chat_id=new_chat_id())

    chat_id = sess.chat_id if sess else new_chat_id()
    user_msg = create_message(query_text)

    body = {
        "id": chat_id,
        "messages": [user_msg.model_dump()],
    }

    if sess and sess.messages:
        history = [m.model_dump() for m in sess.messages]
        history.append(user_msg.model_dump())
        body["messages"] = history

    if as_json:
        asyncio.run(_stream_json(body))
        return

    if no_stream:
        asyncio.run(_stream_buffered(body, sess))
    else:
        asyncio.run(_stream_live(body, sess))


# ── Entry point ───────────────────────────────────────────────

@click.group(invoke_without_command=True)
@click.argument("query", nargs=-1)
@click.option("--no-stream", is_flag=True, help="Buffer response, print once complete.")
@click.option("--session", "-s", default=None, help="Session name for multi-turn chat.")
@click.option("--json", "as_json", is_flag=True, help="Output raw JSON events.")
@click.pass_context
def main(ctx: click.Context, query: tuple[str, ...], no_stream: bool, session: str | None, as_json: bool):
    """jeem — conversational search CLI for jeem.ai"""
    if ctx.invoked_subcommand is None:
        query_text = " ".join(query)
        if not query_text.strip():
            click.echo(ctx.get_help())
            return
        _run_query(query_text, no_stream, session, as_json)


@main.command()
@click.argument("query", nargs=-1)
@click.option("--no-stream", is_flag=True, help="Buffer response, print once complete.")
@click.option("--session", "-s", default=None, help="Session name for multi-turn chat.")
@click.option("--json", "as_json", is_flag=True, help="Output raw JSON events.")
def ask(query: tuple[str, ...], no_stream: bool, session: str | None, as_json: bool):
    """Ask a question (explicit alias for jeem <query>)."""
    _run_query(" ".join(query), no_stream, session, as_json)


# ── Streaming ─────────────────────────────────────────────────

async def _stream_json(body: dict) -> None:
    async for event in stream_chat(body):
        console.print_json(data=event.model_dump())


async def _stream_live(body: dict, sess: Session | None) -> None:
    buffer: list[str] = []
    followups: list[str] = []
    finish_reason: str | None = None
    chat_id: str | None = None

    md = Markdown("", code_theme="github-dark")

    with Live(md, console=console, refresh_per_second=20, vertical_overflow="visible", transient=True) as live:
        async for event in stream_chat(body):
            if isinstance(event, TextDelta):
                buffer.append(event.delta)
                live.update(_render(buffer, followups))

            elif isinstance(event, DataFollowups):
                followups = event.data.suggestions
                live.update(_render(buffer, followups))

            elif isinstance(event, Finish):
                finish_reason = event.finishReason
                chat_id = event.messageMetadata.chatId

    console.print(_render(buffer, followups))
    if finish_reason:
        console.print(Text(f"  ⏎  {finish_reason}", style="dim"))

    if sess:
        assistant_msg = create_message("".join(buffer), role="assistant")
        sess.messages.append(create_message(body["messages"][-1]["parts"][0]["text"]))
        sess.messages.append(assistant_msg)
        if chat_id:
            sess.chat_id = chat_id
        save(sess)


async def _stream_buffered(body: dict, sess: Session | None) -> None:
    buffer: list[str] = []
    followups: list[str] = []
    finish_reason: str | None = None
    chat_id: str | None = None

    async for event in stream_chat(body):
        if isinstance(event, TextDelta):
            buffer.append(event.delta)
        elif isinstance(event, DataFollowups):
            followups = event.data.suggestions
        elif isinstance(event, Finish):
            finish_reason = event.finishReason
            chat_id = event.messageMetadata.chatId

    text = "".join(buffer)
    console.print(_render(buffer, followups))
    if finish_reason:
        console.print(Text(f"  ⏎  {finish_reason}", style="dim"))

    if sess:
        assistant_msg = create_message(text, role="assistant")
        sess.messages.append(create_message(body["messages"][-1]["parts"][0]["text"]))
        sess.messages.append(assistant_msg)
        if chat_id:
            sess.chat_id = chat_id
        save(sess)


def _render(buffer: list[str], followups: list[str]) -> Markdown:
    text = "".join(buffer)
    if followups:
        lines = "\n".join(f"  - {s}" for s in followups)
        text += f"\n\n**Follow-ups:**\n{lines}"
    return Markdown(text, code_theme="github-dark")


# ── Session management ────────────────────────────────────────

@main.group()
def session():
    """Manage conversation sessions."""


@session.command("list")
def session_list():
    """List all saved sessions."""
    sessions = list_all()
    if not sessions:
        console.print(Text("No sessions.", style="dim"))
        return
    for s in sessions:
        msg_count = len(s.messages)
        updated = s.updated_at.strftime("%Y-%m-%d %H:%M")
        console.print(f"  [bold]{s.name}[/]  —  {msg_count} msgs  —  {updated}")


@session.command("show")
@click.argument("name")
def session_show(name: str):
    """Show messages in a session."""
    sess = load(name)
    if sess is None:
        console.print(f"No session named '[bold]{name}[/]'.", style="red")
        return
    for i, msg in enumerate(sess.messages):
        role = msg.role
        color = "cyan" if role == "user" else "green"
        for part in msg.parts:
            console.print(Text(f"\n── {role} ──", style=f"bold {color}"))
            console.print(Markdown(part.text, code_theme="github-dark"))


@session.command("delete")
@click.argument("name", required=False)
@click.option("--all", "delete_all", is_flag=True, help="Delete all sessions.")
@click.confirmation_option(prompt="Delete?")
def session_delete(name: str | None, delete_all: bool):
    """Delete a session, or --all to delete every session."""
    if delete_all:
        sessions = list_all()
        if not sessions:
            console.print(Text("No sessions to delete.", style="dim"))
            return
        for s in sessions:
            delete(s.name)
        console.print(f"Deleted [bold]{len(sessions)}[/] session(s).")
    elif name:
        if delete(name):
            console.print(f"Deleted session '[bold]{name}[/]'.")
        else:
            console.print(f"No session named '[bold]{name}[/]'.", style="red")
    else:
        console.print(Text("Specify a session name or use --all.", style="dim"))
