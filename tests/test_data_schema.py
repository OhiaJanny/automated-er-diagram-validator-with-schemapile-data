from __future__ import annotations

import copy
from pathlib import Path

import pytest
from jsonschema import (
    Draft202012Validator,
    ValidationError,
)

from src.core.io import (
    load_json,
)


ROOT = Path(
    __file__
).resolve().parents[1]

SCHEMA_PATH = (
    ROOT
    / "schemas"
    / "er_case.schema.json"
)

VALID_EXAMPLE_PATH = (
    ROOT
    / "data"
    / "toy"
    / "valid_example.json"
)

INVALID_EXAMPLE_PATH = (
    ROOT
    / "data"
    / "toy"
    / "invalid_example.json"
)


@pytest.fixture
def validator():
    schema = load_json(
        SCHEMA_PATH
    )

    return Draft202012Validator(
        schema
    )


def test_schema_itself_is_valid():
    schema = load_json(
        SCHEMA_PATH
    )

    Draft202012Validator.check_schema(
        schema
    )


def test_valid_example_matches_schema(
    validator,
):
    case = load_json(
        VALID_EXAMPLE_PATH
    )

    validator.validate(
        case
    )

    assert (
        case[
            "ground_truth"
        ]["valid"]
        is True
    )


def test_invalid_er_example_still_matches_schema(
    validator,
):
    case = load_json(
        INVALID_EXAMPLE_PATH
    )

    validator.validate(
        case
    )

    assert (
        case[
            "ground_truth"
        ]["valid"]
        is False
    )


def test_missing_required_fields_fails(
    validator,
):
    case = load_json(
        VALID_EXAMPLE_PATH
    )

    case.pop(
        "entities"
    )

    with pytest.raises(
        ValidationError
    ):
        validator.validate(
            case
        )


def test_valid_case_cannot_have_ground_truth_errors(
    validator,
):
    case = load_json(
        VALID_EXAMPLE_PATH
    )

    case[
        "ground_truth"
    ][
        "errors"
    ] = [
        {
            "error_type": (
                "FK_TARGET_NOT_KEY"
            )
        }
    ]

    with pytest.raises(
        ValidationError
    ):
        validator.validate(
            case
        )


def test_invalid_case_requires_ground_truth_error(
    validator,
):
    case = load_json(
        VALID_EXAMPLE_PATH
    )

    case[
        "ground_truth"
    ][
        "valid"
    ] = False

    case[
        "ground_truth"
    ][
        "errors"
    ] = []

    with pytest.raises(
        ValidationError
    ):
        validator.validate(
            case
        )


def test_foreign_key_requires_reference_target(
    validator,
):
    case = load_json(
        VALID_EXAMPLE_PATH
    )

    mutated = copy.deepcopy(
        case
    )

    foreign_key = None

    for entity in mutated[
        "entities"
    ]:
        for attribute in entity[
            "attributes"
        ]:
            if attribute.get(
                "foreign_key",
                False,
            ):
                foreign_key = (
                    attribute
                )
                break

        if (
            foreign_key
            is not None
        ):
            break

    assert (
        foreign_key
        is not None
    )

    foreign_key.pop(
        "references",
        None,
    )

    with pytest.raises(
        ValidationError
    ):
        validator.validate(
            mutated
        )