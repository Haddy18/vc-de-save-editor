#!/usr/bin/env python3
"""GTA Vice City: Definitive Edition — 100% Save Editor :: 100% save editor

Load a .sav, show the full GTASnP 100% checklist (missions, side missions,
collectibles, properties) with a checkbox per item, recompute the
percentage (x/154) and the story-mission count, and save the file
with the correct MD5 seal in the header (without it the game shows an
empty slot with no error at all).

Standard library only. No dependencies.

Format (verified against 6 real saves written by the game itself):
  seal      = NOT(MD5( first 24 bytes zeroed + file[24:] )) at 0x08..0x17
  globals   = base = position of `b"SCR\\x00"` + 0x14
               (byte index comes from the two zlib tables the save itself
               carries: "//Globalvariables V2 ...")
  flags     = 1 byte (0/1) at base + index
  counters  = u32 at base + index
  percent   = float32 at base + index (the GAME_PERCENTAGE global)

Usage:
  GUI:       python vc_save_editor.py
  Selftest:  python vc_save_editor.py --selftest
"""

import base64
import hashlib
import json
import os
import re
import struct
import sys
import zlib


# ---------------------------------------------------------------- data
# Checklist + backing save locations. The story/asset/side variables
# come from the game's own scripts (SCFIX-Miami decompilation and the
# Definitive Edition scripts) and are checked against GTASnP's state for
# the sample saves in samples/. Rows whose variable is not documented
# here have no "src" and are shown read-only in the GUI.

