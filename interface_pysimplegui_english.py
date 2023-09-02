#!/usr/bin/env python3
"""
Interface
"""

# pyinstaller --onefile --add-binary
# "sportsbetting\resources\chromedriver.exe;sportsbetting\resources" --add-data
# "sportsbetting\resources\teams.db;sportsbetting\resources" interface_pysimplegui.py --noconfirm
import collections
import queue
import threading
import pickle
import os
import sys
import time
from math import ceil

import PySimpleGUI as sg
import sportsbetting
from sportsbetting.auxiliary_functions import get_nb_outcomes
from sportsbetting.database_functions import get_all_sports, get_all_competitions
from sportsbetting.user_functions import parse_competitions
from sportsbetting.interface_functions import (odds_table_combine,
                                               best_match_under_conditions_interface,
                                               best_match_freebet_interface,
                                               best_match_cashback_interface,
                                               best_matches_combine_interface,
                                               best_match_stakes_to_bet_interface,
                                               best_stakes_match_interface,
                                               best_matches_freebet_interface,
                                               best_match_pari_gagnant_interface,
                                               odds_match_interface, delete_odds_interface,
                                               get_current_competitions_interface,
                                               get_main_competitions_interface,
                                               best_combine_reduit_interface)

PATH_DATA = os.path.dirname(sportsbetting.__file__) + "/resources/data.pickle"

sports = get_all_sports()
sites = sportsbetting.BOOKMAKERS


print("""
   _____                  __             __         __  __  _            
  / ___/____  ____  _____/ /______      / /_  ___  / /_/ /_(_)___  ____ _
  \__ \/ __ \/ __ \/ ___/ __/ ___/_____/ __ \/ _ \/ __/ __/ / __ \/ __ `/
 ___/ / /_/ / /_/ / /  / /_(__  )_____/ /_/ /  __/ /_/ /_/ / / / / /_/ / 
/____/ .___/\____/_/   \__/____/     /_.___/\___/\__/\__/_/_/ /_/\__, /  
    /_/                                                         /____/   
""")

try:
    sportsbetting.ODDS = pickle.load(open(PATH_DATA, "rb"))
except FileNotFoundError:
    pass


# All the stuff inside your window.
sg.set_options(enable_treeview_869_patch=False)
parsing_layout = [
    [
        sg.Listbox(sports, size=(20, 6), key="SPORT", enable_events=True),
        sg.Column([[sg.Listbox((), size=(27, 12), key='COMPETITIONS', select_mode='multiple')],
                   [sg.Button("Unselect all", key="SELECT_NONE_COMPETITION")],
                   [sg.Button("Current leagues", key="CURRENT_COMPETITIONS")],
                   [sg.Button("Main leagues", key="MAIN_COMPETITIONS")]]),
        sg.Column([[sg.Listbox(sites, size=(20, 12), key="SITES", select_mode='multiple')],
                   [sg.Button("Select all", key="SELECT_ALL")],
                   [sg.Button("Unselect all", key="SELECT_NONE_SITE")]])
    ],
    [sg.Col([[sg.Button('Start', key="START_PARSING")]]),
     sg.Col([[sg.Button('Stop', key="STOP_PARSING", button_color=("white", "red"), visible=False)]]),
     sg.Col([[sg.ProgressBar(max_value=100, orientation='h', size=(20, 20), key='PROGRESS_PARSING',
                             visible=False)]]),
     sg.Col([[sg.Text("Initialisation of selenium in progress", key="TEXT_PARSING", visible=False)]]),
     sg.Col([[sg.Text("8:88:88", key="REMAINING_TIME_PARSING", visible=False)]])],
    [sg.Col([[sg.ProgressBar(max_value=100, orientation='v', size=(10, 20),
                             key="PROGRESS_{}_PARSING".format(site), visible=False)],
             [sg.Text(site, key="TEXT_{}_PARSING".format(site), visible=False)]],
            element_justification="center") for site in sites]
]

column_text_under_condition = [[sg.Text("Stake")], [sg.Text("Minimum dds")]]
column_fields_under_condition = [[sg.InputText(key='BET_UNDER_CONDITION', size=(6, 1))],
                                 [sg.InputText(key='ODD_UNDER_CONDITION', size=(6, 1))]]
column_under_condition = [[sg.Column(column_text_under_condition),
                           sg.Column(column_fields_under_condition)],
                          [sg.Listbox(sports, size=(20, 6), key="SPORT_UNDER_CONDITION")]]
options_under_condition = [[sg.Text("Options")],
                           [sg.Checkbox("Minimum date/time ",
                                        key="DATE_MIN_UNDER_CONDITION_BOOL"),
                            sg.InputText(tooltip="DD/MM/YYYY", size=(12, 1),
                                         key="DATE_MIN_UNDER_CONDITION"),
                            sg.InputText(tooltip="HH:MM", size=(7, 1),
                                         key="TIME_MIN_UNDER_CONDITION")],
                           [sg.Checkbox("Maximum date/time", key="DATE_MAX_UNDER_CONDITION_BOOL"),
                            sg.InputText(tooltip="DD/MM/YYYY", size=(12, 1),
                                         key="DATE_MAX_UNDER_CONDITION"),
                            sg.InputText(tooltip="HH:MM", size=(7, 1),
                                         key="TIME_MAX_UNDER_CONDITION")],
                           [sg.Checkbox("Stakes to be spread over several outcomes of the same match",
                                        key="ONE_SITE_UNDER_CONDITION")]]
