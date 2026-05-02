# How I Used IBM Bob to Build SaveAlife

This document describes how IBM Bob was used to build the SaveAlife with IBM emergency response system, and what I learned about the human–Bob collaboration during the hackathon.

## Overview

I built SaveAlife solo in approximately 9 hours of focused work, using IBM Bob as my primary coding partner. **Bob wrote roughly 95% of the production code.** My role was to design the architecture, craft the prompts, integrate watsonx.ai, refine the medical guardrails, and iterate on the UI.

**Total Bob usage: approximately 6.31 Bobcoins (16% of the 40-coin hackathon budget) across 7 distinct tasks.**

## Task-by-Task Breakdown

Each Bob task was scoped tightly, with a clear input contract and output contract. The full session reports for each task are saved in the `bob_sessions/` folder.

| # | Task | What Bob Built | ~Cost |
|---|---|---|---|
| 1 | Project scaffold | Folder structure, `requirements.txt`, `.env.example`, `.gitignore`, `README.md`, abstract `FacilityAdapter` base class, sample data files (CSV, JSON, messy text) | ~2.4 coins |
| 2 | Data adapters | `HospitalsCsvAdapter`, `PharmaciesJsonAdapter`, `BloodBanksTextAdapter`, plus the `watsonx_client.py` wrapper around `ibm-watsonx-ai` SDK | ~0.6 coins |
| 3 | Three AI agents | `TriageAgent`, `FirstAidAgent`, `ERHandoffAgent` with carefully-designed prompts, JSON output schemas, and defensive defaults | ~0.6 coins |
| 4 | Pipeline orchestrator | `pipeline.py:run_pipeline()` end-to-end orchestrator with timing instrumentation, plus `utils/facility_matcher.py` with Haversine distance and weighted scoring | ~1.0 coins |
| 5 | Streamlit UI | Two-view app (Bystander + ER Trauma Bay), session state for an ER queue, sample reports, dark theme | included in pipeline task |
| 6a | Hospital matcher refinement | Priority-aware scoring (P1 weights closeness 70%, hard specialty requirement) | ~1.5 coins |
| 6b | Live data ingestion | New `ClinicsTextAdapter`, sample data file, UI upload component, map integration with cyan pins | ~1.7 coins |

## Where Bob Excelled

**Scaffolding speed.** The initial project structure — 11 files, sample data, abstract base class — was generated in a single Bob task in under two minutes. A junior engineer would take half a day for the same output.

**Adherence to constraints.** When I told Bob *"don't modify the existing pipeline file"* or *"don't run any code, just write the files,"* it followed those instructions reliably. Each task ended with the right deliverables and no unsolicited extras.

**Adapter pattern propagation.** Once the abstract `FacilityAdapter` base class was in place, every new adapter (CSV, JSON, AI-text, clinics) followed the same pattern automatically. Bob picked up the convention from one example.

**Watsonx.ai integration.** Bob correctly used the `ibm-watsonx-ai` SDK, structured prompts as Python f-string templates, and built defensive JSON parsing tolerant of markdown fences and prefix/suffix text — exactly what's needed for production LLM use.

## Where I Refined Bob's Output

Three places needed human-in-the-loop refinement after Bob's initial implementation. Each is documented here honestly because they show where the collaboration model worked best — Bob wrote, I reviewed, I patched.

**1. Granite 4 chat API migration.** Bob's initial `watsonx_client.py` used `model.generate_text(prompt=...)`, the legacy completion API. The hackathon-provisioned account only exposes Granite 4 H Small, which requires the chat API: `model.chat(messages=[...])`. I diagnosed the empty-string returns, then patched `watsonx_chat()` to build a proper messages array and extract content from the chat response shape. **Lesson: Bob's training data favored older API patterns; verifying SDK calls against your environment is essential.**

**2. Specialty matching logic.** Bob's first hospital matcher used loose substring matching: `"surgery" in "neurosurgery"` returned true, so a hospital with general surgery would falsely match a request for neurosurgery. I added a `_SPECIALTY_ALIASES` dictionary and an exact-equality-first matcher (`_specialties_match()`). For a P1 head trauma case, the system now correctly routes to Central City Hospital (neurology) over Coastal Emergency (surgery only), even though the latter is closer and superficially scored higher. **Lesson: clinical correctness needed domain-specific aliasing that Bob couldn't have known to add.**

**3. Streamlit callback signature mismatch.** Bob's first Streamlit code defined the progress callback with a different argument order than the pipeline used. I traced the runtime error, swapped the parameters, and added a more informative `try/except` block that surfaces tracebacks both to the browser and to the terminal. **Lesson: cross-file contracts (pipeline expects callback(stage_name, step, total); UI passed callback(step, total, stage_name)) are exactly the kind of subtle mismatch a human reviewer catches faster than the AI.**

## Working Style That Worked

A few patterns made the collaboration efficient:

- **One focused task per Bob conversation.** Mixing concerns into a single prompt produced lower-quality output and confused the session report. Discrete tasks each got their own Bob session.
- **Explicit "do not modify" lists.** Telling Bob what *not* to touch was as important as telling it what to build.
- **Type-precise inputs and outputs.** Specifying the exact JSON schema each agent should return eliminated guesswork.
- **Sample-first, abstract-second.** Showing Bob a concrete sample data file made adapter generation flawless.

## Compliance

All watsonx.ai inference was performed against the hackathon-provisioned IBM Cloud account (account ID `2998220 - watsonx`), using the `ibm/granite-4-h-small` model. Total cloud spend was approximately $0.005 of the $80 credit allocation.

## Conclusion

Bob is best used as a **fast, literal, well-instructed collaborator** — not as an oracle. The 95/5 split between Bob-generated code and human-written prompts/refinements feels about right for a hackathon. Bob compressed two days of work into nine hours.