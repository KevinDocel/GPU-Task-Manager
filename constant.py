class STATE:
    RUNNING = 0
    PENDING = 1
    QUEUING = 2
    DONE = 3

    @staticmethod
    def get_state_str(state):
        if state == STATE.RUNNING:
            return "running"
        elif state == STATE.PENDING:
            return "pending"
        elif state == STATE.QUEUING:
            return "queuing"
        else:
            return "done"
    
    @staticmethod
    def get_state_from_str(state_str):
        if state_str == "running":
            return STATE.RUNNING
        elif state_str == "pending":
            return STATE.PENDING
        elif state_str == "queuing":
            return STATE.QUEUING
        elif state_str == "done":
            return STATE.DONE
        else:
            raise ValueError(f"Unknown state: {state_str}")
    
    @staticmethod
    def get_state_color(state):
        if state == STATE.RUNNING:
            color = "green"
        elif state == STATE.QUEUING:
            color = "cyan"
        elif state == STATE.PENDING:
            color = "yellow"
        else:
            color = "red"
        
        return color


if __name__ == "__main__":
    print(STATE.RUNNING)