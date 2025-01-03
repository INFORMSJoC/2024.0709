![INFORMS Journal on Computing Logo](https://INFORMSJoC.github.io/logos/INFORMS_Journal_on_Computing_Header.jpg)

# Non-monotonicity of Branching Rules with Respect to Linear Relaxations

This project is distributed in association with the [INFORMS Journal on
Computing](https://pubsonline.informs.org/journal/ijoc) under the [MIT License](LICENSE).

% The software and data in this repository are associated with the paper [Non-monotonicity of Branching Rules with Respect to Linear Relaxations](https://doi.org/10.1287/ijoc.2024.0709) by Prachi Shah, Santanu S. Dey and Marco Molinaro.


## Cite

To cite the contents of this repository, please cite both the paper and this repo, using their respective DOIs.

https://doi.org/10.1287/ijoc.2024.0709

https://doi.org/10.1287/ijoc.2024.0709.cd

Below is the BibTex for citing this snapshot of the repository.

```
@misc{Shah2025,
  author =        {Shah, Prachi and Dey, Santanu S and Molinaro, Marco},
  publisher =     {INFORMS Journal on Computing},
  title =         {Non-monotonicity of Branching Rules with Respect to Linear Relaxations},
  year =          {2025},
  doi =           {10.1287/ijoc.2024.0709},
  url =           {https://github.com/INFORMSJoC/2024.0709},
  note =          {Available for download at \url{https://github.com/INFORMSJoC/2024.0709}},
}
```
## Description

The goal of this software is to computationally ascertain how common it is for the strong branching rule to exhibit non-monotonicity in practice.  We do so by applying cover cuts on randomly generated multi-dimensional knapsacks as well as by considering cuts applied by [SCIP](https://www.scipopt.org/) on [MIPLIB 2017 benchmark set](https://miplib.zib.de/tag_benchmark.html). Our main insight from these experiments is that if the gap closed by cuts is small, change in tree size is difficult to predict, and often increases, possibly due to inherent non-monotonicity. However, when a sufficiently large gap is closed, a significant decrease in tree size may be expected. 


## Replicating

### Prerequisites

- Python 3
- [SCIP](https://www.scipopt.org/)
- [Gurobi](https://www.gurobi.com/)
- Required Python Libraries: pyscipopt, gurobipy, pandas, numpy, matplotlib, scipy

To replicate the results pertaining to Cover Cuts for Multi-dimensional Knapsack Problem (MKP):

```
python scripts/MultiKnapsack/run_multiknapsack_expt.py
```

To replicate the results on MIPLIB Benchmark Set, do 
```
python scripts/MIPLIB/run_miplib_expt.py
```
Alternately, considering the long time duration of this experiment, the following can be run in parallel for all combinations of instances, seeds and rounds 
```
python scripts/MIPLIB/get_scip_cuts.py <instance> <seed> <cut_rounds>
```
followed by, 
```
python scripts/MIPLIB/solve_mips.py <instance> <seed> <cut_rounds>
```
and to plot the results,
```
python scripts/MIPLIB/plot_results.py
```


