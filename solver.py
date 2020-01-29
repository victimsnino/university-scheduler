import cplex
import re
from general_utils import * 
from university import University, Lesson, Teacher
import copy
import progressbar
from functools import wraps


timeslots_filter_cache = {}

def _add_constraint(my_model, indexes_or_variables, sense, value, val = None):
    valid_operations = ["<=", ">=", "=="]
    senses = ["L", "G", "E"]
    if sense not in valid_operations:
        raise Exception("Not valid operation! %s" % sense)

    if val is None:
        val = [1.0]*len(indexes_or_variables)
    
    my_model.linear_constraints.add(lin_expr = [cplex.SparsePair(ind = indexes_or_variables, 
                                                                 val = val)], 
                                    senses = senses[valid_operations.index(sense)],
                                    rhs = [value])

def _get_indexes_by_name(variables, search, is_just_regex = False, source = None):
    if is_just_regex == False:
        search = r'.*' + search.replace('[', r'\[').replace(']', r'\]') + r'.*'

    indexes = []
    if source is None:
        source = variables.get_names()
    for name in source:
        if not re.search(search, name) is None:
            indexes.append(variables.get_indices(name))
    return indexes

def _get_indexes_of_timeslots_by_filter(variables, week = None, day = None, corpus = None, 
                                        room = None, timeslot = None, lesson = None, group_id = None, 
                                        type = None, teacher_id = None, source = None):
    global timeslots_filter_cache
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
        search += lesson_prefix + str(lesson.replace('[', r'\[').replace(']', r'\]'))
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
    if not type is None:
        search += type_prefix + str(type)
        search += '.*'

    cached = timeslots_filter_cache.setdefault(week, {})
    cached = cached.setdefault(day, {})
    cached = cached.setdefault(corpus, {})
    cached = cached.setdefault(room, {})
    cached = cached.setdefault(timeslot, {})
    cached = cached.setdefault(lesson, {})
    cached = cached.setdefault(group_id, {})
    cached = cached.setdefault(type, {})
    cached = cached.setdefault(teacher_id, {})
    cached = cached.setdefault(str(source), {})
    if 'cache' in cached:
        return cached['cache']

    result = _get_indexes_by_name(variables, search, True, source)
    cached['cache'] = result

    return result
                        

def _get_corpus_tracker_by_filter(variables, corpus = None, week = None, day = None, group_id = None, teacher_id = None, source = None):
    search = r'.*'
    if not corpus is None:
        search += corpus_corpus_prefix + str(corpus)
        search += r'.*'
    if not week is None:
        search += corpus_week_prefix + str(week)
        search += r'.*'
    if not day is None:
        search += corpus_day_prefix + str(day)
        search += r'.*'
    if not group_id is None:
        search += corpus_group_prefix + str(group_id)
        search += r'.*'
    if not teacher_id is None:
        search += corpus_teacher_prefix + str(teacher_id)
        search += r'.*'

    return _get_indexes_by_name(variables, search, True, source)

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
    _type = eval(_type)
    return [week, day, corpus, room, ts, lesson,  group_ids,  _type, teacher]

def _calculate_cost_of_lesson_by_position(variable):
    variables = _get_variables_from_general_variable(variable)
    if len(variables) == 0:
        raise Exception('Internal error')
    week, day, _, _, ts, _,  _,  _, _  = variables
    return 1+ts+global_config.time_slots_per_day_available*(day+week*global_config.study_days)

#decorators

def _get_timeslots_for_corpuses(function):
    @wraps(function)
    def _decorator(self, source=None, **kwargs):
        for corpus_i in self.university.corpuses:
            temp = self.model.variables.get_names(_get_indexes_of_timeslots_by_filter(self.model.variables, corpus=corpus_i, source=source))
            function(self, temp, corpus_i=corpus_i, **kwargs)
    return _decorator

def _get_timeslots_for_week_and_day(function):
    @wraps(function)
    def _decorator(self, source=None, **kwargs):
        for week_i, day_i in self.university.study_weeks_and_days:
            temp = self.model.variables.get_names(_get_indexes_of_timeslots_by_filter(self.model.variables, week=week_i, day=day_i, source=source))
            function(self, temp, week_i=week_i, day_i=day_i, **kwargs)
    return _decorator

