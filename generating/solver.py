import cplex
from general_utils import * 
from university import University, Lesson, Teacher
import copy
import progressbar
from functools import wraps
import warnings
import re




timeslots_filter_cache = {}

def _add_constraint(my_model, indexes_or_variables, sense, value, val = None):
    valid_operations = ["<=", ">=", "=="]
    senses = ["L", "G", "E"]
    if sense not in valid_operations:
        raise Exception("Not valid operation! %s" % sense)

    if len(indexes_or_variables) == 0:
        raise Exception('List of indexes is empty!')

    if val is None:
        val = [1.0]*len(indexes_or_variables)

    debug(str(indexes_or_variables) + sense + str(value))

    my_model.linear_constraints.add(lin_expr = [cplex.SparsePair(ind = indexes_or_variables, 
                                                                 val = val)], 
                                    senses = senses[valid_operations.index(sense)],
                                    rhs = [value])

def _get_indexes_by_name(variables, search, is_just_regex = False, source = None):
    if is_just_regex == False:
        search = r'^' + search.replace('[', r'\[').replace(']', r'\]') + r'$'

    indexes = []
    if source is None:
        source = variables.get_names()

    global timeslots_filter_cache
    cache = timeslots_filter_cache.setdefault(search, {}).setdefault(str(source), {})
    value = cache.get('cached_var', None)
    if not value is None:
        return value

    debug(search)
    data_regex = re.compile(search)

    for name in source:
        if not data_regex.match(name) is None:
            indexes.append(variables.get_indices(name))

    cache['cached_var'] = indexes

    return indexes

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
    lesson = int(lesson)
    group_ids = eval(group_ids)
    _type = eval(_type)
    return [week, day, corpus, room, ts, lesson,  group_ids,  _type, teacher]

def _calculate_cost_of_lesson_by_position(variable):
    variables = _get_variables_from_general_variable(variable)
    if len(variables) == 0:
        raise Exception('Internal error')
    week, day, _, _, ts, _,  _,  _, _  = variables
    return 1+ts+global_config.time_slots_per_day_available*(day+week*global_config.study_days)


def _get_time_slot_tracker_by_filter(variables, week_i =r'.*', day_i =r'.*', corpus_i =r'.*', room_i =r'.*', timeslot_i =r'.*', lesson_i =r'.*', group_i =r'.*', type_i =r'.*', teacher_i =r'.*', source = None):
	search=r'^'

	search += week_prefix       + str(week_i)
	search += day_prefix        + str(day_i)
	search += corpus_prefix     + str(corpus_i)
	search += room_prefix       + str(room_i)
	search += timeslot_prefix   + str(timeslot_i)
	search += lesson_prefix     + str(lesson_i)
	search += group_prefix      + r'\[.*,? ?' + str(group_i)+ r',? ?.*\]'
	search += type_prefix       + str(type_i)
	search += teacher_prefix    + str(teacher_i)

	search += r'$'

	if 'None' in search:
		raise Exception('None in search: '+search)
	return _get_indexes_by_name(variables, search, True, source)

def _get_corpus_tracker_by_filter(variables, corpus_i =r'.*', week_i =r'.*', day_i =r'.*', group_i =None, teacher_i =None, source = None):
	search=r'^'

	search += corpus_prefix     + str(corpus_i)
	search += week_prefix       + str(week_i)
	search += day_prefix        + str(day_i)
	if not group_i is None:
		search += group_prefix      + str(group_i)
	elif not teacher_i is None:
		search += teacher_prefix    + str(teacher_i)
	else:
		search += '_.*'

	search += r'$'

	if 'None' in search:
		raise Exception('None in search: '+search)
	return _get_indexes_by_name(variables, search, True, source)

