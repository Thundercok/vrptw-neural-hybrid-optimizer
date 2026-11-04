"""Fill the IEEE response template: cover page and 23 concern blocks. Usage: build_response.py decision.txt unpacked/"""
import re
import sys
from pathlib import Path
from xml.sax.saxutils import escape

decision, unpacked = Path(sys.argv[1]), Path(sys.argv[2])
doc = unpacked / "word/document.xml"
xml = doc.read_text(encoding="utf8")

# ---- Concerns, verbatim from the decision letter ----
lines = decision.read_text(encoding="utf8").splitlines()
noise = re.compile(r"^(https://mail\.google|\d+/\d+/\d+, .*Gmail)")


def concerns(after, count):
    start = next(i for i, l in enumerate(lines) if l.startswith(after)) + 1
    items, cur = [], None
    for l in lines[start:]:
        if noise.match(l):
            continue
        if l.startswith("Additional Questions"):
            break
        m = re.match(r"^(\d+)\. (.*)", l)
        if m and int(m.group(1)) == len(items) + (1 if cur is None else 2):
            if cur is not None:
                items.append(cur)
            cur = m.group(2)
        elif cur is not None:
            cur = cur + l if cur.endswith("-") else cur + " " + l
    items.append(cur)
    assert len(items) == count, (after, len(items))
    return [i.replace(r"\(O(1)\)", "O(1)") for i in items]


R1 = concerns("Reviewer: 1", 6)
R2 = concerns("Reviewer: 2", 5)
R3 = concerns("Reviewer: 3", 12)

