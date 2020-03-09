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


#[[[cog trackers
import cog
import xml.etree.ElementTree as ET

trackers = {}

def add_variable_search(pov):
    base_name = pov.get('name')
    prefix_name = base_name+'_prefix'
    variable_name = base_name+'_i'

    cog.outl("\tsearch += {:<17} + {}".format(prefix_name, pov.get('use_as').format(variable_name)))

data = ET.parse('./xmls/tracker_variables.xml')
data = data.getroot()
for variable in data.getchildren():
    cog.out('def _get_{0}_by_filter(variables, '.format(variable.get('name')))
    cog.out(", ".join([pov.get('name')+'_i ='+ pov.get('default') for pov in variable.findall('.//part')]))
    cog.outl(', source = None):')
    cog.outl("\tsearch=r'^'\n")

    arguments = []
    for pov in variable.getchildren():
        if pov.tag =='part':
            arguments.append([pov.get('name')+'_i'])
            add_variable_search(pov)
        elif pov.tag == 'variants':
            arguments.append([pov.get('name'), pov.get('value')])
            for i, temp_pov in enumerate(pov.getchildren()):
                if temp_pov.tag == 'part':
                    base_name = temp_pov.get('name')
                    variable_name = base_name+'_i'
                    cog.out('\t')
                    cog.out('if ' if i == 0 else 'elif ')
                    cog.outl('not {0} is None:'.format(variable_name))
                    cog.out('\t')
                    add_variable_search(temp_pov)
                else:
                    cog.outl('\telse:')
                    cog.outl('\t\tsearch={0}'.format(temp_pov.get('value')))


    trackers[variable.get('name')] = arguments

    cog.outl("\n\tsearch += r'$'")
    cog.outl("\n\tif 'None' in search:")
    cog.outl("\t\traise Exception('None in search: '+search)")
    cog.outl("\treturn _get_indexes_by_name(variables, search, True, source)\n")
# ]]]
#[[[end]]]


#[[[cog
import cog
import xml.etree.ElementTree as ET

decorators = {}
data = ET.parse('./xmls/decorators.xml')
data = data.getroot()
for decorator in data.getchildren():
    cog.outl('def {}(function):'.format(decorator.get('name')))
    cog.outl('    @wraps(function)')
    cog.outl('    def _decorator(self, **kwargs):')

    tabs = "        "
    all_vars = []
    for for_code in decorator.findall('./for'):
        vars = [var.get('name') for var in for_code.findall('./variable')]
        all_vars.extend(vars)

        cog.outl(tabs+'for {0} in {1}:'.format(", ".join(vars), for_code.get('source')))
        tabs+='    '

        for temp_variable in for_code.findall('./local_variable'):
            cog.outl(tabs+'{0}={1}'.format(temp_variable.get('name'), temp_variable.get('default')))
            all_vars.append(temp_variable.get('name'))

    cog.outl(tabs+'function(self, {0}, **kwargs)'.format(", ".join("{0}={0}".format(var) for var in all_vars)))
    cog.outl('    return _decorator\n')
    decorators[decorator.get('name')] = all_vars

# ]]]
#[[[end]]]

#[[[cog
import cog

for function_name, variables in trackers.items():
    source_name = function_name+'_source'
    original_function_name = '_get_'+function_name+'_by_filter'
    new_function_name = 'get_'+function_name

    cog.outl('def {}(function):'.format(new_function_name))
    cog.outl('    @wraps(function)')
    cog.outl('    def _decorator(self, {0}=None, **kwargs):'.format(source_name))
    tabs = '        '
    specific_variables = []
    variants_variables = []
    for var_variables in variables:
        for variable in var_variables:
            cog.outl(tabs+"{0:<15}=kwargs.get('{0}', {1})".format(variable, "r'.*'" if len(var_variables) == 1 else "None"))
        if len(var_variables) == 1:
            specific_variables.append(var_variables[0])
        else:
            variants_variables.append(var_variables)
    
    cog.outl()
    cog.outl(tabs+'indexes = {0}(self.model.variables, {1}, source={2})'.format(original_function_name, ", ".join([var+'='+var for var in specific_variables]), source_name))
    cog.outl(tabs+'temp = self.model.variables.get_names(indexes)')
    cog.outl()
    for variains in variants_variables:
        cog.outl(tabs+'if {0}:'.format(variains[0]))
        cog.outl(tabs+'    '+"indexes = eval('{0}(self.model.variables, %s={2}, source=temp)' % {1})".format(original_function_name, variains[0], variains[1]))
        cog.outl(tabs+'    '+'temp = self.model.variables.get_names(indexes)')
    
    cog.outl()
    cog.outl(tabs+'function(self, {0}=temp, **kwargs)'.format(source_name))
    cog.outl('    return _decorator\n')
    decorators[new_function_name] = [source_name]

# ]]]
#[[[end]]]

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

#[[[cog
import cog
import xml.etree.ElementTree as ET
import numpy as np
cog.outl('#')

data = ET.parse('./xmls/methods.xml')
data = data.getroot()

for method in data.getchildren():
    tabs = "    "
    input_vars = []
    for decorator_name in method.get('decorators', "").split(' '):
        if len(decorator_name) <= 0:
            continue
        cog.outl(tabs+'@{0}'.format(decorator_name))
        input_vars.extend(decorators[decorator_name])
    input_vars = np.unique(input_vars)
    cog.outl(tabs+"def {0}(self, {1}, **kwargs):".format(method.get('name'), ", ".join([var+'=None' for var in input_vars])))
    cog.outl(method.find('code').text)
    cog.outl()

# ]]]
#[[[end]]]


    def solve(self):
        #self.model.set_results_stream(None) # ignore standart useless output
        if len(global_config.soft_constraints.timeslots_penalty) != global_config.time_slots_per_day_available:
            msg = 'Expected equality of len of timeslots_penalty and timee_slots_per_day_available. Len %s timeslots %s' % (len(global_config.soft_constraints.timeslots_penalty), global_config.time_slots_per_day_available)
            warnings.warn(msg)
            print(msg)
#[[[cog
import cog
import xml.etree.ElementTree as ET
import numpy as np
cog.outl('#')

data = ET.parse('./xmls/methods.xml')
data = data.getroot()
methods = [method.get('name') for method in data.getchildren()]
methods.append('model.solve')
cog.outl('        methods=[{0}]'.format(", ".join(['self.'+method for method in methods])))
# ]]]
#[[[end]]]
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