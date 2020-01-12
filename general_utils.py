from enum import Flag

# Parameters
DEBUG_PRINT = False
time_slots_per_day = 5


# Some constants
corpus_prefix   = '_corpus_'
room_prefix     = '_room_'
timeslot_prefix = '_timeslot_'
lesson_prefix   = '_lesson_'
group_prefix    = '_groupids_'
type_prefix     = '_type_'

time_slot_format = corpus_prefix    +   "%d"    +\
                   room_prefix      +   "%d"    +\
                   timeslot_prefix  +   "%d"    +\
                   lesson_prefix    +   "%s"    +\
                   group_prefix     +   "%s"    +\
                   type_prefix      +   "%s"

class RoomType(Flag):
    COMPUTER    = 1
    LECTURE     = 2

def debug(string):
    global DEBUG_PRINT
    if DEBUG_PRINT == True:
        print("DEBUG: " + str(string))

def set_debug(bool):
    global DEBUG_PRINT
    DEBUG_PRINT = bool
