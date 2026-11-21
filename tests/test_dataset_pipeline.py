from __future__ import annotations

from collections import Counter
from pathlib import Path

from src.core.io import (
    load_json,
    load_jsonl,
    validate_case_dict,
)


ROOT = Path(
    __file__
).resolve().parents[1]

TRAIN_PATH = (
    ROOT
    / "data"
    / "train.jsonl"
)

DEV_PATH = (
    ROOT
    / "data"
    / "dev.jsonl"
)

TEST_PATH = (
    ROOT
    / "data"
    / "test.jsonl"
)

MANIFEST_PATH = (
    ROOT
    / "data"
    / "dataset_manifest.json"
)


def load_splits():
    return {
        "train": (
            load_jsonl(
                TRAIN_PATH
            )
        ),
        "dev": (
            load_jsonl(
                DEV_PATH
            )
        ),
        "test": (
            load_jsonl(
                TEST_PATH
            )
        ),
    }


def test_final_dataset_files_exist():
    assert TRAIN_PATH.exists()
    assert DEV_PATH.exists()
    assert TEST_PATH.exists()
    assert MANIFEST_PATH.exists()


def test_manifest_matches_files():
    manifest = load_json(
        MANIFEST_PATH
    )

    splits = load_splits()

    total = sum(
        len(cases)
        for cases
        in splits.values()
    )

    assert (
        total
        == manifest[
            "total_cases"
        ]
    )

    for (
        split_name,
        cases,
    ) in splits.items():
        assert (
            len(cases)
            == manifest[
                "splits"
            ][
                split_name
            ][
                "total"
            ]
        )


def test_dataset_is_balanced():
    splits = load_splits()

    valid_count = 0
    invalid_count = 0

    for cases in (
        splits.values()
    ):
        for case in cases:
            if case[
                "ground_truth"
            ]["valid"]:
                valid_count += 1
            else:
                invalid_count += 1

    assert (
        valid_count
        == invalid_count
    )


def test_error_distribution_is_balanced():
    manifest = load_json(
        MANIFEST_PATH
    )

    expected = (
        manifest[
            "cases_per_error_type"
        ]
    )

    counts = Counter()

    for cases in (
        load_splits().values()
    ):
        for case in cases:
            if not case[
                "ground_truth"
            ]["valid"]:
                counts.update(
                    [
                        case[
                            "ground_truth"
                        ][
                            "errors"
                        ][0][
                            "error_type"
                        ]
                    ]
                )

    assert len(counts) == 7

    for count in (
        counts.values()
    ):
        assert count == expected


def test_repositories_do_not_cross_splits():
    splits = load_splits()

    repositories = {
        split_name: {
            case["metadata"][
                "source_repository"
            ]
            for case in cases
        }
        for (
            split_name,
            cases,
        ) in splits.items()
    }

    assert not (
        repositories[
            "train"
        ]
        & repositories[
            "dev"
        ]
    )

    assert not (
        repositories[
            "train"
        ]
        & repositories[
            "test"
        ]
    )

    assert not (
        repositories[
            "dev"
        ]
        & repositories[
            "test"
        ]
    )


def test_source_schemas_are_not_reused():
    source_schema_ids = []

    for cases in (
        load_splits().values()
    ):
        source_schema_ids.extend(
            case["metadata"][
                "source_schema_id"
            ]
            for case in cases
        )

    assert (
        len(source_schema_ids)
        == len(
            set(
                source_schema_ids
            )
        )
    )


def test_all_cases_match_schema():
    for cases in (
        load_splits().values()
    ):
        for case in cases:
            validate_case_dict(
                case
            )


def test_all_cases_are_from_schemapile():
    for cases in (
        load_splits().values()
    ):
        for case in cases:
            assert (
                case[
                    "metadata"
                ][
                    "source_dataset"
                ]
                == "SchemaPile-Perm"
            )