from model_gen_function import generate_model_from_csv
from model_simulation_function import total_load_calculation

def batch_simulation(path_for_csv_inputs, raws, path_to_epw, energyplus_path, simulation_folder, cop):
    batch_results = []
    for raw in raws:
        model, inputs = generate_model_from_csv(path_for_csv_inputs, raw)
        identifier, result = total_load_calculation(model, path_to_epw, energyplus_path, simulation_folder, cop)
        result = [identifier] + inputs + [round(load,4) for load in result]
        batch_results.append(result)
    return batch_results