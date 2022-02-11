import json
import random
import threading
import time

import arrow
import socketio
import tenacity

from lokbot.client import LokBotApi
from lokbot import logger, builtin_logger, project_root

# 资源 code
from lokbot.exceptions import OtherException

# 刚进游戏
TUTORIAL_CODE_INTRO = 'Intro'
# 完成改名字主线后, 弹出 "学徒的板条箱 $0.99" 购买按钮
TUTORIAL_CODE_START = 'TutorialStart'

# 任务状态
STATUS_PENDING = 1  # 未完成任务
STATUS_FINISHED = 2  # 已完成待领取奖励
STATUS_CLAIMED = 3  # 已领取奖励

# 任务类型 code
TASK_CODE_SILVER_HAMMER = 1  # 免费建筑工
TASK_CODE_GOLD_HAMMER = 8  # 黄金建筑工
TASK_CODE_CAMP = 3  # 军营
TASK_CODE_ACADEMY = 6  # 学院

BUILDING_STATE_NORMAL = 1  # 正常
BUILDING_STATE_UPGRADING = 2  # 升级中

BUILDING_POSITION_MAP = {
    'academy': 5,
    'castle': 1,
    'hall_of_alliance': 7,
    'hospital': 6,
    'storage': 2,
    'trading_post': 9,
    'treasure_house': 4,
    'wall': 8,
    'watch_tower': 3,
}

BUILDING_CODE_MAP = {
    'academy': 40100105,
    'barrack': 40100201,
    'castle': 40100101,
    'farm': 40100202,
    'gold_mine': 40100205,
    'hall_of_alliance': 40100107,
    'hospital': 40100106,
    'lumber_camp': 40100203,
    'quarry': 40100204,
    'storage': 40100102,
    'trading_post': 40100109,
    'treasure_house': 40100104,
    'wall': 40100108,
    'watch_tower': 40100103,
}

# 可收获的资源
HARVESTABLE_CODE = [
    BUILDING_CODE_MAP['farm'],
    BUILDING_CODE_MAP['lumber_camp'],
    BUILDING_CODE_MAP['quarry'],
    BUILDING_CODE_MAP['gold_mine']
]

ITEM_CODE_FOOD_1K = 10101013
ITEM_CODE_FOOD_5K = 10101014
ITEM_CODE_FOOD_10K = 10101015
ITEM_CODE_FOOD_50K = 10101016
ITEM_CODE_FOOD_100K = 10101017
ITEM_CODE_FOOD_500K = 10101018
ITEM_CODE_FOOD_1M = 10101019

ITEM_CODE_LUMBER_1K = 10101022
ITEM_CODE_LUMBER_5K = 10101023
ITEM_CODE_LUMBER_10K = 10101024
ITEM_CODE_LUMBER_50K = 10101025
ITEM_CODE_LUMBER_100K = 10101026
ITEM_CODE_LUMBER_500K = 10101027
ITEM_CODE_LUMBER_1M = 10101028

ITEM_CODE_STONE_1K = 10101031
ITEM_CODE_STONE_5K = 10101032
ITEM_CODE_STONE_10K = 10101033
ITEM_CODE_STONE_50K = 10101034
ITEM_CODE_STONE_100K = 10101035
ITEM_CODE_STONE_500K = 10101036
ITEM_CODE_STONE_1M = 10101037

ITEM_CODE_GOLD_1K = 10101040
ITEM_CODE_GOLD_5K = 10101041
ITEM_CODE_GOLD_10K = 10101042
ITEM_CODE_GOLD_50K = 10101043
ITEM_CODE_GOLD_100K = 10101044
ITEM_CODE_GOLD_500K = 10101045
ITEM_CODE_GOLD_1M = 10101046

