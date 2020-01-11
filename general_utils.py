from enum import Flag

# Parameters
DEBUG_PRINT = False
time_slots_per_day = 5


# Some constants
corpus_prefix   = 'corpus'
room_prefix     = 'room'
timeslot_prefix = 'timeslot'
lesson_prefix   = 'lesson'
group_prefix    = 'groupids'
type_prefix     = 'type'

time_slot_format = corpus_prefix+"_%d_"+room_prefix+ "_%d_" + timeslot_prefix+ "_%d_" + lesson_prefix + "_%s_" + group_prefix + "_%s_" + type_prefix + "_%s"

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
