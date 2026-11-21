# Automated ER Diagram Validator

Automated detection of non-trivial integrity and relationship errors in **Information Engineering / Crow's-Foot ER designs**, comparing deterministic rule-based validation, formal constraint solving, and LLM-based validation on a benchmark derived from real-world relational schemas.

## Project Overview

This repository contains the CSCE 811 Data Modeling final project:

**Automated Detection of Non-Trivial Integrity and Relationship Errors in ER Diagrams: A Comparison of Rule-Based, Constraint-Solver, and LLM-Based Validation**

All three methods solve the same task:

> Given a normalized ER design and its relationship requirements, determine whether the design is logically valid and identify any errors using the project's shared taxonomy.

Methods:

1. **Deterministic Rule-Based Validator**
2. **Constraint-Solver Validator using Z3**
3. **LLM-Based Validator**

All methods use the same benchmark, normalized input representation, seven-class taxonomy, prediction schema, held-out test set, and evaluation pipeline.

## Real-World Data Source

The benchmark is derived from **SchemaPile-Perm v0.2**, the permissively licensed subset of SchemaPile.

SchemaPile paper:

> Till Döhmen, Radu Geacu, Madelon Hulsebos, and Sebastian Schelter. 2024. **SchemaPile: A Large Collection of Relational Database Schemas.** *Proceedings of the ACM on Management of Data*, 2(3), Article 172. https://doi.org/10.1145/3654975

Dataset:

- Project: https://schemapile.github.io/
- Zenodo: https://doi.org/10.5281/zenodo.12682521
- SchemaPile-Perm schemas: **22,989**
- SchemaPile-Perm tables: approximately **199K**

This project uses SchemaPile-Perm as a real-world data source; it does **not** replicate the original SchemaPile experiments.

## Benchmark Construction

```text
SchemaPile-Perm
      ↓
download
      ↓
conservative filtering
      ↓
normalize into ERCase
      ↓
eligibility audit for E01–E07
      ↓
controlled single-error mutation
      ↓
repository-grouped split
      ↓
final benchmark
```

Production import:

```text
Raw schemas screened:       22,989
Accepted reference cases:    7,366
Distinct repositories:       5,897
Rejected schemas:           15,623
```

A reference case means the schema is representable and internally consistent under this project's selected constraints. It is not a claim that every accepted real-world schema is universally optimal.

## Final Benchmark

```text
1,400 total cases
700 valid reference cases
700 controlled invalid cases
7 error classes
100 invalid cases per error class
```

| Split | Valid | Invalid | Total |
|---|---:|---:|---:|
| Train | 490 | 490 | 980 |
| Dev | 105 | 105 | 210 |
| Test | 105 | 105 | 210 |
| **Total** | **700** | **700** | **1,400** |

Each error class contributes 70 train, 15 dev, and 15 test invalid cases.

## Repository-Grouped Split

A deterministic **70/15/15 repository-grouped split** is used.

All schemas from the same GitHub repository stay in one split, and the same SchemaPile source schema is never reused across final benchmark cases.

## Error Taxonomy

1. `FK_TARGET_NOT_KEY`
2. `FK_WRONG_ENTITY`
3. `COMPOSITE_FK_INCOMPLETE`
4. `CARDINALITY_UNIQUENESS_CONFLICT`
5. `PARTICIPATION_OPTIONALITY_CONFLICT`
6. `IDENTIFYING_RELATIONSHIP_KEY_ERROR`
7. `MISSING_REQUIRED_RELATIONSHIP`

Definitions: `docs/error_taxonomy.md`

## Eligibility Audit

| Error Type | Eligible Cases |
|---|---:|
| `FK_TARGET_NOT_KEY` | 4,476 |
| `FK_WRONG_ENTITY` | 5,681 |
| `COMPOSITE_FK_INCOMPLETE` | 394 |
| `CARDINALITY_UNIQUENESS_CONFLICT` | 966 |
| `PARTICIPATION_OPTIONALITY_CONFLICT` | 7,282 |
| `IDENTIFYING_RELATIONSHIP_KEY_ERROR` | 2,164 |
| `MISSING_REQUIRED_RELATIONSHIP` | 7,366 |

Generated report:

```text
data/audits/eligibility_report.json
```

## Why Controlled Mutations?

SchemaPile provides real-world schemas but does not label them with this project's seven ER error classes.

To obtain exact evaluation ground truth, the project:

1. starts from an eligible reference-consistent real-world schema;
2. applies one controlled structural mutation;
3. records the intended violation for evaluation.

Current benchmark v2.0 uses single-error invalid cases only.

## Repository Structure

```text
automated-er-diagram-validator-schemapile/
│
├── README.md
├── requirements.txt
├── .gitignore
├── .env.example
├── config.yaml
├── pytest.ini
│
├── docs/
│   ├── project_scope.md
│   ├── data_format.md
│   ├── error_taxonomy.md
│   └── method_interface.md
│
├── schemas/
│   ├── er_case.schema.json
│   └── prediction.schema.json
│
├── data/
│   ├── raw/
│   ├── processed/
│   ├── audits/
│   │   ├── import_report.json
│   │   └── eligibility_report.json
│   ├── toy/
│   │   ├── valid_example.json
│   │   └── invalid_example.json
│   ├── train.jsonl
│   ├── dev.jsonl
│   ├── test.jsonl
│   └── dataset_manifest.json
│
├── diagrams/
│   ├── plantuml/
│   └── png/
│
├── src/
│   ├── core/
│   │   ├── models.py
│   │   ├── io.py
│   │   ├── validator_interface.py
│   │   └── constants.py
│   ├── data/
│   │   ├── download_schemapile.py
│   │   ├── import_schemapile.py
│   │   ├── eligibility_report.py
│   │   ├── inject_errors.py
│   │   ├── build_dataset.py
│   │   └── render_plantuml.py
│   ├── methods/
│   │   ├── rule_based/
│   │   │   └── validator.py
│   │   ├── constraint_solver/
│   │   │   └── validator.py
│   │   └── llm_based/
│   │       ├── validator.py
│   │       └── prompt.txt
│   └── evaluation/
│       ├── metrics.py
│       ├── evaluate.py
│       └── compare_methods.py
│
├── tests/
├── outputs/
├── results/
└── report/
    └── notes/
```

