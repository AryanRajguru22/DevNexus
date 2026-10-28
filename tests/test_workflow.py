"""Workflow rules (Phase 3 Fig 3.7): every valid transition, every invalid (state, event) pair, actor and guard checks."""
from __future__ import annotations

import pytest
from sqlalchemy import select

from app import workflow
from app.enums import TaskStatus
from app.errors import ApiError
from app.models import Agent, AgentRun, AuditLog, Project, Requirement, Task, User
from app.validation import default_pipeline

ALL_STATES = [s.value for s in TaskStatus]

# (event, source state, destination state, actor key used to fire it)
VALID = [
    ("assign", "Created", "Assigned", "developer"),
    ("agent_start", "Assigned", "Generating", "agent:code_generation"),
    ("code_ready", "Generating", "In Review", "agent:code_generation"),
    ("agent_error", "Generating", "Failed", "agent:code_generation"),
    ("approve", "In Review", "Testing", "developer"),
    ("reject", "In Review", "Generating", "developer"),
    ("tests_passed", "Testing", "Ready for Deployment", "agent:testing"),
    ("tests_failed", "Testing", "Generating", "agent:testing"),
    ("authorise_deployment", "Ready for Deployment", "Deployed", "developer"),
    ("authorise_deployment", "Ready for Deployment", "Deployed", "project_manager"),
    ("retry", "Failed", "Assigned", "developer"),
]


@pytest.fixture
def db(app):
    with app.state.runtime.session_factory() as session:
        yield session


@pytest.fixture
def make_task(db):
    pm = db.get(User, 1)
    project = Project(name="P", manager_id=pm.user_id, pipeline_config=default_pipeline())
    db.add(project)
    db.flush()
    req = Requirement(project_id=project.project_id, description="req text", type="functional", priority="High")
    db.add(req)
    db.flush()

    def _make(status: str) -> Task:
        task = Task(project_id=project.project_id, req_id=req.req_id, developer_id=2, title="T1", status=status)
        db.add(task)
        db.flush()
        return task

    return _make


def actor_for(db, key: str) -> workflow.Actor:
    if key.startswith("agent:"):
        return workflow.Actor(agent=db.scalars(select(Agent).where(Agent.type == key.split(":")[1])).one())
    return workflow.Actor(user=db.get(User, {"developer": 2, "project_manager": 1}[key]))


def add_run(db, task) -> None:
    agent = db.scalars(select(Agent).where(Agent.type == "code_generation")).one()
    db.add(AgentRun(task_id=task.task_id, agent_id=agent.agent_id, branch_name="feature/x"))
    db.flush()


def test_exactly_the_eight_documented_states():
    assert ALL_STATES == [
        "Created", "Assigned", "Generating", "In Review", "Testing", "Ready for Deployment", "Deployed", "Failed",
    ]
    in_table = {t.src.value for t in workflow.TRANSITIONS.values()} | {t.dst.value for t in workflow.TRANSITIONS.values()}
    assert in_table == set(ALL_STATES)


def test_transition_table_matches_state_chart():
    assert len(workflow.TRANSITIONS) == 10
    assert {(t.event, t.src.value, t.dst.value) for t in workflow.TRANSITIONS.values()} == {
        (e, s, d) for e, s, d, _ in VALID
    }


@pytest.mark.parametrize("event,src,dst,actor_key", VALID)
def test_valid_transition_changes_state_and_writes_audit(db, make_task, event, src, dst, actor_key):
    task = make_task(src)
    workflow.apply_event(db, task, event, actor_for(db, actor_key), detail="why")
    assert task.status == dst
    row = db.scalars(select(AuditLog).order_by(AuditLog.log_id.desc())).first()
    assert row.target_ref == f"task:{task.task_id}"
    assert (row.user_id is None) != (row.agent_id is None)  # exactly one actor
    assert row.detail == "why"


@pytest.mark.parametrize(
    "event,state", [(e, s) for e in workflow.TRANSITIONS for s in ALL_STATES if s != workflow.TRANSITIONS[e].src.value]
)
def test_every_other_state_event_pair_is_rejected(db, make_task, event, state):
    task = make_task(state)
    actor_key = sorted(workflow.TRANSITIONS[event].actors)[0]
    with pytest.raises(ApiError) as exc:
        workflow.apply_event(db, task, event, actor_for(db, actor_key))
    assert exc.value.code == "invalid_transition" and exc.value.status_code == 409
    assert task.status == state  # unchanged