DATA = json.loads(r"""{"game":"VC","denom":154,"pctg":"GAME_PERCENTAGE","tag":"SCR\u0000","items":[{"key":"Story Missions|Beach Island|An Old Friend","sec":"Story Missions","sub":"Beach Island","disp":"An Old Friend","kind":"flag","src":"FLAG_HOTEL_MISSION1_PASSED","w":1.0,"max":null},{"key":"Story Missions|Beach Island|The Party","sec":"Story Missions","sub":"Beach Island","disp":"The Party","kind":"flag","src":"FLAG_LAWYER_MISSION1_PASSED","w":1.0,"max":null},{"key":"Story Missions|Beach Island|Back Alley Brawl","sec":"Story Missions","sub":"Beach Island","disp":"Back Alley Brawl","kind":"flag","src":"FLAG_LAWYER_MISSION2_PASSED","w":1.0,"max":null},{"key":"Story Missions|Beach Island|Jury Fury","sec":"Story Missions","sub":"Beach Island","disp":"Jury Fury","kind":"flag","src":"FLAG_LAWYER_MISSION3_PASSED","w":1.0,"max":null},{"key":"Story Missions|Beach Island|Riot","sec":"Story Missions","sub":"Beach Island","disp":"Riot","kind":"flag","src":"FLAG_LAWYER_MISSION4_PASSED","w":1.0,"max":null},{"key":"Story Missions|Beach Island|Four Iron","sec":"Story Missions","sub":"Beach Island","disp":"Four Iron","kind":"flag","src":"FLAG_SERGIO_MISSION1_PASSED","w":1.0,"max":null},{"key":"Story Missions|Beach Island|Demolition Man","sec":"Story Missions","sub":"Beach Island","disp":"Demolition Man","kind":"flag","src":"FLAG_SERGIO_MISSION2_PASSED","w":1.0,"max":null},{"key":"Story Missions|Beach Island|Treacherous Swine","sec":"Story Missions","sub":"Beach Island","disp":"Treacherous Swine","kind":"flag","src":"FLAG_GENERAL_MISSION1_PASSED","w":1.0,"max":null},{"key":"Story Missions|Beach Island|Mall Shootout","sec":"Story Missions","sub":"Beach Island","disp":"Mall Shootout","kind":"flag","src":"FLAG_GENERAL_MISSION2_PASSED","w":1.0,"max":null},{"key":"Story Missions|Beach Island|Guardian Angels","sec":"Story Missions","sub":"Beach Island","disp":"Guardian Angels","kind":"flag","src":"FLAG_GENERAL_MISSION3_PASSED","w":1.0,"max":null},{"key":"Story Missions|Beach Island|The Chase","sec":"Story Missions","sub":"Beach Island","disp":"The Chase","kind":"flag","src":"FLAG_BARON_MISSION1_PASSED","w":1.0,"max":null},{"key":"Story Missions|Beach Island|Phnom Penh '86","sec":"Story Missions","sub":"Beach Island","disp":"Phnom Penh '86","kind":"flag","src":"FLAG_BARON_MISSION2_PASSED","w":1.0,"max":null},{"key":"Story Missions|Gang Mission|Stunt Boat Challenge","sec":"Story Missions","sub":"Gang Mission","disp":"Stunt Boat Challenge","kind":"flag","src":"FLAG_CUBAN_MISSION1_PASSED","w":1.0,"max":null},{"key":"Story Missions|Gang Mission|Cannon Fodder","sec":"Story Missions","sub":"Gang Mission","disp":"Cannon Fodder","kind":"flag","src":"FLAG_CUBAN_MISSION2_PASSED","w":1.0,"max":null},{"key":"Story Missions|Gang Mission|Naval Engagement","sec":"Story Missions","sub":"Gang Mission","disp":"Naval Engagement","kind":"flag","src":"FLAG_CUBAN_MISSION3_PASSED","w":1.0,"max":null},{"key":"Story Missions|Gang Mission|Trojan Voodoo","sec":"Story Missions","sub":"Gang Mission","disp":"Trojan Voodoo","kind":"flag","src":"FLAG_CUBAN_MISSION4_PASSED","w":1.0,"max":null},{"key":"Story Missions|Gang Mission|Juju Scramble","sec":"Story Missions","sub":"Gang Mission","disp":"Juju Scramble","kind":"flag","src":"FLAG_HAITIAN_MISSION1_PASSED","w":1.0,"max":null},{"key":"Story Missions|Gang Mission|Bombs Away!","sec":"Story Missions","sub":"Gang Mission","disp":"Bombs Away!","kind":"flag","src":"FLAG_HAITIAN_MISSION2_PASSED","w":1.0,"max":null},{"key":"Story Missions|Gang Mission|Dirty Lickin's","sec":"Story Missions","sub":"Gang Mission","disp":"Dirty Lickin's","kind":"flag","src":"FLAG_HAITIAN_MISSION3_PASSED","w":1.0,"max":null},{"key":"Story Missions|Gang Mission|Love Juice","sec":"Story Missions","sub":"Gang Mission","disp":"Love Juice","kind":"flag","src":"FLAG_ROCK_MISSION1_PASSED","w":1.0,"max":null},{"key":"Story Missions|Gang Mission|Psycho Killer","sec":"Story Missions","sub":"Gang Mission","disp":"Psycho Killer","kind":"flag","src":"FLAG_ROCK_MISSION2_PASSED","w":1.0,"max":null},{"key":"Story Missions|Gang Mission|Publicity Tour","sec":"Story Missions","sub":"Gang Mission","disp":"Publicity Tour","kind":"flag","src":"FLAG_ROCK_MISSION3_PASSED","w":1.0,"max":null},{"key":"Story Missions|Gang Mission|Alloy Wheels of Steel","sec":"Story Missions","sub":"Gang Mission","disp":"Alloy Wheels of Steel","kind":"flag","src":"FLAG_BIKERS_MISSION1_PASSED","w":1.0,"max":null},{"key":"Story Missions|Gang Mission|Messing With The Man","sec":"Story Missions","sub":"Gang Mission","disp":"Messing With The Man","kind":"flag","src":"FLAG_BIKERS_MISSION2_PASSED","w":1.0,"max":null},{"key":"Story Missions|Gang Mission|Hog Tied","sec":"Story Missions","sub":"Gang Mission","disp":"Hog Tied","kind":"flag","src":"FLAG_BIKERS_MISSION3_PASSED","w":1.0,"max":null},{"key":"Story Missions|Mainland Island|The Fastest Boat","sec":"Story Missions","sub":"Mainland Island","disp":"The Fastest Boat","kind":"flag","src":"FLAG_BARON_MISSION3_PASSED","w":1.0,"max":null},{"key":"Story Missions|Mainland Island|Supply & Demand","sec":"Story Missions","sub":"Mainland Island","disp":"Supply & Demand","kind":"flag","src":"FLAG_BARON_MISSION4_PASSED","w":1.0,"max":null},{"key":"Story Missions|Mainland Island|Two Bit Hit","sec":"Story Missions","sub":"Mainland Island","disp":"Two Bit Hit","kind":"flag","src":"FLAG_SERGIO_MISSION3_PASSED","w":1.0,"max":null},{"key":"Story Missions|Mainland Island|Sir, Yes Sir!","sec":"Story Missions","sub":"Mainland Island","disp":"Sir, Yes Sir!","kind":"flag","src":"FLAG_GENERAL_MISSION4_PASSED","w":1.0,"max":null},{"key":"Story Missions|Mainland Island|Death Row","sec":"Story Missions","sub":"Mainland Island","disp":"Death Row","kind":"flag","src":"FLAG_KENT_MISSION1_PASSED","w":1.0,"max":null},{"key":"Story Missions|Mainland Island|Rub Out","sec":"Story Missions","sub":"Mainland Island","disp":"Rub Out","kind":"flag","src":"FLAG_BARON_MISSION5_PASSED","w":1.0,"max":null},{"key":"Story Missions|Mainland Island|All Hands On Deck","sec":"Story Missions","sub":"Mainland Island","disp":"All Hands On Deck","kind":"flag","src":"FLAG_GENERAL_MISSION5_PASSED","w":1.0,"max":null},{"key":"Story Missions|Mainland Island|Shakedown","sec":"Story Missions","sub":"Mainland Island","disp":"Shakedown","kind":"flag","src":"FLAG_PROTECT_MISSION1_PASSED","w":1.0,"max":null},{"key":"Story Missions|Mainland Island|Bar Brawl","sec":"Story Missions","sub":"Mainland Island","disp":"Bar Brawl","kind":"flag","src":"FLAG_PROTECT_MISSION2_PASSED","w":1.0,"max":null},{"key":"Story Missions|Mainland Island|Cop Land","sec":"Story Missions","sub":"Mainland Island","disp":"Cop Land","kind":"flag","src":"FLAG_PROTECT_MISSION3_PASSED","w":1.0,"max":null},{"key":"Story Missions|Mainland Island|Cap The Collector","sec":"Story Missions","sub":"Mainland Island","disp":"Cap The Collector","kind":"flag","src":"FLAG_FINALE_MISSION1_PASSED","w":1.0,"max":null},{"key":"Story Missions|Mainland Island|Keep Your Friends Close...","sec":"Story Missions","sub":"Mainland Island","disp":"Keep Your Friends Close...","kind":"flag","src":"FLAG_FINALE_MISSION2_PASSED","w":1.0,"max":null},{"key":"Asset Missions|The Boatyard|Asset Acquired","sec":"Asset Missions","sub":"The Boatyard","disp":"Asset Acquired","kind":"flag","src":"BOATYARD_ASSET_ACQUIRED","w":1.0,"max":null},{"key":"Asset Missions|The Boatyard|Checkpoint Charlie","sec":"Asset Missions","sub":"The Boatyard","disp":"Checkpoint Charlie","kind":"stage","src":"FLAG_COKERUN_PASSED","w":1.0,"max":null,"on":3},{"key":"Asset Missions|Cherry Popper Ice Cream Factory|Asset Acquired","sec":"Asset Missions","sub":"Cherry Popper Ice Cream Factory","disp":"Asset Acquired","kind":"flag","src":"ICECREAM_ASSET_ACQUIRED","w":1.0,"max":null},{"key":"Asset Missions|Cherry Popper Ice Cream Factory|Distribution","sec":"Asset Missions","sub":"Cherry Popper Ice Cream Factory","disp":"Distribution","kind":"flag","src":"FLAG_ICECUT_MISSION1_PASSED","w":1.0,"max":null},{"key":"Asset Missions|Pole Position Club|Asset Acquired","sec":"Asset Missions","sub":"Pole Position Club","disp":"Asset Acquired","kind":"flag","src":"FLAG_STRIP_ASSET_CUTSCENE","w":1.0,"max":null},{"key":"Asset Missions|Pole Position Club|Spend At Least $300","sec":"Asset Missions","sub":"Pole Position Club","disp":"Spend At Least $300","kind":"counter","src":"COUNTER_TITTYCASH_SPENT","w":0.0033333333333333335,"max":300,"thresh":1,"on":300},{"key":"Asset Missions|Sunshine Autos|Asset Acquired","sec":"Asset Missions","sub":"Sunshine Autos","disp":"Asset Acquired","kind":"flag","src":"SHOWROOM_ASSET_ACQUIRED","w":1.0,"max":null},{"key":"Asset Missions|Sunshine Autos|Import Street Cars and SUVs","sec":"Asset Missions","sub":"Sunshine Autos","disp":"Import Street Cars and SUVs","kind":"flag","src":"IMPORT_CAR_GENERATOR1_CREATED","w":1.0,"max":null},{"key":"Asset Missions|Sunshine Autos|Import Expensive Cars","sec":"Asset Missions","sub":"Sunshine Autos","disp":"Import Expensive Cars","kind":"flag","src":"IMPORT_CAR_GENERATOR2_CREATED","w":1.0,"max":null},{"key":"Asset Missions|Sunshine Autos|Import Sports Cars","sec":"Asset Missions","sub":"Sunshine Autos","disp":"Import Sports Cars","kind":"flag","src":"IMPORT_CAR_GENERATOR3_CREATED","w":1.0,"max":null},{"key":"Asset Missions|Sunshine Autos|Import Gang Cars and Oddballs","sec":"Asset Missions","sub":"Sunshine Autos","disp":"Import Gang Cars and Oddballs","kind":"flag","src":"IMPORT_CAR_GENERATOR4_CREATED","w":1.0,"max":null},{"key":"Asset Missions|InterGlobal Film Studio|Asset Acquired","sec":"Asset Missions","sub":"InterGlobal Film Studio","disp":"Asset Acquired","kind":"flag","src":"PORN_ASSET_ACQUIRED","w":1.0,"max":null},{"key":"Asset Missions|InterGlobal Film Studio|Recruitment Drive","sec":"Asset Missions","sub":"InterGlobal Film Studio","disp":"Recruitment Drive","kind":"flag","src":"FLAG_PORN_MISSION1_PASSED","w":1.0,"max":null},{"key":"Asset Missions|InterGlobal Film Studio|Dildo Dodo","sec":"Asset Missions","sub":"InterGlobal Film Studio","disp":"Dildo Dodo","kind":"flag","src":"FLAG_PORN_MISSION2_PASSED","w":1.0,"max":null},{"key":"Asset Missions|InterGlobal Film Studio|Martha's Mug Shot","sec":"Asset Missions","sub":"InterGlobal Film Studio","disp":"Martha's Mug Shot","kind":"flag","src":"FLAG_PORN_MISSION3_PASSED","w":1.0,"max":null},{"key":"Asset Missions|InterGlobal Film Studio|G-Spotlight","sec":"Asset Missions","sub":"InterGlobal Film Studio","disp":"G-Spotlight","kind":"flag","src":"FLAG_PORN_MISSION4_PASSED","w":1.0,"max":null},{"key":"Asset Missions|Kaufman Cabs|Asset Acquired","sec":"Asset Missions","sub":"Kaufman Cabs","disp":"Asset Acquired","kind":"flag","src":"TAXIFIRM_ASSET_ACQUIRED","w":1.0,"max":null},{"key":"Asset Missions|Kaufman Cabs|V.I.P.","sec":"Asset Missions","sub":"Kaufman Cabs","disp":"V.I.P.","kind":"flag","src":"FLAG_TAXIWAR_MISSION1_PASSED","w":1.0,"max":null},{"key":"Asset Missions|Kaufman Cabs|Friendly Rivalry","sec":"Asset Missions","sub":"Kaufman Cabs","disp":"Friendly Rivalry","kind":"flag","src":"FLAG_TAXIWAR_MISSION2_PASSED","w":1.0,"max":null},{"key":"Asset Missions|Kaufman Cabs|Cabmaggedon","sec":"Asset Missions","sub":"Kaufman Cabs","disp":"Cabmaggedon","kind":"flag","src":"FLAG_TAXIWAR_MISSION3_PASSED","w":1.0,"max":null},{"key":"Asset Missions|Print Works|Asset Acquired","sec":"Asset Missions","sub":"Print Works","disp":"Asset Acquired","kind":"flag","src":null,"w":1.0,"max":null},{"key":"Asset Missions|Print Works|Spilling The Beans","sec":"Asset Missions","sub":"Print Works","disp":"Spilling The Beans","kind":"flag","src":"FLAG_COUNTER_MISSION1_PASSED","w":1.0,"max":null},{"key":"Asset Missions|Print Works|Hit The Courier","sec":"Asset Missions","sub":"Print Works","disp":"Hit The Courier","kind":"flag","src":"FLAG_COUNTER_MISSION2_PASSED","w":1.0,"max":null},{"key":"Asset Missions|Malibu Club|Asset Acquired","sec":"Asset Missions","sub":"Malibu Club","disp":"Asset Acquired","kind":"flag","src":"MALIBU_ASSET_ACQUIRED","w":1.0,"max":null},{"key":"Asset Missions|Malibu Club|No Escape?","sec":"Asset Missions","sub":"Malibu Club","disp":"No Escape?","kind":"flag","src":"FLAG_BANKJOB_MISSION1_PASSED","w":1.0,"max":null},{"key":"Asset Missions|Malibu Club|The Shootist","sec":"Asset Missions","sub":"Malibu Club","disp":"The Shootist","kind":"flag","src":"FLAG_BANKJOB_MISSION2_PASSED","w":1.0,"max":null},{"key":"Asset Missions|Malibu Club|The Driver","sec":"Asset Missions","sub":"Malibu Club","disp":"The Driver","kind":"flag","src":"FLAG_BANKJOB_MISSION3_PASSED","w":1.0,"max":null},{"key":"Asset Missions|Malibu Club|The Job","sec":"Asset Missions","sub":"Malibu Club","disp":"The Job","kind":"flag","src":"FLAG_BANKJOB_MISSION4_PASSED","w":1.0,"max":null},{"key":"Asset Missions|Phil's Place|Gun Runner","sec":"Asset Missions","sub":"Phil's Place","disp":"Gun Runner","kind":"flag","src":"FLAG_PHIL_MISSION1_PASSED","w":1.0,"max":null},{"key":"Asset Missions|Phil's Place|Boomshine Saigon","sec":"Asset Missions","sub":"Phil's Place","disp":"Boomshine Saigon","kind":"flag","src":"FLAG_PHIL_MISSION2_PASSED","w":1.0,"max":null},{"key":"Asset Missions|Safe Houses|Ocean Heights Apartment","sec":"Asset Missions","sub":"Safe Houses","disp":"Ocean Heights Apartment","kind":"flag","src":"OCEAN_HEIGHTS_BOUGHT","w":1.0,"max":null},{"key":"Asset Missions|Safe Houses|Links View Apartment","sec":"Asset Missions","sub":"Safe Houses","disp":"Links View Apartment","kind":"flag","src":"LINKS_VIEW_BOUGHT","w":1.0,"max":null},{"key":"Asset Missions|Safe Houses|El Swanko Casa","sec":"Asset Missions","sub":"Safe Houses","disp":"El Swanko Casa","kind":"flag","src":"ELSWANKO_BOUGHT","w":1.0,"max":null},{"key":"Asset Missions|Safe Houses|1102 Washington Street","sec":"Asset Missions","sub":"Safe Houses","disp":"1102 Washington Street","kind":"flag","src":"WASHINGTON_1102_BOUGHT","w":1.0,"max":null},{"key":"Asset Missions|Safe Houses|3321 Vice Point","sec":"Asset Missions","sub":"Safe Houses","disp":"3321 Vice Point","kind":"flag","src":"VICE_POINT_3321_BOUGHT","w":1.0,"max":null},{"key":"Asset Missions|Safe Houses|Hyman Condo","sec":"Asset Missions","sub":"Safe Houses","disp":"Hyman Condo","kind":"flag","src":"HYMAN_CONDO_BOUGHT","w":1.0,"max":null},{"key":"Asset Missions|Safe Houses|Skumole Shack","sec":"Asset Missions","sub":"Safe Houses","disp":"Skumole Shack","kind":"flag","src":"SKUMOLE_BOUGHT","w":1.0,"max":null},{"key":"Other Missions|Collectibles|Hidden Packages {n}","sec":"Other Missions","sub":"Collectibles","disp":"Hidden Packages   100 out of 100","kind":"counter","src":"NUMBER_OF_PACKAGES_COLLECTED","w":0.035,"max":100},{"key":"Other Missions|Collectibles|Rampages {n}","sec":"Other Missions","sub":"Collectibles","disp":"Rampages   35 out of 35","kind":"counter","src":"TOTAL_RAMPAGES_PASSED","w":0.3,"max":35},{"key":"Other Missions|Collectibles|Unique Stunt Jumps {n}","sec":"Other Missions","sub":"Collectibles","disp":"Unique Stunt Jumps   36 out of 36","kind":"counter","src":"TOTAL_COMPLETED_USJ","w":1.0,"max":36},{"key":"Other Missions|Collectibles|Rob All Stores {n}","sec":"Other Missions","sub":"Collectibles","disp":"Rob All Stores   15 out of 15","kind":"sum","src":null,"w":0.0,"max":15,"srcs":["ROBBED_SHOP_1","ROBBED_SHOP_2","ROBBED_SHOP_3","ROBBED_SHOP_4","ROBBED_SHOP_5","ROBBED_SHOP_6","ROBBED_SHOP_7","ROBBED_SHOP_8","ROBBED_SHOP_9","ROBBED_SHOP_10","ROBBED_SHOP_11","ROBBED_SHOP_12","ROBBED_HARDSHOP_1","ROBBED_HARDSHOP_2","ROBBED_HARDSHOP_3"]},{"key":"Other Missions|Vehicle Missions|Pizza Boy","sec":"Other Missions","sub":"Vehicle Missions","disp":"Pizza Boy","kind":"flag","src":"FLAG_PIZZA_MISSION_PASSED","w":1.0,"max":null},{"key":"Other Missions|Vehicle Missions|Paramedic","sec":"Other Missions","sub":"Vehicle Missions","disp":"Paramedic","kind":"flag","src":"DONE_AMBULANCE_PROGRESS","w":1.0,"max":null},{"key":"Other Missions|Vehicle Missions|Firefighter","sec":"Other Missions","sub":"Vehicle Missions","disp":"Firefighter","kind":"flag","src":"DONE_FIRETRUCK_PROGRESS","w":1.0,"max":null},{"key":"Other Missions|Vehicle Missions|Vigilante","sec":"Other Missions","sub":"Vehicle Missions","disp":"Vigilante","kind":"flag","src":null,"w":1.0,"max":null},{"key":"Other Missions|Vehicle Missions|Taxi Driver {n}","sec":"Other Missions","sub":"Vehicle Missions","disp":"Taxi Driver   100 out of 100","kind":"counter","src":"TAXI_PASSED","w":0.0,"max":100},{"key":"Other Missions|Street Races|Terminal Velocity","sec":"Other Missions","sub":"Street Races","disp":"Terminal Velocity","kind":"flag","src":"DONE_RACE1_PROGRESS","w":1.0,"max":null},{"key":"Other Missions|Street Races|Ocean Drive","sec":"Other Missions","sub":"Street Races","disp":"Ocean Drive","kind":"flag","src":"DONE_RACE2_PROGRESS","w":1.0,"max":null},{"key":"Other Missions|Street Races|Border Run","sec":"Other Missions","sub":"Street Races","disp":"Border Run","kind":"flag","src":"DONE_RACE3_PROGRESS","w":1.0,"max":null},{"key":"Other Missions|Street Races|Capital Cruise","sec":"Other Missions","sub":"Street Races","disp":"Capital Cruise","kind":"flag","src":"DONE_RACE4_PROGRESS","w":1.0,"max":null},{"key":"Other Missions|Street Races|Tour!","sec":"Other Missions","sub":"Street Races","disp":"Tour!","kind":"flag","src":"DONE_RACE5_PROGRESS","w":1.0,"max":null},{"key":"Other Missions|Street Races|V.C. Endurance","sec":"Other Missions","sub":"Street Races","disp":"V.C. Endurance","kind":"flag","src":"DONE_RACE6_PROGRESS","w":1.0,"max":null},{"key":"Other Missions|Mr. Black Payphone Missions|Road Kill","sec":"Other Missions","sub":"Mr. Black Payphone Missions","disp":"Road Kill","kind":"flag","src":"FLAG_ASSIN_MISSION1_PASSED","w":1.0,"max":null},{"key":"Other Missions|Mr. Black Payphone Missions|Waste The Wife","sec":"Other Missions","sub":"Mr. Black Payphone Missions","disp":"Waste The Wife","kind":"flag","src":"FLAG_ASSIN_MISSION2_PASSED","w":1.0,"max":null},{"key":"Other Missions|Mr. Black Payphone Missions|Autocide","sec":"Other Missions","sub":"Mr. Black Payphone Missions","disp":"Autocide","kind":"flag","src":"FLAG_ASSIN_MISSION3_PASSED","w":1.0,"max":null},{"key":"Other Missions|Mr. Black Payphone Missions|Check Out At The Check In","sec":"Other Missions","sub":"Mr. Black Payphone Missions","disp":"Check Out At The Check In","kind":"flag","src":"FLAG_ASSIN_MISSION4_PASSED","w":1.0,"max":null},{"key":"Other Missions|Mr. Black Payphone Missions|Loose Ends","sec":"Other Missions","sub":"Mr. Black Payphone Missions","disp":"Loose Ends","kind":"flag","src":"FLAG_ASSIN_MISSION5_PASSED","w":1.0,"max":null},{"key":"Other Missions|Hyman Memorial Standium Missions|Hotring","sec":"Other Missions","sub":"Hyman Memorial Standium Missions","disp":"Hotring","kind":"flag","src":"BEST_NASCAR_RESULT","w":1.0,"max":null,"on":1,"truthy":[1,2,3]},{"key":"Other Missions|Hyman Memorial Standium Missions|Bloodring","sec":"Other Missions","sub":"Hyman Memorial Standium Missions","disp":"Bloodring","kind":"flag","src":"MM_MISSION_PASSED_ONCE","w":1.0,"max":null},{"key":"Other Missions|Hyman Memorial Standium Missions|Dirtring","sec":"Other Missions","sub":"Hyman Memorial Standium Missions","disp":"Dirtring","kind":"flag","src":"FLAG_KICKSTART_PASSED_1STIME","w":1.0,"max":null},{"key":"Other Missions|Chopper Checkpoint Missions|Ocean Beach","sec":"Other Missions","sub":"Chopper Checkpoint Missions","disp":"Ocean Beach","kind":"flag","src":"DONE_HELI1_PROGRESS","w":1.0,"max":null},{"key":"Other Missions|Chopper Checkpoint Missions|Vice Point","sec":"Other Missions","sub":"Chopper Checkpoint Missions","disp":"Vice Point","kind":"flag","src":"DONE_HELI2_PROGRESS","w":1.0,"max":null},{"key":"Other Missions|Chopper Checkpoint Missions|Little Haiti","sec":"Other Missions","sub":"Chopper Checkpoint Missions","disp":"Little Haiti","kind":"flag","src":"DONE_HELI3_PROGRESS","w":1.0,"max":null},{"key":"Other Missions|Chopper Checkpoint Missions|Downtown","sec":"Other Missions","sub":"Chopper Checkpoint Missions","disp":"Downtown","kind":"flag","src":"DONE_HELI4_PROGRESS","w":1.0,"max":null},{"key":"Other Missions|Off-Road Missions|PCJ Playground","sec":"Other Missions","sub":"Off-Road Missions","disp":"PCJ Playground","kind":"flag","src":"FLAG_BMX_1_PASSED","w":1.0,"max":null},{"key":"Other Missions|Off-Road Missions|Cone Crazy","sec":"Other Missions","sub":"Off-Road Missions","disp":"Cone Crazy","kind":"flag","src":"FLAG_CARPARK1_PASSED","w":1.0,"max":null},{"key":"Other Missions|Off-Road Missions|Trial By Dirt","sec":"Other Missions","sub":"Off-Road Missions","disp":"Trial By Dirt","kind":"flag","src":"FLAG_BMX_2_PASSED","w":1.0,"max":null},{"key":"Other Missions|Off-Road Missions|Test Track","sec":"Other Missions","sub":"Off-Road Missions","disp":"Test Track","kind":"flag","src":"FLAG_4X4_MISSION1_PASSED","w":1.0,"max":null},{"key":"Other Missions|RC Vehicle Missions|RC Bandit Race","sec":"Other Missions","sub":"RC Vehicle Missions","disp":"RC Bandit Race","kind":"flag","src":null,"w":1.0,"max":null},{"key":"Other Missions|RC Vehicle Missions|RC Baron Race","sec":"Other Missions","sub":"RC Vehicle Missions","disp":"RC Baron Race","kind":"flag","src":null,"w":1.0,"max":null},{"key":"Other Missions|RC Vehicle Missions|RC Raider Pickup","sec":"Other Missions","sub":"RC Vehicle Missions","disp":"RC Raider Pickup","kind":"flag","src":"FLAG_COMPLETE_RCHELI_ONCE","w":1.0,"max":null},{"key":"Other Missions|Ammu-Nation Shooting Range|Score 45 Points or More","sec":"Other Missions","sub":"Ammu-Nation Shooting Range","disp":"Score 45 Points or More","kind":"flag","src":"FLAG_PASSED_RANGE","w":1.0,"max":null}]}""")

