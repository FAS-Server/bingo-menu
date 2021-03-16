import json
import os
import re
import shutil
import time
from threading import Lock
from mcdreforged.api.all import *

PLUGIN_ID = 'fas_bingo_manager'
PLUGIN_METADATA = {
    'id': PLUGIN_ID,
    'version': '1.0.7',
    'name': 'FAS bingo manager',
    'description': 'bingo 小游戏帮助菜单',
    'author': [
        'YehowahLiu'
    ],
    'link': 'https://github.com/FAS-Server/FAS-bingo',
    'dependencies': {
        'mcdreforged': '>=1.0.0-alpha.7',
    }
}
Prefix = '!!bingo'
server_path = '.\server'
datapack_path = '.\server\datapacks'
ignore_datapacks = False
world_names = [
    'world',
    'world_nether',
    'world_the_end',
]
teams = [
    'red',
    'blue',
    'green',
    'yellow',
    'pink',
    'aqua',
    'gray'
]
pvp = -1
wincondition = 1
timer = 1
timer_len = '60'
game_status = 'not_start'
bingo_players = []
sp_players = []
vote_agree = []
vote_disagree = []
vote_title = ''

bingo_msg = '''
§7-----§6{1}§r V§a{2}§7-----
§6Bingo §7小游戏管理插件
§a!!bg§7 显示快捷控制面板
§e{0}§7 显示这条帮助信息
§e{0} team§7 选择队伍
§e{0} vote§7 进行投票
§e{0} config§7 快捷修改游戏设置
§e{0} pvp§7 开/关pvp功能
§e{0} timer§7 开/关限时模式
§e{0} timer§a [<time>] §7修改限时模式时间，单位：分钟
§e{0} card§7 修改物品稀有度
§e{0} wincondition§a [<length>] §7修改完成游戏所需连线数量
§c注意：限于MCDR工作机制，在加入队伍后需在指令前加入§e/all §c参数§r
'''.format(Prefix, PLUGIN_METADATA['name'], PLUGIN_METADATA['version'])
vote_title = ''

reseting_game_lock = Lock()
voting_lock = Lock()


def print_msg(source: CommandSource, msg, tell=True, prefix='§e[FAS-Bingo] §r'):
    msg = prefix + msg
    if source.is_player and not tell:
        source.get_server().say(msg)
    else:
        source.reply(msg)


def print_log(source: CommandSource, msg, prefix='§e[FAS-Bingo] §r'):
    source.get_server().logger.info(prefix + msg)


def format_time(time_length):
    if time_length < 60:
        return '{}分钟'.format(time_length)
    elif time_length < 60 * 60:
        return '{}小时'.format(round(time_length / 60, 2))


def team_join(source: PlayerCommandSource, team=None):
    global game_status, sp_players, bingo_players
    if game_status != 'not_start':
        print_msg(source, f'当前游戏状态为:{game_status}，无法加入队伍', True)
        return
    elif team == 'spectator':
        source.get_server().execute(f'gamemode spectator {source.player}')
        if not source.player in sp_players:
            sp_players.append(source.player)
        if source.player in bingo_players:
            bingo_players.remove(source.player)
            source.get_server().execute(f'team remove {source.player}')
        return
    elif team in teams:
        source.get_server().execute(
            f'team add {source.player} {team}')
        if not source.player in bingo_players:
            bingo_players.append(source.player)
        if source.player in sp_players:
            sp_players.remove(source.player)
            source.get_server().execute(f'gamemode survival {source.player}')
        return
    else:
        print_msg(source, f'无法加入队伍: {team}，请重新选择', True)
        print_team_msg(source)


def print_team_msg(source: PlayerCommandSource):
    tell_all = ''
    if source is None:
        pass
    elif source.player in bingo_players:
        tell_all = '/all '
    msg = RTextList(
        RText('§6--------选择队伍---------§r\n'),
        RText('§6◤§c红队§6◢   ', color=RColor.red).c(
            RAction.run_command, f'{tell_all}{Prefix} team red'),
        RText('§6◤§9蓝队§6◢   ', color=RColor.blue).c(
            RAction.run_command, f'{tell_all}{Prefix} team blue'),
        RText('§6◤§a绿队§6◢   ', color=RColor.green).c(
            RAction.run_command, f'{tell_all}{Prefix} team green'),
        RText('§6◤§e黄队§6◢\n', color=RColor.yellow).c(
            RAction.run_command, f'{tell_all}{Prefix} team yellow'),
        RText('§6◤§d粉队§6◢   ', color=RColor.dark_purple).c(
            RAction.run_command, f'{tell_all}{Prefix} team pink'),
        RText('§6◤§3天蓝§6◢   ', color=RColor.aqua).c(
            RAction.run_command, f'{tell_all}{Prefix} team aqua'),
        RText('§6◤§7灰队§6◢   ', color=RColor.gold).c(
            RAction.run_command, f'{tell_all}{Prefix} team gray'),
        RText('§6◤§8旁观§6◢', color=RColor.gray).c(
            RAction.run_command, f'{tell_all}{Prefix} team spectator')
    )
    if source is None:
        return msg
    else:
        source.reply(msg)


