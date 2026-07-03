#!/usr/bin/env python3
"""Package a frontend prototype into source_code.zip and dist.zip."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Iterable


EXCLUDED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".idea",
    ".vscode",
    ".next",
    ".nuxt",
    ".output",
    ".turbo",
    ".vite",
    ".angular",
    ".cache",
    ".parcel-cache",
    ".svelte-kit",
    ".vercel",
    "coverage",
    "dist",
    "build",
    "out",
    "node_modules",
}

BUILD_OUTPUT_CANDIDATES = (
    "dist",
    "build",
    "out",
    ".output/public",
)

EXCLUDED_FILE_NAMES = {
    ".DS_Store",
    "source_code.zip",
    "dist.zip",
    "npm-debug.log",
    "yarn-error.log",
    "pnpm-debug.log",
}

EXCLUDED_SUFFIXES = {
    ".log",
    ".tmp",
    ".zip",
}


class PackageError(RuntimeError):
    """Raised when the prototype cannot be packaged."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a frontend prototype and create source_code.zip plus dist.zip."
    )
    parser.add_argument(
        "project_dir",
        nargs="?",
        default=".",
        help="Prototype project directory containing package.json or index.html. Defaults to cwd.",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory for source_code.zip and dist.zip. Defaults to project_dir.",
    )
    parser.add_argument(
        "--dist-dir",
        default=None,
        help="Build output directory relative to project_dir. Defaults to auto-detect.",
    )
    parser.add_argument(
        "--install",
        choices=("auto", "always", "never"),
        default="auto",
        help="Dependency installation behavior. Defaults to auto.",
    )
    parser.add_argument(
        "--skip-build",
        action="store_true",
        help="Skip the build command and package the existing static output.",
    )
    return parser.parse_args()


