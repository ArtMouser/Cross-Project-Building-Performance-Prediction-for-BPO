from  ladybug_geometry.geometry3d import Point3D
from  ladybug_geometry.geometry3d import LineSegment3D
from  ladybug_geometry.geometry3d import Face3D
from  ladybug_geometry.geometry3d import Vector3D
from  ladybug_geometry.geometry3d import Sphere
from  ladybug_geometry.geometry3d import Ray3D
from  ladybug_geometry.geometry3d import Plane

from ladybug_geometry.intersection3d import intersect_line3d_sphere
from ladybug_geometry.intersection3d import intersect_plane_sphere

from honeybee.room import Room
from honeybee.face import Face
from honeybee.shade import Shade
import honeybee.facetype as facetype
from honeybee.model import Model
from honeybee.boundarycondition import Outdoors

from honeybee_energy.boundarycondition import Adiabatic
from honeybee_energy.programtype import ProgramType
from honeybee_energy.construction.window import WindowConstruction
from honeybee_energy.construction.windowshade import WindowConstructionShade
from honeybee_energy.construction.opaque import OpaqueConstruction
from honeybee_energy.material.opaque import EnergyMaterial
from honeybee_energy.material.shade import EnergyWindowMaterialShade
from honeybee_energy.schedule.ruleset import ScheduleRuleset
from honeybee_energy.properties.room import RoomEnergyProperties
from honeybee_energy.hvac.idealair import IdealAirSystem
from honeybee_energy.properties.model import ModelEnergyProperties
from honeybee_energy.constructionset import ConstructionSet
from honeybee_energy.constructionset import ApertureConstructionSet
from honeybee_energy.constructionset import WallConstructionSet

import honeybee_energy

import math
import json
import csv

