import cplex
import numpy as np
from enum import Flag
import re

''' 
Done:
* Skipping by type of lesson and room type
* Skipping by size of room and lesson
* Constraint: 1 lessons in 1 timeslot
* Constraint: count of lessons == count of lessons in time-slots
'''


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

def debug(string):
    if DEBUG_PRINT == True:
        print("DEBUG: " + str(string))

class RoomType(Flag):
    COMPUTER    = 1
    LECTURE     = 2
    ALL         = COMPUTER | LECTURE

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

        self.model = cplex.Cplex()
        self.model.objective.set_sense(self.model.objective.sense.minimize)

    def add_room(self, corpus_number, room_number, room_type, size):
        for i in range(2):
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

    def _fill_lessons_to_time_slots(self):
        ''' 
        Fill base variables from our university structure to solver.
        ''' 
        for corpus_i in self.corpuses:
            for room in self.corpuses[corpus_i]:
                for time_slot in range(time_slots_per_day):
                    indexes = []
                    for lesson in university.lessons:
                        if lesson.lesson_type not in room.room_type:
                            debug("Lesson skipped by TYPE: lesson %s room %s" % (lesson, room))
                            continue

                        if room.size < lesson.total_size(self.groups):
                            debug("Room size < lesson size: lesson %s room %s" % (lesson, room))
                            continue

                        indexes.append(self.model.variables.add(obj=[0],
                                            lb=[0], 
                                            ub=[1],
                                            types=[self.model.variables.type.integer],
                                            names=[time_slot_format % ( corpus_i, room.room_number, time_slot, lesson.lesson_name, 
                                                                        str(lesson.group_indexes), str(lesson.lesson_type))])[0])
                    
                    # each time-slot can have only 1 lesson
                    _add_constraint(self.model, indexes, '<=', 1)

    def _fill_lessons_constraints(self):
        ''' 
        Every lesson should have a count of lessons, which we request \n
        Therefore we should add constraints for it (count of all lessons in timeslots == requested)
        '''
        names = self.model.variables.get_names()

        for lesson in self.lessons:
            indexes = []
            for name in names:
                if lesson_prefix+'_'+lesson.full_name() in name:
                    indexes.append(self.model.variables.get_indices(name))
            _add_constraint(self.model, indexes, '==', lesson.count)

    def solve(self):
        self.model.set_results_stream(None)
        self.model.solve()

    def __str__(self):
        return "*****************************************************\n" + \
                "*** University INFO: *** \n" + \
                "Rooms by corpuses: " + str(self.corpuses) + "\n" + \
                "Lessons: " + str(self.lessons) + "\n" + \
                "*****************************************************"

    def parse_output_and_create_schedule(self):
        # solution.get_status() returns an integer code
        print("Solution status = ",     self.model.solution.get_status(), ":", self.model.solution.status[self.model.solution.get_status()])
        if self.model.solution.get_status() != 1 and self.model.solution.get_status() != 101:
            return

        print("Array of X = ",          self.model.solution.get_values())
        print("Solution value  = ",     self.model.solution.get_objective_value())

        names = self.model.variables.get_names()
        values = self.model.solution.get_values()
        template = time_slot_format.replace("%d", "(\d+)").replace("%s", "(.*)")
        debug(template)
        for i in range(len(values)):
            if values[i] == 0:
                continue

            parsed = re.findall(template, names[i])[0]
            debug(names[i] + '\t\t-> \t' +  str(parsed))
            print('Corpus %s Room %s TS %s Lesson %s GroupIDs %s' % (parsed[0], parsed[1], parsed[2], parsed[3], parsed[4]))





def _add_constraint(my_model, variables, sense, value):
    debug(str(variables) + str(sense) + str(value))

    valid_operations = ["<=", ">=", "=="]
    senses = ["L", "G", "E"]
    if sense not in valid_operations:
        raise BaseException("Not valid operation!")

    my_model.linear_constraints.add(lin_expr = [cplex.SparsePair(ind = variables, 
                                                                 val = [1.0]*len(variables))], 
                                    senses = senses[valid_operations.index(sense)],
                                    rhs = [value])

def build_model_for_university(university):
    university._fill_lessons_to_time_slots()

    debug(university.model.variables.get_names())

    university._fill_lessons_constraints()
    university.solve()

if __name__ == "__main__":
    university = University()

    university.add_room(1, 320, RoomType.LECTURE, 38) 
    university.add_room(1, 321, RoomType.COMPUTER, 37) 
    university.add_room(1, 322, RoomType.LECTURE, 60) 

    university.add_group("16-pmi", 30)
    university.add_group("17-pmi", 20)

    university.add_lesson("матан", '16-pmi', 1, RoomType.LECTURE)
    university.add_lesson("матан", '16-pmi', 2, RoomType.LECTURE) # summarize with above
    university.add_lesson("матан", '17-pmi', 1, RoomType.COMPUTER)
    university.add_lesson("матан", ['17-pmi', '16-pmi'], 1, RoomType.LECTURE)

    print(university)
    build_model_for_university(university)
    university.parse_output_and_create_schedule()

