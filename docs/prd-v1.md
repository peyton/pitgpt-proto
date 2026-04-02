**PRODUCT REQUIREMENTS DOCUMENT**

**PitGPT**

A Consumer N-of-1 Trial Platform for Research-Driven Self-Experimentation

*Upload questions. Upload research. Generate valid personal experiments.*

  -------------- ---------------------------------
  **Version**    1.0

  **Date**       April 2, 2026

  **Status**     Draft --- For Founder Review

  **Audience**   Product, Engineering, Investors
  -------------- ---------------------------------

**CONFIDENTIAL**

1\. Executive Summary

PitGPT is a consumer self-experimentation platform that transforms informal personal testing into structured, statistically valid N-of-1 trials. The core innovation is a research ingestion pipeline: users upload questions they care about or research they have found (PDFs, links, plain-text hypotheses), and the platform generates a valid, personally executable experimental protocol --- complete with randomized scheduling, locked outcomes, and honest statistical analysis.

The product sits at the intersection of three converging trends: the explosion of consumer wellness experimentation (driven by social content and a \~\$1.8T global wellness market), growing demand for personalized evidence over population averages, and the maturation of N-of-1 trial methodology in clinical research. PitGPT bridges the gap between rigorous single-case experimental design and everyday consumer decision-making.

+-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| **Core Value Proposition**                                                                                                                                                                                                                      |
|                                                                                                                                                                                                                                                 |
| \"Help me decide what works for me, faster, with less regret --- by turning my routine changes into a structured test.\" Users go from a question or a study they found online to a running, randomized personal experiment in under 3 minutes. |
+-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+

**Target user:** \"Maximalist optimizers\" --- the \~25% of wellness consumers who are digitally savvy, experimentally inclined, and already informally testing routines, supplements, and products. They want answers, not just data.

**Starting wedge:** Beauty, cosmetic, and non-disease skincare routines. This domain is low-risk, reversible, fast-feedback, and avoids medical/regulatory complexity. It proves the experimentation model before expanding to harder health domains.

2\. Problem Statement

2.1 The Unmet Need

Millions of consumers experiment with products and routines daily --- switching skincare, trying new supplements, changing sleep habits --- but they do so in a way that produces no reliable signal. The typical pattern is: try something, notice (or imagine) a change, attribute it to the new thing, and either stick with it or move on. This is correlation masquerading as evidence.

Existing tools fail to bridge this gap:

- **Symptom trackers** (Bearable, Guava, Apple Health): great for logging, but surface correlations at best. No randomization, no protocol lock, no causal inference.

- **Patient communities** (PatientsLikeMe, StuffThatWorks): valuable peer experience, but observational and vulnerable to selection/reporting bias.

- **Wellness apps** (Oura, Whoop): aggregate biometric data beautifully, but don't adjudicate between interventions.

- **Academic N-of-1 tools** (StudyU, Trialist, Self-E): scientifically sound but lack consumer distribution, social dynamics, and usable design.

2.2 Why N-of-1 Trials Are the Right Method

A well-designed N-of-1 trial treats the individual as their own control through randomized crossover periods. This is closer to an RCT within a single person than to correlation-based self-tracking. The method produces valid within-person causal inference when the platform enforces: (1) a prospective, locked protocol with a primary outcome, (2) randomized switching between conditions, (3) frequent repeated measurements, and (4) controls for time trends and carryover.

The N-of-1 approach is especially compelling when treatment effect heterogeneity is large --- i.e., when \"what works on average\" is a poor guide for what works for you. Beauty/skincare is an ideal domain because individual skin type, environment, and routine interactions make population averages nearly useless.

2.3 The Research Ingestion Insight

The unique feature of PitGPT is that users don't start from a blank slate. They arrive with questions and context --- a blog post about vitamin C serums, a PubMed abstract about retinol, a TikTok claim about rice water rinses --- and the platform converts that raw curiosity into a structured, defensible protocol. This is the \"research-to-trial\" pipeline that no existing product provides.

