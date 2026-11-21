from __future__ import annotations

import gzip
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from src.core.io import (
    get_er_case_validator,
    save_json,
    save_jsonl,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]

RAW_PATH = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "schemapile-perm.json.gz"
)

PROCESSED_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
)

REFERENCE_CASES_PATH = (
    PROCESSED_DIR
    / "reference_cases.jsonl"
)

AUDIT_DIR = (
    PROJECT_ROOT
    / "data"
    / "audits"
)

IMPORT_REPORT_PATH = (
    AUDIT_DIR
    / "import_report.json"
)


SOURCE_DATASET = "SchemaPile-Perm"
SOURCE_DOI = "10.1145/3654975"
SOURCE_ZENODO = "10.5281/zenodo.12682521"

IMPORT_VERSION = "1.0"

MIN_TABLES = 2
MAX_TABLES = 20
MAX_COLUMNS_PER_TABLE = 60
MAX_TOTAL_COLUMNS = 200
MAX_FOREIGN_KEYS = 30


def as_string_list(
    value: Any,
) -> list[str]:
    if value is None:
        return []

    if isinstance(
        value,
        str,
    ):
        return [value]

    if not isinstance(
        value,
        list,
    ):
        return []

    result: list[str] = []

    for item in value:

        if isinstance(
            item,
            str,
        ):
            result.append(item)

        elif isinstance(
            item,
            list,
        ):
            result.extend(
                as_string_list(
                    item
                )
            )

    return result


def get_primary_key_names(
    table: dict[str, Any],
) -> list[str]:
    columns = table.get(
        "COLUMNS",
        {},
    )

    explicit = as_string_list(
        table.get(
            "PRIMARY_KEYS"
        )
    )

    result: list[str] = []

    for name in explicit:
        if (
            name in columns
            and name not in result
        ):
            result.append(name)

    for (
        column_name,
        column_data,
    ) in columns.items():

        if (
            isinstance(
                column_data,
                dict,
            )
            and column_data.get(
                "IS_PRIMARY",
                False,
            )
            and column_name
            not in result
        ):
            result.append(
                column_name
            )

    return result


def parse_foreign_key(
    foreign_key: dict[str, Any],
) -> dict[str, Any]:
    return {
        "columns": (
            as_string_list(
                foreign_key.get(
                    "COLUMNS"
                )
            )
        ),
        "foreign_table": (
            str(
                foreign_key.get(
                    "FOREIGN_TABLE",
                    "",
                )
            )
        ),
        "referred_columns": (
            as_string_list(
                foreign_key.get(
                    "REFERRED_COLUMNS"
                )
            )
        ),
        "on_delete": (
            foreign_key.get(
                "ON_DELETE"
            )
        ),
        "on_update": (
            foreign_key.get(
                "ON_UPDATE"
            )
        ),
    }


def extract_repository(
    url: str,
) -> str | None:
    if not url:
        return None

    try:
        parsed = urlparse(url)
    except ValueError:
        return None

    host = (
        parsed.netloc
        .lower()
        .removeprefix("www.")
    )

    parts = [
        part
        for part in (
            parsed.path.split("/")
        )
        if part
    ]

    if (
        host == "github.com"
        and len(parts) >= 2
    ):
        owner = parts[0]
        repository = (
            parts[1]
            .removesuffix(".git")
        )

        return (
            f"{owner}/{repository}"
            .lower()
        )

    if (
        host
        == "raw.githubusercontent.com"
        and len(parts) >= 2
    ):
        owner = parts[0]
        repository = parts[1]

        return (
            f"{owner}/{repository}"
            .lower()
        )

    return None


def target_columns_form_key(
    parent_table: dict[str, Any],
    referred_columns: list[str],
) -> bool:
    if not referred_columns:
        return False

    columns = parent_table[
        "COLUMNS"
    ]

    primary_keys = (
        get_primary_key_names(
            parent_table
        )
    )

    if (
        len(primary_keys)
        == len(referred_columns)
        and set(primary_keys)
        == set(referred_columns)
    ):
        return True

    for column_name in (
        referred_columns
    ):
        column = columns.get(
            column_name
        )

        if not isinstance(
            column,
            dict,
        ):
            return False

        if not column.get(
            "UNIQUE",
            False,
        ):
            return False

    return True


