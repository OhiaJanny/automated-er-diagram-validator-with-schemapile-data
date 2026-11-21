from __future__ import annotations

from src.core.io import (
    validate_case_dict,
)
from src.data.import_schemapile import (
    extract_repository,
    normalize_schema_record,
    screen_schema,
)


def make_raw_schema():
    return {
        "INFO": {
            "URL": (
                "https://github.com/"
                "example/project/blob/"
                "abc123/schema.sql"
            ),
            "LICENSE": (
                "MIT"
            ),
            "PERMISSIVE": True,
        },
        "TABLES": {
            "users": {
                "COLUMNS": {
                    "id": {
                        "TYPE": (
                            "Integer"
                        ),
                        "NULLABLE": (
                            False
                        ),
                        "UNIQUE": (
                            True
                        ),
                        "IS_PRIMARY": (
                            True
                        ),
                        "IS_INDEX": (
                            False
                        ),
                    },
                    "status": {
                        "TYPE": (
                            "Integer"
                        ),
                        "NULLABLE": (
                            False
                        ),
                        "UNIQUE": (
                            False
                        ),
                        "IS_PRIMARY": (
                            False
                        ),
                        "IS_INDEX": (
                            False
                        ),
                    },
                },
                "PRIMARY_KEYS": [
                    "id"
                ],
                "FOREIGN_KEYS": [],
                "CHECKS": [],
                "INDEXES": [],
            },
            "orders": {
                "COLUMNS": {
                    "id": {
                        "TYPE": (
                            "Integer"
                        ),
                        "NULLABLE": (
                            False
                        ),
                        "UNIQUE": (
                            True
                        ),
                        "IS_PRIMARY": (
                            True
                        ),
                        "IS_INDEX": (
                            False
                        ),
                    },
                    "user_id": {
                        "TYPE": (
                            "Integer"
                        ),
                        "NULLABLE": (
                            False
                        ),
                        "UNIQUE": (
                            False
                        ),
                        "IS_PRIMARY": (
                            False
                        ),
                        "IS_INDEX": (
                            False
                        ),
                    },
                },
                "PRIMARY_KEYS": [
                    "id"
                ],
                "FOREIGN_KEYS": [
                    {
                        "COLUMNS": [
                            "user_id"
                        ],
                        "FOREIGN_TABLE": (
                            "users"
                        ),
                        "REFERRED_COLUMNS": [
                            "id"
                        ],
                        "ON_DELETE": (
                            "CASCADE"
                        ),
                        "ON_UPDATE": None,
                    }
                ],
                "CHECKS": [],
                "INDEXES": [],
            },
        },
    }


def test_extract_repository():
    url = (
        "https://github.com/"
        "Example/Project/blob/"
        "abc/schema.sql"
    )

    assert (
        extract_repository(
            url
        )
        == "example/project"
    )


def test_schema_passes_screening():
    accepted, reason, metrics = (
        screen_schema(
            "example.sql",
            make_raw_schema(),
        )
    )

    assert accepted is True
    assert reason is None

    assert (
        metrics[
            "table_count"
        ]
        == 2
    )

    assert (
        metrics[
            "foreign_key_count"
        ]
        == 1
    )


def test_normalization_matches_project_schema():
    case = (
        normalize_schema_record(
            "example.sql",
            make_raw_schema(),
        )
    )

    validate_case_dict(case)

    assert (
        case["domain"]
        == "real_world"
    )

    assert (
        case["metadata"][
            "source_dataset"
        ]
        == "SchemaPile-Perm"
    )

    assert (
        case["metadata"][
            "source_repository"
        ]
        == "example/project"
    )

    assert (
        case[
            "ground_truth"
        ]["valid"]
        is True
    )


def test_foreign_key_is_preserved():
    case = (
        normalize_schema_record(
            "example.sql",
            make_raw_schema(),
        )
    )

    orders = next(
        entity
        for entity
        in case["entities"]
        if entity[
            "name"
        ] == "orders"
    )

    user_id = next(
        attribute
        for attribute
        in orders[
            "attributes"
        ]
        if attribute[
            "name"
        ] == "user_id"
    )

    assert (
        user_id[
            "foreign_key"
        ]
        is True
    )

    assert (
        user_id[
            "references"
        ][
            "entity"
        ]
        == "users"
    )

    assert (
        user_id[
            "references"
        ][
            "attribute"
        ]
        == "id"
    )


def test_relationship_cardinality_is_derived():
    case = (
        normalize_schema_record(
            "example.sql",
            make_raw_schema(),
        )
    )

    relationship = (
        case[
            "relationships"
        ][0]
    )

    assert (
        relationship[
            "parent"
        ]
        == "users"
    )

    assert (
        relationship[
            "child"
        ]
        == "orders"
    )

    assert (
        relationship[
            "parent_cardinality"
        ]
        == "1"
    )

    assert (
        relationship[
            "child_cardinality"
        ]
        == "0..*"
    )