import subprocess
import pandas as pd


# MIPLIB Benchmark instances
instance_dir = f"data/miplibFiles/"

# filter instances based on ease of solving and number of variables
csv_file = f"{instance_dir}TheBenchmarkSet.csv"
miplib_df = pd.read_csv(csv_file)
miplib_df = miplib_df[
    (miplib_df['Status  Sta.'] == "easy") &
    (miplib_df['Integers  Int.'] + miplib_df['Binaries  Bin.'] <= 500) &
    (miplib_df['Variables  Var.'] <= 10000) &
    (miplib_df['Objective  Obj.'] != 'Infeasible')
    ][['Instance  Ins.', 'Objective  Obj.']]

miplib_df.set_index('Instance  Ins.', inplace=True)
miplib_df['Objective  Obj.'] = pd.to_numeric(miplib_df['Objective  Obj.'])


# iterate through all instances
for instance, row in miplib_df.iterrows():

    # Repeat for 3 seeds and upto 10 rounds of cuts
    for seed in range(1, 4):
        for cut_rounds in range(1, 11):

            arguments = [instance, str(seed), str(cut_rounds)]

            for script_path in ["scripts/MIPLIB/get_scip_cuts.py", "scripts/MIPLIB/solve_mips.py"]: # add cuts and then solve

                # Create command
                command = ["python", script_path] + arguments

                # Run the script
                result = subprocess.run(command, capture_output=True, text=True)

            # Output the results
            print(f"Args: {instance}, {seed}, {cut_rounds}")
            print("Output:", result.stdout)
            print("Errors:", result.stderr)


# Generate plots

result = subprocess.run(["python", "plot_results.py"], capture_output=True, text=True)
print(f"Plotting results")
print("Output:", result.stdout)
print("Errors:", result.stderr)
