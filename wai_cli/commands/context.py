"""
Context Command

Output context files for LLM paste with markdown rendering.
"""

import sys
from pathlib import Path


def output_context(path: str = '.', render_markdown: bool = True) -> None:
    """
    Output context for LLM paste with optional markdown rendering.

    Args:
        path: Path to spoke project
        render_markdown: Whether to render markdown (default: True)
    """
    project_path = Path(path).expanduser().resolve()
    wai_dir = project_path / 'WAI-Spoke'

    if not wai_dir.exists():
        print(f"No spoke found at: {project_path}", file=sys.stderr)
        return

    # Check if rich is available for markdown rendering
    can_render = False
    if render_markdown:
        try:
            from rich.console import Console
            from rich.markdown import Markdown
            can_render = True
            console = Console()
        except ImportError:
            can_render = False

    # Output Guide first
    guide_path = wai_dir / 'WAI-Guide.md'
    if guide_path.exists():
        content = guide_path.read_text(encoding='utf-8')
        print("\n" + "=" * 60)
        print("WAI-Guide.md")
        print("=" * 60 + "\n")

        if can_render:
            console.print(Markdown(content))
        else:
            print(content)

        print("\n" + "=" * 60 + "\n")

    # Output State.json
    state_path = wai_dir / 'WAI-State.json'
    if state_path.exists():
        print("\n" + "=" * 60)
        print("WAI-State.json")
        print("=" * 60 + "\n")
        print("```json")
        print(state_path.read_text(encoding='utf-8'))
        print("```")
        print("\n" + "=" * 60 + "\n")

    # Output State.md
    state_md_path = wai_dir / 'WAI-State.md'
    if state_md_path.exists():
        content = state_md_path.read_text(encoding='utf-8')
        print("\n" + "=" * 60)
        print("WAI-State.md")
        print("=" * 60 + "\n")

        if can_render:
            console.print(Markdown(content))
        else:
            print(content)

        print("\n" + "=" * 60 + "\n")

    if not can_render and render_markdown:
        print("\nNote: Install 'rich' package for better markdown rendering:")
        print("  pip install rich\n")


def cmd_context(args):
    """
    Handle context command.

    Args:
        args: Argument namespace with optional 'path' and 'no_render' attributes
    """
    path = getattr(args, 'path', '.')
    render_markdown = not getattr(args, 'no_render', False)
    output_context(path, render_markdown)
