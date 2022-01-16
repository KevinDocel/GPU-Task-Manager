import datetime

from pony.orm import *

from constant import *

# set_sql_debug(True)

db = Database()


class Task(db.Entity):
    id = PrimaryKey(int, auto=True)
    state = Required(int, default=STATE.QUEUING)
    priority = Required(int, default=100)
    submit_time = Required(datetime.datetime, default=datetime.datetime.utcnow)
    execute_time = Optional(datetime.datetime)
    system_pid = Optional(int)
    occupied_gpus = Optional(IntArray)
    exclude_gpus = Optional(IntArray)
    command = Required(str)
    num_gpus_required = Required(int, default=1)


class Server(db.Entity):
    id = PrimaryKey(int, auto=True)
    pid = Required(int)
    start_time = Required(datetime.datetime, default=datetime.datetime.utcnow)
    stop_time = Optional(datetime.datetime)


class GPUTaskDatabase(object):
    def __init__(self, database):
        self.db = database
        self.db.bind(provider='sqlite', filename='task.db', create_db=True)
        self.db.generate_mapping(create_tables=True)
    
    @db_session
    def add_task(self, command, num_gpus_required, exclude_gpus):
        Task(command=command, num_gpus_required=num_gpus_required, exclude_gpus=exclude_gpus)
    
    def find_tasks_by_state(self, state):
        tasks = select(t for t in Task if t.state==state).order_by(Task.priority, Task.submit_time)
        return list(tasks)
    
    def get_next_task(self):
        # highest priority (smallest value), most early submity_time
        task = select(t for t in Task if t.state == STATE.QUEUING).order_by(Task.priority, Task.submit_time)[:1]
        task = list(task)
        
        if len(task) == 1:
            return task[0]

        return None
    
    def get_task_by_id(self, task_id):
        if Task.exists(id=task_id):
            return Task[task_id]
        
        return None
    
    def get_last_server(self):
        server = select(s for s in Server).order_by(desc(Server.start_time))[:1]
        server = list(server)

        if len(server) == 1:
            return server[0]
        
        return None
    
    def get_server_by_pid(self, pid):
        server = select(s for s in Server if s.pid == pid)
        server = list(server)

        if len(server) >= 1:
            return server[0]
        
        return None
    
    @db_session
    def add_server(self, pid):
        Server(pid=pid)
        

    # @db_session
    # def update_task(self, task_id, new_task):
    #     task = Task[task_id]
    #     task.state = new_task.state
    #     task.priority = new_task.priority
    #     task.execute_time = new_task.execute_time
    #     task.system_pid = new_task.system_pid
    #     task.occupied_gpus = new_task.occupied_gpus

    @db_session
    def remove_task(self, task_id):
        task = Task[task_id]
        task.delete()

    @db_session
    def remove_all(self):
        delete(t for t in Task)
    

def get_database():
    gpu_task_db = GPUTaskDatabase(db)
    return gpu_task_db

if __name__ == '__main__':
    gpu_task_db = get_database()
    
    # add dummy task
    import random

    for i in range(4):
        gpu_task_db.add_task(
            command=f"echo Hi {i}!",
            num_gpus_required=random.randint(1, 4),
            exclude_gpus=[],
        )
    
    # find task by state
    task_id = -1
    with db_session:
        tasks = gpu_task_db.find_tasks_by_state(state=STATE.PENDING)
        for task in tasks:
            # print(task)
            task_id = task.id
    
    # gpu_task_db.update_task_state(task_id, STATE.RUNNING)

    # # gpu_task_db.remove_task(1)

    # with db_session:
    #     task = gpu_task_db.get_next_task()
    #     print(task.id, task.submit_time, task.command)