def screen_schema(
    schema_id: str,
    schema: dict[str, Any],
) -> tuple[
    bool,
    str | None,
    dict[str, Any],
]:
    if not isinstance(
        schema,
        dict,
    ):
        return (
            False,
            "schema_not_object",
            {},
        )

    info = schema.get(
        "INFO",
        {},
    )

    if not isinstance(
        info,
        dict,
    ):
        return (
            False,
            "missing_info",
            {},
        )

    source_url = str(
        info.get(
            "URL",
            "",
        )
        or ""
    )

    repository = (
        extract_repository(
            source_url
        )
    )

    if repository is None:
        return (
            False,
            "unusable_source_repository",
            {},
        )

    permissive = info.get(
        "PERMISSIVE",
        schema.get(
            "PERMISSIVE",
            True,
        ),
    )

    if permissive is False:
        return (
            False,
            "not_permissive",
            {},
        )

    tables = schema.get(
        "TABLES"
    )

    if not isinstance(
        tables,
        dict,
    ):
        return (
            False,
            "missing_tables",
            {},
        )

    table_count = len(tables)

    if (
        table_count
        < MIN_TABLES
    ):
        return (
            False,
            "too_few_tables",
            {},
        )

    if (
        table_count
        > MAX_TABLES
    ):
        return (
            False,
            "too_many_tables",
            {},
        )

    lower_table_names = [
        str(name).lower()
        for name in tables
    ]

    if (
        len(lower_table_names)
        != len(
            set(
                lower_table_names
            )
        )
    ):
        return (
            False,
            "case_ambiguous_table_names",
            {},
        )

    total_columns = 0
    total_primary_keys = 0
    total_foreign_keys = 0
    composite_foreign_keys = 0

    foreign_key_pairs: dict[
        tuple[str, str],
        tuple[
            tuple[str, ...],
            tuple[str, ...],
        ],
    ] = {}

    local_column_targets: dict[
        tuple[str, str],
        tuple[str, str],
    ] = {}

    for (
        table_name,
        table,
    ) in tables.items():

        if not isinstance(
            table,
            dict,
        ):
            return (
                False,
                "table_not_object",
                {},
            )

        columns = table.get(
            "COLUMNS"
        )

        if not isinstance(
            columns,
            dict,
        ):
            return (
                False,
                "missing_columns",
                {},
            )

        if not columns:
            return (
                False,
                "empty_table",
                {},
            )

        if (
            len(columns)
            > MAX_COLUMNS_PER_TABLE
        ):
            return (
                False,
                "too_many_columns_in_table",
                {},
            )

        total_columns += len(
            columns
        )

        if (
            total_columns
            > MAX_TOTAL_COLUMNS
        ):
            return (
                False,
                "too_many_total_columns",
                {},
            )

        lower_column_names = [
            str(name).lower()
            for name in columns
        ]

        if (
            len(lower_column_names)
            != len(
                set(
                    lower_column_names
                )
            )
        ):
            return (
                False,
                "case_ambiguous_column_names",
                {},
            )

        primary_keys = (
            get_primary_key_names(
                table
            )
        )

        total_primary_keys += len(
            primary_keys
        )

        for primary_key in (
            primary_keys
        ):
            if (
                primary_key
                not in columns
            ):
                return (
                    False,
                    "missing_primary_key_column",
                    {},
                )

        raw_foreign_keys = (
            table.get(
                "FOREIGN_KEYS",
                [],
            )
        )

        if raw_foreign_keys is None:
            raw_foreign_keys = []

        if not isinstance(
            raw_foreign_keys,
            list,
        ):
            return (
                False,
                "foreign_keys_not_list",
                {},
            )

        for raw_fk in (
            raw_foreign_keys
        ):

            if not isinstance(
                raw_fk,
                dict,
            ):
                return (
                    False,
                    "foreign_key_not_object",
                    {},
                )

            foreign_key = (
                parse_foreign_key(
                    raw_fk
                )
            )

            local_columns = (
                foreign_key[
                    "columns"
                ]
            )

            parent_name = (
                foreign_key[
                    "foreign_table"
                ]
            )

            referred_columns = (
                foreign_key[
                    "referred_columns"
                ]
            )

            if (
                not local_columns
                or not parent_name
                or not referred_columns
            ):
                return (
                    False,
                    "incomplete_foreign_key",
                    {},
                )

            if (
                len(local_columns)
                != len(
                    referred_columns
                )
            ):
                return (
                    False,
                    "foreign_key_arity_mismatch",
                    {},
                )

            if (
                parent_name
                not in tables
            ):
                return (
                    False,
                    "missing_foreign_table",
                    {},
                )

            if (
                parent_name
                == table_name
            ):
                return (
                    False,
                    "self_referential_foreign_key",
                    {},
                )

            for column_name in (
                local_columns
            ):
                if (
                    column_name
                    not in columns
                ):
                    return (
                        False,
                        "missing_local_fk_column",
                        {},
                    )

            parent_table = (
                tables[parent_name]
            )

            parent_columns = (
                parent_table.get(
                    "COLUMNS",
                    {},
                )
            )

            for column_name in (
                referred_columns
            ):
                if (
                    column_name
                    not in parent_columns
                ):
                    return (
                        False,
                        "missing_referred_column",
                        {},
                    )

            if not target_columns_form_key(
                parent_table,
                referred_columns,
            ):
                return (
                    False,
                    "foreign_key_target_not_representable_key",
                    {},
                )

            pair = (
                str(table_name),
                str(parent_name),
            )

            signature = (
                tuple(local_columns),
                tuple(
                    referred_columns
                ),
            )

            if (
                pair
                in foreign_key_pairs
                and foreign_key_pairs[
                    pair
                ]
                != signature
            ):
                return (
                    False,
                    "multiple_fk_relations_same_table_pair",
                    {},
                )

            foreign_key_pairs[
                pair
            ] = signature

            for (
                local_column,
                referred_column,
            ) in zip(
                local_columns,
                referred_columns,
            ):
                mapping_key = (
                    str(table_name),
                    local_column,
                )

                target = (
                    str(parent_name),
                    referred_column,
                )

                if (
                    mapping_key
                    in local_column_targets
                    and local_column_targets[
                        mapping_key
                    ]
                    != target
                ):
                    return (
                        False,
                        "fk_column_has_multiple_targets",
                        {},
                    )

                local_column_targets[
                    mapping_key
                ] = target

            total_foreign_keys += 1

            if (
                len(local_columns)
                > 1
            ):
                composite_foreign_keys += (
                    1
                )

            if (
                total_foreign_keys
                > MAX_FOREIGN_KEYS
            ):
                return (
                    False,
                    "too_many_foreign_keys",
                    {},
                )

    if (
        total_foreign_keys
        == 0
    ):
        return (
            False,
            "no_foreign_keys",
            {},
        )

    if (
        total_primary_keys
        == 0
    ):
        return (
            False,
            "no_primary_keys",
            {},
        )

    return (
        True,
        None,
        {
            "schema_id": schema_id,
            "source_repository": (
                repository
            ),
            "table_count": (
                table_count
            ),
            "column_count": (
                total_columns
            ),
            "foreign_key_count": (
                total_foreign_keys
            ),
            "composite_foreign_key_count": (
                composite_foreign_keys
            ),
        },
    )