USABLE_ITEM_CODE_LIST = (
    ITEM_CODE_FOOD_1K, ITEM_CODE_FOOD_5K, ITEM_CODE_FOOD_10K, ITEM_CODE_FOOD_50K, ITEM_CODE_FOOD_100K,

    ITEM_CODE_LUMBER_1K, ITEM_CODE_LUMBER_5K, ITEM_CODE_LUMBER_10K, ITEM_CODE_LUMBER_50K, ITEM_CODE_LUMBER_100K,

    ITEM_CODE_STONE_1K, ITEM_CODE_STONE_5K, ITEM_CODE_STONE_10K, ITEM_CODE_STONE_50K, ITEM_CODE_STONE_100K,

    ITEM_CODE_GOLD_1K, ITEM_CODE_GOLD_5K, ITEM_CODE_GOLD_10K, ITEM_CODE_GOLD_50K, ITEM_CODE_GOLD_100K,
)

RESEARCH_CODE_MAP = {
    # 生产优先
    'production': {
        'food_production': 30102001,
        'wood_production': 30102002,
        'stone_production': 30102003,
        'gold_production': 30102004,
        'food_capacity': 30102005,
        'wood_capacity': 30102006,
        'stone_capacity': 30102007,
        'gold_capacity': 30102008,
        'food_gathering_speed': 30102009,
        'wood_gathering_speed': 30102010,
        'stone_gathering_speed': 30102011,
        'gold_gathering_speed': 30102012,
        'crystal_gathering_speed': 30102013,
        'infantry_storage': 30102014,
        'ranged_storage': 30102015,
        'cavalry_storage': 30102016,
        'research_speed': 30102017,
        'construction_speed': 30102018,
        'resource_protect': 30102019,
        'advanced_food_production': 30102020,
        'advanced_wood_production': 30102021,
        'advanced_stone_production': 30102022,
        'advanced_gold_production': 30102023,
        'advanced_food_capacity': 30102024,
        'advanced_wood_capacity': 30102025,
        'advanced_stone_capacity': 30102026,
        'advanced_gold_capacity': 30102027,
        'advanced_research_speed': 30102028,
        'advanced_construction_speed': 30102029,
        'advanced_food_gathering_speed': 30102030,
        'advanced_wood_gathering_speed': 30102031,
        'advanced_stone_gathering_speed': 30102032,
        'advanced_gold_gathering_speed': 30102033,
        'advanced_crystal_gathering_speed': 30102034,
    },
    # 训练其次
    'battle': {
        'infantry_hp': 30101001,
        'ranged_hp': 30101002,
        'cavalry_hp': 30101003,
        'infantry_def': 30101004,
        'ranged_def': 30101005,
        'cavalry_def': 30101006,
        'infantry_atk': 30101007,
        'ranged_atk': 30101008,
        'cavalry_atk': 30101009,
        'infantry_spd': 30101010,
        'ranged_spd': 30101011,
        'cavalry_spd': 30101012,
        'troops_storage': 30101013,
        'warrior': 30101014,
        'longbow_man': 30101015,
        'horseman': 30101016,
        'infantry_training_amount': 30101017,
        'ranged_training_amount': 30101018,
        'cavalry_training_amount': 30101019,
        'infantry_training_speed': 30101020,
        'ranged_training_speed': 30101021,
        'cavalry_training_speed': 30101022,
        'infantry_training_cost': 30101023,
        'ranged_training_cost': 30101024,
        'cavalry_training_cost': 30101025,
        'march_size': 30101026,
        'march_limit': 30101027,
        'knight': 30101028,
        'ranger': 30101029,
        'heavy_cavalry': 30101030,
        'troops_spd': 30101031,
        'troops_hp': 30101032,
        'troops_def': 30101033,
        'troops_atk': 30101034,
        'hospital_capacity': 30101035,
        'healing_time_reduced': 30101036,
        'guardian': 30101037,
        'crossbow_man': 30101038,
        'iron_cavalry': 30101039,
        'rally_attack_amount': 30101040,
        'advanced_infantry_hp': 30101041,
        'advanced_ranged_hp': 30101042,
        'advanced_cavalry_hp': 30101043,
        'advanced_infantry_def': 30101044,
        'advanced_ranged_def': 30101045,
        'advanced_cavalry_def': 30101046,
        'advanced_infantry_atk': 30101047,
        'advanced_ranged_atk': 30101048,
        'advanced_cavalry_atk': 30101049,
        'advanced_infantry_spd': 30101050,
        'advanced_ranged_spd': 30101051,
        'advanced_cavalry_spd': 30101052,
        'crusader': 30101053,
        'sniper': 30101054,
        'dragoon': 30101055,
    },
    'advanced': {
        'resource_production': 30103001,
        'infantry_hp_against_archer': 30103002,
        'infantry_def_against_archer': 30103003,
        'infantry_atk_against_archer': 30103004,
        'archer_hp_against_cavalry': 30103005,
        'archer_def_against_cavalry': 30103006,
        'archer_atk_against_cavalry': 30103007,
        'cavalry_hp_against_infantry': 30103008,
        'cavalry_def_against_infantry': 30103009,
        'cavalry_atk_against_infantry': 30103010,
        'resource_capacity': 30103011,
        'castle_defending_infantrys_hp': 30103012,
        'castle_defending_infantrys_def': 30103013,
        'castle_defending_infantrys_atk': 30103014,
        'castle_defending_archers_hp': 30103015,
        'castle_defending_archers_def': 30103016,
        'castle_defending_archers_atk': 30103017,
        'castle_defending_cavalrys_hp': 30103018,
        'castle_defending_cavalrys_def': 30103019,
        'castle_defending_cavalrys_atk': 30103020,
        'resource_protect': 30103021,
        'infantrys_hp_when_composed_of_infantry_only': 30103022,
        'infantrys_def_when_composed_of_infantry_only': 30103023,
        'infantrys_atk_when_composed_of_infantry_only': 30103024,
        'archers_hp_when_composed_of_archer_only': 30103025,
        'archers_def_when_composed_of_archer_only': 30103026,
        'archers_atk_when_composed_of_archer_only': 30103027,
        'cavalrys_hp_when_composed_of_cavalry_only': 30103028,
        'cavalrys_def_when_composed_of_cavalry_only': 30103029,
        'cavalrys_atk_when_composed_of_cavalry_only': 30103030,
        'troop_speed_when_participating_a_rally': 30103031,
        'infantrys_hp_when_participating_a_rally': 30103032,
        'infantrys_def_when_participating_a_rally': 30103033,
        'infantrys_atk_when_participating_a_rally': 30103034,
        'archers_hp_when_participating_a_rally': 30103035,
        'archers_def_when_participating_a_rally': 30103036,
        'archers_atk_when_participating_a_rally': 30103037,
        'cavalrys_hp_when_participating_a_rally': 30103038,
        'cavalrys_def_when_participating_a_rally': 30103039,
        'cavalrys_atk_when_participating_a_rally': 30103040,
    },
}

