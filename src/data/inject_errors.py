from __future__ import annotations

import copy
import random
from typing import Any

from src.core.constants import (
    ERROR_CARDINALITY_UNIQUENESS_CONFLICT,
    ERROR_COMPOSITE_FK_INCOMPLETE,
    ERROR_FK_TARGET_NOT_KEY,
    ERROR_FK_WRONG_ENTITY,
    ERROR_IDENTIFYING_RELATIONSHIP_KEY_ERROR,
    ERROR_MISSING_REQUIRED_RELATIONSHIP,
    ERROR_PARTICIPATION_OPTIONALITY_CONFLICT,
)
from src.core.io import (
    validate_case_dict,
)


MUTATION_VERSION = "3.0"


ERROR_ORDER = (
    ERROR_FK_TARGET_NOT_KEY,
    ERROR_FK_WRONG_ENTITY,
    ERROR_COMPOSITE_FK_INCOMPLETE,
    ERROR_CARDINALITY_UNIQUENESS_CONFLICT,
    ERROR_PARTICIPATION_OPTIONALITY_CONFLICT,
    ERROR_IDENTIFYING_RELATIONSHIP_KEY_ERROR,
    ERROR_MISSING_REQUIRED_RELATIONSHIP,
)


ERROR_SELECTION_ORDER = (
    ERROR_COMPOSITE_FK_INCOMPLETE,
    ERROR_IDENTIFYING_RELATIONSHIP_KEY_ERROR,
    ERROR_CARDINALITY_UNIQUENESS_CONFLICT,
    ERROR_FK_TARGET_NOT_KEY,
    ERROR_FK_WRONG_ENTITY,
    ERROR_PARTICIPATION_OPTIONALITY_CONFLICT,
    ERROR_MISSING_REQUIRED_RELATIONSHIP,
)


def get_entity(
    case: dict[str, Any],
    entity_name: str,
) -> dict[str, Any]:
    for entity in case[
        "entities"
    ]:
        if (
            entity["name"]
            == entity_name
        ):
            return entity

    raise ValueError(
        f"Entity not found: "
        f"{entity_name}"
    )


def primary_key_attributes(
    entity: dict[str, Any],
) -> list[dict[str, Any]]:
    return [
        attribute
        for attribute
        in entity["attributes"]
        if attribute.get(
            "primary_key",
            False,
        )
    ]


def candidate_key_attributes(
    entity: dict[str, Any],
) -> list[dict[str, Any]]:
    primary_keys = (
        primary_key_attributes(
            entity
        )
    )

    candidates = []

    if (
        len(primary_keys)
        == 1
    ):
        candidates.append(
            primary_keys[0]
        )

    for attribute in entity[
        "attributes"
    ]:
        if (
            attribute.get(
                "unique",
                False,
            )
            and attribute
            not in candidates
        ):
            candidates.append(
                attribute
            )

    return candidates


def foreign_keys_to_parent(
    case: dict[str, Any],
    relationship: dict[str, Any],
) -> list[dict[str, Any]]:
    child = get_entity(
        case,
        relationship["child"],
    )

    parent_name = (
        relationship["parent"]
    )

    result = []

    for attribute in child[
        "attributes"
    ]:

        if not attribute.get(
            "foreign_key",
            False,
        ):
            continue

        reference = (
            attribute.get(
                "references"
            )
        )

        if not reference:
            continue

        if (
            reference["entity"]
            == parent_name
        ):
            result.append(
                attribute
            )

    return result


def choose_candidate(
    candidates: list[Any],
    seed: int,
) -> Any:
    if not candidates:
        raise ValueError(
            "No eligible mutation "
            "candidate."
        )

    rng = random.Random(seed)

    return rng.choice(
        candidates
    )


def candidates_fk_target_not_key(
    case: dict[str, Any],
) -> list[dict[str, Any]]:
    candidates = []

    for relationship in case[
        "relationships"
    ]:

        parent = get_entity(
            case,
            relationship["parent"],
        )

        child_fks = (
            foreign_keys_to_parent(
                case,
                relationship,
            )
        )

        if (
            len(child_fks)
            != 1
        ):
            continue

        child_fk = (
            child_fks[0]
        )

        for target in parent[
            "attributes"
        ]:

            if target.get(
                "primary_key",
                False,
            ):
                continue

            if target.get(
                "unique",
                False,
            ):
                continue

            if (
                target["type"]
                != child_fk["type"]
            ):
                continue

            candidates.append(
                {
                    "relationship": (
                        relationship
                    ),
                    "child_fk": (
                        child_fk
                    ),
                    "target": target,
                }
            )

    return candidates


