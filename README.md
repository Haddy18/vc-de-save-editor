# GTA Vice City: Definitive Edition — 100% Save Editor

```
..........................             ::       ................................
...................            :+#%@@@@@@@@#-.      ............................
.................      .=+%@@@@@@@@@@@@%@@@@@@@@=       ........................
.................  +@@@@@@@@@@@%%#%@%@@%@@@%@@%@@@@%=.      ....................
.  .. ..........   @@@%###%@%%%%@%%@@@@@@@@@@%#%%@@@@@@@=.    ..................
................  @@%%%%#%%%%%%@@%@@@@@@@@@@@%%@@%@@@@@@@@@@   .................
...............  %@@%%@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@%%%@@@@=   ...............
.............   :@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@   ..............
.............   @@@@@@@@@*:                        .=%@@@@@@@@@@    ............
.............  @@%%@@@:                                .=#@@@@@@@   ............
.............  @@#%@@=                          .. .::::.:#@@@@@@@  ............
.............  @%%@@=                      ......::::--====@@@@%@@@  .  ........
............. :@@@@% .:.........             ..:::::-==++*++@@@@%@@  ...........
...........   +@@@@+                                 .:-+**+%@@@@@@: ...........
............  @@%%@.                     :   ....--------=+*%@@@@@@: ...........
............  @@#@@ -%#%@@@@@@@@%%%**###*@@@@@@@@@@@@@@@@#++#@@@@@@= ...........
............ .@%@@*    .-+**%@@@@@@@%=:#@%%%%%##%#**+====*%+*@@@%@@+ ...........
............ -@@@@..=#@@@@#**%@@@%+-   .*#**%@@@#***%%#**=+#+@@@@@@%  ..........
............ -@@@=:@@@@*:*@@@@@@=.     -+***#%%-%@@@++@@@%**+%@@@@@@  ..........
............ :@@@.=+--.-.:+=-          =+***=   :+#%::%%@@@#+*@@@@@=  ..........
............ .@@% :       ..    ...   .++***--::::::-++-..=**+@@@@@  ...........
.........     @@- :   ..  .:....::    :++***===--===++=----**+#@@@@    .........
.........  :  -@ ...:..... .. ...   .-*+=+*+++=------=+=+++**++@@@*     ........
      ...  @%. =.:---:......:.:::@@@@@%@@@#***++=--===++*****+=@#:==#*  ........
        .  @@@+*+:=====:...:--:.:%%@@@@@@%%###**+==+++***#***+#@==*@@@  ........
       ..  **@@@%--=====:.:--.:=-   ..-::-+#*+*#*+=+*###******@@+%@@%@  ........
        . -@%@%*#++==---.:-::--.  .     .:-+**++**++******#*##@%@@%*%@  ........
        . -@-%+ +++-------++==+@@@@@@@@@@@@%#**#*#********#####*%%@*@@  ........
           @..***+==-----=*#++#+-.     ..-+*###%@%##******####**@#*+@+  ........
           #% =#@+=======+=::::..:-=====--==+****##**#*######%%@@*-@@  .........
            @#@@%*=====+=-===-=#@@@@@@@@@@@%##*#######*#######@@@*%@   .........
            .-.  +*===-=+===---+=... .=+*#%##########*#######@@#%%@*  ..........
                 :@==--:-===---:      .:-+#*#######***#####*@@        ..........
                  *@+===--==+==-:::--==++*########*##*####%@@          .........
                   -@#*++==-===+*++++**##################@@+                  ..
                    =@@%#**+=+#%%#######################@@                 ...
                     *#%%%%%#######%%%%################%@
                .   -:==+*##%%%##########*########%###%@=
            ::-::..---+++++**##%%%%%%%%%%%%%%%%%%######@
         ::--:::..---=+++==+***######%##########***##*#%
******=.:+. .:...-:--====-==+*************##***+***#**#*
+++=-..=*++- .. :::----------=+++++=-=+*+**+++++++**+**=:--
--.  .:-##+=-:..::--:--::::::-===++==+++==-======++++*+--+#@-
:. .:     :==+= :::::::::::.:----======-:-========+++*+  :+*+
: .-+=...    --....:::::::::::----=------=--=======++*-:*+: -
  =##@@: ---   .:::.........:::::-::::---------=====+*:--::-::. ..
 *@@@@@@= :=+-     ::..........::::::::::--------===*=   .-::-::==:
%@%%###%@@::==*+  .  .:.....::.:::::::::::::::::::---  .:::::-:-----:
```