def _get_room_tracker_by_filter(variables, room_i =r'.*', corpus_i =r'.*', week_i =r'.*', day_i =r'.*', group_i =None, teacher_i =None, source = None):
	search=r'^'

	search += room_prefix       + str(room_i)
	search += corpus_prefix     + str(corpus_i)
	search += week_prefix       + str(week_i)
	search += day_prefix        + str(day_i)
	if not group_i is None:
		search += group_prefix      + str(group_i)
	elif not teacher_i is None:
		search += teacher_prefix    + str(teacher_i)
	else:
		search += '_.*'

	search += r'$'

	if 'None' in search:
		raise Exception('None in search: '+search)
	return _get_indexes_by_name(variables, search, True, source)

def _get_lesson_id_per_day_tracker_by_filter(variables, week_i =r'.*', day_i =r'.*', lesson_i =r'.*', group_i =None, teacher_i =None, source = None):
	search=r'^'

	search += week_prefix       + str(week_i)
	search += day_prefix        + str(day_i)
	search += lesson_prefix     + str(lesson_i)
	if not group_i is None:
		search += group_prefix      + str(group_i)
	elif not teacher_i is None:
		search += teacher_prefix    + str(teacher_i)
	else:
		search += '_.*'

	search += r'$'

	if 'None' in search:
		raise Exception('None in search: '+search)
	return _get_indexes_by_name(variables, search, True, source)

def _get_teacher_per_lesson_tracker_by_filter(variables, lesson_i =r'.*', teacher_i =r'.*', source = None):
	search=r'^'

	search += lesson_prefix     + str(lesson_i)
	search += teacher_prefix    + str(teacher_i)

	search += r'$'

	if 'None' in search:
		raise Exception('None in search: '+search)
	return _get_indexes_by_name(variables, search, True, source)



def _for_corpuses(function):
    @wraps(function)
    def _decorator(self, **kwargs):
        for corpus_i in self.university.corpuses:
            function(self, corpus_i=corpus_i, **kwargs)
    return _decorator

def _for_week_and_day(function):
    @wraps(function)
    def _decorator(self, **kwargs):
        for week_i, day_i in self.university.study_weeks_and_days:
            function(self, week_i=week_i, day_i=day_i, **kwargs)
    return _decorator

def _for_week_only(function):
    @wraps(function)
    def _decorator(self, **kwargs):
        for week_i in range(self.university.study_weeks):
            function(self, week_i=week_i, **kwargs)
    return _decorator

def _for_day_only(function):
    @wraps(function)
    def _decorator(self, **kwargs):
        for day_i in self.university.study_days:
            function(self, day_i=day_i, **kwargs)
    return _decorator

def _for_timeslots(function):
    @wraps(function)
    def _decorator(self, **kwargs):
        for timeslot_i in range(global_config.time_slots_per_day_available):
            function(self, timeslot_i=timeslot_i, **kwargs)
    return _decorator

def _for_rooms(function):
    @wraps(function)
    def _decorator(self, **kwargs):
        for corpus_i in self.university.corpuses:
            for room in self.university.corpuses[corpus_i]:
                room_i=room.room_number
                function(self, corpus_i=corpus_i, room=room, room_i=room_i, **kwargs)
    return _decorator

def _for_groups_or_teachers(function):
    @wraps(function)
    def _decorator(self, **kwargs):
        for container, format_out, column in self._get_groups_teachers_list():
            for ith, teacher_or_group in enumerate(container):
                function(self, container=container, format_out=format_out, column=column, ith=ith, teacher_or_group=teacher_or_group, **kwargs)
    return _decorator

def _for_lessons(function):
    @wraps(function)
    def _decorator(self, **kwargs):
        for lesson_i, lesson in enumerate(self.university.lessons):
            function(self, lesson_i=lesson_i, lesson=lesson, **kwargs)
    return _decorator