def candidates_fk_wrong_entity(
    case: dict[str, Any],
) -> list[dict[str, Any]]:
    candidates = []

    for relationship in case[
        "relationships"
    ]:

        child_fks = (
            foreign_keys_to_parent(
                case,
                relationship,
            )
        )

        if (
            len(child_fks)
            != 1
        ):
            continue

        child_fk = (
            child_fks[0]
        )

        expected_parent = (
            relationship[
                "parent"
            ]
        )

        for alternative in case[
            "entities"
        ]:

            if (
                alternative["name"]
                == expected_parent
            ):
                continue

            for key_attribute in (
                candidate_key_attributes(
                    alternative
                )
            ):

                if (
                    key_attribute[
                        "type"
                    ]
                    != child_fk[
                        "type"
                    ]
                ):
                    continue

                candidates.append(
                    {
                        "relationship": (
                            relationship
                        ),
                        "child_fk": (
                            child_fk
                        ),
                        "alternative_entity": (
                            alternative
                        ),
                        "alternative_key": (
                            key_attribute
                        ),
                    }
                )

    return candidates


def candidates_composite_fk_incomplete(
    case: dict[str, Any],
) -> list[dict[str, Any]]:
    candidates = []

    for relationship in case[
        "relationships"
    ]:

        child_fks = (
            foreign_keys_to_parent(
                case,
                relationship,
            )
        )

        if (
            len(child_fks)
            < 2
        ):
            continue

        candidates.append(
            {
                "relationship": (
                    relationship
                ),
                "child_fks": (
                    child_fks
                ),
            }
        )

    return candidates


def candidates_cardinality_uniqueness(
    case: dict[str, Any],
) -> list[dict[str, Any]]:
    candidates = []

    for relationship in case[
        "relationships"
    ]:

        if (
            relationship[
                "child_cardinality"
            ]
            not in {
                "0..1",
                "1",
            }
        ):
            continue

        child_fks = (
            foreign_keys_to_parent(
                case,
                relationship,
            )
        )

        if (
            len(child_fks)
            != 1
        ):
            continue

        child_fk = (
            child_fks[0]
        )

        if not child_fk.get(
            "unique",
            False,
        ):
            continue

        candidates.append(
            {
                "relationship": (
                    relationship
                ),
                "child_fk": (
                    child_fk
                ),
            }
        )

    return candidates


def candidates_participation_optionality(
    case: dict[str, Any],
) -> list[dict[str, Any]]:
    candidates = []

    for relationship in case[
        "relationships"
    ]:

        if (
            relationship[
                "parent_cardinality"
            ]
            != "1"
        ):
            continue

        child_fks = (
            foreign_keys_to_parent(
                case,
                relationship,
            )
        )

        nonnullable = [
            attribute
            for attribute
            in child_fks
            if not attribute.get(
                "nullable",
                False,
            )
        ]

        if not nonnullable:
            continue

        candidates.append(
            {
                "relationship": (
                    relationship
                ),
                "eligible_fks": (
                    nonnullable
                ),
            }
        )

    return candidates


def candidates_identifying_key_error(
    case: dict[str, Any],
) -> list[dict[str, Any]]:
    candidates = []

    for relationship in case[
        "relationships"
    ]:

        if not relationship.get(
            "identifying",
            False,
        ):
            continue

        child_fks = (
            foreign_keys_to_parent(
                case,
                relationship,
            )
        )

        primary_fks = [
            attribute
            for attribute
            in child_fks
            if attribute.get(
                "primary_key",
                False,
            )
        ]

        if not primary_fks:
            continue

        candidates.append(
            {
                "relationship": (
                    relationship
                ),
                "primary_fks": (
                    primary_fks
                ),
            }
        )

    return candidates


def candidates_missing_relationship(
    case: dict[str, Any],
) -> list[dict[str, Any]]:
    candidates = []

    for relationship in case[
        "relationships"
    ]:

        child_fks = (
            foreign_keys_to_parent(
                case,
                relationship,
            )
        )

        if not child_fks:
            continue

        candidates.append(
            {
                "relationship": (
                    relationship
                ),
                "child_fks": (
                    child_fks
                ),
            }
        )

    return candidates


