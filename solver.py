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
import sys

from id_wrapper import *
from concurrent.futures import ThreadPoolExecutor 
import multiprocessing

variables_filter_cache = {}

def add_constraint(my_model, indexes_or_variables, sense, value, val = None):
    valid_operations = ["<=", ">=", "=="]
    senses = ["L", "G", "E"]
    if sense not in valid_operations:
        raise Exception("Not valid operation! %s" % sense)

    if len(indexes_or_variables) == 0:
        raise Exception('List of indexes is empty!')

    if val is None:
        val = [1.0]*len(indexes_or_variables)

    if DEBUG_PRINT:
        debug(str(indexes_or_variables) + sense + str(value) + str(val))
    my_model.linear_constraints.add(lin_expr = [cplex.SparsePair(ind = indexes_or_variables, 
                                                                val = val)], 
                                    senses = senses[valid_operations.index(sense)],
                                    rhs = [value])

def add_variables(my_model, obj=0, ub=1, names=None):
    ub   = ub     if isinstance(ub, list)   else [ub] 
    obj  = obj    if isinstance(obj, list)  else [obj]
    names = names if isinstance(names, list) else [names]

    non_standard_size = 1
    for temp in [ub, obj, names]:
        if len(temp) != non_standard_size and len(temp) != 1:
            if non_standard_size != 1:
                raise Exception("Different sizes of arguments!")
            non_standard_size = len(temp)
    
    ub    = ub    if len(ub) == non_standard_size    else ub*non_standard_size
    obj   = obj   if len(obj) == non_standard_size   else obj*non_standard_size
    names = names if len(names) == non_standard_size else names*non_standard_size


    types = [my_model.variables.type.binary  if ub_t == 1 else my_model.variables.type.integer for ub_t in ub  ]
    lb = [0]*non_standard_size

    debug(",".join([str(obj), str(lb), str(ub), str(types), str(names)]))
    return list(my_model.variables.add(obj=obj,
                                  lb=lb,
                                  ub=ub,
                                  types=types,
                                  names=names))

def add_soft_constraint(my_model, indexes_or_variables, sense, value, vals, penalty, val_for_new_variable, name=None, ub = None):
    if penalty > 0: # A.K.A soft constraint
        indexes_or_variables += add_variables(my_model, obj=[penalty], 
                                                        ub =[ub] if ub else [cplex.infinity], 
                                                        names=[name] if name else None)
        vals.append(val_for_new_variable)

    add_constraint(my_model, indexes_or_variables, sense, value, vals)

def _get_indexes_from_container(target, source, container):
    cache = variables_filter_cache.setdefault(str(target), {}).setdefault(str(source), {})
    value = cache.get('cached_var', None)
    if value:
        return copy.copy(value)
    
    out = [index for index in source if container.get(index, None) == target]

    cache['cached_var'] = out
    return copy.copy(out)

def get_indexes_of_timeslots_by_filter(timeslots, week = -1, day = -1, corpus = -1, 
                                       room = -1, timeslot = -1, lesson = -1, group_id = list(), 
                                       type = -1, teacher_id = -1, source = None):

    target = TimeSlotWrapper(week, day, corpus, room, timeslot, lesson, group_id, type, teacher_id)
    if source is None:
        source = list(timeslots.keys())

    return _get_indexes_from_container(target, source, timeslots)

def get_corpus_tracker_by_filter(corpus_trackers, corpus = -1, week = -1, day = -1, group_id = -1, teacher_id = -1, source = None):
    target = CorpusTrackerWrapper(corpus=corpus, week=week, day=day, group_id=group_id, teacher_id=teacher_id)
    if source is None:
        source = list(corpus_trackers.keys())

    return _get_indexes_from_container(target, source, corpus_trackers)

def get_room_tracker_by_filter(room_trackers, room=-1, corpus = -1, week = -1, day = -1, group_id = -1, teacher_id = -1, source = None):
    target = RoomTrackerWrapper(room=room, corpus=corpus, week=week, day=day, group_id=group_id, teacher_id=teacher_id)
    if source is None:
        source = list(room_trackers.keys())

    return _get_indexes_from_container(target, source, room_trackers)
                        
def get_lesson_tracker_by_filter(lesson_trackers, week = -1, day = -1, lesson_id = -1, group_id = -1, teacher_id = -1, source = None):
    target = LessonTrackerWrapper(week=week, day=day, lesson=lesson_id, group_id=group_id, teacher_id=teacher_id)
    if source is None:
        source = list(lesson_trackers.keys())

    return _get_indexes_from_container(target, source, lesson_trackers)