# GTASnP ground truth for the sample saves: expected state bits, counter
# values and the percentage each save reports.
EXPECTED = json.loads(r"""{"GTAVCsf1.sav":{"pct":154.0,"gtasnp":100.0,"bits":"/////////////////x8=","counts":[100,35,36,15,100]},"GTAVCsf3.sav":{"pct":18.0,"gtasnp":11.688311576843262,"bits":"/w8AdgAAAABAAAAAAAA=","counts":[0,0,0,0,0]},"GTAVCsf7.sav":{"pct":154.0,"gtasnp":100.0,"bits":"/////////////////x8=","counts":[100,35,36,15,100]},"GTAVCsf9.sav":{"pct":19.0,"gtasnp":12.337662696838379,"bits":"/w8AdgAAAABAAAAAQAA=","counts":[0,0,0,0,0]}}""")

GAME = "Vice City"
TITLE = "GTA Vice City: Definitive Edition — 100% Save Editor"
DENOM = 154
TAG = b"SCR\x00"
PCTG = "GAME_PERCENTAGE"

SEAL_OFF = 0x08
SEAL_LEN = 16
ZERO_LEN = 0x18

ITEMS = DATA["items"]
KEYS = [it["key"] for it in ITEMS]


def compute_seal(data):
    """Seal = NOT(MD5(first 24 bytes zeroed + rest))."""
    buf = bytearray(data)
    buf[:ZERO_LEN] = b"\x00" * ZERO_LEN
    digest = hashlib.md5(bytes(buf)).digest()
    return bytes((~b) & 0xFF for b in digest)


