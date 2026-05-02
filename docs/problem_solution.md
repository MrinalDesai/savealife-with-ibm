# SaveAlife with IBM
*AI-coordinated trauma response for the Golden Hour*

## The Problem

In India, **road accidents kill over 150,000 people every year** — roughly 17 deaths every hour. Most of those deaths are not caused by the impact itself. They happen in the **Golden Hour** — the critical first 60 minutes after injury, when timely medical intervention determines whether the victim survives.

The bottleneck isn't medicine. It's **coordination**. Bystanders don't know what first-aid is safe. Ambulances arrive without knowing what the patient needs. Hospitals receive patients without knowing what blood, what specialists, or what equipment to prepare. Every minute of that uncertainty costs lives.

Building a system that fixes this is hard for one specific reason: **integrating new data sources is slow**. Every new region, every new hospital network, every new pharmacy chain ships its data in a different format. Traditional integration takes weeks. Lives don't have weeks.

## The Solution

**SaveAlife with IBM** is an AI-coordinated trauma response system, designed to compress the Golden Hour from minutes of confusion into seconds of structured action.

A bystander submits a free-text accident report. In approximately 24 seconds, three watsonx.ai-powered Granite agents process it sequentially:

1. **Triage Agent** — classifies severity (P1/P2/P3/P4) and extracts structured clinical signals using ESI/START protocols.
2. **First-Aid Agent** — generates safe, evidence-based bystander instructions with strict guardrails (no medications, no clinical interventions beyond bystander scope).
3. **ER Handoff Agent** — produces a pre-arrival trauma brief for the receiving hospital, including bay assignment, blood product cross-matching, and specialist pages.

A priority-aware facility matcher then routes the patient to the most appropriate hospital, weighing distance against specialty match. For P1 head trauma, the system correctly prefers a hospital with neurosurgical capability slightly farther away over a closer hospital without it.

## How IBM Bob Powers Impact at Scale

The hackathon theme is *"Turn idea into impact faster."* In emergency response, faster impact means faster integration of new healthcare facility data — the bottleneck that has historically slowed deployment.

**IBM Bob built this entire system in approximately 6 Bobcoins of usage** (16% of the hackathon budget) across 7 well-scoped tasks: scaffold, three data adapters, three watsonx.ai agents, pipeline orchestrator, Streamlit UI, hospital matcher refinement, and live data ingestion.

The system also includes a **live data integration demo**: a user can paste any unstructured text describing new clinics, pharmacies, or facilities. Watsonx.ai's Granite model parses it into structured records, and the new facilities appear on the coordination map within seconds. **What used to take weeks of integration engineering now takes seconds of Bob-assisted code generation plus one watsonx call.**

## Why This Matters

Every region SaveAlife is deployed in saves lives. Every hospital network it integrates with saves more. Bob compresses that deployment timeline from quarters to coffee breaks. That is what *"impact faster"* looks like in healthcare.

---

**Tech stack**: Python · Streamlit · IBM Bob IDE · IBM watsonx.ai (Granite 4 H Small) · pandas · pydeck.

**Built solo for the IBM Bob Dev Day Hackathon, May 2026.**