#!/usr/bin/python3

def calculate_target_course(course_diff):
    slowdown_factor_left = 1.0
    slowdown_factor_right = 1.0
    if course_diff <=180.0:
        # right turn
        slowdown_factor_right = 1 - (course_diff / 180)
    else:
        # left turn
        slowdown_factor_left = (course_diff - 180) / (359.9 - 180)

    return (slowdown_factor_left, slowdown_factor_right)

if __name__ == "__main__":
    print(calculate_target_course(359))