# ---- Answers ----
A = {}
A[1, 1] = (
    "We agree, and iteration budgets are no longer the basis of any claim. The evaluation now covers the full suite of 74 instances (56 Solomon-100, 12 Homberger-200, 6 Homberger-400) with five seeds at matched wall-clock budgets of 10, 60, 300 and 900 s, with 300 s as the primary budget. Construction, model inference, search, compilation after the start, and certification are charged to each solver's budget. An incumbent counts only if a supervisor process has received and validated it before the cutoff. While doing this work we also found that a wall-clock budget does not fix the compute a run receives: on 18 instances at 60 s, cells of our first full sweep took a median of 2.3 times as long as the same cells on a later night. The reported results therefore come from a rerun in which all cases of an instance, seed and cutoff run as one block, and a block interrupted by machine sleep runs again. [PENDING: state whether the 900 s stage was completed, and the number of blocks rerun.]",
    "We removed the iteration-budget tables and the anytime subset, and added the sections \"Comparison at 300 s\" and \"Effect of the Time Budget\". The setup section describes the budget accounting and the machine-speed variation.",
)
A[1, 2] = (
    "We agree. We now run PyVRP 0.14.1 (its iterated local search) as a modern classical solver and an adapted NeuroLKH as a learning-augmented method, on the same machine, with the same seeds, budgets, supervisor and blocks as our solver. Two limits apply. Each solver keeps its own construction procedure, charged to its budget, so initialization is not identical. PyVRP-ILS is not HGS, and NeuroLKH-adapted is an adaptation at a pinned commit with the pretrained CVRPTW checkpoint, not a replication of its authors' experiments. We did not run SISR or a neural LNS, and we removed the literature-context rows instead of comparing against published numbers. Our claims are restricted accordingly. In the first sweep at 300 s, the hybrid did not differ detectably from PyVRP-ILS on fleet size and used more vehicles than NeuroLKH-adapted. [PENDING: rerun result against each baseline at 300 s.]",
    "We added both baselines to the setup and results, removed the literature-context comparisons from the manuscript and the supplement, and restricted the abstract and conclusion to what the comparisons support.",
)
A[1, 3] = (
    "We agree, and we no longer attribute the total gain to the DDQN hierarchy. The LOCO table and the contribution ladder are replaced by a wall-clock factorial ablation on 18 instances with five seeds at 60 and 300 s. It covers GEC, route-pool recombination, macro DDQN, micro DDQN, LAC and GNN guidance in an anchored design of 16 cases plus a 2x2 contrast of the learning and heuristic bundles. It is not a full 2^6 factorial. Low levels are defined explicitly: for example, the macro and micro DDQNs are replaced by rule-based policies, not simply removed. In the first sweep, no primary contrast excluded zero on fleet size at 300 s after Bonferroni correction. Evidence for learned control appeared on unadjusted intervals, mainly at 60 s, and is reported as descriptive. [PENDING: rerun factorial result.] We also state that the search includes classical Guided Ejection Search and tail phases that do not involve learning.",
    "We replaced the LOCO and ladder sections with the section \"Factorial Ablation\", rewrote the discussion and contributions, and added the first-sweep ablation to the section \"Record of the First Sweep\".",
)
A[1, 4] = (
    "We agree, and the claim is removed. The rule accepts every SA-approved move and adds rescue transitions that SA rejects, so it defines a different transition kernel, and the classical result does not carry over. The search also uses geometric cooling within a finite budget. We make no convergence claim and state only that LAC keeps SA-approved moves among the moves it decides on and adds predictive rescue transitions. We also state that LAC is not consulted during penalized search phases.",
    "We rewrote the LAC section and Design Principle 2, and rescoped the supplement.",
)
A[1, 5] = (
    "The previous win/tie/loss counts and Wilcoxon tests were computed from per-instance means over five seeds. They are withdrawn, including the figures 23/49/2 and p = 1.70e-5. The unit is now the seed pair within an instance. The fleet score is +1, 0 or -1 for each pair, combined with fixed size weights. Uncertainty comes from a bootstrap of 10,000 replicates that resamples the seeds and, within each size, the groups of instances sharing customer geometry. Bonferroni corrections apply within declared families. There are four geometry groups per size, so the intervals are coarse, and we say so. The distance gap uses only seed pairs with matched fleet size and is described as conditional. Intervals that are undefined because a replicate has no matched pair are reported as undefined.",
    "We added the section \"Statistical Analysis\" and removed all previous tests.",
)
A[1, 6] = (
    "We agree. We withdrew the previous recall figures and the pruning figures of 97.5-98.74% because we could not trace them to the registered checkpoint. Recall is now reported on validation data against heuristic teacher edges, and is described as optimistic and as agreement with heuristic labels. Use at 400 customers is stated to be an extrapolation. The effect of the GNN on solutions rests only on the factorial contrasts, and in the first sweep its contrast at 300 s did not exclude zero (fleet score -0.033, interval [-0.169, 0.145]). [PENDING: rerun contrast.] The set-partitioning penalty bound is now stated for an optimal solution of the model over the columns that enter it, with no claim of global optimality, and the supplement states that the time limit and the smaller penalty scales fall outside it.",
    "We rewrote the GNN paragraph, the contributions, the architecture figure, Property 2 and Section 1 of the supplement.",
)
A[2, 1] = (
    "We agree that most components are existing techniques, and we do not claim a fundamentally new search principle. The contribution we claim is narrower. First, we specify a control layer for ALNS whose macro controller, micro controller and acceptance model learn online from random weights in every run, with no offline policy training. Second, we measure whether such control pays for its compute, under equal wall-clock budgets against ALNS-Base and two contemporary solvers with certified incumbents. Third, we separate learning from heuristic machinery with a factorial ablation and report where the method does not help. [PENDING: one sentence on what the rerun shows this contribution amounts to.]",
    "We rewrote the abstract, the contributions list and the positioning paragraph accordingly.",
)
A[2, 2] = (
    "No. The 12 macro features are a lossy summary of the search state, which also includes the routes, the route pool, operator weights, network parameters and random-number state. Distinct search states share an observation, so the macro process need not be Markov. We provide no convergence guarantee and no approximation error bound. Such guarantees are not available in general for Q-learning over aggregated observations, and our controller also uses nonlinear function approximation, replay and target networks. The Bellman contraction in the supplement holds only for a finite MDP and establishes only that Q* is well defined.",
    "We rewrote the macro section to describe the controller as a learned policy over a partially observed, state-aggregated process, and rescoped Section 2 of the supplement.",
)
A[2, 3] = (
    "No, and we no longer claim it. See Reviewer 1, Concern 4. The rule adds transitions that SA rejects, so the classical result does not carry over, and we make no convergence claim.",
    "We removed the claim from the LAC section, Design Principle 2 and the supplement.",
)
A[2, 4] = (
    "That table used iteration budgets and is removed. We do not claim that learning justifies itself at every budget. In the first sweep's wall-clock factorial, adding the learning bundle to the heuristic bundle did not exclude zero at 300 s (fleet score +0.067, interval [-0.187, 0.322]). It did at 60 s on an unadjusted interval (+0.189, [0.067, 0.363]). [PENDING: rerun result, and a plain statement of whether the learning components are justified at each budget.]",
    "We removed Table 8 and the ladder, and report the bundle contrasts in the section \"Factorial Ablation\".",
)
A[2, 5] = (
    "The figures 95.8%, 91.4% and 78.2% are withdrawn because we could not trace them to the registered checkpoint. For that checkpoint, validation recall against heuristic teacher edges at threshold 0.01 is 100% at 100 customers and 99.85% at 200, retaining about 29% of candidate arcs. These instances also selected the checkpoint, so the figures are optimistic. The model was trained only at 100 and 200 customers, so use at 400 is an extrapolation, and we do not claim generalization to larger problems. [PENDING: recall at 400 customers and on benchmark sizes, and the GNN contrast by size.]",
    "We rewrote the GNN paragraph and added the scale shift to the limitations.",
)
A[3, 1] = (
    "See Reviewer 2, Concern 1. Compared with learning-guided ALNS methods, the specific features of this framework are the separation of a macro plateau controller from a micro operator controller, and an acceptance model added to SA, all learned online from random weights within one run. We do not claim that these features make the method better than those methods, which we did not run. We claim what the wall-clock comparison and factorial ablation measure. [PENDING: summary of that measurement.]",
    "We rewrote the contributions list and the positioning paragraph.",
)
A[3, 2] = (
    "See Reviewer 1, Concern 3. The factorial covers all six components you list: plateau controller (Macro), DDQN operator selection (Micro), learned acceptance (LAC), GNN guidance (GNN), generalized ejection chains (GEC) and set-partitioning recombination (SP). Each is contrasted in the full configuration and, as an exploratory analysis, in the bare configuration. In the first sweep at 300 s and 99.38% intervals, the full-configuration fleet scores were: GEC +0.033, SP -0.108, Macro +0.011, Micro +0.089, LAC -0.033, GNN -0.033. All of these intervals include zero. [PENDING: rerun values.]",
    "We added the section \"Factorial Ablation\".",
)
A[3, 3] = (
    "All cases now share one machine, budget, stopping rule (wall clock), seed set, supervisor and block structure. We did not tune the baselines for these budgets. Several conditions need disclosure, and the manuscript states them. (i) In the first sweep our hybrid read the best-known fleet size during search and the baselines did not; every lookup is disabled in the rerun. (ii) One rule of our solver uses the RC prefix in the instance name, and it remains in the code. (iii) The hand-set values of our solver have no retained calibration log. (iv) Test results motivated the Guided Ejection Search phase. Its parameters were chosen on 30 development instances that share customer coordinates with test instances, and the rule for adopting it was fixed before a single rerun. (v) The previous description of ALNS-Base was wrong. It is our own implementation with Thompson-sampling selection, not a reproduction of the original method. (vi) Machine speed varied between blocks. [PENDING: outcome of the adoption rule and the load sensitivity result.]",
    "We rewrote the setup section, including the sections on reference-fleet information and the experimental firewall, and corrected the ALNS-Base description.",
)
A[3, 4] = (
    "The macro DDQN, micro DDQN and LAC have no offline phase. They start from random weights in every run and learn online within that run's budget, so they have no train/test split, nothing is carried between runs, and we make no claim that a learned policy transfers between instances. Only the GNN is trained offline, on 48 synthetic instances with 12 for validation at 100 and 200 customers, and then frozen. No benchmark test instance was used to train or select it. We did not run a transfer experiment across distributions, time-window structures or sizes, so we do not claim such generalization. The instances of each family and size are reported separately instead.",
    "We added the paragraph \"Training and testing protocol\" to the setup section.",
)
A[3, 5] = (
    "LAC is consulted only for feasible candidates that keep the fleet and increase distance, outside penalized search phases. The first 300 consulted decisions use SA alone while their features are queued. After 80 further consulted decisions, a decision is labeled 1 if the best distance has decreased since it was made, and 0 otherwise. Every 20 consulted decisions, the network trains on a batch of 64 from a buffer of 5,000 with class-weighted binary cross-entropy. The labels are observational and non-stationary, and they follow distance, not the lexicographic objective. We compare LAC only with SA, through the factorial contrast, and did not evaluate other acceptance strategies. In the first sweep at 300 s the contrast did not exclude zero (fleet score -0.033, interval [-0.229, 0.137]). Because the first phase can take most of the main loop at this budget, LAC may act little at 300 s. [PENDING: rerun contrast and how often LAC was consulted and rescued moves.]",
    "We rewrote the LAC section, its feature vector and its training description to match the code.",
)
A[3, 6] = (
    "The GNN heatmap biases insertion costs and filters insertion positions, so promising options can be lost. On validation data at threshold 0.01, 2 of 2,005 teacher edges were lost. Teacher edges come from a heuristic, so this does not bound the loss of useful arcs. The effect on solutions is measured by the GNN contrast, which in the first sweep at 300 s did not exclude zero in either direction (full configuration, fleet score -0.033, interval [-0.169, 0.145]). The data therefore show neither a clear benefit nor a clear harm. [PENDING: rerun contrast and benchmark recall.]",
    "We rewrote the GNN paragraph and report the contrast in the section \"Factorial Ablation\".",
)
A[3, 7] = (
    "Constant time applies only to one insertion query against a cached route profile, which holds arrival times, load, and the forward slack or, equivalently, the latest feasible arrival at each position. The profile must be valid; refreshing it costs O(m) after each change to a route of length m. Scanning all positions of one route is O(m), and evaluating one customer against K routes is O(Km) before granular restriction. Moves that reverse or relocate a segment recompute times along it. The ejection chain does not use these queries and replays routes at linear cost. We claim no O(1) bound for a move or an iteration. In this audit we also corrected the feasibility condition, which ignored waiting at the next node. The exact condition is max(0, delta - W_(i+1)) <= F_(i+1).",
    "We rewrote the insertion-check section, corrected its equations, and rewrote Sections 3 and 4 of the supplement.",
)
A[3, 8] = (
    "[PENDING: measured time per component (DDQN inference and updates, GNN prediction, ejection chains, set partitioning, certification) from a phase trace on a representative subset, and iterations per second by size for each solver.] Practical efficiency is assessed through the wall-clock comparisons, where all of this cost is charged to the budget. The previous figures of 1.5x-4x slowdown and 17.8% and 8.1% overhead are withdrawn because we could not trace them.",
    "We added the section \"Computational Cost\" and removed the earlier overhead claims.",
)
A[3, 9] = (
    "The objective is enforced at the level of the best solution, not at every move. A candidate replaces the best solution only if it has fewer vehicles, or the same number and strictly lower distance, after validation in the original instance. The reported solution is therefore non-increasing in fleet size over time, and it never trades a vehicle for distance. Intermediate states do not all respect the order: the current solution may take one extra vehicle in the DIVERSIFY mode, and penalized phases may visit infeasible states. Set partitioning uses a certified penalty only at its largest scale, with a guarantee only within the model's columns. The controllers receive scalarized rewards, and LAC labels follow distance. These affect search behavior but not the update of the best solution.",
    "We rewrote the set-partitioning and objective paragraphs, and stated these scopes in the macro section and in the discussion.",
)
A[3, 10] = (
    "See Reviewer 1, Concern 5. Results are reported at seed-pair level with win/tie/loss counts, bootstrap intervals over seeds and geometry groups, and declared multiplicity families. [PENDING: per-family variability from the rerun and per-instance tables in Section 8 of the supplement.]",
    "We added the section \"Statistical Analysis\" and rebuilt the per-instance tables from the rerun.",
)
A[3, 11] = (
    "We replace the blanket claim of 100% feasibility with a verifiable procedure. During search, the current solution may be infeasible in penalized phases. A plan can become the best solution only after validation of exact cover, capacity and time windows. Set partitioning uses feasible pool routes and exact cover; when exact partitioning fails, a set-covering fallback removes duplicate customers and the result is validated. The supervisor validates each incumbent in the original problem space before the cutoff, and a separate script recomputes feasibility and distance from the stored routes. A cell without such an incumbent is reported as unavailable. This audit also found a defect: the greedy construction did not check the depot return deadline, so all 20 ALNS-Base runs on R1_2_5 failed. We fixed it and reran them. In the first sweep, 21 of 8,620 cells were lost to infrastructure failures, and we report bounds for them. [PENDING: the same counts for the rerun.]",
    "We rewrote the feasibility section and added the section \"Availability and Feasibility\".",
)
A[3, 12] = (
    "See Reviewer 1, Concern 3. In the first sweep at 300 s, adding the heuristic bundle without learning (fleet score +0.033, interval [-0.244, 0.191]) and adding the learning bundle to the heuristics (+0.067, [-0.187, 0.322]) both had intervals including zero, so the data do not separate them at this budget. Comparison with ALNS-Base does not isolate learning, because ALNS-Base lacks the heuristic components and the tail phases of the hybrid. In the rerun, Guided Ejection Search is a fixed classical layer, and any gain from it is not a gain from learning. [PENDING: rerun contrasts.]",
    "We report the bundle contrasts in the section \"Factorial Ablation\" and interpret them in the discussion.",
)

