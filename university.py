import numpy as np

from general_utils import group_prefix, type_prefix, RoomType

def list_intersection(lst1, lst2): 
    return set(lst1).intersection(lst2)

class Lesson:
    def __init__(self, lesson_name, group_indexes, count, lesson_type, teacher_indexes, self_index):
        self.lesson_name    = lesson_name
        self.group_indexes  = group_indexes
        self.count          = count
        self.lesson_type    = RoomType(lesson_type)
        self.teacher_indexes=teacher_indexes
        self.self_index     = self_index
        self.should_be_after=[]

    def __eq__(self, other):
        return self.full_name() == other.full_name()

    def full_name(self):
        ''' Lesson name + group name. Used as uniq index '''
        return self.lesson_name + group_prefix + str(self.group_indexes)  + type_prefix + str(self.lesson_type)

    def __str__(self):
        return self.full_name() + ' Count: ' + str(self.count) + ' Teachers: ' + str(self.teacher_indexes)
    
    def __repr__(self):
        return self.__str__()
    
    def total_size(self, groups):
        size = 0
        for group_index in self.group_indexes:
            size += groups[group_index].size

        return size

    def should_be_after_lessons(self, another_lesson):
        '''
        another_lesson is lesson, that should be before current:\n
        At any moment of time count of another_lessons >= count of self lessons
        for example:
            x - lecture (another lessons)
            y - practice (self)
            | - cut
                     |
            [x][ ][x]|[x][ ]
            [ ][y][ ]|[ ][y]
                     |
        However, it doesn't guarantee, that lessons should alternate
        '''
        if self.self_index == another_lesson.self_index:
            raise Exception("Can't create relations to self for lessons!")
        
        if len(list_intersection(self.group_indexes, another_lesson.group_indexes)) == 0:
            raise Exception("Lesson %s and %s don't have common groups!" % (self, another_lesson))

        self.should_be_after.append(another_lesson.self_index)

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

class Teacher:
    def __init__(self, full_name):
        self.name = full_name

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.__str__()

class University:
    def __init__(self):
        self.corpuses = {}
        self.lessons = []
        self.groups = []
        self.teachers = []

    def add_room(self, corpus_number, room_number, room_type, size):
        for _ in range(2):
            corpus = self.corpuses.get(corpus_number)
            if corpus is None:
                self.corpuses[corpus_number] = []

        for room in corpus:
            if room.room_number == room_number:
                raise BaseException("Room %d in corpus %d just exist!" % (room_number, corpus_number))

        corpus.append(Room(room_number, room_type, size))

    def add_group(self, group_name, size):
        for group in self.groups:
            if group.group_name == group_name:
                raise BaseException("WARNING: Group %s just exist! " % group_name)
        
        self.groups.append(Group(group_name, size))

    def add_lesson(self, lesson_name, group_names, count, lesson_type, teachers):
        '''
        Add lesson for study plan. \n
        Lesson name used as uniq index. \n
        Groups must have created for this moment! \n
        Teachers - list of compatible teachers for this lesson.
        '''
        group_indexes = []
        for group_i in range(len(self.groups)):
            if self.groups[group_i].group_name in group_names:
                group_indexes.append(group_i)

        if len(group_indexes) != len(group_names):
            raise BaseException("Some of groups from %s don't exist!" % group_names)
        
        teacher_indexes = []
        for teacher_name in teachers:
            find = False
            for teacher_i in range(len(self.teachers)):
                if self.teachers[teacher_i].name == teacher_name:
                    find = True
                    teacher_indexes.append(teacher_i)
                    break

            if find == False:
                raise BaseException('Teacher %s doesn\'t exist!' % teacher_name)
        
        new_lesson = Lesson(lesson_name, group_indexes, count, lesson_type, teacher_indexes, len(self.lessons))
        for i in range(len(self.lessons)):
            lesson = self.lessons[i]
            if lesson == new_lesson:
                raise BaseException('Lesson %s just exist!' % lesson)

        self.lessons.append(new_lesson)
        return self.lessons[-1]

    def add_teacher(self, name):
        for teacher in self.teachers:
            if teacher.name == name:
                raise BaseException('Teacher %s just exist!' % name)

        self.teachers.append(Teacher(name))

    def __str__(self):
        return "*****************************************************\n" + \
                "*** University INFO: *** \n" + \
                "Rooms by corpuses: " + str(self.corpuses) + "\n" + \
                "Lessons: " + str(self.lessons) + "\n" + \
                "Teachers: " + str(self.teachers) + "\n" + \
                "*****************************************************"