def _get_timeslots_for_week_only(function):
    @wraps(function)
    def _decorator(self, source=None, **kwargs):
        for week_i in range(self.university.study_weeks):
            temp = self.model.variables.get_names(_get_indexes_of_timeslots_by_filter(self.model.variables, week=week_i, source=source))
            function(self, temp, week_i=week_i, **kwargs)
    return _decorator

def _get_timeslots_for_timeslots(function):
    @wraps(function)
    def _decorator(self, source=None, **kwargs):
        for timeslot in range(global_config.time_slots_per_day_available):
            temp = self.model.variables.get_names(_get_indexes_of_timeslots_by_filter(self.model.variables, timeslot=timeslot, source=source))
            function(self, temp, timeslot=timeslot, **kwargs)
    return _decorator

def _get_corpus_tracker_for_week_and_day(function):
    @wraps(function)
    def _decorator(self, source=None, **kwargs):
        for week_i, day_i in self.university.study_weeks_and_days:
            temp = self.model.variables.get_names(_get_corpus_tracker_by_filter(self.model.variables, week=week_i, day=day_i, source=source))
            function(self, temp, week_i=week_i, day_i=day_i, **kwargs)
    return _decorator

class Solver:
    def __init__(self, university):
        self.model = cplex.Cplex()
        self.university = university
        self.model.objective.set_sense(self.model.objective.sense.minimize)
        
        global timeslots_filter_cache
        timeslots_filter_cache.clear()
    
    def __fill_lessons_to_time_slots(self):
        ''' 
        Fill base variables from our university structure to solver.
        ''' 
        for corpus_i in self.university.corpuses:
            for room in self.university.corpuses[corpus_i]:
                for week_i, day_i in self.university.study_weeks_and_days:
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

    
    @_get_timeslots_for_corpuses
    @_get_timeslots_for_week_and_day
    def __fill_dummy_variables_for_tracking_corpuses(self, source = None, week_i = None, day_i = None, corpus_i = None, **kwargs):
        ''' 
        Add dummy variables for corpus tracking (Group or teacher has lection in i-th corpus)
        '''
        for container, format_out, column in self.__get_groups_teachers_list():
            for ith in range(len(container)):
                corpus_tracker_index = [self.model.variables.add(obj=[0],
                                                                lb=[0], 
                                                                ub=[1],
                                                                types=[self.model.variables.type.integer],
                                                                names=[format_out % ( corpus_i, week_i, day_i, ith)])[0]]

                lections_indexes = eval('_get_indexes_of_timeslots_by_filter(self.model.variables, %s=ith, source=source)' % column)

                _add_constraint(self.model, lections_indexes + corpus_tracker_index, '<=', 0, 
                                [1]*len(lections_indexes)+[-1*global_config.time_slots_per_day_available])

                _add_constraint(self.model, lections_indexes + corpus_tracker_index, '>=', -1*(global_config.time_slots_per_day_available-1), 
                                [1]*len(lections_indexes)+[-1*global_config.time_slots_per_day_available])

    def __fill_dummy_variables_for_tracking_teachers(self):
        ''' 
        Add dummy variables for teachers tracking (which teachers marked for current lesson during module)
        '''
        for lesson in self.university.lessons:
            for teacher_i in lesson.teacher_indexes:
                teacher_tracker_index = [self.model.variables.add(obj=[0],
                                                                  lb=[0], 
                                                                  ub=[1],
                                                                  types=[self.model.variables.type.integer],
                                                                  names=[teachers_per_lesson_format % (lesson.full_name(), teacher_i)])[0]]


                lections_indexes = _get_indexes_of_timeslots_by_filter(self.model.variables, lesson=lesson.full_name(), teacher_id=teacher_i)

                _add_constraint(self.model, lections_indexes + teacher_tracker_index, '<=', 0, 
                                [1]*len(lections_indexes)+[-1*lesson.count])

                _add_constraint(self.model, lections_indexes + teacher_tracker_index, '>=', -1*(lesson.count-1), 
                                [1]*len(lections_indexes)+[-1*lesson.count])

    def __constraint_total_count_of_lessons(self):
        ''' 
        Every lesson should have a count of lessons, which we request \n
        Therefore we should add constraints for it (count of all lessons in timeslots == requested)
        '''
        for lesson in self.university.lessons:
            _add_constraint(self.model, _get_indexes_of_timeslots_by_filter(self.model.variables, lesson=lesson.full_name()), '==', lesson.count)

    @_get_timeslots_for_week_and_day
    @_get_timeslots_for_timeslots
    def __constraint_group_or_teacher_only_in_one_room_per_timeslot(self, source=None, **kwargs):
        for container, _, column in self.__get_groups_teachers_list():
            for ith in range(len(container)):
                    _add_constraint(self.model, eval('_get_indexes_of_timeslots_by_filter(self.model.variables, source=source, %s=ith)' % column), '<=', 1)

    @_get_corpus_tracker_for_week_and_day
    def __constraint_ban_changing_corpus_for_groups_or_teachers_during_day(self, source=None, **kwargs):
        for container, _, column in self.__get_groups_teachers_list():
            for ith in range(len(container)):
                indexes = []
                for corpus_i in self.university.corpuses:
                    indexes += eval('_get_corpus_tracker_by_filter(self.model.variables, source=source, corpus=corpus_i, %s=ith)'% column)

                _add_constraint(self.model, indexes, '<=', 1)

    @_get_timeslots_for_week_and_day
    def __constraint_max_lessons_per_day_for_teachers_or_groups(self, source=None, **kwargs):
        '''
        Every teacher or group can be busy only limited count of lessons per day
        '''
        for container, _, column in self.__get_groups_teachers_list():
            for ith in range(len(container)):
                indexes = eval("_get_indexes_of_timeslots_by_filter(self.model.variables, source=source, %s=ith)" % column)
                _add_constraint(self.model, indexes, '<=', global_config.max_lessons_per_day)
    
    @_get_timeslots_for_week_only
    def __constraint_max_lessons_per_week_for_teachers_or_groups(self, source=None, **kwargs):
        '''
        Every teacher or group can be busy only limited count of lessons per week
        '''
        for container, _, column in self.__get_groups_teachers_list():
            for ith in range(len(container)):
                indexes = eval("_get_indexes_of_timeslots_by_filter(self.model.variables, source=source, %s=ith)" % column)
                _add_constraint(self.model, indexes, '<=', global_config.max_lessons_per_week)

    def __local_constraint_lesson_after_another_lesson(self):
        '''
        Some lessons should be after some another. \n
        For example, practice should be after lection. Therefore we should track it.
        '''
        # practice
        for lesson in self.university.lessons:
            if len(lesson.should_be_after) == 0:
                continue

            original_indexes = _get_indexes_of_timeslots_by_filter(self.model.variables, lesson=lesson.full_name())
            original_indexes = sorted(original_indexes, key=lambda index: _calculate_cost_of_lesson_by_position(self.model.variables.get_names(index)))
            original_costs   = [_calculate_cost_of_lesson_by_position(self.model.variables.get_names(i)) for i in original_indexes]

            # lection
            for index_after in lesson.should_be_after:
                should_be_after_this = self.university.lessons[index_after]
                should_be_after_indexes = _get_indexes_of_timeslots_by_filter(self.model.variables, lesson=should_be_after_this.full_name())
                should_be_after_indexes = sorted(should_be_after_indexes, key=lambda index: _calculate_cost_of_lesson_by_position(self.model.variables.get_names(index)))
                after_costs   = [_calculate_cost_of_lesson_by_position(self.model.variables.get_names(i)) for i in should_be_after_indexes]
                set_after_costs = sorted(list(set(after_costs)))
                for cost in set_after_costs:
                    after_till_index = 0
                    while after_till_index < len(after_costs):
                        if after_costs[after_till_index] > cost:
                            break;
                        after_till_index += 1

                    original_till_index = 0
                    while original_till_index < len(original_costs):
                        if original_costs[original_till_index] > cost:
                            break;
                        original_till_index += 1
                    
                    _add_constraint(self.model, should_be_after_indexes[:after_till_index]+original_indexes[:original_till_index], '>=', 0,
                                    [float(lesson.count/should_be_after_this.count)]*after_till_index+[-1]*original_till_index)

    def __local_constraint_teacher_or_group_has_banned_ts(self):
        for container, _, column in self.__get_groups_teachers_list():
            for ith in range(len(container)):
                teacher_or_group = container[ith]
                for week, day, timeslot in teacher_or_group.banned_time_slots:
                    indexes = eval('_get_indexes_of_timeslots_by_filter(self.model.variables, week=week, day=day, timeslot=timeslot, %s=ith)' % column)
                    _add_constraint(self.model, indexes, '==', 0)

    @_get_timeslots_for_week_and_day
    def __constraint_ban_windows(self, source=None, **kwargs):
        '''
        Ban windows between lessons\n
        Take all combinations of length 3,4,5....,lessons_per_day and check, that it doesn't looks like 1,0.....,0,1
        '''
        if global_config.time_slots_per_day_available <= 2:
            return
        
        for container, _, column in self.__get_groups_teachers_list():
            for ith in range(len(container)):
                indexes_by_ts = []
                for timeslot in range(global_config.time_slots_per_day_available):
                    indexes_by_ts.append(eval('_get_indexes_of_timeslots_by_filter(self.model.variables, source=source, timeslot=timeslot, %s=ith)' % column))

                # select size of block for checking
                for max_timeslots in range(3, global_config.time_slots_per_day_available+1):
                    for ind in range(max_timeslots, global_config.time_slots_per_day_available+1):
                        val = []
                        temp_indexes = []
                        for ts in range(ind-max_timeslots, ind):
                            v =  1 if ts == (ind-max_timeslots) or ts == (ind-1) else -1
                            val += [v]*len(indexes_by_ts[ts])
                            temp_indexes += indexes_by_ts[ts]

                        _add_constraint(self.model, temp_indexes, '<=', 1, val)

    def __constraint_one_teacher_per_lessons(self):
        for lesson in self.university.lessons:
            indexes = []
            for teacher_i in lesson.teacher_indexes:
                indexes += _get_indexes_by_name(self.model.variables, teachers_per_lesson_format % (lesson.full_name(), teacher_i))

            _add_constraint(self.model, indexes, '<=', 1)

    def solve(self):

        for method in progressbar.progressbar([ self.__fill_lessons_to_time_slots,
                                                self.__fill_dummy_variables_for_tracking_corpuses,
                                                self.__fill_dummy_variables_for_tracking_teachers,
                                                self.__constraint_total_count_of_lessons,
                                                self.__constraint_group_or_teacher_only_in_one_room_per_timeslot,
                                                self.__constraint_ban_changing_corpus_for_groups_or_teachers_during_day,
                                                self.__constraint_max_lessons_per_day_for_teachers_or_groups,
                                                self.__constraint_max_lessons_per_week_for_teachers_or_groups,
                                                self.__local_constraint_lesson_after_another_lesson,
                                                self.__local_constraint_teacher_or_group_has_banned_ts,
                                                self.__constraint_ban_windows,
                                                self.__constraint_one_teacher_per_lessons]):
            print(method.__name__)
            method()
        

        debug(self.model.variables.get_names())

        self.model.set_results_stream(None) # ignore standart useless output
        self.model.solve()
        output = self.__parse_output_and_create_schedule()
        return not (self.model.solution.get_status() != 1 and self.model.solution.get_status() != 101), output

    def __parse_output_and_create_schedule(self):
        # solution.get_status() returns an integer code
        print("Solution status = ",     self.model.solution.get_status(), ":", self.model.solution.status[self.model.solution.get_status()])
        if self.model.solution.get_status() != 1 and self.model.solution.get_status() != 101:
            return None

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
                              (group, week, day, corpus, ts, room, lesson, str(_type).split('.')[1], ",".join(str(i) for i in other_groups), self.university.teachers[teacher] ))

        return by_group
    
    def __get_groups_teachers_list(self):   
        ''' Returns tuple of (container, format for corpus tracking, column for filter) '''
        return [(self.university.groups, corpus_tracker_of_groups_format, 'group_id'), 
                (self.university.teachers, corpus_tracker_of_teachers_format, 'teacher_id')]