RESEARCH_MINIMUM_LEVEL_MAP = {
    'production': {
        "food_production": 2,
        "wood_production": 2,
        "stone_production": 2,
        "gold_production": 2,
        "food_capacity": 2,
        "wood_capacity": 2,
        "stone_capacity": 2,
        "gold_capacity": 2,
        "food_gathering_speed": 2,
        "wood_gathering_speed": 2,
        "stone_gathering_speed": 2,
        "gold_gathering_speed": 2,
        "crystal_gathering_speed": 2,
        "infantry_storage": 2,
        "ranged_storage": 2,
        "cavalry_storage": 2,
        "research_speed": 2,
        "construction_speed": 2,
        "resource_protect": 2,
        "advanced_food_production": 3,
        "advanced_wood_production": 3,
        "advanced_stone_production": 3,
        "advanced_gold_production": 3,
        "advanced_food_capacity": 3,
        "advanced_wood_capacity": 3,
        "advanced_stone_capacity": 3,
        "advanced_gold_capacity": 3,
        "advanced_research_speed": 3,
        "advanced_construction_speed": 3,
        "advanced_food_gathering_speed": 3,
        "advanced_wood_gathering_speed": 3,
        "advanced_stone_gathering_speed": 3,
        "advanced_gold_gathering_speed": 3
    },
    'battle': {
        "infantry_hp": 2,
        "ranged_hp": 2,
        "cavalry_hp": 2,
        "infantry_def": 2,
        "ranged_def": 2,
        "cavalry_def": 2,
        "infantry_atk": 2,
        "ranged_atk": 2,
        "cavalry_atk": 2,
        "infantry_spd": 2,
        "ranged_spd": 2,
        "cavalry_spd": 2,
        "troops_storage": 3,
        "warrior": 1,
        "longbow_man": 1,
        "horseman": 1,
        "infantry_training_amount": 2,
        "ranged_training_amount": 2,
        "cavalry_training_amount": 2,
        "infantry_training_speed": 2,
        "ranged_training_speed": 2,
        "cavalry_training_speed": 2,
        "infantry_training_cost": 3,
        "ranged_training_cost": 3,
        "cavalry_training_cost": 3,
        "march_size": 2,
        "march_limit": 1,
        "knight": 1,
        "ranger": 1,
        "heavy_cavalry": 1,
        "troops_spd": 3,
        "troops_hp": 3,
        "troops_def": 3,
        "troops_atk": 3,
        "hospital_capacity": 3,
        "healing_time_reduced": 3,
        "guardian": 1,
        "crossbow_man": 1,
        "iron_cavalry": 1,
        "rally_attack_amount": 5,
        "advanced_infantry_hp": 5,
        "advanced_ranged_hp": 5,
        "advanced_cavalry_hp": 5,
        "advanced_infantry_def": 5,
        "advanced_ranged_def": 5,
        "advanced_cavalry_def": 5,
        "advanced_infantry_atk": 5,
        "advanced_ranged_atk": 5,
        "advanced_cavalry_atk": 5,
        "advanced_infantry_spd": 5,
        "advanced_ranged_spd": 5,
        "advanced_cavalry_spd": 5
    },
    'advanced': {
        "resource_production": 3,
        "infantry_hp_against_archer": 3,
        "infantry_def_against_archer": 3,
        "archer_hp_against_cavalry": 3,
        "archer_def_against_cavalry": 3,
        "cavalry_hp_against_infantry": 3,
        "cavalry_def_against_infantry": 3,
        "infantry_atk_against_archer": 3,
        "archer_atk_against_cavalry": 3,
        "cavalry_atk_against_infantry": 3,
        "resource_capacity": 3,
        "castle_defending_infantrys_hp": 3,
        "castle_defending_infantrys_def": 3,
        "castle_defending_archers_hp": 3,
        "castle_defending_archers_def": 3,
        "castle_defending_cavalrys_hp": 3,
        "castle_defending_cavalrys_def": 3,
        "castle_defending_infantrys_atk": 3,
        "castle_defending_archers_atk": 3,
        "castle_defending_cavalrys_atk": 3,
        "resource_protect": 3,
        "infantrys_hp_when_composed_of_infantry_only": 3,
        "infantrys_def_when_composed_of_infantry_only": 3,
        "archers_hp_when_composed_of_archer_only": 3,
        "archers_def_when_composed_of_archer_only": 3,
        "cavalrys_hp_when_composed_of_cavalry_only": 3,
        "cavalrys_def_when_composed_of_cavalry_only": 3,
        "infantrys_atk_when_composed_of_infantry_only": 3,
        "archers_atk_when_composed_of_archer_only": 3,
        "cavalrys_atk_when_composed_of_cavalry_only": 3,
        "troop_speed_when_participating_a_rally": 3,
        "infantrys_hp_when_participating_a_rally": 3,
        "infantrys_def_when_participating_a_rally": 3,
        "archers_hp_when_participating_a_rally": 3,
        "archers_def_when_participating_a_rally": 3,
        "cavalrys_hp_when_participating_a_rally": 3,
        "cavalrys_def_when_participating_a_rally": 3
    }
}

