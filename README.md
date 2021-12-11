### bingo-menu

**中文** | [English](./README_en.md)

一个 bingo 小游戏的管理插件, 方便玩家进行队伍选择、游戏配置和对局的开始与结束


### 使用方法

1. 配置 [MCDR](https://github.com/Fallen-Breath/MCDReforged/)

2. 配置 handler

   - 在 MCDR 工作目录下创建 `handler/` 文件夹, 并将本项目专用的 `bingo_handler.py `放入其中
   - 在 `config.yml` 中的 custom_handlers项目下添加 - handler.bingo_handler.BingoHandler
   - 在 `config.yml` 中设置 handler 为 bingo_handler

3. 将 `bingo_menu.py` 加入 `plugin/ `文件夹

4. 使用 paper 的服务端, 并加入 [Bingo插件](https://github.com/Extremelyd1/minecraft-bingo)

5. 在 server/ 目录下添加 `datapacks/` 目录, 并将专用数据包`Worldgen_{version}.zip`加入其中(用于缩小群系与结构，由 [Youmiel](https://github.com/Youmiel) 贡献)

6. 开始游玩, 并在游戏中输入 `/all !!bg` 或 `/all !!bingo` 获取帮助信息

### 目录结构
```
mcdr_root\
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