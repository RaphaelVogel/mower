import time
import random
import queue


def get_rpm(rpm_queue):
    while True:
        time.sleep(0.3)
        try:
            rpm_queue.put_nowait((random.randint(1, 10), random.randint(1, 10)))
        except queue.Full:
            pass
