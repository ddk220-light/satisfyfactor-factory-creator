# Satisfactory Factory Planning Skill - Design

**Date:** 2026-02-15
**Status:** Approved

## Goal

Create a skill that teaches Claude how to decompose Satisfactory production chains, compare alternate recipes, and calculate factory throughput — using the satisfactory.db SQLite database as the source of truth.

## Scope

**In scope:**
- Production chain decomposition algorithm (recursive, with SQL at each step)
- Alternate recipe comparison methodology
- By-product handling patterns
- Core formula reference (rates, power, fluids)
- Corrections to Claude's wrong training data

**Out of scope:**
- Raw DB schema/query patterns (covered by satisfactory-db skill)
- Specific optimization algorithms (LP, constraint solving) — varies by use case
- Full factory blueprint generation (building layout, belt routing)

## Approach

Algorithm-First Reference (Approach A): Teach the mechanical procedure for decomposing production chains, with SQL queries for each step. Minimal prose, maximum actionability.

## Key Design Decisions

1. **Complements satisfactory-db** — no schema duplication, references it for raw access
2. **DB is source of truth** — never rely on training data for specific values
3. **Algorithm-specific SQL** — queries tailored to decomposition steps (find recipe, get ingredients, check if raw resource)
4. **Corrections table** — explicitly calls out what Claude's training data gets wrong
5. **Worked example** — Supercomputer chain traced from DB, verified against actual data

## Raw Resources in Supercomputer Chain

Verified from DB: Copper Ore, Caterium Ore, Crude Oil. NO iron ore (Claude's training data incorrectly includes Screws/Iron).
