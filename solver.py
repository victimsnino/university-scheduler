import cplex
import re
from general_utils import debug, time_slots_per_day, RoomType, time_slot_format, lesson_prefix
from university import University, Lesson

def _add_constraint(my_model, variables, sense, value):
    debug(str(variables) + str(sense) + str(value))

    valid_operations = ["<=", ">=", "=="]
    senses = ["L", "G", "E"]
    if sense not in valid_operations:
        raise BaseException("Not valid operation! %s" % sense)

    my_model.linear_constraints.add(lin_expr = [cplex.SparsePair(ind = variables, 
                                                                 val = [1.0]*len(variables))], 
                                    senses = senses[valid_operations.index(sense)],
                                    rhs = [value])

class Solver:
    def __init__(self, university):
        self.model = cplex.Cplex()
        self.university = university
        self.model.objective.set_sense(self.model.objective.sense.minimize)
    
    def __fill_lessons_to_time_slots(self):
        ''' 
        Fill base variables from our university structure to solver.
        ''' 
        for corpus_i in self.university.corpuses:
            for room in self.university.corpuses[corpus_i]:
                for time_slot in range(time_slots_per_day):
                    indexes = []
                    for lesson in self.university.lessons:
                        if RoomType(lesson.lesson_type) not in RoomType(room.room_type):
                            debug("Lesson skipped by TYPE: lesson %s room %s" % (lesson, room))
                            continue

                        if room.size < lesson.total_size(self.university.groups):
                            debug("Room size < lesson size: lesson %s room %s" % (lesson, room))
                            continue

                        indexes.append(self.model.variables.add(obj=[0],
                                            lb=[0], 
                                            ub=[1],
                                            types=[self.model.variables.type.integer],
                                            names=[time_slot_format % ( corpus_i, room.room_number, time_slot, lesson.lesson_name, 
                                                                        str(lesson.group_indexes), str(lesson.lesson_type))])[0])
                    
                    # each time-slot can have only 1 lesson
                    if len(indexes) != 0:
                        _add_constraint(self.model, indexes, '<=', 1)

    def __fill_lessons_constraints(self):
        ''' 
        Every lesson should have a count of lessons, which we request \n
        Therefore we should add constraints for it (count of all lessons in timeslots == requested)
        '''
        names = self.model.variables.get_names()

        for lesson in self.university.lessons:
            indexes = []
            for name in names:
                if lesson_prefix+'_'+lesson.full_name() in name:
                    indexes.append(self.model.variables.get_indices(name))
            _add_constraint(self.model, indexes, '==', lesson.count)
        
        debug(self.model.variables.get_names())

    def solve(self):
        self.__fill_lessons_to_time_slots()
        self.__fill_lessons_constraints()

        self.model.set_results_stream(None) # ignore standart useless output
        self.model.solve()
        self.__parse_output_and_create_schedule()

    def __parse_output_and_create_schedule(self):
        # solution.get_status() returns an integer code
        print("Solution status = ",     self.model.solution.get_status(), ":", self.model.solution.status[self.model.solution.get_status()])
        if self.model.solution.get_status() != 1 and self.model.solution.get_status() != 101:
            return

        print("Array of X = ",          self.model.solution.get_values())
        print("Solution value  = ",     self.model.solution.get_objective_value())

        names = self.model.variables.get_names()
        values = self.model.solution.get_values()
        template = time_slot_format.replace("%d", r"(\d+)").replace("%s", "(.*)")
        debug(template)
        for i in range(len(values)):
            if values[i] == 0:
                continue

            parsed = re.findall(template, names[i])[0]
            debug(names[i] + '\t\t-> \t' +  str(parsed))
            print('Corpus %s Room %s TS %s Lesson %s GroupIDs %s' % (parsed[0], parsed[1], parsed[2], parsed[3], parsed[4]))