3\. Product Vision & Positioning

3.1 Product Category

PitGPT is a consumer N-of-1 experimentation platform --- a \"personal evidence engine.\" It is not a tracker, not a health dashboard, and not a recommendation engine. The core job-to-be-done is turning routine changes into structured tests.

3.2 Positioning Statement

*For wellness-curious consumers who are tired of guessing which product or routine works best for them, PitGPT is a self-experimentation tool that generates valid personal A/B experiments from questions and research they care about. Unlike symptom trackers that show correlations or forums that share anecdotes, PitGPT uses randomized switching and protocol lock to deliver personal causal evidence with honest uncertainty.*

3.3 Brand Principles

- A tracker tells you what happened. A trial tells you what caused it.

- n=1 isn't weak. Sloppy n=1 is weak.

- The product isn't data. It's decision clarity.

- Private by default. Scientific by design.

- We don't recommend treatments. We help you ask a better question and test it safely.

3.4 Anti-Positioning (What PitGPT Is NOT)

- \"We'll tell you what to take.\"

- \"The app cures X.\"

- \"Our community discovered the best treatment for Y.\"

- \"AI doctor in your pocket.\"

- \"Upload your data and we'll diagnose you.\"

4\. Core User Journey

The end-to-end flow is gated, templated, and locked --- with freedom only inside safe boundaries. The journey has three phases: Ingest, Execute, and Learn.

4.1 Phase 1: Research Ingestion & Question Framing

This is PitGPT's unique differentiator. Users arrive with raw curiosity and leave with a testable protocol.

4.1.1 Input Methods

Users can seed a trial through multiple pathways:

1.  **Natural language question:** \"Is CeraVe or La Roche-Posay better for my dry skin?\" The system parses the question, identifies the comparison, and maps it to an appropriate template.

2.  **PDF/link upload:** User uploads a PubMed abstract, blog post, or product review. The AI extraction pipeline identifies the intervention, claimed outcomes, study design, and relevant parameters --- then translates these into a personal N-of-1 protocol.

3.  **Template selection:** User browses pre-built experiment templates (skincare comparison, morning routine A/B, haircare, sleep routine, custom) and picks one directly.

4.  **Community protocol:** (Post-MVP) User discovers and follows a protocol shared by another user.

4.1.2 AI-Powered Protocol Generation

When a user uploads research or poses a question, the system performs:

- **Entity extraction:** Identifies intervention(s), comparator(s), claimed outcome(s), dosing/timing, study population, and reported effect sizes.

- **Safety classification:** Classifies the proposed experiment as Green (safe to run), Yellow (allowed with restrictions/warnings), or Red (blocked --- disease treatment, medications, high-risk interventions).

- **Protocol synthesis:** Generates a complete N-of-1 protocol: primary outcome measure (locked), block schedule, measurement cadence, washout guidance, adherence requirements, and pre-specified analysis plan.

- **Confidence labeling:** Tags the generated protocol with a \"research basis\" indicator: strong (multiple RCTs), moderate (pilot studies), weak (anecdotal/theoretical), or novel (no prior evidence found).

4.1.3 Safety Gating (Green / Yellow / Red Framework)

  --------------- --------------------------------------- ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  **Tier**        **Scope**                               **Examples & Rules**

  **✅ GREEN**    Low-risk, non-disease, reversible       Skincare products, beauty routines, haircare, sleep hygiene timing, morning routines. No restrictions.

  **⚠️ YELLOW**   Moderate risk; extra consent required   OTC actives (benzoyl peroxide, salicylic acid), diet pattern changes, exercise protocol comparisons. Requires explicit warnings, exclusion screening, and \"do not change medications\" acknowledgment.

  **❌ RED**      Blocked --- not allowed on platform     Prescription medications, supplements with interaction risks (e.g., NAC), disease management claims (ADHD, depression, eczema), invasive devices, anything requiring medical supervision.
  --------------- --------------------------------------- ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

