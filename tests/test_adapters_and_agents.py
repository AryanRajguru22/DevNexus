"""NFR-6 (feature branches only), the Git adapter, the mock LLM/CI adapters and agent safety."""
from __future__ import annotations

import os

import pytest

from app.adapters.cicd import MockCICDAdapter
from app.adapters.git_local import GitAdapterError, LocalGitAdapter, ProtectedBranchError
from app.adapters.llm import CodeRequest, LLMUnavailable, MockLLMProvider, slugify
from app.agents.base import AgentError
from app.agents.codegen import CodeGenerationAgent
from app.agents.deployment import DeploymentAgent
from app.agents.testing import TestingAgent


@pytest.fixture
def git(tmp_path):
    return LocalGitAdapter(tmp_path / "ws")


# -- Git adapter ------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("branch", ["main", "master"])
def test_commit_to_protected_branch_is_refused(git, branch):
    with pytest.raises(ProtectedBranchError):
        git.commit(1, branch, {"a.py": "x = 1"}, "msg")
    assert git.read_main(1) == {}


@pytest.mark.parametrize("branch", ["../escape", "feature/../../x", "/abs", "a//b", "feature/", "bad branch", ""])
def test_invalid_branch_names_are_refused(git, branch):
    with pytest.raises(GitAdapterError):
        git.commit(1, branch, {"a.py": "x = 1"}, "msg")


@pytest.mark.parametrize("path", ["../evil.py", "/etc/passwd", "a/../../b.py", "c:\\x.py", ""])
def test_path_traversal_in_file_names_is_refused(git, tmp_path, path):
    with pytest.raises(GitAdapterError):
        git.commit(1, "feature/x", {path: "boom"}, "msg")
    assert not (tmp_path / "evil.py").exists()


def test_branches_are_isolated_from_main_and_each_other(git):
    git.commit(1, "feature/a", {"generated/a.py": "a = 1\n"}, "m")
    git.commit(1, "feature/b", {"generated/b.py": "b = 2\n"}, "m")
    assert git.read_main(1) == {}
    assert list(git.read_branch(1, "feature/a")) == ["generated/a.py"]
    assert list(git.read_branch(1, "feature/b")) == ["generated/b.py"]
    assert git.read_branch(2, "feature/a") == {}  # other project


def test_diff_merge_and_rollback(git):
    git.commit(1, "feature/a", {"generated/a.py": "a = 1\nb = 2\n"}, "m")
    diff = git.diff(1, "feature/a")
    assert diff[0]["path"] == "generated/a.py" and "+a = 1" in diff[0]["diff"]
    snapshot = git.merge_to_main(1, "feature/a")
    assert git.read_main(1) == {"generated/a.py": "a = 1\nb = 2\n"} and git.diff(1, "feature/a") == []
    git.commit(1, "feature/c", {"generated/c.py": "c = 3\n"}, "m")
    snap2 = git.merge_to_main(1, "feature/c")
    assert set(git.read_main(1)) == {"generated/a.py", "generated/c.py"}
    git.rollback(1, snap2)
    assert set(git.read_main(1)) == {"generated/a.py"}
    git.rollback(1, snapshot)
    assert git.read_main(1) == {}


def test_loc_counts_non_blank_source_lines_and_ignores_tests(git):
    git.commit(1, "feature/a", {"generated/a.py": "a = 1\n\n\nb = 2\n", "tests/test_a.py": "x\ny\nz\n"}, "m")
    assert git.loc(1, "feature/a") == 2


# -- mock adapters ----------------------------------------------------------------------------------------------
def request(**kw) -> CodeRequest:
    base = dict(title="Build login API", description="", requirement="Users log in", feedback=None, attempt=1, max_loc=200)
    return CodeRequest(**(base | kw))


def test_mock_llm_is_deterministic_valid_python_within_limits():
    llm = MockLLMProvider()
    first, second = llm.generate(request()), llm.generate(request())
    assert first == second
    source = next(iter(first.files.values()))
    compile(source, "generated.py", "exec")  # valid Python
    assert sum(1 for line in source.splitlines() if line.strip()) <= 30
    assert "not a real model" in source  # honestly labelled


@pytest.mark.parametrize("title", ['Quote " and \\ backslash', "Line one\nline two", "123 starts with digit", "ünïcode ☃", '"""'])
def test_mock_llm_survives_awkward_titles(title):
    source = next(iter(MockLLMProvider().generate(request(title=title, requirement=title)).files.values()))
    compile(source, "generated.py", "exec")


def test_mock_llm_failure_markers():
    llm = MockLLMProvider()
    with pytest.raises(LLMUnavailable):
        llm.generate(request(title="x [fail-llm]", attempt=1))
    assert llm.generate(request(title="x [fail-llm]", attempt=2))
    with pytest.raises(LLMUnavailable):
        llm.generate(request(description="[FAIL-LLM-ALWAYS]", attempt=5))


