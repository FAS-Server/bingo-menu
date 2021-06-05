import os
import re
import time
import random
import shutil
from threading import Lock
from mcdreforged.api.decorator import *
from mcdreforged.api.command import Literal, GreedyText, UnknownArgument, Integer
from mcdreforged.api.rtext import RAction, RText, RTextList, RColor
from mcdreforged.api.types import CommandSource, PlayerCommandSource, ServerInterface, Info


PLUGIN_ID = 'bingo_menu'
PLUGIN_METADATA = {
    'id': PLUGIN_ID,
    'version': '1.1.1',
    'name': 'FAS bingo menu',
    'description': 'bingo 小游戏帮助菜单',
    'author': [
        'YehowahLiu', 'xunfeng'
    ],
    'link': 'https://github.com/FAS-Server/bingo-menu',
    'dependencies': {
        'mcdreforged': '>=1.0.0',
    }
}

conf = {
    # -------------------
    # | Plugin Settings |
    # -------------------
    'server_path': './server',
    'datapack_path': './server/datapacks',
    'ignore_datapacks': False,
    'world_names': ['world', 'world_nether', 'world_the_end'],
    'teams': ['red', 'blue', 'green', 'yellow', 'pink', 'aqua', 'gray', 'orange'],
    'restart_countdown': 300,

    # -----------------
    # | Game Settings |
    # -----------------
    'timer': True,
    'timer_len': 1800,
    'mode': 'lines',
    'item_distribution': '2,6,9,6,2',
    'pvp': False

}

default_conf = conf.copy()

Prefix = '!!bingo'

game_status = 'not_start'
teaming_players = []
teamed_players = []
spec_players = []
vote_agree_list = []
vote_disagree_list = []

# ------------
# | Messages |
# ------------

bingo_msg = '''§7-----§6{1}§r V§a{2}§7-----
§6Bingo §7小游戏管理插件
§a!!bg§7 显示快捷控制面板
§e{0}§7 显示这条帮助信息
§e{0} team§7 选择队伍
§e{0} vote§7 进行投票
§e{0} config§7 快捷修改游戏设置
§e{0} mode §7修改游戏模式
§e{0} timer§7 开/关限时模式
§e{0} timer§a [<限时时长>] §7修改限时模式时间，单位：分钟
§e{0} card§7 修改物品稀有度'''.format(Prefix, PLUGIN_METADATA['name'], PLUGIN_METADATA['version'])

to_all = "/all "

team_msg = RTextList(
    RText('§6--------选择队伍---------§r\n'),
    RText('§6◤§c红队§6◢   ').c(RAction.run_command,
                             f'{to_all}{Prefix} team red'),
    RText('§6◤§9蓝队§6◢   ').c(RAction.run_command,
                             f'{to_all}{Prefix} team blue'),
    RText('§6◤§a绿队§6◢ \n').c(RAction.run_command,
                             f'{to_all}{Prefix} team green'),
    RText('§6◤§e黄队§6◢   ').c(RAction.run_command,
                             f'{to_all}{Prefix} team yellow'),
    RText('§6◤§d粉队§6◢   ').c(RAction.run_command,
                             f'{to_all}{Prefix} team pink'),
    RText('§6◤§3天蓝§6◢ \n').c(RAction.run_command,
                             f'{to_all}{Prefix} team aqua'),
    RText('§6◤§7灰队§6◢   ').c(RAction.run_command,
                             f'{to_all}{Prefix} team gray'),
    RText('§6◤§6橙色§6◢   ').c(RAction.run_command,
                             f'{to_all}{Prefix} team orange'),
    RText('§6◤§8旁观§6◢ \n').c(RAction.run_command,
                             f'{to_all}{Prefix} team spec'),
    RText('§9◤§6随机分队§9◢ ').h(f'选择队伍数'),
    RText('[1]', ).c(
        RAction.run_command, f'{to_all}{Prefix} team random 1'),
    RText('[2]', ).c(
        RAction.run_command, f'{to_all}{Prefix} team random 2'),
    RText('[3]', ).c(
        RAction.run_command, f'{to_all}{Prefix} team random 3'),
    RText('[4]', ).c(
        RAction.run_command, f'{to_all}{Prefix} team random 4'),
    RText('[5]', ).c(
        RAction.run_command, f'{to_all}{Prefix} team random 5'),
    RText('[6]', ).c(
        RAction.run_command, f'{to_all}{Prefix} team random 6'),
    RText('[7]', ).c(
        RAction.run_command, f'{to_all}{Prefix} team random 7'),
    RText('[8]', ).c(
        RAction.run_command, f'{to_all}{Prefix} team random 8'),
)