CANDIDATE_FUNCTIONS = {
    ERROR_FK_TARGET_NOT_KEY: (
        candidates_fk_target_not_key
    ),
    ERROR_FK_WRONG_ENTITY: (
        candidates_fk_wrong_entity
    ),
    ERROR_COMPOSITE_FK_INCOMPLETE: (
        candidates_composite_fk_incomplete
    ),
    ERROR_CARDINALITY_UNIQUENESS_CONFLICT: (
        candidates_cardinality_uniqueness
    ),
    ERROR_PARTICIPATION_OPTIONALITY_CONFLICT: (
        candidates_participation_optionality
    ),
    ERROR_IDENTIFYING_RELATIONSHIP_KEY_ERROR: (
        candidates_identifying_key_error
    ),
    ERROR_MISSING_REQUIRED_RELATIONSHIP: (
        candidates_missing_relationship
    ),
}


def eligible_error_types(
    case: dict[str, Any],
) -> list[str]:
    result = []

    for error_type in (
        ERROR_ORDER
    ):
        candidate_function = (
            CANDIDATE_FUNCTIONS[
                error_type
            ]
        )

        if candidate_function(
            case
        ):
            result.append(
                error_type
            )

    return result


def finalize_invalid_case(
    case: dict[str, Any],
    *,
    original_case_id: str,
    case_id: str,
    error_type: str,
    entity: str | None,
    attribute: str | None,
    relationship: str | None,
    details: dict[str, Any],
    seed: int,
) -> dict[str, Any]:
    case["case_id"] = case_id

    case["metadata"] = (
        copy.deepcopy(
            case["metadata"]
        )
    )

    case["metadata"][
        "parent_case_id"
    ] = original_case_id

    case["metadata"][
        "mutation"
    ] = error_type

    case["metadata"][
        "mutation_version"
    ] = MUTATION_VERSION

    case["metadata"][
        "mutation_seed"
    ] = seed

    case["metadata"][
        "mutation_source"
    ] = "controlled"

    case["metadata"][
        "error_count"
    ] = 1

    error: dict[str, Any] = {
        "error_type": (
            error_type
        ),
        "details": details,
    }

    if entity is not None:
        error["entity"] = entity

    if attribute is not None:
        error[
            "attribute"
        ] = attribute

    if relationship is not None:
        error[
            "relationship"
        ] = relationship

    case["ground_truth"] = {
        "valid": False,
        "errors": [error],
    }

    validate_case_dict(case)

    return case


def inject_fk_target_not_key(
    base_case: dict[str, Any],
    *,
    case_id: str,
    seed: int,
) -> dict[str, Any]:
    case = copy.deepcopy(
        base_case
    )

    candidate = choose_candidate(
        candidates_fk_target_not_key(
            case
        ),
        seed,
    )

    relationship = (
        candidate[
            "relationship"
        ]
    )

    child_fk = (
        candidate[
            "child_fk"
        ]
    )

    target = candidate[
        "target"
    ]

    old_reference = (
        copy.deepcopy(
            child_fk[
                "references"
            ]
        )
    )

    child_fk[
        "references"
    ] = {
        "entity": (
            relationship[
                "parent"
            ]
        ),
        "attribute": (
            target[
                "name"
            ]
        ),
    }

    return finalize_invalid_case(
        case,
        original_case_id=(
            base_case[
                "case_id"
            ]
        ),
        case_id=case_id,
        error_type=(
            ERROR_FK_TARGET_NOT_KEY
        ),
        entity=(
            relationship[
                "child"
            ]
        ),
        attribute=(
            child_fk[
                "name"
            ]
        ),
        relationship=(
            relationship[
                "name"
            ]
        ),
        details={
            "original_reference": (
                old_reference
            ),
            "mutated_reference": (
                child_fk[
                    "references"
                ]
            ),
        },
        seed=seed,
    )


def inject_fk_wrong_entity(
    base_case: dict[str, Any],
    *,
    case_id: str,
    seed: int,
) -> dict[str, Any]:
    case = copy.deepcopy(
        base_case
    )

    candidate = choose_candidate(
        candidates_fk_wrong_entity(
            case
        ),
        seed,
    )

    relationship = (
        candidate[
            "relationship"
        ]
    )

    child_fk = (
        candidate[
            "child_fk"
        ]
    )

    alternative_entity = (
        candidate[
            "alternative_entity"
        ]
    )

    alternative_key = (
        candidate[
            "alternative_key"
        ]
    )

    old_reference = (
        copy.deepcopy(
            child_fk[
                "references"
            ]
        )
    )

    child_fk[
        "references"
    ] = {
        "entity": (
            alternative_entity[
                "name"
            ]
        ),
        "attribute": (
            alternative_key[
                "name"
            ]
        ),
    }

    return finalize_invalid_case(
        case,
        original_case_id=(
            base_case[
                "case_id"
            ]
        ),
        case_id=case_id,
        error_type=(
            ERROR_FK_WRONG_ENTITY
        ),
        entity=(
            relationship[
                "child"
            ]
        ),
        attribute=(
            child_fk[
                "name"
            ]
        ),
        relationship=(
            relationship[
                "name"
            ]
        ),
        details={
            "expected_parent": (
                relationship[
                    "parent"
                ]
            ),
            "original_reference": (
                old_reference
            ),
            "mutated_reference": (
                child_fk[
                    "references"
                ]
            ),
        },
        seed=seed,
    )


