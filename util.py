import os
import logging


def is_pid_alive(pid):
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    else:
        return True


def get_logger(log_path):
    log_dir = os.path.dirname(log_path)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
        
    logging.basicConfig(
            level=logging.INFO, 
            format='%(asctime)s %(levelname)s: %(message)s',
            handlers=[
                logging.FileHandler(log_path, mode='a'),
                logging.StreamHandler()
                ]
            )
    logger = logging.getLogger(__name__)
    return logger