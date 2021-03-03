import json
import os
import re
import shutil
import time
from threading import Lock
from typing import Optional
from mcdreforged.api.all import *

PLUGIN_ID = 'fas_bingo_manager'
PLUGIN_METADATA = {
    'id': PLUGIN_ID,
    'version': '1.0.1',
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
    'orange',
    'gray'
]
itemdistribution = {
    's': '10,4,4,4,3',
    'a': '8,5,4,4,4',
    'b': '5,5,5,5,5',
    'c': '4,4,4,5,8',
    'd': '3,4,4,4,10'
}
pvp = -1
card = 'c'
wincondition = 1
timer = 1
timer_len = '60'
game_status = 'not_start'
# not_start, to_be_start,started,ended
bingo_players = []
vote_agree = []
vote_disagree = []
voting = False
vote_info = ['当前无进行中的投票\n', '', '']


def print_message(source: CommandSource, msg, tell=True, prefix='[FAS-Bingo] '):
    msg = prefix + msg
    if source.is_player and not tell:
        source.get_server().say(msg)
    else:
        source.reply(msg)


def format_time(time_length):
    if time_length < 60:
        return '{}分钟'.format(time_length)
    elif time_length < 60 * 60:
        return '{}小时'.format(round(time_length / 60, 2))


def team_join(source: PlayerCommandSource, team=None):
    if game_status != 'not_start':
        source.reply('当前游戏状态下，无法加入队伍')
    elif team in teams:
        source.get_server().execute(
            f'team add {source.player} {team}')
        if not source.player in bingo_players:
            bingo_players.append(source.player)
    else:
        source.reply('无法加入该队伍，请检查队伍名称')


@new_thread
def vote(source: PlayerCommandSource, msg):
    global vote_agree, vote_disagree, vote_info, voting, bingo_players
    if voting:
        source.reply(vote_info)
    elif not source.player in bingo_players:
        print_message(source, RText('选择队伍 ').h('点击进行队伍选择,可选§cred§r|§9blue§r|§agreen§r|§eyellow§r|§dpink§r|§baqua§r|§6orange§r|§7gray§r').c(
            RAction.suggest_command, f'/all {Prefix} team 队伍颜色'), True)
    elif msg == 'restart':
        voting_restart(source)
    else:
        voting = True
        vote_agree.append(source.player)
        vote_info = []
        vote_info.append(f'{source.player} 发起了投票：{msg}  请在30s内表决\n')
        vote_info.append('')
        vote_info.append(
            RTextList(
                RText('点击同意    ').c(
                    RAction.run_command, f'/all {Prefix} vote agree'),
                RText('点击反对').c(RAction.run_command, f'/all {Prefix} vote disagree')
            )
        )
        reset_vote_info(source)
        print_vote_msg(source)
        vote_timer = 0
        while(voting):
            time.sleep(1)
            vote_timer += 1
            source.get_server().logger.info('')
            if len(vote_agree) >= len(bingo_players) / 2:
                source.get_server().execute(f'[Fas-Bingo] 投票进行中,剩余{30-vote_timer}s')
                print_message(
                    source, f'{source.player}发起的投票：{msg}已被超过半数玩家同意', False)
                break
            elif len(vote_disagree) >= len(bingo_players) / 2:
                print_message(
                    source, f'{source.player}发起的投票：{msg}已被超过半数玩家反对', False)
                break
            elif vote_timer >= 30 and len(vote_agree) >= len(vote_disagree):
                source.get_server().execute(msg)
                print_message(
                    source, f'{source.player}发起的投票：{msg}已超时，同意方胜利', False)
                break
            elif vote_timer >= 30 and len(vote_disagree) > len(vote_agree):
                print_message(
                    source, f'{source.player}发起的投票：{msg}已超时，反对方胜利', False)
                break
            else:
                pass
        voting = False
        reset_vote_info(source)
        vote_agree = []
        vote_disagree = []