def inject_composite_fk_incomplete(
    base_case: dict[str, Any],
    *,
    case_id: str,
    seed: int,
) -> dict[str, Any]:
    case = copy.deepcopy(
        base_case
    )

    candidate = choose_candidate(
        candidates_composite_fk_incomplete(
            case
        ),
        seed,
    )

    relationship = (
        candidate[
            "relationship"
        ]
    )

    child_fks = (
        candidate[
            "child_fks"
        ]
    )

    rng = random.Random(
        seed
    )

    removed_component = (
        rng.choice(
            child_fks
        )
    )

    removed_reference = (
        copy.deepcopy(
            removed_component[
                "references"
            ]
        )
    )

    removed_component[
        "foreign_key"
    ] = False

    removed_component.pop(
        "references",
        None,
    )

    return finalize_invalid_case(
        case,
        original_case_id=(
            base_case[
                "case_id"
            ]
        ),
        case_id=case_id,
        error_type=(
            ERROR_COMPOSITE_FK_INCOMPLETE
        ),
        entity=(
            relationship[
                "child"
            ]
        ),
        attribute=(
            removed_component[
                "name"
            ]
        ),
        relationship=(
            relationship[
                "name"
            ]
        ),
        details={
            "removed_component": (
                removed_component[
                    "name"
                ]
            ),
            "removed_reference": (
                removed_reference
            ),
        },
        seed=seed,
    )


def inject_cardinality_uniqueness_conflict(
    base_case: dict[str, Any],
    *,
    case_id: str,
    seed: int,
) -> dict[str, Any]:
    case = copy.deepcopy(
        base_case
    )

    candidate = choose_candidate(
        candidates_cardinality_uniqueness(
            case
        ),
        seed,
    )

    relationship = (
        candidate[
            "relationship"
        ]
    )

    child_fk = (
        candidate[
            "child_fk"
        ]
    )

    child_fk[
        "unique"
    ] = False

    return finalize_invalid_case(
        case,
        original_case_id=(
            base_case[
                "case_id"
            ]
        ),
        case_id=case_id,
        error_type=(
            ERROR_CARDINALITY_UNIQUENESS_CONFLICT
        ),
        entity=(
            relationship[
                "child"
            ]
        ),
        attribute=(
            child_fk[
                "name"
            ]
        ),
        relationship=(
            relationship[
                "name"
            ]
        ),
        details={
            "declared_child_cardinality": (
                relationship[
                    "child_cardinality"
                ]
            ),
            "foreign_key_unique": (
                False
            ),
        },
        seed=seed,
    )


def inject_participation_optionality_conflict(
    base_case: dict[str, Any],
    *,
    case_id: str,
    seed: int,
) -> dict[str, Any]:
    case = copy.deepcopy(
        base_case
    )

    candidate = choose_candidate(
        candidates_participation_optionality(
            case
        ),
        seed,
    )

    relationship = (
        candidate[
            "relationship"
        ]
    )

    rng = random.Random(
        seed
    )

    child_fk = rng.choice(
        candidate[
            "eligible_fks"
        ]
    )

    child_fk[
        "nullable"
    ] = True

    return finalize_invalid_case(
        case,
        original_case_id=(
            base_case[
                "case_id"
            ]
        ),
        case_id=case_id,
        error_type=(
            ERROR_PARTICIPATION_OPTIONALITY_CONFLICT
        ),
        entity=(
            relationship[
                "child"
            ]
        ),
        attribute=(
            child_fk[
                "name"
            ]
        ),
        relationship=(
            relationship[
                "name"
            ]
        ),
        details={
            "required_parent_cardinality": (
                relationship[
                    "parent_cardinality"
                ]
            ),
            "mutated_nullable": (
                True
            ),
        },
        seed=seed,
    )