@new_thread
def vote(source: PlayerCommandSource, msg):
    global vote_agree, vote_disagree, voting_lock, bingo_players, sp_players, vote_title
    if reseting_game_lock.locked():
        print_msg(source, '§c重置游戏中，无法进行投票§r', True)
        return
    elif source.player in sp_players:
        print_msg(source, '§c观察者不能投票§r', True)
        print_team_msg(source)
        return
    elif not source.player in bingo_players:
        print_msg(source, RText('§c加入非观察者队伍才能投票§r \n'), True)
        print_team_msg(source)
        return
    elif msg == 'restart' and game_status in ['started', 'to_be_start']:
        print_msg(source,
                  '游戏进行中，点击开启 ' +
                  RText('§6◤§c结束游戏§6◢§r').c(RAction.run_command,
                                            f'/all {Prefix} vote end')
                  + ' 投票')
        return
    else:
        acquire = voting_lock.acquire(blocking=False)
        if not acquire:
            print_msg(source, '§c已有进行中的投票：§r', True)
            print_msg(source, vote_title, True, '')
            print_msg(source,
                      RTextList(
                          RText('§6◤§a点击同意§6◢§r').c(
                              RAction.run_command, f'/all {Prefix} vote agree'),
                          RText('    '),
                          RText('§6◤§c点击反对§6◢§r').c(
                              RAction.run_command, f'/all {Prefix} vote disagree')
                      ),
                      True, '')
            return
        elif acquire:
            vote_agree.append(source.player)
            vote_title = f'{source.player} 发起投票：{msg}'
            print_msg(source, vote_title+',请在30s内表决', False, '')
            print_msg(source,
                      RTextList(
                          RText('  '),
                          RText('§6◤§a点击同意§6◢§r').c(RAction.run_command,
                                                    f'/all {Prefix} vote agree'),
                          RText('    '),
                          RText('§6◤§c点击反对§6◢§r').c(RAction.run_command,
                                                    f'/all {Prefix} vote disagree')
                      ),
                      False, '')
            vote_timer = 0
            while(vote_timer < 300):
                time.sleep(0.1)
                vote_timer += 1
                if len(vote_agree) >= len(bingo_players) / 2:
                    break
                elif len(vote_disagree) >= len(bingo_players) / 2:
                    break
                else:
                    if vote_timer % 100 == 0 or vote_timer >= 250:
                        source.get_server().broadcast(
                            f'距离投票结束还有{30 - vote_timer / 10}秒')
            execute_vote_result(source, msg, len(vote_agree)
                                >= len(vote_disagree), vote_timer >= 300)
            vote_agree = []
            vote_disagree = []
            vote_title = ''
            voting_lock.release()


def execute_vote_result(source: PlayerCommandSource, msg: str, result=True, time_out=False):
    global vote_title, server_path
    message = vote_title
    message += ' 已超时,' if time_out else ' 已结束,'
    message += '§a同意方' if result else '§c反对方'
    message += ' §r胜利'
    print_msg(source, message, False, '')
    if result:
        if msg == 'restart':
            restart_game(source, server_path)
            return
        else:
            if msg == 'start':
                for countdown in range(1, 5):
                    print_msg(
                        source, f'§c{5 - countdown}§r秒后开始游戏，请做好准备！', False)
                    time.sleep(1)
            source.get_server().execute(msg)


def agree_vote(source: PlayerCommandSource):
    global vote_agree, voting_lock, bingo_players
    if not source.player in bingo_players:
        print_msg(source, RText('§c请先选择非观察者队伍§r'))
        print_team_msg(source)
    elif not voting_lock.locked():
        print_msg(source, '§c没有进行中的投票§r', True)
    elif source.player in vote_disagree or source.player in vote_agree:
        print_msg(source, '§c你已经投过票了§r', True)
    else:
        vote_agree.append(source.player)
        print_msg(source, f'{source.player}投出§a同意§r票', False)


def disagree_vote(source: PlayerCommandSource):
    global vote_disagree, voting_lock, bingo_players
    if not source.player in bingo_players:
        print_msg(source, RText('请先选择非观察者队伍 \n'))
        print_team_msg(source)
    elif not voting_lock.locked():
        print_msg(source, '§c没有进行中的投票§r', True)
    elif source.player in vote_disagree or source.player in vote_agree:
        print_msg(source, '§c你已经投过票了§r')
    else:
        vote_disagree.append(source.player)
        print_msg(source, f'{source.player}投出了§c反对§r票', False)


