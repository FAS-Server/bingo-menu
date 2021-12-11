### bingo-menu

[中文](./README.md) | **English**

A manager plugin for Bingo games, making it easier for players to select team, config the game, and start / stop the game instance.

### Usage

1. Setup [MCDR](https://github.com/Fallen-Breath/MCDReforged/)

2. Setup custom handler

   - Create folder `handler/` under MCDR working directory, put `bingo_handler.py ` inside
   - Edit `custom_handlers` in MCDR config file `config.yml` , add `- handler.bingo_handler.BingoHandler`
   - Set the `handler` in file `config.yml` to `bingo_handler`

3. add `bingo_menu.py` to MCDR's plugin folder `plugin/ `

4. Setup a [paper](https://papermc.io/) server, add the  [Bingo](https://github.com/Extremelyd1/minecraft-bingo) plugin

5. Create folder `datapacks/` in `server/`, put `Worldgen_{version}.zip` into it (used to increase the chance to see various biomes, credit to [Youmiel](https://github.com/Youmiel))

6. start playing, type `/all !!bg` in game to get the menu, or `/all !!bingo` for detailed help

### File Struct
```
bingo_root\
    handler\
        bingo_handler.py
    plugins\
        fas_bingo_manager.py
    config.yml
    server\
        plugins\
            MinecraftBingo-{version}.jar
        datapacks\
            Worldgen_{version}.zip
```