### FAS-bingo

一个用于 fas 服务器 bingo 小游戏的 mcdr 插件


### 使用方法

1. 配置 [MCDR](https://github.com/Fallen-Breath/MCDReforged/)

2. 配置 handler

   - 在 MCDR 工作目录下创建 `handler/` 文件夹, 并将本项目专用的 `bingo_handler.py `放入其中
   - 在 `config.yml` 中的 custom_handlers项目下添加 - handler.bingo_handler.BingoHandler
   - 在 `config.yml` 中设置 handler 为 bingo_handler

3. 将 `fas_bingo_manager.py` 加入 `plugin/ `文件夹

4. 使用类 paper 的服务端, 并加入 [Bingo插件](https://github.com/Extremelyd1/minecraft-bingo)

5. 在 server/ 目录下添加 `datapacks/` 目录, 并将专用数据包`world_gene.zip`加入其中(用于修改世界生成时的群系与结构)

6. 开始游玩, 并在游戏中输入 `!!bg` 获取帮助信息

### 目录结构
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
            world_gene.zip
```

**tips**: 在加入队伍后，需要使用 `/all` 发送全体消息, 因为 MCDR 无法响应队伍消息。