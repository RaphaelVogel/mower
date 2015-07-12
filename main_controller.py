import multiprocessing as mp
import queue
import modules.rpm_controller as rpm
import time


rpm_queue = mp.Queue(1)
p_rpm = mp.Process(target=rpm.get_rpm, args=(rpm_queue,))
p_rpm.daemon = True
p_rpm.start()

# main loop
while True:
    try:
        print(rpm_queue.get_nowait())
    except queue.Empty:
        print("Queue was empty")
    time.sleep(0.5)
