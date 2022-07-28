import os
import subprocess
import json
import shutil

from ladybug.futil import write_to_file_by_name, nukedir
from ladybug.epw import EPW
from ladybug.sql import SQLiteResult
from ladybug.datacollection import MonthlyCollection
from ladybug.header import Header
from ladybug.analysisperiod import AnalysisPeriod
from ladybug.datatype.energyintensity import EnergyIntensity

from honeybee.config import Folders as folders
from honeybee.model import Model

from honeybee_energy.result.loadbalance import LoadBalance
from honeybee_energy.simulation.parameter import SimulationParameter
from honeybee_energy.run import run_idf
from honeybee_energy.result.err import Err
from honeybee_energy.writer import energyplus_idf_version
from honeybee_energy.config import Folders as energy_folders

from lbt_recipes.version import check_energyplus_version



def data_to_load_intensity(data_colls, floor_area, data_type, cop=1, mults=None):
  """Convert data collections output by EnergyPlus to a single load intensity collection.

  Args:
  data_colls: A list of monthly data collections for an energy term.
  floor_area: The total floor area of the rooms, used to compute EUI.
  data_type: Text for the data type of the collections (eg. "Cooling").
  cop: Optional number for the COP, which the results will be divided by.
  """
  if len(data_colls) != 0:
    if mults is not None:
      data_colls = [dat * mul for dat, mul in zip(data_colls, mults)]
    total_vals = [sum(month_vals) / floor_area for month_vals in zip(*data_colls)]
    if cop != 1:
      total_vals = [val / cop for val in total_vals]
  else:  # just make a "filler" collection of 0 values
    total_vals = [0] * 12
  meta_dat = {'type': data_type}
  total_head = Header(EnergyIntensity(), 'kWh/m2', AnalysisPeriod(), meta_dat)
  return MonthlyCollection(total_head, total_vals, range(12))


def serialize_data(data_dicts):
  """Reserialize a list of MonthlyCollection dictionaries."""
  return [MonthlyCollection.from_dict(data) for data in data_dicts]

