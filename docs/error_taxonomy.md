# ER Validation Error Taxonomy

## 1. Purpose

All three validation methods must use the same seven-label error taxonomy.

The current benchmark is derived from real-world SchemaPile-Perm schemas and uses controlled **single-error mutations** to create exact invalid-case ground truth.

Supported labels:

```text
FK_TARGET_NOT_KEY
FK_WRONG_ENTITY
COMPOSITE_FK_INCOMPLETE
CARDINALITY_UNIQUENESS_CONFLICT
PARTICIPATION_OPTIONALITY_CONFLICT
IDENTIFYING_RELATIONSHIP_KEY_ERROR
MISSING_REQUIRED_RELATIONSHIP
```

## E01 — `FK_TARGET_NOT_KEY`

### Definition

A foreign key references an attribute that is not represented as a primary key or candidate/unique key of the referenced entity.

### Controlled Mutation

For an eligible real-world relationship:

1. select a single-column FK;
2. keep the expected parent entity unchanged;
3. redirect the FK to a same-type attribute in that parent;
4. require the new target to be non-primary and non-unique.

### Expected Detection

Report the child entity, FK attribute, referenced entity, invalid target attribute, and relationship.

### Production Eligibility

**4,476** accepted reference cases.

## E02 — `FK_WRONG_ENTITY`

### Definition

A foreign key references a valid key in the wrong parent entity relative to the declared relationship or requirement.

### Difference from E01

E01 asks whether the target attribute is a valid key.

E02 asks whether the referenced entity is the logically expected parent.

### Controlled Mutation

For an eligible FK:

1. retain the original relationship expectation;
2. find another entity containing a compatible same-type candidate key;
3. redirect the FK to that alternative entity/key;
4. leave the original requirement and relationship parent unchanged.

### Production Eligibility

**5,681** accepted reference cases.

## E03 — `COMPOSITE_FK_INCOMPLETE`

### Definition

A relationship requires a multi-column foreign key, but one or more required FK components are missing from the mapping.

### Controlled Mutation

For an eligible relationship with at least two FK components:

1. select one FK component;
2. remove its FK status;
3. remove its explicit reference mapping;
4. preserve the other composite components and relationship requirement.

### Production Eligibility

**394** accepted reference cases.

This is the rarest production class, but it still supports the balanced 100-case benchmark.

## E04 — `CARDINALITY_UNIQUENESS_CONFLICT`

### Definition

The declared relationship multiplicity conflicts with the uniqueness/key structure.

### Example

The relationship states:

```text
child_cardinality = "0..1"
```

but the FK is represented as non-unique, allowing multiple child rows to reference one parent.

### Controlled Mutation

Preserve the relationship cardinality and FK target, but remove the relevant uniqueness representation.

### Production Eligibility

**966** accepted reference cases.

## E05 — `PARTICIPATION_OPTIONALITY_CONFLICT`

### Definition

The relationship requires mandatory child-to-parent participation, but the candidate FK representation permits the reference to be absent.

### Example

The relationship requires:

```text
parent_cardinality = "1"
```

but a participating FK component is nullable.

### Controlled Mutation

Preserve the relationship and target, but change an eligible non-null FK component to nullable.

### Production Eligibility

**7,282** accepted reference cases.

## E06 — `IDENTIFYING_RELATIONSHIP_KEY_ERROR`

### Definition

A relationship is declared identifying, but a parent identifier propagated through the FK is not correctly retained as part of the child's primary key.

### Controlled Mutation

For an eligible identifying relationship:

1. preserve the FK reference;
2. preserve the identifying relationship;
3. remove primary-key membership from one FK component that originally participated in the child PK.

### Production Eligibility

**2,164** accepted reference cases.

## E07 — `MISSING_REQUIRED_RELATIONSHIP`

### Definition

The requirements state that two entities must be related, but the candidate design no longer contains the required relationship or corresponding FK connection.

### Controlled Mutation

For an eligible relationship:

1. preserve the requirement;
2. remove the candidate relationship;
3. remove the corresponding FK status/reference mapping;
4. leave unrelated structure unchanged.

### Production Eligibility

**7,366** accepted reference cases.

## 2. Eligibility Summary

| Error Type | Eligible Cases |
|---|---:|
| `FK_TARGET_NOT_KEY` | 4,476 |
| `FK_WRONG_ENTITY` | 5,681 |
| `COMPOSITE_FK_INCOMPLETE` | 394 |
| `CARDINALITY_UNIQUENESS_CONFLICT` | 966 |
| `PARTICIPATION_OPTIONALITY_CONFLICT` | 7,282 |
| `IDENTIFYING_RELATIONSHIP_KEY_ERROR` | 2,164 |
| `MISSING_REQUIRED_RELATIONSHIP` | 7,366 |

The machine-generated report is stored at:

```text
data/audits/eligibility_report.json
```

## 3. Valid Cases

A valid case contains:

```json
{
  "valid": true,
  "errors": []
}
```

In this benchmark, "valid" means **reference-consistent under the project's representable constraints and seven-error taxonomy**.

It does not mean that every accepted real-world schema is universally optimal or free of every possible database-design issue.

## 4. Invalid Cases

Current benchmark v2.0 contains one intended taxonomy violation per invalid case:

```json
{
  "valid": false,
  "errors": [
    {
      "error_type": "FK_TARGET_NOT_KEY"
    }
  ]
}
```

## 5. Current Single-Error Policy

Benchmark v2.0 contains:

```text
700 valid cases
700 invalid cases
100 invalid cases per error type
1,400 total cases
```

Single-error construction supports clean per-class comparison and exact mutation attribution.

## 6. Multi-Error Cases

Multi-error cases are **not part of the current production benchmark**.

They may be added later as a robustness extension after the single-error comparison is complete.

## 7. Error Injection Rules

Every invalid benchmark case must:

1. start from an accepted reference-consistent SchemaPile case;
2. pass the relevant mutation-eligibility check;
3. receive exactly one controlled mutation;
4. record the mutation for auditing;
5. preserve unaffected structure;
6. validate against `schemas/er_case.schema.json`;
7. preserve the requirement needed to expose the violation;
8. avoid source-schema reuse in the final benchmark;
9. avoid unintended additional taxonomy violations where practical.

## 8. Ground-Truth Isolation

Construction metadata is not a prediction feature.

Fields such as:

```text
mutation
mutation_version
mutation_seed
mutation_source
error_count
```

must not be exposed to validators.

Method-facing case IDs must also be opaque with respect to validity and error type.

## 9. No Dataset-Specific Heuristics

A validator must not identify errors using:

- source repository name;
- source SchemaPile ID;
- benchmark case ID;
- mutation metadata;
- memorized entity/attribute names.

Detection must be based on the normalized ER structure and stated requirements.

## 10. Future Extensions

Any future error label must:

- have a precise definition;
- be observable from the shared input;
- support verifiable ground truth;
- have enough eligible cases for meaningful comparison;
- be integrated consistently into evaluation and documentation.