column_indicators_under_condition = [[sg.Text("", size=(15, 1),
                                              key="INDICATORS_UNDER_CONDITION" + str(_),
                                              visible=False)] for _ in range(5)]
column_results_under_condition = [[sg.Text("", size=(30, 1),
                                           key="RESULTS_UNDER_CONDITION" + str(_),
                                           visible=False)] for _ in range(5)]
match_under_condition_layout = [[sg.Listbox(sites, size=(20, 12), key="SITE_UNDER_CONDITION"),
                                 sg.Column(column_under_condition),
                                 sg.Column(options_under_condition)],
                                [sg.Button("Compute", key="BEST_MATCH_UNDER_CONDITION")],
                                [sg.Text("", size=(30, 1), key="MATCH_UNDER_CONDITION"),
                                 sg.Text("", size=(30, 1), key="DATE_UNDER_CONDITION")],
                                [sg.Table([["parionssport", "0000", "0000", "0000"]],
                                          headings=["Odds", "1", "X", "2"],
                                          key="ODDS_UNDER_CONDITION",
                                          visible=False, hide_vertical_scroll=True,
                                          size=(None, 12)),
                                 sg.Column([[sg.Text(
                                     "Distribution of stakes (the displayed amounts take into "
                                     "account possible freebets):",
                                     key="TEXT_UNDER_CONDITION", visible=False)],
                                     [sg.MLine(size=(100, 12), key="RESULT_UNDER_CONDITION",
                                               font="Consolas 10", visible=False)]])],
                                [sg.Column(column_indicators_under_condition),
                                 sg.Column(column_results_under_condition)]
                                ]

column_text_stake = [[sg.Text("Stake")], [sg.Text("Minimum odds")]]
column_fields_stake = [[sg.InputText(key='BET_STAKE', size=(6, 1))],
                       [sg.InputText(key='ODD_STAKE', size=(6, 1))]]
column_stake = [[sg.Column(column_text_stake), sg.Column(column_fields_stake)],
                [sg.Listbox(sports, size=(20, 6), key="SPORT_STAKE", enable_events=True)]]
column_indicators_stake = [[sg.Text("", size=(15, 1), key="INDICATORS_STAKE" + str(_),
                                    visible=False)] for _ in range(5)]
column_results_stake = [[sg.Text("", size=(30, 1), key="RESULTS_STAKE" + str(_),
                                 visible=False)] for _ in range(5)]
stake_layout = [
    [sg.Listbox(sites, size=(20, 12), key="SITE_STAKE"),
     sg.Column(column_stake),
     sg.Listbox([], size=(40, 12), key="MATCHES")],
    [sg.Button("Compute", key="BEST_STAKE")],
    [sg.Text("", size=(30, 1), key="MATCH_STAKE"),
     sg.Text("", size=(30, 1), key="DATE_STAKE")],
    [sg.Table([["parionssport", "0000", "0000", "0000"]], headings=["Odds", "1", "X", "2"],
              key="ODDS_STAKE", visible=False, hide_vertical_scroll=True, size=(None, 12)),
     sg.Column([[sg.Text(
         "Distribution of stakes (the displayed amounts take into account possible freebets):",
         key="TEXT_STAKE", visible=False)],
         [sg.MLine(size=(100, 12), key="RESULT_STAKE", font="Consolas 10", visible=False)]])],
    [sg.Column(column_indicators_stake),
     sg.Column(column_results_stake)]
]

column_freebet = [[sg.Text("Freebet"), sg.InputText(key='BET_FREEBET', size=(6, 1))],
                  [sg.Listbox(sports, size=(20, 6), key="SPORT_FREEBET")]]
column_indicators_freebet = [[sg.Text("", size=(15, 1), key="INDICATORS_FREEBET" + str(_),
                                      visible=False)] for _ in range(5)]
column_results_freebet = [[sg.Text("", size=(30, 1), key="RESULTS_FREEBET" + str(_),
                                   visible=False)] for _ in range(5)]
freebet_layout = [
    [sg.Listbox(sites, size=(20, 12), key="SITE_FREEBET"),
     sg.Column(column_freebet)],
    [sg.Button("Compute", key="BEST_MATCH_FREEBET")],
    [sg.Text("", size=(30, 1), key="MATCH_FREEBET"),
     sg.Text("", size=(30, 1), key="DATE_FREEBET")],
    [sg.Table([["parionssport", "0000", "0000", "0000"]],
              headings=["Odds", "1", "X", "2"], key="ODDS_FREEBET", visible=False,
              hide_vertical_scroll=True, size=(None, 12)),
     sg.Column([[sg.Text(
         "Distribution of stakes (the displayed amounts take into account possible freebets):",
         key="TEXT_FREEBET", visible=False)],
         [sg.MLine(size=(100, 12), key="RESULT_FREEBET", font="Consolas 10",
                   visible=False)]])],
    [sg.Column(column_indicators_freebet), sg.Column(column_results_freebet)]
]

column_text_cashback = [[sg.Text("Stake")], [sg.Text("Minimum odds")]]
column_fields_cashback = [[sg.InputText(key='BET_CASHBACK', size=(6, 1))],
                          [sg.InputText(key='ODD_CASHBACK', size=(6, 1))]]