def _u32(data, off):
    return struct.unpack_from("<I", data, off)[0]


def _set_u32(buf, off, value):
    struct.pack_into("<I", buf, off, value & 0xFFFFFFFF)


class SaveError(Exception):
    pass


# ---------------------------------------------------------------- save file


class GameSave:
    """Parsing and writing of a Vice City Definitive Edition (1.1x) .sav."""

    def __init__(self, data, path=None):
        if len(data) < 0x1000:
            raise SaveError("The file is too small to be a save")
        self.data = bytes(data)
        self.path = path
        self.names = self._name_table()
        if not self.names:
            raise SaveError("No global variable name table found "
                            "(is this a Vice City DE save?)")
        self._indexes = set(self.names.values())
        self.gbase = self._globals_base()
        self._check_layout()

    def _check_layout(self):
        """Refuse files whose global space does not look like the one the
        mapping was built against: the checklist flags must read 0/1.
        Catches the offset drift reported for other game builds before
        anything is written."""
        flags = [it for it in ITEMS
                 if it["kind"] in ("flag", "stage") and it["src"]]
        if not flags:
            return
        bad = [it["disp"] for it in flags if self.byte(it["src"], 0) > 1]
        if len(bad) > len(flags) * 0.1:
            raise SaveError(
                "This save's global layout does not match the one this "
                "editor was built against (%d of %d checklist flags hold "
                "values other than 0/1). Nothing was written; please "
                "report the game build."
                % (len(bad), len(flags)))

    # ---- location ----------------------------------------------------
    def _name_table(self):
        names = {}
        for magic in (b"\x78\x01", b"\x78\x9c", b"\x78\xda", b"\x78\x5e"):
            pos = 0
            while True:
                i = self.data.find(magic, pos)
                if i < 0:
                    break
                try:
                    raw = zlib.decompress(self.data[i:])
                except zlib.error:
                    pos = i + 1
                    continue
                if b"Globalvariables" in raw[:64]:
                    for line in raw.decode("utf-8", "replace").splitlines():
                        if not line or line.startswith("//"):
                            continue
                        parts = line.split(",")
                        if len(parts) >= 4:
                            try:
                                names.setdefault(parts[1], int(parts[3]))
                            except ValueError:
                                pass
                pos = i + 1
        return names

    def _flag_offset(self, name):
        if name not in self.names:
            return None
        off = self.gbase + self.names[name]
        return off if 0 <= off < len(self.data) else None

    def _globals_base(self):
        """base = TAG + 0x14. Each candidate is scored on the percentage
        global (which must be 0 or a plausible 0..100 float) and on the
        checklist flags reading 0/1; the documented offset wins ties."""
        probes = [it["src"] for it in ITEMS
                  if it["kind"] in ("flag", "stage") and it["src"]]
        idx_pct = self.names.get(PCTG)
        best, best_score = None, -1.0
        pos = 0
        while True:
            i = self.data.find(TAG, pos)
            if i < 0:
                break
            pos = i + 1
            for delta in (0x14, 0x15):
                base = i + delta
                score = 0.0
                if idx_pct is not None and base + idx_pct + 4 <= len(self.data):
                    v = struct.unpack_from("<f", self.data,
                                           base + idx_pct)[0]
                    if v == 0.0 or 0.05 <= v <= 100.5:
                        score += 10.0
                ok = tot = 0
                for name in probes:
                    idx = self.names.get(name)
                    if idx is None:
                        continue
                    off = base + idx
                    if 0 <= off < len(self.data):
                        tot += 1
                        if self.data[off] in (0, 1):
                            ok += 1
                if tot:
                    score += ok / tot
                if score > best_score:
                    best, best_score = base, score
        if best is None or best_score < 10.0:
            # fall back to the documented layout: first TAG + 0x14
            i = self.data.find(TAG)
            if i < 0 or i + 0x14 >= len(self.data):
                raise SaveError("Could not locate the save's global "
                                "variable space")
            best = i + 0x14
        return best

    # ---- reads -------------------------------------------------------
    def global32(self, name, default=None):
        idx = self.names.get(name)
        if idx is None:
            return default
        off = self.gbase + idx
        if off + 4 > len(self.data):
            return default
        return _u32(self.data, off)

    def flag(self, name):
        off = self._flag_offset(name)
        if off is None:
            return 0
        return 1 if self.data[off] else 0

    def percent(self):
        idx = self.names.get(PCTG)
        if idx is None:
            return None
        off = self.gbase + idx
        if off + 4 > len(self.data):
            return None
        return struct.unpack_from("<f", self.data, off)[0]

    # ---- writes ------------------------------------------------------
    def set_global(self, name, value):
        idx = self.names.get(name)
        if idx is None:
            return False
        off = self.gbase + idx
        if off + 4 > len(self.data):
            return False
        buf = bytearray(self.data)
        _set_u32(buf, off, value)
        self.data = bytes(buf)
        return True

    def byte(self, name, default=0):
        """Raw byte value of a global (checklist flags and stages)."""
        idx = self.names.get(name)
        if idx is None:
            return default
        off = self.gbase + idx
        if off >= len(self.data):
            return default
        return self.data[off]

    def counter(self, name, default=0):
        """u32 value of a global. If another variable begins in the very
        next byte the two are packed in one word and only the low byte
        belongs to this name (that is how the game stores a few of
        them, e.g. some script counters)."""
        idx = self.names.get(name)
        if idx is None:
            return default
        off = self.gbase + idx
        if off + 4 > len(self.data):
            return default
        if (idx + 1) in self._indexes:
            return self.data[off]
        return _u32(self.data, off)

    def set_counter(self, name, value):
        """Write a counter with the width the name table implies: whole
        word normally, single byte only when the next variable starts in
        the following byte."""
        idx = self.names.get(name)
        if idx is None:
            return False
        off = self.gbase + idx
        if off + 4 > len(self.data):
            return False
        buf = bytearray(self.data)
        if (idx + 1) in self._indexes:
            buf[off] = int(value) & 0xFF
        else:
            _set_u32(buf, off, int(value))
        self.data = bytes(buf)
        return True

    def set_flag(self, name, value):
        off = self._flag_offset(name)
        if off is None:
            return False
        buf = bytearray(self.data)
        buf[off] = int(value) & 0xFF
        self.data = bytes(buf)
        return True

    def set_percent(self, value):
        idx = self.names.get(PCTG)
        if idx is None:
            return False
        off = self.gbase + idx
        if off + 4 > len(self.data):
            return False
        buf = bytearray(self.data)
        struct.pack_into("<f", buf, off, float(value))
        self.data = bytes(buf)
        return True

    def reseal(self):
        buf = bytearray(self.data)
        buf[SEAL_OFF:SEAL_OFF + SEAL_LEN] = compute_seal(bytes(buf))
        self.data = bytes(buf)

    def to_bytes(self):
        return self.data

    # ---- full state (what the GUI models) ----------------------------
    def read_state(self):
        return {it["key"]: item_read(self, it) for it in ITEMS}


