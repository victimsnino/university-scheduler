import cplex
import re
from general_utils import * 
from university import University, Lesson, Teacher
import copy
import progressbar
from functools import wraps
import warnings
import numpy as np
import math

from id_wrapper import TimeSlotWrapper
from concurrent.futures import ThreadPoolExecutor 
import multiprocessing

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

def _add_soft_constraint(my_model, indexes_or_variables, sense, value, vals, penalty, val_for_new_variable, name=None, ub = None):
    if penalty > 0: # A.K.A soft constraint
        indexes_or_variables.append(my_model.variables.add(   obj=[penalty],
                                                        lb=[0],
                                                        ub =[ub] if ub else None,
                                                        names=[name] if name else None,
                                                        types=[my_model.variables.type.integer])[0])
        vals.append(val_for_new_variable)

    _add_constraint(my_model, indexes_or_variables, sense, value, vals)

def calculate_valid(data_regex, source):
    def process_part(data_regex, temp_data):
        return [i for i in temp_data if data_regex.match(i)]
    
    #if len(source) < 800:
    return process_part(data_regex, source)
        
    threads = 2
    part = int(len(source)/threads)

    futures = []
    with ThreadPoolExecutor(threads) as executor:
        for thread in range(threads):
            min = thread*part
            max = (thread+1)*part
            if thread == threads-1:
                max = len(source)
            temp_source = source[min:max]
            futures.append(executor.submit(process_part, data_regex, temp_source))
        output = []
        for res in futures:
            output += res.result()
    return output

def _get_indexes_by_name(variables, search, is_just_regex = False, source = None):
    if is_just_regex == False:
        search = r'^' + search.replace('[', r'\[').replace(']', r'\]') + r'$'

    if source is None:
        source = variables.get_names()

    global timeslots_filter_cache
    cache = timeslots_filter_cache.setdefault(search, {}).setdefault(str(source), {})
    value = cache.get('cached_var', None)
    if not value is None:
        return copy.deepcopy(value)

    debug(search)
    data_regex = re.compile(search)

    indexes = calculate_valid(data_regex, source)

    #indexes = [source[i] for i, is_valid in enumerate(valid) if is_valid]
    cache['cached_var'] = indexes

    return copy.deepcopy(indexes)

def _get_indexes_of_timeslots_by_filter(solver, week = -1, day = -1, corpus = -1, 
                                        room = -1, timeslot = -1, lesson = -1, group_id = list(), 
                                        type = -1, teacher_id = -1, source = None):

    target = TimeSlotWrapper(week, day, corpus, room, timeslot, lesson, group_id, type, teacher_id)
    if source is None:
        source = list(solver.timeslots.keys())

    out = []
    for index in source:
        if index in solver.timeslots and solver.timeslots[index] == target:
            out.append(index)
            pass
    
    return out[:len(out)]
                        
def _get_corpus__or_room_tracker_by_filter(variables, room = None, corpus = r'.*', week = r'.*', day = r'.*', group_id = None, teacher_id = None, source = None):
    search = r'^'
    if room:
        search += room_prefix + str(room)

    search += corpus_prefix   + str(corpus)
    search += week_prefix    + str(week)
    search += day_prefix     + str(day)
    if not group_id is None:
        search += group_prefix + str(group_id)
    elif not teacher_id is None:
        search += teacher_prefix + str(teacher_id)
    else:
        search += '_.*'
   
    search += r'$'

    if 'None' in search:
        raise Exception('None in search: '+search)

    return _get_indexes_by_name(variables, search, True, source)

def get_lesson_tracker_by_filter(variables, week = r'.*', day = r'.*', lesson_id = r'.*', group_id = None, teacher_id = None, source = None):
    search = r'^'
    search += week_prefix    + str(week)
    search += day_prefix     + str(day)
    search += lesson_prefix  + str(lesson_id)
    if not group_id is None:
        search += group_prefix + str(group_id)
    elif not teacher_id is None:
        search += teacher_prefix + str(teacher_id)
    else:
        search += '_.*'
   
    search += r'$'

    if 'None' in search:
        raise Exception('None in search: '+search)

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

##################### decorators ########################
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
        for timeslot in range(global_config.time_slots_per_day_available):
            function(self, timeslot=timeslot, **kwargs)
    return _decorator

def _for_rooms(function):
    @wraps(function)
    def _decorator(self, **kwargs):
        for corpus_i in self.university.corpuses:
            for room in self.university.corpuses[corpus_i]:
                function(self, room_i = room.room_number, corpus_i=corpus_i, **kwargs)
    return _decorator

def _for_groups_or_teachers(function):
    @wraps(function)
    def _decorator(self, **kwargs):
        for container, format_out, column in self._get_groups_teachers_list():
            for ith, teacher_or_group in enumerate(container):
                function(self, ith=ith, format_out=format_out, teacher_or_group=teacher_or_group, column=column, **kwargs)
    return _decorator

def _for_lessons(function):
    @wraps(function)
    def _decorator(self, **kwargs):
        for lesson_i, lesson in enumerate(self.university.lessons):
            function(self, lesson=lesson, lesson_i=lesson_i, **kwargs)
    return _decorator

# required to put it after @_for_groups_or_teachers
def _for_lessons_with_friends(function):
    @wraps(function)
    def _decorator(self, **kwargs):
        for lesson_i, lesson in enumerate(self.university.lessons):
            function(self, lesson=lesson, lesson_i=lesson_i, friends_enabled=True, **kwargs)
    return _decorator

#########################################

