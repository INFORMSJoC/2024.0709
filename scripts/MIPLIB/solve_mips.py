import sys
import pandas as pd
import pyscipopt as scip


def solve_mip(lpfile, objval, seed):

    scip_parameters = {
        "presolving/maxrounds": 0,
        "presolving/maxrestarts": 0,

        "propagating/maxrounds": 0,
        "propagating/maxroundsroot": 0,

        "separating/maxroundsroot": 0,
        "separating/maxcutsroot": 0,
        "separating/maxrounds": 0,
        "separating/maxcuts": 0,

        "conflict/enable": False,

        # "display/verblevel": 5,
        # "display/freq": 1,

        "branching/vanillafullstrong/priority": 536870911,
        "branching/vanillafullstrong/idempotent": True,
        "branching/vanillafullstrong/scoreall": True,

        # "limits/time": 3600,
        "limits/nodes": -1,
    }

    randomization_params = {
        "randomization/randomseedshift": 0,
        "randomization/permutationseed": 0,
        "randomization/lpseed": 0,
    }

    solve_model = scip.Model()
    for k in randomization_params.keys():
        randomization_params[k] = seed

    solve_model.setParams(scip_parameters)
    solve_model.setParams(randomization_params)

    solve_model.setPresolve(scip.SCIP_PARAMSETTING.OFF)
    solve_model.setHeuristics(scip.SCIP_PARAMSETTING.OFF)
    solve_model.disablePropagation()

    solve_model.readProblem(lpfile)
    solve_model.setObjlimit(float(objval))

    solve_model.optimize()
    return solve_model.getNTotalNodes(), solve_model.getNNodes()


def solve_lp(lpfile):
    solve_model = scip.Model()
    solve_model.readProblem(lpfile)

    for v in solve_model.getVars():
        solve_model.chgVarType(v, 'C')

    solve_model.optimize()
    return solve_model.getObjVal()


instance_dir = f"data/miplibFiles/"
csv_file = f"{instance_dir}TheBenchmarkSet.csv"
miplib_df = pd.read_csv(csv_file)
miplib_df.set_index('Instance  Ins.', inplace=True)

instance, seed, round = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])

if round == 0:
    lp_file = f"{instance_dir}{instance}.lp"
else:
    lp_file = f"{instance_dir}{instance}_seed{seed}_round{round}.lp"

rootlp = solve_lp(lp_file)
ntotalnodes, nnodes = solve_mip(lp_file, miplib_df.loc[instance, 'Objective  Obj.'], seed)

results_dir = f"results/MIPLIB/"
with open(f"{results_dir}results.txt", "a+") as f:
    print(f"{instance}, {seed}, {round}, {rootlp}, {ntotalnodes}, {nnodes}", end='\n', file=f)