def generate_model_from_csv(csv_path, row):
  input_row_number = row            # Raw number from a csv file with model parameters
  path_for_csv_inputs = csv_path    # Path to csv file with model parameters

  # Upload inputs from csv file
  inputs_csv = open(path_for_csv_inputs)
  inputs_lib = csv.DictReader(inputs_csv)
  cur_inputs = None
  for raw in inputs_lib:
    if inputs_lib.line_num < input_row_number:
      continue
    elif inputs_lib.line_num > input_row_number:
      break
    cur_inputs = raw

  # Upload Resources (construction set, constructions, materials, program and schedules)
  cons_set_json = open('resources/Cls_Cons_Set.json')
  const_json = open('resources/Cls_Const.json')
  mats_json = open('resources/Cls_Mats.json')
  residential_program_json = open('resources/IS_Residential_Program.json')
  residential_schedules_json = open('resources/IS_Residential_Schedules.json')

  cons_set_lib = json.load(cons_set_json)
  const_lib = json.load(const_json)
  mats_lib = json.load(mats_json)
  residential_program = ProgramType.from_dict(json.load(residential_program_json))
  residential_schedules_lib = json.load(residential_schedules_json)

  inputs_csv.close()
  cons_set_json.close()
  const_json.close()
  mats_json.close()
  residential_program_json.close()
  residential_schedules_json.close()


  ### PARAMETERS ###
  # Default Inputs
  width = 3                 # 2 - 16      East-West 
  length = 5                # 2 - 16      North-South
  height = 3                # 2.5 - 5
  rotation = -20            # -45 - 45

  north_wwr = 0.3           # 0 - 1
  west_wwr = 0              # 0 - 1
  south_wwr = 0.5           # 0 - 1
  east_wwr = 0              # 0 - 1

  north_shade_size = 1.5    # 0 - 4
  north_svf = 80            # 100 - 0
  west_shade_size = 0       # 0 - 4
  west_svf = 100            # 100 - 0
  south_shade_size = 0      # 0 - 4
  south_svf = 30            # 100 - 0
  east_shade_size = 0       # 0 - 4
  east_svf = 100            # 100 - 0

  north_adiabatic = 0       # 0 - 1
  west_adiabatic = 1        # 0 - 1
  south_adiabatic = 0.8     # 0 - 1
  east_adiabatic = 0        # 0 - 1

  insulation = 0.04         # 0.02 - 0.06
  glazing_type = 1          # 0 (Single Glazing), 1 (Double Glazing)

  model_name = "model_with_default_settings"

  # Custom Inputs from csv file
  if cur_inputs != None:
    width = round(float(cur_inputs['width']), 3)
    length = round(float(cur_inputs['length']), 3)
    height = round(float(cur_inputs['height']), 3)
    rotation = round(float(cur_inputs['rotation']), 3)
    north_wwr = float(cur_inputs['north_wwr'])
    west_wwr = float(cur_inputs['west_wwr'])
    south_wwr = float(cur_inputs['south_wwr'])
    east_wwr = float(cur_inputs['east_wwr'])
    north_shade_size = round(float(cur_inputs['north_shade_size']), 3)
    north_svf = round(float(cur_inputs['north_svf']), 3)
    west_shade_size = round(float(cur_inputs['west_shade_size']), 3)
    west_svf = round(float(cur_inputs['west_svf']), 3)
    south_shade_size = round(float(cur_inputs['south_shade_size']), 3)
    south_svf = round(float(cur_inputs['south_svf']), 3)
    east_shade_size = round(float(cur_inputs['east_shade_size']), 3)
    east_svf = round(float(cur_inputs['east_svf']), 3)
    north_adiabatic = float(cur_inputs['north_adiabatic'])
    west_adiabatic = float(cur_inputs['west_adiabatic'])
    south_adiabatic = float(cur_inputs['south_adiabatic'])
    east_adiabatic = float(cur_inputs['east_adiabatic'])
    insulation = float(cur_inputs['insulation'])
    glazing_type = float(cur_inputs['glazing_type'])
    
    inp_file_name = path_for_csv_inputs.replace("/", "_")
    inp_file_name = inp_file_name.replace(".", "_")
    model_name = "model_from_" + inp_file_name + "_raw_" + str(input_row_number)

  # Inputs reorganisation
  wwr = {
    "North": north_wwr,
    "West": west_wwr,
    "South": south_wwr,
    "East": east_wwr
  }
  shade_size = {
    "North": north_shade_size,
    "West": west_shade_size,
    "South": south_shade_size,
    "East": east_shade_size
  }
  svf = {
    "North": north_svf,
    "East": east_svf,
    "South": south_svf,
    "West": west_svf
  }
  adiabatic = {
    "North": north_adiabatic,
    "West": west_adiabatic,
    "South": south_adiabatic,
    "East": east_adiabatic
  }

  lines = {
    "North": [],
    "West": [],
    "South": [],
    "East": []
  }
  faces = {
    "North": [],
    "West": [],
    "South": [],
    "East": [],
  }
  hb_faces = {
    "North": [],
    "West": [],
    "South": [],
    "East": [],
  }
  shades = {
    "North": None,
    "West": None,
    "South": None,
    "East": None
  }
  sky = {
    "North": None,
    "West": None,
    "South": None,
    "East": None
  }

  inputs = [width, length, height, rotation, north_wwr, 
            west_wwr, south_wwr, east_wwr, north_shade_size, north_svf, 
            west_shade_size, west_svf, south_shade_size, south_svf, east_shade_size,
            east_svf, north_adiabatic, west_adiabatic, south_adiabatic, east_adiabatic,
            insulation, glazing_type]

  # Auxiliary variables
  shades_count = 0
  context_count = 0

  side_rot = {
    "North": 0,
    "West": 90,
    "South": 180,
    "East": 270
  }

  # Context dome settings
  dome_rad = 45              # Context dome radius
  dome_num_parallels = 10    # Context dome number of parallels for one direction
  dome_num_meridians = 8     # Context dome number of meridians for one direction


  ### MODEL GEOMETRY ###
  # Vertices
  p_orig = Point3D(0,0,0)
  pSW = Point3D(-width/2 + p_orig.x, -length/2 + p_orig.y, 0 + p_orig.z)
  pSE = Point3D(width/2 + p_orig.x, -length/2 + p_orig.y, 0 + p_orig.z)
  pNE = Point3D(width/2 + p_orig.x, length/2 + p_orig.y, 0 + p_orig.z)
  pNW = Point3D(-width/2 + p_orig.x, length/2 + p_orig.y, 0 + p_orig.z)

  points = {
    "North": [pNE, pNW],
    "West": [pNW, pSW],
    "South": [pSW, pSE],
    "East": [pSE, pNE]
  }

  # Vectors
  vect_z = Vector3D(x=0,y=0,z=height)
  axis_x = Vector3D(x=1,y=0,z=0)
  axis_y = Vector3D(x=0,y=1,z=0)

  # Context dome original Geometry
  dome_p_orig = p_orig.move(vect_z.__mul__(0.5))
  dome = Sphere(dome_p_orig, dome_rad)

  # Base walls lines
  for side in lines:
      if adiabatic[side] <= 0 or adiabatic[side] >= 1:
          lines[side].append(LineSegment3D.from_end_points(p1=points[side][0],p2=points[side][1]))
      else:
          points[side].append(Point3D(points[side][0].x + (points[side][1].x - points[side][0].x) * (adiabatic[side]/2), points[side][0].y + (points[side][1].y - points[side][0].y) * (adiabatic[side]/2)))
          points[side].append(Point3D(points[side][1].x - (points[side][1].x - points[side][0].x) * (adiabatic[side]/2), points[side][1].y - (points[side][1].y - points[side][0].y) * (adiabatic[side]/2)))
          lines[side].append(LineSegment3D.from_end_points(p1=points[side][0],p2=points[side][2]))
          lines[side].append(LineSegment3D.from_end_points(p1=points[side][2],p2=points[side][3]))
          lines[side].append(LineSegment3D.from_end_points(p1=points[side][3],p2=points[side][1]))

  # Walls faces
  for side in faces:
      for line in lines[side]:
          faces[side].append(Face3D.from_extrusion(line_segment=line,extrusion_vector=vect_z))

  # Walls HB faces
  for side in hb_faces:
      if adiabatic[side] == 0:
          hb_faces[side].append(Face(identifier="wall_"+side,geometry=faces[side][0],boundary_condition=Outdoors()))
          if wwr[side]>0 and wwr[side]<1:
              hb_faces[side][0].apertures_by_ratio(ratio=wwr[side])
      elif adiabatic[side] == 1:
          hb_faces[side].append(Face(identifier="wall_"+side,geometry=faces[side][0],boundary_condition=Adiabatic()))
      else:
          hb_faces[side].append(Face(identifier="wall_"+side+"_0",geometry=faces[side][0],boundary_condition=Adiabatic()))
          hb_faces[side].append(Face(identifier="wall_"+side+"_1",geometry=faces[side][1],boundary_condition=Outdoors()))
          hb_faces[side].append(Face(identifier="wall_"+side+"_2",geometry=faces[side][2],boundary_condition=Adiabatic()))
          if wwr[side]>0 and wwr[side]<1:
              hb_faces[side][1].apertures_by_ratio(ratio=wwr[side])

  # Top face
  face_top = Face3D(boundary=[pNE,pNW,pSW,pSE])
  face_top = face_top.move(vect_z)
  hb_face_top = Face(identifier="ceiling",geometry=face_top,boundary_condition=Adiabatic())
  # Bottom face
  face_bottom = Face3D(boundary=[pSW,pSE,pNE,pNW])
  hb_face_bottom = Face(identifier="floor",geometry=face_bottom,type=facetype.Floor(),boundary_condition=Adiabatic())

  all_faces = [item for sublist in list(hb_faces.values()) for item in sublist]+[hb_face_top,hb_face_bottom]

  # Shades
  for side in shades:
      if round(shade_size[side],3) > 0:
          s_point1 = points[side][0].duplicate()
          s_point2 = points[side][1].duplicate()
          s_vector1 = Vector3D(x=s_point1.x-s_point2.x, y=s_point1.y-s_point2.y, z=0)
          s_vector1 = s_vector1.normalize()
          s_vector1 = s_vector1.__mul__(math.sqrt((shade_size[side]**2)*2))
          s_vector1 = s_vector1.rotate_xy(math.radians(45))
          s_vector2 = s_vector1.duplicate()
          s_vector2 = s_vector2.rotate_xy(math.radians(90))
          s_point1 = s_point1.move(s_vector1)
          s_point2 = s_point2.move(s_vector2)
          s_face = Face3D(boundary=[points[side][1],points[side][0],s_point1,s_point2])
          s_face = s_face.move(vect_z)
          shades[side] = Shade(identifier="shade_"+side, geometry=s_face)
          shades_count += 1

  # Context
  for side in sky:
      if svf[side] > 0 and svf[side] < 100:
          sky_points = []
          faces = []
          h = (((100 - svf[side])/100) * (((dome_rad**2)*(4*math.pi))/2)) / (dome_rad * (2*math.pi))
          ang = 90-math.degrees(math.acos(h/dome_rad))
          num_sides = math.ceil(ang / (90/dome_num_parallels))
          for x in range(num_sides+1):
              cur_ang = x*(ang/num_sides)
              vec = axis_y.rotate(axis_x, math.radians(cur_ang))
              int_p = intersect_line3d_sphere(Ray3D(dome_p_orig, vec),dome)
              int_c = intersect_plane_sphere(Plane(o=int_p[0]),dome)
              cur_points = []
              for y in range(dome_num_meridians+1):
                  cur_point = int_c[0]
                  cur_vec = axis_y.rotate_xy(math.radians(side_rot[side]+y*(90/dome_num_meridians)-45+rotation))
                  cur_vec = cur_vec.__mul__(int_c[2])
                  cur_point = cur_point.move(cur_vec)
                  cur_points.append(cur_point)
              sky_points.append(cur_points)
          for x in range(num_sides):
              for y in range(dome_num_meridians):
                  if x == 0:
                      faces.append(Shade(identifier="context"+side+"_"+str(context_count), geometry=Face3D(boundary=[Point3D(sky_points[x][y].x,sky_points[x][y].y,0),Point3D(sky_points[x][y+1].x,sky_points[x][y+1].y,0),sky_points[x][y+1],sky_points[x][y]])))
                      context_count += 1
                  faces.append(Shade(identifier="context"+side+"_"+str(context_count), geometry=Face3D(boundary=[sky_points[x][y],sky_points[x][y+1],sky_points[x+1][y+1],sky_points[x+1][y]])))
                  context_count += 1
          sky[side] = faces.copy()


  ### MODEL ENERGY PROPERTIES ###
  wall_mat01 = EnergyMaterial.from_dict(mats_lib["Cls_Cement Mortar"])
  wall_mat02 = EnergyMaterial.from_dict(mats_lib["Cls_Concrete 20cm"])
  wall_mat03 = EnergyMaterial.from_dict(mats_lib["Cls_Concrete 30cm"])
  wall_mat04 = EnergyMaterial.from_dict(mats_lib["Cls_Lime-Cement Mortar"])
  wall_insulation = EnergyMaterial.from_dict(mats_lib["Cls_Ins_Mat_3cm"])
  if insulation > 0:
    wall_insulation.thickness = insulation
    wall_insulation.identifier = wall_insulation.display_name = "Cls_Ins_Mat_" +  str(insulation) + "m"
    walls_construction = OpaqueConstruction("Wall Structure + " + str(insulation) + "m Insulation", materials=[wall_mat01, wall_insulation, wall_mat02, wall_mat03, wall_mat04])
  elif insulation == 0:
    walls_construction = OpaqueConstruction("Wall Structure No Insulation", materials=[wall_mat01, wall_mat02, wall_mat03, wall_mat04])

  mat_tris = EnergyWindowMaterialShade.from_dict(mats_lib["Cls_Tris"])
  schedule_tris = ScheduleRuleset.from_dict(residential_schedules_lib["IS_Residential_TrisSchd"])
  const_single_glazing = WindowConstruction.from_dict(const_lib["Cls_SgCl_Alumin_140x95_5.84_.7_.68"])
  const_double_glazing = WindowConstruction.from_dict(const_lib["Cls_DgCl_Alum_140x95_3.12_.59_.59"])
  if glazing_type == 0:
    windows_construction = WindowConstructionShade("Single glazing + Shades", const_single_glazing, mat_tris, shade_location="Exterior", schedule=schedule_tris)
  if glazing_type == 1:
    windows_construction = WindowConstructionShade("Double Glazing + Shades", const_double_glazing, mat_tris, shade_location="Exterior", schedule=schedule_tris)

  aperture_construction_set = ApertureConstructionSet(window_construction=windows_construction)
  wall_construction_set = WallConstructionSet(exterior_construction=walls_construction)
  zone_construction_set = ConstructionSet("zone_construction_set", wall_set=wall_construction_set, aperture_set=aperture_construction_set)


  ### HB ROOM with properties ###
  hb_zone = Room(identifier="Zone",faces=all_faces)
  if shades_count > 0: hb_zone.add_outdoor_shades(filter(None,shades.values()))
  hb_zone.rotate_xy(angle=rotation,origin=p_orig)

  hb_zone.properties.energy.program_type = residential_program
  hb_zone.properties.energy.add_default_ideal_air()
  hb_zone.properties.energy.construction_set = zone_construction_set


  ### HB MODEL ###
  if context_count > 0:
      context = filter(None,sky.values())
      context = [item for sublist in context for item in sublist]
      hb_model = Model(identifier="model_" + str(row), rooms=[hb_zone], orphaned_shades=context)
  else: hb_model = Model(identifier="model_" + str(row), rooms=[hb_zone])


  ### MODEL CHECK ###
  check_room = 0
  check_zone = 0
  if check_room:
      print(hb_zone.check_non_zero())
      print(hb_zone.check_planar())
      print(hb_zone.check_self_intersecting())
      print(hb_zone.check_solid())
      print(hb_zone.check_sub_faces_valid())
      print(hb_zone.check_sub_faces_overlapping())
  if check_zone:
      print(hb_model.check_all())


  ### MODEL OUTPUT ###
  return hb_model, inputs