>*Tommy Vercetti — rendered from his in-game portrait.*
A small Windows app that finishes the last few items of your *GTA
Vice City: Definitive Edition* save so you can unlock the **100% completion**
achievement without replaying a long game.

Tick a checkbox, save, done.

## Download

Grab **`GTA-VC-DE-Save-Editor.exe`** from the
[latest release](https://github.com/Haddy18/vc-de-save-editor/releases/latest)
and double-click it — no installation, no dependencies.

## Project status

This is a fan-made, community project and it still has **known limitations
and bugs**. Some custom or modded saves may fail to load, and the
achievement preparation is best-effort rather than guaranteed. The editor
writes into your save file, so **always keep a backup** before pressing
Save (the app also keeps the first `<file>.sav.bak` it sees). It is
provided as is, without warranty of any kind.

### Checklist mapping (fixed in this version)

The first release derived each checklist row from whatever variable held a
matching value in a 100% save, so ticking a mission could write "completed"
into a radar blip, a pickup index or a help timer and leave the save in a
state the game refuses to deserialize. The mapping was rebuilt from the
game's own scripts and is now checked against GTASnP for the sample saves in
`samples/`:

- all 37 story missions (Vercetti's Shakedown / Bar Brawl / Cop Land are the
  `FLAG_PROTECT_MISSION*_PASSED` flags), the 7 safe houses and the asset
  missions use their real flags;
- collectibles use their counters (packages, rampages, unique jumps) and
  "Rob All Stores" is the sum of the 15 `ROBBED_*` flags;
- five rows have no documented variable in the current build (Print Works
  and Phil's Place "Asset Acquired", Vigilante, RC Bandit Race and RC Baron
  Race). They are shown greyed out and read-only; the editor never writes
  them. Their weight is excluded from the displayed progress, and a save
  whose editable items are all complete is still reported as 100%.

Before saving, the editor diffs the result and aborts (writing nothing) if a
changed byte falls outside the checklist variables, the percentage float or
the MD5 seal. It also refuses to open a save whose flags do not read 0/1,
which catches saves from game builds with a different global layout.

## Related projects

Same family, other two games:

- [GTA III: Definitive Edition — 100% Save Editor](https://github.com/Haddy18/gta3-de-save-editor)
- [GTA San Andreas: Definitive Edition — 100% Save Editor](https://github.com/Haddy18/sa-de-save-editor)

## How to use

1. **Back up your save.** It lives in
   `Documents\Rockstar Games\GTA Vice City Definitive Edition\Profiles\<PROFILE>\GTAVCsf1.sav`.
2. Open the app and press **Open .sav...**
3. Tick whatever your save is still missing: story missions, asset missions, street races, payphone jobs, stadium events, chopper checkpoints, off-road and RC races, rampages, unique stunt jumps, hidden packages, and the taxi / firefighter / vigilante / paramedic missions.
4. The counters at the bottom update live: **Progress x/154** and
   **Missions x/37** are the real numbers the game uses for 100%.
5. Press **Save**. The save is written with a valid checksum, so the
   game loads it without complaining.

If the Rockstar launcher reports a cloud-sync conflict, pick **Local** —
that's normal for any edited save.

You can verify the result yourself by uploading the file to
[GTASnP](https://gtasnp.com) — everything should show green.

## Notes

- Works with any slot (`GTAVCsf1.sav`, `GTAVCsf2.sav`, …) and finds
  everything by structure, so it isn't tied to one specific playthrough.
- Single-player only. It edits your local save file; it does not touch
  online services. Still — always keep a backup.
- Missing a feature or found a bug? See [Contributing](#contributing).

## Contributing

This project is open to improvements — bug reports, fixes, new features and
forks are all welcome:

- **Found a bug?** Open an
  [issue](https://github.com/Haddy18/vc-de-save-editor/issues) with the
  game version, the save slot and what you expected to happen.
  Attaching a save that reproduces it (or the relevant offsets) helps
  a lot.
- **Want to fix it?** Fork the repository, make the change and send a **pull
  request**. Small, focused PRs are the easiest to review.
- **Forking is fine.** Derivative tools, translations and patches are
  welcome; a link back to this repository is appreciated.
- **No need to ask first.** There is no CLA and no fixed roadmap — the
  project moves at the pace of whoever has time and interest.

Testing a save from a different playthrough and reporting whether it loads
correctly is already a useful contribution.

## For developers

The whole editor is a single standard-library Python file:

```
python vc_save_editor.py            # GUI
python vc_save_editor.py --selftest # 27 checks against real saves
```

Releases are built automatically by GitHub Actions when a release is
published (PyInstaller, Windows).
