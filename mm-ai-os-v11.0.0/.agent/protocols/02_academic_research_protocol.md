# 02 Academic Research Protocol — v7.0

Uses dynamic academic search planning and source-backed method selection.

## Core Principle

The Agent MUST NOT rely on pre-installed old method packs, hardcoded method lists, or AI self-knowledge to determine modeling approaches. Instead, the Agent MUST execute academic web searches to discover relevant mathematical methods from authoritative sources.

## Protocol Steps

### 1. Problem Signature Extraction

After `problem-parse-v2`, read the problem corpus and output `workspace/problem_signatures/case.signatures.json` containing:

- `domain_family`: The primary academic domain (e.g., `physical_process.thermal_process`)
- `entities`: Physical entities mentioned in the problem (with types: thermal, mechanical, etc.)
- `physical_quantities`: Measurable quantities
- `task_archetypes`: Types of tasks (e.g., `mechanistic_modeling`, `constrained_optimization`)
- `outputs_required`: Expected deliverables
- `constraints`: Explicit and implicit constraints
- `negative_evidence`: Domains/tasks that can be RULED OUT

All fields must be populated by semantic understanding, NOT keyword matching.

### 2. Academic Search

Execute `academic-search` to generate search queries from the problem signature, then use WebSearch/WebFetch to retrieve results.

Rules:
- NO fallback to AI self-knowledge. If a search returns nothing, report `status=failed`.
- Search queries must be derived from the problem signature, not from a pre-installed pack.
- Search across multiple engines: general web, academic databases, textbooks.
- Collect at least 5 relevant search results per question (budget=full).

### 3. Method Matching

For each question, inspect search results and identify:
- Candidate mathematical models (with source citations)
- Applicable solving algorithms
- Independent verification methods
- Constraint handling approaches

Output `workspace/academic_search/method_matches.json`.

Each identified method MUST:
- Cite at least one search result as its source
- Include a relevance score
- Include a feasibility assessment

### 4. Method Plan Construction

Synthesize a structured method plan (`workspace/method_plan/<QID>_method_plan.json`) containing:
- `primary_model`: Best-supported approach with source citation
- `alternative_models`: At least 2 backup approaches
- `optimization_method`: How to solve/optimize
- `verification_approach`: Independent verification strategy
- `literature_references`: All cited search results

### 5. Coverage Validation

Run `coverage-gap-analysis` to verify:
- Modeling coverage: Every task archetype has a method
- Solution coverage: Every model has a solver plan
- Verification coverage: Independent verification exists
- Citation coverage: Every method has a reference

Gaps must be addressed by additional academic searches — NOT by AI self-knowledge.

### 6. Citation Management

Run `citation-validate` to ensure:
- Every citation has a title
- Every citation has a URL or snippet from actual search
- Every citation is referenced by at least one method plan entry

## Hard Rules

1. **NO AI self-knowledge method selection.** Every modeling decision must cite an academic search result.
2. **NO hardcoded method lists.** Do not use any pre-installed method catalog.
3. **Search template usage is OPTIONAL.** Search templates in `templates/search_templates/` provide query suggestions only — they do NOT prescribe methods.
4. **Search failures are BLOCKING.** If academic search returns no usable results, the case cannot proceed — do not substitute AI knowledge.