column_cashback = [[sg.Column(column_text_cashback), sg.Column(column_fields_cashback)],
                   [sg.Listbox(sports, size=(20, 6), key="SPORT_CASHBACK")]]
options_cashback = [
    [sg.Text("Options", font="bold")],
    [sg.Checkbox("Cashback in freebet", default=True, key="FREEBET_CASHBACK")],
    [sg.Text("Cashback rate"), sg.InputText(size=(5, 1), key="RATE_CASHBACK",
                                                    default_text="100"), sg.Text("%")],
    [sg.Text("Bonus combo"), sg.InputText(size=(5, 1), key="COMBI_MAX_CASHBACK",
                                            default_text="0"), sg.Text("%")],
    [sg.Text("Combo odds"), sg.InputText(size=(5, 1), key="COMBI_ODD_CASHBACK",
                                           default_text="1")],
    [sg.Checkbox("Minimum date/time", key="DATE_MIN_CASHBACK_BOOL"),
     sg.InputText(tooltip="DD/MM/YYYY", size=(12, 1), key="DATE_MIN_CASHBACK"),
     sg.InputText(tooltip="HH:MM", size=(7, 1), key="TIME_MIN_CASHBACK")],
    [sg.Checkbox("Maximum date/time", key="DATE_MAX_CASHBACK_BOOL"),
     sg.InputText(tooltip="DD/MM/YYYY", size=(12, 1), key="DATE_MAX_CASHBACK"),
     sg.InputText(tooltip="HH:MM", size=(7, 1), key="TIME_MAX_CASHBACK")]
]
column_indicators_cashback = [[sg.Text("", size=(15, 1), key="INDICATORS_CASHBACK" + str(_),
                                       visible=False)] for _ in range(5)]
column_results_cashback = [[sg.Text("", size=(30, 1), key="RESULTS_CASHBACK" + str(_),
                                    visible=False)] for _ in range(5)]
cashback_layout = [
    [sg.Listbox(sites, size=(20, 12), key="SITE_CASHBACK"),
     sg.Column(column_cashback), sg.Column(options_cashback)],
    [sg.Button("Compute", key="BEST_MATCH_CASHBACK")],
    [sg.Text("", size=(30, 1), key="MATCH_CASHBACK"),
     sg.Text("", size=(30, 1), key="DATE_CASHBACK")],
    [sg.Table([["parionssport", "0000", "0000", "0000"]],
              headings=["Odds", "1", "X", "2"], key="ODDS_CASHBACK", visible=False,
              hide_vertical_scroll=True, size=(None, 12)),
     sg.Column([[sg.Text(
         "Distribution of stakes (the displayed amounts take into account possible freebets):",
         key="TEXT_CASHBACK", visible=False)],
         [sg.MLine(size=(100, 12), key="RESULT_CASHBACK", font="Consolas 10",
                   visible=False)]])],
    [sg.Column(column_indicators_cashback), sg.Column(column_results_cashback)]
]

column_text_combine = [[sg.Text("Stake")],
                       [sg.Text("Minimum odds")],
                       [sg.Text("Number of matches")],
                       [sg.Text("Minimum odds per match")]]
column_fields_combine = [[sg.InputText(key='BET_COMBINE', size=(6, 1))],
                         [sg.InputText(key='ODD_COMBINE', size=(6, 1))],
                         [sg.InputText(key='NB_MATCHES_COMBINE', size=(6, 1), default_text="2")],
                         [sg.InputText(key='ODD_SELECTION_COMBINE', size=(6, 1),
                                       default_text="1.01")]]
column_combine = [[sg.Column(column_text_combine), sg.Column(column_fields_combine)],
                  [sg.Listbox(sports, size=(20, 6), key="SPORT_COMBINE")]]
options_combine = [[sg.Text("Options")],
                   [sg.Checkbox("Minimum date/time ", key="DATE_MIN_COMBINE_BOOL"),
                    sg.InputText(tooltip="DD/MM/YYYY", size=(12, 1), key="DATE_MIN_COMBINE"),
                    sg.InputText(tooltip="HH:MM", size=(7, 1), key="TIME_MIN_COMBINE")],
                   [sg.Checkbox("Maximum date/time", key="DATE_MAX_COMBINE_BOOL"),
                    sg.InputText(tooltip="DD/MM/YYYY", size=(12, 1), key="DATE_MAX_COMBINE"),
                    sg.InputText(tooltip="HH:MM", size=(7, 1), key="TIME_MAX_COMBINE")],
                   [sg.Checkbox("Stakes to be spread over several outcomes of the same match",
                                key="ONE_SITE_COMBINE")]]
column_indicators_combine = [[sg.Text("", size=(15, 1), key="INDICATORS_COMBINE" + str(_),
                                      visible=False)] for _ in range(5)]
column_results_combine = [[sg.Text("", size=(6, 1), key="RESULTS_COMBINE" + str(_),
                                   visible=False)] for _ in range(5)]
