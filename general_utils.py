from enum import Flag, Enum

# Parameters
DEBUG_PRINT = False
class SoftConstraints:
    def __init__(self):
        self.max_lessons_per_day                            = 3
        self.max_lessons_per_day_penalty                    = 1
        self.lessons_in_similar_day_and_ts_penalty          = 1
        self.lessons_in_similar_day_and_ts_all_as_soft      = False    # It can allow you to create schedule in case of non-norm plan, but it multiple time for solving
        
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

teacher_per_lesson_teacher = '_teacherid_'
teacher_per_lesson_lesson = '_forlesson_'
teachers_per_lesson_format =    teacher_per_lesson_lesson   + "%s"  +\
                                teacher_per_lesson_teacher  + "%d"


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