def make_case_id(
    source_schema_id: str,
) -> str:
    digest = hashlib.sha1(
        source_schema_id.encode(
            "utf-8"
        )
    ).hexdigest()[:12]

    return (
        f"SP_{digest.upper()}"
    )


def relationship_name(
    child_name: str,
    parent_name: str,
    index: int,
) -> str:
    return (
        f"fk_{index:03d}_"
        f"{child_name}_to_"
        f"{parent_name}"
    )


def cardinality_bounds(
    cardinality: str,
) -> tuple[
    int,
    int | str,
]:
    mapping = {
        "0..1": (0, 1),
        "1": (1, 1),
        "0..*": (0, "*"),
        "1..*": (1, "*"),
    }

    return mapping[
        cardinality
    ]


def build_requirement(
    relationship: dict[str, Any],
    index: int,
) -> dict[str, Any]:
    child = relationship[
        "child"
    ]

    parent = relationship[
        "parent"
    ]

    parent_cardinality = (
        relationship[
            "parent_cardinality"
        ]
    )

    child_cardinality = (
        relationship[
            "child_cardinality"
        ]
    )

    source_min, source_max = (
        cardinality_bounds(
            parent_cardinality
        )
    )

    target_min, target_max = (
        cardinality_bounds(
            child_cardinality
        )
    )

    if parent_cardinality == "1":
        text = (
            f"Each {child} row must "
            f"reference exactly one "
            f"{parent} row for this "
            f"foreign-key relationship."
        )
    else:
        text = (
            f"Each {child} row may "
            f"reference at most one "
            f"{parent} row for this "
            f"foreign-key relationship."
        )

    return {
        "requirement_id": (
            f"R{index}"
        ),
        "text": text,
        "type": (
            "relationship_cardinality"
        ),
        "source": child,
        "target": parent,
        "source_min": source_min,
        "source_max": source_max,
        "target_min": target_min,
        "target_max": target_max,
    }


