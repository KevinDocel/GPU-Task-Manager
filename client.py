import os
import argparse
import time
import sys

from pony import orm
from termcolor import colored
from tabulate import tabulate

from config import *
from constant import *

from database import get_database


class GPUTaskManagerClient(object):
    def __init__(self, database):
        self.db = database
    

    def submit(self, command, num_gpus_required, exclude_gpus=[]):
        command = " ".join([c for c in command])
        self.db.add_task(command=command, num_gpus_required=num_gpus_required, exclude_gpus=exclude_gpus)
        print(f"successfully add task `{command}`")
    
    def submit_from_file(self, filepath, exclude_gpus=[]):
        if not os.path.exists(filepath):
            raise ValueError(f"`{filepath}` does not exit!")

        with open(filepath, 'r') as f:
            for line in f.readlines():
                line = line.strip()
                if line.startswith("#") or line == '':
                    # ignore comment or blank line
                    continue
                
                items = line.split(";")
        
                cmd = items[0].split()
                num_gpus = 1
                if len(items) > 1:
                    num_gpus = int(items[1])
                
                # submit task
                self.submit(command=cmd, num_gpus_required=num_gpus, exclude_gpus=exclude_gpus)
    
    @orm.db_session
    def delete(self, task_id):
        task = self.db.get_task_by_id(task_id)
        
        if task is None:
            print(f"no task found by id {task_id}")
            return
        
        if task.state == STATE.QUEUING:
            self.db.remove_task(task_id)
            print(f"successfully delete task id {task_id}")
        else:
            print(f"task in {STATE.get_state_str(task.state)} state can not be deleted")
    
    @orm.db_session
    def update_priority(self, task_id, new_priority):
        task = self.db.get_task_by_id(task_id)
        if task is None:
            print(f"no task found by id {task_id}")
            return
        
        try:
            new_priority = int(new_priority)
        except:
            print(f"priority value of {new_priority} is not allowed, requires int")
            return
        
        if new_priority > 0:
            old_priority = task.priority
            task.priority = new_priority
            print(f"successfully update priority of task id {task_id} from {old_priority} to {new_priority}")
        else:
            print(f"priority requires positive int, but got {new_priority}")

    @orm.db_session
    def show(self, limit=None, state=None):
        all_tasks = []
        if state is None:
            allowed_states = (STATE.RUNNING, STATE.PENDING, STATE.QUEUING, STATE.DONE)
        else:
            allowed_states = (STATE.get_state_from_str(state),)

        for state in allowed_states:
            tasks = self.db.find_tasks_by_state(state)
            all_tasks.extend(tasks)
        self.__formatted_print(all_tasks, limit)


    def __formatted_print(self, tasks, limit):
        headers = ["ID", "STATE", "PRIORITY", "SUBMIT_TIME", "EXECUTE_TIME", "SYSTEM_PID", 
                    "OCCUPIED_GPUS", "EXCLUDE_GPUS", "NUM_GPUS", "COMMAND"]
        
        table = []
        for idx, t in enumerate(tasks):
            if limit is not None and limit == idx:
                break
            table.append([t.id, colored(STATE.get_state_str(t.state), STATE.get_state_color(t.state)), t.priority,
                            t.submit_time.strftime("%Y-%m-%d %H:%M:%S") if t.submit_time is not None else None, 
                            t.execute_time.strftime("%Y-%m-%d %H:%M:%S") if t.execute_time is not None else None, 
                            t.system_pid, t.occupied_gpus, t.exclude_gpus, t.num_gpus_required, t.command])
        
        print(tabulate(table, headers=headers))


if __name__ == "__main__":
    parser = argparse.ArgumentParser("GPU Task Manager")
    # show
    parser.add_argument("--loop", "-l", type=int, default=None)
    parser.add_argument("--limit", "-m", type=int, default=None)
    parser.add_argument("--state", "-s", type=str, default=None)
    
    # delete
    parser.add_argument("--delete", "-d", type=int, default=None)

    # update priority
    parser.add_argument("--update-priority", "-p", nargs="+", default=None)

    # command line
    parser.add_argument("--command", "-c", nargs="+", default=None)
    parser.add_argument("--num-gpus", "-n", type=int, default=1)
    # file
    parser.add_argument("--file-path", "-f", type=str, default=None)
    parser.add_argument("--exclude-gpus", "-e", nargs="*", type=int, default=[])

    args = parser.parse_args()

    client = GPUTaskManagerClient(get_database())

    if args.command is not None:
        client.submit(args.command, args.num_gpus, args.exclude_gpus)
    elif args.file_path is not None:
        client.submit_from_file(args.file_path)
    elif args.delete is not None:
        client.delete(args.delete)
    elif args.update_priority is not None:
        if len(args.update_priority) > 0 and len(args.update_priority) % 2 == 0:
            for i in range(len(args.update_priority) // 2):
                task_id = args.update_priority[2 * i]
                priority = args.update_priority[2 * i + 1]
                client.update_priority(task_id, priority)
        else:
            print("update priority with key value pairs: task_id_1 new_priority_1 task_id_2 new_priority_2 ...")
    elif args.loop is not None:
        while True:
            try:
                os.system('clear')
                client.show(args.limit, args.state)
                time.sleep(args.loop)
            except KeyboardInterrupt:
                sys.exit()
    else:
        client.show(args.limit, args.state)
