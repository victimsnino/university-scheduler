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


#[[[cog
import cog
import xml.etree.ElementTree as ET
data = ET.parse('./xmls/tracker_variables.xml')
data = data.getroot()
for variable in data.getchildren():

    cog.out('def _get_{0}_by_filter(variables, '.format(variable.get('name')))
    cog.out(", ".join([pov.get('name')+'_i ='+ pov.get('default') for pov in variable.getchildren()]))
    cog.outl(', source = None):')

    cog.outl("\tsearch=r'^'\n")
    for pov in variable.getchildren():
        base_name = pov.get('name')
        prefix_name = base_name+'_prefix'
        variable_name = base_name+'_i'

        pre_use = pov.get('pre_use', None)
        if pre_use:
            cog.outl("\t"+pre_use.format(variable_name))
            cog.out("\t")
            
        cog.outl("\tsearch += {:<17} + {}".format(prefix_name, pov.get('use_as').format(variable_name)))
        else_usage  = pov.get('else', None)
        if else_usage:
            cog.outl("\telse:")
            cog.outl("\t\tsearch += {}".format(else_usage))

    cog.outl("\n\tsearch += r'$'")
    cog.outl("\n\tif 'None' in search:")
    cog.outl("\t\traise Exception('None in search: '+search)")
    cog.outl("\treturn _get_indexes_by_name(variables, search, True, source)\n")
    # ]]]
#[[[end]]]