def get_timeslots(function):
    @wraps(function)
    def _decorator(self, source=None,**kwargs):
        week_i       = kwargs.get('week_i', r'.*')
        day_i        = kwargs.get('day_i', r'.*')
        corpus_i     = kwargs.get('corpus_i', r'.*')
        room_i       = kwargs.get('room_i', r'.*')
        timeslot_i   = kwargs.get('timeslot_i', r'.*')
        lesson_i     = kwargs.get('lesson_i', r'.*')
        type_i       = kwargs.get('type_i', r'.*')
        column       = kwargs.get('column', None)
        ith          = kwargs.get('ith', None)

        indexes = _get_time_slot_tracker_by_filter(self.model.variables, week_i=week_i, day_i=day_i, corpus_i=corpus_i, room_i=room_i, timeslot_i=timeslot_i, lesson_i=lesson_i, type_i=type_i, source=source)
        source = self.model.variables.get_names(indexes)
        if column:
            indexes = eval('_get_time_slot_tracker_by_filter(self.model.variables, source=source,  %s=ith)' % column)
            source = self.model.variables.get_names(indexes)

        function(self, source=source, **kwargs)
    return _decorator

def get_corpus_tracker(function):
    @wraps(function)
    def _decorator(self, corpus_tracker_source=None,**kwargs):
        week_i       = kwargs.get('week_i', r'.*')
        day_i        = kwargs.get('day_i', r'.*')
        corpus_i     = kwargs.get('corpus_i', r'.*')
        column       = kwargs.get('column', None)
        ith          = kwargs.get('ith', None)

        indexes = _get_corpus_tracker_by_filter(self.model.variables, week_i=week_i, day_i=day_i, corpus_i=corpus_i, source=corpus_tracker_source)
        corpus_tracker_source = self.model.variables.get_names(indexes)
        if column:
            indexes = eval('_get_corpus_tracker_by_filter(self.model.variables, source=corpus_tracker_source,  %s=ith)' % column)
            corpus_tracker_source = self.model.variables.get_names(indexes)

        function(self, corpus_tracker_source=corpus_tracker_source, **kwargs)
    return _decorator

def get_room_tracker(function):
    @wraps(function)
    def _decorator(self, room_tracker_source=None,**kwargs):
        room_i       = kwargs.get('room_i', r'.*')
        week_i       = kwargs.get('week_i', r'.*')
        day_i        = kwargs.get('day_i', r'.*')
        corpus_i     = kwargs.get('corpus_i', r'.*')
        column       = kwargs.get('column', None)
        ith          = kwargs.get('ith', None)

        indexes = _get_room_tracker_by_filter(self.model.variables, room_i=room_i, week_i=week_i, day_i=day_i, corpus_i=corpus_i, source=room_tracker_source)
        room_tracker_source = self.model.variables.get_names(indexes)
        if column:
            indexes = eval('_get_room_tracker_by_filter(self.model.variables, source=room_tracker_source,  %s=ith)' % column)
            room_tracker_source = self.model.variables.get_names(indexes)

        function(self, room_tracker_source=room_tracker_source, **kwargs)
    return _decorator

def get_lesson_tracker(function):
    @wraps(function)
    def _decorator(self, lesson_tracker_source=None,**kwargs):
        week_i       = kwargs.get('week_i', r'.*')
        day_i        = kwargs.get('day_i', r'.*')
        lesson_i     = kwargs.get('lesson_i', r'.*')
        column       = kwargs.get('column', None)
        ith          = kwargs.get('ith', None)

        indexes = get_lesson_tracker_by_filter(self.model.variables, week_i=week_i, day_i=day_i, lesson_i=lesson_i, source=lesson_tracker_source)
        lesson_tracker_source = self.model.variables.get_names(indexes)
        if column:
            indexes = eval('get_lesson_tracker_by_filter(self.model.variables, source=lesson_tracker_source,  %s=ith)' % column)
            lesson_tracker_source = self.model.variables.get_names(indexes)

        function(self, lesson_tracker_source=lesson_tracker_source, **kwargs)
    return _decorator