def _get_indexes_with_friends(list_of_friends):
    def wrapper(function):
        @wraps(function)
        def _decorator(self, lesson):
            indexes = function(self, lesson)
            for friend_lesson in list_of_friends:
                indexes += function(self, friend_lesson)
            return indexes
        return _decorator
    return wrapper

########################################
def get_timeslots(function):
    @wraps(function)
    def _decorator(self, source=None, **kwargs):
        week            = kwargs.get('week_i', -1)
        day             = kwargs.get('day_i', -1)
        corpus          = kwargs.get('corpus_i', -1)
        room            = kwargs.get('room_i', -1)
        timeslot        = kwargs.get('timeslot', -1)
        lesson_i        = kwargs.get('lesson_i', -1)
        type            = kwargs.get('type', -1)
        column          = kwargs.get('column', None)
        ith             = kwargs.get('ith', None)
        friends_enabled = kwargs.get('friends_enabled', False)

        friend_indexes = []
        if friends_enabled:
            if column is None or ith is None:
                raise Exception("teacher or group must be not None in case of using 'friends'")
            
            if self.university.is_teacher_or_group_in_lesson(lesson_i, ith, column == 'teacher_id'):
                friend_indexes = self.university.get_friend_indexes(lesson_i, ith, column == 'teacher_id')
        
        @_get_indexes_with_friends(friend_indexes)
        def get_indexes(self, lesson):
            indexes = _get_indexes_of_timeslots_by_filter(self, source=source, week=week, day=day, corpus=corpus, room=room, timeslot=timeslot, lesson=lesson, type=type)
            if column:
                indexes = eval('_get_indexes_of_timeslots_by_filter(self, source = indexes, %s=ith)' % column)
                ith # needed for capturing it inside functon
            return indexes

        indexes = get_indexes(self, lesson_i)

        function(self, source=indexes, **kwargs)
    return _decorator

##########################################

def get_corpus_tracker(function):
    @wraps(function)
    def _decorator(self, corpus_tracker_source=None, **kwargs):
        week        = kwargs.get('week_i', r'.*')
        day         = kwargs.get('day_i', r'.*')
        corpus      = kwargs.get('corpus_i', r'.*')
        column      = kwargs.get('column', None)
        ith         = kwargs.get('ith', None)

        indexes = _get_corpus__or_room_tracker_by_filter(self.model.variables, corpus=corpus, week=week, day=day, source=corpus_tracker_source)
        if column:
            indexes = eval('_get_corpus__or_room_tracker_by_filter(self.model.variables, source=indexes, %s=ith)' % column)

        function(self, corpus_tracker_source=indexes, **kwargs)
    return _decorator

##########################################

def get_room_tracker(function):
    @wraps(function)
    def _decorator(self, room_tracker_source=None, **kwargs):
        room        = kwargs.get('room_i', r'.*')
        week        = kwargs.get('week_i', r'.*')
        day         = kwargs.get('day_i', r'.*')
        corpus      = kwargs.get('corpus_i', r'.*')
        column      = kwargs.get('column', None)
        ith         = kwargs.get('ith', None)

        indexes = _get_corpus__or_room_tracker_by_filter(self.model.variables, room=room, corpus=corpus, week=week, day=day, source=room_tracker_source)
        if column:
            indexes = eval('_get_corpus__or_room_tracker_by_filter(self.model.variables, room=room, source=indexes, %s=ith)' % column)

        function(self, room_tracker_source=indexes, **kwargs)
    return _decorator

###########################################

def get_lesson_tracker(function):
    @wraps(function)
    def _decorator(self, lesson_tracker_source=None, **kwargs):
        week        = kwargs.get('week_i', r'.*')
        day         = kwargs.get('day_i', r'.*')
        lesson_id   = kwargs.get('lesson_i', r'.*')
        column      = kwargs.get('column', None)
        ith         = kwargs.get('ith', None)

        @_get_indexes_with_friends([] )# kwargs.get('friends_indexes', []))
        def get_indexes(self, lesson_id):
            indexes = get_lesson_tracker_by_filter(self.model.variables, week=week, day=day, lesson_id=lesson_id, source=lesson_tracker_source)
            if column:
                indexes = eval('get_lesson_tracker_by_filter(self.model.variables, source=indexes, %s=ith)' % column)
                ith # needed for capturing it inside functon 
            return indexes

        indexes = get_indexes(self, lesson_id)
        function(self, lesson_tracker_source=indexes, **kwargs)
    return _decorator


###################