no_team_msg = "未加入有效队伍!\n" + team_msg

not_start_menu = RTextList(
    RText('§a开始游戏§r  ').h('点击进行游戏开始投票').c(
        RAction.run_command, f'{to_all}{Prefix} vote start'),
    RText('§a游戏模式§r  ').h('点击选择游戏模式').c(
        RAction.run_command, f'{to_all}{Prefix} mode'),
    RText('§2切换队伍§r  ').h('点击切换队伍').c(
        RAction.run_command, f'{to_all}{Prefix} team'),
    RText('§e游戏设定§r').h('点击修改游戏设定').c(
        RAction.run_command, f'{to_all}{Prefix} config')
)

to_be_start_menu = '游戏马上开始，请做好准备'

started_menu = RTextList(
    RText('bingo？  ').h('检查bingo卡片').c(
        RAction.run_command, '/bingo'),
    RText('获取卡片  ').h('获得一张新的bingo卡片').c(
        RAction.run_command, '/card'),
    RText('分享坐标  ').h('向同队伍成员发送坐标').c(
        RAction.suggest_command, '/coords 可选注释'),
    RText('重选卡片  ').h('重新生成bingo卡片').c(
        RAction.run_command, f'{to_all}{Prefix} vote reroll'
    ),
    RText('公屏消息 ').h('发送一条所有人可见的消息').c(
        RAction.suggest_command, '/all 消息'),
    RText('§c结束游戏§r').h('点击进行结束游戏的投票').c(
        RAction.run_command, f'{to_all}{Prefix} vote end')
)

ended_menu = RText('§c重启游戏§r').h('进行重置游戏的投票').c(
    RAction.run_command, f'{to_all}{Prefix} vote restart')

vote_title = '无'

vote_choice_msg = RTextList(
    RText('§6◤§a点击同意§6◢§r').c(RAction.run_command,
                              f'{to_all}{Prefix} vote agree'),
    RText('    '),
    RText('§6◤§c点击反对§6◢§r').c(RAction.run_command,
                              f'{to_all}{Prefix} vote disagree')
)


mode_menu = RTextList(
    "§6-----选择模式-----\n",
    RText("§6◤§e全收集§6◢").c(RAction.run_command,
                           to_all + Prefix + " mode full"),
    "    ",
    RText("§6◤§a正 常§6◢").c(RAction.suggest_command,
                           to_all + Prefix + " mode lines 1"),
    "    ",
    RText("§6◤§d独 占§6◢").c(RAction.suggest_command,
                           to_all + Prefix + " mode lockout 1")
)

reseting_game_lock = Lock()
voting_lock = Lock()


# ---------
# | Utils |
# ---------


def print_msg(source: CommandSource, msg, tell=True, prefix='§e[Bingo] §r'):
    msg = prefix + msg
    if source.is_player and not tell:
        source.get_server().say(msg)
    else:
        source.reply(msg)


def print_log(source: CommandSource, msg, prefix='§e[Bingo] §r'):
    source.get_server().logger.info(prefix + msg)


def format_time(time_length):
    if time_length < 60:
        return '{}分钟'.format(time_length)
    elif time_length < 60 * 60:
        return '{}小时'.format(round(time_length / 60, 2))


# --------
# | Team |
# --------


def team_join(source: PlayerCommandSource, team=None):
    global game_status, spec_players, teamed_players, teaming_players
    if game_status != 'not_start':
        print_msg(source, f'当前游戏状态为:{game_status}，无法加入队伍', True)
        return
    elif team == 'spec':
        source.get_server().execute(f'gamemode spectator {source.player}')
        if not source.player in spec_players:
            spec_players.append(source.player)
        if source.player in teamed_players:
            teamed_players.remove(source.player)
            source.get_server().execute(f'team remove {source.player}')
        if source.player in teaming_players:
            teaming_players.remove(source.player)
        return
    elif team in conf['teams']:
        source.get_server().execute(
            f'team add {source.player} {team}')
        if not source.player in teamed_players:
            teamed_players.append(source.player)
        if source.player in spec_players:
            spec_players.remove(source.player)
            source.get_server().execute(f'gamemode survival {source.player}')
        return
    else:
        print_msg(source, f'无法加入队伍: {team}，请重新选择', True)
        print_msg(source, team_msg)


