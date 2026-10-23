# Reviewer comments: Access-2026-45322

Source: the author pasted the complete decision email into this Codex conversation
on 2026-10-19. Letter date: 15-Oct-2026; received: 16-Oct-2026. This is a
transcription of the 23 numbered technical comments, with line wrapping
normalised. It is not an independently downloaded email or a submitted response.
Private email addresses and portal tokens are omitted.

Manuscript: **Tri-Level Hybrid DDQN-ALNS: A Hierarchical Learning-Augmented
Metaheuristic for the Vehicle Routing Problem with Time Windows**.

The editor's letter rejects the current version and encourages resubmission,
allows one resubmission opportunity, and asks for:

1. A response covering each concern, the author's response and the remedial action.
2. A highlighted PDF showing every change, including grammatical changes.
3. Clean manuscript source (Word or LaTeX) and PDF.

The byline-change form applies if authorship changes; no such change is requested.
No submission deadline is specified in the supplied letter. The three attachment
names are recorded in the email, but their contents were not supplied with this
reply and are not certified by this transcription. The additional questionnaire
answers are not counted as extra numbered technical comments.

## Reviewer 1

### R1.1

Please make equal-compute evaluation the primary basis for the performance claims. The main 74-instance results use the same iteration budget, yet the proposed solver has approximately 1.5×–4× greater per-iteration cost because of online neural updates and set-partitioning solves. The limited 300-second anytime study shows that this distinction materially affects convergence behavior. Please extend the equal wall-clock evaluation across the full benchmark suite, or at least across a substantially larger stratified subset of Solomon-100, Homberger-200, and Homberger-400 instances. Report lexicographic performance at matched wall-clock budgets such as 10 s, 60 s, 300 s, and a longer operational horizon.

### R1.2

Please strengthen the baseline set with directly reproduced contemporary methods. The current controlled experiments primarily compare against ALNS-Base, whereas HGS, SISR, neural LNS, and related methods appear mainly as literature-context rows based on published results. At least one strong modern classical VRPTW solver and one learning-augmented routing method should be evaluated under the same hardware, initialization, stopping criterion, and seed protocol. Otherwise, the claims should be restricted to improvement over the implemented ALNS baseline.

### R1.3

Please disentangle the contribution of learning from that of stronger heuristic machinery. The constructive contribution ladder indicates that adding GEC and set-partitioning to ALNS already produces a statistically significant improvement, whereas several learning-component ablations are individually non-significant at the current seed count. Please revise the interpretation so that the total gain is not attributed predominantly to the DDQN hierarchy. A wall-clock-matched factorial ablation separating GEC, route-pool recombination, macro DDQN, micro DDQN, LAC, and GNN guidance would substantially strengthen the causal argument.

### R1.4

Please remove or rigorously prove the claim that the LAC acceptance override preserves classical Simulated Annealing asymptotic convergence guarantees. The disjunctive rule accepts all SA-approved moves but also accepts additional moves that SA rejects, thereby changing the transition kernel. This alone does not establish preservation of the classical convergence theorem. A formal proof under explicit conditions is required; otherwise, the claim should be limited to the experimentally supported statement that LAC preserves SA-approved moves while introducing additional predictive rescue transitions.

### R1.5

Please clarify the statistical hierarchy and incorporate seed-level uncertainty more explicitly. State exactly whether the fleet win/tie/loss counts and Wilcoxon tests are computed from per-instance means, medians, or best-of-five outcomes. Since each benchmark instance contains five paired stochastic runs, consider a hierarchical bootstrap or paired resampling procedure over instances and seeds. The fleet-matched distance analysis should remain explicitly conditional rather than being interpreted as an unconditional improvement.

### R1.6

Please moderate claims regarding GNN guidance and lexicographic guarantees. The GNN pruning module is computationally attractive, but its recall declines substantially at 400 customers and its incremental contribution is not consistently significant. Similarly, the scalarization and set-partitioning penalty guarantees establish lexicographic ordering within the candidate/route-pool space, not global optimality of the original VRPTW. The manuscript should make these scopes explicit to avoid overstatement.

## Reviewer 2

### R2.1

Most components are existing techniques, and the method seems mainly an incremental combination. What is the fundamental innovation?

### R2.2

Does the aggregated SMDP satisfy the Markov property? Can the authors provide convergence guarantees or approximation error bounds?

### R2.3

The learned acceptance criterion modifies Simulated Annealing. Does it still preserve the classical convergence guarantees?

### R2.4

The ablation results are not fully convincing. In Table 8, the heuristic-only A1 achieves better average distance than the full A4. How can the authors justify the additional learning components?

### R2.5

GNN edge recall drops from 95.8% to 78.2% as problem size increases. How does this affect solution quality and generalization to larger problems?

## Reviewer 3

### R3.1

A clear explanation of the novelty of the proposed Tri-Level Hybrid DDQN-ALNS framework compared with existing learning-guided ALNS methods is needed, highlighting its specific contributions beyond combining established optimization techniques.

### R3.2

A comprehensive ablation study is required to evaluate the individual contributions of the plateau controller, DDQN-based operator selection, learned acceptance criterion, GNN-based pruning, generalized ejection chains, and set partitioning recombination.

### R3.3

A fair comparison with established VRPTW algorithms under consistent computational budgets, stopping criteria, hardware configurations, and parameter-tuning conditions is necessary to validate the reported improvements.

### R3.4

A detailed explanation of the training and testing protocol is needed to establish whether the learned controllers generalize to unseen benchmark instances with different customer distributions, time-window constraints, and problem sizes.

### R3.5

Further clarification is needed on how the Learned Acceptance Criterion is trained using delayed outcomes over the 80-step horizon and how its performance compares with standard Simulated Annealing acceptance and other relevant strategies.

### R3.6

An evaluation of the impact of GNN-based candidate pruning on solution quality is needed, particularly regarding the risk of eliminating promising customer-insertion options.

### R3.7

The claimed \(O(1)\) insertion-feasibility checking complexity requires further justification, including the underlying data structures, assumptions, and conditions under which constant-time execution is achieved.

### R3.8

A detailed analysis of the total computational cost of the framework, including DDQN inference, GNN prediction, Generalized Ejection Chains, and Set Partitioning, is necessary to establish its practical efficiency.

### R3.9

A clear explanation of how the hierarchical objective is enforced throughout the search is needed to ensure that reducing travel distance never takes precedence over minimizing the number of vehicles.

### R3.10

Additional statistical evidence, including variability across independent runs and appropriate significance testing, is needed to establish the reliability of the reported improvements over baseline methods.

### R3.11

A detailed explanation of how feasibility is maintained after complex route modifications and Set Partitioning recombination is needed to substantiate the reported 100% operational constraint feasibility.

### R3.12

Further analysis is needed to distinguish the contributions of the proposed learning mechanisms from those of established optimization techniques, particularly generalized ejection chains and set partitioning.