def inject_identifying_relationship_key_error(
    base_case: dict[str, Any],
    *,
    case_id: str,
    seed: int,
) -> dict[str, Any]:
    case = copy.deepcopy(
        base_case
    )

    candidate = choose_candidate(
        candidates_identifying_key_error(
            case
        ),
        seed,
    )

    relationship = (
        candidate[
            "relationship"
        ]
    )

    rng = random.Random(
        seed
    )

    child_fk = rng.choice(
        candidate[
            "primary_fks"
        ]
    )

    child_fk[
        "primary_key"
    ] = False

    return finalize_invalid_case(
        case,
        original_case_id=(
            base_case[
                "case_id"
            ]
        ),
        case_id=case_id,
        error_type=(
            ERROR_IDENTIFYING_RELATIONSHIP_KEY_ERROR
        ),
        entity=(
            relationship[
                "child"
            ]
        ),
        attribute=(
            child_fk[
                "name"
            ]
        ),
        relationship=(
            relationship[
                "name"
            ]
        ),
        details={
            "parent_entity": (
                relationship[
                    "parent"
                ]
            ),
            "removed_child_key_component": (
                child_fk[
                    "name"
                ]
            ),
        },
        seed=seed,
    )


def inject_missing_required_relationship(
    base_case: dict[str, Any],
    *,
    case_id: str,
    seed: int,
) -> dict[str, Any]:
    case = copy.deepcopy(
        base_case
    )

    candidate = choose_candidate(
        candidates_missing_relationship(
            case
        ),
        seed,
    )

    relationship = (
        candidate[
            "relationship"
        ]
    )

    relationship_name = (
        relationship[
            "name"
        ]
    )

    removed_foreign_keys = []

    for child_fk in (
        candidate[
            "child_fks"
        ]
    ):
        removed_foreign_keys.append(
            child_fk[
                "name"
            ]
        )

        child_fk[
            "foreign_key"
        ] = False

        child_fk.pop(
            "references",
            None,
        )

    case[
        "relationships"
    ] = [
        existing
        for existing
        in case[
            "relationships"
        ]
        if (
            existing[
                "name"
            ]
            != relationship_name
        )
    ]

    return finalize_invalid_case(
        case,
        original_case_id=(
            base_case[
                "case_id"
            ]
        ),
        case_id=case_id,
        error_type=(
            ERROR_MISSING_REQUIRED_RELATIONSHIP
        ),
        entity=(
            relationship[
                "child"
            ]
        ),
        attribute=(
            removed_foreign_keys[
                0
            ]
            if removed_foreign_keys
            else None
        ),
        relationship=(
            relationship_name
        ),
        details={
            "required_parent": (
                relationship[
                    "parent"
                ]
            ),
            "required_child": (
                relationship[
                    "child"
                ]
            ),
            "removed_foreign_keys": (
                removed_foreign_keys
            ),
        },
        seed=seed,
    )


INJECTORS = {
    ERROR_FK_TARGET_NOT_KEY: (
        inject_fk_target_not_key
    ),
    ERROR_FK_WRONG_ENTITY: (
        inject_fk_wrong_entity
    ),
    ERROR_COMPOSITE_FK_INCOMPLETE: (
        inject_composite_fk_incomplete
    ),
    ERROR_CARDINALITY_UNIQUENESS_CONFLICT: (
        inject_cardinality_uniqueness_conflict
    ),
    ERROR_PARTICIPATION_OPTIONALITY_CONFLICT: (
        inject_participation_optionality_conflict
    ),
    ERROR_IDENTIFYING_RELATIONSHIP_KEY_ERROR: (
        inject_identifying_relationship_key_error
    ),
    ERROR_MISSING_REQUIRED_RELATIONSHIP: (
        inject_missing_required_relationship
    ),
}


def inject_error(
    base_case: dict[str, Any],
    error_type: str,
    *,
    case_id: str,
    seed: int,
) -> dict[str, Any]:
    validate_case_dict(
        base_case
    )

    if not base_case[
        "ground_truth"
    ]["valid"]:
        raise ValueError(
            "Controlled mutation "
            "requires a valid "
            "reference case."
        )

    if (
        error_type
        not in INJECTORS
    ):
        raise ValueError(
            f"Unsupported error type: "
            f"{error_type}"
        )

    if (
        error_type
        not in eligible_error_types(
            base_case
        )
    ):
        raise ValueError(
            f"{base_case['case_id']} "
            f"is not eligible for "
            f"{error_type}."
        )

    return INJECTORS[
        error_type
    ](
        base_case,
        case_id=case_id,
        seed=seed,
    )