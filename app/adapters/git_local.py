"""Local Git-like workspace used instead of GitHub/GitLab (deviation D-4).

Layout: <root>/<project_id>/main/** and <root>/<project_id>/branches/<branch>/**
Enforces NFR-6: agents commit only to isolated feature branches; protected branches are refused.
"""
from __future__ import annotations

import difflib
import re
import shutil
from pathlib import Path

PROTECTED_BRANCHES = {"main", "master"}
_BRANCH_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,198}$")


class ProtectedBranchError(Exception):
    """An agent tried to write to a protected branch (forbidden by the SRS design constraints)."""


class GitAdapterError(Exception):
    pass


class LocalGitAdapter:
    def __init__(self, root: Path):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    # -- path helpers (all paths are validated to stay inside the workspace) ---------------------------------
    def _inside(self, path: Path) -> Path:
        resolved = path.resolve()
        if self.root != resolved and self.root not in resolved.parents:
            raise GitAdapterError(f"path escapes the workspace: {path}")
        return resolved

    @staticmethod
    def _check_branch(branch: str) -> str:
        if not _BRANCH_RE.match(branch) or ".." in branch or branch.endswith("/") or "//" in branch:
            raise GitAdapterError(f"invalid branch name: {branch!r}")
        return branch

    def _main_dir(self, project_id: int) -> Path:
        return self._inside(self.root / str(project_id) / "main")

    def _branch_dir(self, project_id: int, branch: str) -> Path:
        return self._inside(self.root / str(project_id) / "branches" / self._check_branch(branch))

    @staticmethod
    def _read_tree(base: Path) -> dict[str, str]:
        if not base.exists():
            return {}
        return {
            p.relative_to(base).as_posix(): p.read_text(encoding="utf-8")
            for p in sorted(base.rglob("*"))
            if p.is_file()
        }

    @staticmethod
    def _check_file_path(rel: str) -> None:
        p = Path(rel)
        if not rel or rel.startswith("/") or p.is_absolute() or ".." in p.parts or "\\" in rel or ":" in rel:
            raise GitAdapterError(f"invalid file path: {rel!r}")

    # -- Git-like operations ----------------------------------------------------------------------------------
    def commit(self, project_id: int, branch: str, files: dict[str, str], message: str) -> None:
        """Write files to a feature branch. Protected branches are refused."""
        if branch in PROTECTED_BRANCHES:
            raise ProtectedBranchError(f"direct commits to protected branch '{branch}' are not allowed")
        target = self._branch_dir(project_id, branch)
        for rel, content in files.items():
            self._check_file_path(rel)
            dest = self._inside(target / rel)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content, encoding="utf-8")

    def read_branch(self, project_id: int, branch: str) -> dict[str, str]:
        return self._read_tree(self._branch_dir(project_id, branch))

    def read_main(self, project_id: int) -> dict[str, str]:
        return self._read_tree(self._main_dir(project_id))

    def diff(self, project_id: int, branch: str) -> list[dict[str, str]]:
        """Unified diff of the feature branch against main (UC-05 step 2)."""
        base, head = self.read_main(project_id), self.read_branch(project_id, branch)
        out = []
        for path in sorted(set(base) | set(head)):
            if base.get(path) == head.get(path):
                continue
            lines = difflib.unified_diff(
                base.get(path, "").splitlines(),
                head.get(path, "").splitlines(),
                fromfile=f"main/{path}",
                tofile=f"{branch}/{path}",
                lineterm="",
            )
            out.append({"path": path, "diff": "\n".join(lines)})
        return out

    def loc(self, project_id: int, branch: str) -> int:
        """Non-blank lines of generated source (test files excluded) - input to the estimation (FR-10)."""
        return sum(
            sum(1 for line in text.splitlines() if line.strip())
            for path, text in self.read_branch(project_id, branch).items()
            if not path.startswith("tests/")
        )

    def merge_to_main(self, project_id: int, branch: str) -> str:
        """Merge the branch into main (Deployment Agent only). Returns a snapshot id for rollback()."""
        files = self.read_branch(project_id, branch)
        main = self._main_dir(project_id)
        snapshot = self._inside(self.root / str(project_id) / ".snapshots" / branch.replace("/", "_"))
        if snapshot.exists():
            shutil.rmtree(snapshot)
        if main.exists():
            shutil.copytree(main, snapshot)
        else:
            snapshot.mkdir(parents=True)
        for rel, content in files.items():
            self._check_file_path(rel)
            dest = self._inside(main / rel)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content, encoding="utf-8")
        return snapshot.name

    def rollback(self, project_id: int, snapshot_id: str) -> None:
        """Restore main from the snapshot taken by merge_to_main()."""
        snapshot = self._inside(self.root / str(project_id) / ".snapshots" / snapshot_id)
        main = self._main_dir(project_id)
        if main.exists():
            shutil.rmtree(main)
        if snapshot.exists():
            shutil.copytree(snapshot, main)
        else:
            main.mkdir(parents=True)
