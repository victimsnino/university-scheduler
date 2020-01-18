from enum import Flag

# Parameters
DEBUG_PRINT = False

class Config:
    def __init__(self):
        self.reset()
        
    def reset(self):
        self.time_slots_per_day_available = 6
        self.study_days                   = 6
        self.study_weeks                  = 1
        self.max_lessons_per_day          = 5
        self.max_lessons_per_week         = 16 # 25 hours / 6 = 16.666666

global_config = Config()

# Some constants
week_prefix     = '_week_'
day_prefix      = '_day_'  # 0-5
corpus_prefix   = '_corpus_'
room_prefix     = '_room_'
timeslot_prefix = '_timeslot_'
lesson_prefix   = '_lesson_'
group_prefix    = '_groupids_'
type_prefix     = '_type_'
teacher_prefix  = '_teacher_'

time_slot_format =  week_prefix     +   "%d"    +\
                    day_prefix      +   "%d"    +\
                    corpus_prefix   +   "%d"    +\
                    room_prefix     +   "%d"    +\
                    timeslot_prefix +   "%d"    +\
                    lesson_prefix   +   "%s"    +\
                    group_prefix    +   "%s"    +\
                    type_prefix     +   "%s"    +\
                    teacher_prefix  +   "%d"

# should have uniq string, therefore doesnt equil with above
corpus_corpus_prefix = '_in_corp_'
corpus_week_prefix   = '_cweek_'
corpus_day_prefix    = '_cday_'
corpus_group_prefix = '_group_'
corpus_teacher_prefix = '_teach_'

corpus_tracker_of_groups_format =   corpus_corpus_prefix    +   "%d"    +\
                                    corpus_week_prefix      +   "%d"    +\
                                    corpus_day_prefix       +   "%d"    +\
                                    corpus_group_prefix     +   "%d"
corpus_tracker_of_teachers_format = corpus_corpus_prefix    +   "%d"    +\
                                    corpus_week_prefix      +   "%d"    +\
                                    corpus_day_prefix       +   "%d"    +\
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
