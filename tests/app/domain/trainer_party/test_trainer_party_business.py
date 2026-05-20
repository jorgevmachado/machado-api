import pytest
from fastapi import HTTPException

from app.domain.trainer.trainer_party import MAX_PARTY_SIZE, validate_party_selection


def test_validate_party_selection_rejects_more_than_max_size():
    with pytest.raises(HTTPException) as exc_info:
        validate_party_selection(list(range(MAX_PARTY_SIZE + 1)))

    assert exc_info.value.status_code == 400


def test_validate_party_selection_rejects_duplicates():
    with pytest.raises(HTTPException) as exc_info:
        validate_party_selection(["1", "1"])

    assert exc_info.value.status_code == 400