@new_thread
def voting_restart(source: PlayerCommandSource):
    global game_status, vote_agree, vote_disagree, server_path
    if game_status in ['started', 'to_be_start']:
        source.reply('正在游戏中，请先投票结束游戏')
    else:
        voting = True
        vote_agree.append(source.player)
        vote_info = []
        vote_info.append(f'{source.player} 发起了投票：重置游戏 请在30s内表决\n')
        vote_info.append('')
        vote_info.append(
            RTextList(
                RText('点击同意    ').c(
                    RAction.run_command, f'/all {Prefix} vote agree'),
                RText('点击反对').c(RAction.run_command, f'/all {Prefix} vote disagree')
            )
        )
        reset_vote_info(source)
        vote_timer = 0
        print_vote_msg(source)
        while(voting):
            time.sleep(0.5)
            vote_timer += 1
            if len(vote_agree) >= len(bingo_players) / 2:
                print_message(
                    source, f'{source.player}发起的投票: 重置游戏 已被超过半数玩家同意', False)
                restart_game(source, server_path)
                break
            elif len(vote_disagree) >= len(bingo_players) / 2:
                print_message(
                    source, f'{source.player}发起的投票: 重置游戏 已被超过半数玩家反对', False)
                break
            elif vote_timer >= 60 and len(vote_agree) >= len(vote_disagree):
                print_message(
                    source, f'{source.player}发起的投票: 重置游戏 已超时，同意方胜利', False)
                restart_game(source, server_path)
                break
            elif vote_timer >= 60 and len(vote_disagree) > len(vote_agree):
                print_message(
                    source, f'{source.player}发起的投票: 重置游戏 已超时，反对方胜利', False)
                break
            else:
                pass
        voting = False
        reset_vote_info(source)
        vote_agree = []
        vote_disagree = []


def reset_vote_info(source: CommandSource):
    global vote_info, voting
    if voting:
        vote_info[1] = f'{len(vote_agree)}人赞同：'
        for i in vote_agree:
            vote_info[1] += i + ' '
        vote_info[1] += '\n{len(vote_disagree)}人反对：'
        for i in vote_disagree:
            vote_info[1] += i + ' '
        vote_info[1] += '\n'
    else:
        vote_info = ['当前无进行中的投票\n', '', '']


def agree_vote(source: PlayerCommandSource):
    global vote_agree, voting, bingo_players
    if not source.player in bingo_players:
        print_message(source, '请先加入队伍', True)
    elif not voting:
        print_message(source, '没有进行中的投票', True)
    elif source.player in vote_disagree or source.player in vote_agree:
        print_message(source, '你已经投过票了')
    else:
        vote_agree.append(source.player)
        print_message(source, f'{source.player}投出同意票', False)
        reset_vote_info(source)


def disagree_vote(source: PlayerCommandSource):
    global vote_disagree, voting, bingo_players
    if not source.player in bingo_players:
        print_message(source, '请先加入队伍', True)
    elif not voting:
        print_message(source, '没有进行中的投票', True)
    elif source.player in vote_disagree or source.player in vote_agree:
        print_message(source, '你已经投过票了')
    else:
        vote_disagree.append(source.player)
        print_message(source, f'{source.player}投出了反对票', False)
        reset_vote_info(source)


def print_vote_msg(source: CommandSource):
    msg = ''
    for i in vote_info:
        msg += i
    print_message(source, i, False)


def start_game(source: CommandSource):
    for countdown in range(1, 5):
        print_message(source, f'{5 - countdown}秒后开始游戏，请做好准备！', tell=False)
        time.sleep(1)
    source.get_server().execute('start')


def restart_game(source: CommandSource, folder):
    def mkdir(path):
        if not os.path.exists(path):
            os.mkdir(path)
    for countdown in range(1, 10):
        print_message(source, f'{10 - countdown}s后重启服务器', False)
        time.sleep(1)
    bingo_players = []
    game_status = 'not_start'
    source.get_server().stop()
    source.get_server().wait_for_start()

    for world in world_names:
        shutil.rmtree(os.path.realpath(os.path.join(folder, world)))

    mkdir(os.path.join(server_path, 'world'))
    shutil.copytree(os.path.join(server_path, 'datapacks'),
                    os.path.realpath(os.path.join(server_path, 'world', 'datapacks')))
    source.get_server().start()


def set_pvp(source: CommandSource):
    global pvp
    source.get_server().execute('pvp')
    pvp *= -1


def set_timer_len(source: CommandSource, length: int):
    source.get_server().execute('timer {}'.format(length * 60))
    timer_len = length
    print_message(source, f'当前的时间限制为 {format_time(length)}', False)


def set_timer(source: CommandSource):
    global timer
    command_line = 'timer '
    command_line += 'enable' if timer == -1 else 'disable'
    timer *= -1
    source.get_server().execute(command_line)
    print_message(source, f'限时模式已{"关闭" if timer == -1 else "打开"}', False)


def set_itemdistribution(source: CommandSource, s: str):
    global itemdistribution, card
    if s in ['s', 'a', 'b', 'c', 'd']:
        source.get_server().execute(f'itemdistribution {itemdistribution[s]}')
        print_message(source, f'当前物品稀有度为{s}: {itemdistribution[s]}', False)
        card = s
    else:
        source.reply('参数错误！物品稀有度应为s、a、b、c、d之一')


def set_wincondition(source: CommandSource, line: Integer):
    global wincondition
    if line <= 10 and line >= 1:
        source.get_server().execute(f'wincondition {line}')
        print_message(source, f'当前胜利条件为完成{line}条线', False)
        wincondition = line
    else:
        source.reply('参数错误：胜利条件应该为1-10的整数！')


