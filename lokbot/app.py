import functools
import json
import os.path
import threading
import time

import schedule

from lokbot.farmer import LokFarmer
from lokbot import project_root


def find_alliance(farmer: LokFarmer):
    while True:
        alliance = farmer.api.alliance_recommend().get('alliance')

        if alliance.get('numMembers') < alliance.get('maxMembers'):
            farmer.api.alliance_join(alliance.get('_id'))
            break

        time.sleep(60 * 5)


def load_config():
    os.chdir(project_root)

    if os.path.exists('config.json'):
        return json.load(open('config.json'))

    if os.path.exists('config.example.json'):
        return json.load(open('config.example.json'))

    return {}


thread_map = {}


def run_threaded(name, job_func):
    if name in thread_map and thread_map[name].is_alive():
        return

    job_thread = threading.Thread(target=job_func, name=name)
    thread_map[name] = job_thread
    job_thread.start()


def main(token, captcha_solver_config=None):
    if captcha_solver_config is None:
        captcha_solver_config = {}

    config = load_config()

    farmer = LokFarmer(token, captcha_solver_config)
    farmer.keepalive_request()

    threading.Thread(target=farmer.sock_thread).start()
    # threading.Thread(target=farmer.socc_thread).start()

    # wait for the socket to be ready
    time.sleep(4)

    for job in config.get('main').get('jobs'):
        if not job.get('enabled'):
            continue

        name = job.get('name')

        schedule.every(
            job.get('interval').get('start')
        ).to(
            job.get('interval').get('end')
        ).minutes.do(run_threaded, name, functools.partial(getattr(farmer, name), **job.get('kwargs', {})))

    schedule.run_all()

    schedule.every(5).to(15).minutes.do(farmer.keepalive_request)

    for thread in config.get('main').get('threads'):
        if not thread.get('enabled'):
            continue

        threading.Thread(target=getattr(farmer, thread.get('name')), kwargs=thread.get('kwargs')).start()

    while True:
        schedule.run_pending()
        time.sleep(1)