def team_random(source: PlayerCommandSource, num: int):
    global teaming_players, teamed_players, conf
    server = source.get_server()
    if source.player in spec_players:
        print_msg(source, "§c观察者不能随机分队!")
        return
    teams = conf['teams']
    if num <= len(teams) and num > 0:
        teamed_players = []
        players = teaming_players.copy()
        i = 0
        while len(players) != 0:
            player = random.choice(players)
            server.execute(f'gamemode survival {player}')
            server.execute(f'team add {player} {teams[i % num]}')
            teamed_players.append(player)
            players.remove(player)
            i += 1
    else:
        print_msg(source, "错误的数字, 队伍数目应在1到{}之间".format(len(teams)))


# --------
# | Vote |
# --------

@new_thread
def vote(source: PlayerCommandSource, command):
    global vote_agree_list, vote_disagree_list, voting_lock, vote_title
    if reseting_game_lock.locked():
        print_msg(source, '§c重置游戏中，无法进行投票§r', True)
        return
    elif source.player in spec_players:
        print_msg(source, '§c观察者不能投票§r', True)
        print_msg(source, team_msg)
        return
    elif not source.player in teamed_players:
        print_msg(source, RText('§c加入非观察者队伍才能投票§r \n'), True)
        print_msg(source, team_msg)
        return
    elif command == 'restart' and game_status in ['started', 'to_be_start']:
        print_msg(source,
                  '游戏进行中，点击开启 ' +
                  RText('§6◤§c结束游戏§6◢§r').c(RAction.run_command,
                                            f'{to_all}{Prefix} vote end')
                  + ' 投票')
        return
    else:
        acquire = voting_lock.acquire(blocking=False)
        if not acquire:
            print_msg(source, '§c已有进行中的投票：§r', True)
            print_msg(source, vote_title, True, '')
            print_msg(source, vote_choice_msg, True, '')
            return
        elif acquire:
            vote_agree_list.append(source.player)
            vote_title = f'{source.player} 发起投票：{command}'
            print_msg(source, vote_title+',请在30s内表决', False, '')
            print_msg(source, vote_choice_msg, False, '')
            vote_timer = 0
            server = source.get_server()
            server.execute(
                'bossbar add bingo:vote {"text":"Vote time left:","color":"red"}')
            server.execute('bossbar set bingo:vote color red')
            server.execute('bossbar set bingo:vote style notched_6')
            server.execute('bossbar set bingo:vote max 300')
            server.execute('bossbar set bingo:vote players @a')
            while(vote_timer < 300):
                time.sleep(0.1)
                vote_timer += 1

                server.execute(
                    f'bossbar set bingo:vote value {300 - vote_timer}')
                if len(vote_agree_list) >= len(teamed_players) / 2 \
                        or len(vote_disagree_list) >= len(teamed_players) / 2:
                    break
                elif vote_timer % 10 == 0:
                    server.execute(
                        'bossbar set bingo:vote name {"text":"Vote time left:' + str(300-vote_timer/10)+'s","color":"red"}')
                    if vote_timer % 100 == 0 or vote_timer >= 250:
                        server.say(f'距离投票结束还有{30 - vote_timer / 10}秒')
            server.execute('bossbar remove bingo:vote')
            execute_vote_result(source, command, len(vote_agree_list)
                                >= len(vote_disagree_list), vote_timer >= 300)
            vote_agree_list = []
            vote_disagree_list = []
            vote_title = ''
            voting_lock.release()


