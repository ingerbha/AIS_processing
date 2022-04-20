""" Will extract parameters from the cases                          """
""" Can also be used to plot cases/situations                       """
""" Plotting requires basemap (used with conda and python 3.8.10)   """

from AutoVerification import AutoVerification
from AutoVerification import abs_ang_diff
from dataclasses import asdict
import os
import time
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import multiprocessing as mp

multiple            = True 

plot_trajectories   = False
plot_case           = False 

SPECIFIC_OWN_NAME   = ''    # Set to '' for no specific and automatic plotting

SPECIFIC_OBST_NAMES = ['']  # Set to '' for no specific and automatic plotting

unique_case = ''            # Set to '' for non unique case-code (plot all). 
                            # To plot specific case add case-code of the file

TRAJ = None                 # Set to None if automatic trajectory detection 

cpu_usage           = 80
overwrite           = False 

paths = ['./encs_selected','./encs_north', './encs_south']

# ---------------------------------------------------------------------------------------------------
# Combined algorithm
def getCaseParamFromFile(filename):
    if not multiple and unique_case != '' and unique_case not in filename:
        return

    import os.path
    from os import path
        
    if not multiple:
        print(path.join(root,filename))

    if overwrite:
        start = ' - '
        end = '-60-sec'
        code =  filename[filename.find(start)+len(start):filename.rfind(end)]
        param_filename = './para/Params - ' + code + '.csv'
        import os.path
        from os import path
        if path.exists(param_filename):
            return

    ship_path = './' + root.split('/')[1] + '/''full_shipdata.csv'
    AV = AutoVerification(AIS_path = path.join(root, filename),
                            ship_path = ship_path,
                            r_colregs_2_max=5000,
                            r_colregs_3_max=3000,
                            r_colregs_4_max=400,
                            r_pref=1500,  # todo: Find the value used by Woerner
                            r_min=1000,
                            r_nm=800,
                            r_col=200,
                            epsilon_course=10,
                            epsilon_speed=2.5,
                            delta_chi_apparent=30,
                            delta_speed_apparent=5,
                            alpha_critical_13=45.0, #45,  # absolute value is used
                            alpha_critical_14=13.0, #13.0,  # absolute value is used
                            alpha_critical_15=-10.0,  # -10.0 
                            alpha_cpa_min_15=-25.0,  # -25
                            alpha_cpa_max_15=165.0,  # 165
                            alpha_ahead_lim_13=45.0,  # absolute value is used
                            phi_OT_min=112.5, # 112.5,  # equal
                            phi_OT_max=247.5) # 247.5,  # equal

    AV.find_ranges() # Find ranges between all ships

    for vessel in AV.vessels:
        
        AV.find_maneuver_detect_index(vessel) # Find maneuvers made by ownship
        for obst in AV.vessels:
            if vessel.id == obst.id:
                continue
            sits = []
            sit_happened = False
            for k in range(AV.n_msgs):
                if AV.entry_criteria(vessel, obst, k) != AV.NAR: # Find applicable COLREG situations between all ships
                    sit_happened = True
                if k == 0:
                    continue
                if AV.situation_matrix[vessel.id, obst.id, k] != AV.situation_matrix[vessel.id, obst.id, k-1]:
                    sits.append(k)
            if sit_happened:
                AV.filterOutNonCompleteSituations(vessel, obst)

    maneuvers = []
    filter_outliners = 2

    data_bank = pd.DataFrame()

    start = ' - '
    end = '-60-sec'
    code =  filename[filename.find(start)+len(start):filename.rfind(end)]
    code = code[-5:]

    params = []
    for vessel in AV.vessels:
        if vessel.travel_dist < 500 or 7 in vessel.nav_status:
            continue

        plot = False

        if SPECIFIC_OWN_NAME == '':
            specific_own_name = vessel.name
        else:
            specific_own_name = SPECIFIC_OWN_NAME

        specific_obst_names = SPECIFIC_OBST_NAMES

        for obst in AV.vessels:
            if vessel.id != obst.id and not all(x == 0 for x in AV.situation_matrix[vessel.id, obst.id, :]):
                arr = AV.situation_matrix[vessel.id, obst.id, :]
                arr[0] = AV.NAR
                indxies = np.where(\
                        np.logical_and(arr[:-1] != arr[1:], \
                        np.logical_or(arr[:-1] == 0, arr[1:] == 0)))[0]

                if len(indxies) > 0:
                    plot = True

                for start, stop in zip(indxies[0::2], indxies[1::2]):    
                    if stop - start < 5:
                        continue
                    p = AV.constructParams(vessel, obst, start + 1, stop + 1)

                    if p is None:
                        continue

                    param_dict = asdict(p)

                    if False and not multiple: print(param_dict) # debug disabled

                    if SPECIFIC_OBST_NAMES == ['']:
                        specific_obst_names = [obst.name]

                    param_dict['case'] = code
                    param_dict['dataset'] = root.split('/')[1]
                    params.append(param_dict)

                    if plot and plot_trajectories and not multiple:
                        if specific_obst_names == ['']:
                            specific_obst_names = [obst.name]

                        if vessel.name == specific_own_name:
                            AV.OWN_SHIP = vessel.id
                            if TRAJ is None:
                                traj = param_dict['maneuver_index_own'] 
                            else:
                                traj = TRAJ
                            AV.plot_trajectories2(show_trajectory_at = traj, specific_obst_names = specific_obst_names)

    if plot_case:
        AV.plot_case()

    data_bank = pd.DataFrame(params)
    start = ' - '
    end = '-60-sec'
    code =  filename[filename.find(start)+len(start):filename.rfind(end)]
    data_bank.to_csv('./para/Params - ' + code + '.csv', sep= ';', index = False)
    del data_bank


#################################################################################
print('STARTING')
from itertools import chain

for root, dirs, files in chain.from_iterable(os.walk(path) for path in paths):
    proc = []
    import random
    import sys
    import psutil

    random.shuffle(dirs)
    random.shuffle(files)
    number_of_files = len(files)

    for count, filename in enumerate(files):
        if filename.endswith("60-sec.csv"): 
            if not multiple:
                getCaseParamFromFile(filename)
                continue
            p = mp.Process(target = getCaseParamFromFile, args = (filename,))
            proc.append(p)
            p.start()

            sys.stdout.flush()
            sys.stdout.write("Working file %s/%s - children working %s        \r " % (count, number_of_files, len(proc)))

            while psutil.cpu_percent() > cpu_usage:
                for ps in proc:
                    ps.join(timeout = 0)
                    if not ps.is_alive():
                        proc.remove(ps)
                time.sleep(0.5)

    while len(mp.active_children()) > 0:
        time.sleep(0.5)