def supported(it):
    """Whether the item has a known, safe place in the save."""
    return bool(it.get("src") or it["kind"] == "sum")


def item_read(sav, it):
    if it["kind"] == "sum":
        n = sum(1 for name in it["srcs"] if sav.byte(name))
        return min(n, it["max"] or 0)
    if not it.get("src"):
        return 0
    if it["kind"] == "counter":
        v = int(sav.counter(it["src"], 0))
        cap = it["max"] or 0
        return min(v, cap) if cap else v
    v = sav.byte(it["src"])
    truthy = it.get("truthy")
    if truthy is not None:
        return 1 if v in truthy else 0
    return 1 if v else 0


def item_target(it):
    """Value that marks the item as complete in the save."""
    if it.get("on") is not None:
        return it["on"]
    if it["kind"] == "counter":
        return it["max"] or 0
    return 1


def compute_progress(st):
    """Progress points out of DENOM (the 100% weights calibrated on the
    real saves: exactly reproduces every sample). Rows without a known
    variable cannot be read and therefore add nothing."""
    total = 0.0
    for it in ITEMS:
        if not supported(it):
            continue
        v = st.get(it["key"], 0)
        if it["kind"] in ("counter", "sum"):
            total += it["w"] * (v or 0)
        elif v:
            total += it["w"]
    return min(DENOM, max(0.0, total))


