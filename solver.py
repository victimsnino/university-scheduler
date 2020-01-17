import cplex
import re
from general_utils import * 
from university import University, Lesson
import copy

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

def _get_indexes_of_timeslots_by_filter(variables, week = None, day = None, corpus = None, room = None, timeslot = None, lesson = None, group_id = None, type = None, teacher_id = None):
    search = r'.*'
    if not week is None:
        search += week_prefix + str(week)
        search += r'.*'
    if not day is None:
        search += day_prefix + str(day)
        search += r'.*'
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
    if not teacher_id is None:
        search +=   teacher_prefix  + str(teacher_id)
        search += r'.*'

    return _get_indexes_by_name(variables, search, True)
    
    if not type is None:
        search += type_prefix + str(type)
        search += '.*'

def _get_variables_from_general_variable(variable):
    template = time_slot_format.replace("%d", r"(\d+)").replace("%s", "(.*)")
    finded = re.findall(template, variable)
    if len(finded) == 0:
        return []

    parsed = finded[0]
    week, day, corpus, room, ts, lesson,  group_ids,  _type, teacher = parsed
    week = int(week)
    day = int(day)
    ts = int(ts)
    group_ids = eval(group_ids)
    return [week, day, corpus, room, ts, lesson,  group_ids,  _type, teacher]

