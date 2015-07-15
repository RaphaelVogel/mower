import multiprocessing as mp
import modules.drive_controller as drive
import time


drive_conn, drive_conn1 = mp.Pipe()
p_drive = mp.Process(target=drive.start, args=(drive_conn1,))
p_drive.start()

while True:
    time.sleep(0.1)
    if drive_conn.poll():
        print(drive_conn.recv())