@pytest.mark.parametrize(
    "event,wrong_actor",
    [
        ("assign", "project_manager"),
        ("approve", "project_manager"),
        ("reject", "project_manager"),
        ("retry", "project_manager"),
        ("agent_start", "developer"),
        ("code_ready", "developer"),
        ("tests_passed", "developer"),
        ("tests_failed", "agent:code_generation"),
        ("authorise_deployment", "agent:deployment"),
    ],
)
def test_wrong_actor_is_forbidden(db, make_task, event, wrong_actor):
    src = workflow.TRANSITIONS[event].src.value
    task = make_task(src)
    with pytest.raises(ApiError) as exc:
        workflow.apply_event(db, task, event, actor_for(db, wrong_actor))
    assert exc.value.code == "forbidden"
    assert task.status == src


@pytest.mark.parametrize(
    "event,src,agent",
    [
        ("assign", "Created", "code_generation"),
        ("approve", "In Review", "testing"),
        ("reject", "In Review", "code_generation"),
        ("tests_failed", "Testing", "code_generation"),  # rework re-enters Generating, so generation must be active
        ("authorise_deployment", "Ready for Deployment", "deployment"),
        ("retry", "Failed", "code_generation"),
    ],
)
def test_inactive_agent_blocks_the_transition(db, make_task, event, src, agent):
    task = make_task(src)
    pipeline = default_pipeline()
    pipeline["active_agents"] = [a for a in pipeline["active_agents"] if a != agent]
    task.project.pipeline_config = pipeline
    actor = actor_for(db, sorted(workflow.TRANSITIONS[event].actors)[0])
    with pytest.raises(ApiError) as exc:
        workflow.apply_event(db, task, event, actor)
    assert exc.value.code == "agent_inactive"


@pytest.mark.parametrize("event,src", [("reject", "In Review"), ("retry", "Failed"), ("tests_failed", "Testing")])
def test_rework_is_bounded_by_the_retry_limit(db, make_task, event, src):
    task = make_task(src)
    task.project.pipeline_config = default_pipeline() | {"retry_limit": 1}
    add_run(db, task)
    assert workflow.rework_allowed(db, task, workflow.load_pipeline(task.project.pipeline_config))  # 1 run <= limit 1
    add_run(db, task)
    actor = actor_for(db, sorted(workflow.TRANSITIONS[event].actors)[0])
    with pytest.raises(ApiError) as exc:
        workflow.apply_event(db, task, event, actor)
    assert exc.value.code == "retry_limit_exceeded"
    assert task.status == src  # no extra state is invented: the task stays where it was


def test_zero_retry_limit_forbids_any_rework(db, make_task):
    task = make_task("In Review")
    task.project.pipeline_config = default_pipeline() | {"retry_limit": 0}
    add_run(db, task)
    with pytest.raises(ApiError) as exc:
        workflow.apply_event(db, task, "reject", actor_for(db, "developer"))
    assert exc.value.code == "retry_limit_exceeded"


def test_available_actions_follow_state_and_role(db, make_task):
    dev, pm = db.get(User, 2), db.get(User, 1)
    assert workflow.available_actions(db, make_task("Created"), dev) == ["assign"]
    assert workflow.available_actions(db, make_task("Created"), pm) == []
    assert workflow.available_actions(db, make_task("In Review"), dev) == ["approve", "reject"]
    assert workflow.available_actions(db, make_task("Testing"), dev) == ["tests"]
    assert workflow.available_actions(db, make_task("Ready for Deployment"), dev) == ["deploy"]
    assert workflow.available_actions(db, make_task("Ready for Deployment"), pm) == ["deploy"]
    assert workflow.available_actions(db, make_task("Failed"), dev) == ["retry"]
    assert workflow.available_actions(db, make_task("Deployed"), dev) == []
    assert workflow.available_actions(db, make_task("Generating"), dev) == []
