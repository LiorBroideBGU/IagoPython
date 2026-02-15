# Evaluation Plan: Negotiation Platform Dynamic Evaluation

## Overview

This experiment evaluates the platform's ability to produce diverse, meaningful results by running all pairings of five intuitively-understood agents — **Fair**, **Linear**, **Generous**, **Bargainer (Greedy)**, and **Tit-for-Tat (Reciprocal)** — across a systematic grid of configurations. The experiment varies the number of items, item quantities, and deadline pressure. Results are presented as figures and tables suitable for an academic paper, demonstrating that the platform captures expected behavioral differences and reveals insights across multiple dimensions.

---

## 1. Agent Definitions

### 1.1 Fair Agent
- **Behavior:** Proposes near-equal splits of items; accepts any offer within a small fairness threshold of the equal split.
- **Expected outcome:** Since it aims for equal splits, agreements should be reached quickly (few rounds) with high joint utility and high fairness. However, its individual utility will be lower when paired against aggressive agents that take advantage of its willingness to split evenly.

### 1.2 Linear Agent
- **Behavior:** Concedes at a constant, steady rate from its opening demand toward the midpoint, evenly spreading concessions across the available rounds.
- **Expected outcome:** Since it concedes gradually, the number of rounds to agreement should scale proportionally with the deadline. It should achieve moderate individual utility — better than Fair against aggressive opponents (because it doesn't give in immediately) but worse than Bargainer (because it keeps conceding). Fairness should be moderate.

### 1.3 Generous Agent
- **Behavior:** Prioritizes the opponent's satisfaction; proposes offers that favor the opponent, and accepts any offer that gives itself at least a minimal share.
- **Expected outcome:** Since it gives away value to please the opponent, agreements should be reached very quickly (fewest rounds of all agents), but its own individual utility will be the lowest overall. Against Bargainer, it should produce the most lopsided outcomes in the experiment. It should almost always reach agreement since it rarely rejects.

### 1.4 Bargainer (Greedy) Agent
- **Behavior:** Opens with extreme demands (claims most/all items); concedes very slowly over rounds, making only minimal concessions as the deadline approaches.
- **Expected outcome:** Since it bargains hard and concedes slowly, it should take the most rounds to reach agreement and is the most likely to fail to reach agreement (especially in self-play — two stubborn agents deadlock). When it does reach a deal, its individual utility should be the highest, particularly against Generous and Fair. Joint utility will suffer due to deadlocks.

### 1.5 Tit-for-Tat (Reciprocal) Agent
- **Behavior:** Starts with a cooperative (fair) opening offer. In subsequent rounds, mirrors the opponent's behavior — if the opponent conceded, TFT concedes similarly; if the opponent was aggressive, TFT becomes aggressive.
- **Expected outcome:** Since it adapts to the opponent, its results should vary the most across matchups. Against cooperative agents (Fair, Generous), it should converge quickly to fair outcomes. Against Bargainer, it should mirror the stubbornness, leading to longer negotiations and possible deadlock. Its overall utility should land in the middle — it avoids being exploited but doesn't exploit others either.

---

## 2. Agent Matchups

Run all pairings of the 5 agents (including self-play), with each agent taking a turn as the starter — yielding **25 runs per configuration** (5 × 5 ordered pairings).

| # | Agent A    | Agent B    | Expected Outcome |
|---|------------|------------|------------------|
| 1 | Fair       | Fair       | Quick agreement, equal split, high joint utility |
| 2 | Fair       | Linear     | Swift agreement — Linear concedes toward the fair split anyway |
| 3 | Fair       | Generous   | Very fast agreement — Generous gives more than Fair asks, slight asymmetry favoring Fair |
| 4 | Fair       | Bargainer  | Agreement likely but Bargainer exploits Fair — high utility asymmetry |
| 5 | Fair       | TFT        | Converges to cooperative outcome, similar to Fair vs Fair |
| 6 | Linear     | Linear     | Steady convergence, moderate rounds to agreement, balanced outcome |
| 7 | Linear     | Generous   | Quick agreement — Generous concedes faster than Linear, Linear gets slight edge |
| 8 | Linear     | Bargainer  | Linear concedes steadily while Bargainer holds — Bargainer gets more, risk of late or no deal |
| 9 | Linear     | TFT        | TFT mirrors Linear's steady concession — convergence to balanced deal |
| 10 | Generous  | Generous   | Immediate agreement — both rush to please; fair-ish but possibly below Pareto frontier |
| 11 | Generous  | Bargainer  | Bargainer heavily exploits Generous — highest asymmetry in the experiment |
| 12 | Generous  | TFT        | TFT mirrors generosity — cooperative outcome, fast agreement |
| 13 | Bargainer | Bargainer  | Deadlock expected, no agreement, longest negotiation |
| 14 | Bargainer | TFT        | TFT mirrors aggression — likely deadlock or late deal, lower joint utility |
| 15 | TFT       | TFT        | Cooperative convergence after initial mirroring phase |

---

## 3. Configuration Grid

Vary **one dimension at a time** from the baseline (controlled experiment).

### 3.1 Baseline Configuration
- **Number of item types:** 4
- **Item quantity per type:** 3–5
- **Deadline (max rounds):** 10
### 3.2 Configuration Variants

| Dimension              | Levels                                  | Purpose |
|------------------------|-----------------------------------------|---------|
| **Number of item types** | 2, 4 (baseline), 6                     | Does more item variety allow richer trade-offs and higher joint utility? |
| **Item quantity**       | Low (1–3 each), High (5–10 each)        | Does granularity (divisibility) change fairness and agreement rates? |
| **Deadline (rounds)**   | Short (5), Medium (10, baseline), Long (20) | Does time pressure change concession rates and deadlock frequency? |

### 3.3 Total Experiment Size
- **25 runs per configuration** (5 × 5 ordered pairings)
- **7 configurations** (1 baseline + 2 item-type variants + 2 item-quantity variants + 2 deadline variants)
- **25 × 7 = 175 total scenarios**
- **Each scenario is run once** (the system and all agents are fully deterministic — identical inputs always produce identical outputs)
- Report exact values per scenario

---

## 4. Metrics to Collect

For each run, record the following:

| Metric                  | Description |
|-------------------------|-------------|
| **Agreement** (yes/no)  | Whether the pair reaches a deal before the deadline |
| **Individual utility** (Agent A / Agent B) | Each agent's utility from the final deal (0 if no agreement) |
| **Joint utility** (sum) | Total value created — measures social welfare |
| **Fairness index**      | min(utility_A, utility_B) / max(utility_A, utility_B), or Nash product |
| **Rounds to agreement** | Number of rounds until deal is reached (max = deadline if no deal) |

---

## 5. Figures and Tables for the Paper

### Tables

#### Table 1 — Baseline Results Matrix
A 5×5 matrix (Fair, Linear, Generous, Bargainer, TFT on both axes) where rows represent the starter and columns the responder. Each cell shows:
- Agreement (yes/no)
- Starter utility / Responder utility
- Joint utility
- Fairness index

The full starter/responder breakdown is shown for transparency and completeness, but the paper's analysis and figures focus on per-pairing results (averaged across both start orders) rather than on first-mover effects.

**Purpose:** The headline result — shows that different agent pairings produce clearly different outcomes.

#### Table 2 — Per-Agent Average Utility
Each agent's individual utility averaged across all matchups and configurations. Summarizes which strategy is most rewarding overall.

### Figures

#### Figure 1 — Agreement by Matchup and Deadline
- **Type:** Grouped bar chart
- **X-axis:** Matchup (15 pairings, averaged over both start orders)
- **Bars:** Colored by deadline length (Short / Medium / Long)
- **Shows:** Which pairings reach agreement under different deadlines. Expected: Bargainer vs Bargainer fails under short deadlines.

#### Figure 2 — Joint Utility vs. Number of Items
- **Type:** Line plot
- **X-axis:** Number of item types (2, 4, 6)
- **Lines:** One per matchup (15 lines, or group by agent-type category for readability)
- **Shows:** Whether more items allow richer trade-offs. Expected: cooperative pairs benefit most from more items; Bargainer vs Bargainer sees little gain.

#### Figure 3 — Fairness Index by Matchup and Item Quantity
- **Type:** Grouped bar chart
- **X-axis:** Matchup (15 pairings, or a representative subset)
- **Bars:** Colored by item quantity level (Low / High)
- **Shows:** How item granularity affects fairness. Expected: higher quantities allow finer splits, improving fairness for cooperative pairings.

#### Figure 4 — Rounds-to-Agreement Heatmap
- **Type:** Heatmap
- **Rows:** Matchup (15 pairings)
- **Columns:** Deadline length (Short / Medium / Long)
- **Cell value:** Rounds to agreement (or "no deal")
- **Shows:** Negotiation efficiency across conditions.

#### Figure 5 — Individual Utility Bar Chart
- **Type:** Grouped bar chart
- **X-axis:** Matchup (15 pairings, or a representative subset)
- **Y-axis:** Individual utility
- **Shows:** Each agent's utility at baseline. Two bars per matchup (Agent A, Agent B).

---

## 7. Key Claims the Experiment Should Support

1. **Agent sensitivity:** Different agent strategies produce clearly different outcomes (utility, fairness, agreement), confirming the platform faithfully models strategic variation.
2. **Configuration sensitivity:** Varying item count, item quantities, and deadlines changes results in predictable, interpretable ways, showing the platform supports multi-dimensional scientific inquiry.

---