def _calculate_cost_of_lesson_by_position(variable):
    variables = _get_variables_from_general_variable(variable)
    if len(variables) == 0:
        raise Exception('Internal error')
    week, day, _, _, ts, _,  _,  _, _  = variables
    return 1+ts+global_config.time_slots_per_day_available*(day+week*global_config.study_days)


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
                for week_i in range(global_config.study_weeks):
                    for day_i in range(global_config.study_days):
                        for time_slot in range(global_config.time_slots_per_day_available):
                            indexes = []
                            for lesson in self.university.lessons:
                                if RoomType(lesson.lesson_type) not in RoomType(room.room_type):
                                    debug("Lesson skipped by TYPE: lesson %s room %s" % (lesson, room))
                                    continue

                                if room.size < lesson.total_size(self.university.groups):
                                    debug("Room size < lesson size: lesson %s room %s" % (lesson, room))
                                    continue

                                for teacher_i in lesson.teacher_indexes:
                                    indexes.append(self.model.variables.add(obj=[0],
                                                        lb=[0], 
                                                        ub=[1],
                                                        types=[self.model.variables.type.integer],
                                                        names=[time_slot_format % (week_i, day_i, corpus_i, room.room_number, time_slot, lesson.lesson_name, 
                                                                                    str(lesson.group_indexes), str(lesson.lesson_type), teacher_i)])[0])
                                
                            # each time-slot can have only 1 lesson
                            if len(indexes) != 0:
                                _add_constraint(self.model, indexes, '<=', 1)

        self.__fill_dummy_variables_for_tracking_corpuses()
            
    def __fill_dummy_variables_for_tracking_corpuses(self):
        ''' 
        Add dummy variables for corpus tracking (Group or teacher has lection in i-th corpus)
        '''
        for container, format_out, column in self.__get_groups_teachers_list():
            for corpus_i in self.university.corpuses:
                for week_i in range(global_config.study_weeks):
                    for day_i in range(global_config.study_days):
                        for ith in range(len(container)):
                            corpus_tracker_index = [self.model.variables.add(obj=[0],
                                                                            lb=[0], 
                                                                            ub=[1],
                                                                            types=[self.model.variables.type.integer],
                                                                            names=[format_out % ( corpus_i, week_i, day_i, ith)])[0]]

                            lections_indexes = eval('_get_indexes_of_timeslots_by_filter(self.model.variables, week=week_i, \
                                                    day = day_i, corpus = corpus_i, %s=ith)' % column)

                            _add_constraint(self.model, lections_indexes + corpus_tracker_index, '<=', 0, 
                                            [1]*len(lections_indexes)+[-1*global_config.time_slots_per_day_available])

                            _add_constraint(self.model, lections_indexes + corpus_tracker_index, '>=', -1*(global_config.time_slots_per_day_available-1), 
                                            [1]*len(lections_indexes)+[-1*global_config.time_slots_per_day_available])
                                
    def __constraint_total_count_of_lessons(self):
        ''' 
        Every lesson should have a count of lessons, which we request \n
        Therefore we should add constraints for it (count of all lessons in timeslots == requested)
        '''
        for lesson in self.university.lessons:
            _add_constraint(self.model, _get_indexes_by_name(self.model.variables, lesson_prefix+lesson.full_name()), '==', lesson.count)
        
        debug(self.model.variables.get_names())

    def __constraint_group_or_teacher_only_in_one_room_per_timeslot(self):
        for container, _, column in self.__get_groups_teachers_list():
            for ith in range(len(container)):
                for week_i in range(global_config.study_weeks):
                    for day_i in range(global_config.study_days):
                        for timeslot in range(global_config.time_slots_per_day_available):
                            _add_constraint(self.model, eval('_get_indexes_of_timeslots_by_filter(self.model.variables, week=week_i, \
                                                            day=day_i, timeslot=timeslot, %s=ith)' % column), '<=', 1)

    def __constraint_ban_changing_corpus_for_groups_or_teachers_during_day(self):
        for container, format_out, _ in self.__get_groups_teachers_list():
            for week_i in range(global_config.study_weeks):
                for day_i in range(global_config.study_days):
                    for ith in range(len(container)):
                        indexes = []
                        for corpus_i in self.university.corpuses:
                            indexes += _get_indexes_by_name(self.model.variables, format_out % ( corpus_i, week_i, day_i, ith))

                        _add_constraint(self.model, indexes, '<=', 1)

    def __constraint_max_lessons_per_day_for_teachers_or_groups(self):
        '''
        Every teacher or group can be busy only limited count of lections per day
        '''
        for container, _, column in self.__get_groups_teachers_list():
            for week_i in range(global_config.study_weeks):
                for day_i in range(global_config.study_days):
                    for ith in range(len(container)):
                        indexes = eval("_get_indexes_of_timeslots_by_filter(self.model.variables, week = week_i, day=day_i, %s=ith)" % column)
                        _add_constraint(self.model, indexes, '<=', global_config.max_lections_per_day)

    def __local_constraint_lesson_after_another_lesson(self):
        '''
        Some lessons should be after some another. For example, practice should be after lection. Therefore we should track it. \t
        Currnet code works this way: \t
        1) Find all indexes of original lesson and each for lessons, that should be before
        2) Calculate some 'cost' (ts+max_ts*(day+week*day))
        3) sum of costs original should be >= sum of costs lessons, that should be before
        '''
        for lesson in self.university.lessons:
            if len(lesson.should_be_after) == 0:
                continue

            original_indexes = _get_indexes_by_name(self.model.variables, lesson.full_name())
            original_val = [_calculate_cost_of_lesson_by_position(self.model.variables.get_names(i)) 
                            for i in original_indexes]

            for index_after in lesson.should_be_after:
                should_be_after_this = self.university.lessons[index_after]
                should_be_after_indexes = _get_indexes_by_name(self.model.variables, should_be_after_this.full_name())
                should_be_after_val = [-1*_calculate_cost_of_lesson_by_position(self.model.variables.get_names(i)) 
                                        for i in should_be_after_indexes]
                _add_constraint(self.model, original_indexes+should_be_after_indexes, '>=', 0, original_val+should_be_after_val)

    def solve(self):
        self.__fill_lessons_to_time_slots()

        self.__constraint_total_count_of_lessons()
        self.__constraint_group_or_teacher_only_in_one_room_per_timeslot()
        self.__constraint_ban_changing_corpus_for_groups_or_teachers_during_day()
        self.__constraint_max_lessons_per_day_for_teachers_or_groups()
        self.__local_constraint_lesson_after_another_lesson()

        self.model.set_results_stream(None) # ignore standart useless output
        self.model.solve()
        self.__parse_output_and_create_schedule()

    def __parse_output_and_create_schedule(self):
        # solution.get_status() returns an integer code
        print("Solution status = ",     self.model.solution.get_status(), ":", self.model.solution.status[self.model.solution.get_status()])
        if self.model.solution.get_status() != 1 and self.model.solution.get_status() != 101:
            return

        debug("Array of X = %s" %           self.model.solution.get_values())
        debug("Solution value  = %s" %      self.model.solution.get_objective_value())

        names = self.model.variables.get_names()
        values = self.model.solution.get_values()

        by_group = {}
        for i in range(len(values)):
            if values[i] == 0:
                continue
            
            variables = _get_variables_from_general_variable(names[i])
            if len(variables) == 0:
                continue

            week, day, corpus, room, ts, lesson,  group_ids,  _type, teacher = variables
            for group_id in group_ids:
                temp = by_group
                if not group_id in temp:
                    temp[group_id] = {}

                temp = temp[group_id]
                if not week in temp:
                    temp[week] = {}

                temp = temp[week]
                if not day in temp:
                    temp[day] = {}

                temp = temp[day]
                if not ts in temp:
                    temp[ts] = {}
                temp_list = copy.deepcopy(group_ids)
                temp_list.remove(group_id)
                temp[ts] = [int(corpus), int(room), lesson, _type, int(teacher), temp_list]

        for group, weeks in sorted(by_group.items()):
            for week, days in sorted(weeks.items()):
                for day, tss in sorted(days.items()):
                    for ts, listt in sorted(tss.items()):
                        corpus, room, lesson, _type, teacher, other_groups = listt
                        print("Groups %s \t Week %d\tDay %d Corpus %d  TS %d  room %d\tlesson %s\ttype %s\t\t With %s  \tteacher %s" % 
                              (group, week, day, corpus, ts, room, lesson, _type.split('.')[1], ",".join(str(i) for i in other_groups), self.university.teachers[teacher] ))

    def __get_groups_teachers_list(self):
        ''' Returns tuple of (container, format for corpus tracking, column for filter) '''
        return [(self.university.groups, corpus_tracker_of_groups_format, 'group_id'), 
                (self.university.teachers, corpus_tracker_of_teachers_format, 'teacher_id')]