def test_slugify_is_a_valid_identifier():
    for text in ("Build login API", "123", "!!!", "ünï", "a" * 100):
        assert slugify(text).isidentifier()


def test_mock_ci_failure_marker_only_on_first_attempt():
    ci = MockCICDAdapter()
    assert not ci.deploy(branch="b", environment="staging", attempt=1, hints="x [fail-deploy]").succeeded
    assert ci.deploy(branch="b", environment="staging", attempt=2, hints="x [fail-deploy]").succeeded


# -- agents -----------------------------------------------------------------------------------------------------
def test_codegen_agent_commits_only_to_a_feature_branch(git):
    agent = CodeGenerationAgent(MockLLMProvider(), git)
    args = dict(project_id=1, title="T task", description="", requirement="r", feedback=None, attempt=1, max_loc=200)
    result = agent.run(branch="feature/t", **args)
    assert result.loc > 0 and git.read_branch(1, "feature/t")
    with pytest.raises(AgentError, match="protected"):
        agent.run(branch="main", **args)
    assert git.read_main(1) == {}


def test_testing_agent_never_executes_generated_code(git, tmp_path):
    marker = tmp_path / "PWNED.txt"
    evil = (
        f'"""evil"""\nopen({str(marker)!r}, "w").write("pwned")\nimport os\nos._exit(1)\n'
        'def f() -> int:\n    """doc"""\n    return 1\n'
    )
    git.commit(1, "feature/evil", {"generated/evil.py": evil}, "m")
    outcome = TestingAgent(git).run(project_id=1, branch="feature/evil", hints="", attempt=1)
    assert not marker.exists()  # the code was only parsed, never run
    assert outcome.failed == 0 and outcome.passed == 2


def test_testing_agent_reports_syntax_errors_and_missing_docs(git):
    git.commit(1, "feature/bad", {"generated/bad.py": "def broken(:\n"}, "m")
    out = TestingAgent(git).run(project_id=1, branch="feature/bad", hints="", attempt=1)
    assert out.failed == 1 and "syntax error" in out.report

    git.commit(1, "feature/nodoc", {"generated/nodoc.py": "def f():\n    return 1\n"}, "m")
    out = TestingAgent(git).run(project_id=1, branch="feature/nodoc", hints="", attempt=1)
    assert out.failed == 2 and out.coverage_pct == 0.0


def test_testing_agent_commits_generated_tests_to_the_branch_only(git):
    git.commit(1, "feature/ok", {"generated/ok.py": 'def f() -> int:\n    """d"""\n    return 1\n'}, "m")
    out = TestingAgent(git).run(project_id=1, branch="feature/ok", hints="", attempt=1)
    assert out.coverage_pct == 100.0
    assert "tests/test_ok.py" in git.read_branch(1, "feature/ok") and git.read_main(1) == {}


def test_testing_agent_with_no_sources_fails(git):
    out = TestingAgent(git).run(project_id=1, branch="feature/empty", hints="", attempt=1)
    assert out.failed == 1 and "no source files" in out.report


def test_deployment_agent_merges_on_success_and_restores_main_on_failure(git):
    git.commit(1, "feature/a", {"generated/a.py": "a = 1\n"}, "m")
    agent = DeploymentAgent(git, MockCICDAdapter())
    failed = agent.deploy(project_id=1, branch="feature/a", environment="staging", hints="[fail-deploy]", attempt=1)
    assert not failed.succeeded and git.read_main(1) == {}
    ok = agent.deploy(project_id=1, branch="feature/a", environment="staging", hints="[fail-deploy]", attempt=2)
    assert ok.succeeded and "generated/a.py" in git.read_main(1)


def test_workspace_stays_inside_data_dir(git):
    git.commit(1, "feature/a", {"generated/a.py": "a = 1\n"}, "m")
    for root, _dirs, files in os.walk(git.root):
        assert str(git.root) in root


def test_diff_lists_only_the_branchs_own_files_not_other_tasks_merged_files(git):
    """Issue #3: files merged to main by other tasks must not show up as deletions in this branch's diff."""
    git.commit(1, "feature/a", {"generated/a.py": "a = 1\n"}, "m")
    git.merge_to_main(1, "feature/a")
    git.commit(1, "feature/b", {"generated/b.py": "b = 2\n"}, "m")
    diff = git.diff(1, "feature/b")
    assert [d["path"] for d in diff] == ["generated/b.py"]
    assert "+b = 2" in diff[0]["diff"] and "-a = 1" not in diff[0]["diff"]
    # a branch file that changes a path already on main is still a real modification
    git.commit(1, "feature/c", {"generated/a.py": "a = 1\na2 = 2\n"}, "m")
    changed = git.diff(1, "feature/c")
    assert [d["path"] for d in changed] == ["generated/a.py"] and "+a2 = 2" in changed[0]["diff"]