class Solver:
    def __init__(self, university):
        self.model = cplex.Cplex()
        self.university = university
        self.model.objective.set_sense(self.model.objective.sense.minimize)
        #self.model.parameters.mip.strategy.search.set(1)
        self.model.parameters.simplex.limits.lowerobj.set(0)
        self.model.parameters.timelimit.set(global_config.timelimit_for_solve)
        
        global timeslots_filter_cache
        timeslots_filter_cache.clear()

    def _add_tracker_variable(self, name, source, max_value=global_config.time_slots_per_day_available):
        tracker_index = [self.model.variables.add(obj=[0],
                                                        lb=[0], 
                                                        ub=[1],
                                                        types=[self.model.variables.type.binary],
                                                        names=[name])[0]]


        _add_constraint(self.model, source + tracker_index, '<=', 0, 
                        [1]*len(source)+[-1*max_value])

        _add_constraint(self.model, source + tracker_index, '>=', -1*(max_value-1), 
                        [1]*len(source)+[-1*max_value])

#
    @_for_rooms
    @_for_week_and_day
    @_for_timeslots
    def __fill_lessons_to_time_slots(self, corpus_i=None, day_i=None, room=None, room_i=None, timeslot_i=None, week_i=None, **kwargs):

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
                                    types=[self.model.variables.type.binary],
                                    names=[time_slot_format % (week_i, day_i, corpus_i, room.room_number, timeslot_i, lesson.self_index, 
                                                                str(lesson.group_indexes), str(lesson.lesson_type), teacher_i)])[0])
            
        # each time-slot can have only 1 lesson
        if len(indexes) != 0:
            _add_constraint(self.model, indexes, '<=', 1)
        

    @_for_corpuses
    @get_timeslots
    @_for_week_and_day
    @get_timeslots
    @_for_groups_or_teachers
    @get_timeslots
    def __fill_dummy_variables_for_tracking_corpuses(self, column=None, container=None, corpus_i=None, day_i=None, format_out=None, ith=None, source=None, teacher_or_group=None, week_i=None, **kwargs):
        self._add_tracker_variable(format_out % ( corpus_i, week_i, day_i, ith), source)

    @_for_rooms
    @get_timeslots
    @_for_week_and_day
    @get_timeslots
    @_for_groups_or_teachers
    @get_timeslots
    def __fill_dummy_variables_for_tracking_rooms(self, column=None, container=None, corpus_i=None, day_i=None, format_out=None, ith=None, room=None, room_i=None, source=None, teacher_or_group=None, week_i=None, **kwargs):
        new_format = room_prefix + "%d" + format_out
        self._add_tracker_variable(new_format % (room_i, corpus_i, week_i, day_i, ith), source) 
        

    @_for_lessons
    @get_timeslots
    @_for_week_and_day
    @get_timeslots
    @_for_groups_or_teachers
    @get_timeslots
    def __fill_dummy_variables_for_tracking_lessons(self, column=None, container=None, day_i=None, format_out=None, ith=None, lesson=None, lesson_i=None, source=None, teacher_or_group=None, week_i=None, **kwargs):
        new_format = lesson_id_per_day_base_tracker_format + (group_prefix if column == 'group_i' else teacher_prefix) + '%d'
        self._add_tracker_variable(new_format % (week_i, day_i, lesson.self_index, ith), source) 
        

    @_for_lessons
    @get_timeslots
    def __fill_dummy_variables_for_tracking_teachers(self, lesson=None, lesson_i=None, source=None, **kwargs):
        for teacher_i in lesson.teacher_indexes:
                self._add_tracker_variable(teachers_per_lesson_format % (lesson.self_index, teacher_i), source, lesson.count)

    @_for_lessons
    @get_timeslots
    def __constraint_total_count_of_lessons(self, lesson=None, lesson_i=None, source=None, **kwargs):
        _add_constraint(self.model, source, '==', lesson.count)

    @_for_timeslots
    @get_timeslots
    @_for_week_and_day
    @get_timeslots
    @_for_groups_or_teachers
    @get_timeslots
    def __constraint_group_or_teacher_only_in_one_room_per_timeslot(self, column=None, container=None, day_i=None, format_out=None, ith=None, source=None, teacher_or_group=None, timeslot_i=None, week_i=None, **kwargs):
        _add_constraint(self.model, source, '<=', 1)

    @_for_week_and_day
    @get_corpus_tracker
    @_for_groups_or_teachers
    @get_corpus_tracker
    def __constraint_ban_changing_corpus_for_groups_or_teachers_during_day(self, column=None, container=None, corpus_tracker_source=None, day_i=None, format_out=None, ith=None, teacher_or_group=None, week_i=None, **kwargs):
        _add_constraint(self.model, corpus_tracker_source, '<=', 1)

    @_for_week_and_day
    @get_timeslots
    @_for_groups_or_teachers
    @get_timeslots
    def __constraint_max_lessons_per_day_for_teachers_or_groups(self, column=None, container=None, day_i=None, format_out=None, ith=None, source=None, teacher_or_group=None, week_i=None, **kwargs):
        _add_constraint(self.model, source, '<=', global_config.max_lessons_per_day)

    @_for_week_only
    @get_timeslots
    @_for_groups_or_teachers
    @get_timeslots
    def __constraint_max_lessons_per_week_for_teachers_or_groups(self, column=None, container=None, format_out=None, ith=None, source=None, teacher_or_group=None, week_i=None, **kwargs):
        _add_constraint(self.model, source, '<=', global_config.max_lessons_per_week)



    def solve(self):
        #self.model.set_results_stream(None) # ignore standart useless output
        if len(global_config.soft_constraints.timeslots_penalty) != global_config.time_slots_per_day_available:
            msg = 'Expected equality of len of timeslots_penalty and timee_slots_per_day_available. Len %s timeslots %s' % (len(global_config.soft_constraints.timeslots_penalty), global_config.time_slots_per_day_available)
            warnings.warn(msg)
            print(msg)