def print_bingo_menu(source: PlayerCommandSource):
    global game_status, bingo_players, voting, vote_info
    msg = ''
    if not source.player in bingo_players:
        msg += f'你还未选择队伍：'
        msg += RText('选择队伍 ').h('点击进行队伍选择,可选§cred§r | §9blue§r | §agreen§r | §eyellow§r | §dpink§r | §baqua§r | §6orange§r | §7gray§r').c(
            RAction.suggest_command, f'{Prefix} team 队伍颜色')
    elif voting:
        msg += vote_info
    elif game_status == 'not_start':
        msg = RTextList(
            RText('开始游戏  ').h('点击进行游戏开始投票').c(
                RAction.run_command, f'/all {Prefix} vote start'),
            RText('切换队伍  ').h('点击进行队伍选择,可选§cred§r|§9blue§r|§agreen§r|§eyellow§r|§dpink§r|§baqua§r|§6orange§r|§7gray§r').c(
                RAction.suggest_command, f'/all {Prefix} team 队伍颜色'),
            RText('游戏设定').h('点击修改游戏设定').c(
                RAction.run_command, f'/all {Prefix} config')
        )
    elif game_status == 'to_be_start':
        msg += '游戏马上开始，请做好准备'
    elif game_status == 'started':
        msg += RTextList(
            RText('bingo？  ').h('检查bingo卡片').c(RAction.run_command, f'/bingo'),
            RText('获取卡片  ').h('获得一张新的bingo卡片').c(
                RAction.run_command, f'/card'),
            RText('分享坐标  ').h('向同队伍成员发送坐标').c(
                RAction.suggest_command, f'/coords 可选注释'),
            RText('公屏消息 ').h('发送一条所有人可见的消息').c(
                RAction.suggest_command, f'/all 消息'),
            RText('结束游戏').h('点击进行结束游戏的投票').c(
                RAction.run_command, f'/all {Prefix} vote end')
        )
    else:
        msg += RText('重启游戏').h('进行重置游戏的投票').c(RAction.run_command,
                                              f'/all {Prefix} vote restart')
    print_message(source, msg)


def print_config_edit(source: PlayerCommandSource):
    msg = ''
    if not source.player in bingo_players:
        msg += '您未加入队伍，无法更改配置'
    elif voting:
        msg += '无法修改游戏配置，请先完成投票：\n'+vote.status()
    elif game_status != 'not_start':
        msg += '只有游戏未开始时可以修改游戏配置！'
    else:
        msg += RText('pvp    ').h('开/关 pvp').c(RAction.run_command,
                                               f'/all {Prefix} pvp')
        msg += RText('限时模式    ').h('开/关 限时模式').c(RAction.run_command,
                                                 f'/all {Prefix} timer')
        msg += RText('限时模式时长    ').h('单位：分钟').c(RAction.suggest_command,
                                                f'/all {Prefix} timer 时长')
        msg += RText('胜利条件    ').h('选择胜利所需要的连线数量').c(RAction.suggest_command,
                                                     f'/all {Prefix} wincondition 连线数量')
        msg += RText('物品稀有度    ').h('更改bingo卡片上物品的稀有度分布，可选 s a b c d').c(
            RAction.suggest_command, f'/all {Prefix} card 稀有度')
    print_message(source, msg)


def print_unknown_argument_message(source: CommandSource, error: UnknownArgument):
    print_message(source, RText('参数错误！请输入§7{}§r以获取插件信息'.format(
        Prefix)).h('点击查看帮助').c(RAction.run_command, Prefix))


def register_command(server: ServerInterface):
    global card, itemdistribution
    server.register_command(
        Literal(Prefix).
        runs(print_bingo_menu).
        on_error(UnknownArgument, print_unknown_argument_message, handled=True).
        then(
            Literal('team').
            then(GreedyText('color').runs(
                lambda src, ctx: team_join(src, ctx['color'])))
        ).
        then(
            Literal('vote').runs(lambda src: print_message(src, vote_info[0]+vote_info[1]+vote_info[2], True)).
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
            Literal('card').runs(lambda src: print_message(src, f'当前物品稀有度为{card}: {itemdistribution[card]}', False)).
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


def on_load(server: ServerInterface, old):
    register_command(server)
    server.register_help_message(Prefix, RText(
        'bingo游戏菜单').h('点击显示').c(RAction.run_command, Prefix))


def on_info(server, info):  # 检测bingo游戏结束
    global game_status
    if not info.is_user and re.fullmatch(r'BINGO                             Game has ended!', info.content):
        game_status = 'ended'
    if not info.is_user and re.fullmatch(r'BINGO                            Game has started!', info.content):
        game_status = 'started'
