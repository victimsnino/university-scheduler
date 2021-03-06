from enum import Flag, Enum

# Parameters
DEBUG_PRINT = False

FAST    = 1
MIDDLE  = 2
SLOW    = 3

class BalancedConstraints:
    def __init__(self):
        self.by_lesson_penalty              = 1
        self.by_ts_penalty                  = 1
        #[DEPRECATED]
        self.by_room_penalty                = 0
        self.skip_balance_by_penalty        = 0.001 #It is better to use 0.01, but it can slow down performance (since it is so hard to satisfy it)

class SoftConstraints:
    def __init__(self):
        self.max_lessons_per_day                            = 3
        self.max_lessons_per_day_penalty                    = 1
        # it works like,  lessons == 0 or >= *value*
        self.min_lessons_per_day                            = 2
        self.min_lessons_per_day_penalty                    = 6 # My opinion, that it should be greater, than bachelor_time_slots_per_day*stability_penalty
        
        # multiply for weeks of common type. For example, 0th and 2th week similarity is more prioritized, than 0th and 1th (another words, upper and down weeks)
        self.similar_week_multiply                          = 5
        self.balanced_constraints                           = BalancedConstraints()
        
        self.minimize_count_of_rooms_per_day_penalty        = 0.1
        # nobody wants to study on saturday
        self.last_day_in_week_penalty                       = 0.1
        
        self.timeslots_penalty                              = [1, 0, 0, 0, 0.1, 1.1, -1, -1] # must be like a gradient of penalties without gaps. 

        self.min_count_of_specific_lessons_during_day       = 2  # as a result, it tries to group at least by X lessons by day. For lecture used/2 value
        self.min_count_of_specific_lessons_penalty          = 1

        self.max_count_of_specific_lessons_during_day       = 3  # as a result, it tries to group maximum by X lessons by day
        self.max_count_of_specific_lessons_penalty          = 1
        
         # value < 0  is Hard constraint
        self.grouping_subjects_during_day_penalty           = 1

        # 0 - disabled, < 0 - hard, > 0 soft
        self.lesson_after_lesson_penalty                    = 1

        # 0 - disabled, < 0 - hard, > 0 soft
        self.ban_corpuses_penalty                           = 1
        
        
class Config:
    def __init__(self):
        self.reset()
        
    def reset(self):
        self.timelimit_for_solve            = 300
        self.bachelor_time_slots_per_day    = 6
        self.magistracy_time_slots_per_day  = 2
        # Expected, that lessons for magistracy AFTER bachelors
        self.time_slots_per_day_available   = self.bachelor_time_slots_per_day + self.magistracy_time_slots_per_day
        self.study_days                     = 6
        self.max_lessons_per_day            = 5
        self.max_lessons_per_week           = 16 # 25 hours / 6 = 16.666666
        # -1 -> hard constraint, 0 - without constraint, >= 1  - penalty for soft costraint
        self.windows_penalty                = 20
        # windows for groups is more critical thing then for teachers.
        self.windows_groups_multiplier      = 2
        self.soft_constraints               = SoftConstraints()
        
        self.friend_lessons                 = True

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



teachers_per_lesson_format  =   lesson_prefix   + "%d"  +\
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
