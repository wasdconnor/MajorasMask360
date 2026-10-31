# Majora's Mask 360

The Legend of Zelda: Majora's Mask running natively on a modded Xbox 360, as a `.xex`. It's a port
of the PC recompilation ([Zelda64Recomp](https://github.com/Zelda64Recomp/Zelda64Recomp), built on
[N64Recomp](https://github.com/N64Recomp/N64Recomp)) with a renderer written for the 360's GPU.
It's not an emulator: the game's code was recompiled to run directly on the console.

**No game data is included.** You need your own copy of the game (see below).

## Improvements over the original

- **Higher resolution:** drawn at 1280×720, three times the N64's 320×240
- **60 FPS**
- **16:9 widescreen** 
- **Anti-aliasing:** FXAA smooths jagged edges.
- **HD textures (optional):** load a 2 Ship 2 Harkinian HD texture pack, such as ReMasked, for
  high-resolution HUD, text, icons and more (see [HD textures](#hd-textures-optional)).

## What you need

1. **A modded Xbox 360 (RGH or JTAG)** that can run unsigned homebrew, with a dashboard or file
   manager that launches `.xex` files (Aurora, FreeStyle Dash, XeXMenu, ...).
2. **A way to copy files to it**: a USB drive (FAT32), or FTP to the console's hard drive.
3. **Your own Majora's Mask ROM: the USA (NTSC-U 1.0) release.** Other versions (Europe, Japan,
   GameCube, Virtual Console) won't work. You can check yours against these hashes:
   - SHA-1 `d6133ace5afaa0882cf214cf88daba39e266c078`
   - MD5 `2a0a8acb61538235bc1094d297fb6556`

   Tthe file's extension must be `.z64`: rename it if it isn't.

## Installing

1. Download `mm360.xex` from the [latest release](https://github.com/wasdconnor/MajorasMask360/releases/latest).
2. Make a folder for the game on the console's hard drive or a USB drive, for example
   `Hdd1:\Games\MajorasMask360\` or `Usb0:\Apps\MajorasMask360\`.
3. Put two files in it:
   ```
   MajorasMask360\
     mm360.xex
     <your ROM>.z64      (any name, as long as it ends in .z64)
   ```
4. Launch `mm360.xex` from your dashboard's file manager. (If you'd like your dashboard's game
   scanner to find it, rename it to `default.xex`.)

The folder has to be writable: the game creates a few files of its own next to the `.xex`.

| File | What it is |
|---|---|
| `saves\` | Your save file. Back this folder up if you care about your progress. |
| `shaders.bin` | Graphics shaders compiled on earlier runs. The first time a new effect shows up it can be missing for a moment while it compiles; afterwards it's instant. Safe to delete. |
| `watchdog.txt` | A small diagnostic log. Safe to delete. |

## HD textures (optional)

The game can replace its textures with ones from a [2 Ship 2 Harkinian](https://github.com/HarbourMasters/2ship2harkinian)
HD texture pack (an `.o2r` file), such as ReMasked. Packs are made by their own authors and aren't
included here; the console needs one converted into `hd_textures.bin` with the script in `tools/`.
You need Python 3 and Git on a PC.

1. Get the pack and extract its `.o2r` file (for ReMasked, `MM_ReMasked_V1.4.2.o2r` from its zip).
2. Install Pillow, and get the Majora's Mask decompilation, which says where each texture is in
   the ROM:
   ```
   pip install pillow
   git clone https://github.com/zeldaret/mm mm-decomp
   git -C mm-decomp checkout 5607eec18bae68e4cd38ef6d1fa69d7f1d84bfc8
   ```
3. Download this repository's `tools` folder and run, with your ROM (the `.z64` byte order only):
   ```
   python -I tools/build_hd_pack.py MM_ReMasked_V1.4.2.o2r <your ROM>.z64 hd_textures.bin --decomp mm-decomp
   ```
4. Copy `hd_textures.bin` into the game's folder, next to `mm360.xex`. The game loads it at
   startup; delete it to go back to the original textures.

The pack is held in memory, and the script scales its images down to three times the original
size (what 720p can show), which keeps ReMasked to about 45 MB. Anything the pack doesn't cover
keeps its original texture, and so do a few textures the game loads in pieces (the title logo,
the day title cards).

## Controls

| N64 | Xbox 360 |
|---|---|
| Analog stick | Left stick |
| A | A |
| B | X |
| C buttons | Right stick (up / down / left / right) |
| Z | Left trigger |
| R | Right trigger or right bumper |
| L | Left bumper |
| Start | Start |
| D-pad | D-pad |

Rumble works as the Rumble Pak. Clicking the right stick shows or hides a performance readout in
the right-hand border.

## Troubleshooting

**A dark red screen with a red square and a number:** the game didn't find a ROM it can use.

| Number | Meaning |
|---|---|
| 1 | No `.z64` file next to the `.xex` (check the extension) |
| 2 | The file isn't an N64 ROM |
| 3 | It's a ROM of a different game |
| 5 | It's Majora's Mask, but not the USA (NTSC-U 1.0) version |

Press Back on that screen to return to the dashboard.

## Known issues

- The pause menu's blurred background and the Pictograph Box's photos aren't drawn.
- There's no settings menu: controls and display options are fixed.

## Legal

This is a fan project, not affiliated with or endorsed by Nintendo. The `.xex` contains no assets
from the game (models, textures, music, text); it can't run without a ROM you supply, and the
game's data comes from that ROM. Only use a ROM dumped from a cartridge you own.

Credits: [Zelda64Recomp](https://github.com/Zelda64Recomp/Zelda64Recomp),
[N64Recomp](https://github.com/N64Recomp/N64Recomp) and
[N64ModernRuntime](https://github.com/N64Recomp/N64ModernRuntime) by Wiseguy and contributors,
the [Majora's Mask decompilation](https://github.com/zeldaret/mm) project, and the audio code from
[mupen64plus-rsp-hle](https://github.com/mupen64plus/mupen64plus-rsp-hle).
