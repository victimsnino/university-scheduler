import cplex
import re
from general_utils import * #debug, time_slots_per_day, RoomType, time_slot_format, lesson_prefix, group_prefix, timeslot_prefix, corpus_prefix, corpus_tracker_format
from university import University, Lesson

def _add_constraint(my_model, indexes_or_variables, sense, value, val = None):
    debug(str(indexes_or_variables) + str(sense) + str(value))

    valid_operations = ["<=", ">=", "=="]
    senses = ["L", "G", "E"]
    if sense not in valid_operations:
        raise BaseException("Not valid operation! %s" % sense)

    if val is None:
        val = [1.0]*len(indexes_or_variables)
    
    my_model.linear_constraints.add(lin_expr = [cplex.SparsePair(ind = indexes_or_variables, 
                                                                 val = val)], 
                                    senses = senses[valid_operations.index(sense)],
                                    rhs = [value])

def _get_indexes_by_name(variables, search, is_just_regex = False):
    if is_just_regex == False:
        search = r'.*' + search.replace('[', r'\[').replace(']', r'\]') + r'.*'
    debug('_get_indexes_by_name ' + search)
    indexes = []
    for name in variables.get_names():
        if not re.search(search, name) is None:
            debug('Matched! ' + name)
            indexes.append(variables.get_indices(name))
    return indexes

def _get_indexes_of_timeslots_by_filter(variables, corpus = None, room = None, timeslot = None, lesson = None, group_id = None, type = None):
    search = r'.*'
    if not corpus is None:
        search += corpus_prefix + str(corpus)
        search += r'.*'
    if not room is None:
        search += room_prefix + str(room)
        search += r'.*'
    if not timeslot is None:
        search += timeslot_prefix + str(timeslot)
        search += r'.*'
    if not lesson is None:
        search += lesson_prefix + str(timeslot)
        search += r'.*'
    if not group_id is None:
        search +=   group_prefix    + \
                    r'\[.*,? ?'     + \
                    str(group_id)   + \
                    r',? ?.*\]'
        search += r'.*'

    return _get_indexes_by_name(variables, search, True)
    
    if not type is None:
        search += type_prefix + str(type)
        search += '.*'

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

        self.__fill_tracking_variables_for_corpus()
            
    def __fill_tracking_variables_for_corpus(self):
        ''' 
        Add dummy variables for corpus tracking (Group has lection in this corpus)
        '''
        for corpus_i in self.university.corpuses:
            for group_i in range(len(self.university.groups)):
                corpus_tracker_index = [self.model.variables.add(obj=[0],
                                                                lb=[0], 
                                                                ub=[1],
                                                                types=[self.model.variables.type.integer],
                                                                names=[corpus_tracker_format % ( corpus_i, group_i)])[0]]

                lections_indexes = _get_indexes_of_timeslots_by_filter(self.model.variables, corpus = corpus_i, group_id=group_i)

                _add_constraint(self.model, lections_indexes + corpus_tracker_index, '<=', 0, 
                                [1]*len(lections_indexes)+[-1*time_slots_per_day])

                _add_constraint(self.model, lections_indexes + corpus_tracker_index, '>=', -1*(time_slots_per_day-1), 
                                [1]*len(lections_indexes)+[-1*time_slots_per_day])
                                
    def __constraint_total_count_of_lessons(self):
        ''' 
        Every lesson should have a count of lessons, which we request \n
        Therefore we should add constraints for it (count of all lessons in timeslots == requested)
        '''
        for lesson in self.university.lessons:
            _add_constraint(self.model, _get_indexes_by_name(self.model.variables, lesson_prefix+lesson.full_name()), '==', lesson.count)
        
        debug(self.model.variables.get_names())

    def __constraint_group_only_in_one_room_per_timeslot(self):
        for group_i in range(len(self.university.groups)):
            for timeslot in range(time_slots_per_day):
                _add_constraint(self.model, _get_indexes_of_timeslots_by_filter(self.model.variables, timeslot=timeslot, group_id=group_i), '<=', 1)

    def __constraint_ban_changing_corpus_during_day(self):
        for group_i in range(len(self.university.groups)):
            indexes = []

            for corpus_i in self.university.corpuses:
                indexes += _get_indexes_by_name(self.model.variables, corpus_tracker_format % ( corpus_i, group_i))

            _add_constraint(self.model, indexes, '<=', 1)

    def solve(self):
        self.__fill_lessons_to_time_slots()
        self.__constraint_total_count_of_lessons()
        self.__constraint_group_only_in_one_room_per_timeslot()
        self.__constraint_ban_changing_corpus_during_day()

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

            finded = re.findall(template, names[i])
            if len(finded) == 0:
                continue

            parsed = finded[0]
            debug(names[i] + '\t\t-> \t' +  str(parsed))
            print('Corpus %s Room %s TS %s Lesson %s Type: %s GroupIDs %s' % (parsed[0], parsed[1], parsed[2], parsed[3], parsed[5].split('.')[1], parsed[4]))