def total_load_calculation(model, path_to_epw, energyplus_path, simulation_folder, cop):
  if energyplus_path:
    energy_folders.energyplus_path = energyplus_path
  folders.default_simulation_folder = simulation_folder

  _model = model
  _rooms = _model.rooms
  shades_ = _model.shades
  _epw_file = path_to_epw

  # List of all the output strings that will be requested
  cool_out = 'Zone Ideal Loads Supply Air Total Cooling Energy'
  heat_out = 'Zone Ideal Loads Supply Air Total Heating Energy'
  light_out = 'Zone Lights Electricity Energy'
  el_equip_out = 'Zone Electric Equipment Electricity Energy'
  gas_equip_out = 'Zone Gas Equipment NaturalGas Energy'
  process1_out = 'Zone Other Equipment Total Heating Energy'
  process2_out = 'Zone Other Equipment Lost Heat Energy'
  shw_out = 'Water Use Equipment Heating Energy'
  gl_el_equip_out = 'Zone Electric Equipment Total Heating Energy'
  gl_gas_equip_out = 'Zone Gas Equipment Total Heating Energy'
  gl1_shw_out = 'Water Use Equipment Zone Sensible Heat Gain Energy'
  gl2_shw_out = 'Water Use Equipment Zone Latent Gain Energy'
  energy_output = (cool_out, heat_out, light_out, el_equip_out, gas_equip_out, process1_out, process2_out, shw_out)

  _heat_cop_ = cop
  _cool_cop_ = cop

  floor_area = _model.floor_area
  assert floor_area != 0, 'Connected _rooms have no floors with which to compute EUI.'
  mults = [rm.multiplier for rm in _rooms]
  mults = None if all(mul == 1 for mul in mults) else mults

  # process the simulation folder name and the directory
  directory = os.path.join(folders.default_simulation_folder, _model.identifier)
  sch_directory = os.path.join(directory, 'schedules')
  nukedir(directory)  # delete any existing files in the directory

  # create simulation parameters for the coarsest/fastest E+ sim possible
  _sim_par_ = SimulationParameter()
  _sim_par_.timestep = 1
  _sim_par_.shadow_calculation.solar_distribution = 'FullExterior'
  _sim_par_.output.add_zone_energy_use()
  _sim_par_.output.reporting_frequency = 'Monthly'

  # assign design days from the EPW
  msg = None
  folder, epw_file_name = os.path.split(_epw_file)
  ddy_file = os.path.join(folder, epw_file_name.replace('.epw', '.ddy'))
  if os.path.isfile(ddy_file):
    try:
      _sim_par_.sizing_parameter.add_from_ddy_996_004(ddy_file)
    except AssertionError:
      msg = 'No design days were found in the .ddy file next to the _epw_file.'
  else:
    msg = 'No .ddy file was found next to the _epw_file.'
  if msg is not None:
    epw_obj = EPW(_epw_file)
    des_days = [epw_obj.approximate_design_day('WinterDesignDay'), epw_obj.approximate_design_day('SummerDesignDay')]
    _sim_par_.sizing_parameter.design_days = des_days
    msg = msg + 'Design days were generated from the input _epw_file but this is not as accurate as design days from DDYs distributed with the EPW.'
    print (msg)

  # create the strings for simulation paramters and model
  ver_str = energyplus_idf_version() #if energy_folders.energyplus_version is not None else energyplus_idf_version(compatibe_ep_version)
  sim_par_str = _sim_par_.to_idf()
  model_str = _model.to.idf(_model, schedule_directory=sch_directory, patch_missing_adjacencies=True)
  idf_str = '\n\n'.join([ver_str, sim_par_str, model_str])

  # write the final string into an IDF
  idf = os.path.join(directory, 'in.idf')
  write_to_file_by_name(directory, 'in.idf', idf_str, True)

  # run the IDF through EnergyPlus
  silent = True
  sql, zsz, rdd, html, err = run_idf(idf, _epw_file, silent=silent)
  if html is None and err is not None:  # something went wrong; parse the errors
    err_obj = Err(err)
    print(err_obj.file_contents)
    for error in err_obj.fatal_errors:
      raise Exception(error)

  # parse the result sql and get the monthly data collections
  if os.name == 'nt':  # we are on windows; use IronPython like usual
    sql_obj = SQLiteResult(sql)
    cool_init = sql_obj.data_collections_by_output_name(cool_out)
    heat_init = sql_obj.data_collections_by_output_name(heat_out)
    light_init = sql_obj.data_collections_by_output_name(light_out)
    elec_equip_init = sql_obj.data_collections_by_output_name(el_equip_out)
    gas_equip_init = sql_obj.data_collections_by_output_name(gas_equip_out)
    process1_init = sql_obj.data_collections_by_output_name(process1_out)
    process2_init = sql_obj.data_collections_by_output_name(process2_out)
    shw_init = sql_obj.data_collections_by_output_name(shw_out)
  else:  # we are on Mac; sqlite3 module doesn't work in Mac IronPython
    # Execute the honybee CLI to obtain the results via CPython
    cmds = [folders.python_exe_path, '-m', 'honeybee_energy', 'result', 'data-by-outputs', sql]
    for outp in energy_output:
      cmds.append('["{}"]'.format(outp))
    process = subprocess.Popen(cmds, stdout=subprocess.PIPE)
    stdout = process.communicate()
    data_coll_dicts = json.loads(stdout[0])
    cool_init = serialize_data(data_coll_dicts[0])
    heat_init = serialize_data(data_coll_dicts[1])
    light_init = serialize_data(data_coll_dicts[2])
    elec_equip_init = serialize_data(data_coll_dicts[3])
    gas_equip_init = serialize_data(data_coll_dicts[4])
    process1_init = serialize_data(data_coll_dicts[5])
    process2_init = serialize_data(data_coll_dicts[6])
    shw_init = serialize_data(data_coll_dicts[7])

  # convert the results to EUI and ouput them
  cooling = data_to_load_intensity(cool_init, floor_area, 'Cooling', _cool_cop_)
  heating = data_to_load_intensity(heat_init, floor_area, 'Heating', _heat_cop_)
  lighting = data_to_load_intensity(light_init, floor_area, 'Lighting', 1, mults)
  equip = data_to_load_intensity(elec_equip_init, floor_area, 'Electric Equipment', 1, mults)
  total_load = [cooling.total, heating.total, lighting.total, equip.total]

  # add gas equipment if it is there
  if len(gas_equip_init) != 0:
    gas_equip = data_to_load_intensity(gas_equip_init, floor_area, 'Gas Equipment', 1, mults)
    equip = [equip, gas_equip]
    total_load.append(gas_equip.total)
  # add process load if it is there
  process = []
  if len(process1_init) != 0:
    process1 = data_to_load_intensity(process1_init, floor_area, 'Process', 1, mults)
    process2 = data_to_load_intensity(process2_init, floor_area, 'Process', 1, mults)
    process = process1 + process2
    total_load.append(process.total)
  # add hot water if it is there
  hot_water = []
  if len(shw_init) != 0:
    hot_water = data_to_load_intensity(shw_init, floor_area, 'Service Hot Water', 1, mults)
    total_load.append(hot_water.total)

  shutil.rmtree(directory)
  print(total_load)
  return _model.identifier, total_load
