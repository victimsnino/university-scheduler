import re
import cplex
from general_utils import * 



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