for key in ((1, i) for i in range(1, 7)):
    assert key in A
assert len(A) == 23

# ---- XML helpers: run properties copied from the template ----
FONT = '<w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/>'
SIZE = '<w:sz w:val="22"/><w:szCs w:val="22"/>'


def run(text, bold=False, color=None, highlight=False):
    props = FONT + ("<w:b/><w:bCs/>" if bold else "")
    props += f'<w:color w:val="{color}"/>' if color else ""
    props += SIZE
    props += '<w:highlight w:val="yellow"/>' if highlight else ""
    return f'<w:r><w:rPr>{props}</w:rPr><w:t xml:space="preserve">{escape(text)}</w:t></w:r>'


def runs(text):
    """Plain text with [PENDING: ...] markers highlighted so none can reach submission unnoticed."""
    out = []
    for part in re.split(r"(\[PENDING:[^\]]*\])", text):
        if part:
            out.append(run(part, highlight=part.startswith("[PENDING:")))
    return "".join(out)


def para(content, page_break=False):
    ppr = ("<w:pageBreakBefore/>" if page_break else "") + f'<w:jc w:val="both"/><w:rPr>{FONT}{SIZE}</w:rPr>'
    return f"<w:p><w:pPr>{ppr}</w:pPr>{content}</w:p>"