def determine_difficulty(
    table_count: int,
    foreign_key_count: int,
    composite_foreign_key_count: int,
) -> str:
    if (
        composite_foreign_key_count
        > 0
        or table_count > 10
        or foreign_key_count > 8
    ):
        return "hard"

    if (
        table_count > 5
        or foreign_key_count > 3
    ):
        return "medium"

    return "easy"


def normalize_schema_record(
    source_schema_id: str,
    raw_schema: dict[str, Any],
) -> dict[str, Any]:
    accepted, reason, metrics = (
        screen_schema(
            source_schema_id,
            raw_schema,
        )
    )

    if not accepted:
        raise ValueError(
            f"Schema {source_schema_id} "
            f"did not pass screening: "
            f"{reason}"
        )

    info = raw_schema[
        "INFO"
    ]

    tables = raw_schema[
        "TABLES"
    ]

    source_url = str(
        info.get(
            "URL",
            "",
        )
        or ""
    )

    license_name = str(
        info.get(
            "LICENSE",
            "",
        )
        or ""
    )

    reference_map: dict[
        tuple[str, str],
        dict[str, str],
    ] = {}

    parsed_relationships: list[
        dict[str, Any]
    ] = []

    relationship_index = 1

    for (
        child_name,
        child_table,
    ) in tables.items():

        child_columns = (
            child_table[
                "COLUMNS"
            ]
        )

        child_pk = (
            get_primary_key_names(
                child_table
            )
        )

        for raw_fk in (
            child_table.get(
                "FOREIGN_KEYS",
                [],
            )
            or []
        ):
            foreign_key = (
                parse_foreign_key(
                    raw_fk
                )
            )

            local_columns = (
                foreign_key[
                    "columns"
                ]
            )

            parent_name = (
                foreign_key[
                    "foreign_table"
                ]
            )

            referred_columns = (
                foreign_key[
                    "referred_columns"
                ]
            )

            for (
                local_column,
                referred_column,
            ) in zip(
                local_columns,
                referred_columns,
            ):
                reference_map[
                    (
                        str(
                            child_name
                        ),
                        local_column,
                    )
                ] = {
                    "entity": (
                        str(
                            parent_name
                        )
                    ),
                    "attribute": (
                        referred_column
                    ),
                }

            local_nullable = []

            local_unique = []

            for column_name in (
                local_columns
            ):
                column_data = (
                    child_columns[
                        column_name
                    ]
                )

                is_primary = (
                    column_name
                    in child_pk
                )

                nullable = (
                    False
                    if is_primary
                    else bool(
                        column_data.get(
                            "NULLABLE",
                            True,
                        )
                    )
                )

                unique = bool(
                    column_data.get(
                        "UNIQUE",
                        False,
                    )
                )

                if (
                    len(child_pk) == 1
                    and is_primary
                ):
                    unique = True

                local_nullable.append(
                    nullable
                )

                local_unique.append(
                    unique
                )

            parent_cardinality = (
                "1"
                if not any(
                    local_nullable
                )
                else "0..1"
            )

            foreign_key_is_unique = (
                (
                    len(child_pk)
                    == len(
                        local_columns
                    )
                    and set(
                        child_pk
                    )
                    == set(
                        local_columns
                    )
                )
                or all(
                    local_unique
                )
            )

            child_cardinality = (
                "0..1"
                if foreign_key_is_unique
                else "0..*"
            )

            identifying = all(
                column_name
                in child_pk
                for column_name
                in local_columns
            )

            parsed_relationships.append(
                {
                    "name": (
                        relationship_name(
                            str(
                                child_name
                            ),
                            str(
                                parent_name
                            ),
                            relationship_index,
                        )
                    ),
                    "parent": (
                        str(
                            parent_name
                        )
                    ),
                    "child": (
                        str(
                            child_name
                        )
                    ),
                    "parent_cardinality": (
                        parent_cardinality
                    ),
                    "child_cardinality": (
                        child_cardinality
                    ),
                    "identifying": (
                        identifying
                    ),
                }
            )

            relationship_index += (
                1
            )

    entities: list[
        dict[str, Any]
    ] = []

    for (
        table_name,
        table,
    ) in tables.items():

        columns = table[
            "COLUMNS"
        ]

        primary_keys = (
            get_primary_key_names(
                table
            )
        )

        attributes: list[
            dict[str, Any]
        ] = []

        for (
            column_name,
            column_data,
        ) in columns.items():

            is_primary = (
                column_name
                in primary_keys
            )

            unique = bool(
                column_data.get(
                    "UNIQUE",
                    False,
                )
            )

            if (
                len(primary_keys)
                == 1
                and is_primary
            ):
                unique = True

            nullable = (
                False
                if is_primary
                else bool(
                    column_data.get(
                        "NULLABLE",
                        True,
                    )
                )
            )

            reference = (
                reference_map.get(
                    (
                        str(
                            table_name
                        ),
                        str(
                            column_name
                        ),
                    )
                )
            )

            attribute: dict[
                str,
                Any,
            ] = {
                "name": (
                    str(
                        column_name
                    )
                ),
                "type": (
                    str(
                        column_data.get(
                            "TYPE",
                            "UNKNOWN",
                        )
                        or "UNKNOWN"
                    )
                ),
                "primary_key": (
                    is_primary
                ),
                "foreign_key": (
                    reference
                    is not None
                ),
                "nullable": (
                    nullable
                ),
                "unique": (
                    unique
                ),
            }

            if (
                reference
                is not None
            ):
                attribute[
                    "references"
                ] = reference

            attributes.append(
                attribute
            )

        entities.append(
            {
                "name": (
                    str(
                        table_name
                    )
                ),
                "attributes": (
                    attributes
                ),
            }
        )

    requirements = [
        build_requirement(
            relationship,
            index,
        )
        for index, relationship
        in enumerate(
            parsed_relationships,
            start=1,
        )
    ]

    difficulty = (
        determine_difficulty(
            metrics[
                "table_count"
            ],
            metrics[
                "foreign_key_count"
            ],
            metrics[
                "composite_foreign_key_count"
            ],
        )
    )

    repository = metrics[
        "source_repository"
    ]

    case = {
        "case_id": (
            make_case_id(
                source_schema_id
            )
        ),
        "domain": "real_world",
        "description": (
            "Real-world relational "
            "schema imported from "
            "SchemaPile-Perm. "
            f"Source repository: "
            f"{repository}."
        ),
        "entities": entities,
        "relationships": (
            parsed_relationships
        ),
        "requirements": (
            requirements
        ),
        "metadata": {
            "source": (
                "real_world"
            ),
            "difficulty": (
                difficulty
            ),
            "version": 1,
            "source_dataset": (
                SOURCE_DATASET
            ),
            "source_schema_id": (
                source_schema_id
            ),
            "source_url": (
                source_url
            ),
            "source_repository": (
                repository
            ),
            "license": (
                license_name
            ),
            "import_version": (
                IMPORT_VERSION
            ),
            "reference_status": (
                "reference_consistent"
            ),
            "table_count": (
                metrics[
                    "table_count"
                ]
            ),
            "column_count": (
                metrics[
                    "column_count"
                ]
            ),
            "foreign_key_count": (
                metrics[
                    "foreign_key_count"
                ]
            ),
            "composite_foreign_key_count": (
                metrics[
                    "composite_foreign_key_count"
                ]
            ),
            "error_count": 0,
        },
        "ground_truth": {
            "valid": True,
            "errors": [],
        },
    }

    return case


