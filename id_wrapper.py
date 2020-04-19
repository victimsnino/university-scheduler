from general_utils import *

def _is_equal(left, right):
    return left == -1 or right == -1 or left == right 

class _WeekDayWrapper:
    def __init__(self, week=-1, day=-1):
        self.week = int(week)
        self.day  = int(day)

    def __eq__(self, other):
        return _is_equal(self.week, other.week) and _is_equal(self.day, other.day)

class _GroupIdOrTeacherIdWrapper:
    def __init__(self, group_id=-1, teacher_id=-1):
        if group_id != -1 and teacher_id != -1:
            raise Exception("only one field from group/teacher should pe filled")
        self.group_id   = int(group_id) if teacher_id == -1 else None
        self.teacher_id = int(teacher_id) if group_id == -1 else None

    def __eq__(self, other):
        return _is_equal(self.group_id, other.group_id) and _is_equal(self.teacher_id, other.teacher_id)

class TimeSlotWrapper(_WeekDayWrapper):
    def __init__(self, week=-1, day=-1, corpus=-1, room=-1, timeslot=-1,
                 lesson=-1, group_id=list(), type=-1, teacher_id=-1):
        _WeekDayWrapper.__init__(self, week, day)
        self.corpus     = int(corpus)
        self.room       = int(room)
        self.timeslot   = int(timeslot)
        self.lesson     = int(lesson)
        self.group_id   = group_id if isinstance(group_id, list) else [int(group_id)]
        self.type       = type
        self.teacher_id = int(teacher_id)

    def __str__(self):
        return time_slot_format % (self.week, self.day, self.corpus, self.room, self.timeslot, self.lesson,
                                  str(self.group_id), self.type, self.teacher_id)

    def __eq__(self, other):
        if not _WeekDayWrapper.__eq__(self, other):
            return False
        if not _is_equal(self.corpus,     other.corpus):
            return False
        if not _is_equal(self.room,       other.room):
            return False
        if not _is_equal(self.timeslot,   other.timeslot):
            return False
        if not _is_equal(self.lesson,     other.lesson):
            return False
        if not _is_equal(self.type,       other.type):
            return False
        if not _is_equal(self.teacher_id, other.teacher_id):
            return False
        return (len(self.group_id) == 0 or len(other.group_id) == 0 or all(elem in self.group_id  for elem in other.group_id)) 

_corpus_tracker_of_groups_format =   corpus_prefix    +   "%d"    +\
                                    week_prefix      +   "%d"    +\
                                    day_prefix       +   "%d"    +\
                                    group_prefix     +   "%d"

_corpus_tracker_of_teachers_format = corpus_prefix    +   "%d"    +\
                                    week_prefix      +   "%d"    +\
                                    day_prefix       +   "%d"    +\
                                    teacher_prefix   +   "%d"

class CorpusTrackerWrapper(_WeekDayWrapper, _GroupIdOrTeacherIdWrapper):
    def __init__(self, corpus=-1, week=-1, day=-1, group_id=-1, teacher_id=-1):        
        _WeekDayWrapper.__init__(self, week, day)
        _GroupIdOrTeacherIdWrapper.__init__(self, group_id, teacher_id)
        self.corpus     = int(corpus)

    def __str__(self):
        if self.group_id != -1 and self.group_id != None:
            return _corpus_tracker_of_groups_format % (self.corpus, self.week, self.day, self.group_id)
        elif self.teacher_id != -1 and self.teacher_id != None:
            return _corpus_tracker_of_teachers_format % (self.corpus, self.week, self.day, self.teacher_id)
        else:
            return (_corpus_tracker_of_groups_format+teacher_prefix+"%d") % (self.corpus, self.week, self.day, self.group_id, self.teacher_id)
    
    def __eq__(self, other):
        return  _is_equal(self.corpus, other.corpus) and \
                _WeekDayWrapper.__eq__(self, other)  and \
                _GroupIdOrTeacherIdWrapper.__eq__(self, other)

class RoomTrackerWrapper(CorpusTrackerWrapper):
    def __init__(self, room=-1, corpus=-1, week=-1, day=-1, group_id=-1, teacher_id=-1):
        CorpusTrackerWrapper.__init__(self, corpus=corpus, week=week, day=day, group_id=group_id, teacher_id=teacher_id)
        self.room = int(room)
    
    def __str__(self):
        return room_prefix + str(self.room) + CorpusTrackerWrapper.__str__(self)
    
    def __eq__(self, other):
        return _is_equal(self.room, other.room) and CorpusTrackerWrapper.__eq__(self, other)

lesson_id_per_day_base_tracker_format       =   week_prefix     +   "%d"    +\
                                                day_prefix      +   "%d"    +\
                                                lesson_prefix   +   "%d"

lesson_id_per_day_for_groups_tracker_format =   lesson_id_per_day_base_tracker_format   +\
                                                group_prefix    +   "%d"

lesson_id_per_day_for_teacher_tracker_format =  lesson_id_per_day_base_tracker_format   +\
                                                teacher_prefix  +   "%d"


class LessonTrackerWrapper(_WeekDayWrapper, _GroupIdOrTeacherIdWrapper):
    def __init__(self, week=-1, day=-1,lesson=-1, group_id=-1, teacher_id=-1):
        _WeekDayWrapper.__init__(self, week, day)
        _GroupIdOrTeacherIdWrapper.__init__(self, group_id, teacher_id)
        self.lesson = int(lesson)
    
    def __str__(self):
        if self.group_id != -1 and self.group_id != None:
            return lesson_id_per_day_for_groups_tracker_format % (self.week, self.day, self.lesson, self.group_id)
        elif self.teacher_id != -1 and self.teacher_id != None:
            return lesson_id_per_day_for_teacher_tracker_format % (self.week, self.day, self.lesson, self.teacher_id)
        else:
            return (lesson_id_per_day_for_groups_tracker_format+teacher_prefix+"%d") % (self.week, self.day, self.lesson, self.group_id, self.teacher_id)
    
    def __eq__(self, other):
        return  _is_equal(self.lesson, other.lesson) and \
                _WeekDayWrapper.__eq__(self, other)  and \
                _GroupIdOrTeacherIdWrapper.__eq__(self, other) 