combine_layout = [[sg.Listbox(sites, size=(20, 12), key="SITE_COMBINE"), sg.Column(column_combine),
                   sg.Column(options_combine)],
                  [sg.Button("Compute", key="BEST_MATCHES_COMBINE"),
                   sg.ProgressBar(100, orientation='h', size=(20, 20), key='PROGRESS_COMBINE', visible=False)],
                  [sg.Text("", size=(100, 1), key="MATCH_COMBINE")],
                  [sg.Text("", size=(30, 1), key="DATE_COMBINE")],
                  [sg.Column([[sg.Button("All the odds", key="ODDS_COMBINE",
                                         visible=False)],
                              [sg.Column(column_indicators_combine),
                               sg.Column(column_results_combine)]]),
                   sg.Column([[sg.Text(
                       "Distribution of stakes (the displayed amounts take into account possible "
                       "freebets):",
                       key="TEXT_COMBINE", visible=False)],
                       [sg.MLine(size=(120, 12), key="RESULT_COMBINE", font="Consolas 10",
                                 visible=False)]])
                   ]]

column_stakes = [[sg.Text("Bookmaker"), sg.Text("Stakes")],
                 [sg.Combo(sites, key="SITE_STAKES_0"),
                  sg.Input(key="STAKE_STAKES_0", size=(6, 1))],
                 *([sg.Combo(sites, key="SITE_STAKES_" + str(i), visible=False),
                    sg.Input(key="STAKE_STAKES_" + str(i), size=(6, 1), visible=False)]
                   for i in range(1, 9)),
                 [sg.Button("Delete stake", key="REMOVE_STAKES"),
                  sg.Button("Add stake", key="ADD_STAKES")]]

visible_stakes = 1
column_indicators_stakes = [[sg.Text("", size=(15, 1), key="INDICATORS_STAKES" + str(_),
                                     visible=False)] for _ in range(5)]
column_results_stakes = [[sg.Text("", size=(6, 1), key="RESULTS_STAKES" + str(_),
                                  visible=False)] for _ in range(5)]
stakes_layout = [
    [sg.Text("Bookmaker\t"), sg.Text("Stake"), sg.Text("Minimum odds"),
     sg.Button("Delete stake", key="REMOVE_STAKES"), sg.Text("Number of matches"),
     sg.Spin([i for i in range(1, 4)], initial_value=1, key="NB_MATCHES_STAKES"),
     sg.Text("Sport"),
     sg.Combo(sports, default_value="football", key="SPORT_STAKES")],
    [sg.Col([[sg.Combo(sites, key="SITE_STAKES_0")]]),
     sg.Col([[sg.Input(key="STAKE_STAKES_0", size=(6, 1))]]),
     sg.Col([[sg.Input(key="ODD_STAKES_0", size=(6, 1))]]),
     sg.Button("Add stake", key="ADD_STAKES"),
     sg.Checkbox("Maximum date/time", key="DATE_MAX_STAKES_BOOL"),
     sg.InputText(tooltip="DD/MM/YYYY", size=(12, 1), key="DATE_MAX_STAKES"),
     sg.InputText(tooltip="HH:MM", size=(7, 1), key="TIME_MAX_STAKES")],
    *([sg.Col([[sg.Combo(sites, key="SITE_STAKES_" + str(i), visible=False)]]),
       sg.Col([[sg.Input(key="STAKE_STAKES_" + str(i), size=(6, 1), visible=False)]]),
       sg.Col([[sg.Input(key="ODD_STAKES_" + str(i), size=(6, 1), visible=False)]])]
      for i in range(1, 9)),
    [sg.Button("Compute", key="BEST_MATCH_STAKES"),
     sg.ProgressBar(100, orientation='h', size=(20, 20), key='PROGRESS_STAKES', visible=False)],
    [sg.Text("", size=(100, 1), key="MATCH_STAKES")],
    [sg.Text("", size=(30, 1), key="DATE_STAKES")],
    [sg.Column([[sg.Button("All the odds", key="ODDS_STAKES", visible=False)],
                [sg.Column(column_indicators_stakes),
                 sg.Column(column_results_stakes)]
                ]),
     sg.Column([[sg.Text(
         "Distribution of stakes (the displayed amounts take into account possible freebets):",
         key="TEXT_STAKES", visible=False)],
         [sg.MLine(size=(120, 12), key="RESULT_STAKES", font="Consolas 10", visible=False)]])
     ]]

column_sites_freebets = [[sg.Text("Bookmaker")],
                         [sg.Combo(sites, key="SITE_FREEBETS_0")],
                         *([sg.Combo(sites, key="SITE_FREEBETS_" + str(i),
                                     visible=False)] for i in range(1, 9)),
                         [sg.Button("Add stake", key="ADD_FREEBETS")]]

column_freebets_freebets = [[sg.Text("Stakes")],
                            [sg.Input(key="STAKE_FREEBETS_0", size=(6, 1))],
                            *([sg.Input(key="STAKE_FREEBETS_" + str(i), size=(6, 1),
                                        visible=False)] for i in range(1, 9)),
                            [sg.Button("Delete stake", key="REMOVE_FREEBETS")]]

visible_freebets = 1

column_indicators_freebets = [[sg.Text("", size=(15, 1), key="INDICATORS_FREEBETS" + str(_),
                                       visible=False)] for _ in range(5)]

column_results_freebets = [[sg.Text("", size=(6, 1), key="RESULTS_FREEBETS" + str(_),
                                    visible=False)] for _ in range(5)]

