# Validator Method Interface

## 1. Purpose

This document defines the software contract followed by all three ER validation methods.

The three methods may use different internal algorithms, but they must receive equivalent normalized input and return the same prediction format.

Supported method names:

```text
rule_based
constraint_solver
llm_based
```

## 2. Shared Validation Task

For each normalized ER case, a validator determines:

1. whether the candidate design is valid under the seven-error taxonomy; and
2. which error label(s) are present when invalid.

All methods are evaluated on the same SchemaPile-derived benchmark.

## 3. Common Base Class

Every validator must inherit from:

```python
from src.core.validator_interface import BaseValidator
```

Conceptually:

```python
from src.core.models import Prediction
from src.core.validator_interface import BaseValidator


class MyValidator(BaseValidator):
    method_name = "rule_based"

    def _validate_case(self, case: dict) -> Prediction:
        ...
```

The public call is:

```python
prediction = validator.validate(case)
```

`BaseValidator` centralizes shared input/output checks, runtime measurement, prediction consistency, and batch behavior.

## 4. Standard Input

A validator may reason from:

- opaque case ID;
- domain;
- entities;
- attributes;
- data types;
- primary-key membership;
- foreign-key membership;
- reference targets;
- uniqueness;
- nullability;
- relationships;
- cardinalities;
- identifying-relationship flags;
- requirements.

The normalized format is defined in:

```text
docs/data_format.md
```

## 5. Prohibited Input

A validator must not receive or use the gold answer.

Before prediction, method-facing input must remove:

```text
ground_truth
mutation
mutation_version
mutation_seed
mutation_source
error_count
```

and any equivalent answer-bearing field.

Case IDs must not encode:

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

The same sanitization policy applies to all methods.

## 6. Provenance Is Not a Prediction Feature

SchemaPile provenance is retained for reproducibility and split construction, not as evidence for validity.

Validators must not use source repository, source URL, source SchemaPile ID, license, or parent-case ID to infer the answer.

## 7. Standard Output

Predictions must conform to:

```text
schemas/prediction.schema.json
```

Example:

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

For a valid prediction:

```json
{
  "case_id": "CASE_41CF74F318A2",
  "method": "constraint_solver",
  "predicted_valid": true,
  "errors": [],
  "runtime_ms": 8.2
}
```

If `predicted_valid` is `true`, `errors` must be empty.

If `predicted_valid` is `false`, at least one error must be returned.

## 8. Allowed Error Labels

```text
FK_TARGET_NOT_KEY
FK_WRONG_ENTITY
COMPOSITE_FK_INCOMPLETE
CARDINALITY_UNIQUENESS_CONFLICT
PARTICIPATION_OPTIONALITY_CONFLICT
IDENTIFYING_RELATIONSHIP_KEY_ERROR
MISSING_REQUIRED_RELATIONSHIP
```

Definitions are in:

```text
docs/error_taxonomy.md
```

## 9. Dataset Usage

Production benchmark:

```text
data/train.jsonl
data/dev.jsonl
data/test.jsonl
```

Current split:

```text
Train: 980
Dev:   210
Test:  210
Total: 1,400
```

The test split is held out for final comparison.

Development and tuning should use train/dev only.

## 10. Repository-Grouped Test Design

Schemas from the same source GitHub repository cannot appear in multiple splits.

Methods must not circumvent the split by retrieving original source records from the web during test prediction.

## 11. Command-Line Interface

Rule-based:

```bash
python -m src.methods.rule_based.validator --input data/test.jsonl --output outputs/rule_based/predictions.jsonl
```

Constraint solver:

```bash
python -m src.methods.constraint_solver.validator --input data/test.jsonl --output outputs/constraint_solver/predictions.jsonl
```

LLM:

```bash
python -m src.methods.llm_based.validator --input data/test.jsonl --output outputs/llm_based/predictions.jsonl
```

## 12. Batch Processing

Each method should:

1. load the requested JSONL file;
2. apply shared leakage-safe input preparation;
3. validate each case independently;
4. preserve the opaque case ID;
5. measure runtime;
6. produce one prediction per input case;
7. write predictions as JSONL.

## 13. Rule-Based Method

Location:

```text
src/methods/rule_based/validator.py
```

Method name:

```text
rule_based
```

The implementation may use deterministic rules, NetworkX, graph traversal, key/FK checks, relationship/requirement checks, cardinality/uniqueness checks, nullability checks, and identifying-key checks.

Output:

```text
outputs/rule_based/predictions.jsonl
```

Tests:

```text
tests/test_rule_based.py
```

## 14. Constraint-Solver Method

Location:

```text
src/methods/constraint_solver/validator.py
```

Method name:

```text
constraint_solver
```

The implementation may use Python, Z3, Boolean constraints, cardinality constraints, key/FK constraints, and satisfiability checking.

Output:

```text
outputs/constraint_solver/predictions.jsonl
```

Tests:

```text
tests/test_solver.py
```

## 15. LLM-Based Method

Location:

```text
src/methods/llm_based/validator.py
```

Prompt:

```text
src/methods/llm_based/prompt.txt
```

Method name:

```text
llm_based
```

The LLM must receive the same leakage-free candidate information as the other methods.

The prompt should define the seven labels, request structured output, prohibit unsupported labels, and avoid all gold labels/mutation metadata.

Model name, prompt version, decoding settings, retries, and structured-output strategy should be documented.

Output:

```text
outputs/llm_based/predictions.jsonl
```

Tests:

```text
tests/test_llm.py
```

## 16. Shared Evaluation

Individual validators do not calculate their own final comparison metrics.

Shared evaluation belongs under:

```text
src/evaluation/
```

including:

```text
src/evaluation/metrics.py
src/evaluation/evaluate.py
src/evaluation/compare_methods.py
```

## 17. Output Directories

```text
outputs/
├── rule_based/
├── constraint_solver/
└── llm_based/
```

A method must not overwrite another method's predictions.

## 18. Reproducibility

Where randomness exists:

- document the seed;
- expose it as a parameter where practical;
- record relevant configuration;
- preserve case IDs;
- preserve prompt/model versions.

## 19. Current Shared-Test Status

At the current SchemaPile benchmark milestone:

```text
pytest -v
```

passes **47 tests**.

Method-specific tests may increase the total as the validators are completed.
