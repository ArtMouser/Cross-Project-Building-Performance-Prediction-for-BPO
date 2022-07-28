from multiprocessing import Pool
import math
import csv
import time
import subprocess

from batch_simulation_function import batch_simulation

if __name__ == '__main__':

    # SETTINGS
    start_row = 2             # first row in csv file with input parameters for simulation
    end_row = 2000              # last row in csv file with input parameters for simulation
    raws_in_batch = 3         # number of models to be sent to each worker at a time
    nb_process = 10           # number of workers
    chunk_size = 500          # number of simulations to be written to output csv file at a time (Data loss prevention)

    # PATHS
    path_for_csv_inputs = 'resources\inputs.csv' 
    path_for_csv_outputs = 'outputs/results.csv'
    path_to_epw = 'resources\ISR_Beer.Sheva.401900_MSI\ISR_Beer.Sheva.401900_MSI.epw'
    energyplus_path = None    # None = C:\EnergyPlusV**-*-*
    simulation_folder = "simulation"
    cop = 3

    # Create groups of ranges representing input CSV row numbers spited in batches and chunks
    ranges = []
    for i in range(math.floor((end_row-start_row)/raws_in_batch)):
        ranges.append(range(i * raws_in_batch + start_row, (i + 1) * raws_in_batch + start_row))
    ranges.append(range(math.floor((end_row-start_row)/raws_in_batch) * raws_in_batch + start_row, end_row + 1))
    ranges = [ranges[i:i+math.floor(chunk_size/raws_in_batch)] for i in range(0, len(ranges), math.floor(chunk_size/raws_in_batch))]

    t = time.time()
    for range in ranges:
        # Open CSV for outputs
        results_csv = open(path_for_csv_outputs, "a", newline='')

        # Start Multiprocessing
        p = Pool(nb_process)
        batched_results = p.starmap(batch_simulation, [(path_for_csv_inputs, raws, path_to_epw, energyplus_path, simulation_folder, cop) for raws in range])
        p.close()
        p.join()

        # Flatten results
        results = []
        for batch in batched_results:
            for result in batch:
                results.append(result)

        # Write results to CSV
        writer = csv.writer(results_csv)
        for result in results:
            writer.writerow(result)
        results_csv.close()

    t=time.time()-t
    print("Total time spent: " + str(t))

