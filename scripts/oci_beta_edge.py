#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
import stat
import sys
import tempfile
from pathlib import Path


class EdgeConfigError(ValueError):
    """The beta include is missing, ambiguous, or outside its beta vhost."""


def _scope_depths(text: str) -> list[int]:
    depths = [0] * (len(text) + 1)
    depth = 0
    in_comment = False
    quote: str | None = None
    escaped = False
    for index in range(len(text)):
        character = text[index]
        depths[index] = depth
        if in_comment:
            if character == "\n":
                in_comment = False
            continue
        if quote is not None:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == quote:
                quote = None
            continue
        if character == "#":
            in_comment = True
        elif character in "\"'":
            quote = character
        elif character == "{":
            depth += 1
        elif character == "}":
            depth -= 1
    depths[len(text)] = depth
    return depths


def _server_bounds(text: str, hostname: str) -> tuple[int, int, int, list[int]]:
    depths = _scope_depths(text)
    names = list(re.finditer(r"(?m)^[ \t]*server_name[ \t]+([^;]+);", text))
    blocks: list[tuple[int, int, int]] = []
    for match in re.finditer(r"(?m)^[ \t]*server[ \t]*\{", text):
        opening_brace = match.end() - 1
        body_depth = depths[opening_brace] + 1
        closing_brace = next(
            (
                index
                for index in range(opening_brace + 1, len(text))
                if text[index] == "}" and depths[index] == body_depth
            ),
            None,
        )
        if closing_brace is None:
            raise EdgeConfigError("server block end was not found")
        closing_line_start = text.rfind("\n", 0, closing_brace) + 1
        blocks.append((match.start(), closing_line_start, body_depth))

    selected = []
    for start, end, body_depth in blocks:
        direct_names = [
            match
            for match in names
            if start < match.start() < end
            and depths[match.start()] == body_depth
            and hostname in match.group(1).split()
        ]
        if direct_names:
            selected.append((start, end, body_depth))
    if len(selected) != 1:
        raise EdgeConfigError(f"expected exactly one direct server_name for {hostname}")
    start, end, body_depth = selected[0]
    return start, end, body_depth, depths


def render_edge_config(text: str, *, include_path: str, hostname: str) -> str:
    """Validate the beta include and return an idempotent rendered config."""

    server_start, server_end, server_depth, depths = _server_bounds(text, hostname)
    begin = f"# BEGIN hermes-chatgpt-mcp-beta managed include"
    end = f"# END hermes-chatgpt-mcp-beta managed include"
    begin_positions = [match.start() for match in re.finditer(re.escape(begin), text)]
    end_positions = [match.start() for match in re.finditer(re.escape(end), text)]
    if len(begin_positions) != len(end_positions) or len(begin_positions) > 1:
        raise EdgeConfigError("expected at most one complete beta managed include")

    if not begin_positions:
        block = f"\n    {begin}\n    include {include_path};\n    {end}\n"
        return text[:server_end] + block + text[server_end:]

    begin_position = begin_positions[0]
    end_position = end_positions[0]
    if not server_start < begin_position < end_position < server_end:
        raise EdgeConfigError("beta managed include is outside the beta server block")
    if depths[begin_position] != server_depth or depths[end_position] != server_depth:
        raise EdgeConfigError("beta managed include is nested below direct server scope")
    managed_lines = [line.strip() for line in text[begin_position + len(begin) : end_position].splitlines()]
    managed_lines = [line for line in managed_lines if line]
    if managed_lines != [f"include {include_path};"]:
        raise EdgeConfigError("beta managed include does not match the expected include")
    return text


def _atomic_write(path: Path, text: str) -> None:
    original = path.stat()
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary_name, stat.S_IMODE(original.st_mode))
        try:
            os.chown(temporary_name, original.st_uid, original.st_gid)
        except PermissionError:
            pass
        os.replace(temporary_name, path)
        directory_descriptor = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)


def _arguments() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate or atomically update the beta OpenResty include")
    parser.add_argument("operation", choices=("validate", "apply"))
    parser.add_argument("--edge", required=True, type=Path)
    parser.add_argument("--include", required=True)
    parser.add_argument("--hostname", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = _arguments().parse_args(argv)
    text = arguments.edge.read_text(encoding="utf-8")
    rendered = render_edge_config(text, include_path=arguments.include, hostname=arguments.hostname)
    if arguments.operation == "apply" and rendered != text:
        _atomic_write(arguments.edge, rendered)
    return 0


if __name__ == "__main__":  # pragma: no cover
    try:
        raise SystemExit(main())
    except EdgeConfigError as error:
        print(f"beta OpenResty validation failed: {error}", file=sys.stderr)
        raise SystemExit(1) from error
