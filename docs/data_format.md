# ER Case Data Format

## 1. Purpose

This document defines the common normalized ER representation used by all three validation methods.

The source data comes from **SchemaPile-Perm**, but validators do not operate directly on SchemaPile's raw JSON. Eligible schemas are converted into the project's shared ERCase representation.

The canonical benchmark format is **JSON Lines (`.jsonl`)**, with one ER validation case per line.

## 2. Data Flow

```text
SchemaPile-Perm v0.2
        ↓
data/raw/schemapile-perm.json.gz
        ↓
src/data/import_schemapile.py
        ↓
filter + normalize
        ↓
data/processed/reference_cases.jsonl
        ↓
src/data/eligibility_report.py
        ↓
controlled mutation eligibility audit
        ↓
src/data/build_dataset.py
        ↓
train.jsonl / dev.jsonl / test.jsonl
```

The final benchmark files are:

```text
data/
├── train.jsonl
├── dev.jsonl
├── test.jsonl
├── dataset_manifest.json
├── audits/
│   ├── import_report.json
│   └── eligibility_report.json
└── toy/
    ├── valid_example.json
    └── invalid_example.json
```

The raw and processed source pools are reproducible and may remain excluded from Git.

## 3. Production Benchmark Size

| Split | Valid | Invalid | Total |
|---|---:|---:|---:|
| Train | 490 | 490 | 980 |
| Dev | 105 | 105 | 210 |
| Test | 105 | 105 | 210 |
| **Total** | **700** | **700** | **1,400** |

There are **100 invalid cases per error category**.

## 4. Case Structure

Each stored benchmark case contains:

```text
case_id
domain
description
entities
relationships
requirements
metadata
ground_truth
```

`ground_truth` is used only for construction, auditing, and evaluation.

Answer-bearing metadata is also construction/evaluation information and must not be exposed to validators.

## 5. Case IDs

`case_id` uniquely associates an input case with its prediction.

Final method-facing IDs should be **opaque with respect to validity and error type**.

Do not encode:

```text
VALID
INVALID
E01
E02
E03
E04
E05
E06
E07
```

inside IDs used by validators.

## 6. Domain

Because the project does not infer a reliable semantic domain for every SchemaPile source, normalized records use:

```json
"domain": "real_world"
```

Repository provenance is stored separately for audit and split construction.

## 7. Simplified Normalized Example

```json
{
  "case_id": "CASE_A19F03D28B11",
  "domain": "real_world",
  "description": "Real-world relational schema normalized from SchemaPile-Perm.",
  "entities": [
    {
      "name": "users",
      "attributes": [
        {
          "name": "id",
          "type": "Integer",
          "primary_key": true,
          "foreign_key": false,
          "nullable": false,
          "unique": true
        }
      ]
    },
    {
      "name": "orders",
      "attributes": [
        {
          "name": "id",
          "type": "Integer",
          "primary_key": true,
          "foreign_key": false,
          "nullable": false,
          "unique": true
        },
        {
          "name": "user_id",
          "type": "Integer",
          "primary_key": false,
          "foreign_key": true,
          "nullable": false,
          "unique": false,
          "references": {
            "entity": "users",
            "attribute": "id"
          }
        }
      ]
    }
  ],
  "relationships": [
    {
      "name": "fk_001_orders_to_users",
      "parent": "users",
      "child": "orders",
      "parent_cardinality": "1",
      "child_cardinality": "0..*",
      "identifying": false
    }
  ],
  "requirements": [
    {
      "requirement_id": "R1",
      "text": "Each orders row must reference exactly one users row for this foreign-key relationship.",
      "type": "relationship_cardinality",
      "source": "orders",
      "target": "users",
      "source_min": 1,
      "source_max": 1,
      "target_min": 0,
      "target_max": "*"
    }
  ],
  "metadata": {
    "source": "real_world",
    "difficulty": "easy",
    "version": 1,
    "source_dataset": "SchemaPile-Perm",
    "benchmark_version": "2.0"
  },
  "ground_truth": {
    "valid": true,
    "errors": []
  }
}
```

This example illustrates the normalized shape; production cases may contain more entities, attributes, relationships, and provenance metadata.

## 8. Entity Representation

Each entity contains:

```json
{
  "name": "orders",
  "attributes": []
}
```

Each attribute contains:

- `name`
- `type`
- `primary_key`
- `foreign_key`
- `nullable`
- `unique`

A foreign-key attribute also contains:

```json
"references": {
  "entity": "users",
  "attribute": "id"
}
```

