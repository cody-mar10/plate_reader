#!/usr/bin/env python3
# coding: utf-8

import sys, argparse
def main():
    ###############
    ## Arguments ##
    ###############
    
    import pandas as pd
    import numpy as np
    from openpyxl import Workbook
    import openpyxl

    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input", type=str, action="store", help="Input file", required=True)
    parser.add_argument("-p", "--plate", type=str, action="store", help="Plate setup file", required=True)
    parser.add_argument("-a", "--active", type=int, action="store", help="Active data sheet", default=0)
    parser.add_argument("-gs", "--graphsoft", type=str, action="store", help="Set graphing program", default="excel")
    parser.add_argument("-pp", "--produceplot", action="store_false", help="Autogenerate python plot: True/False")
    parser.add_argument("-y", "--yaxis", type=str, action="store", help="y-axis label on plot", default="OD600")
    parser.add_argument("-gm", "--graphmeth", type=str, action="store", help="graphing method: time series, time diff", default="time series")
    parser.add_argument("-pw", "--pointsperwell", type=int, action="store", help="readings per well", default=4)
    args = parser.parse_args()

    file = args.input
    plate_setup_file = args.plate
    active_sheet = args.active
    graph_soft = args.graphsoft
    produce_plot = args.produceplot
    y_ax_label = args.yaxis
    graph_method = args.graphmeth
    points_per_well = args.pointsperwell

    print("\ndata file:", file)
    print("plate setup:", plate_setup_file)
    print("active sheet:", (active_sheet + 1))
    print("graphing software:", graph_soft)
    print("y axis label:", y_ax_label)
    print("graphing method:", graph_method)
    print("points per well:", points_per_well)
    print("\nNOTE: for large data sets, could take a few min")

    # Need to coerce all sample names to strings to allow proper replicate concatenation
    plate_setup_df = pd.read_csv(plate_setup_file, dtype={1: str, 2: str, 3: str,
                                                          4: str, 5: str, 6: str,
                                                          7: str, 8: str, 9: str,
                                                          10: str, 11: str, 12: str})
    plate_setup_df = plate_setup_df.set_index("row")

    row_letters = list(plate_setup_df.index) # list of row letters
    col_numbers = list(plate_setup_df.columns) # list of column numbers

    # Get all possible row/col well combinations in a standard 96-well plate
    all_wells = []
    for row in row_letters:
        for col in col_numbers:
            well = row + col
            all_wells.append(well)

    def findReplicates(df, value):
        #Get row and col positions of value in dataframe i.e. df
        list_of_positions = []

        # Get bool dataframe with True at positions where the given value exists
        result = df.isin([value])

        # Get list of columns that contains the value
        result_series = result.any()

        columnNames = list(result_series[result_series == True].index)

        # Iterate over list of columns and fetch the rows indexes where value exists
        for col in columnNames:
            rows = list(result[col][result[col] == True].index)
            for row in rows:
                list_of_positions.append([row, col])

        num_occurences = len(list_of_positions)
        for occurence in range(num_occurences):
            list_of_positions[occurence] = list_of_positions[occurence][0] + str(list_of_positions[occurence][1])

        # Return a list of the value's coordinates in the dataframe
        return list_of_positions

    # Create a list, based on the plate setup, of all unique samples
    sample_list = []
    for row in range(8):
        for col in range(12):
            if pd.isnull(plate_setup_df.iloc[row, col]) == False:
                if plate_setup_df.iloc[row, col] not in sample_list:
                    sample_list.append(plate_setup_df.iloc[row, col])

    # Then for each sample, get the cell coordinates in the well for all replicates
    replicates = {}
    for sample in sample_list:
        sample_reps = findReplicates(plate_setup_df, sample)
        replicates[sample] = sample_reps

    # Activate an xlsx workbook
    wb = openpyxl.load_workbook(file, read_only=True)
    wb.active = active_sheet ### this is something that needs to be input
    rawdata = wb.active

    if "air" in replicates:
        air_wells = replicates["air"]

    # data always starts around cell A60 but not always - especially if any changes to data have been made
    def splitCellCoordinates(word):
        col_letters = []
        row_num = []
        for char in word:
            if char.isalpha() == True: # checks if the character is a letter
                col_letters.append(char) # will input excel column letter
            else: # if the character is a number
                row_num.append(char)

        final_row = ""
        for row_char in row_num:
            final_row += row_char

        final_col = ""
        for col_char in col_letters:
            final_col += col_char

        cell_coordinates = [final_col, final_row]
        return cell_coordinates # return a list in form of [col_letter, row_num]

    # finds the first time series data table
    found_first_datatable = False
    for row in rawdata.iter_rows():
        for cell in row:
            if cell.value in all_wells:
                start_cell = cell.coordinate
                found_first_datatable = True
                if "air" in replicates and cell.value in air_wells: # checks if that value is was an air value
                    found_first_datatable = False
        if found_first_datatable:
            break

    start_row = int(splitCellCoordinates(start_cell)[1]) # row_num will always be the second entry returned
    end_row = start_row + 4 + points_per_well # the other +4 is for the temp, time, mean, and stdev

    num_columns = 0
    for row in rawdata.iter_rows(min_row = start_row, max_row = start_row):
        for cell in row:
            if cell.value != None:
                num_columns += 1
    num_timepoints = num_columns - 1 # there is an extra col for the data labels

    def getWellTable(data, startrow, endrow):
        well_dict = {}
        for row in data.iter_rows(min_row = startrow,
                                  max_row = endrow,
                                  max_col = num_timepoints + 1,
                                  values_only = True):
            myrow = []
            for val in row:
                myrow.append(val)

            tablevals = []
            for i in range(len(myrow)):
                if i == 0:
                    rowname = myrow[i]
                else:
                    tablevals.append(myrow[i])
            well_dict[rowname] = tablevals

        well_table_df = pd.DataFrame.from_dict(well_dict, orient="index")
        well_tag = [well_table_df.index[0]] * len(well_table_df)
        well_table_df["well"] = well_tag

        # drop first row that has the well number and the timepoint numbers
        well_table_df = well_table_df.drop(well_table_df.index[[0,2,3,4]])

        time_min = []
        time_hour = []
        for val in well_table_df.loc["Time [s]"]:
            if isinstance(val, (int, float)):
                time_min.append(val / 60)
                time_hour.append(round(val / 3600, 3))
            else:
                time_min.append(val)
                time_hour.append(val)

        well_table_df.loc["Time [m]"] = time_min
        well_table_df.loc["Time [h]"] = time_hour
        well_table_df = well_table_df.sort_index(ascending = False)

        return well_table_df

    def getAllDataTables(setup_df, startrow, endrow):
        # This gets all tables for all 96 wells in the plate, regardless of if they have data
        list_of_well_datatables = []
        for i in range(96):
            list_of_well_datatables.append(getWellTable(rawdata, startrow, endrow))
            startrow = endrow + 3
            endrow = startrow + 4 + points_per_well
            
        # Then create a single list of all well positions with actual data
        rep_list = []
        for group_name in replicates:
            rep_list.append(replicates[group_name])

        rep_list = sum(rep_list, [])

        # only choose tables that contain data
        data_list = []
        for table in list_of_well_datatables:
            if table["well"][0] in rep_list:
                data_list.append(table)
        return data_list

    def concatenateReplicateTables(setup_df, startrow, endrow):
        all_tables = getAllDataTables(setup_df, startrow, endrow)
        num_groups = len(sample_list)
        num_samples = sum(plate_setup_df.count())
        reps_grouped = []
        concat_reps = {}
        #### fix replicates
        for group_num in range(num_groups):
            group_name = sample_list[group_num]

            num_reps = len(replicates[group_name])
            data_labels = [str(val+1) for val in range(points_per_well * num_reps)]

            list_rep_tables = []
            for rep_num in range(num_reps):
                for sample_num in range(num_samples):
                    if replicates[group_name][rep_num] == all_tables[sample_num]["well"][0]:
                        list_rep_tables.append(all_tables[sample_num])

                if rep_num != 0: # only need to remove time labels from the all reps after the first
                    list_rep_tables[rep_num] = list_rep_tables[rep_num].drop(["Time [s]", "Time [m]", "Time [h]"])

            reps_grouped.append(list_rep_tables)
            if group_name == "air": # skips the rest of this process for the air scans
                continue
            if len(reps_grouped[group_num]) == 1: # if there is only one replicate
                concat_reps[group_name] = reps_grouped[group_num][0]
            elif len(reps_grouped[group_num]) > 1:
                concat_reps[group_name] = pd.concat(reps_grouped[group_num])

            concat_indices = list(concat_reps[group_name].index)

            num_rows = len(concat_reps[group_name])
            for row_num in range(num_rows):
                if row_num > 2: # skip first 3 time rows
                    concat_indices[row_num] = data_labels[row_num - 3]
            concat_reps[group_name].index = concat_indices

        return concat_reps

    def summarizeTimepoints(setup_df, startrow, endrow):
        total_concat_reps = concatenateReplicateTables(setup_df, startrow, endrow)

        for group_name in sample_list:
            if group_name == "air":
                continue
            num_reps = len(replicates[group_name])
            OD_only = total_concat_reps[group_name].loc["1":str(num_reps * points_per_well)]

            average_for_timepoint = []
            stdev_for_timepoint = []
            for col in OD_only:
                if col != "well":
                    mean_at_timepoint = round(OD_only[col].mean(), 4)
                    stdev_at_timepoint = round(OD_only[col].std(), 4)
                    average_for_timepoint.append(mean_at_timepoint)
                    stdev_for_timepoint.append(stdev_at_timepoint)

            # include entry for the well column
            average_for_timepoint.append("all")
            stdev_for_timepoint.append("all")

            total_concat_reps[group_name].loc["Mean"] = average_for_timepoint
            total_concat_reps[group_name].loc["Stdev"] = stdev_for_timepoint
        return total_concat_reps

    def subtractBackground(setup_df, startrow, endrow):
        summary = summarizeTimepoints(setup_df, startrow, endrow)

        background = summary["Blank"]
        avg_background = list(background.loc["Mean"])
        del avg_background[-1] # remove the well column "all"

        for group_name in sample_list:
            if group_name == "air":
                continue
            if group_name != "Blank":
                current_group = list(summary[group_name].loc["Mean"])
                del current_group[-1]

                subtract_background = []
                for val in range(num_timepoints):
                    diff = round(current_group[val] - avg_background[val], 4)
                    subtract_background.append(diff)
                subtract_background.append("all")

                summary[group_name].loc["Signal"] = subtract_background
        return summary

    final = subtractBackground(plate_setup_df, start_row, end_row)

    meandict = {}
    stdevdict = {}
    time_hour_list = ["Time [h]", "time"]
    timepoints_h = list(final["Blank"].loc["Time [h]"])
    del timepoints_h[-1]

    for timepoint in timepoints_h:
        time_hour_list.append(timepoint)

    timepoints_df = pd.DataFrame([time_hour_list])

    for group_name in final: # iterate off keys
        if group_name == "air":
            continue
        if group_name != "Blank":
            meanlist = list(final[group_name].loc["Signal"])
            del meanlist[-1]
            stdevlist = list(final[group_name].loc["Stdev"])
            del stdevlist[-1]

            meandict[group_name] = meanlist
            stdevdict[group_name] = stdevlist

    all_means = []
    all_stdevs = []
    for group_name in sample_list:
        if group_name == "air":
            continue
        if group_name != "Blank":
            meanlist = [group_name, "mean"]
            stdevlist = [group_name, "stdev"]
            for mean, stdev in zip(meandict[group_name], stdevdict[group_name]):
                meanlist.append(mean)
                stdevlist.append(stdev)
            all_means.append(meanlist)
            all_stdevs.append(stdevlist)

    means_df = pd.DataFrame(all_means)
    stdevs_df = pd.DataFrame(all_stdevs)
    end = pd.concat([means_df, stdevs_df], ignore_index = True)
    colnames = ["group", "type"]
    for i in range(num_timepoints):
        colnames.append(i)
    end.columns = colnames

    timepoints_df.columns = colnames
    timeend = pd.concat([timepoints_df, end], ignore_index = True)
    timeend = timeend.dropna(axis=1) # drop columns with NaN values

    time_row = list(timeend[timeend["type"] == "time"].loc[0])
    del time_row[0]
    del time_row[0]
    means_data = timeend[timeend["type"] == "mean"].reset_index(drop=True)
    stdev_data = timeend[timeend["type"] == "stdev"].reset_index(drop=True)
    reps = {}
    for key in replicates:
        reps[key] = len(replicates[key])

    savefile = file.split(".")[0] + "_PROCESSED.csv"

    from math import sqrt
    if graph_soft == "excel":
        timeend.to_csv(savefile, index = False)
    elif graph_soft == "R":
        num_groups = len(replicates) - 1 # subtract Blank group
        longtime = time_row * num_groups

        longmean = timeend[timeend["type"] == "mean"].T
        longmean = longmean.drop(["group", "type"])

        all_means = []
        for col in longmean.columns:
            all_means.append(longmean[col].tolist())
        all_means = sum(all_means, [])

        longstdev = timeend[timeend["type"] == "stdev"].T
        longstdev = longstdev.drop(["group", "type"])

        all_stdevs = []
        for col in longstdev.columns:
            all_stdevs.append(longstdev[col].tolist())
        all_stdevs = sum(all_stdevs, [])

        group_names = np.array(longmean.columns)
        longgroup = list(np.repeat(group_names, len(time_row), axis=0))

        # make df to combine all times, groups, means, and stdevs in long data format
        long_timeend = pd.DataFrame(list(zip(longtime, longgroup, all_means, all_stdevs)),
                                    columns = ["Time_h", "group", "mean", "stdev"])

        # calculate standard error of mean
        all_sems = []
        for row in long_timeend.index:
            sem = long_timeend.iloc[row, 3] / sqrt(reps[str(long_timeend.iloc[row, 1])])
            all_sems.append(sem)

        # add sem column to long_timeend df
        long_timeend["sem"] = all_sems

        # return long_timeend
        long_timeend.to_csv(savefile, index=False)
        
    if produce_plot == True:
        import matplotlib.pyplot as plt
        import itertools

        if graph_method == "time series":
            ftsize = 20
            fig = plt.figure(figsize=(10,15))
            fig.suptitle(file.split(".")[0][0:20], fontsize = ftsize, fontweight="bold")

            mksize = 15
            lnwid = 3
            names = list(means_data["group"])
            my_markers = itertools.cycle(("o", "s", "v", "p", "P", "X", "D", "h", "*", "^", "<", ">"))
            solid_lines = ["-"] * 10
            dashed_lines = ["--"] * 10
            dotted_lines = [":"] * 10
            my_linestyles = solid_lines + dashed_lines + dotted_lines
            my_linestyles = itertools.cycle(my_linestyles)

            for row in means_data.index:
                my_y = list(means_data.loc[row])
                del my_y[0]
                del my_y[0]

                my_y_sd = list(stdev_data.loc[row])
                del my_y_sd[0]
                del my_y_sd[0]
                my_reps = points_per_well * reps[names[row]]
                weight = sqrt(my_reps)
                my_y_se = [(sd/weight) for sd in my_y_sd]

                plt.errorbar(x = time_row,
                             y = my_y,
                             yerr = my_y_se,
                             marker = next(my_markers),
                             linestyle = next(my_linestyles),
                             mec = "black",
                             ms = mksize,
                             capsize = 5,
                             #alpha = 0.7,
                             lw = lnwid,
                             mew = 2.5
                            )

            plt.ylabel(y_ax_label, fontsize = ftsize, fontweight="bold") # should probably make this an arg to specify
            plt.xlabel("Time (h)", fontsize = ftsize, fontweight="bold")
            plt.xticks(fontsize = ftsize * 0.75)
            plt.yticks(fontsize = ftsize * 0.75)

            plt.legend(names, loc = "center left", bbox_to_anchor=(1, 0.5), fontsize = (ftsize*0.75), edgecolor = "black")

            plt.tight_layout(rect=[0, 0.03, 1, 0.96])
            plt.savefig((file.split(".")[0] + "_PROCESSED.pdf"))

if __name__ == "__main__":
   main()