ps = re.findall(r"<w:p[ >].*?</w:p>", xml, flags=re.S)
RULE = next(p for p in ps if 'o:hr="t"' in p)
rule_count = [p for p in ps if 'o:hr="t"' in p]

blocks = []
first = True
for n, items in ((1, R1), (2, R2), (3, R3)):
    for i, text in enumerate(items, 1):
        response, action = A[n, i]
        head = run(f"Reviewer#{n}, Concern # {i}:", bold=True, color="008000") + run(f" {text}", color="008000")
        blocks.append(para(head, page_break=first))
        blocks.append(para(run("Author response: ", bold=True) + runs(response)))
        blocks.append(para(run("Author action: ", bold=True) + runs(action)))
        blocks.append(RULE)
        first = False

# ---- Cover page ----
corrections = [
    "Results based on iteration budgets, including 23/49/2 fleet wins and -1.80% matched distance, are withdrawn and replaced by wall-clock results.",
    "GNN recall of 95.8/91.4/78.2%, pruning of 97.5-98.74%, and overhead figures could not be traced to the registered checkpoint or to retained data, and are withdrawn.",
    "ALNS-Base was described as a faithful reproduction with a roulette wheel. It is our own implementation with Thompson-sampling selection.",
    "The method description differed from the code in the granular neighborhood, hyperparameter table, blending rule, macro modes, reward constants, LAC features and labels, ejection chains, set-partitioning limits and hardware. All are corrected to the code. The search phases, previously undescribed, are now stated.",
    "The two-stage set-partitioning theorem, the ejection-chain complexity proof and the forward-slack condition were wrong or did not describe the solver. They are removed or corrected.",
    "The sensitivity table, PCA table and literature-comparison table of the supplement could not be traced to source data and are withdrawn. A claim that hand-set constants were calibrated on synthetic pilot instances is withdrawn, because no calibration log exists.",
    "Our first sweep's hybrid read best-known fleet sizes during search, and test results motivated a new Guided Ejection Search phase. Both are disclosed, and the reported results come from a single rerun with its adoption rule fixed in advance.",
    "The previous repository link returned an error, and we know of no Zenodo archive, so that statement is corrected. [PENDING: final data availability statement after publishing the code, records, checkpoint and logs.]",
]


