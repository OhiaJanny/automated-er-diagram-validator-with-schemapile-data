from __future__ import annotations

import argparse
import copy
import hashlib
from collections import Counter
from pathlib import Path
from typing import Any

from src.core.io import (
    get_er_case_validator,
    load_jsonl,
    save_json,
    save_jsonl,
)
from src.data.inject_errors import (
    ERROR_ORDER,
    ERROR_SELECTION_ORDER,
    eligible_error_types,
    inject_error,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = (
    PROJECT_ROOT
    / "data"
)

REFERENCE_CASES_PATH = (
    DATA_DIR
    / "processed"
    / "reference_cases.jsonl"
)

TRAIN_PATH = (
    DATA_DIR
    / "train.jsonl"
)

DEV_PATH = (
    DATA_DIR
    / "dev.jsonl"
)

TEST_PATH = (
    DATA_DIR
    / "test.jsonl"
)

MANIFEST_PATH = (
    DATA_DIR
    / "dataset_manifest.json"
)

TOY_DIR = (
    DATA_DIR
    / "toy"
)

TOY_VALID_PATH = (
    TOY_DIR
    / "valid_example.json"
)

TOY_INVALID_PATH = (
    TOY_DIR
    / "invalid_example.json"
)


BENCHMARK_VERSION = "2.0"
RANDOM_SEED = 811

AUTO_MAX_PER_ERROR = 100
AUTO_MIN_PER_ERROR = 20


ERROR_CODES = {
    ERROR_ORDER[0]: "E01",
    ERROR_ORDER[1]: "E02",
    ERROR_ORDER[2]: "E03",
    ERROR_ORDER[3]: "E04",
    ERROR_ORDER[4]: "E05",
    ERROR_ORDER[5]: "E06",
    ERROR_ORDER[6]: "E07",
}


def repository_split(
    repository: str,
    seed: int = RANDOM_SEED,
) -> str:
    digest = hashlib.sha256(
        (
            f"{seed}:"
            f"{repository}"
        ).encode(
            "utf-8"
        )
    ).hexdigest()

    bucket = (
        int(
            digest[:8],
            16,
        )
        / 0xFFFFFFFF
    )

    if bucket < 0.70:
        return "train"

    if bucket < 0.85:
        return "dev"

    return "test"


def stable_rank(
    value: str,
    *,
    salt: str,
) -> str:
    return hashlib.sha256(
        (
            f"{RANDOM_SEED}:"
            f"{salt}:"
            f"{value}"
        ).encode(
            "utf-8"
        )
    ).hexdigest()


def allocate_error_quota(
    total_per_error: int,
) -> dict[str, int]:
    train = int(
        total_per_error
        * 0.70
    )

    dev = int(
        total_per_error
        * 0.15
    )

    test = (
        total_per_error
        - train
        - dev
    )

    return {
        "train": train,
        "dev": dev,
        "test": test,
    }


def load_reference_cases() -> list[
    dict[str, Any]
]:
    if not (
        REFERENCE_CASES_PATH.exists()
    ):
        raise FileNotFoundError(
            "Reference cases are missing. "
            "Run:\n"
            "python -m "
            "src.data.import_schemapile"
        )

    cases = load_jsonl(
        REFERENCE_CASES_PATH
    )

    if not cases:
        raise ValueError(
            "Reference case file "
            "is empty."
        )

    for case in cases:
        if not case[
            "ground_truth"
        ]["valid"]:
            raise ValueError(
                "Reference pool contains "
                "an invalid case."
            )

    return cases


def split_reference_cases(
    cases: list[dict[str, Any]],
) -> dict[
    str,
    list[dict[str, Any]],
]:
    result = {
        "train": [],
        "dev": [],
        "test": [],
    }

    for case in cases:
        repository = (
            case["metadata"][
                "source_repository"
            ]
        )

        split_name = (
            repository_split(
                repository
            )
        )

        result[
            split_name
        ].append(
            case
        )

    return result


def build_eligibility_cache(
    cases: list[dict[str, Any]],
) -> dict[
    str,
    set[str],
]:
    return {
        case["case_id"]: set(
            eligible_error_types(
                case
            )
        )
        for case in cases
    }


def try_selection_plan(
    split_cases: dict[
        str,
        list[dict[str, Any]],
    ],
    eligibility: dict[
        str,
        set[str],
    ],
    total_per_error: int,
) -> dict[
    str,
    dict[
        str,
        list[dict[str, Any]],
    ],
] | None:
    quotas = (
        allocate_error_quota(
            total_per_error
        )
    )

    used = {
        "train": set(),
        "dev": set(),
        "test": set(),
    }

    plan = {
        "train": {},
        "dev": {},
        "test": {},
    }

    for error_type in (
        ERROR_SELECTION_ORDER
    ):

        for split_name in (
            "train",
            "dev",
            "test",
        ):
            required = quotas[
                split_name
            ]

            candidates = [
                case
                for case
                in split_cases[
                    split_name
                ]
                if (
                    case["case_id"]
                    not in used[
                        split_name
                    ]
                    and error_type
                    in eligibility[
                        case[
                            "case_id"
                        ]
                    ]
                )
            ]

            candidates.sort(
                key=lambda case: (
                    stable_rank(
                        case[
                            "case_id"
                        ],
                        salt=(
                            f"{split_name}:"
                            f"{error_type}"
                        ),
                    )
                )
            )

            if (
                len(candidates)
                < required
            ):
                return None

            selected = (
                candidates[
                    :required
                ]
            )

            plan[
                split_name
            ][
                error_type
            ] = selected

            used[
                split_name
            ].update(
                case[
                    "case_id"
                ]
                for case
                in selected
            )

    for split_name in (
        "train",
        "dev",
        "test",
    ):
        invalid_count = sum(
            len(
                plan[
                    split_name
                ][
                    error_type
                ]
            )
            for error_type
            in ERROR_ORDER
        )

        remaining_count = (
            len(
                split_cases[
                    split_name
                ]
            )
            - len(
                used[
                    split_name
                ]
            )
        )

        if (
            remaining_count
            < invalid_count
        ):
            return None

    return plan


def choose_total_per_error(
    split_cases: dict[
        str,
        list[dict[str, Any]],
    ],
    eligibility: dict[
        str,
        set[str],
    ],
    requested: int | None,
) -> tuple[
    int,
    dict[
        str,
        dict[
            str,
            list[dict[str, Any]],
        ],
    ],
]:
    if requested is not None:

        if (
            requested
            < AUTO_MIN_PER_ERROR
        ):
            raise ValueError(
                f"--per-error must be "
                f"at least "
                f"{AUTO_MIN_PER_ERROR}."
            )

        plan = try_selection_plan(
            split_cases,
            eligibility,
            requested,
        )

        if plan is None:
            raise ValueError(
                f"A balanced benchmark "
                f"with {requested} cases "
                "per error type is not "
                "feasible with the "
                "current filtered pool. "
                "Use --per-error auto "
                "or a smaller number."
            )

        return requested, plan

    for total_per_error in range(
        AUTO_MAX_PER_ERROR,
        AUTO_MIN_PER_ERROR - 1,
        -1,
    ):
        plan = try_selection_plan(
            split_cases,
            eligibility,
            total_per_error,
        )

        if plan is not None:
            return (
                total_per_error,
                plan,
            )

    raise ValueError(
        "Could not construct a "
        "balanced benchmark with "
        f"at least "
        f"{AUTO_MIN_PER_ERROR} "
        "examples per error type."
    )


def mutation_seed(
    case_id: str,
    error_type: str,
) -> int:
    digest = hashlib.sha256(
        (
            f"{RANDOM_SEED}:"
            f"{case_id}:"
            f"{error_type}"
        ).encode(
            "utf-8"
        )
    ).hexdigest()

    return int(
        digest[:8],
        16,
    )


def create_invalid_cases(
    plan: dict[
        str,
        dict[
            str,
            list[dict[str, Any]],
        ],
    ],
) -> dict[
    str,
    list[dict[str, Any]],
]:
    result = {
        "train": [],
        "dev": [],
        "test": [],
    }

    for split_name in (
        "train",
        "dev",
        "test",
    ):

        counters = Counter()

        for error_type in (
            ERROR_ORDER
        ):
            selected = (
                plan[
                    split_name
                ][
                    error_type
                ]
            )

            error_code = (
                ERROR_CODES[
                    error_type
                ]
            )

            for base_case in (
                selected
            ):
                counters[
                    error_type
                ] += 1

                item_number = (
                    counters[
                        error_type
                    ]
                )

                case_id = (
                    f"INVALID_"
                    f"{error_code}_"
                    f"{split_name.upper()}_"
                    f"{item_number:04d}"
                )

                invalid_case = (
                    inject_error(
                        base_case,
                        error_type,
                        case_id=(
                            case_id
                        ),
                        seed=(
                            mutation_seed(
                                base_case[
                                    "case_id"
                                ],
                                error_type,
                            )
                        ),
                    )
                )

                invalid_case[
                    "metadata"
                ][
                    "split"
                ] = split_name

                invalid_case[
                    "metadata"
                ][
                    "benchmark_version"
                ] = (
                    BENCHMARK_VERSION
                )

                result[
                    split_name
                ].append(
                    invalid_case
                )

    return result


def selected_invalid_base_ids(
    plan: dict[
        str,
        dict[
            str,
            list[dict[str, Any]],
        ],
    ],
    split_name: str,
) -> set[str]:
    result: set[str] = set()

    for error_type in (
        ERROR_ORDER
    ):
        result.update(
            case["case_id"]
            for case in (
                plan[
                    split_name
                ][
                    error_type
                ]
            )
        )

    return result


def create_valid_cases(
    split_cases: dict[
        str,
        list[dict[str, Any]],
    ],
    plan: dict[
        str,
        dict[
            str,
            list[dict[str, Any]],
        ],
    ],
    invalid_cases: dict[
        str,
        list[dict[str, Any]],
    ],
) -> dict[
    str,
    list[dict[str, Any]],
]:
    result = {
        "train": [],
        "dev": [],
        "test": [],
    }

    for split_name in (
        "train",
        "dev",
        "test",
    ):
        excluded = (
            selected_invalid_base_ids(
                plan,
                split_name,
            )
        )

        candidates = [
            case
            for case
            in split_cases[
                split_name
            ]
            if (
                case["case_id"]
                not in excluded
            )
        ]

        candidates.sort(
            key=lambda case: (
                stable_rank(
                    case["case_id"],
                    salt=(
                        f"valid:"
                        f"{split_name}"
                    ),
                )
            )
        )

        required = len(
            invalid_cases[
                split_name
            ]
        )

        if (
            len(candidates)
            < required
        ):
            raise ValueError(
                f"Not enough unused "
                f"reference cases for "
                f"{split_name} valid "
                "examples."
            )

        for base_case in (
            candidates[:required]
        ):
            case = copy.deepcopy(
                base_case
            )

            original_case_id = (
                case["case_id"]
            )

            case["case_id"] = (
                f"VALID_"
                f"{original_case_id}"
            )

            case["metadata"] = (
                copy.deepcopy(
                    case[
                        "metadata"
                    ]
                )
            )

            case["metadata"][
                "parent_case_id"
            ] = original_case_id

            case["metadata"][
                "split"
            ] = split_name

            case["metadata"][
                "benchmark_version"
            ] = (
                BENCHMARK_VERSION
            )

            case["metadata"][
                "error_count"
            ] = 0

            case[
                "ground_truth"
            ] = {
                "valid": True,
                "errors": [],
            }

            result[
                split_name
            ].append(
                case
            )

    return result


def deterministic_shuffle(
    cases: list[dict[str, Any]],
    split_name: str,
) -> list[dict[str, Any]]:
    return sorted(
        cases,
        key=lambda case: (
            stable_rank(
                case[
                    "case_id"
                ],
                salt=(
                    f"final:"
                    f"{split_name}"
                ),
            )
        ),
    )


def verify_repository_isolation(
    final_splits: dict[
        str,
        list[dict[str, Any]],
    ],
) -> None:
    repository_sets = {}

    for (
        split_name,
        cases,
    ) in final_splits.items():
        repository_sets[
            split_name
        ] = {
            case["metadata"][
                "source_repository"
            ]
            for case in cases
        }

    if (
        repository_sets[
            "train"
        ]
        & repository_sets[
            "dev"
        ]
    ):
        raise ValueError(
            "Repository leakage "
            "between train and dev."
        )

    if (
        repository_sets[
            "train"
        ]
        & repository_sets[
            "test"
        ]
    ):
        raise ValueError(
            "Repository leakage "
            "between train and test."
        )

    if (
        repository_sets[
            "dev"
        ]
        & repository_sets[
            "test"
        ]
    ):
        raise ValueError(
            "Repository leakage "
            "between dev and test."
        )


def verify_source_schema_uniqueness(
    final_splits: dict[
        str,
        list[dict[str, Any]],
    ],
) -> None:
    source_schema_ids = []

    for cases in (
        final_splits.values()
    ):
        source_schema_ids.extend(
            case["metadata"][
                "source_schema_id"
            ]
            for case in cases
        )

    if (
        len(source_schema_ids)
        != len(
            set(
                source_schema_ids
            )
        )
    ):
        raise ValueError(
            "A SchemaPile source "
            "schema was reused in "
            "multiple benchmark cases."
        )


def create_toy_examples(
    final_splits: dict[
        str,
        list[dict[str, Any]],
    ],
) -> None:
    TOY_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    valid_source = next(
        case
        for case
        in final_splits[
            "test"
        ]
        if case[
            "ground_truth"
        ]["valid"]
    )

    invalid_source = next(
        case
        for case
        in final_splits[
            "test"
        ]
        if (
            not case[
                "ground_truth"
            ]["valid"]
            and case[
                "ground_truth"
            ][
                "errors"
            ][0][
                "error_type"
            ]
            == ERROR_ORDER[0]
        )
    )

    valid_toy = copy.deepcopy(
        valid_source
    )

    invalid_toy = copy.deepcopy(
        invalid_source
    )

    valid_toy[
        "case_id"
    ] = "TOY_VALID_001"

    invalid_toy[
        "case_id"
    ] = "TOY_INVALID_001"

    valid_toy[
        "metadata"
    ]["source"] = "toy"

    invalid_toy[
        "metadata"
    ]["source"] = "toy"

    save_json(
        valid_toy,
        TOY_VALID_PATH,
    )

    save_json(
        invalid_toy,
        TOY_INVALID_PATH,
    )


def build_manifest(
    final_splits: dict[
        str,
        list[dict[str, Any]],
    ],
    *,
    per_error_total: int,
) -> dict[str, Any]:
    error_distribution = Counter()

    valid_total = 0
    invalid_total = 0

    split_summary = {}

    for (
        split_name,
        cases,
    ) in final_splits.items():

        valid_count = sum(
            1
            for case in cases
            if case[
                "ground_truth"
            ]["valid"]
        )

        invalid_count = (
            len(cases)
            - valid_count
        )

        valid_total += (
            valid_count
        )

        invalid_total += (
            invalid_count
        )

        repository_count = len(
            {
                case[
                    "metadata"
                ][
                    "source_repository"
                ]
                for case in cases
            }
        )

        for case in cases:
            if not case[
                "ground_truth"
            ]["valid"]:
                error_distribution.update(
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

        split_summary[
            split_name
        ] = {
            "total": (
                len(cases)
            ),
            "valid": (
                valid_count
            ),
            "invalid": (
                invalid_count
            ),
            "source_repositories": (
                repository_count
            ),
        }

    return {
        "benchmark_version": (
            BENCHMARK_VERSION
        ),
        "source_dataset": (
            "SchemaPile-Perm"
        ),
        "source_paper": (
            "SchemaPile: A Large "
            "Collection of Relational "
            "Database Schemas"
        ),
        "source_paper_doi": (
            "10.1145/3654975"
        ),
        "source_dataset_doi": (
            "10.5281/zenodo.12682521"
        ),
        "random_seed": (
            RANDOM_SEED
        ),
        "diagram_type": (
            "Information Engineering "
            "Crow's-Foot ER"
        ),
        "total_cases": (
            valid_total
            + invalid_total
        ),
        "valid_cases": (
            valid_total
        ),
        "invalid_cases": (
            invalid_total
        ),
        "error_types": (
            len(ERROR_ORDER)
        ),
        "cases_per_error_type": (
            per_error_total
        ),
        "split_strategy": (
            "Deterministic "
            "repository-grouped "
            "70/15/15 split. "
            "All schemas from the "
            "same GitHub repository "
            "remain in one split."
        ),
        "source_schema_reuse": (
            "No SchemaPile source "
            "schema is used more "
            "than once in the final "
            "benchmark."
        ),
        "splits": (
            split_summary
        ),
        "error_distribution": (
            dict(
                sorted(
                    error_distribution.items()
                )
            )
        ),
    }


def build_dataset(
    requested_per_error: int | None = None,
) -> dict[
    str,
    list[dict[str, Any]],
]:
    references = (
        load_reference_cases()
    )

    split_cases = (
        split_reference_cases(
            references
        )
    )

    eligibility = (
        build_eligibility_cache(
            references
        )
    )

    (
        per_error_total,
        plan,
    ) = choose_total_per_error(
        split_cases,
        eligibility,
        requested_per_error,
    )

    print(
        f"Selected "
        f"{per_error_total} "
        "cases per error type."
    )

    invalid_cases = (
        create_invalid_cases(
            plan
        )
    )

    valid_cases = (
        create_valid_cases(
            split_cases,
            plan,
            invalid_cases,
        )
    )

    final_splits = {}

    for split_name in (
        "train",
        "dev",
        "test",
    ):
        combined = (
            valid_cases[
                split_name
            ]
            + invalid_cases[
                split_name
            ]
        )

        final_splits[
            split_name
        ] = (
            deterministic_shuffle(
                combined,
                split_name,
            )
        )

    validator = (
        get_er_case_validator()
    )

    case_ids = []

    for cases in (
        final_splits.values()
    ):
        for case in cases:
            validator.validate(
                case
            )

            case_ids.append(
                case[
                    "case_id"
                ]
            )

    if (
        len(case_ids)
        != len(
            set(
                case_ids
            )
        )
    ):
        raise ValueError(
            "Duplicate benchmark "
            "case IDs detected."
        )

    verify_repository_isolation(
        final_splits
    )

    verify_source_schema_uniqueness(
        final_splits
    )

    save_jsonl(
        final_splits[
            "train"
        ],
        TRAIN_PATH,
    )

    save_jsonl(
        final_splits[
            "dev"
        ],
        DEV_PATH,
    )

    save_jsonl(
        final_splits[
            "test"
        ],
        TEST_PATH,
    )

    manifest = build_manifest(
        final_splits,
        per_error_total=(
            per_error_total
        ),
    )

    save_json(
        manifest,
        MANIFEST_PATH,
    )

    create_toy_examples(
        final_splits
    )

    print()
    print(
        "SchemaPile benchmark "
        "build complete."
    )
    print()

    for split_name in (
        "train",
        "dev",
        "test",
    ):
        cases = final_splits[
            split_name
        ]

        valid_count = sum(
            1
            for case in cases
            if case[
                "ground_truth"
            ]["valid"]
        )

        invalid_count = (
            len(cases)
            - valid_count
        )

        print(
            f"{split_name.capitalize()}: "
            f"{len(cases):,} cases "
            f"({valid_count:,} valid, "
            f"{invalid_count:,} invalid)"
        )

    print()

    print(
        f"Total benchmark cases: "
        f"{manifest['total_cases']:,}"
    )

    print(
        f"Cases per error type: "
        f"{per_error_total:,}"
    )

    print(
        f"Manifest: "
        f"{MANIFEST_PATH}"
    )

    return final_splits


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Build the final "
            "SchemaPile-based "
            "ER validation benchmark."
        )
    )

    parser.add_argument(
        "--per-error",
        default="auto",
        help=(
            "Number of invalid cases "
            "per error category, or "
            "'auto'. Default: auto."
        ),
    )

    args = parser.parse_args()

    if (
        args.per_error.lower()
        == "auto"
    ):
        requested = None
    else:
        requested = int(
            args.per_error
        )

    build_dataset(
        requested_per_error=(
            requested
        )
    )


if __name__ == "__main__":
    main()