RESOURCE_IDX_MAP = {
    'food': 0,
    'lumber': 1,
    'stone': 2,
    'gold': 3,
}


def load_building_json():
    result = {}

    for building_type, building_code in BUILDING_CODE_MAP.items():
        current_building_json = json.load(open(project_root.joinpath(f'lokbot/assets/buildings/{building_type}.json')))
        result[building_code] = current_building_json

    return result


def load_research_json():
    result = {}

    for research_category, research in RESEARCH_CODE_MAP.items():
        current_research_json = json.load(
            open(project_root.joinpath(f'lokbot/assets/research/{research_category}.json'))
        )
        for research_name, research_code in research.items():
            result[research_code] = current_research_json[research_name]

    return result


building_json = load_building_json()
research_json = load_research_json()


class LokFarmer:
    def __init__(self, access_token, captcha_solver_config):
        self.access_token = access_token
        self.api = LokBotApi(access_token, captcha_solver_config, self._request_callback)
        self.kingdom_enter = self.api.kingdom_enter()
        # [food, lumber, stone, gold]
        self.resources = self.kingdom_enter.get('kingdom').get('resources')

    @staticmethod
    def calc_time_diff_in_seconds(expected_ended):
        time_diff = arrow.get(expected_ended) - arrow.utcnow()

        return time_diff.seconds + random.randint(10, 20)

    def _is_building_upgradeable(self, building, buildings):
        if building.get('state') != BUILDING_STATE_NORMAL:
            return False

        # 暂时忽略联盟中心
        if building.get('code') == BUILDING_CODE_MAP['hall_of_alliance']:
            return False

        building_level = building.get('level')
        current_building_json = building_json.get(building.get('code'))

        if not current_building_json:
            return False

        next_level_building_json = current_building_json.get(str(building_level + 1))
        for requirement in next_level_building_json.get('requirements'):
            req_level = requirement.get('level')
            req_type = requirement.get('type')
            req_code = BUILDING_CODE_MAP.get(req_type)

            if not [b for b in buildings if b.get('code') == req_code and b.get('level') >= req_level]:
                return False

        for res_requirement in next_level_building_json.get('resources'):
            req_value = res_requirement.get('value')
            req_type = res_requirement.get('type')

            if self.resources[RESOURCE_IDX_MAP[req_type]] < req_value:
                return False

        return True

    def _is_researchable(self, academy_level, category_name, research_name, exist_researches, to_max_level=False):
        research_category = RESEARCH_CODE_MAP.get(category_name)
        research_code = research_category.get(research_name)

        exist_research = [each for each in exist_researches if each.get('code') == research_code]
        current_research_json = research_json.get(research_code)

        # already finished
        if exist_research and exist_research[0].get('level') >= int(current_research_json[-1].get('level')):
            return False

        # minimum required level only
        if not to_max_level and \
                exist_research and \
                exist_research[0].get('level') >= RESEARCH_MINIMUM_LEVEL_MAP.get(category_name).get(research_name, 0):
            return False

        next_level_research_json = current_research_json[0]
        if exist_research:
            next_level_research_json = current_research_json[exist_research[0].get('level')]

        for requirement in next_level_research_json.get('requirements'):
            req_level = int(requirement.get('level'))
            req_type = requirement.get('type')

            # 判断学院等级
            if req_type == 'academy' and req_level > academy_level:
                return False

            # 判断前置研究是否完成
            if req_type != 'academy' and not [each for each in exist_researches if
                                              each.get('code') == research_category.get(req_type)
                                              and each.get('level') >= req_level]:
                return False

        for res_requirement in next_level_research_json.get('resources'):
            req_value = int(res_requirement.get('value'))
            req_type = res_requirement.get('type')

            if self.resources[RESOURCE_IDX_MAP[req_type]] < req_value:
                return False

        return True

    def _update_building(self, building):
        buildings = self.kingdom_enter.get('kingdom', {}).get('buildings', [])

        self.kingdom_enter['kingdom']['buildings'] = [
                                                         b for b in buildings if
                                                         b.get('position') != building.get('position')
                                                     ] + [building]

    def _request_callback(self, json_response):
        resources = json_response.get('resources')

        if resources and len(resources) == 4:
            logger.info(f'resources updated: {resources}')
            self.resources = resources

    @tenacity.retry(
        stop=tenacity.stop_after_attempt(4),
        wait=tenacity.wait_random_exponential(multiplier=1, max=60),
        reraise=True
    )
    def sock_thread(self, url='https://sock-lok-live.leagueofkingdoms.com/socket.io/'):
        """
        websocket connection of the kingdom
        :return:
        """
        sio = socketio.Client(reconnection=False, logger=builtin_logger, engineio_logger=builtin_logger)

        @sio.on('/building/update')
        def on_building_update(data):
            logger.info(f'on_building_update: {data}')
            self._update_building(data)

            return

        @sio.on('/resource/upgrade')
        def on_resource_update(data):
            logger.info(f'on_resource_update: {data}')
            self.resources[data.get('resourceIdx')] = data.get('value')

        sio.connect(url, transports=["websocket"])

        sio.emit('/kingdom/enter', {'token': self.access_token})

        sio.wait()

    def socf_thread(self):
        """
        websocket connection of the field
        :return:
        """
        pass

    def alliance_helper(self):
        """
        帮助联盟
        :return:
        """
        try:
            self.api.alliance_help_all()
        except OtherException:
            pass

    def harvester(self):
        """
        收获资源
        :return:
        """
        buildings = self.kingdom_enter.get('kingdom', {}).get('buildings', [])

        random.shuffle(buildings)

        harvested_code = set()
        for building in buildings:
            code = building.get('code')
            position = building.get('position')

            if code not in HARVESTABLE_CODE:
                continue

            # 每个种类只需要收获一次, 就会自动收获整个种类下所有资源
            if code in harvested_code:
                continue

            harvested_code.add(code)

            self.api.kingdom_resource_harvest(position)

    def quest_monitor(self):
        """
        任务监控
        :return:
        """
        quest_list = self.api.quest_list()

        # main quest(currently only one)
        [self.api.quest_claim(q) for q in quest_list.get('mainQuests') if q.get('status') == STATUS_FINISHED]

        # side quest(max 5)
        if len([self.api.quest_claim(q) for q in quest_list.get('sideQuests') if
                q.get('status') == STATUS_FINISHED]) >= 5:
            # 若五个均为已完成, 则翻页
            threading.Thread(target=self.quest_monitor).start()
            return

        quest_list_daily = self.api.quest_list_daily().get('dailyQuest')

        # daily quest(max 5)
        if len([self.api.quest_claim_daily(q) for q in quest_list_daily.get('quests') if
                q.get('status') == STATUS_FINISHED]) >= 5:
            # 若五个均为已完成, 则翻页
            threading.Thread(target=self.quest_monitor).start()
            return

        # daily quest reward
        [self.api.quest_claim_daily_level(q) for q in quest_list_daily.get('rewards') if
         q.get('status') == STATUS_FINISHED]

        logger.info('quest_monitor: done, sleep for 1h')
        threading.Timer(3600, self.quest_monitor).start()
        return

    def building_farmer(self, task_code=TASK_CODE_SILVER_HAMMER):
        """
        building farmer
        :param task_code:
        :return:
        """
        current_tasks = self.api.kingdom_task_all().get('kingdomTasks', [])

        worker_used = [t for t in current_tasks if t.get('code') == task_code]

        if worker_used:
            threading.Timer(
                self.calc_time_diff_in_seconds(worker_used[0].get('expectedEnded')),
                self.building_farmer,
                [task_code]
            ).start()
            return

        buildings = self.kingdom_enter.get('kingdom', {}).get('buildings', [])

        if not buildings:
            logger.warning('building_farmer: no building')
            return

        for building in buildings:
            if not self._is_building_upgradeable(building, buildings):
                continue

            try:
                res = self.api.kingdom_building_upgrade(building)
            except OtherException as error_code:
                if str(error_code) == 'full_task':
                    logger.warning('building_farmer: full_task, quit')
                    return

                logger.info(f'building upgrade failed, try next one, current: {building}')
                continue

            building['state'] = BUILDING_STATE_UPGRADING
            self._update_building(building)

            threading.Timer(
                self.calc_time_diff_in_seconds(res.get('newTask').get('expectedEnded')),
                self.building_farmer,
                [task_code]
            ).start()
            return

        logger.info('building_farmer: no building to upgrade, sleep for 2h')
        threading.Timer(2 * 3600, self.building_farmer, [task_code]).start()
        return

    def academy_farmer(self, to_max_level=False):
        """
        research farmer
        :param to_max_level:
        :return:
        """
        current_tasks = self.api.kingdom_task_all().get('kingdomTasks', [])

        worker_used = [t for t in current_tasks if t.get('code') == TASK_CODE_ACADEMY]

        if worker_used:
            if worker_used[0].get('status') != STATUS_CLAIMED:
                threading.Timer(
                    self.calc_time_diff_in_seconds(worker_used[0].get('expectedEnded')),
                    self.academy_farmer,
                    [to_max_level]
                ).start()
                return

            # 如果已完成, 则领取奖励并继续
            self.api.kingdom_task_claim(BUILDING_POSITION_MAP['academy'])

        exist_researches = self.api.kingdom_academy_research_list().get('researches', [])
        buildings = self.kingdom_enter.get('kingdom', {}).get('buildings', [])
        academy_level = [b for b in buildings if b.get('code') == BUILDING_CODE_MAP['academy']][0].get('level')

        for category_name, each_category in RESEARCH_CODE_MAP.items():
            logger.info(f'start researching category: {category_name}')
            for research_name, research_code in each_category.items():
                if not self._is_researchable(
                        academy_level, category_name, research_name, exist_researches, to_max_level
                ):
                    continue

                try:
                    res = self.api.kingdom_academy_research({'code': research_code})
                except OtherException as error_code:
                    if str(error_code) == 'not_enough_condition':
                        logger.warning(f'category {category_name} reached max level')
                        break

                    logger.info(f'research failed, try next one, current: {research_name}({research_code})')
                    continue

                threading.Timer(
                    self.calc_time_diff_in_seconds(res.get('newTask').get('expectedEnded')),
                    self.academy_farmer,
                    [to_max_level]
                ).start()
                return

        logger.info('academy_farmer: no research to do, sleep for 2h')
        threading.Timer(2 * 3600, self.academy_farmer, [to_max_level]).start()
        return

    def free_chest_farmer(self, _type=0):
        """
        领取免费宝箱
        :return:
        """
        try:
            res = self.api.item_free_chest(_type)
        except OtherException as error_code:
            if str(error_code) == 'free_chest_not_yet':
                logger.info('free_chest_farmer: free_chest_not_yet, sleep for 2h')
                threading.Timer(2 * 3600, self.free_chest_farmer).start()
                return

            raise

        next_gold = arrow.get(res.get('freeChest', {}).get('gold', {}).get('next'))
        next_silver = arrow.get(res.get('freeChest', {}).get('silver', {}).get('next'))

        if next_gold < next_silver:
            threading.Timer(self.calc_time_diff_in_seconds(next_gold), self.free_chest_farmer, [1]).start()
        else:
            threading.Timer(self.calc_time_diff_in_seconds(next_silver), self.free_chest_farmer, [0]).start()

    def use_resource_in_item_list(self):
        """

        :return:
        """
        item_list = self.api.item_list().get('items', [])

        if not item_list:
            return

        usable_item_list = filter(lambda x: x.get('code') in USABLE_ITEM_CODE_LIST, item_list)

        for each_item in usable_item_list:
            self.api.item_use(each_item.get('code'), each_item.get('amount'))
            time.sleep(random.randint(1, 3))

    def vip_chest_claim(self):
        """
        领取vip宝箱
        daily
        :return:
        """
        vip_info = self.api.kingdom_vip_info()

        if vip_info.get('vip', {}).get('isClaimed'):
            return

        self.api.kingdom_vip_claim()

    def alliance_farmer(self):
        try:
            research_list = self.api.alliance_research_list()
        except OtherException:
            return

        code = research_list.get('recommendResearch')

        if not code:
            code = 31101003  # 骑兵攻击力 1

        try:
            self.api.alliance_research_donate_all(code)
        except OtherException:
            pass
