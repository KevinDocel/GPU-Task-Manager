# GPU Task Manager
A simple GPU task manager that can automatically run user-defined tasks on available GPUs.

# Updates
- [2021.11.20] A whole new design which includes background server and user-friendly client.

# TODO
- [x] restore unfinised tasks when started
- [ ] installable service
- [x] show server state

# Dependencies
- [GPUtil](https://github.com/anderskm/gputil)
- [pony](https://ponyorm.org/)
- [termcolor](https://pypi.org/project/termcolor/)
- [tabulate](https://pypi.org/project/tabulate/)

# Usages
`GPU-Task-Manager` includes server and client. The server manages reading and running tasks. The client supports: display task state, submit new tasks, delete tasks and modify the priority of tasks.


## Configuration
- `config.py`

```python
DELAY = 60
LOG_PATH = ""
```

- It is recommended to configure `alias` in your `.bashrc`. Assuming that you have downloaded this repo in to `root`.

```shell
alias gpu-task-server='bash root/GPU-Task-Mananer/main.sh'
alias gpu-task-client='python root/GPU-Task-Manager/client.py'
```

## Server
Suppose that `alias` has been configured , then you can start, stop, and restart server by:

```shell
gpu-task-serer [start|stop|restart]
```

You can also check thet running state of server by

```shell
gpu-task-server show
```

In case that the server is unexpectedly down, you can periodically start server by crontab. Note that if server is running, the `start` command does nothing but print messages of the running server.

```shell
0 * * * * bash /path/to/GPU-Task-Manager/main.sh start
```

Also, you should source the python virtual env in `main.sh` if you are using conda.

```shell
source ~/miniconda3/etc/profile.d/conda.sh
conda activate XXX
```

## Client
- show task state
```shell
gpu-task-client
```

- show first n tasks
```shell
gpu-task-client -m n
```

- show task state every 3 seconds
```shell
gpu-task-client -l 3
gpu-task-client --loop 3
```

- show task by state
```shell
gpu-task-client -s running
```

- submit task from command line
    - `-c --command`: task command
    - `-n --num-gpus`: number of gpus required, default 1
    - `-e --exclude-gpus`: exclude gpus
```shell
gpu-task-client -c bash train.sh
gpu-task-client -c bash train.sh -n 1
gpu-task-client -c bash train.sh -n 4
gpu-task-client --command bash train.sh --num-gpus 4
gpu-task-client --command bash train.sh --num-gpus 4 -e 0 1 2 3
```
- submit task from file
    - `--file-path`: task file path
    - `-e --exclude-gpus`: exclude gpus for all tasks in task file
    - task file definition (default `num_gpus=1`)
    ```
    command(;num_gpus)
    echo Hi;
    echo Hi;4
    ...
    ```
- delete task
    - `-d --delete`: delete task by task id
```shell
gpu-task-client -d 1
```

- update task priority
    - `-p --update-priority`: set new task priority by task id
```shell
gpu-task-client -p 1 10
```
It will set the priority of task with ID `1` to `10`.
This feature is useful when you need to change the execution order of task. Note that smaller value (>0) means higher priority.