freebets_layout = [[sg.Column(column_sites_freebets),
                    sg.Column(column_freebets_freebets),
                    sg.Listbox(sites, size=(20, 12), key="SITES_FREEBETS", select_mode='multiple')],
                   [sg.Button("Compute", key="BEST_MATCH_FREEBETS")],
                   [sg.Text("", size=(100, 1), key="MATCH_FREEBETS")],
                   [sg.Text("", size=(30, 1), key="DATE_FREEBETS")],
                   [sg.Column([[sg.Button("All the odds", key="ODDS_FREEBETS",
                                          visible=False)],
                               [sg.Column(column_indicators_freebets),
                                sg.Column(column_results_freebets)]
                               ]),
                    sg.Column([[sg.Text(
                        "Distribution of stakes (the displayed amounts take into account possible "
                        "freebets):",
                        key="TEXT_FREEBETS", visible=False)],
                        [sg.MLine(size=(120, 12), key="RESULT_FREEBETS", font="Consolas 10",
                                  visible=False)]])
                    ]]

column_text_gagnant = [[sg.Text("Stake")], [sg.Text("Minimum odds")]]
column_fields_gagnant = [[sg.InputText(key='BET_GAGNANT', size=(6, 1))],
                         [sg.InputText(key='ODD_GAGNANT', size=(6, 1))]]
column_gagnant = [[sg.Column(column_text_gagnant), sg.Column(column_fields_gagnant)],
                  [sg.Listbox(sports, size=(20, 6), key="SPORT_GAGNANT")]]
options_gagnant = [[sg.Text("Options")],
                   [sg.Checkbox("Minimum date/time ", key="DATE_MIN_GAGNANT_BOOL"),
                    sg.InputText(tooltip="DD/MM/YYYY", size=(12, 1), key="DATE_MIN_GAGNANT"),
                    sg.InputText(tooltip="HH:MM", size=(7, 1), key="TIME_MIN_GAGNANT")],
                   [sg.Checkbox("Maximum date/time", key="DATE_MAX_GAGNANT_BOOL"),
                    sg.InputText(tooltip="DD/MM/YYYY", size=(12, 1), key="DATE_MAX_GAGNANT"),
                    sg.InputText(tooltip="HH:MM", size=(7, 1), key="TIME_MAX_GAGNANT")],
                   [sg.Text("Number of matches"), sg.Spin([i for i in range(1, 4)], initial_value=1, key="NB_MATCHES_GAGNANT")]]
column_indicators_gagnant = [[sg.Text("", size=(15, 1), key="INDICATORS_GAGNANT" + str(_),
                                      visible=False)] for _ in range(5)]
column_results_gagnant = [[sg.Text("", size=(30, 1), key="RESULTS_GAGNANT" + str(_),
                                   visible=False)] for _ in range(5)]
gagnant_layout = [
    [sg.Listbox(sites, size=(20, 12), key="SITE_GAGNANT"),
     sg.Column(column_gagnant),
     sg.Column(options_gagnant)],
    [sg.Button("Compute", key="BEST_MATCH_GAGNANT")],
    [sg.Text("", size=(60, 1), key="MATCH_GAGNANT")],
    [sg.Text("", size=(30, 1), key="DATE_GAGNANT")],
    [sg.Column([[sg.Table([["parionssport", "0000", "0000", "0000"]], headings=["Odds", "1", "X", "2"],
              key="ODDS_GAGNANT", visible=False, hide_vertical_scroll=True, size=(None, 12))],
     [sg.Button("All the odds", key="ODDS_COMBINE_GAGNANT", visible=False)]]),
     sg.Column([[sg.Text(
         "Distribution of stakes (the displayed amounts take into account possible freebets):",
         key="TEXT_GAGNANT", visible=False)],
         [sg.MLine(size=(90, 12), key="RESULT_GAGNANT", font="Consolas 10",
                   visible=False)]])],
    [sg.Column(column_indicators_gagnant),
     sg.Column(column_results_gagnant)]
]

odds_layout = [
    [sg.Listbox(sports, size=(20, 6), key="SPORT_ODDS", enable_events=True),
     sg.Listbox([], size=(40, 12), key="MATCHES_ODDS", enable_events=True),
     sg.Col([[sg.Text("", size=(30, 1), key="MATCH_ODDS", visible=False)],
             [sg.Text("", size=(30, 1), key="DATE_ODDS", visible=False)],
             [sg.Table([["parionssport", "0000", "0000", "0000"]],
                       headings=["Odds", "1", "X", "2"], key="ODDS_ODDS", visible=False,
                       hide_vertical_scroll=True, size=(None, 12))],
             [sg.Button("Delete match", key="DELETE_ODDS", visible=False)]])
     ]
]

visible_combi_opt = 1
column_indicators_combi_opt = [[sg.Text("", size=(15, 1), key="INDICATORS_COMBI_OPT" + str(_),
                                     visible=False)] for _ in range(5)]
column_results_combi_opt = [[sg.Text("", size=(6, 1), key="RESULTS_COMBI_OPT" + str(_),
                                  visible=False)] for _ in range(5)]