def print_vote_msg(source: CommandSource):
    global voting_lock, game_status, vote_title
    if voting_lock.locked:
        print_msg(source, '§c已经有正在进行的投票了：§r', True, '')
        print_msg(source, vote_title, True, '')
    pass


@new_thread
def restart_game(source: CommandSource, folder):
    global game_status, bingo_players, reseting_game_lock

    def mkdir(path):
        if not os.path.exists(path):
            os.mkdir(path)
    acquire = reseting_game_lock.acquire(blocking=False)
    if not acquire:
        print_msg(source, '正在重启中，请不要重复输入')
        return
    elif acquire:
        for countdown in range(1, 10):
            print_msg(source, f'{10 - countdown}s后重启服务器', False)
            time.sleep(1)
        bingo_players = []
        print_log(source, '服务器关闭中~')
        source.get_server().stop()
        source.get_server().wait_for_start()

        print_log(source, '进行文件操作中')
        for world in world_names:
            shutil.rmtree(os.path.realpath(os.path.join(folder, world)))
        if not ignore_datapacks:
            shutil.copytree(datapack_path,
                            os.path.realpath(os.path.join(server_path, 'world', 'datapacks')))

        print_log(source, '第一次重启服务器')
        source.get_server().start()
        while(game_status != 'not_start'):
            time.sleep(0.01)
        source.get_server().restart()
        print_log(source, '第二次重启，以确保加载到世界生成数据包')
        reseting_game_lock.release()


def set_pvp(source: CommandSource):
    global pvp
    source.get_server().execute('pvp')
    pvp *= -1


def set_timer_len(source: CommandSource, length: int):
    source.get_server().execute('timer {}'.format(length * 60))
    timer_len = length
    print_msg(source, f'当前的时间限制为 {format_time(length)}', False)


def set_timer(source: CommandSource):
    global timer
    command_line = 'timer '
    command_line += 'enable' if timer == -1 else 'disable'
    timer *= -1
    source.get_server().execute(command_line)
    print_msg(source, f'限时模式已{"§c关闭§r" if timer == -1 else "§a打开§r"}', False)


def set_itemdistribution(source: CommandSource, s: str):
    nums = [int(i) for i in s.split(',')]
    if len(nums) == 5:
        sum_of_nums = 0
        for i in nums:
            sum_of_nums += i
        if sum_of_nums == 25:
            source.get_server().execute('itemdistribution '+s)
            return
        else:
            source.reply('§c参数错误：物品稀有度的和不是25§r')
    else:
        source.reply('§c参数错误：物品稀有度需要5个数字§r')


def set_wincondition(source: CommandSource, line: Integer):
    global wincondition
    if line <= 10 and line >= 1:
        source.get_server().execute(f'wincondition {line}')
        print_msg(source, f'当前胜利条件为完成{line}条线', False)
        wincondition = line
    else:
        source.reply('§c参数错误：胜利条件应该为1-10的整数！§r')


def print_bingo_menu(source: PlayerCommandSource):
    global game_status, bingo_players, voting_lock, vote_title
    if source is None or not source.player in bingo_players:
        print_msg(source, RText('请先 §2选择队伍§r'), True)
        print_team_msg(source)
    elif voting_lock.locked():
        msg = vote_title
        msg += '\n'+RTextList(
            RText('§6◤§a点击同意§6◢§r').c(RAction.run_command,
                                      f'/all {Prefix} vote agree'),
            RText('    '),
            RText('§6◤§c点击反对§6◢§r').c(RAction.run_command,
                                      f'/all {Prefix} vote disagree')
        )
        print_msg(source, msg)
    elif game_status == 'not_start':
        print_msg(source, RTextList(
            RText('§a开始游戏§r  ').h('点击进行游戏开始投票').c(
                RAction.run_command, f'/all {Prefix} vote start'),
            RText('§2切换队伍§r  ').h('点击切换队伍').c(
                RAction.run_command, f'/all {Prefix} team'),
            RText('§e游戏设定§r').h('点击修改游戏设定').c(
                RAction.run_command, f'/all {Prefix} config')
        ))
    elif game_status == 'to_be_start':
        print_msg(source, '游戏马上开始，请做好准备')
    elif game_status == 'started':
        print_msg(source,
                  RTextList(
                      RText('bingo？  ').h('检查bingo卡片').c(
                          RAction.run_command, f'/bingo'),
                      RText('获取卡片  ').h('获得一张新的bingo卡片').c(
                          RAction.run_command, f'/card'),
                      RText('分享坐标  ').h('向同队伍成员发送坐标').c(
                          RAction.suggest_command, f'/coords 可选注释'),
                      RText('公屏消息 ').h('发送一条所有人可见的消息').c(
                          RAction.suggest_command, f'/all消息'),
                      RText('§c结束游戏§r').h('点击进行结束游戏的投票').c(
                          RAction.run_command, f'/all {Prefix} vote end')
                  ))
    else:
        print_msg(source, RText('§c重启游戏§r').h('进行重置游戏的投票').c(
            RAction.run_command, f'/all {Prefix} vote restart'))