def execute_vote_result(source: PlayerCommandSource, command: str, result=True, time_out=False):
    global vote_title
    server = source.get_server()
    message = vote_title
    message += ' 已超时,' if time_out else ' 已结束,'
    message += '§a同意方' if result else '§c反对方'
    message += ' §r胜利'
    print_msg(source, message, False, '')
    if result:
        if command == 'restart':
            restart_game(source.get_server())
            return
        elif command == 'start':
            server.execute(
                'bossbar add bingo:vote_result {"text":"Starting Game...","color":"green"}')
            server.execute('bossbar set bingo:vote_result color green')
            server.execute('bossbar set bingo:vote_result style progress')
            server.execute('bossbar set bingo:vote_result max 5')
            server.execute('bossbar set bingo:vote_result players @a')
            for countdown in range(1, 5):
                print_msg(
                    source, f'§c{5 - countdown}§r秒后开始游戏，请做好准备！', False)
                server.execute(
                    f'bossbar set bingo:vote_result value {5 - countdown}')
                time.sleep(1)
            server.execute('bossbar remove bingo:vote_result')
        server.execute(command)


def agree_vote(source: PlayerCommandSource, agree: bool):
    listA, agree_msg = (vote_agree_list, '§a同意§r') if agree else (
        vote_disagree_list, '§c反对§r')
    if not source.player in teamed_players:
        print_msg(source, no_team_msg)
    elif not voting_lock.locked():
        print_msg(source, '§c没有进行中的投票§r', True)
    elif source.player in vote_disagree_list or source.player in vote_agree_list:
        print_msg(source, '§c你已经投过票了§r', True)
    else:
        listA.append(source.player)
        print_msg(source, f'{source.player}投出{agree_msg}票', False)


def print_vote_msg(source: CommandSource):
    global voting_lock, game_status, vote_title
    if voting_lock.locked:
        print_msg(source, '§c已经有正在进行的投票了：§r', True, '')
        print_msg(source, vote_title, True, '')
    pass


# ------------------
# | Server Control |
# ------------------

@new_thread
def restart_game(server: ServerInterface):
    global conf, game_status, teamed_players, spec_players, teaming_players, reseting_game_lock
    folder = conf['server_path']
    acquire = reseting_game_lock.acquire(blocking=False)
    if not acquire:
        return
    elif acquire:
        server.execute(
            'bossbar add bingo:restarting {"text":"Restarting Server...","color":"aqua"}')
        server.execute('bossbar set bingo:restarting color blue')
        server.execute('bossbar set bingo:restarting style progress')
        server.execute('bossbar set bingo:restarting max 10')
        server.execute('bossbar set bingo:restarting players @a')
        for countdown in range(1, 10):
            server.say(f'{10 - countdown}s后重启服务器')
            server.execute(
                f'bossbar set bingo:restarting value {10 - countdown}')
            time.sleep(1)
        server.execute('bossbar remove bingo:restarting')

        # reset confings
        teamed_players = []
        spec_players = []
        teaming_players = []
        conf = default_conf.copy()

        # first restart
        server.stop()
        server.wait_for_start()
        for world in conf['world_names']:
            shutil.rmtree(os.path.realpath(os.path.join(folder, world)))
        if not conf['ignore_datapacks']:
            shutil.copytree(conf['datapack_path'],
                            os.path.realpath(os.path.join(folder, 'world', 'datapacks')))
        server.start()

        while(game_status != 'not_start'):
            time.sleep(0.1)
        server.restart()
        reseting_game_lock.release()


# ---------------
# | Game Config |
# ---------------

def print_config_edit(source: PlayerCommandSource):
    global voting_lock, teamed_players, conf
    timer = conf["timer"]
    timer_len = conf["timer_len"]
    msg = ''
    if not source.player in teamed_players:
        msg = not_start_menu.copy()
    elif voting_lock.locked():
        msg = '§c无法修改游戏配置，请先完成投票：§r\n'
        msg += vote_title + vote_choice_msg
    elif game_status != 'not_start':
        msg = '§c只有游戏未开始时可以修改游戏配置！§r'
    else:
        msg = RTextList(
            RText('  '),
            RText(f'§{"a" if timer else "c"}限时模式§r')
            .h(f'{"§c关闭" if timer else "§a打开"}§r限时模式')
            .c(RAction.run_command, f'{to_all}{Prefix} timer'),
            RText('  '),
            RText('限时时长')
            .h(f'当前 {timer_len}s, 点击切换')
            .c(RAction.suggest_command, f'{to_all}{Prefix} timer 30'),
            RText('    '),
            RText('物品稀有度')
            .h('物品的稀有度分布 <S> <A> <B> <C> <D>,\n要求<S>+<A>+<B>+<C>+<D> = 25')
            .c(RAction.suggest_command, f'{to_all}{Prefix} card 2 6 9 6 2')
        )
    print_msg(source, msg, prefix='')