class Solver:
    def __init__(self, university):
        self.model = cplex.Cplex()
        self.university = university
        self.model.objective.set_sense(self.model.objective.sense.minimize)
        #self.model.parameters.mip.strategy.search.set(1)
        self.model.parameters.simplex.limits.lowerobj.set(0)
        if global_config.timelimit_for_solve > 0:
            self.model.parameters.timelimit.set(global_config.timelimit_for_solve)
        
        global timeslots_filter_cache
        timeslots_filter_cache.clear()
        self.timeslots = {}

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
                                name = time_slot_format % (week_i, day_i, corpus_i, room.room_number, time_slot, lesson.self_index, 
                                                                                str(lesson.group_indexes), str(lesson.lesson_type), teacher_i)
                                indexes.append(self.model.variables.add(obj=[0],
                                                    lb=[0], 
                                                    ub=[1],
                                                    types=[self.model.variables.type.binary],
                                                    names=[name])[0])
                                self.timeslots[name] = TimeSlotWrapper(week_i, day_i, corpus_i, room.room_number, time_slot, lesson.self_index, 
                                                                                lesson.group_indexes, lesson.lesson_type, teacher_i)
                            
                        # each time-slot can have only 1 lesson
                        if len(indexes) != 0:
                            _add_constraint(self.model, indexes, '<=', 1)


    def __fill_variables_helper(self, name, source, max_limit):
        tracker_index  = [self.model.variables.add(obj=[0],
                                                    lb=[0], 
                                                    ub=[1],
                                                    types=[self.model.variables.type.binary],
                                                    names=[name])[0]]

        _add_constraint(self.model, source + tracker_index, '<=', 0, 
                        [1]*len(source)+[-1*max_limit])

        _add_constraint(self.model, source + tracker_index, '>=', -1*(max_limit-1), 
                        [1]*len(source)+[-1*max_limit])

    @_for_corpuses
    @get_timeslots
    @_for_week_and_day
    @get_timeslots
    @_for_groups_or_teachers
    @get_timeslots
    def __fill_dummy_variables_for_tracking_corpuses(self, source = None, week_i = None, day_i = None, corpus_i = None, format_out = None, ith=None,  **kwargs):
        ''' 
        Add dummy variables for corpus tracking (Group or teacher has lection in i-th corpus)
        '''
        self.__fill_variables_helper(format_out % ( corpus_i, week_i, day_i, ith), source, global_config.time_slots_per_day_available)

    
    @_for_rooms
    @get_timeslots
    @_for_week_and_day
    @get_timeslots
    @_for_groups_or_teachers
    @get_timeslots
    def __fill_dummy_variables_for_tracking_rooms(self, source = None, week_i = None, day_i = None, corpus_i = None, room_i = None, format_out = None, ith=None,  **kwargs):
        ''' 
        Add dummy variables for corpus tracking (Group or teacher has lection in i-th corpus)
        '''
        new_format = room_prefix + "%d" + format_out
        self.__fill_variables_helper(new_format % (room_i, corpus_i, week_i, day_i, ith), source, global_config.time_slots_per_day_available)

    
    @_for_lessons
    @get_timeslots
    @_for_week_and_day
    @get_timeslots
    @_for_groups_or_teachers
    @get_timeslots
    def __fill_dummy_variables_for_tracking_lessons(self, source = None, week_i = None, day_i = None, lesson = None, column = None, ith=None,  **kwargs):
        new_format = lesson_id_per_day_base_tracker_format + (group_prefix if column == 'group_id' else teacher_prefix) + '%d'
        self.__fill_variables_helper(new_format % (week_i, day_i, lesson.self_index, ith), source, global_config.time_slots_per_day_available)


    @_for_lessons
    @get_timeslots
    def __fill_dummy_variables_for_tracking_teachers(self, source = None, lesson=None, **kwargs):
        ''' 
        Add dummy variables for teachers tracking (which teachers marked for current lesson during module)
        '''
        for teacher_i in lesson.teacher_indexes:
            lections_indexes = _get_indexes_of_timeslots_by_filter(self, source=source, teacher_id=teacher_i)
            self.__fill_variables_helper(teachers_per_lesson_format % (lesson.self_index, teacher_i), lections_indexes, lesson.get_count())

    @_for_lessons
    @get_timeslots
    def __constraint_total_count_of_lessons(self, source = None, lesson = None, **kwargs):
        ''' 
        Every lesson should have a count of lessons, which we request \n
        Therefore we should add constraints for it (count of all lessons in timeslots == requested)
        '''
        _add_constraint(self.model, source, '==', lesson.get_count())

    @_for_timeslots
    @get_timeslots
    @_for_week_and_day
    @get_timeslots
    @_for_groups_or_teachers
    @get_timeslots
    def __constraint_group_or_teacher_only_in_one_room_per_timeslot(self, source=None, **kwargs):
        _add_constraint(self.model, source, '<=', 1)

    @_for_week_and_day
    @get_corpus_tracker
    @_for_groups_or_teachers
    @get_corpus_tracker
    def __constraint_ban_changing_corpus_for_groups_or_teachers_during_day(self, corpus_tracker_source=None, **kwargs):
        _add_constraint(self.model, corpus_tracker_source, '<=', 1)

    @_for_week_and_day
    @get_timeslots
    @_for_groups_or_teachers
    @get_timeslots
    def __constraint_max_lessons_per_day_for_teachers_or_groups(self, source=None, **kwargs):
        '''
        Every teacher or group can be busy only limited count of lessons per day
        '''
        _add_constraint(self.model, source, '<=', global_config.max_lessons_per_day)
    
    @_for_week_only
    @get_timeslots
    @_for_groups_or_teachers
    @get_timeslots
    def __constraint_max_lessons_per_week_for_teachers_or_groups(self, source=None, **kwargs):
        '''
        Every teacher or group can be busy only limited count of lessons per week
        '''
        _add_constraint(self.model, source, '<=', global_config.max_lessons_per_week)

    def __local_constraint_lesson_after_another_lesson(self):
        '''
        Some lessons should be after some another. \n
        For example, practice should be after lection. Therefore we should track it.
        '''
        def get_sorted_indexes_and_costs(self, lesson_i):
            original_indexes = _get_indexes_of_timeslots_by_filter(self, lesson=str(lesson_i))
            original_indexes = sorted(original_indexes, key=lambda index: _calculate_cost_of_lesson_by_position(index))
            original_costs   = [_calculate_cost_of_lesson_by_position(i) for i in original_indexes]
            return original_indexes, original_costs

        def fill_at_any_moment_lections_ge_practices(self, original_costs, after_costs, original_indexes, should_be_after_indexes):
            def get_greater_index(costs, cost):
                index = 0
                while index < len(costs):
                    if costs[index] > cost:
                        break
                    index += 1
                return index

            set_after_costs = sorted(list(set(after_costs)))
            for cost in set_after_costs:
                after_till_index    = get_greater_index(after_costs, cost)
                original_till_index = get_greater_index(original_costs, cost)
                
                indexes = should_be_after_indexes[:after_till_index]+original_indexes[:original_till_index]
                vals = [float(lesson.get_count()/should_be_after_this.get_count())]*after_till_index+[-1]*original_till_index
                _add_soft_constraint(self.model, indexes, '>=', 0, vals, 1, 1, 'Less after less min')
                _add_soft_constraint(self.model, indexes, '<=', 2, vals, 1, -1, 'Less after less max')

        # practice
        for lesson_i, lesson in enumerate(self.university.lessons):
            if len(lesson.should_be_after) == 0:
                continue

            original_indexes, original_costs = get_sorted_indexes_and_costs(self, lesson_i)

            # lection
            for index_after in lesson.should_be_after:
                should_be_after_this = self.university.lessons[index_after]
                should_be_after_indexes, after_costs = get_sorted_indexes_and_costs(self, should_be_after_this.self_index)

                fill_at_any_moment_lections_ge_practices(self, original_costs, after_costs, original_indexes, should_be_after_indexes)

    @_for_groups_or_teachers
    @get_timeslots
    def __local_constraint_teacher_or_group_has_banned_ts(self, source = None, teacher_or_group = None, **kwargs):
        for week, day, timeslot in teacher_or_group.banned_time_slots:
            if week is None:
                week = -1
            elif week >= self.university.study_weeks:
                continue

            if day is None:
                day = -1
            elif day >= global_config.study_days:
                continue

            if timeslot is None:
                timeslot = -1
            elif timeslot >= global_config.time_slots_per_day_available:
                continue

            indexes = _get_indexes_of_timeslots_by_filter(self, week=week, day=day, timeslot=timeslot, source=source)
            _add_constraint(self.model, indexes, '==', 0)

    def __ban_windows(self, source, penalty):
        indexes_by_ts = []
        for timeslot in range(global_config.time_slots_per_day_available):
            indexes_by_ts.append(_get_indexes_of_timeslots_by_filter(self, source=source, timeslot=timeslot))

        # select size of block for checking
        for max_timeslots in range(3, global_config.time_slots_per_day_available+1):
            for ind in range(max_timeslots, global_config.time_slots_per_day_available+1):
                val = []
                temp_indexes = []
                for ts in range(ind-max_timeslots, ind):
                    v =  1 if ts == (ind-max_timeslots) or ts == (ind-1) else -1
                    val += [v]*len(indexes_by_ts[ts])
                    temp_indexes += indexes_by_ts[ts]

                _add_soft_constraint(self.model, temp_indexes, '<=', 1, val, penalty*(penalty>0)*(max_timeslots-2), -1, 'Ban_windows', 1)

    @_for_week_and_day
    @get_timeslots
    @_for_groups_or_teachers
    @get_timeslots
    def __constraint_ban_windows(self, source=None, column = None, **kwargs):
        '''
        Ban windows between lessons\n
        Take all combinations of length 3,4,5....,lessons_per_day and check, that it doesn't looks like 1,0.....,0,1
        '''
        if global_config.time_slots_per_day_available <= 2 or global_config.windows_penalty == 0:
            return
        
        penalty = global_config.windows_penalty
        if column == 'group_id':
            penalty *= global_config.windows_groups_multiplier
        
        self.__ban_windows(source, penalty)
    
    def __constraint_one_teacher_per_lessons(self):
        for lesson in self.university.lessons:
            indexes = []
            for teacher_i in lesson.teacher_indexes:
                indexes += _get_indexes_by_name(self.model.variables, teachers_per_lesson_format % (lesson.self_index, teacher_i))

            _add_constraint(self.model, indexes, '<=', 1)

    @_for_week_and_day
    @get_timeslots
    @_for_groups_or_teachers
    @get_timeslots
    def __soft_constraint_max_lessons_per_day(self, source=None, teacher_or_group = None, week_i = None, day_i = None, **kwargs):
        if  global_config.soft_constraints.max_lessons_per_day_penalty <= 0 or \
            global_config.soft_constraints.max_lessons_per_day <= 0 or  \
            global_config.soft_constraints.max_lessons_per_day >= global_config.time_slots_per_day_available:
            return
        name = "MaxLessons {0} w{1} d{2}".format(str(teacher_or_group), week_i, day_i)
        for excess_lessons_per_day in range(global_config.soft_constraints.max_lessons_per_day, global_config.time_slots_per_day_available):
            vals = [1]*len(source)
            penalty = excess_lessons_per_day*global_config.soft_constraints.max_lessons_per_day_penalty
            _add_soft_constraint(self.model, copy.deepcopy(source), '<=', excess_lessons_per_day, vals, penalty, -1, name, ub=global_config.time_slots_per_day_available)

    @_for_week_and_day
    @get_timeslots
    @_for_groups_or_teachers
    @get_timeslots
    def __soft_constraint_min_lessons_per_day(self, source=None, teacher_or_group=None, **kwargs):
        if  global_config.soft_constraints.min_lessons_per_day_penalty <= 0 or \
            global_config.soft_constraints.min_lessons_per_day <= 0 or  \
            global_config.soft_constraints.min_lessons_per_day >= global_config.time_slots_per_day_available:
            return
        min_lessons = global_config.soft_constraints.min_lessons_per_day

        if teacher_or_group.count_of_lessons/(self.university.study_weeks/2) < min_lessons:
            return

        vars = []
        indicies = []
        penalties = []
        for lessons in range(0, global_config.time_slots_per_day_available+1):
            penalty = 0
            index = min_lessons-lessons

            if lessons > 0 and lessons < min_lessons:
                penalty = global_config.soft_constraints.min_lessons_per_day_penalty*(index)
                
            vars.append(self.model.variables.add( obj=[penalty],
                                                    lb=[0], 
                                                    ub=[1],
                                                    types=[self.model.variables.type.binary],
                                                    names=['MinLessons'+str(teacher_or_group)])[0])
            indicies.append(index)
            penalties.append(penalty)

        _add_constraint(self.model, source + vars, '==', min_lessons, [1]*len(source)+indicies)
        _add_constraint(self.model, vars, '==', 1)
        
    def __balance_timeslots_in_current_day_every_week(self, source, similar_type_only, base_penalty, multiple_for_similar_type, banned_weeks_only, day, lesson = None, name= ""):
        ts_by_weeks = {}

        @_for_week_only
        @get_timeslots
        def get_timeslots_for_week(self, source=None, week_i=None,  **kwargs):
            ts_by_weeks.setdefault(week_i, []).extend(source)
        
        def calculate_penalty(base, weeks):
            penalty = base
            if lesson:
                per_week = float(lesson.get_count()/weeks)
                if per_week == int(per_week) and per_week > 0: # can be boosted as a hard constraint
                    penalty = -1
            return penalty

        get_timeslots_for_week(self, source=source)

        up_down_weeks = [[],[]]
        active_weeks = [0,0]
        for div in range(0, 1+1):
            for week_i in self.university.get_weeks_for_day(day):
                if week_i % 2 == div:
                    continue

                if week_i in banned_weeks_only:
                    continue

                wi = ts_by_weeks[week_i]
                if len(wi) == 0:
                    continue

                up_down_weeks[div].extend(wi)
                active_weeks[div] += 1
        
        for div in range(0, 1+1):
            if active_weeks[div] <= 1:
                continue
            
            dummy_var = self.model.variables.add(obj=[0],
                                                lb=[0],
                                                ub=[1],
                                                types=[self.model.variables.type.binary])[0]

            temp_weeks = up_down_weeks[div] + [ dummy_var]

            penalty = base_penalty*multiple_for_similar_type
            weeks = copy.deepcopy(active_weeks[div])

            penalty = calculate_penalty(penalty, weeks)
            if penalty != -1:
                temp = calculate_penalty(0, active_weeks[0]+active_weeks[1])
                if temp == -1:
                    penalty = -1

            if penalty != -1:
                self.temp.setdefault(str(lesson), {}).setdefault(day, set()).add(weeks)
            _add_soft_constraint(self.model, temp_weeks, '==', weeks, [1]*(len(temp_weeks)-1) + [weeks], penalty, 1, name + " div " + str(div))

        if similar_type_only:
            return

        dummy_vars = list(self.model.variables.add(obj=[0.0001, 0],
                                            lb=[0]*2,
                                            ub=[1]*2,
                                            types=[self.model.variables.type.binary]*2,
                                            names=["dummy " + name]*2))

        temp_weeks = up_down_weeks[0]+up_down_weeks[1] + dummy_vars
        weeks = active_weeks[0]+active_weeks[1]
        vals = [1]*(len(temp_weeks)-2) + [int(np.min(active_weeks)), weeks]

        penalty = base_penalty #calculate_penalty(base_penalty, weeks)
        _add_soft_constraint(self.model, temp_weeks, '==', weeks, vals, penalty, 1, name + " general")

    def __legacy_balance_timeslots_in_current_day_every_week(self, source, level_of_solve, base_penalty, multiple_for_similar_type, banned_weeks_only, lesson = None, name= ""):
        ts_by_weeks = {}

        @_for_week_only
        @get_timeslots
        def get_timeslots_for_week(self, source=None, week_i=None,  **kwargs):
            ts_by_weeks.setdefault(week_i, []).extend(source)
        
        get_timeslots_for_week(self, source=source)

        cached_is_just_have_different_type_of_week = False

        def add_constraint_for_balanced(self, is_soft_constraint, similar_type_of_week, indexes, values):
            if not is_soft_constraint and not similar_type_of_week:
                if level_of_solve == 2:
                    is_soft_constraint = True
                elif level_of_solve == 1:
                    if cached_is_just_have_different_type_of_week:
                        return
                    is_soft_constraint = True
                        
                        
            if is_soft_constraint:
                penalty = base_penalty*(1+multiple_for_similar_type*similar_type_of_week)
                temp_variables = list(self.model.variables.add( obj=[penalty]*2,
                                                                lb=[0]*2, 
                                                                ub=[1]*2,
                                                                types=[self.model.variables.type.binary]*2,
                                                                names=['Balance + ' + name]*2))

                indexes += temp_variables
                values += [1,-1]

            _add_constraint(self.model, indexes, '==', 0, values)

        for week_i in range(self.university.study_weeks-1):
            for week_j in range(week_i+1, self.university.study_weeks):    
                wi = ts_by_weeks[week_i]
                wj = ts_by_weeks[week_j]

                if len(wi) == 0 or len(wj) == 0:
                    continue
                
                # want to add check, that ts concrete day on week and week+1 equal. then           
                # f = |x-a|    however we don't have absolute value
                # then change |x-a| to p+q
                # f = p+q
                # s.t.
                # x - a + p - q == 0

                similar_type_of_week = (week_i % 2) == (week_j % 2) 
                is_soft_constraint = False
                is_have_banned = week_i in banned_weeks_only or week_j in banned_weeks_only

                if level_of_solve == 3:
                    is_soft_constraint = True
                elif is_have_banned:
                    is_soft_constraint = True
                elif lesson and lesson.get_count() < self.university.study_weeks/2:
                    is_soft_constraint = True

                indexes = wi + wj
                values = [1]*len(wi) + [-1]*len(wj)
                add_constraint_for_balanced(self, is_soft_constraint, similar_type_of_week, indexes, values)

    @_for_groups_or_teachers
    @get_timeslots
    @_for_timeslots
    @get_timeslots
    @_for_lessons
    @get_timeslots
    @_for_day_only
    @get_timeslots
    @_for_rooms
    @get_timeslots
    def __soft_constraint_lessons_balanced_during_module(self, source = None, lesson=None, day_i = None, ith=None, column=None, **kwargs):
        '''
        It is very cool, when lessons on every week placed at similar day and timeslot
        '''
        #TODO
        if column == 'teacher_id':
            return

        if len(source) == 0:
            return

        if global_config.soft_constraints.balanced_constraints.by_lesson_penalty <= 0 or self.university.study_weeks <= 1:
            return

        if lesson.get_count() == 1:
            return

        if lesson.get_count() < self.university.study_weeks/2:
            print("Lesson {0} can be potential reason for slowing of solving (count of lessons lower, than count of weeks/2.".format(lesson))

        banned_weeks_only = set()

        groups_and_teachers = []
        for group_i in lesson.group_indexes:
            groups_and_teachers.append(self.university.groups[group_i])
        for teacher_i in lesson.teacher_indexes:
            groups_and_teachers.append(self.university.teachers[teacher_i])

        for group_or_teacher in groups_and_teachers:
            for week, day, ts in group_or_teacher.banned_time_slots:
                if not week is None:
                    if day is None or day == day_i:
                        banned_weeks_only.add(week)
                elif not day is None and day == day_i:
                    return

        count_of_lessons = self.university.get_count_of_lessons_with_friends(lesson.self_index, ith, column == 'teacher_id')
        lessons_per_day = global_config.soft_constraints.min_count_of_specific_lessons_during_day
        self.__balance_timeslots_in_current_day_every_week( source, 
                                                            int(count_of_lessons/(self.university.get_weeks_count_for_day(day_i)/2)) <= lessons_per_day,
                                                            global_config.soft_constraints.balanced_constraints.by_lesson_penalty,
                                                            global_config.soft_constraints.similar_week_multiply,
                                                            banned_weeks_only,
                                                            day_i,
                                                            lesson,
                                                            "LessDurModule "+ str(lesson))
 
    @_for_week_and_day
    @get_room_tracker
    @get_lesson_tracker
    @_for_groups_or_teachers
    @get_room_tracker
    @get_lesson_tracker
    def __soft_constraint_count_of_lessons_more_than_count_of_rooms(self, room_tracker_source = None, lesson_tracker_source=None, **kwargs):
        if global_config.soft_constraints.minimize_count_of_rooms_per_day_penalty <= 0:
            return

        if len(room_tracker_source) == 0:
            return  

        vals = [1]*len(lesson_tracker_source)+[-1]*len(room_tracker_source)
        penalty = global_config.soft_constraints.minimize_count_of_rooms_per_day_penalty
        _add_soft_constraint(self.model, lesson_tracker_source+room_tracker_source, '>=', 0, vals, penalty, 1, "CountOfLessonsGERomms")
   
    def __soft_constraint_last_day_in_week(self):
        if len(self.university.lessons) == 0:
            return

        if global_config.soft_constraints.last_day_in_week_penalty <= 0 or global_config.study_days <= 1:
            return

        indexes = _get_indexes_of_timeslots_by_filter(self, day=global_config.study_days-1)
        _add_soft_constraint(self.model, copy.deepcopy(indexes), '==', 0, [1]*len(indexes), global_config.soft_constraints.last_day_in_week_penalty, -1, "LastDay")
    
    @_for_groups_or_teachers
    @get_timeslots
    def __soft_constraint_first_or_last_timeslot_in_day(self, source=None, teacher_or_group = None, column=None, **kwargs):
        if len(self.university.lessons) == 0:
            return
        
        #todo
        if column == "teacher_id":
            return

        if teacher_or_group.group_type == GroupType.MAGISTRACY:
            return

        def get_personal_penalties(teacher_or_group):
            def get_count_of_unbanned_ts(penalties):
                return np.sum(penalties == 0)

            def is_stop_condition(personal_penalties, lessons_per_day):
                return get_count_of_unbanned_ts(personal_penalties) >= lessons_per_day or np.sum(personal_penalties <= 0) == len(personal_penalties)

            def get_index_of_minimal_non_zero(personal_penalties):
                index = 0
                for ind, temp in enumerate(personal_penalties):
                    if temp > 0 and temp <= personal_penalties[index]:
                        index = ind
                return index

            personal_penalties = np.array(copy.deepcopy(global_config.soft_constraints.timeslots_penalty))
            lessons_per_day = math.ceil(teacher_or_group.count_of_lessons/self.university.study_weeks/global_config.study_days)

            while not is_stop_condition(personal_penalties, lessons_per_day):
                personal_penalties[get_index_of_minimal_non_zero(personal_penalties)] = 0
                print("Removed index " + str(teacher_or_group))
            return personal_penalties

        personal_penalties = get_personal_penalties(teacher_or_group)

        def add_constraint_for_timeslot(timeslot, penalty):
            if penalty <= 0:
                return

            indexes = _get_indexes_of_timeslots_by_filter(self, timeslot=timeslot)
            _add_soft_constraint(self.model, copy.deepcopy(indexes), '==', 0, [1]*len(indexes), penalty, -1, "LastTSinDay " + str(timeslot) + " " + str(teacher_or_group))

        for ts, penalty in enumerate(personal_penalties):
            add_constraint_for_timeslot(ts, penalty)

    def __legacy_soft_constraint_first_or_last_timeslot_in_day(self):
        if len(self.university.lessons) == 0:
            return

        def add_constraint_for_timeslot(timeslot, penalty):
            if penalty <= 0:
                return

            indexes = _get_indexes_of_timeslots_by_filter(self, timeslot=timeslot)
            _add_soft_constraint(self.model, copy.deepcopy(indexes), '==', 0, [1]*len(indexes), penalty, -1, "LastTSinDay")

        for ts, penalty in enumerate(global_config.soft_constraints.timeslots_penalty):
            add_constraint_for_timeslot(ts, penalty)

    @_for_week_and_day
    @get_timeslots
    @get_lesson_tracker
    @_for_groups_or_teachers
    @get_timeslots
    @get_lesson_tracker
    @_for_lessons_with_friends
    @get_timeslots
    @get_lesson_tracker
    def __soft_constraint_reduce_ratio_of_lessons_and_subjects(self, source =  None, lesson_tracker_source= None, lesson=None, column=None, ith = None, week_i = None, day_i=None, **kwargs):
        if len(source) == 0:
            return

        sc = global_config.soft_constraints
        min_count           = sc.min_count_of_specific_lessons_during_day
        if lesson.lesson_type == RoomType.LECTURE:
            min_count = math.ceil(min_count/2)
        min_count_penalty   = sc.min_count_of_specific_lessons_penalty

        max_count           = sc.max_count_of_specific_lessons_during_day
        max_count_penalty   = sc.max_count_of_specific_lessons_penalty

        min_is_able         = min_count > 0 and min_count_penalty > 0
        max_is_able         = max_count > 0 and max_count_penalty > 0

        if not min_is_able and not max_is_able:
            return

        count_of_lessons = self.university.get_count_of_lessons_with_friends(lesson.self_index, ith, column == 'teacher_id')

        if min_is_able and count_of_lessons > self.university.study_weeks/2: # if we can set it minimum as 2 lesons 1 time per 2 weeks
            indexes =  source+lesson_tracker_source
            vals = [1/min_count]*len(source)+[-1]*len(lesson_tracker_source)
            _add_soft_constraint(self.model, indexes, '>=', 0, vals, min_count_penalty, 1, "MinRatio w {0} d {1} l {2} c {3}".format(week_i, day_i, str(lesson), column))
        
        if max_is_able:
            #todo
            if column == "teacher_id":
                return
            
            indexes =  source+lesson_tracker_source
            vals = [1/max_count]*len(source)+[-1]*len(lesson_tracker_source)
            _add_soft_constraint(self.model, indexes, '<=', 0, vals, max_count_penalty, -1, "MaxRatio w {0} d {1} l {2} c {3}".format(week_i, day_i, str(lesson), column))

    @_for_week_and_day
    @get_timeslots
    @_for_lessons
    @get_timeslots
    def __soft_constraint_ban_windows_between_one_subject_during_day(self, source=None, **kwargs):
        '''
        Ban windows between lessons of one subject. Another words, grouping subjects during day\n
        Take all combinations of length 3,4,5....,lessons_per_day and check, that it doesn't looks like 1,0.....,0,1
        '''
        penalty = global_config.soft_constraints.grouping_subjects_during_day_penalty
        if global_config.time_slots_per_day_available <= 2 or penalty == 0:
            return
        
        self.__ban_windows(source, penalty)

    @_for_timeslots
    @get_timeslots
    @_for_day_only
    @get_timeslots
    @_for_groups_or_teachers
    @get_timeslots
    def __soft_constraint_lessons_balanced_during_module_by_timeslots(self, source = None, day_i = None, teacher_or_group=None, column=None, **kwargs):
        '''
        It is very cool, when lessons on every week in current day placed at similar timeslot
        '''
        if len(source) == 0:
            return
        
        # TODO
        if column == "teacher_id":
            return

        if global_config.soft_constraints.balanced_constraints.by_ts_penalty <= 0 or self.university.study_weeks <= 1:
            return

        if teacher_or_group.count_of_lessons <= 1:
            return

        banned_weeks_only = set()

        for week, day, ts in teacher_or_group.banned_time_slots:
            if not week is None:
                if day is None or day == day_i:
                    banned_weeks_only.add(week)
            elif not day is None and day == day_i:
                return

        self.__balance_timeslots_in_current_day_every_week( source, 
                                                            int(teacher_or_group.count_of_lessons/(self.university.get_weeks_count_for_day(day_i)/2)) <= 2,
                                                            global_config.soft_constraints.balanced_constraints.by_ts_penalty,
                                                            global_config.soft_constraints.similar_week_multiply,
                                                            banned_weeks_only,
                                                            day_i,
                                                            name="LessByTS"+str(teacher_or_group))

    @_for_timeslots
    @get_timeslots
    @_for_day_only
    @get_timeslots
    @_for_groups_or_teachers
    @get_timeslots
    @_for_rooms
    @get_timeslots
    def __soft_constraint_lessons_balanced_during_module_by_rooms(self, source = None, day_i = None, teacher_or_group=None, room_i = None, **kwargs):
        '''
        It is very cool, when lessons on every week in current day placed at similar room
        '''
        if len(source) == 0:
            return

        if global_config.soft_constraints.balanced_constraints.by_room_penalty <= 0 or self.university.study_weeks <= 1:
            return

        if teacher_or_group.count_of_lessons <= 1:
            return

        banned_weeks_only = set()

        for week, day, ts in teacher_or_group.banned_time_slots:
            if not week is None:
                if day is None or day == day_i:
                    banned_weeks_only.add(week)
            elif not day is None and day == day_i:
                return

        self.__balance_timeslots_in_current_day_every_week( source, 
                                                            int(teacher_or_group.count_of_lessons/(self.university.get_weeks_count_for_day(day_i)/2)) <= 2,
                                                            global_config.soft_constraints.balanced_constraints.by_room_penalty,
                                                            global_config.soft_constraints.similar_week_multiply,
                                                            banned_weeks_only,
                                                            day_i,
                                                            name="LessByRooms "+str(teacher_or_group) + " Room "+ str(room_i))

    def solve(self):
        #self.model.set_results_stream(None) # ignore standart useless output
        if len(global_config.soft_constraints.timeslots_penalty) != global_config.time_slots_per_day_available:
            msg = 'Expected equality of len of timeslots_penalty and timee_slots_per_day_available. Len %s timeslots %s' % (len(global_config.soft_constraints.timeslots_penalty), global_config.time_slots_per_day_available)
            warnings.warn(msg)
            print(msg)

        self.temp = {}
        for method in progressbar.progressbar([ self.__fill_lessons_to_time_slots,
                                                self.__fill_dummy_variables_for_tracking_corpuses,
                                                self.__fill_dummy_variables_for_tracking_rooms,
                                                self.__fill_dummy_variables_for_tracking_teachers,
                                                self.__fill_dummy_variables_for_tracking_lessons,
                                                self.__constraint_total_count_of_lessons,
                                                self.__constraint_group_or_teacher_only_in_one_room_per_timeslot,
                                                self.__constraint_ban_changing_corpus_for_groups_or_teachers_during_day,
                                                self.__constraint_max_lessons_per_day_for_teachers_or_groups,
                                                self.__constraint_max_lessons_per_week_for_teachers_or_groups,
                                                self.__local_constraint_lesson_after_another_lesson,
                                                self.__local_constraint_teacher_or_group_has_banned_ts,
                                                self.__constraint_ban_windows,
                                                self.__constraint_one_teacher_per_lessons,
                                                self.__soft_constraint_max_lessons_per_day,
                                                self.__soft_constraint_min_lessons_per_day,
                                                self.__soft_constraint_lessons_balanced_during_module,
                                                self.__soft_constraint_count_of_lessons_more_than_count_of_rooms,
                                                self.__soft_constraint_last_day_in_week,
                                                self.__soft_constraint_first_or_last_timeslot_in_day,
                                                self.__soft_constraint_reduce_ratio_of_lessons_and_subjects,
                                                self.__soft_constraint_ban_windows_between_one_subject_during_day,
                                                self.__soft_constraint_lessons_balanced_during_module_by_timeslots, 
                                                self.__soft_constraint_lessons_balanced_during_module_by_rooms,
                                               # self.model.solve
                                                ]):
            print()
            print(method.__name__)
            method()
       # print(self.temp)
        return False
        debug(self.model.variables.get_names())
        output = self.__parse_output_and_create_schedule()
        return not output is None, output

    def __parse_output_and_create_schedule(self):
        print("Solution status = ",     self.model.solution.get_status(), ":", self.model.solution.status[self.model.solution.get_status()])
        if self.model.solution.get_status() in [1, 101, 102, 107, 113]:
            print("Value: ", self.model.solution.get_objective_value())
        else:
            return None

        debug("Array of X = %s" %           self.model.solution.get_values())
        debug("Solution value  = %s" %      self.model.solution.get_objective_value())

        names = self.model.variables.get_names()
        values = self.model.solution.get_values()
        objectives = self.model.objective.get_linear()

        by_group = {}
        for i, val in enumerate(values):
            if val == 0:
                continue
            
            variables = _get_variables_from_general_variable(names[i])
            if len(variables) == 0:
                if objectives[i] > 0:
                    print("{0} = {1}".format(names[i], val*objectives[i]))
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
                temp[ts] = [int(corpus), int(room), self.university.lessons[lesson], _type, int(teacher), temp_list]

        # for group, weeks in sorted(by_group.items()):
        #     for week, days in sorted(weeks.items()):
        #         for day, tss in sorted(days.items()):
        #             for ts, listt in sorted(tss.items()):
        #                 corpus, room, lesson, _type, teacher, other_groups = listt
        #                 print("Groups %s \t Week %d\tDay %d Corpus %d  TS %d  room %d\tlesson %s\ttype %s\t\t With %s  \tteacher %s" % 
        #                       (group, week, day, corpus, ts, room, lesson, str(_type).split('.')[1], ",".join(str(i) for i in other_groups), self.university.teachers[teacher] ))

        return by_group
    
    def _get_groups_teachers_list(self):
        ''' Returns tuple of (container, format for corpus tracking, column for filter) '''
        return [(self.university.groups, corpus_tracker_of_groups_format, 'group_id'), 
                (self.university.teachers, corpus_tracker_of_teachers_format, 'teacher_id')]
