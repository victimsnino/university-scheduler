from enum import Flag, Enum

# Parameters
DEBUG_PRINT = False
class SoftConstraints:
    def __init__(self):
        self.max_lessons_per_day                            = 3
        self.max_lessons_per_day_penalty                    = 1
        self.lessons_in_similar_day_and_ts_penalty          = 1
        # 1 - fast but can be not optimal,  2 - partly optimal and partly fast, 3 - optimal
        self.lessons_in_similar_day_and_ts_level_of_solve   = 1
        self.minimize_count_of_rooms_per_day_penalty        = 1
        
class Config:
    def __init__(self):
        self.reset()
        
    def reset(self):
        self.bachelor_time_slots_per_day    = 6
        self.magistracy_time_slots_per_day  = 2
        # Expected, that lessons for magistracy AFTER bachelors
        self.time_slots_per_day_available   = self.bachelor_time_slots_per_day + self.magistracy_time_slots_per_day
        self.study_days                     = 6
        self.max_lessons_per_day            = 5
        self.max_lessons_per_week           = 16 # 25 hours / 6 = 16.666666
        # -1 -> hard constraint, 0 - without constraint, >= 1  - penalty for soft costraint
        self.windows_penalty                = 1
        # windows for groups is more critical thing then for teachers.
        self.windows_groups_multiplier      = 2
        self.soft_constraints               = SoftConstraints()

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
                    lesson_prefix   +   "%d"    +\
                    group_prefix    +   "%s"    +\
                    type_prefix     +   "%s"    +\
                    teacher_prefix  +   "%d"



corpus_tracker_of_groups_format =   corpus_prefix    +   "%d"    +\
                                    week_prefix      +   "%d"    +\
                                    day_prefix       +   "%d"    +\
                                    group_prefix     +   "%d"

corpus_tracker_of_teachers_format = corpus_prefix    +   "%d"    +\
                                    week_prefix      +   "%d"    +\
                                    day_prefix       +   "%d"    +\
                                    teacher_prefix   +   "%d"

room_tracker_of_groups_format  =    room_prefix      +   "%d"    +\
                                    corpus_tracker_of_groups_format

room_tracker_of_teachers_format  =  room_prefix      +   "%d"    +\
                                    corpus_tracker_of_teachers_format


teachers_per_lesson_format  =   lesson_prefix   + "%s"  +\
                                teacher_prefix  + "%d"



class RoomType(Flag):
    COMPUTER    = 1
    LECTURE     = 2
    PRACTICE    = 4

class GroupType(Enum):
    BACHELOR = 1
    MAGISTRACY = 2

def debug(string):
    global DEBUG_PRINT
    if DEBUG_PRINT == True:
        print("DEBUG: " + str(string))

def set_debug(bool):
    global DEBUG_PRINT
    DEBUG_PRINT = bool