4.2 Phase 2: Trial Execution

4.2.1 Protocol Lock & Randomization

Once the user confirms their protocol, the system locks the primary outcome, measurement cadence, and analysis plan. This is non-negotiable for any result labeled as causal evidence. The system generates a block-randomized A/B schedule (e.g., 6 weeks = 3 pairs, each pair randomly assigning one week to A and one to B). The schedule is concealed --- the user sees only the current week's assignment.

4.2.2 Daily Check-In Loop

The daily check-in is the atomic unit of the product and must be completable in under 20 seconds:

1.  **Primary outcome:** A single 0--10 slider with anchored endpoints defined by the template.

2.  **Adverse event flag:** \"Did you experience any irritation, discomfort, or reaction today?\" (yes/no; if yes, free-text description).

3.  **Adherence flag:** \"Did you use the assigned product/routine today?\" (yes/no/partial).

4.  **Optional note:** Collapsed by default, for contextual logging (travel, stress, sleep, cycle).

4.2.3 No Interim Results

PitGPT shows NO mid-trial comparisons between conditions. If users see \"A is winning\" partway through, they will unconsciously bias their ratings or stop early. This is the critical design constraint that separates PitGPT from a symptom tracker. The only mid-trial data visible is progress (days completed, adherence percentage) and the current week's assignment.

4.2.4 Adverse Event Handling

If a user reports irritation for 3+ consecutive days, a persistent banner recommends stopping the experiment. A \"Stop Experiment Early\" button is always available. Early-stopped trials are still analyzed with available data, but the quality grade is capped and the result includes a note about early termination.

4.3 Phase 3: Results & Learning

4.3.1 Personal Results Dashboard

After trial completion, the user receives a results card containing:

