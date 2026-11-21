# Automated ER Diagram Validation — Project Scope

## 1. Project Title

**Automated Detection of Non-Trivial Integrity and Relationship Errors in ER Diagrams: A Comparison of Rule-Based, Constraint-Solver, and LLM-Based Validation**

## 2. Project Focus

This project develops and evaluates automated methods for determining whether an Information Engineering / Crow's-Foot Entity-Relationship (ER) design satisfies predefined logical rules and integrity constraints.

The project focuses on logical schema and relationship errors rather than cosmetic layout or drawing syntax.

The benchmark is derived from **real-world relational schemas in SchemaPile-Perm**, the permissively licensed subset of the SchemaPile corpus introduced by Döhmen et al. (SIGMOD 2024 / Proceedings of the ACM on Management of Data).

This project uses SchemaPile as a real-world data source. It does **not** replicate the SchemaPile paper's experiments.

## 3. Diagram Type

The project evaluates one diagram family:

**Information Engineering / Crow's-Foot ER diagrams**

SchemaPile relational metadata is normalized into a common ER representation containing:

- entities/tables;
- attributes/columns;
- primary-key membership;
- foreign-key membership and references;
- uniqueness;
- nullability;
- parent/child relationships;
- derived cardinalities;
- identifying-relationship information; and
- relationship requirements.

ORM, UML, and Chen notation are outside the experimental comparison.

## 4. Validation Goal

Given a normalized ER case containing:

1. entities and attributes;
2. primary-key definitions;
3. foreign-key definitions;
4. relationship structure;
5. cardinality and participation information;
6. identifying-relationship information; and
7. stated design requirements,

a validator must determine:

- whether the candidate design is logically valid under the project taxonomy; and
- which error type or error types are present.

All three methods solve the same task.

## 5. Real-World Data Source

The source dataset is **SchemaPile-Perm v0.2**.

SchemaPile was introduced in:

> Till Döhmen, Radu Geacu, Madelon Hulsebos, and Sebastian Schelter. 2024. *SchemaPile: A Large Collection of Relational Database Schemas*. Proceedings of the ACM on Management of Data, 2(3), Article 172. DOI: 10.1145/3654975.

Dataset release:

- SchemaPile-Perm v0.2
- Zenodo DOI: `10.5281/zenodo.12682521`
- Project website: `https://schemapile.github.io/`
- Raw permissive subset: **22,989 schemas**
- Approximately **199,000 tables**

The project downloads the published `schemapile-perm.json.gz` file. The raw dataset is reproducible and is not intended to be committed to this repository.

## 6. Reference-Case Construction

The project does not automatically assume that every real-world SchemaPile schema is a perfect database design.

Instead, the import pipeline creates a **reference-consistent subset** that can be represented faithfully by the project's shared ERCase format and used for controlled-error experiments.

The production importer screened all **22,989 SchemaPile-Perm schemas**.

After conservative filtering:

- **7,366 reference-consistent schemas** were accepted;
- the accepted pool came from **5,897 distinct source repositories**;
- **15,623 schemas** were excluded because they did not satisfy the current representability/filtering rules.

The filtering pipeline requires, among other checks:

- at least 2 tables;
- no more than 20 tables;
- at least one primary key;
- at least one foreign key;
- no more than 60 columns per table;
- no more than 200 total columns per schema;
- no more than 30 foreign keys;
- usable GitHub repository provenance;
- referenced tables and columns to exist;
- foreign-key arity to be internally consistent;
- foreign-key targets to be representable as a primary/candidate key;
- no self-referential foreign keys in the current benchmark;
- no ambiguous case-insensitive table/column names;
- no incompatible multiple FK mappings for the same child-parent pair.

These are project-specific experimental filters. They are not judgments that rejected schemas are inherently incorrect.

## 7. Relationship Derivation

SchemaPile is a relational-schema corpus, not a Crow's-Foot diagram corpus. ER relationship properties are therefore derived deterministically.

For each foreign key:

- the referenced table becomes the parent entity;
- the referencing table becomes the child entity;
- a non-null FK implies mandatory child-to-parent participation (`1`);
- a nullable FK implies optional child-to-parent participation (`0..1`);
- a unique FK implies at most one child per parent (`0..1`);
- a non-unique FK permits many children per parent (`0..*`);
- if all local FK columns participate in the child's primary key, the relationship is marked identifying.

These rules are part of this project's normalization protocol and are applied consistently to all methods.

## 8. Error Taxonomy

The benchmark contains seven logical error classes:

1. `FK_TARGET_NOT_KEY`
2. `FK_WRONG_ENTITY`
3. `COMPOSITE_FK_INCOMPLETE`
4. `CARDINALITY_UNIQUENESS_CONFLICT`
5. `PARTICIPATION_OPTIONALITY_CONFLICT`
6. `IDENTIFYING_RELATIONSHIP_KEY_ERROR`
7. `MISSING_REQUIRED_RELATIONSHIP`

Definitions and mutations are specified in `docs/error_taxonomy.md`.

## 9. Eligibility Audit

Every accepted reference case is audited to determine which controlled mutations can be applied generically.

Production eligibility counts:

