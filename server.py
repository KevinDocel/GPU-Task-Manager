from math import inf
import os
import time
import subprocess
import argparse
import datetime
import signal

import GPUtil
from pony import orm

from config import *
from constant import *

from database import get_database
from util import is_pid_alive, get_logger


class GPUManager(object):
    def __init__(self, logger):
        self.logger = logger

        self.all_gpus = self.__get_all_gpus()
        self.gpu_process = [None for _ in range(len(self.all_gpus))]

    def get_gpus(self, num_gpus, exclude_gpus, find_gpu_delay):
        gpu_ids = self.__find_avaiable_devices(num_gpus, exclude_gpus)
        while len(gpu_ids) < num_gpus:
            self.logger.info(f"Avaiable GPU devices are {gpu_ids}, but requires {num_gpus} devices")
            time.sleep(find_gpu_delay)
            gpu_ids = self.__find_avaiable_devices(num_gpus, exclude_gpus)
        
        return gpu_ids
    
    def update_gpu_process(self, gpu_ids, process):
        is_success = self.release_gpus(process.pid)
        if is_success:
            for gpu in gpu_ids:
                self.gpu_process[gpu] = process
        else:
            raise ValueError(f"Process {self.gpu_process[gpu_ids[0]].pid} on GPU {gpu_ids} is not finished")
    
    def release_gpus(self, pid):
        for idx, _proc in enumerate(self.gpu_process):
            if _proc is None:
                continue

            if _proc.pid == pid:
                if _proc.poll() is None:
                    return False
                else:
                    self.gpu_process[idx] = None
        
        return True

    def __get_all_gpus(self):
        return [gpu.id for gpu in GPUtil.getGPUs()]

    def __find_avaiable_devices(self, num_gpus, exclude_gpus):
        gpu_ids = GPUtil.getAvailable(
            order='first',
            limit=inf,
            maxLoad=0.1,
            maxMemory=0.1,
            includeNan=False,
            excludeID=exclude_gpus,
            excludeUUID=[]
            )
        
        gpu_ids = [gpu for gpu in gpu_ids if not self.__is_gpu_occupied(gpu)]

        return gpu_ids[:num_gpus]
    
    def __is_gpu_occupied(self, gpu):
        _proc = self.gpu_process[gpu]
        if _proc is None:
            return False
        else:
            return _proc.poll() is None


class GPUTaskManagerServer(object):
    def __init__(self, database, logger):
        self.db = database
        self.logger = logger
        self.gpu_manager = GPUManager(logger)

        self.is_stop_requested = False

        signal.signal(signal.SIGINT, self.__stop)
        signal.signal(signal.SIGTERM, self.__stop)

    def __start(self):
        while not self.is_stop_requested:
            self.__check_if_task_done()
            # read next command from database
            with orm.db_session:
                task = self.db.get_next_task()
                if task is not None:
                    self.logger.info(f"task: {task.id}, {task.command}")
                    
                    # 1. update task's state
                    self.logger.info(f"change task {task.id} from {STATE.get_state_str(task.state)} to {STATE.get_state_str(STATE.PENDING)}")
                    task.state = STATE.PENDING
                    orm.commit()
                    
                    # 2. find available gpus
                    gpu_ids = self.gpu_manager.get_gpus(task.num_gpus_required, task.exclude_gpus, FIND_GPU_DELAY)
                    # update task's occupied_gpus
                    task.occupied_gpus = gpu_ids
                    orm.commit()
                    
                    # 3. execute in background
                    self.logger.info(f"run command {task.command} in background")
                    process = self.__run_background_process(task.command.split(), gpu_ids)
                    task.state = STATE.RUNNING
                    task.system_pid = process.pid
                    task.execute_time = datetime.datetime.utcnow()
                    orm.commit()

                    self.gpu_manager.update_gpu_process(gpu_ids, process)
                
            time.sleep(SUBMIT_TASK_DELAY)
        
        self.logger.info("stop requested")
        self.__rollback_pending_tasks()
        self.__check_if_task_done()

        with orm.db_session:
            server = self.db.get_server_by_pid(os.getpid())
            if server is not None:
                server.stop_time = datetime.datetime.utcnow()
                self.logger.info("stopped")
            else:
                self.logger.error("internal error when stopping")

        
    def __stop(self, *args):
        self.is_stop_requested = True
                
    @orm.db_session
    def __check_if_task_done(self):
        self.logger.info("check done task")
        for task in self.db.find_tasks_by_state(STATE.RUNNING):
            if self.gpu_manager.release_gpus(task.system_pid) or not is_pid_alive(task.system_pid):
                self.logger.info(f"task {task.id} is done")
                task.state = STATE.DONE
    
    @orm.db_session
    def __rollback_pending_tasks(self):
        self.logger.info("rollback pending tasks")
        for task in self.db.find_tasks_by_state(STATE.PENDING):
            self.logger.info(f"change state of task {task.id} \
                                from {STATE.get_state_str(task.state)} to {STATE.get_state_str(STATE.QUEUING)}")
            task.state = STATE.QUEUING

    def __run_background_process(self, cmd, gpu_ids):
        env = os.environ.copy()
        env['CUDA_VISIBLE_DEVICES'] = ",".join([str(gpu) for gpu in gpu_ids])
        proc = subprocess.Popen(cmd, env=env)
        return proc
    

    def start(self):
        can_start = False
        with orm.db_session:
            last_server = self.db.get_last_server()
            if last_server is None or last_server.stop_time is not None:
                can_start = True
            else:
                if is_pid_alive(last_server.pid):
                    raise ValueError(f"server with pid {last_server.pid} are running from {last_server.start_time}")
                else:
                    last_server.stop_time = datetime.datetime.utcnow()
                    can_start = True
        
        if can_start:
            self.db.add_server(os.getpid())
            self.logger.info("started")
            self.__start()

    def stop(self):
        with orm.db_session:
            last_server = self.db.get_last_server()
            if last_server is None or last_server.stop_time is not None:
                print("no server is running")
            else:
                print('stopping ', end='', flush=True)
                while is_pid_alive(last_server.pid):
                    # kill process by pid
                    try:
                        os.kill(last_server.pid, signal.SIGTERM)
                        print('.', end='', flush=True)
                        time.sleep(10)
                    except:
                        if is_pid_alive(last_server.pid):
                            continue
                        else:
                            break
                
                print("stopped")


if __name__ == "__main__":
    parser = argparse.ArgumentParser("GPU Task Manager")
    parser.add_argument("mode", type=str, default="start", choices=["start", "stop", "restart"])
    args = parser.parse_args()

    db = get_database()
    logger = get_logger(LOG_PATH)
    server = GPUTaskManagerServer(db, logger)
    
    if args.mode == "start":
        server.start()
    elif args.mode == "stop":
        server.stop()