- **Verdict:** A plain-language summary (e.g., \"Condition A scored higher on 72% of days, with an average difference of 1.3 points\").

- **Effect size + confidence interval:** Mean scores for each condition, the difference, and a 95% CI. Presented visually and in plain English.

- **Quality grade (A--D):** Based on adherence rate, data completeness, and trial integrity.

- **Time-series chart:** Daily outcome scores color-coded by condition, showing the full trial trajectory.

- **Honest caveats:** Always visible, not buried: expectancy effects (unblinded), regression to the mean, and limitations of personal evidence.

4.3.2 Three Tiers of Evidence (The Trust Contract)

The platform explicitly distinguishes and labels three types of output:

1.  **Personal causal estimate (within-person):** \"In your trial, with your data, under this protocol, the estimated effect is X ± Y.\" Requires locked protocol + randomization.

2.  **Pooled evidence across users:** \"Across users who ran this locked protocol, the distribution of effects is Z.\" Requires aligned protocols + opt-in consent + minimum thresholds. (Post-MVP.)

3.  **Observational / hypothesis-only:** \"Here are associations from unlocked tracking. Not causal.\" For exploratory sandbox mode.

5\. Feature Requirements

5.1 MVP Features (v1 --- Ship First)

  ------------------------------- ------------------------------------------------------------------------------------------------- ------------------
  **Feature**                     **Description**                                                                                   **Priority**

  Research Ingestion Pipeline     Upload PDFs, paste links/questions; AI extracts entities and generates protocol drafts            P0 --- Core

  Safety Classification Engine    Green/Yellow/Red gating; blocks disease claims, medications, high-risk interventions              P0 --- Core

  Template-Driven Trial Builder   6 pre-built templates (skincare, haircare, morning routine, evening routine, sleep, custom A/B)   P0 --- Core

  Protocol Lock                   Primary outcome, cadence, and analysis plan frozen at trial start; immutable                      P0 --- Core

  Randomization Engine            Block-randomized A/B schedule with concealed allocation; seeded for reproducibility               P0 --- Core

  Daily Check-In (\<20s)          Outcome slider, adverse event flag, adherence flag, optional note; append-only                    P0 --- Core

  Reminder System                 Daily in-app prompt + optional email reminders at user-set time                                   P0 --- Core

  Personal Results Dashboard      Effect size, CI, quality grade, time-series chart, plain-language verdict and caveats             P0 --- Core

  Adverse Event Capture           Irritation flag logging; 3-day consecutive warning; early stop pathway                            P0 --- Core

  Data Export & Deletion          CSV/JSON export of all trial data; permanent deletion on request                                  P0 --- Trust

  Backfill Guard                  Max 2-day retrospective entry; beyond that, marked as missing                                     P1 --- Integrity

  Research Basis Indicator        Tags protocols with evidence strength: strong / moderate / weak / novel                           P1 --- Trust
  ------------------------------- ------------------------------------------------------------------------------------------------- ------------------

5.2 Post-MVP Features (v2+)

  ---------------------------------- --------------------------------------------------------------------------------- -----------------
  **Feature**                        **Description**                                                                   **Phase**

  Community Protocol Sharing         Opt-in protocol sharing; users can follow others' locked protocols                v2

  Pooled Results (Opt-In Registry)   Bayesian hierarchical pooling across aligned protocols; IRB-backed consent        v2

  Bayesian Personal Analysis         Replace paired t-test with Bayesian time-series; probability-of-benefit framing   v2

  Photo Capture & Standardization    Guided photo capture with lighting/framing controls for skincare trials           v2

  Buddy Blinding Workflow            Guided flow for a friend to label products A/B for partial blinding               v2

  Wearable Integration               Oura, Apple Health, Whoop data as objective outcome supplements                   v3

  Heterogeneity Explorer             \"Likely responders vs non-responders\" visualization from pooled data            v3

  Yellow-Category Expansion          Acne (restricted), OTC supplement comparisons with clinician guardrails           v3

  Brand-Agnostic Trial Marketplace   Browse and run experiments by category; social feed of completed trials           v4
  ---------------------------------- --------------------------------------------------------------------------------- -----------------

5.3 Explicitly Out of Scope for v1

- Public \"what works for ADHD/acne\" rankings or pooled effectiveness leaderboards

- Algorithmic recommendation engine that suggests treatments for diseases

- AI diagnosis or automated photographic severity classifiers (high device risk)

- Brand-sponsored trials (scientific conflict + claims pressure)

- Supplement or ingestible templates (regulatory safety)

- Disease-specific templates (ADHD, depression, eczema, acne)

- User accounts with authentication (v1 uses device-local or anonymous ID)

- Push notifications (in-app banners and email reminders only)

- Multiple concurrent trials (one active trial per user)

6\. Research Ingestion Pipeline --- Technical Specification

The research ingestion pipeline is the feature that transforms PitGPT from \"yet another A/B template tool\" into a research-powered personal evidence engine. It is the primary differentiator.

6.1 Input Processing

The pipeline accepts three input types, each processed through a common extraction layer:

  ------------------ ------------------------------------------------------------------------------------------------- --------------------------------------------------------------
  **Input Type**     **Processing**                                                                                    **Output**

  PDF Upload         OCR + structured extraction; identify study design, population, endpoints, dosing, effect sizes   Extracted Protocol Skeleton with confidence scores per field

  URL / Link         Web fetch + content extraction; parse blog posts, abstracts, product pages                        Structured claims + source metadata + evidence quality tag

  Natural Language   Intent classification + entity extraction; parse comparison structure, outcomes, timing           Mapped template selection + pre-filled condition labels
  ------------------ ------------------------------------------------------------------------------------------------- --------------------------------------------------------------

6.2 Protocol Synthesis Logic

After extraction, the synthesis engine maps research findings to a valid N-of-1 protocol:

1.  **Intervention mapping:** Extracted interventions are matched against the platform's intervention library. Unknown interventions trigger safety classification review.

2.  **Outcome selection:** The system selects the most appropriate validated outcome measure from the outcome library, or generates a constrained 0--10 scale with specific anchors.

3.  **Design parameter optimization:** Based on extracted onset time, washout requirements, and expected effect size, the system recommends block length (1--2 weeks), total duration (4--8 weeks), and measurement cadence.

4.  **Confounder identification:** The system flags likely confounders for the specific domain (e.g., menstrual cycle for skincare, sleep quality for cognitive outcomes) and adds them as optional tracking fields.

5.  **Human review prompt:** The generated protocol is presented to the user for review and confirmation before locking. Users can adjust condition labels but not the scientific design parameters.

6.3 Evidence Quality Tagging

Every ingested source receives an evidence quality tag that persists through the protocol and into results:

- **Strong:** Multiple randomized controlled trials support the comparison.

- **Moderate:** Pilot studies, small RCTs, or systematic reviews with limitations.

- **Weak:** Observational data, case reports, or mechanistic reasoning only.

- **Novel:** No prior evidence found; user is pioneering this comparison. Labeled as purely exploratory.

7\. Data Model

The core data model supports the full lifecycle from ingestion through analysis.

  ------------------- ----------------------------------------------------------------------------------------- ----------------------------------------------------------------
  **Entity**          **Key Fields**                                                                            **Notes**

  User                id, created_at, reminder_time, timezone                                                   Anonymous by default; no email/login in v1

  Research Source     id, type (pdf\|url\|text), raw_content, extracted_entities, evidence_quality_tag          Stores raw upload + AI extraction output

  Trial               id, user_id, template_id, condition_a/b labels, status, schedule, randomization_seed      Protocol is immutable after lock; schedule is seeded for audit

  Protocol (Locked)   trial_id, primary_outcome_question, duration, block_length, cadence, analysis_plan_hash   Versioned; hash ensures integrity

  Observation         id, trial_id, date, primary_score, irritation, adherence, note, is_backfill               Append-only; no edits after submission

  Result              id, trial_id, mean_a/b, difference, ci_lower/upper, quality_grade, verdict                Computed only after trial completion

  Adverse Event       id, trial_id, date, description, severity                                                 All AE reports preserved in export
  ------------------- ----------------------------------------------------------------------------------------- ----------------------------------------------------------------

8\. Analysis & Statistical Engine

8.1 Primary Analysis (v1)

The v1 analysis uses a straightforward comparison of daily scores between conditions:

5.  Compute mean daily primary outcome score for Condition A days and Condition B days separately. Exclude days where adherence = \"no\" (per-protocol analysis).

6.  Compute the difference (mean_A -- mean_B).

7.  Compute a 95% confidence interval for the difference using a two-sample t-test (Welch's, to handle unequal variance).

8.  Generate a quality grade (A--D) based on adherence rate, data completeness, and trial integrity.

9.  Produce a plain-language verdict combining direction, magnitude, uncertainty, and quality.

8.2 Quality Grading Rubric

  ----------- ----------------------------------------------------------- ------------------------------------------
  **Grade**   **Criteria**                                                **Interpretation**

  A           ≥85% adherence, ≥90% days logged, full protocol completed   Strong personal evidence

  B           ≥70% adherence, ≥75% days logged, full protocol completed   Good personal evidence with some gaps

  C           \<70% adherence OR early stop OR significant missing data   Suggestive but interpret with caution

  D           \<50% adherence OR \<50% days logged                        Insufficient data for reliable inference
  ----------- ----------------------------------------------------------- ------------------------------------------

8.3 Future: Bayesian Analysis (v2)

V2 will upgrade to Bayesian time-series regression with explicit terms for treatment indicator, period effects, linear time trend, and carryover. This enables expressing results as \"probability of meaningful benefit,\" which is more decision-useful for consumers than p-values. Pooled analysis across users will use a Bayesian hierarchical model to estimate both the population average effect and the heterogeneity of individual effects.

9\. Experiment Templates (v1)

Each template defines locked scientific parameters. Users can only customize their condition labels and notes --- not the outcome measure, duration, block structure, or analysis method.

  ------------------ --------------------------- -------------- ------------ ------------- ---------- -------------
  **Template**       **Primary Outcome**         **Duration**   **Blocks**   **Cadence**   **Tier**   **Washout**

  Skincare Product   Skin satisfaction (0--10)   6 weeks        1-week       Daily         Green      None

  Morning Routine    Midday appearance (0--10)   6 weeks        1-week       Daily         Green      None

  Haircare Product   Hair quality (0--10)        6 weeks        1-week       Daily         Green      None

  Evening Routine    Morning skin feel (0--10)   6 weeks        1-week       Daily         Green      None

  Sleep Routine      Sleep quality (0--10)       4 weeks        1-week       Daily AM      Green      1--2 days

  Custom A/B         User-defined (0--10)        6 weeks        1-week       Daily         Green\*    None
  ------------------ --------------------------- -------------- ------------ ------------- ---------- -------------

*\* Custom A/B template includes a warning: \"This tool is for comparing everyday routines and products. It is not designed for testing medications, supplements, or treatments for medical conditions.\"*

10\. Safety, Regulatory & Claims Strategy

10.1 Operating Model

PitGPT launches as Model A: a private self-experimentation tool. Users run personal experiments and receive private results. No pooled public effectiveness claims until governance and IRB infrastructure are in place.

10.2 Regulatory Positioning

The product is positioned as a general wellness / personal decision tool, not a medical device or clinical decision support system. This positioning is maintained through:

- **Language discipline:** \"Compare routines,\" \"personal evidence,\" \"general wellness,\" \"appearance/comfort.\" Never: \"treat,\" \"cure,\" \"manage symptoms,\" \"clinical decision support.\"

- **Template restrictions:** No disease-specific templates. No supplement templates. No medication templates.

- **Claims guardrails:** Results pages carry persistent disclaimers. No aggregate \"what works\" claims until IRB-backed.

- **FDA alignment:** Designed to fit within FDA's \"General Wellness: Policy for Low Risk Devices\" guidance --- low-risk, intended only for general wellness use, unrelated to disease diagnosis/treatment.

- **FTC compliance:** No health benefit claims without competent and reliable scientific evidence. Platform does not endorse specific products.

10.3 Privacy Architecture

Privacy is not optional --- it is an existential product requirement. V1 design principles:

- No ad trackers, analytics pixels, or third-party data sharing.

- Client-side or anonymous-ID data storage in v1; no email/password accounts.

- All data exportable by the user at any time (CSV/JSON).

- All data permanently deletable on request.

- Designed for compliance with CCPA/CPRA, Washington My Health My Data Act, and FTC Health Breach Notification Rule.

- GDPR-ready architecture for future international expansion.

10.4 Copy Guidelines

**Always use:** \"Compare,\" \"test,\" \"personal experiment,\" \"routine,\" \"product,\" \"structured A/B,\" \"personal evidence,\" \"decision clarity.\"

**Never use:** \"Clinically proven,\" \"treatment,\" \"therapy,\" \"diagnosis,\" \"cure,\" \"heal,\" \"medical-grade,\" any disease name, \"FDA\" anything, \"We recommend \[product\].\"

11\. Technical Architecture (High-Level)

V1 is designed for speed-to-ship. A client-only web application with local storage is acceptable if it ships faster than a full backend.

11.1 Core Services

- **Research Ingestion Service:** PDF parsing (OCR), web content extraction, NLP entity extraction, safety classification. Powered by LLM with structured output constraints.

- **Protocol Synthesis Service:** Maps extracted entities to templates, selects outcome measures, generates block schedule, locks analysis plan.

- **Randomization Service:** Generates seeded block-randomized schedules. Append-only audit log.

- **Data Capture Service:** Time-stamped observation logging, adherence tracking, AE capture. Append-only.

- **Analysis Engine:** Reproducible, versioned analysis. Computes effect sizes, CIs, quality grades. Outputs structured result objects.

- **Safety Service:** Green/Yellow/Red classification, intervention gating, AE escalation logic, consecutive-irritation warnings.

11.2 Technology Choices (Recommended)

- **Frontend:** React (responsive web app; mobile-first). No native app in v1.

- **Storage:** LocalStorage / IndexedDB for v1 (zero-server MVP). Migrate to encrypted cloud storage in v2.

- **AI/LLM:** Claude API for research ingestion, entity extraction, protocol synthesis, and evidence quality tagging.

- **Randomization:** Client-side seeded PRNG (e.g., seedrandom.js). Deterministic, reproducible, auditable.

- **Statistics:** Client-side computation (jStat or simple-statistics). Welch's t-test + CI. Bayesian upgrade in v2 via API.

12\. Success Metrics & Acceptance Criteria

12.1 MVP Acceptance Criteria

The MVP is shippable when a user can:

- Upload a question, PDF, or link and receive a generated protocol in under 60 seconds

- Pick a template and set up an experiment in under 2 minutes

- See their current week's assignment (and only the current week)

- Complete a daily check-in in under 20 seconds

- See their progress (days completed, adherence %)

- Stop an experiment early with data preserved

- View results with verdict, scores, CI, quality grade, caveats, and evidence basis tag

- View a time-series chart of daily scores color-coded by condition

- Export their data as CSV and delete all data

- Complete the full end-to-end flow on mobile web (responsive)

12.2 Key Metrics (First 90 Days)

  ----------------------------------- ---------------------- -------------------------------------------------------
  **Metric**                          **Target**             **Why It Matters**

  Trial completion rate               ≥40%                   Proves users tolerate multi-week structured protocols

  Mean daily adherence                ≥75%                   Minimum for Grade B results

  Research-to-protocol conversion     ≥60%                   Validates ingestion pipeline value

  User-reported decision usefulness   ≥4.0/5                 Core value prop validation

  \"Inconclusive\" acceptance rate    ≥70% don't churn       Users accept honest uncertainty

  Time to first check-in              \<3 min from landing   Onboarding friction test
  ----------------------------------- ---------------------- -------------------------------------------------------

13\. Roadmap

13.1 90-Day Validation Plan

**Weeks 1--2:** Concierge pilot with 50--100 users running a single cosmetic A/B protocol. Measure completion rate, adherence, and perceived decision usefulness. Test research ingestion pipeline with real user-uploaded PDFs and questions.

**Weeks 3--6:** A/B test protocol friction: \"fully guided\" (AI generates everything) vs \"semi-guided\" (user selects template). Track drop-off points and iterate templates.

**Weeks 7--10:** Validate analysis comprehension: can users correctly interpret uncertainty warnings? Use comprehension quizzes. Iterate results UI based on misinterpretation patterns.

**Weeks 11--13:** Build opt-in cohort prototype (private). Evaluate whether users want to contribute data under explicit consent and whether they understand re-identification risk.

13.2 12-Month Phased Roadmap

**Q1:** MVP launch with green-wedge templates + research ingestion pipeline + personal inference + privacy baseline.

**Q2:** Add yellow-category skincare (restricted) + stronger safety gating. Begin independent IRB discussions for opt-in research registry.

**Q3:** Launch opt-in registry with umbrella protocol and locked analyses. Publish only aggregate method-demo stats (not intervention claims). Bayesian analysis upgrade.

**Q4:** Consider acne (restricted) if protocol integrity is maintained. Community protocol sharing. Wearable integrations. Still avoid ADHD/supplements until clinician model is operational.

14\. Key Risks & Mitigations

  ------------------------------------------------- --------------- ---------------------------------------------------------------------------------------------------------------
  **Risk**                                          **Severity**    **Mitigation**

  Users won't complete multi-week protocols         High            Under-20s check-in; progress gamification; concierge pilot to validate before building

  Claims creep under growth pressure                Critical        Protocol lock is architectural, not optional; legal review on all public-facing copy

  FDA/FTC enforcement action                        High            Green-only wedge; no disease claims; no supplement templates; regulatory counsel on retainer

  Privacy breach / consumer data scandal            Critical        No analytics pixels; local storage in v1; CCPA/WA MHMD compliant architecture

  Research ingestion generates unsafe protocols     High            Red-tier blocking; human review for edge cases; safety classification validated against expert panel

  Users misinterpret results as medical advice      Medium          Persistent caveats; quality grades; comprehension testing in pilot; no disease framing

  Low perceived value of \"inconclusive\" results   Medium          Frame inconclusive as valuable (\"you saved money/time\"); educational content on why uncertainty is honest

  Incumbents add experimentation features           Medium          Depth advantage: protocol lock + randomization + analysis is hard to bolt on; move fast on ingestion pipeline
  ------------------------------------------------- --------------- ---------------------------------------------------------------------------------------------------------------

15\. Open Questions

10. What is the minimum adherence and data density needed for \"decision-useful\" personal inference in beauty/skincare outcomes?

11. Can we communicate uncertainty well enough that users don't treat every positive result as conclusive proof?

12. Will the beauty/skincare wedge prove that structured experimentation has enough perceived value to expand to harder health domains?

13. How should the research ingestion pipeline handle conflicting studies (e.g., two PDFs with opposite conclusions about an ingredient)?

14. What is the right threshold for showing pooled results --- minimum number of aligned protocols, minimum mean quality grade?

15. Can buddy blinding be made easy enough that a meaningful fraction of users actually do it?

16. How do we prevent the community layer (v2+) from creating \"protocol hacking\" where users game shared experiments?

17. What is the IRB pathway for transitioning from private tool to opt-in research registry without a pause in operations?

18. Should the AI ingestion pipeline attempt to assess risk of drug interactions when users upload supplement research, or simply block all ingestible protocols?

19. What is the right business model that doesn't create conflicts with scientific integrity (e.g., brand-sponsored trials)?

Appendix A: Competitive Landscape Summary

  ----------------- ------------------------------------- --------------------------------------------------- -------------------------------------------------------
  **Competitor**    **Strength**                          **Weakness vs PitGPT**                              **Lesson**

  Bearable          Habit-forming tracking UX             Observational only; no randomization                Great UX can mislead without causal guardrails

  PatientsLikeMe    Structured patient data + community   Not designed for within-person causal inference     Publishing \"what works\" invites scrutiny

  StudyU            Open-source N-of-1 design             Not a consumer product; no distribution             Methods are sound; UX is the bottleneck

  Radicle Science   Blinded RCTs for brands               Brand-sponsored; not consumer-initiated             Independence is a differentiator if real

  Oura / Whoop      Biometric data + habit loops          No intervention adjudication                        Data ingestion moat is real; integrate, don't compete

  Guava             Correlation-based insights            Explicitly emphasizes correlations, not causation   \"Find triggers\" UX encourages over-interpretation
  ----------------- ------------------------------------- --------------------------------------------------- -------------------------------------------------------

Appendix B: N-of-1 Trial Suitability Rubric

Each dimension is scored 1--5 (higher = better for consumer N-of-1). Used by the safety classification engine to evaluate user-submitted protocols:

- Intervention risk (5 = very low/common consumer use; 1 = meaningful medical risk)

- Reversibility (5 = reversible within days; 1 = not reversible)

- Onset time (5 = hours--days; 1 = weeks--months)

- Washout feasibility (5 = easy/short; 1 = unclear/long)

- Blinding feasibility (5 = easy; 1 = impossible)

- Outcome measurability (5 = objective or validated simple scale; 1 = vague)

- User burden (5 = minimal; 1 = high daily friction)

- Confounding susceptibility (5 = low; 1 = high)

- Expected effect size vs noise (5 = moderate/large; 1 = small)

- Regulatory sensitivity (5 = low; 1 = high)

**END OF DOCUMENT**
