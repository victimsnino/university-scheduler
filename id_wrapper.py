from general_utils import time_slot_format

def is_equal(left, right):
    return left == right or left == -1 or right == -1

class TimeSlotWrapper:
    def __init__(self, week=-1, day=-1, corpus=-1, room=-1, timeslot=-1,
                 lesson=-1, group_id=list(), type=-1, teacher_id=-1):
        self.week       = int(week)
        self.day        = int(day)
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
        equal = True
        equal = equal and is_equal(self.week,       other.week)
        equal = equal and is_equal(self.day,        other.day)
        equal = equal and is_equal(self.corpus,     other.corpus)
        equal = equal and is_equal(self.room,       other.room)
        equal = equal and is_equal(self.timeslot,   other.timeslot)
        equal = equal and is_equal(self.lesson,     other.lesson)
        equal = equal and is_equal(self.type,       other.type)
        equal = equal and is_equal(self.teacher_id, other.teacher_id)
        equal = equal and (len(self.group_id) == 0 or len(other.group_id) == 0 or all(elem in self.group_id  for elem in other.group_id)) 
        return equal