def load_package_json(project_dir: Path) -> dict | None:
    package_file = project_dir / "package.json"
    if not package_file.exists():
        return None
    try:
        return json.loads(package_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise PackageError(f"Invalid package.json: {exc}") from exc


def choose_package_manager(project_dir: Path) -> str:
    lockfiles = [
        ("pnpm-lock.yaml", "pnpm"),
        ("yarn.lock", "yarn"),
        ("package-lock.json", "npm"),
        ("bun.lockb", "bun"),
        ("bun.lock", "bun"),
    ]
    for lockfile, manager in lockfiles:
        if (project_dir / lockfile).exists():
            return manager
    return "npm"


def command_for(manager: str, action: str) -> list[str]:
    commands = {
        "npm": {
            "install": ["npm", "install"],
            "build": ["npm", "run", "build"],
        },
        "pnpm": {
            "install": ["pnpm", "install"],
            "build": ["pnpm", "run", "build"],
        },
        "yarn": {
            "install": ["yarn", "install"],
            "build": ["yarn", "run", "build"],
        },
        "bun": {
            "install": ["bun", "install"],
            "build": ["bun", "run", "build"],
        },
    }
    return commands[manager][action]


def ensure_command_available(command: list[str]) -> None:
    executable = command[0]
    if shutil.which(executable) is None:
        raise PackageError(f"Required command not found: {executable}")


def run(command: list[str], cwd: Path) -> None:
    ensure_command_available(command)
    print(f"$ {' '.join(command)}", flush=True)
    completed = subprocess.run(command, cwd=str(cwd))
    if completed.returncode != 0:
        raise PackageError(
            f"Command failed with exit code {completed.returncode}: {' '.join(command)}"
        )


def should_install(project_dir: Path, mode: str) -> bool:
    if mode == "always":
        return True
    if mode == "never":
        return False
    return not (project_dir / "node_modules").exists()


def should_exclude_source(path: Path, relative: Path) -> bool:
    parts = set(relative.parts)
    if parts & EXCLUDED_DIRS:
        return True
    if path.name in EXCLUDED_FILE_NAMES:
        return True
    if path.is_file() and path.suffix in EXCLUDED_SUFFIXES:
        return True
    return False


def iter_files(root: Path) -> Iterable[Path]:
    for current_root, dirnames, filenames in os.walk(root):
        current_path = Path(current_root)
        relative_root = current_path.relative_to(root)
        dirnames[:] = [
            dirname
            for dirname in dirnames
            if not should_exclude_source(current_path / dirname, relative_root / dirname)
        ]
        for filename in filenames:
            path = current_path / filename
            relative = path.relative_to(root)
            if not should_exclude_source(path, relative):
                yield path


def has_root_index(directory: Path) -> bool:
    return (directory / "index.html").is_file()


def find_deploy_dir(project_dir: Path, dist_dir_name: str | None) -> Path | None:
    if dist_dir_name:
        return (project_dir / dist_dir_name).resolve()

    for candidate in BUILD_OUTPUT_CANDIDATES:
        path = project_dir / candidate
        if path.is_dir() and has_root_index(path):
            return path

    for candidate in BUILD_OUTPUT_CANDIDATES:
        path = project_dir / candidate
        if not path.is_dir():
            continue
        matches = sorted(path.rglob("index.html"))
        if len(matches) == 1:
            return matches[0].parent
        browser_matches = [match for match in matches if match.parent.name == "browser"]
        if len(browser_matches) == 1:
            return browser_matches[0].parent

    public_dir = project_dir / "public"
    if public_dir.is_dir() and has_root_index(public_dir):
        return public_dir

    if has_root_index(project_dir):
        return project_dir

    return None


def write_zip(zip_path: Path, files: Iterable[tuple[Path, Path]]) -> int:
    count = 0
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path, archive_name in files:
            archive.write(path, archive_name.as_posix())
            count += 1
    if count == 0:
        raise PackageError(f"No files were added to {zip_path}")
    return count


def package_source(project_dir: Path, output_dir: Path) -> Path:
    zip_path = output_dir / "source_code.zip"
    files = ((path, path.relative_to(project_dir)) for path in iter_files(project_dir))
    count = write_zip(zip_path, files)
    print(f"Created {zip_path} ({count} files)", flush=True)
    return zip_path


def package_dist(project_dir: Path, output_dir: Path, dist_dir_name: str | None) -> Path:
    dist_dir = find_deploy_dir(project_dir, dist_dir_name)
    if not dist_dir or not dist_dir.is_dir():
        raise PackageError(
            "Build output directory not found. Pass --dist-dir if the project uses a custom output path."
        )
    if dist_dir == project_dir:
        files = ((path, path.relative_to(dist_dir)) for path in iter_files(dist_dir))
    else:
        files = (
            (path, path.relative_to(dist_dir))
            for path in dist_dir.rglob("*")
            if path.is_file() and path.name != ".DS_Store"
        )
    zip_path = output_dir / "dist.zip"
    count = write_zip(zip_path, files)
    print(f"Created {zip_path} from {dist_dir} ({count} files)", flush=True)
    return zip_path


def verify_dist_zip(zip_path: Path) -> None:
    with zipfile.ZipFile(zip_path, "r") as archive:
        names = set(archive.namelist())
    if "index.html" not in names:
        raise PackageError(
            f"{zip_path} does not contain index.html at archive root; upload deployment may fail."
        )


def main() -> int:
    args = parse_args()
    project_dir = Path(args.project_dir).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve() if args.output_dir else project_dir

    try:
        package_json = load_package_json(project_dir)
        scripts = (package_json.get("scripts") or {}) if package_json else {}
        has_build_script = "build" in scripts

        if args.skip_build:
            print("Skipping build", flush=True)
            build_command = "skipped"
        elif has_build_script:
            manager = choose_package_manager(project_dir)
            if should_install(project_dir, args.install):
                run(command_for(manager, "install"), project_dir)
            else:
                print("Skipping dependency install", flush=True)
            build_command = " ".join(command_for(manager, "build"))
            run(command_for(manager, "build"), project_dir)
        else:
            if not find_deploy_dir(project_dir, args.dist_dir):
                if package_json is None:
                    raise PackageError(
                        "package.json not found and no deployable index.html was detected."
                    )
                raise PackageError(
                    "package.json does not define scripts.build and no deployable index.html was detected."
                )
            print("No build script found; packaging existing static output", flush=True)
            build_command = "skipped"

        source_zip = package_source(project_dir, output_dir)
        dist_zip = package_dist(project_dir, output_dir, args.dist_dir)
        verify_dist_zip(dist_zip)

        print("", flush=True)
        print("Package complete:", flush=True)
        print(f"  source_code.zip: {source_zip}", flush=True)
        print(f"  dist.zip: {dist_zip}", flush=True)
        print(f"  build command: {build_command}", flush=True)
        return 0
    except PackageError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
