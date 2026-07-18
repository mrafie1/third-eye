import time
from camera_stuff import agent

if __name__ == "__main__":
    # Define settings and objects
    INTERVAL = 2
    PAUSE_INTERVAL = 15
    agent_object = agent.AgentController()

    def setup():
        print("System starting...")

    def camera_loop():
        response = agent_object.workflow()
        if response == "continue":
            time.sleep(INTERVAL)
        else:
            time.sleep(PAUSE_INTERVAL)

    setup()
    while True:
        camera_loop()