def get_teacher_per_lesson_tracker_by_filter(teach_per_less_trackers, lesson=-1, teacher=-1, source = None):
    target = TeacherPerLessonTrackerWrapper(lesson=lesson, teacher=teacher)
    if source is None:
        source = list(teach_per_less_trackers.keys())

    return _get_indexes_from_container(target, source, teach_per_less_trackers)

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
        for container, column in self._get_groups_teachers_list():
            for ith, teacher_or_group in enumerate(container):
                function(self, ith=ith, teacher_or_group=teacher_or_group, column=column, **kwargs)
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
            indexes = get_indexes_of_timeslots_by_filter(self.timeslots, source=source, week=week, day=day, corpus=corpus, room=room, timeslot=timeslot, lesson=lesson, type=type)
            if column:
                indexes = eval(f'get_indexes_of_timeslots_by_filter(self.timeslots, source = indexes, {column}=ith)')
                ith # needed for capturing it inside functon
            return indexes

        indexes = get_indexes(self, lesson_i)

        function(self, source=indexes, **kwargs)
    return _decorator

##########################################

def get_corpus_tracker(function):
    @wraps(function)
    def _decorator(self, corpus_tracker_source=None, **kwargs):
        week        = kwargs.get('week_i',   -1)
        day         = kwargs.get('day_i',    -1)
        corpus      = kwargs.get('corpus_i', -1)
        column      = kwargs.get('column',   None)
        ith         = kwargs.get('ith',      None)

        indexes = get_corpus_tracker_by_filter(self.corpus_trackers, corpus=corpus, week=week, day=day, source=corpus_tracker_source)
        if column:
            indexes = eval(f'get_corpus_tracker_by_filter(self.corpus_trackers, source=indexes, {column}=ith)')

        function(self, corpus_tracker_source=indexes, **kwargs)
    return _decorator

##########################################

def get_room_tracker(function):
    @wraps(function)
    def _decorator(self, room_tracker_source=None, **kwargs):
        room        = kwargs.get('room_i', -1)
        week        = kwargs.get('week_i', -1)
        day         = kwargs.get('day_i',  -1)
        corpus      = kwargs.get('corpus_i', -1)
        column      = kwargs.get('column', None)
        ith         = kwargs.get('ith', None)

        indexes = get_room_tracker_by_filter(self.room_trackers, room=room, corpus=corpus, week=week, day=day, source=room_tracker_source)
        if column:
            indexes = eval(f'get_room_tracker_by_filter(self.room_trackers, source=indexes, {column}=ith)')

        function(self, room_tracker_source=indexes, **kwargs)
    return _decorator

###########################################

