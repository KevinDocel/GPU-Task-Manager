# GPU Task Manager
A simple GPU task manager that can automatically run user-defined tasks on available GPUs.

# Usages
There are two types of usages: tasks can be defined by either command-line arguments (for single command task) or task files (for multiple commands task)

## Command-line
### Arguments:
- `--cmd`: used-defined command. e.g. "echo Hello World!".
- `--gpus`: number of GPUs to use, default is 1. e.g. 4.
- `--exclude-gpus`: GPU device ids that cannot be used, default is [] e.g. "6 7".
- `--find-gpu-delay`: delay time in seconds when there are no available GPUs currently, default is 600.
- `--log-path`: log file path and name, default is "./logs/submit.log".

```shell
python submit.py --cmd echo Hello World! --gpus 4 --exclude-gpus 6 7 --find-gpu-delay 600 --log-path ./logs/submit.log
```

## Input File
### Arguments:
- `--filepath`: task file path. e.g. "./tasks/test.task"
- `--submit-task-delay`: delay time in seconds after submit a command. e.g. 60.
- `--exclude-gpus`, `--find-gpu-delay` and `--log-path` are same as arguments in command-line.

```shell
python submit.py --filepath ./tasks/test.task --exclude-gpus 6 7 --find-gpu-delay 600 --submit-task-delay 60 --log-path ./logs/test.log
```

### Task File
xxx.task
```
command(;num_gpus)
echo Hi;
echo Hi;4
...
```
By default `num_gpus=1`