| Error Type | Eligible Reference Cases |
|---|---:|
| `FK_TARGET_NOT_KEY` | 4,476 |
| `FK_WRONG_ENTITY` | 5,681 |
| `COMPOSITE_FK_INCOMPLETE` | 394 |
| `CARDINALITY_UNIQUENESS_CONFLICT` | 966 |
| `PARTICIPATION_OPTIONALITY_CONFLICT` | 7,282 |
| `IDENTIFYING_RELATIONSHIP_KEY_ERROR` | 2,164 |
| `MISSING_REQUIRED_RELATIONSHIP` | 7,366 |

The generated report is stored at:

```text
data/audits/eligibility_report.json
```

## 10. Final Production Benchmark

The current benchmark contains:

- **1,400 total cases**
- **700 valid reference cases**
- **700 controlled single-error invalid cases**
- **7 error categories**
- **100 invalid cases per error category**

| Split | Valid | Invalid | Total |
|---|---:|---:|---:|
| Train | 490 | 490 | 980 |
| Dev | 105 | 105 | 210 |
| Test | 105 | 105 | 210 |
| **Total** | **700** | **700** | **1,400** |

Each error category contributes:

- 70 train cases;
- 15 dev cases;
- 15 test cases.

## 11. Split and Leakage Control

The benchmark is split by **source GitHub repository**, not by individual schema.

A deterministic hash assigns each repository to:

- 70% train;
- 15% development;
- 15% test.

All schemas from the same repository remain in one split.

The final benchmark also enforces:

- no source SchemaPile schema is reused more than once;
- a schema used to construct an invalid benchmark case is not also used as a valid benchmark case;
- the same source schema cannot cross splits.

Method-facing inputs must also hide answer-bearing construction information. Ground truth, mutation labels, error counts, mutation seeds, and label-encoding case IDs must not be exposed to validators.

## 12. Ground-Truth Construction

Invalid cases are produced through **controlled structural mutation of real-world reference schemas**.

The underlying schema is real-world; the controlled mutation supplies exact benchmark ground truth.

Current benchmark v2.0 uses **single-error invalid cases only**. Multi-error cases are reserved for future extension.

## 13. Methods

Three methods solve the same validation problem.

### Method 1 — Deterministic Rule-Based Validator

The ER structure is checked with explicit deterministic rules, optionally using a graph representation.

### Method 2 — Formal Constraint-Solver Validator

The ER structure and requirements are translated into logical constraints and evaluated with Z3.

### Method 3 — LLM-Based Validator

A large language model receives the same normalized, leakage-free candidate ER information and returns a structured prediction using the shared taxonomy.

## 14. Shared Input Requirement

All three methods must receive equivalent normalized ER information.

The canonical experimental input is JSON/JSONL.

PlantUML and PNG files may be generated for visualization, manual inspection, report figures, and examples, but are not the authoritative evaluation representation.

## 15. Shared Output Requirement

Every method must produce the same prediction structure:

- case ID;
- method name;
- predicted validity;
- detected error label(s);
- affected entity/attribute/relationship where applicable;
- explanatory message; and
- runtime.

The exact schema is:

```text
schemas/prediction.schema.json
```

## 16. Generalization Requirement

Validation code must not contain:

- special handling for entity names such as `CUSTOMER`, `ORDER`, or `STUDENT`;
- fixed SchemaPile repository names;
- fixed case IDs;
- hard-coded answers;
- source-schema-specific mappings.

Validation must operate on structure and requirements.

## 17. Evaluation

All three methods are evaluated on the same held-out test cases.

Primary metrics include:

- valid/invalid accuracy;
- precision;
- recall;
- F1 score;
- macro-F1;
- per-error metrics;
- exact error-set accuracy;
- localization accuracy;
- false-positive rate; and
- runtime.

Final comparison metrics are computed centrally.

## 18. Experimental Fairness

For a fair comparison:

1. all methods receive the same test cases;
2. all methods use the same seven-error taxonomy;
3. all methods use the same prediction schema;
4. test ground truth is hidden;
5. mutation/construction metadata is hidden;
6. source repositories do not cross splits;
7. final metrics are computed centrally;
8. prompts/model settings are documented;
9. runtime is measured consistently.

## 19. Out of Scope

The current project does not attempt to:

- recognize arbitrary ER diagrams directly from screenshots;
- validate UML, ORM, and Chen diagrams simultaneously;
- perform complete normalization analysis;
- repair every detected error;
- infer semantics absent from both structure and requirements;
- train a multimodal model from scratch;
- reproduce the original SchemaPile experiments.

## 20. Team Responsibilities

### Benchmark / Integration / Evaluation Lead

Responsible for:

- SchemaPile acquisition;
- filtering and normalization;
- eligibility auditing;
- controlled error injection;
- repository-grouped benchmark construction;
- shared schemas/core interfaces;
- evaluation;
- result aggregation;
- report integration.

### Rule-Based Method Owner

Responsible for the deterministic validator, tests, rule documentation, and standardized predictions.

### Constraint-Solver Method Owner

Responsible for formal logical representation, Z3 implementation, tests, and standardized predictions.

### LLM Method Owner

Responsible for LLM validation, prompt design, structured-output handling, tests, and standardized predictions.

## 21. Current Validation Status

At the current SchemaPile benchmark milestone:

```text
pytest -v
```

passes **47 tests** covering schema validation, I/O, shared interfaces, SchemaPile import/normalization, controlled error injection, and production dataset integrity.