def load_raw_schemapile() -> dict[
    str,
    Any,
]:
    if not RAW_PATH.exists():
        raise FileNotFoundError(
            "SchemaPile-Perm has not "
            "been downloaded. Run:\n"
            "python -m "
            "src.data.download_schemapile"
        )

    print(
        "Loading SchemaPile-Perm..."
    )

    with gzip.open(
        RAW_PATH,
        "rt",
        encoding="utf-8",
    ) as file:
        data = json.load(file)

    if not isinstance(
        data,
        dict,
    ):
        raise ValueError(
            "Expected top-level "
            "SchemaPile object."
        )

    return data


def import_schemapile() -> list[
    dict[str, Any]
]:
    PROCESSED_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    AUDIT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    raw_dataset = (
        load_raw_schemapile()
    )

    validator = (
        get_er_case_validator()
    )

    rejection_counts = Counter()

    reference_cases: list[
        dict[str, Any]
    ] = []

    repositories: set[str] = set()

    seen_case_ids: set[str] = (
        set()
    )

    total = len(
        raw_dataset
    )

    for index, source_schema_id in enumerate(
        sorted(
            raw_dataset
        ),
        start=1,
    ):
        raw_schema = (
            raw_dataset[
                source_schema_id
            ]
        )

        (
            accepted,
            reason,
            metrics,
        ) = screen_schema(
            source_schema_id,
            raw_schema,
        )

        if not accepted:
            rejection_counts[
                reason
                or "unknown"
            ] += 1

            continue

        try:
            case = (
                normalize_schema_record(
                    source_schema_id,
                    raw_schema,
                )
            )

            validator.validate(
                case
            )

        except Exception as error:
            rejection_counts[
                "normalization_or_schema_error"
            ] += 1

            print(
                f"\nRejected "
                f"{source_schema_id}: "
                f"{error}"
            )

            continue

        if (
            case["case_id"]
            in seen_case_ids
        ):
            rejection_counts[
                "case_id_collision"
            ] += 1

            continue

        seen_case_ids.add(
            case["case_id"]
        )

        repositories.add(
            metrics[
                "source_repository"
            ]
        )

        reference_cases.append(
            case
        )

        if (
            index % 1000
            == 0
        ):
            print(
                f"Processed "
                f"{index:,}/"
                f"{total:,} raw schemas..."
            )

    save_jsonl(
        reference_cases,
        REFERENCE_CASES_PATH,
    )

    report = {
        "source_dataset": (
            SOURCE_DATASET
        ),
        "source_doi": (
            SOURCE_DOI
        ),
        "source_zenodo": (
            SOURCE_ZENODO
        ),
        "import_version": (
            IMPORT_VERSION
        ),
        "raw_schema_count": (
            total
        ),
        "accepted_reference_cases": (
            len(
                reference_cases
            )
        ),
        "distinct_source_repositories": (
            len(
                repositories
            )
        ),
        "rejected_schema_count": (
            total
            - len(
                reference_cases
            )
        ),
        "rejection_reasons": dict(
            sorted(
                rejection_counts.items()
            )
        ),
        "filters": {
            "min_tables": (
                MIN_TABLES
            ),
            "max_tables": (
                MAX_TABLES
            ),
            "max_columns_per_table": (
                MAX_COLUMNS_PER_TABLE
            ),
            "max_total_columns": (
                MAX_TOTAL_COLUMNS
            ),
            "max_foreign_keys": (
                MAX_FOREIGN_KEYS
            ),
            "requires_foreign_key": True,
            "requires_primary_key": True,
            "requires_github_repository": True,
            "self_referential_fk_allowed": False,
            "multiple_fk_same_pair_allowed": False,
            "fk_target_must_be_representable_key": True,
        },
    }

    save_json(
        report,
        IMPORT_REPORT_PATH,
    )

    print()
    print(
        "SchemaPile import complete."
    )

    print(
        f"Raw schemas: "
        f"{total:,}"
    )

    print(
        f"Accepted reference cases: "
        f"{len(reference_cases):,}"
    )

    print(
        f"Distinct repositories: "
        f"{len(repositories):,}"
    )

    print(
        f"Rejected schemas: "
        f"{total - len(reference_cases):,}"
    )

    print()
    print(
        f"Reference cases: "
        f"{REFERENCE_CASES_PATH}"
    )

    print(
        f"Import report: "
        f"{IMPORT_REPORT_PATH}"
    )

    return reference_cases


def main() -> None:
    import_schemapile()


if __name__ == "__main__":
    main()