def set_timer_len(source: CommandSource, length: int):
    global conf
    conf['timer_len'] = length * 60
    source.get_server().execute('timer {}'.format(conf['timer_len']))
    print_msg(source, f'当前的时间限制为 {conf["timer_len"]/60}min', False)


def set_timer(source: CommandSource):
    global conf
    command_line = 'timer '
    command_line += 'disable' if conf["timer"] else 'enable'
    conf["timer"] = not conf["timer"]
    source.get_server().execute(command_line)
    print_msg(source, f'限时模式已{"§a打开§r" if conf["timer"] else "§c关闭§r"}', False)


def set_itemdist(source: CommandSource, s: str):
    nums = [int(i) for i in s.split()]
    if len(nums) == 5:
        sum_of_nums = 0
        for i in nums:
            sum_of_nums += i
        if sum_of_nums == 25:
            source.get_server().execute('dist '+s)
            return
        else:
            source.reply('§c参数错误：物品稀有度的和不是25§r')
    else:
        source.reply('§c参数错误：物品稀有度需要5个数字§r')


def set_game_mode(src: PlayerCommandSource, mode: str, num: int = 1):
    global conf
    if not src.player in teamed_players:
        print_msg(src, no_team_msg)
    elif game_status != "not_start":
        print_msg(src, f"当前游戏状态为 {game_status} !")
    elif mode == "full":
        src.get_server().execute("wincon full")
        conf["mode"] = mode
    elif mode in ["lockout", "lines"]:
        conf["mode"] = mode
        src.get_server().execute(f"wincon {mode} {num}")
    else:
        print_msg(src, "错误的指令!")
    return


def print_bingo_menu(source: PlayerCommandSource):
    if not source.player in teamed_players:
        print_msg(source, no_team_msg)
        return
    elif voting_lock.locked():
        print_msg(source, vote_title + vote_choice_msg)
        return
    elif game_status == 'not_start':
        print_msg(source, not_start_menu)
        return
    elif game_status == 'to_be_start':
        print_msg(source, to_be_start_menu)
        return
    elif game_status == 'started':
        print_msg(source, started_menu)
        return
    else:
        print_msg(source, ended_menu)
        return


def print_unknown_argument_message(source: CommandSource, error: UnknownArgument):
    print_msg(source, RText('参数错误！请输入§7{}§r以获取插件信息'.format(
        Prefix)).h('点击查看帮助').c(RAction.run_command, Prefix))


def register_command(server: ServerInterface):
    server.register_command(
        Literal(Prefix).
        runs(lambda src: print_msg(src, bingo_msg, True, '')).
        on_error(UnknownArgument, print_unknown_argument_message, handled=True).
        then(
            Literal('team').
            runs(lambda src: print_msg(src, team_msg)).
            then(
                Literal('random').runs(lambda src: print_msg(src, "未选择队伍数")).
                then(Integer('num').runs(
                    lambda src, ctx: team_random(src, ctx['num']))
                )).
            then(GreedyText('color').runs(
                lambda src, ctx: team_join(src, ctx['color'])))
        ).
        then(
            Literal('vote').runs(lambda src: print_vote_msg(src)).
            then(
                Literal('start').runs(lambda src: vote(src, 'start'))
            ).
            then(
                Literal('end').runs(lambda src: vote(src, 'end'))
            ).
            then(
                Literal('reroll').runs(lambda src: vote(src, 'reroll'))
            ).
            then(
                Literal('restart').runs(lambda src: vote(src, 'restart'))
            ).
            then(
                Literal('agree').runs(lambda src: agree_vote(src, True))
            ).
            then(
                Literal('disagree').runs(lambda src: agree_vote(src, False))
            )
        ).
        then(
            Literal('config').runs(print_config_edit)
        ).
        then(
            Literal('timer').runs(set_timer).
            then(
                Integer('length').runs(
                    lambda src, ctx: set_timer_len(src, ctx['length']))
            )
        ).
        then(
            Literal('card').
            then(
                GreedyText('s').runs(
                    lambda src, ctx: set_itemdist(src, ctx['s']))
            )
        ).
        then(
            Literal('mode').runs(lambda src: print_msg(src, mode_menu)).
            then(
                Literal('full').runs(lambda src: set_game_mode(src, "full"))
            ).
            then(
                Literal('lines').runs(lambda src: print_msg(src, '指令不完整！')).
                then(
                    Integer('lines').runs(
                        lambda src, ctx: set_game_mode(src, "lines", ctx['lines']))
                )
            ).
            then(
                Literal('lockout').runs(lambda src: print_msg(src, '指令不完整！')).
                then(
                    Integer('lines').runs(lambda src, ctx: set_game_mode(
                        src, "lockout", ctx['lines']))
                )
            )
        )
    )
    server.register_command(Literal('!!bg').runs(print_bingo_menu))


