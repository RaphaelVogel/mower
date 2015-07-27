import multiprocessing as mp
import modules.drive_controller as drive
import time

drive_conn, drive_conn1 = mp.Pipe()
p_drive = mp.Process(target=drive.start, args=(drive_conn1,))
p_drive.daemon = True
p_drive.start()

while True:
    #right = input("Enter right wheel speed:")
    #left = input("Enter left wheel speed:")
    #cutter = input("Enter cutter speed:")
    #drive_conn.send("cutter/" + cutter)
    val = input("New Value: ")
    drive_conn.send(val)