def set_runs(p, content):
    head = p[: p.index("</w:pPr>") + len("</w:pPr>")]
    return head + content + "</w:p>"


out = xml
id_para, title_para = ps[0], ps[1]
out = out.replace(id_para, set_runs(id_para, run("Original Manuscript ID:", bold=True) + run(" Access-2026-45322")), 1)
title = "Tri-Level Hybrid DDQN-ALNS: A Hierarchical Learning-Augmented Metaheuristic for the Vehicle Routing Problem with Time Windows"
out = out.replace(title_para, set_runs(title_para, run("Original Article Title:", bold=True) + run(f" “{title}”")), 1)
name_para = next(p for p in ps if "et al." in "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", p)))
out = out.replace(name_para, set_runs(name_para, run("Thi-Linh Ho et al.")), 1)

upload = ps[11]
intro = para(run("During this revision we audited the manuscript against our code and retained data, and found errors in the previous version that go beyond the reviewers' concerns. We list the main corrections here so that they are not overlooked. The point-by-point responses give the details."))
items = "".join(para(run(f"({i}) " + "") + runs(c)) for i, c in enumerate(corrections, 1))
blank = para("")
out = out.replace(upload, upload + blank + intro + blank + items, 1)

# Drop the spacer paragraphs after the signature, the sample blocks and the template's instruction note.
start = out.index(ps[30])
end = out.index(ps[-1]) + len(ps[-1])
sign_end = out.index(run("Thi-Linh Ho et al."))
sign_end = out.index("</w:p>", sign_end) + len("</w:p>")
out = out[:sign_end] + "".join(blocks) + out[end:]
doc.write_text(out, encoding="utf8")

import json  # noqa: E402

print(json.dumps({"blocks": len(blocks) // 4, "pending": sum(b.count("[PENDING:") for b in blocks), "chars": sum(len(a[0]) for a in A.values())}))