def all_supported_done(st):
    return all(st.get(it["key"], 0) for it in ITEMS if supported(it))


def compute_percent(st):
    """Percentage written to GAME_PERCENTAGE.

    The five rows without a documented variable are invisible to the
    editor; when every editable item is complete the save is reported
    as 100% (the alternative would be to downgrade a real 100% save).
    """
    if all_supported_done(st):
        return 100.0
    return compute_progress(st) / DENOM * 100.0


def missions_done(st):
    return sum(1 for it in ITEMS
               if it["sec"] == "Story Missions" and st.get(it["key"], 0))


def missions_total():
    return sum(1 for it in ITEMS if it["sec"] == "Story Missions")


def _diff_offsets(a, b):
    return [i for i in range(min(len(a), len(b))) if a[i] != b[i]]


def apply_state(sav, st, dry_run=False):
    """Write the GUI state into the save.

    Only variables that belong to the checklist are touched. The result
    is diffed against the original file and written only when every
    changed byte falls inside one of those variables, the percentage
    float or the MD5 seal; otherwise the save is left untouched and an
    error is raised. That is the guard that would have prevented the
    corrupted save from the issue.
    """
    allowed = set()
    ops = []
    for it in ITEMS:
        if not supported(it):
            continue
        v = st.get(it["key"], 0)
        names = it["srcs"] if it["kind"] == "sum" else [it["src"]]
        for pos, name in enumerate(names):
            idx = sav.names.get(name)
            if idx is None:
                continue
            off = sav.gbase + idx
            if not 0 <= off < len(sav.data):
                continue
            allowed.add(off)
            if it["kind"] == "sum":
                ops.append(("byte", off, 1 if pos < int(v or 0) else 0))
            elif it["kind"] == "counter":
                cap = it["max"] or 0
                val = item_target(it) if v else 0
                if cap:
                    val = max(0, min(int(val), cap))
                allowed.update(range(off, off + 4))
                ops.append(("counter", off, val,
                            (idx + 1) in sav._indexes))
            else:
                val = (item_target(it) if v else 0) & 0xFF
                ops.append(("byte", off, val))

    pct_off = None
    idx = sav.names.get(PCTG)
    if idx is not None:
        pct_off = sav.gbase + idx
        allowed.update(range(pct_off, pct_off + 4))

    buf = bytearray(sav.data)
    for op in ops:
        if op[0] == "byte":
            buf[op[1]] = op[2]
        elif op[3]:
            buf[op[1]] = op[2] & 0xFF
        else:
            _set_u32(buf, op[1], op[2])
    percent = compute_percent(st)
    if pct_off is not None:
        struct.pack_into("<f", buf, pct_off, percent)
    sealed = bytearray(buf)
    sealed[SEAL_OFF:SEAL_OFF + SEAL_LEN] = compute_seal(bytes(buf))
    allowed.update(range(SEAL_OFF, SEAL_OFF + SEAL_LEN))
    stray = [off for off in _diff_offsets(sav.data, bytes(sealed))
             if off not in allowed]
    if stray:
        raise SaveError("Guard: the edit would change %d byte(s) outside "
                        "the checklist variables (offsets %s); nothing "
                        "was written" % (len(stray), stray[:8]))
    if dry_run:
        return sorted(set(_diff_offsets(sav.data, bytes(sealed))) -
                      set(range(SEAL_OFF, SEAL_OFF + SEAL_LEN)))
    sav.data = bytes(sealed)
    return sav


# ---------------------------------------------------------------- selftest


def _pack_bits(values):
    out = bytearray()
    for i in range(0, len(values), 8):
        b = 0
        for j in range(8):
            if i + j < len(values) and values[i + j]:
                b |= 1 << j
        out.append(b)
    return bytes(out)