#
        methods=[self.__fill_lessons_to_time_slots, self.__fill_dummy_variables_for_tracking_corpuses, self.__fill_dummy_variables_for_tracking_rooms, self.__fill_dummy_variables_for_tracking_lessons, self.__fill_dummy_variables_for_tracking_teachers, self.__constraint_total_count_of_lessons, self.__constraint_group_or_teacher_only_in_one_room_per_timeslot, self.__constraint_ban_changing_corpus_for_groups_or_teachers_during_day, self.__constraint_max_lessons_per_day_for_teachers_or_groups, self.__constraint_max_lessons_per_week_for_teachers_or_groups, self.model.solve]
        for method in progressbar.progressbar(methods):
            print()
            print(method.__name__)
            method()
        
        debug(self.model.variables.get_names())
        output = self.__parse_output_and_create_schedule()
        return not output is None, output

    def __parse_output_and_create_schedule(self):
        print("Solution status = ",     self.model.solution.get_status(), ":", self.model.solution.status[self.model.solution.get_status()])
        if self.model.solution.get_status() in [1, 101, 107]:
            print("Value: ", self.model.solution.get_objective_value())
        else:
            return None

        debug("Array of X = %s" %           self.model.solution.get_values())
        debug("Solution value  = %s" %      self.model.solution.get_objective_value())

        names = self.model.variables.get_names()
        values = self.model.solution.get_values()

        by_group = {}
        for i, val in enumerate(values):
            if val == 0:
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
                temp[ts] = [int(corpus), int(room), self.university.lessons[lesson].lesson_name, _type, int(teacher), temp_list]

        for group, weeks in sorted(by_group.items()):
            for week, days in sorted(weeks.items()):
                for day, tss in sorted(days.items()):
                    for ts, listt in sorted(tss.items()):
                        corpus, room, lesson, _type, teacher, other_groups = listt
                        print("Groups %s      Week %d    Day %d Corpus %d  TS %d  room %d    lesson %s    type %s         With %s      teacher %s" % 
                              (group, week, day, corpus, ts, room, lesson, str(_type).split('.')[1], ",".join(str(i) for i in other_groups), self.university.teachers[teacher] ))

        return by_group
    
    def _get_groups_teachers_list(self):
        ''' Returns tuple of (container, format for corpus tracking, column for filter) '''
        return [(self.university.groups, corpus_tracker_of_groups_format, 'group_i'), 
                (self.university.teachers, corpus_tracker_of_teachers_format, 'teacher_i')]