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
teacher_prefix  = '_teacher_'

time_slot_format = corpus_prefix    +   "%d"    +\
                   room_prefix      +   "%d"    +\
                   timeslot_prefix  +   "%d"    +\
                   lesson_prefix    +   "%s"    +\
                   group_prefix     +   "%s"    +\
                   type_prefix      +   "%s"    +\
                   teacher_prefix   +   "%d"

# should have uniq string, therefore doesnt equil with above
corpus_corpus_prefix = '_in_corp_'
corpus_group_prefix = '_group_'
corpus_teacher_prefix = '_teach_'

corpus_tracker_of_groups_format =   corpus_corpus_prefix    +   "%d"    +\
                                    corpus_group_prefix     +   "%d"
corpus_tracker_of_teachers_format =  corpus_corpus_prefix    +   "%d"    +\
                                     corpus_teacher_prefix   +   "%d"


class RoomType(Flag):
    COMPUTER    = 1
    LECTURE     = 2
    PRACTICE    = 4

def debug(string):
    global DEBUG_PRINT
    if DEBUG_PRINT == True:
        print("DEBUG: " + str(string))

def set_debug(bool):
    global DEBUG_PRINT
    DEBUG_PRINT = bool