column_text_combi_opt = [[sg.Text("Maximum stake")], [sg.Text("Boosted odds")], [sg.Text("Bookmaker boosted")]]
column_fields_combi_opt = [[sg.InputText(key='STAKE_COMBI_OPT', size=(6, 1))],
                                 [sg.InputText(key='ODD_COMBI_OPT', size=(6, 1))],
                                 [sg.Combo(sites, key="SITE_COMBI_OPT")]]
column_combi_opt = [[sg.Column(column_text_combi_opt),
                           sg.Column(column_fields_combi_opt)]]

combi_opt_layout = [
    [sg.Column(column_combi_opt), sg.Listbox(sports, size=(20, 6), key="SPORT_COMBI_OPT", enable_events=True)],
    [sg.Text("Match"),
     sg.Button("Delete match", key="REMOVE_COMBI_OPT"),
     sg.Button("Add match", key="ADD_COMBI_OPT"),  sg.Text("\t\t\t\tBoosted outcome")],
    [sg.Col([[sg.Combo([], size=(60, 10), key="MATCH_COMBI_OPT_0")]]),
     sg.Col([[sg.Radio('1', "RES_COMBI_OPT_0", key="1_RES_COMBI_OPT_0", default=True)]]),
     sg.Col([[sg.Radio('X', "RES_COMBI_OPT_0", key="N_RES_COMBI_OPT_0")]]),
     sg.Col([[sg.Radio('2', "RES_COMBI_OPT_0", key="2_RES_COMBI_OPT_0")]])],
     *([sg.Col([[sg.Combo([], size=(60, 10), key="MATCH_COMBI_OPT_" + str(i), visible=False)]]),
     sg.Col([[sg.Radio('1', "RES_COMBI_OPT_" + str(i), key="1_RES_COMBI_OPT_" + str(i), visible=False, default=True)]]),
     sg.Col([[sg.Radio('X', "RES_COMBI_OPT_" + str(i), key="N_RES_COMBI_OPT_" + str(i), visible=False)]]),
     sg.Col([[sg.Radio('2', "RES_COMBI_OPT_" + str(i), key="2_RES_COMBI_OPT_" + str(i), visible=False)]])]
     for i in range(1,9)),
    [sg.Button("Compute", key="BEST_COMBI_OPT")],
    [sg.Text("", size=(100, 1), key="MATCH_COMBI_OPT")],
    [sg.Text("", size=(30, 1), key="DATE_COMBI_OPT")],
    [sg.Column([[sg.Button("All the odds", key="ODDS_COMBI_OPT", visible=False)],
                [sg.Column(column_indicators_combi_opt),
                 sg.Column(column_results_combi_opt)]
                ]),
     sg.Column([[sg.Text(
         "Distribution of stakes (the displayed amounts take into account possible freebets):",
         key="TEXT_COMBI_OPT", visible=False)],
         [sg.MLine(size=(120, 12), key="RESULT_COMBI_OPT", font="Consolas 10", visible=False)]])
     ]]

layout = [[sg.TabGroup([[sg.Tab('Odds retrieval', parsing_layout),
                         sg.Tab('Odds', odds_layout),
                         sg.Tab('Simple stake', match_under_condition_layout),
                         sg.Tab('Stake on a given match', stake_layout),
                         sg.Tab('Cashback', cashback_layout),
                         sg.Tab('Winning bet', gagnant_layout),
                         sg.Tab('Combo', combine_layout),
                         sg.Tab('Unique freebet', freebet_layout),
                         sg.Tab('Several freebets', freebets_layout),
                         sg.Tab('Boosted odds on combo', combi_opt_layout)
                         ]])],
          [sg.Button('Exit', button_color=("white", "red"))]]

# Create the Window
window = sg.Window('Sports betting', layout, location=(0, 0))
event, values = window.read(timeout=0)
sportsbetting.PROGRESS = 0
thread = None
thread_stakes = None
thread_combine = None
window_odds_active = False
sport = ''
old_stdout = sys.stdout
window_odds = None
sportsbetting.INTERFACE = True
start_time = time.time()
elapsed_time = 0
start_parsing = 0
palier = 0

