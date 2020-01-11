import numpy as np

from general_utils import group_prefix, type_prefix, RoomType

class Lesson:
    def __init__(self, lesson_name, group_indexes, count, lesson_type):
        self.lesson_name    = lesson_name
        self.group_indexes  = group_indexes
        self.count          = count
        self.lesson_type    = RoomType(lesson_type)

    def __eq__(self, other):
        return self.full_name() == other.full_name()

    def full_name(self):
        ''' Lesson name + group name. Used as uniq index '''
        return self.lesson_name + '_' + group_prefix + '_' + str(self.group_indexes) + '_' + type_prefix + '_'+str(self.lesson_type)

    def __str__(self):
        return self.full_name() + ' Count: ' + str(self.count)
    
    def __repr__(self):
        return self.__str__()
    
    def total_size(self, groups):
        size = 0
        for group_index in self.group_indexes:
            size += groups[group_index].size

        return size

class Room:
    def __init__(self, room_number, room_type, size):
        self.room_number    = room_number
        self.room_type      = RoomType(room_type)
        self.size           = size

    def __str__(self):
        return str(self.room_number) + "_"+str(self.room_type)
    
    def __repr__(self):
        return self.__str__()

class Group:
    def __init__(self, group_name, size):
        self.group_name     = group_name
        self.size           = size

    def __str__(self):
        return self.group_name + "_size_"+str(self.size)
    
    def __repr__(self):
        return self.__str__()

class University:
    def __init__(self):
        self.corpuses = {}
        self.lessons = []
        self.groups = []

    def add_room(self, corpus_number, room_number, room_type, size):
        for _ in range(2):
            corpus = self.corpuses.get(corpus_number)
            if corpus is None:
                self.corpuses[corpus_number] = []

        corpus.append(Room(room_number, room_type, size))

    def add_group(self, group_name, size):
        for group in self.groups:
            if group.group_name == group_name:
                print("WARNING: Group %s just exist! " % group_name)
                return
        
        self.groups.append(Group(group_name, size))

    def add_lesson(self, lesson_name, group_names, count, lesson_type):
        group_indexes = []
        for group_i in range(len(self.groups)):
            if self.groups[group_i].group_name in group_names:
                group_indexes.append(group_i)

        if len(group_indexes) == 0:
            raise BaseException("Some of groups from %s don't exist!" % group_names)

        new_lesson = Lesson(lesson_name, group_indexes, count, lesson_type)
        for i in range(len(self.lessons)):
            lesson = self.lessons[i]
            if lesson == new_lesson:
                lesson.count += count
                return

        self.lessons.append(new_lesson)

    def __str__(self):
        return "*****************************************************\n" + \
                "*** University INFO: *** \n" + \
                "Rooms by corpuses: " + str(self.corpuses) + "\n" + \
                "Lessons: " + str(self.lessons) + "\n" + \
                "*****************************************************"
