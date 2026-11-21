from __future__ import annotations

import hashlib
from collections import Counter
from pathlib import Path
from typing import Any

from src.core.io import (
    load_jsonl,
    save_json,
)
from src.data.inject_errors import (
    ERROR_ORDER,
    eligible_error_types,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]

REFERENCE_CASES_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "reference_cases.jsonl"
)

REPORT_PATH = (
    PROJECT_ROOT
    / "data"
    / "audits"
    / "eligibility_report.json"
)

RANDOM_SEED = 811


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


def build_eligibility_report() -> dict[
    str,
    Any,
]:
    if not (
        REFERENCE_CASES_PATH.exists()
    ):
        raise FileNotFoundError(
            "Reference cases have not "
            "been created. Run:\n"
            "python -m "
            "src.data.import_schemapile"
        )

    cases = load_jsonl(
        REFERENCE_CASES_PATH
    )

    global_counts = Counter()

    split_counts = {
        "train": Counter(),
        "dev": Counter(),
        "test": Counter(),
    }

    case_counts = Counter()

    repository_sets = {
        "train": set(),
        "dev": set(),
        "test": set(),
    }

    table_counts = []
    column_counts = []
    foreign_key_counts = []

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

        repository_sets[
            split_name
        ].add(
            repository
        )

        case_counts[
            split_name
        ] += 1

        table_counts.append(
            case["metadata"][
                "table_count"
            ]
        )

        column_counts.append(
            case["metadata"][
                "column_count"
            ]
        )

        foreign_key_counts.append(
            case["metadata"][
                "foreign_key_count"
            ]
        )

        eligible = (
            eligible_error_types(
                case
            )
        )

        for error_type in eligible:
            global_counts[
                error_type
            ] += 1

            split_counts[
                split_name
            ][
                error_type
            ] += 1

    report = {
        "reference_case_count": (
            len(cases)
        ),
        "split_case_counts": {
            split_name: (
                case_counts[
                    split_name
                ]
            )
            for split_name in (
                "train",
                "dev",
                "test",
            )
        },
        "split_repository_counts": {
            split_name: (
                len(
                    repository_sets[
                        split_name
                    ]
                )
            )
            for split_name in (
                "train",
                "dev",
                "test",
            )
        },
        "eligibility_global": {
            error_type: (
                global_counts[
                    error_type
                ]
            )
            for error_type in (
                ERROR_ORDER
            )
        },
        "eligibility_by_split": {
            split_name: {
                error_type: (
                    split_counts[
                        split_name
                    ][
                        error_type
                    ]
                )
                for error_type
                in ERROR_ORDER
            }
            for split_name in (
                "train",
                "dev",
                "test",
            )
        },
        "schema_size_summary": {
            "min_tables": (
                min(
                    table_counts
                )
                if table_counts
                else 0
            ),
            "max_tables": (
                max(
                    table_counts
                )
                if table_counts
                else 0
            ),
            "min_columns": (
                min(
                    column_counts
                )
                if column_counts
                else 0
            ),
            "max_columns": (
                max(
                    column_counts
                )
                if column_counts
                else 0
            ),
            "min_foreign_keys": (
                min(
                    foreign_key_counts
                )
                if foreign_key_counts
                else 0
            ),
            "max_foreign_keys": (
                max(
                    foreign_key_counts
                )
                if foreign_key_counts
                else 0
            ),
        },
    }

    save_json(
        report,
        REPORT_PATH,
    )

    print(
        "Eligibility audit complete."
    )

    print()

    print(
        f"Reference cases: "
        f"{len(cases):,}"
    )

    print()

    for error_type in ERROR_ORDER:
        print(
            f"{error_type}: "
            f"{global_counts[error_type]:,}"
        )

        print(
            "  Train: "
            f"{split_counts['train'][error_type]:,}"
        )

        print(
            "  Dev:   "
            f"{split_counts['dev'][error_type]:,}"
        )

        print(
            "  Test:  "
            f"{split_counts['test'][error_type]:,}"
        )

    print()

    print(
        f"Saved report: "
        f"{REPORT_PATH}"
    )

    return report


def main() -> None:
    build_eligibility_report()


if __name__ == "__main__":
    main()