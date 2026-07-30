import uuid
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api.deps import ensure_branch_access


def context_with(*branch_ids: uuid.UUID):
    return SimpleNamespace(sucursal_ids=frozenset(branch_ids))


def test_empty_assignment_means_all_branches() -> None:
    ensure_branch_access(context_with(), uuid.uuid4())


def test_assigned_branch_is_allowed() -> None:
    branch_id = uuid.uuid4()
    ensure_branch_access(context_with(branch_id), branch_id)


def test_other_branch_is_rejected() -> None:
    with pytest.raises(HTTPException) as error:
        ensure_branch_access(context_with(uuid.uuid4()), uuid.uuid4())
    assert error.value.status_code == 403
