from __future__ import annotations

import argparse
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from src.core.io import (
    load_jsonl,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]

PLANTUML_DIR = (
    PROJECT_ROOT
    / "diagrams"
    / "plantuml"
)

PNG_DIR = (
    PROJECT_ROOT
    / "diagrams"
    / "png"
)


CARDINALITY_SYMBOLS = {
    "1": "||",
    "0..1": "o|",
    "0..*": "o{",
    "1..*": "|{",
}


def safe_alias(
    name: str,
    index: int,
) -> str:
    cleaned = re.sub(
        r"[^A-Za-z0-9_]",
        "_",
        name,
    )

    return (
        f"E{index}_{cleaned}"
    )


def case_to_plantuml(
    case: dict[str, Any],
) -> str:
    lines = [
        "@startuml",
        "hide circle",
        "hide methods",
        "skinparam linetype ortho",
        "",
    ]

    aliases = {}

    for index, entity in enumerate(
        case["entities"],
        start=1,
    ):
        alias = safe_alias(
            entity["name"],
            index,
        )

        aliases[
            entity["name"]
        ] = alias

        lines.append(
            f'entity "{entity["name"]}" '
            f"as {alias} {{"
        )

        primary = [
            attribute
            for attribute
            in entity[
                "attributes"
            ]
            if attribute.get(
                "primary_key",
                False,
            )
        ]

        nonprimary = [
            attribute
            for attribute
            in entity[
                "attributes"
            ]
            if not attribute.get(
                "primary_key",
                False,
            )
        ]

        for attribute in primary:
            markers = ["PK"]

            if attribute.get(
                "foreign_key",
                False,
            ):
                markers.append(
                    "FK"
                )

            marker_text = (
                ", ".join(
                    markers
                )
            )

            lines.append(
                f'  * {attribute["name"]} '
                f': {attribute["type"]} '
                f'<<{marker_text}>>'
            )

        if (
            primary
            and nonprimary
        ):
            lines.append(
                "  --"
            )

        for attribute in (
            nonprimary
        ):
            markers = []

            if attribute.get(
                "foreign_key",
                False,
            ):
                markers.append(
                    "FK"
                )

            if attribute.get(
                "unique",
                False,
            ):
                markers.append(
                    "UQ"
                )

            if attribute.get(
                "nullable",
                False,
            ):
                markers.append(
                    "NULL"
                )

            marker_text = (
                f' <<{", ".join(markers)}>>'
                if markers
                else ""
            )

            lines.append(
                f'  {attribute["name"]} '
                f': {attribute["type"]}'
                f"{marker_text}"
            )

        lines.append(
            "}"
        )

        lines.append(
            ""
        )

    for relationship in case[
        "relationships"
    ]:
        parent = aliases[
            relationship[
                "parent"
            ]
        ]

        child = aliases[
            relationship[
                "child"
            ]
        ]

        parent_symbol = (
            CARDINALITY_SYMBOLS[
                relationship[
                    "parent_cardinality"
                ]
            ]
        )

        child_symbol = (
            CARDINALITY_SYMBOLS[
                relationship[
                    "child_cardinality"
                ]
            ]
        )

        relationship_label = (
            relationship[
                "name"
            ]
        )

        identifying = (
            relationship.get(
                "identifying",
                False,
            )
        )

        label = (
            f"{relationship_label} "
            f"[identifying]"
            if identifying
            else relationship_label
        )

        lines.append(
            f"{parent} "
            f"{parent_symbol}--"
            f"{child_symbol} "
            f"{child} "
            f': "{label}"'
        )

    lines.extend(
        [
            "",
            "@enduml",
        ]
    )

    return "\n".join(
        lines
    )


def write_plantuml_files(
    cases: list[dict[str, Any]],
    limit: int | None = None,
) -> list[Path]:
    PLANTUML_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    selected = (
        cases
        if limit is None
        else cases[:limit]
    )

    paths = []

    for case in selected:
        path = (
            PLANTUML_DIR
            / (
                f"{case['case_id']}"
                ".puml"
            )
        )

        path.write_text(
            case_to_plantuml(
                case
            ),
            encoding="utf-8",
        )

        paths.append(
            path
        )

    return paths


def render_pngs(
    paths: list[Path],
) -> None:
    plantuml = shutil.which(
        "plantuml"
    )

    if plantuml is None:
        print(
            "PlantUML executable "
            "was not found. "
            "PUML files were created, "
            "but PNG rendering was skipped."
        )

        return

    PNG_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    for path in paths:
        subprocess.run(
            [
                plantuml,
                "-tpng",
                "-o",
                str(
                    PNG_DIR.resolve()
                ),
                str(
                    path.resolve()
                ),
            ],
            check=True,
        )


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--input",
        default=(
            "data/test.jsonl"
        ),
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=20,
    )

    parser.add_argument(
        "--render-png",
        action="store_true",
    )

    args = parser.parse_args()

    input_path = (
        PROJECT_ROOT
        / args.input
    )

    cases = load_jsonl(
        input_path
    )

    paths = (
        write_plantuml_files(
            cases,
            limit=args.limit,
        )
    )

    print(
        f"Created "
        f"{len(paths)} "
        "PlantUML files."
    )

    if args.render_png:
        render_pngs(
            paths
        )


if __name__ == "__main__":
    main()