# Event Loop to process "events" and get the "values" of the inputs
while True:
    event, values = window.read(timeout=100)
    try:
        if sportsbetting.ABORT or not thread.is_alive():
            pickle.dump(sportsbetting.ODDS, open(PATH_DATA, "wb"))
            window['PROGRESS_PARSING'].update(0, 100, visible=False)
            window["TEXT_PARSING"].update(visible=sportsbetting.ABORT)
            window["REMAINING_TIME_PARSING"].update(visible=False)
            window["STOP_PARSING"].update(visible=False)
            window["START_PARSING"].update(visible=True)
            for site in sites:
                window["TEXT_{}_PARSING".format(site)].update(visible=False)
                window["PROGRESS_{}_PARSING".format(site)].update(0, 100, visible=False)
            if not sportsbetting.ABORT:
                sg.SystemTray.notify('Sports-betting', 'Odds retrieval finished', display_duration_in_ms=750,
                                    fade_in_duration=125)
                thread = None
                print(elapsed_time)
        else:
            window['PROGRESS_PARSING'].update(ceil(sportsbetting.PROGRESS), 100)
            for site in sites:
                (window["PROGRESS_{}_PARSING".format(site)]
                 .update(ceil(sportsbetting.SITE_PROGRESS[site]), 100))
            now = time.time()
            if sportsbetting.IS_PARSING and not start_parsing:
                start_parsing = now
            elapsed_time = now - start_time
            elapsed_time_parsing = now - start_parsing
            if sportsbetting.IS_PARSING and sportsbetting.PROGRESS > palier:
                palier += 5
                sportsbetting.EXPECTED_TIME = elapsed_time * (100 / sportsbetting.PROGRESS - 1)
                time_to_display = sportsbetting.EXPECTED_TIME
                start_parsing = time.time()
            else:
                if start_parsing:
                    window["TEXT_PARSING"].update("Odds retrieval in progress")
                    time_to_display = sportsbetting.EXPECTED_TIME - elapsed_time_parsing
                    window["REMAINING_TIME_PARSING"].update(visible=True)
                else:
                    window["TEXT_PARSING"].update("Initialisation of selenium in progres")
                    time_to_display = sportsbetting.EXPECTED_TIME - elapsed_time
            # sportsbetting.EXPECTED_TIME = int(max(0, sportsbetting.EXPECTED_TIME - 0.1))
            m, s = divmod(max(0, int(time_to_display)), 60)
            window["REMAINING_TIME_PARSING"].update('{:02d}:{:02d}'.format(int(m), int(s)))
            if sportsbetting.IS_PARSING and 100 - sportsbetting.PROGRESS < 1e-6:
                window["TEXT_PARSING"].update("Finalisation")
                window["REMAINING_TIME_PARSING"].update(visible=False)
    except AttributeError:
        pass
    try:
        if not thread_stakes.is_alive():
            window["PROGRESS_STAKES"].update(0, 100, visible=False)
            thread_stakes = None
        else:
            window["PROGRESS_STAKES"].update(ceil(sportsbetting.PROGRESS), 100)
    except AttributeError:
        pass
    try:
        if not thread_combine.is_alive():
            window["PROGRESS_COMBINE"].update(0, 100, visible=False)
            thread_combine = None
        else:
            window["PROGRESS_COMBINE"].update(ceil(sportsbetting.PROGRESS), 100)
    except AttributeError:
        pass
    try:  # see if something has been posted to Queue
        message = sportsbetting.QUEUE_TO_GUI.get_nowait()
        sportsbetting.QUEUE_FROM_GUI.put(sg.popup_yes_no(message))
    except queue.Empty:  # get_nowait() will get exception when Queue is empty
        pass  # break from the loop if no more messages are queued up
    if event == "SPORT":
        sport = values["SPORT"][0]
        competitions = get_all_competitions(sport)
        window['COMPETITIONS'].update(values=competitions)
    elif event == "SELECT_NONE_COMPETITION":
        window['COMPETITIONS'].update(set_to_index=[])
    elif event == "CURRENT_COMPETITIONS":
        thread_competitions = threading.Thread(target=lambda : get_current_competitions_interface(window, values))
        thread_competitions.start()
    elif event == "MAIN_COMPETITIONS":
        get_main_competitions_interface(window, values)
    elif event == "SELECT_ALL":
        window['SITES'].update(set_to_index=[i for i, _ in enumerate(sites)])
    elif event == "SELECT_NONE_SITE":
        window['SITES'].update(set_to_index=[])
    elif event == 'START_PARSING':
        selected_competitions = values["COMPETITIONS"]
        selected_sites = values["SITES"]
        window["MATCHES_ODDS"].update([])
        window["MATCHES"].update([])
        if selected_competitions and selected_sites:
            window["STOP_PARSING"].update(visible=True)
            window["START_PARSING"].update(visible=False)
            def parse_thread():
                """
                :return: Crée un thread pour le parsing des compétitions
                """
                sportsbetting.PROGRESS = 0
                parse_competitions(selected_competitions, sport, *selected_sites)


            thread = threading.Thread(target=parse_thread)
            thread.start()
            start_time = time.time()
            start_parsing = 0
            palier = 20
            window['PROGRESS_PARSING'].update(0, 100, visible=True)
            window["TEXT_PARSING"].update(visible=True)
            window["REMAINING_TIME_PARSING"].update(sportsbetting.EXPECTED_TIME)
            sportsbetting.SITE_PROGRESS = collections.defaultdict(int)
            for site in selected_sites:
                window["TEXT_{}_PARSING".format(site)].update(visible=True)
                window["PROGRESS_{}_PARSING".format(site)].update(0, 100, visible=True)
    elif event == "STOP_PARSING":
        window["STOP_PARSING"].update(visible=False)
        window["TEXT_PARSING"].update("Interruption en cours")
        sportsbetting.ABORT = True
    elif event == "BEST_MATCH_UNDER_CONDITION":
        best_match_under_conditions_interface(window, values)
    elif event == "SPORT_STAKE":
        try:
            matches = sorted(list(sportsbetting.ODDS[values["SPORT_STAKE"][0]]))
            window['MATCHES'].update(values=matches)
        except KeyError:
            window['MATCHES'].update(values=[])
    elif event == "BEST_STAKE":
        best_stakes_match_interface(window, values)
    elif event == "BEST_MATCH_FREEBET":
        best_match_freebet_interface(window, values)
    elif event == "BEST_MATCH_CASHBACK":
        best_match_cashback_interface(window, values)
    elif event == "BEST_MATCHES_COMBINE":
        def combine_thread():
            best_matches_combine_interface(window, values)


        thread_combine = threading.Thread(target=combine_thread)
        thread_combine.start()
        window["PROGRESS_COMBINE"].update(0, 100, visible=True)
    elif not window_odds_active and event in ["ODDS_COMBINE", "ODDS_STAKES", "ODDS_FREEBETS", "ODDS_COMBI_OPT", "ODDS_COMBINE_GAGNANT"]:
        window_odds_active = True
        table = odds_table_combine(sportsbetting.ODDS_INTERFACE)
        layout_odds = [[sg.Table(table[1:], headings=table[0], size=(None, 20))]]
        window_odds = sg.Window('Odds', layout_odds)
    elif window_odds_active:
        ev2, vals2 = window_odds.Read(timeout=100)
        if ev2 is None or ev2 == 'Exit':
            window_odds_active = False
            window_odds.close()
    elif event == "ADD_STAKES":
        if visible_stakes < 9:
            window["SITE_STAKES_" + str(visible_stakes)].update(visible=True)
            window["STAKE_STAKES_" + str(visible_stakes)].update(visible=True)
            window["ODD_STAKES_" + str(visible_stakes)].update(visible=True)
            visible_stakes += 1
    elif event == "REMOVE_STAKES":
        if visible_stakes > 1:
            visible_stakes -= 1
            window["SITE_STAKES_" + str(visible_stakes)].update(visible=False)
            window["STAKE_STAKES_" + str(visible_stakes)].update(visible=False)
            window["ODD_STAKES_" + str(visible_stakes)].update(visible=False)
    elif event == "BEST_MATCH_STAKES":
        def stakes_thread():
            best_match_stakes_to_bet_interface(window, values, visible_stakes)


        thread_stakes = threading.Thread(target=stakes_thread)
        thread_stakes.start()
        window["PROGRESS_STAKES"].Update(visible=True)
    elif event == "ADD_FREEBETS":
        if visible_freebets < 9:
            window["SITE_FREEBETS_" + str(visible_freebets)].update(visible=True)
            window["STAKE_FREEBETS_" + str(visible_freebets)].update(visible=True)
            visible_freebets += 1
    elif event == "REMOVE_FREEBETS":
        if visible_freebets > 1:
            visible_freebets -= 1
            window["SITE_FREEBETS_" + str(visible_freebets)].update(visible=False)
            window["STAKE_FREEBETS_" + str(visible_freebets)].update(visible=False)
    elif event == "BEST_MATCH_FREEBETS":
        sportsbetting.ODDS_INTERFACE = best_matches_freebet_interface(window, values,
                                                                      visible_freebets)
    elif event == "BEST_MATCH_GAGNANT":
        best_match_pari_gagnant_interface(window, values)
    elif event == "SPORT_ODDS":
        try:
            matches = sorted(list(sportsbetting.ODDS[values["SPORT_ODDS"][0]]))
            window['MATCHES_ODDS'].update(values=matches)
        except KeyError:
            window['MATCHES_ODDS'].update(values=[])
    elif event == "MATCHES_ODDS":
        odds_match_interface(window, values)
    elif event == "DELETE_ODDS":
        delete_odds_interface(window, values)
        pickle.dump(sportsbetting.ODDS, open(PATH_DATA, "wb"))
    elif event == "ADD_COMBI_OPT":
        sport = ""
        if values["SPORT_COMBI_OPT"]:
            sport = values["SPORT_COMBI_OPT"][0]
        if visible_combi_opt < 9:
            window["MATCH_COMBI_OPT_" + str(visible_combi_opt)].update(visible=True)
            issues = ["1", "N", "2"] if sport and get_nb_outcomes(sport) == 3 else ["1", "2"]
            for issue in issues:
                window[issue+"_RES_COMBI_OPT_" + str(visible_combi_opt)].update(visible=True)
            visible_combi_opt += 1
    elif event == "REMOVE_COMBI_OPT":
        if visible_combi_opt > 1:
            visible_combi_opt -= 1
            window["MATCH_COMBI_OPT_" + str(visible_combi_opt)].update(visible=False)
            for issue in ["1", "N", "2"]:
                window[issue+"_RES_COMBI_OPT_" + str(visible_combi_opt)].update(visible=False)
    elif event == "BEST_COMBI_OPT":
        best_combine_reduit_interface(window, values, visible_combi_opt)
    elif event == "SPORT_COMBI_OPT":
        sport = values["SPORT_COMBI_OPT"][0]
        for i in range(visible_combi_opt):
            if get_nb_outcomes(sport) == 2:
                window["N_RES_COMBI_OPT_"+str(i)].update(visible=False)
            elif get_nb_outcomes(sport) == 3:
                window["N_RES_COMBI_OPT_"+str(i)].update(visible=True)
        for i in range(9):
            if sport in sportsbetting.ODDS:
                matches = sorted(list(sportsbetting.ODDS[sport]))
                window['MATCH_COMBI_OPT_'+str(i)].update(values=matches)
            else:
                window['MATCH_COMBI_OPT_'+str(i)].update(values=[])
                sg.Popup("No match available in {}".format(sport))
                break
    elif event in (None, 'Exit'):  # if user closes window or clicks cancel
        break
    else:
        pass
sportsbetting.INTERFACE = False
window.close()
sys.stdout = old_stdout