CHECKLIST_SRC_RE = re.compile(
    r"^(FLAG_.*|.*_PASSED|.*_BOUGHT|.*_ASSET_ACQUIRED|.*_CUTSCENE|"
    r"DONE_[A-Z0-9_]+_PROGRESS|IMPORT_CAR_GENERATOR[0-9]_CREATED|"
    r"NUMBER_OF_PACKAGES_COLLECTED|TOTAL_RAMPAGES_PASSED|"
    r"TOTAL_COMPLETED_USJ|TAXI_PASSED|COUNTER_TITTYCASH_SPENT|"
    r"ROBBED_(SHOP|HARDSHOP)_[0-9]+|BEST_NASCAR_RESULT|"
    r"MM_MISSION_PASSED_ONCE)$")


def selftest():
    here = os.path.dirname(os.path.abspath(__file__))
    checks = fails = 0

    def check(cond, label):
        nonlocal checks, fails
        checks += 1
        if not cond:
            fails += 1
            print("FAIL: %s" % label)

    for fn, exp in EXPECTED.items():
        path = os.path.join(here, "samples", fn)
        try:
            data = open(path, "rb").read()
            sav = GameSave(data, path)
        except SaveError as e:
            check(False, "%s: parse (%s)" % (fn, e))
            continue
        check(True, "%s: parse" % fn)

        # 1. the seal the game wrote must match the formula
        check(compute_seal(data)[0:SEAL_LEN] == data[SEAL_OFF:SEAL_OFF + SEAL_LEN],
              "%s: seal" % fn)

        st = sav.read_state()

        # 2. every *editable* checklist bit matches GTASnP (the rows
        # without a documented variable cannot be compared)
        want = base64.b64decode(exp["bits"])
        bad = []
        for i, it in enumerate(ITEMS):
            if not supported(it):
                continue
            got = 1 if (st[it["key"]] >= (it["max"] or 0)
                        if it["kind"] in ("counter", "sum") and it["max"]
                        else st[it["key"]]) else 0
            if got != ((want[i // 8] >> (i % 8)) & 1):
                bad.append(it["disp"])
        check(not bad, "%s: checklist bits vs GTASnP (%s)" % (fn, bad[:3]))

        # 3. the counters GTASnP reports for these saves
        ctrs = [st[it["key"]] for it in ITEMS
                if it["kind"] in ("counter", "sum")
                and it["disp"].split(" ")[0] in
                ("Hidden", "Rampages", "Unique", "Rob", "Taxi")]
        check(ctrs == exp["counts"], "%s: counters vs GTASnP (%s)"
              % (fn, ctrs))

        # 4. the computed percentage matches the checklist model
        pts = compute_progress(st)
        if exp["gtasnp"] >= 99.9:
            check(all_supported_done(st),
                  "%s: every editable item reads complete" % fn)
            check(abs(compute_percent(st) - 100.0) < 0.01,
                  "%s: percent 100" % fn)
        else:
            check(abs(pts - exp["pct"]) < 0.01,
                  "%s: computed points %.3f != %.3f" % (fn, pts, exp["pct"]))
            check(abs(compute_percent(st) - exp["gtasnp"]) < 0.75,
                  "%s: computed pct != gtasnp" % fn)

        # 5. the stored percent global agrees with what GTASnP shows
        stored = sav.percent()
        check(stored is not None and abs(stored - exp["gtasnp"]) < 0.75,
              "%s: stored pct %s != gtasnp %s" % (fn, stored, exp["gtasnp"]))

    # 6. every editable row points at a checklist-owned variable (the
    # regression that corrupted saves: blips, pickups, help timers...)
    stray = []
    for it in ITEMS:
        names = it.get("srcs") or ([it["src"]] if it.get("src") else [])
        for name in names:
            if not CHECKLIST_SRC_RE.match(name):
                stray.append(name)
    check(not stray, "mapping: non-checklist variables in DATA (%s)"
          % sorted(set(stray))[:5])

    # 7. ticking everything must reach exactly 100% and only touch the
    # allowlisted globals (apply_state raises otherwise)
    full = {}
    for it in ITEMS:
        full[it["key"]] = (it["max"] or 0) if it["kind"] in (
            "counter", "sum") else 1
    sample = os.path.join(here, "samples", "GTAVCsf3.sav")
    sav = GameSave(open(sample, "rb").read(), sample)
    before = sav.to_bytes()
    try:
        apply_state(sav, full)
        ok = True
    except SaveError as e:
        ok = False
        print("FAIL: guard rejected check-all: %s" % e)
    check(ok, "full state: guard accepts check-all")
    check(abs((sav.percent() or 0) - 100.0) < 0.01,
          "full state: percent global == 100")
    check(compute_seal(sav.to_bytes()) ==
          sav.to_bytes()[SEAL_OFF:SEAL_OFF + SEAL_LEN],
          "full state: seal valid")
    after = sav.to_bytes()
    pct_idx = sav.names.get(PCTG)
    globals_touched = {
        off - sav.gbase for off in _diff_offsets(before, after)
        if off >= sav.gbase and off < sav.gbase + max(sav.names.values()) + 4}
    allowed_idx = set()
    for it in ITEMS:
        for name in (it.get("srcs") or [it.get("src") or ""]):
            idx = sav.names.get(name)
            if idx is not None:
                allowed_idx.update(range(idx, idx + 4))
    if pct_idx is not None:
        allowed_idx.update(range(pct_idx, pct_idx + 4))
    check(globals_touched <= allowed_idx,
          "full state: no unrelated global touched (%s)"
          % sorted(globals_touched - allowed_idx)[:5])

    print("%d checks, %d failures" % (checks, fails))
    return 1 if fails else 0


# ---------------------------------------------------------------- GUI


class _ScrolledFrame:
    """Canvas + scrollbar hosting an inner frame (for long checklists)."""

    current = None

    def __init__(self, parent):
        import tkinter as tk
        self.canvas = tk.Canvas(parent, highlightthickness=0)
        self.bar = tk.Scrollbar(parent, orient="vertical",
                                command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.bar.set)
        self.bar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.inner = tk.Frame(self.canvas)
        self._win = self.canvas.create_window((0, 0), window=self.inner,
                                              anchor="nw")
        self.inner.bind("<Configure>", lambda e: self.canvas.configure(
            scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(
            self._win, width=e.width))
        self.canvas.bind("<Enter>", lambda e: setattr(
            _ScrolledFrame, "current", self))
        self.canvas.bind("<Leave>", lambda e: setattr(
            _ScrolledFrame, "current", None) if _ScrolledFrame.current is self
            else None)


def _wheel(event):
    sf = _ScrolledFrame.current
    if sf is not None:
        sf.canvas.yview_scroll(-1 * (event.delta // 120), "units")


def run_gui():
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk

    root = tk.Tk()
    root.title(TITLE + " :: editor for 100%")
    root.geometry("760x640")
    root.bind_all("<MouseWheel>", _wheel)

    sav = {"obj": None, "path": None}
    bools = {}   # key -> BooleanVar (flags)
    ints = {}    # key -> IntVar (counters)
    refreshing = {"v": False}

    # ---- toolbar -----------------------------------------------------
    bar = tk.Frame(root)
    bar.pack(side="top", fill="x", padx=6, pady=6)

    status = tk.Label(bar, text="Open a .sav to begin", anchor="w")
    status.pack(side="left", fill="x", expand=True)

    # ---- checklist notebook -----------------------------------------
    host = tk.Frame(root)
    host.pack(side="top", fill="both", expand=True, padx=6)

    sections = []
    for it in ITEMS:
        if it["sec"] not in sections:
            sections.append(it["sec"])

    rows = {}   # key -> (boolvar, intvar or None, checkbutton)

    def refresh(*_a):
        if refreshing["v"]:
            return
        refreshing["v"] = True
        try:
            st = {k: (ints[k].get() if k in ints else
                      (1 if bools[k].get() else 0)) for k in KEYS}
            pts = compute_progress(st)
            pct = compute_percent(st)
            n_done = missions_done(st)
            n_locked = sum(1 for it in ITEMS if not supported(it))
            msg = ("Progress: %g/%d (%.2f%%)  ·  Missions: %d/%d"
                   % (round(pts * 100) / 100, DENOM, pct,
                      n_done, missions_total()))
            if n_locked:
                msg += "  ·  %d item(s) without a documented variable" % n_locked
            status.config(text=msg)
        finally:
            refreshing["v"] = False

    def toggle_counter(key, var_b, var_i, mx):
        var_i.set(mx if var_b.get() else 0)

    def counter_changed(key, var_b, var_i, mx, * _a):
        if refreshing["v"]:
            return
        refreshing["v"] = True
        try:
            v = max(0, min(int(var_i.get() or 0), mx))
            if v != var_i.get():
                var_i.set(v)
            var_b.set(1 if v >= mx and mx else 0)
        finally:
            refreshing["v"] = False
        refresh()

    nb = ttk.Notebook(root)
    nb.pack(side="top", fill="both", expand=True, padx=6, pady=(0, 6))

    for sec in sections:
        wrap = tk.Frame(nb)
        sf = _ScrolledFrame(wrap)
        nb.add(wrap, text=sec)
        subs = []
        for it in ITEMS:
            if it["sec"] == sec and it["sub"] not in subs:
                subs.append(it["sub"])
        for sub in subs:
            same = [it for it in ITEMS
                    if it["sec"] == sec and it["sub"] == sub]
            if len(subs) > 1 or sub != sec:
                box = ttk.Labelframe(sf.inner, text=sub)
                box.pack(fill="x", padx=8, pady=4, anchor="n")
            else:
                box = sf.inner
            for it in same:
                key = it["key"]
                if it["kind"] == "counter":
                    vb = tk.BooleanVar()
                    vi = tk.IntVar(value=0)
                    mx = it["max"] or 0
                    row = tk.Frame(box)
                    row.pack(fill="x", padx=10, pady=1)
                    cb = tk.Checkbutton(
                        row, text=it["disp"].split(" out of ")[0],
                        variable=vb,
                        command=lambda k=key, b=vb, i=vi, m=mx:
                            toggle_counter(k, b, i, m))
                    cb.pack(side="left")
                    tk.Spinbox(row, from_=0, to=mx, width=6, textvariable=vi,
                               command=lambda k=key, b=vb, i=vi, m=mx:
                                   counter_changed(k, b, i, m)).pack(
                        side="left", padx=(6, 0))
                    tk.Label(row, text="/ %d" % mx, fg="#666").pack(
                        side="left", padx=(4, 0))
                    vi.trace_add("write",
                                 lambda *a, k=key, b=vb, i=vi, m=mx:
                                     counter_changed(k, b, i, m))
                    bools[key] = vb
                    ints[key] = vi
                    rows[key] = (vb, vi, cb)
                    vb.trace_add("write", refresh)
                else:
                    vb = tk.BooleanVar()
                    lock = not supported(it)
                    cb = tk.Checkbutton(
                        box,
                        text=it["disp"] + ("   (variable not documented)"
                                           if lock else ""),
                        variable=vb,
                        state="disabled" if lock else "normal",
                        fg="#888" if lock else "")
                    cb.pack(anchor="w", padx=10, pady=1)
                    bools[key] = vb
                    rows[key] = (vb, None, cb)
                    vb.trace_add("write", refresh)

    # ---- actions -----------------------------------------------------
    def load(path):
        data = open(path, "rb").read()
        obj = GameSave(data, path)
        st = obj.read_state()
        refreshing["v"] = True
        try:
            for k in KEYS:
                if k in ints:
                    ints[k].set(int(st.get(k, 0) or 0))
                    bools[k].set(bool(st.get(k, 0)))
                else:
                    bools[k].set(bool(st.get(k, 0)))
        finally:
            refreshing["v"] = False
        sav["obj"], sav["path"] = obj, path
        status.config(text="Loaded %s" % os.path.basename(path))
        refresh()

    def collect():
        return {k: (ints[k].get() if k in ints else
                     (1 if bools[k].get() else 0)) for k in KEYS}

    def on_open():
        path = filedialog.askopenfilename(
            title="Open a save", filetypes=[("Save files", "*.sav")],
            initialdir=os.path.join(os.path.expanduser("~"), "Documents"))
        if not path:
            return
        try:
            load(path)
        except (SaveError, OSError) as e:
            messagebox.showerror(TITLE, str(e))

    def write(path):
        st = collect()
        obj = sav["obj"]
        if obj is None:
            raise SaveError("Open a save first")
        # apply_state raises (and leaves the save untouched) when the
        # edit would reach a byte outside the checklist variables
        apply_state(obj, st)
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        if os.path.exists(path):
            bak = path + ".bak"
            if not os.path.exists(bak):
                with open(path, "rb") as src, open(bak, "wb") as dst:
                    dst.write(src.read())
        tmp = path + ".tmp"
        with open(tmp, "wb") as fh:
            fh.write(obj.to_bytes())
        os.replace(tmp, path)
        sav["path"] = path
        refresh()

    def on_save():
        if sav["path"] is None:
            return on_save_as()
        try:
            write(sav["path"])
            status.config(text="Saved %s" % os.path.basename(sav["path"]))
        except (SaveError, OSError) as e:
            messagebox.showerror(TITLE, str(e))

    def on_save_as():
        if sav["obj"] is None:
            return messagebox.showinfo(TITLE, "Open a save first")
        path = filedialog.asksaveasfilename(
            title="Save the game as", defaultextension="*.sav",
            filetypes=[("Save files", "*.sav")],
            initialfile=os.path.basename(sav["path"] or "GTASAsf1.sav"))
        if not path:
            return
        try:
            write(path)
            status.config(text="Saved %s" % os.path.basename(path))
        except (SaveError, OSError) as e:
            messagebox.showerror(TITLE, str(e))

    def set_all(value):
        if value:
            ok = messagebox.askyesno(
                TITLE,
                "Mark every editable item as complete?\n\n"
                "A copy of the current save is kept as <file>.sav.bak "
                "the first time you save.")
            if not ok:
                return
        refreshing["v"] = True
        try:
            for it in ITEMS:
                k = it["key"]
                if not supported(it):
                    continue
                if k in ints:
                    ints[k].set((it["max"] or 0) if value else 0)
                    bools[k].set(bool(value))
                else:
                    bools[k].set(bool(value))
        finally:
            refreshing["v"] = False
        refresh()

    for label, cmd in (("Open .sav...", on_open), ("Save", on_save),
                       ("Save as", on_save_as),
                       ("Check all", lambda: set_all(True)),
                       ("Uncheck all", lambda: set_all(False))):
        tk.Button(bar, text=label, command=cmd).pack(side="left", padx=3)

    refresh()
    root.mainloop()


# ---------------------------------------------------------------- main


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    run_gui()
