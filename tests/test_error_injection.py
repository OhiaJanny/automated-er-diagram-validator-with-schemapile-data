from __future__ import annotations

import copy

from src.core.io import (
    validate_case_dict,
)
from src.data.inject_errors import (
    ERROR_ORDER,
    eligible_error_types,
    inject_error,
)


def build_universal_test_case():
    return {
        "case_id": (
            "TEST_REFERENCE_001"
        ),
        "domain": (
            "real_world"
        ),
        "description": (
            "Compact structural fixture "
            "used only for mutation "
            "unit testing."
        ),
        "entities": [
            {
                "name": "PARENT",
                "attributes": [
                    {
                        "name": "id",
                        "type": "INTEGER",
                        "primary_key": True,
                        "foreign_key": False,
                        "nullable": False,
                        "unique": True,
                    },
                    {
                        "name": "alt_code",
                        "type": "INTEGER",
                        "primary_key": False,
                        "foreign_key": False,
                        "nullable": False,
                        "unique": False,
                    },
                ],
            },
            {
                "name": "ALTERNATIVE",
                "attributes": [
                    {
                        "name": "alt_id",
                        "type": "INTEGER",
                        "primary_key": True,
                        "foreign_key": False,
                        "nullable": False,
                        "unique": True,
                    }
                ],
            },
            {
                "name": "CHILD",
                "attributes": [
                    {
                        "name": "child_id",
                        "type": "INTEGER",
                        "primary_key": True,
                        "foreign_key": False,
                        "nullable": False,
                        "unique": True,
                    },
                    {
                        "name": "parent_id",
                        "type": "INTEGER",
                        "primary_key": False,
                        "foreign_key": True,
                        "nullable": False,
                        "unique": True,
                        "references": {
                            "entity": (
                                "PARENT"
                            ),
                            "attribute": (
                                "id"
                            ),
                        },
                    },
                ],
            },
            {
                "name": (
                    "COMP_PARENT"
                ),
                "attributes": [
                    {
                        "name": "part_a",
                        "type": "INTEGER",
                        "primary_key": True,
                        "foreign_key": False,
                        "nullable": False,
                        "unique": False,
                    },
                    {
                        "name": "part_b",
                        "type": "INTEGER",
                        "primary_key": True,
                        "foreign_key": False,
                        "nullable": False,
                        "unique": False,
                    },
                ],
            },
            {
                "name": (
                    "COMP_CHILD"
                ),
                "attributes": [
                    {
                        "name": (
                            "part_a"
                        ),
                        "type": (
                            "INTEGER"
                        ),
                        "primary_key": (
                            True
                        ),
                        "foreign_key": (
                            True
                        ),
                        "nullable": (
                            False
                        ),
                        "unique": (
                            False
                        ),
                        "references": {
                            "entity": (
                                "COMP_PARENT"
                            ),
                            "attribute": (
                                "part_a"
                            ),
                        },
                    },
                    {
                        "name": (
                            "part_b"
                        ),
                        "type": (
                            "INTEGER"
                        ),
                        "primary_key": (
                            True
                        ),
                        "foreign_key": (
                            True
                        ),
                        "nullable": (
                            False
                        ),
                        "unique": (
                            False
                        ),
                        "references": {
                            "entity": (
                                "COMP_PARENT"
                            ),
                            "attribute": (
                                "part_b"
                            ),
                        },
                    },
                    {
                        "name": (
                            "local_number"
                        ),
                        "type": (
                            "INTEGER"
                        ),
                        "primary_key": (
                            True
                        ),
                        "foreign_key": (
                            False
                        ),
                        "nullable": (
                            False
                        ),
                        "unique": (
                            False
                        ),
                    },
                ],
            },
        ],
        "relationships": [
            {
                "name": (
                    "parent_child"
                ),
                "parent": (
                    "PARENT"
                ),
                "child": (
                    "CHILD"
                ),
                "parent_cardinality": (
                    "1"
                ),
                "child_cardinality": (
                    "0..1"
                ),
                "identifying": False,
            },
            {
                "name": (
                    "composite_parent_child"
                ),
                "parent": (
                    "COMP_PARENT"
                ),
                "child": (
                    "COMP_CHILD"
                ),
                "parent_cardinality": (
                    "1"
                ),
                "child_cardinality": (
                    "0..*"
                ),
                "identifying": True,
            },
        ],
        "requirements": [
            {
                "requirement_id": (
                    "R1"
                ),
                "text": (
                    "Each CHILD row "
                    "must reference "
                    "exactly one PARENT."
                ),
            },
            {
                "requirement_id": (
                    "R2"
                ),
                "text": (
                    "Each COMP_CHILD "
                    "must reference "
                    "exactly one "
                    "COMP_PARENT."
                ),
            },
        ],
        "metadata": {
            "source": (
                "real_world"
            ),
            "difficulty": (
                "hard"
            ),
            "version": 1,
            "source_dataset": (
                "SchemaPile-Perm"
            ),
            "source_schema_id": (
                "unit_test"
            ),
            "source_repository": (
                "example/project"
            ),
            "error_count": 0,
        },
        "ground_truth": {
            "valid": True,
            "errors": [],
        },
    }


def test_fixture_is_schema_valid():
    case = (
        build_universal_test_case()
    )

    validate_case_dict(case)


def test_fixture_supports_all_errors():
    case = (
        build_universal_test_case()
    )

    eligible = set(
        eligible_error_types(
            case
        )
    )

    assert eligible == set(
        ERROR_ORDER
    )


def test_all_mutations_are_schema_valid():
    for index, error_type in enumerate(
        ERROR_ORDER,
        start=1,
    ):
        case = (
            build_universal_test_case()
        )

        invalid = inject_error(
            case,
            error_type,
            case_id=(
                f"TEST_INVALID_"
                f"{index:02d}"
            ),
            seed=(
                811000 + index
            ),
        )

        validate_case_dict(
            invalid
        )

        assert (
            invalid[
                "ground_truth"
            ]["valid"]
            is False
        )

        assert (
            invalid[
                "ground_truth"
            ][
                "errors"
            ][0][
                "error_type"
            ]
            == error_type
        )


def test_mutation_does_not_change_source():
    case = (
        build_universal_test_case()
    )

    original = copy.deepcopy(
        case
    )

    inject_error(
        case,
        ERROR_ORDER[0],
        case_id=(
            "TEST_INVALID_COPY"
        ),
        seed=811999,
    )

    assert case == original