def get_lesson_tracker(function):
    @wraps(function)
    def _decorator(self, lesson_tracker_source=None, **kwargs):
        week        = kwargs.get('week_i', -1)
        day         = kwargs.get('day_i', -1)
        lesson_id   = kwargs.get('lesson_i', -1)
        column      = kwargs.get('column', None)
        ith         = kwargs.get('ith', None)

        @_get_indexes_with_friends([])# kwargs.get('friends_indexes', []))
        def get_indexes(self, lesson_id):
            indexes = get_lesson_tracker_by_filter(self.lesson_trackers, week=week, day=day, lesson_id=lesson_id, source=lesson_tracker_source)
            if column:
                indexes = eval(f'get_lesson_tracker_by_filter(self.lesson_trackers, source=indexes, {column}=ith)')
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
        self.model.parameters.simplex.limits.lowerobj.set(0)
        if global_config.timelimit_for_solve > 0:
            self.model.parameters.timelimit.set(global_config.timelimit_for_solve)
        self.model.parameters.emphasis.mip.set(2)

        global variables_filter_cache
        variables_filter_cache.clear()
        self.timeslots = {}
        self.corpus_trackers={}
        self.room_trackers={}
        self.lesson_trackers = {}
        self.teacher_per_lesson_trackers = {}

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
                                wrapper = TimeSlotWrapper(week_i, day_i, corpus_i, room.room_number, time_slot, lesson.self_index, 
                                                                                lesson.group_indexes, lesson.lesson_type, teacher_i)
                                indexes += add_variables(self.model, names=[str(wrapper)])
                                self.timeslots[indexes[-1]] = wrapper

                            
                        # each time-slot can have only 1 lesson
                        if len(indexes) != 0:
                            add_constraint(self.model, indexes, '<=', 1)

    def __fill_variables_helper(self, name, source, max_limit):
        tracker_index  = add_variables(self.model, names=[name])

        add_constraint(self.model, source + tracker_index, '<=', 0, 
                        [1]*len(source)+[-1*max_limit])

        add_constraint(self.model, source + tracker_index, '>=', -1*(max_limit-1), 
                        [1]*len(source)+[-1*max_limit])
        return tracker_index[0]

    @_for_corpuses
    @get_timeslots
    @_for_week_and_day
    @get_timeslots
    @_for_groups_or_teachers
    @get_timeslots
    def __fill_dummy_variables_for_tracking_corpuses(self, source = None, week_i = None, day_i = None, corpus_i = None, column = None, ith=None, **kwargs):
        ''' 
        Add dummy variables for corpus tracking (Group or teacher has lection in i-th corpus)
        '''
        tracker = eval(f'CorpusTrackerWrapper(corpus=corpus_i, week=week_i, day=day_i, {column}=ith)')
        index = self.__fill_variables_helper(str(tracker), source, global_config.time_slots_per_day_available)
        self.corpus_trackers[index] = tracker

    @_for_rooms
    @get_timeslots
    @_for_week_and_day
    @get_timeslots
    @_for_groups_or_teachers
    @get_timeslots
    def __fill_dummy_variables_for_tracking_rooms(self, source = None, week_i = None, day_i = None, corpus_i = None, room_i = None, column=None, ith=None,  **kwargs):
        ''' 
        Add dummy variables for corpus tracking (Group or teacher has lection in i-th corpus)
        '''
        tracker = eval(f'RoomTrackerWrapper(room=room_i, corpus=corpus_i, week=week_i, day=day_i, {column}=ith)')
        index = self.__fill_variables_helper(str(tracker), source, global_config.time_slots_per_day_available)
        self.room_trackers[index] = tracker

    @_for_lessons
    @get_timeslots
    @_for_week_and_day
    @get_timeslots
    @_for_groups_or_teachers
    @get_timeslots
    def __fill_dummy_variables_for_tracking_lessons(self, source = None, week_i = None, day_i = None, lesson = None, column = None, ith=None,  **kwargs):
        tracker = eval(f'LessonTrackerWrapper(week=week_i, day=day_i, lesson=lesson.self_index, {column}=ith)')
        index = self.__fill_variables_helper(str(tracker), source, global_config.time_slots_per_day_available)
        self.lesson_trackers[index] = tracker

    @_for_lessons
    @get_timeslots
    def __fill_dummy_variables_for_tracking_teachers(self, source = None, lesson=None, **kwargs):
        ''' 
        Add dummy variables for teachers tracking (which teachers marked for current lesson during module)
        '''
        for teacher_i in lesson.teacher_indexes:
            lections_indexes = get_indexes_of_timeslots_by_filter(self.timeslots, source=source, teacher_id=teacher_i)

            tracker = TeacherPerLessonTrackerWrapper(lesson=lesson.self_index, teacher=teacher_i)
            index = self.__fill_variables_helper(str(tracker), lections_indexes, lesson.get_count())
            self.teacher_per_lesson_trackers[index] = tracker

    @_for_lessons
    @get_timeslots
    def __constraint_total_count_of_lessons(self, source = None, lesson = None, **kwargs):
        ''' 
        Every lesson should have a count of lessons, which we request \n
        Therefore we should add constraints for it (count of all lessons in timeslots == requested)
        '''
        add_constraint(self.model, source, '==', lesson.get_count())

    @_for_timeslots
    @get_timeslots
    @_for_week_and_day
    @get_timeslots
    @_for_groups_or_teachers
    @get_timeslots
    def __constraint_group_or_teacher_only_in_one_room_per_timeslot(self, source=None, **kwargs):
        add_constraint(self.model, source, '<=', 1)

    @_for_week_and_day
    @get_corpus_tracker
    @_for_groups_or_teachers
    @get_corpus_tracker
    def __constraint_ban_changing_corpus_for_groups_or_teachers_during_day(self, corpus_tracker_source=None, **kwargs):
        add_constraint(self.model, corpus_tracker_source, '<=', 1)

    @_for_week_and_day
    @get_timeslots
    @_for_groups_or_teachers
    @get_timeslots
    def __constraint_max_lessons_per_day_for_teachers_or_groups(self, source=None, **kwargs):
        '''
        Every teacher or group can be busy only limited count of lessons per day
        '''
        add_constraint(self.model, source, '<=', global_config.max_lessons_per_day)
    
    @_for_week_only
    @get_timeslots
    @_for_groups_or_teachers
    @get_timeslots
    def __constraint_max_lessons_per_week_for_teachers_or_groups(self, source=None, **kwargs):
        '''
        Every teacher or group can be busy only limited count of lessons per week
        '''
        add_constraint(self.model, source, '<=', global_config.max_lessons_per_week)

    def __local_constraint_lesson_after_another_lesson(self):
        '''
        Some lessons should be after some another. \n
        For example, practice should be after lection. Therefore we should track it.
        '''
        if global_config.soft_constraints.lesson_after_lesson_penalty == 0:
            return

        def get_sorted_indexes_and_costs(self, lesson_i):
            original_indexes = get_indexes_of_timeslots_by_filter(self.timeslots, lesson=str(lesson_i))
            original_indexes = sorted(original_indexes, key=lambda index: _calculate_cost_of_lesson_by_position(self.model.variables.get_names(index)))
            original_costs   = [_calculate_cost_of_lesson_by_position(self.model.variables.get_names(i)) for i in original_indexes]
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
                add_soft_constraint(self.model, indexes, '>=', 0, vals, global_config.soft_constraints.lesson_after_lesson_penalty, 1, 'Less after less min')
                add_soft_constraint(self.model, indexes, '<=', 2, vals, global_config.soft_constraints.lesson_after_lesson_penalty, -1, 'Less after less max')

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

            indexes = get_indexes_of_timeslots_by_filter(self.timeslots, week=week, day=day, timeslot=timeslot, source=source)
            add_constraint(self.model, indexes, '==', 0)

    def __ban_windows(self, source, penalty):
        indexes_by_ts = []
        for timeslot in range(global_config.time_slots_per_day_available):
            indexes_by_ts.append(get_indexes_of_timeslots_by_filter(self.timeslots, source=source, timeslot=timeslot))

        # select size of block for checking
        for max_timeslots in range(3, global_config.time_slots_per_day_available+1):
            for ind in range(max_timeslots, global_config.time_slots_per_day_available+1):
                val = []
                temp_indexes = []
                for ts in range(ind-max_timeslots, ind):
                    v =  1 if ts == (ind-max_timeslots) or ts == (ind-1) else -1
                    val += [v]*len(indexes_by_ts[ts])
                    temp_indexes += indexes_by_ts[ts]

                add_soft_constraint(self.model, temp_indexes, '<=', 1, val, penalty*(penalty>0)*(max_timeslots-2), -1, 'Ban_windows', 1)

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
                indexes += get_teacher_per_lesson_tracker_by_filter(self.teacher_per_lesson_trackers, lesson=lesson.self_index, teacher=teacher_i)

            add_constraint(self.model, indexes, '<=', 1)

    @_for_week_and_day
    @get_timeslots
    @_for_groups_or_teachers
    @get_timeslots
    def __soft_constraint_max_lessons_per_day(self, source=None, teacher_or_group = None, week_i = None, day_i = None, **kwargs):
        if  global_config.soft_constraints.max_lessons_per_day_penalty <= 0 or \
            global_config.soft_constraints.max_lessons_per_day <= 0 or  \
            global_config.soft_constraints.max_lessons_per_day >= global_config.time_slots_per_day_available:
            return
        for excess_lessons_per_day in range(global_config.soft_constraints.max_lessons_per_day, global_config.time_slots_per_day_available):
            name = "MaxLessons {0} w{1} d{2} di{3}".format(str(teacher_or_group), week_i, day_i, excess_lessons_per_day)
            vals = [1]*len(source)
            penalty = excess_lessons_per_day*global_config.soft_constraints.max_lessons_per_day_penalty
            add_soft_constraint(self.model, copy.copy(source), '<=', excess_lessons_per_day, vals, penalty, -1, name, ub=global_config.time_slots_per_day_available)
            
    @_for_week_and_day
    @get_timeslots
    @_for_groups_or_teachers
    @get_timeslots
    def __soft_constraint_min_lessons_per_day(self, source=None, teacher_or_group=None, column=None, **kwargs):
        if  global_config.soft_constraints.min_lessons_per_day_penalty <= 0 or \
            global_config.soft_constraints.min_lessons_per_day <= 0 or  \
            global_config.soft_constraints.min_lessons_per_day >= global_config.time_slots_per_day_available:
            return
        min_lessons = global_config.soft_constraints.min_lessons_per_day

        if teacher_or_group.count_of_lessons/(self.university.study_weeks/2) < min_lessons:
            return

        #TODO
        if column == 'teacher_id':
            return

        vars = []
        indicies = []
        penalties = []
        for lessons in range(0, global_config.time_slots_per_day_available+1):
            penalty = 0
            index = min_lessons-lessons

            if lessons > 0 and lessons < min_lessons:
                penalty = global_config.soft_constraints.min_lessons_per_day_penalty*(index)
                
            vars += add_variables(self.model, obj=[penalty],names=['MinLessons'+str(teacher_or_group)])
            indicies.append(index)
            penalties.append(penalty)

        add_constraint(self.model, source + vars, '==', min_lessons, [1]*len(source)+indicies)
        add_constraint(self.model, vars, '==', 1)
        
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

        get_timeslots_for_week(self, source=copy.copy(source))

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
            
            dummy_var = add_variables(self.model)[0]

            temp_weeks = up_down_weeks[div] + [ dummy_var]

            penalty = base_penalty*multiple_for_similar_type
            weeks = copy.copy(active_weeks[div])

            penalty = calculate_penalty(penalty, weeks)
            if penalty != -1:
                temp = calculate_penalty(0, active_weeks[0]+active_weeks[1])
                if temp == -1:
                    penalty = -1

            add_soft_constraint(self.model, temp_weeks, '==', weeks, [1]*(len(temp_weeks)-1) + [weeks], penalty, 1, name + " div " + str(div))

        if similar_type_only:
            return

        dummy_vars = add_variables(self.model, obj=[global_config.soft_constraints.balanced_constraints.skip_balance_by_penalty, 0],
                                               names=["dummy " + name + " day " + str(day)]*2)

        temp_weeks = up_down_weeks[0]+up_down_weeks[1] + dummy_vars
        weeks = active_weeks[0]+active_weeks[1]
        vals = [1]*(len(temp_weeks)-2) + [int(np.min(active_weeks)), weeks]

        penalty = base_penalty #calculate_penalty(base_penalty, weeks)
        add_soft_constraint(self.model, temp_weeks, '==', weeks, vals, penalty, 1, name + " day " + str(day)+ " general")

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
                temp_variables = list(add_variables(self.model, obj=[penalty]*2,names='Balance + ' + name))

                indexes += temp_variables
                values += [1,-1]

            add_constraint(self.model, indexes, '==', 0, values)

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

    @_for_timeslots
    @get_timeslots
    @_for_day_only
    @get_timeslots
    @_for_lessons
    @get_timeslots
    @_for_rooms
    @get_timeslots
    @_for_groups_or_teachers
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
        add_soft_constraint(self.model, lesson_tracker_source+room_tracker_source, '>=', 0, vals, penalty, 1, "CountOfLessonsGERomms")
   
    def __soft_constraint_last_day_in_week(self):
        if len(self.university.lessons) == 0:
            return

        if global_config.soft_constraints.last_day_in_week_penalty <= 0 or global_config.study_days <= 1:
            return

        indexes = get_indexes_of_timeslots_by_filter(self.timeslots, day=global_config.study_days-1)
        add_soft_constraint(self.model, copy.deepcopy(indexes), '==', 0, [1]*len(indexes), global_config.soft_constraints.last_day_in_week_penalty, -1, "LastDay")
    
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

            indexes = get_indexes_of_timeslots_by_filter(self.timeslots, timeslot=timeslot)
            add_soft_constraint(self.model, copy.deepcopy(indexes), '==', 0, [1]*len(indexes), penalty, -1, "LastTSinDay " + str(timeslot) + " " + str(teacher_or_group))

        for ts, penalty in enumerate(personal_penalties):
            add_constraint_for_timeslot(ts, penalty)

    def __legacy_soft_constraint_first_or_last_timeslot_in_day(self):
        if len(self.university.lessons) == 0:
            return

        def add_constraint_for_timeslot(timeslot, penalty):
            if penalty <= 0:
                return

            indexes = get_indexes_of_timeslots_by_filter(self.timeslots, timeslot=timeslot)
            add_soft_constraint(self.model, copy.deepcopy(indexes), '==', 0, [1]*len(indexes), penalty, -1, "LastTSinDay")

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
    def __soft_constraint_reduce_ratio_of_lessons_and_subjects(self, source =  None, lesson_tracker_source= None, lesson=None, column=None, ith = None, week_i = None, day_i=None, teacher_or_group=None, **kwargs):
        # TODO: Rewrite me pls
        if len(source) == 0:
            return
        
        #todo
        if column == "teacher_id":
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
            add_soft_constraint(self.model, indexes, '>=', 0, vals, min_count_penalty, 1, "MinRatio w {0} d {1} l {2} c {3}".format(week_i, day_i, str(lesson), teacher_or_group))
        
        if max_is_able:            
            indexes =  source+lesson_tracker_source
            vals = [1/max_count]*len(source)+[-1]*len(lesson_tracker_source)
            add_soft_constraint(self.model, indexes, '<=', 0, vals, max_count_penalty, -1, "MaxRatio w {0} d {1} l {2} c {3}".format(week_i, day_i, str(lesson), teacher_or_group))

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

    @_for_groups_or_teachers
    @get_corpus_tracker
    def __soft_constraint_teacher_or_group_has_banned_corpuses(self, corpus_tracker_source=None, teacher_or_group=None, **kwargs):
        if global_config.soft_constraints.ban_corpuses_penalty == 0:
            return

        for banned_corpus in teacher_or_group.banned_corpuses:
            indexes = get_corpus_tracker_by_filter(self.corpus_trackers, corpus = banned_corpus, source=corpus_tracker_source)
            add_soft_constraint(self.model, indexes, '==', 0, [1]*len(indexes), global_config.soft_constraints.ban_corpuses_penalty, -1, "Ban corpus")

    def solve(self):
        #cplexlog = open("cplex.log", 'w')
        #self.model.set_results_stream(cplexlog)
        #self.model.set_warning_stream(cplexlog)
        #self.model.set_error_stream(cplexlog)
        #self.model.set_log_stream(cplexlog)

        if len(global_config.soft_constraints.timeslots_penalty) != global_config.time_slots_per_day_available:
            msg = 'Expected equality of len of timeslots_penalty and timee_slots_per_day_available. Len %s timeslots %s' % (len(global_config.soft_constraints.timeslots_penalty), global_config.time_slots_per_day_available)
            warnings.warn(msg)
            print(msg)

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
                                                self.__soft_constraint_teacher_or_group_has_banned_corpuses,
                                                self.model.solve
                                                ]):
            print()
            print(method.__name__)
            method()

        #cplexlog.close()
        #return False, False, False
        debug(self.model.variables.get_names())
        by_groups, by_teachers = self.__parse_output_and_create_schedule()
        return not by_groups is None, by_groups, by_teachers

    def __parse_output_and_create_schedule(self):
        print("Solution status = ",     self.model.solution.get_status(), ":", self.model.solution.status[self.model.solution.get_status()])
        if self.model.solution.get_status() in [1, 101, 102, 107, 113]:
            print("Value: ", self.model.solution.get_objective_value())
        else:
            return None, None

        debug("Array of X = %s" %           self.model.solution.get_values())
        debug("Solution value  = %s" %      self.model.solution.get_objective_value())

        names = self.model.variables.get_names()
        values = self.model.solution.get_values()
        objectives = self.model.objective.get_linear()

        by_group = {}
        by_teacher = {}
        for i, val in enumerate(values):
            if round(val,3) <= 0:
                continue
            
            variables = _get_variables_from_general_variable(names[i])
            if len(variables) == 0:
                if objectives[i] > 0:
                    print("{0} = {1}".format(names[i], val*objectives[i]))
                continue

            debug(names[i] + str(val))
            week, day, corpus, room, ts, lesson,  group_ids,  _type, teacher = variables
            for group_id in group_ids:
                temp_list = copy.deepcopy(group_ids)
                temp_list.remove(group_id)

                day_dict_by_group = by_group.setdefault(group_id, {}).setdefault(week, {}).setdefault(day, {})
                day_dict_by_group[ts] = [int(corpus), int(room), self.university.lessons[lesson], _type, int(teacher), temp_list]

                day_dict_by_teacher = by_teacher.setdefault(int(teacher), {}).setdefault(week, {}).setdefault(day, {})
                day_dict_by_teacher[ts] = [int(corpus), int(room), self.university.lessons[lesson], _type, group_ids]

        return by_group, by_teacher
    
    def _get_groups_teachers_list(self):
        ''' Returns tuple of (container, column for filter) '''
        return [(self.university.groups,   'group_id'), 
                (self.university.teachers, 'teacher_id')]
