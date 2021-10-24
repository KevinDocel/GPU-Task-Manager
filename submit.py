from math import inf
import os
import time
import subprocess
import argparse
import logging

import GPUtil


class GPUManager(object):
    NOT_OCCUPIED = None

    def __init__(self, exclude_gpus, find_gpu_delay, logger):
        self.exclude_gpus = exclude_gpus
        self.find_gpu_delay = find_gpu_delay
        self.logger = logger
        
        all_gpus = self._get_all_gpus()
        self.gpu_pids = [self.NOT_OCCUPIED for _ in range(len(all_gpus))]

    def get_gpus(self, num_gpus):
        gpu_ids = self._find_avaiable_devices(num_gpus, self.exclude_gpus)
        while len(gpu_ids) < num_gpus:
            self.logger.info(f"Avaiable GPU devices are {gpu_ids}, but requires {num_gpus} devices")
            self.logger.info(f"Delay {self.find_gpu_delay} seconds to find devices")
            
            time.sleep(self.find_gpu_delay)
            gpu_ids = self._find_avaiable_devices(num_gpus, self.exclude_gpus)
        
        self.logger.info(f"Found GPU devices: {gpu_ids}")
        
        return gpu_ids
    
    def update_gpu_pid(self, gpu_ids, pid):
        for gpu in gpu_ids:
            self.gpu_pids[gpu] = pid

    def _get_all_gpus(self):
        return [gpu.id for gpu in GPUtil.getGPUs()]

    def _find_avaiable_devices(self, num_gpus, exclude_gpus):
        gpu_ids = GPUtil.getAvailable(
            order='first',
            limit=inf,
            maxLoad=0.1,
            maxMemory=0.1,
            includeNan=False,
            excludeID=exclude_gpus,
            excludeUUID=[]
            )
        
        self.logger.info(f"Empty GPUs: {gpu_ids}")
        self.logger.info(f"Occupied GPUs: {[gpu for gpu in gpu_ids if self._is_gpu_occupied(gpu)]}")

        gpu_ids = [gpu for gpu in gpu_ids if not self._is_gpu_occupied(gpu)]
        self.update_gpu_pid(gpu_ids, self.NOT_OCCUPIED)

        return gpu_ids[:num_gpus]
    
    def _is_gpu_occupied(self, gpu):
        
        def _is_pid_alive(pid):
            try:
                os.kill(pid, 0)
            except OSError:
                return False
            else:
                return True
        
        if self.gpu_pids[gpu] is None:
            return False
        else:
            return _is_pid_alive(self.gpu_pids[gpu])



class TaskManager(object):
    def __init__(self, cfg):
        self.cfg = cfg
        self.logger = self._init_logger(self.cfg["LOG_PATH"])
        self.gpu_manager = GPUManager(self.cfg["EXCLUDE_GPUS"], self.cfg["FIND_GPU_DELAY"], self.logger)
    
    def submit(self, cmd, num_gpus):
        self.logger.info(f"Try to find {num_gpus} GPU devices, exclude GPUs {self.cfg['EXCLUDE_GPUS']}")
        gpu_ids = self.gpu_manager.get_gpus(num_gpus)

        self.logger.info("Submit task in background")
        pid = self._run_background_process(cmd, gpu_ids)

        self.logger.info(f"Update GPU {gpu_ids} with pid {pid}")
        self.gpu_manager.update_gpu_pid(gpu_ids, pid)

    
    def submit_from_file(self, filepath):
        if not os.path.exists(filepath):
            raise ValueError(f"`{filepath}` does not exit!")

        # read task
        self.logger.info(f"Read commands from {filepath}")
        tasks = []
        with open(filepath, 'r') as f:
            for line in f.readlines():
                items = line.strip().split(";")
        
                cmd = items[0].split()
                gpus = 1
                if len(items) > 1:
                    gpus = int(items[1])
        
                tasks.append((cmd, gpus))
        
        # submit task
        for task in tasks:
            self.submit(cmd=task[0], num_gpus=task[1])
            time.sleep(self.cfg["SUBMIT_TASK_DELAY"])
    
    def _run_background_process(self, cmd, gpu_ids):
        cmd_str = " ".join(cmd)
        self.logger.info(f'Run "{cmd_str}" on GPU {gpu_ids}')

        env = os.environ.copy()
        env['CUDA_VISIBLE_DEVICES'] = ",".join([str(gpu) for gpu in gpu_ids])
        proc = subprocess.Popen(cmd, env=env)
        return proc.pid

    def _init_logger(self, log_path):
        logging.basicConfig(
                level=logging.INFO, 
                format='%(asctime)s %(levelname)s: %(message)s',
                handlers=[
                    logging.FileHandler(log_path, mode='w'),
                    logging.StreamHandler()
                    ]
                )
        logger = logging.getLogger(__name__)
        return logger


def parse_args():
    parser = argparse.ArgumentParser("")
    
    parser.add_argument("--cmd", nargs="+", default=None)
    parser.add_argument("--gpus", type=int, default=1)

    parser.add_argument("--exclude-gpus", nargs="*", type=int, default=[])

    parser.add_argument("--filepath", type=str, default=None)
    parser.add_argument("--find-gpu-delay", type=int, default=60 * 10)
    parser.add_argument("--submit-task-delay", type=int, default=60)

    parser.add_argument("--log-path", type=str, default="./logs/submit.log")

    args = parser.parse_args()
    return args


if __name__ == '__main__':
    '''
    How to use:
        python submit.py --cmd echo Hello! --gpus 1 --exclude-gpus 0 1 --find-gpu-delay 600
        
        python submit.py \
            --filepath ./task/test.task \
            --exclude-gpus 0 1 \
            --find-gpu-delay 600 \
            --submit-task-delay 60 \
            --log-path ./logs/test.log

    test.task
        Command(;NUM_GPUS)
        echo Hello
        echo Hello;1
    '''

    args = parse_args()

    cfg = {
        "FIND_GPU_DELAY": args.find_gpu_delay,
        "SUBMIT_TASK_DELAY": args.submit_task_delay,
        "EXCLUDE_GPUS": args.exclude_gpus,
        "LOG_PATH": args.log_path,
    }

    task_manager = TaskManager(cfg)
    if args.filepath:
        task_manager.submit_from_file(args.filepath)
    elif args.cmd:
        task_manager.submit(args.cmd, args.gpus)
    else:
        print("No commands provided from file or commnand line.")