def on_player_joined(server: ServerInterface, player, info: Info):
    if player not in teaming_players and player not in spec_players:
        teaming_players.append(player)
    if player not in teamed_players:
        server.tell(player, team_msg)
    else:
        try:
            server.tell(player, eval(game_status+"_menu"))
        except:
            pass


def on_player_left(server: ServerInterface, player):
    if player in teaming_players:
        teaming_players.remove(player)


def on_load(server: ServerInterface, old):
    register_command(server)
    server.register_help_message(Prefix, RText(
        'bingo游戏菜单').h('点击显示').c(RAction.run_command, Prefix))


def on_info(server: ServerInterface, info: Info):
    global game_status, teaming_players, conf
    if info.is_user:
        pass
    elif re.fullmatch(r'BINGO                             Game has ended!', info.content):
        restart_countdown(server)
        game_status = 'ended'
    elif re.fullmatch(r'BINGO                            Game has started!', info.content):
        game_status = 'started'
        start_bossbar_countdown(server)
    elif not re.search(r'team has gotten bingo!', info.content) is None:
        restart_countdown(server)
        game_status = 'ended'
    elif not re.search(r'Creating Game instance', info.content) is None:
        game_status = 'not_start'
        conf = default_conf
    elif re.fullmatch(r'Closing Server', info.content):
        game_status = 'ended'
    else:
        pass


@new_thread
def start_bossbar_countdown(server: ServerInterface):
    global game_status, conf
    if conf['timer']:
        timer_len = conf['timer_len']
        server.execute(
            'bossbar add bingo:game {"text":"Time left:","color":"yellow"}')
        server.execute('bossbar set bingo:game color yellow')
        server.execute('bossbar set bingo:game style notched_10')
        server.execute(f'bossbar set bingo:game max {timer_len}')
        server.execute(f'bossbar set bingo:game value {timer_len}')
        server.execute('bossbar set bingo:game players @a')
        maxtime = timer_len
        t = 0
        while t <= maxtime:
            server.execute(f'bossbar set bingo:game value {maxtime - t}')
            command = 'bossbar set bingo:game name {"text":"Time left:' + str(
                maxtime - t) + 's","color":"yellow"}'
            server.execute(command)
            time.sleep(1)
            if game_status == 'started':
                t += 1
            else:
                server.execute('bossbar remove bingo:game')
                break
    return


@new_thread
def restart_countdown(server: ServerInterface):
    global conf, reseting_game_lock
    countdown = conf['restart_countdown']
    if countdown <= 0:
        return
    else:
        server.execute(
            'bossbar add bingo:auto_restart {"text":"Auto Restart in:","color":"red"}')
        server.execute('bossbar set bingo:auto_restart color red')
        server.execute('bossbar set bingo:auto_restart style notched_10')
        server.execute(f'bossbar set bingo:auto_restart max {countdown}')
        server.execute(f'bossbar set bingo:auto_restart value {countdown}')
        server.execute('bossbar set bingo:auto_restart players @a')
        t = 0
        while t <= countdown and not reseting_game_lock.locked():
            server.execute(
                f'bossbar set bingo:auto_restart value {countdown - t}')
            command = 'bossbar set bingo:auto_restart name {"text":"Auto Restart in:' + str(
                countdown - t) + 's","color":"red"}'
            server.execute(command)
            time.sleep(1)
            t += 1
        server.execute('bossbar remove bingo:auto_restart')
        if t > countdown:
            restart_game(server)