## Installation

```powershell
python -m pip install -r requirements.txt
```

Main dependencies include `jsonschema`, `pytest`, `networkx`, `z3-solver`, `openai`, `numpy`, `pandas`, `scikit-learn`, `matplotlib`, `PyYAML`, and `python-dotenv`.

## Reproduce the Data Pipeline

### 1. Download SchemaPile-Perm

```powershell
python -m src.data.download_schemapile
```

The script downloads the published `schemapile-perm.json.gz` release and verifies its MD5 checksum.

### 2. Import and Normalize

```powershell
python -m src.data.import_schemapile
```

Outputs include:

```text
data/processed/reference_cases.jsonl
data/audits/import_report.json
```

### 3. Eligibility Audit

```powershell
python -m src.data.eligibility_report
```

Output:

```text
data/audits/eligibility_report.json
```

### 4. Build Benchmark

```powershell
python -m src.data.build_dataset --per-error auto
```

Production result:

```text
Selected 100 cases per error type.
Train: 980
Dev:   210
Test:  210
Total: 1,400
```

## Tests

Run:

```powershell
pytest -v
```

Current shared benchmark/core status:

```text
47 passed
```

The suite covers schema validation, I/O, shared validator behavior, SchemaPile import/normalization, controlled mutation, benchmark balance, repository isolation, source-schema non-reuse, and final dataset schema validity.

## Shared Architecture

### `src/core/models.py`

Defines shared ER and prediction data models.

### `src/core/io.py`

Handles JSON/JSONL I/O, schema validation, dataclass conversion, prediction I/O, and method-input preparation.

### `src/core/validator_interface.py`

Defines the shared `BaseValidator`.

### `src/core/constants.py`

Defines common method names, error labels, cardinalities, and constants.

## Leakage Prevention

Validators must not receive or use:

- `ground_truth`;
- mutation labels;
- mutation seeds;
- `error_count`;
- answer-bearing case IDs;
- source provenance as an answer shortcut.

Final method-facing case IDs should be opaque with respect to validity and error class.

## Rule-Based Validator

```text
src/methods/rule_based/validator.py
outputs/rule_based/predictions.jsonl
tests/test_rule_based.py
```

Method name:

```text
rule_based
```

## Constraint-Solver Validator

```text
src/methods/constraint_solver/validator.py
outputs/constraint_solver/predictions.jsonl
tests/test_solver.py
```

Method name:

```text
constraint_solver
```

## LLM-Based Validator

```text
src/methods/llm_based/validator.py
src/methods/llm_based/prompt.txt
outputs/llm_based/predictions.jsonl
tests/test_llm.py
```

Method name:

```text
llm_based
```

The LLM must use the same leakage-free candidate information and the same seven labels as the other methods.

## Common Prediction Format

```json
{
  "case_id": "CASE_A19F03D28B11",
  "method": "rule_based",
  "predicted_valid": false,
  "errors": [
    {
      "error_type": "FK_TARGET_NOT_KEY",
      "entity": "orders",
      "attribute": "user_id",
      "relationship": "fk_001_orders_to_users",
      "message": "Foreign key references an attribute that is not a key."
    }
  ],
  "runtime_ms": 2.4
}
```

Full schema:

```text
schemas/prediction.schema.json
```

## Evaluation

Shared evaluation code:

```text
src/evaluation/
```

Planned metrics include:

- validity accuracy;
- precision;
- recall;
- F1;
- macro-F1;
- per-error metrics;
- exact error-set accuracy;
- localization accuracy;
- false-positive rate;
- runtime.

Raw predictions go under `outputs/`. Aggregated results and figures go under `results/`.

## API Keys

Do not commit API keys.

Create `.env` locally from `.env.example` and set:

```text
OPENAI_API_KEY=your_key_here
```

## Collaboration

Before changes:

```powershell
git pull
```

Before merging:

```powershell
pytest -v
```

Do not modify shared benchmark construction, schemas, taxonomy, or core interfaces without team agreement.

## Documentation

```text
docs/project_scope.md
docs/data_format.md
docs/error_taxonomy.md
docs/method_interface.md
```

## Project Principle

All three methods must solve the **same validation problem on the same held-out real-world-derived benchmark** using the same taxonomy, output contract, leakage controls, and evaluation definitions.

## Citation

```text
Döhmen, T., Geacu, R., Hulsebos, M., & Schelter, S. (2024).
SchemaPile: A Large Collection of Relational Database Schemas.
Proceedings of the ACM on Management of Data, 2(3), Article 172.
https://doi.org/10.1145/3654975
```

SchemaPile-Perm:

```text
https://doi.org/10.5281/zenodo.12682521
```