## 9. Composite Primary Keys

Composite PKs are represented by setting:

```json
"primary_key": true
```

on every participating attribute.

## 10. Foreign Keys

Every FK component contains an explicit reference target.

For composite foreign keys, each local component maps to the corresponding referenced component.

The importer preserves SchemaPile's multi-column FK structure.

## 11. Relationship Representation

Each relationship contains:

```json
{
  "name": "fk_001_orders_to_users",
  "parent": "users",
  "child": "orders",
  "parent_cardinality": "1",
  "child_cardinality": "0..*",
  "identifying": false
}
```

Supported cardinalities:

```text
0..1
1
0..*
1..*
```

## 12. Cardinality Derivation

SchemaPile does not directly store Crow's-Foot notation, so the project derives cardinalities deterministically.

### Child-to-parent participation

If all FK components are non-null:

```text
parent_cardinality = "1"
```

If any FK component is nullable:

```text
parent_cardinality = "0..1"
```

### Parent-to-child multiplicity

If the FK is represented as unique:

```text
child_cardinality = "0..1"
```

Otherwise:

```text
child_cardinality = "0..*"
```

The project does not infer that every parent must have at least one child from an FK alone.

## 13. Identifying Relationships

A relationship is marked:

```json
"identifying": true
```

when all local FK components also participate in the child's primary key.

Otherwise it is `false`.

## 14. Requirements

Requirements preserve expected relationship semantics independently of the candidate design.

Example:

```json
{
  "requirement_id": "R1",
  "text": "Each orders row must reference exactly one users row for this foreign-key relationship.",
  "type": "relationship_cardinality",
  "source": "orders",
  "target": "users",
  "source_min": 1,
  "source_max": 1,
  "target_min": 0,
  "target_max": "*"
}
```

Natural-language text supports the LLM and human interpretation.

Machine-readable fields support deterministic and constraint-solver validation.

During controlled mutation, requirements remain unchanged so the intended design can be compared with the mutated candidate structure.

## 15. Ground Truth

Valid case:

```json
{
  "valid": true,
  "errors": []
}
```

Invalid benchmark v2.0 case:

```json
{
  "valid": false,
  "errors": [
    {
      "error_type": "FK_TARGET_NOT_KEY",
      "entity": "orders",
      "attribute": "user_id",
      "relationship": "fk_001_orders_to_users",
      "details": {}
    }
  ]
}
```

Allowed labels are defined in `docs/error_taxonomy.md`.

## 16. Single-Error Benchmark Policy

The current benchmark contains:

- 700 valid cases;
- 700 controlled single-error invalid cases;
- no multi-error production cases.

This supports clean per-error evaluation.

## 17. Stored Metadata

Stored benchmark records may contain audit/provenance fields such as:

```text
source
difficulty
version
source_dataset
source_schema_id
source_url
source_repository
license
import_version
reference_status
table_count
column_count
foreign_key_count
composite_foreign_key_count
benchmark_version
split
```

Controlled invalid records may additionally contain:

```text
parent_case_id
mutation
mutation_version
mutation_seed
mutation_source
error_count
```

These construction fields are useful for reproducibility but are **not prediction features**.

## 18. Method-Facing Sanitization

Before a case is passed to a validator:

1. remove `ground_truth`;
2. remove answer-bearing mutation metadata;
3. use a case ID that does not encode validity or error type;
4. prevent other direct benchmark-answer leakage.

At minimum, these fields must never reach a validator:

```text
mutation
mutation_version
mutation_seed
mutation_source
error_count
```

The same policy applies to all three methods.

## 19. Repository-Grouped Splitting

A deterministic hash assigns source repositories to train/dev/test.

All schemas from the same GitHub repository remain in one split.

The final benchmark also prevents reuse of the same SchemaPile source schema.

## 20. Reference Pool

The production import produced:

```text
22,989 raw schemas screened
7,366 accepted reference cases
5,897 distinct accepted source repositories
15,623 rejected schemas
```

The 1,400-case benchmark is selected from the accepted pool under eligibility, balance, split, and non-reuse constraints.

## 21. PlantUML and PNG

PlantUML and PNG may be generated for:

- visual inspection;
- report/poster figures;
- human review;
- demonstrations.

The authoritative evaluation representation is normalized JSON/JSONL.

## 22. Validation Schemas

Cases:

```text
schemas/er_case.schema.json
```

Predictions:

```text
schemas/prediction.schema.json
```

At the current SchemaPile benchmark milestone, the shared suite passes **47 tests**.