def print_config_edit(source: PlayerCommandSource):
    global voting_lock, bingo_players, pvp, timer, timer_len, wincondition
    msg = ''
    if not source.player in bingo_players:
        msg = '您未加入队伍，无法更改配置\n'
        msg += print_team_msg()
    elif voting_lock.locked():
        msg = '§c无法修改游戏配置，请先完成投票：§r\n'
        msg += vote_title+'\n'
        msg += RTextList(
            RText('§6◤§a点击同意§6◢§r').c(RAction.run_command,
                                      f'/all {Prefix} vote agree'),
            RText('    '),
            RText('§6◤§c点击反对§6◢§r').c(RAction.run_command,
                                      f'/all {Prefix} vote disagree')
        )
    elif game_status != 'not_start':
        msg = '§c只有游戏未开始时可以修改游戏配置！§r'
    else:
        msg = RTextList(
            RText(' '),
            RText(f'§{"a" if pvp == 1 else "c"}pvp§r')
            .h(f'{"§a打开" if pvp == -1 else "§c关闭"}§rpvp模式')
            .c(RAction.run_command, f'/all {Prefix} pvp'),
            RText('  '),
            RText(f'§{"a" if timer == 1 else "c"}限时模式§r')
            .h(f'{"§a打开" if timer == -1 else "§c关闭"}§r限时模式')
            .c(RAction.run_command, f'/all {Prefix} timer'),
            RText('  '),
            RText('限时时长')
            .h(f'当前 {timer_len}min, 点击切换')
            .c(RAction.suggest_command, f'/all {Prefix} timer 30'),
            RText('\n  '),
            RText('胜利条件')
            .h(f'选择胜利所需要的连线数量, 当前为 {wincondition} 条')
            .c(RAction.suggest_command, f'/all {Prefix} wincondition 1'),
            RText('    '),
            RText('物品稀有度')
            .h('物品的稀有度分布，要求S+A+B+C+D = 25')
            .c(RAction.suggest_command, f'/all {Prefix} card 2,6,9,6,2')
        )
    print_msg(source, msg, prefix='')


def print_unknown_argument_message(source: CommandSource, error: UnknownArgument):
    print_msg(source, RText('参数错误！请输入§7{}§r以获取插件信息'.format(
        Prefix)).h('点击查看帮助').c(RAction.run_command, Prefix))


def register_command(server: ServerInterface):
    server.register_command(
        Literal(Prefix).
        runs(lambda src: print_msg(src, bingo_msg, False, '')).
        on_error(UnknownArgument, print_unknown_argument_message, handled=True).
        then(
            Literal('team').
            runs(lambda src: print_team_msg(src)).
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
                Literal('agree').runs(lambda src: agree_vote(src))
            ).
            then(
                Literal('disagree').runs(lambda src: disagree_vote(src))
            )
        ).
        then(
            Literal('config').runs(print_config_edit)
        ).
        then(
            Literal('pvp').runs(lambda src: set_pvp(src))
        ).
        then(
            Literal('timer').runs(lambda src: set_timer(src)).
            then(
                Integer('length').runs(
                    lambda src, ctx: set_timer_len(src, ctx['length']))
            )
        ).
        then(
            Literal('card').
            then(
                GreedyText('s').runs(
                    lambda src, ctx: set_itemdistribution(src, ctx['s']))
            )
        ).
        then(
            Literal('wincondition').
            then(
                Integer('lines').runs(
                    lambda src, ctx: set_wincondition(src, ctx['lines']))
            )
        )
    )
    server.register_command(Literal('!!bg').runs(print_bingo_menu))


def on_player_joined(server: ServerInterface, player, info):
    server.tell(player, print_team_msg(None))


def on_load(server, old):
    register_command(server)
    server.register_help_message(Prefix, RText(
        'bingo游戏菜单').h('点击显示').c(RAction.run_command, Prefix))


def on_info(server, info):
    global game_status
    if info.is_user:
        pass
    elif re.fullmatch(r'BINGO                             Game has ended!', info.content):
        game_status = 'ended'
    elif re.fullmatch(r'BINGO                            Game has started!', info.content):
        game_status = 'started'
    elif not re.search(r'team has gotten bingo!', info.content) is None:
        game_status = 'ended'
    elif not re.search(r'Creating Game instance', info.content) is None:
        game_status = 'not_start'
    elif re.fullmatch(r'Closing Server', info.content):
        game_status = 'ended'
