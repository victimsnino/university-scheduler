import pytest

from university import *
from general_utils import RoomType, debug, set_debug, Config, global_config, GroupType
from solver import *
import copy
from beautiful_out import open_as_html
from id_wrapper import TimeSlotWrapper
import cplex

def setup_function():
    global_config.reset()
    print()


def test_ts_wrapper():
    original = TimeSlotWrapper(week=1, day=0, corpus=1, room=1, timeslot=0, lesson=1, group_id=[0], type=1, teacher_id=1)
    target = TimeSlotWrapper(week=1, day=1, corpus=1, room=1, timeslot=0, lesson=1, group_id=[0], type=1, teacher_id=1)
    assert original != target

def test_model():
    model = cplex.Cplex()
    model.set_results_stream(None) # ignore standart  output
    model.variables.add(obj=[1, -1],
                            lb=[0, 0], 
                            ub=[10, 10])
    add_constraint(model, [1], '<=', 2)
    add_constraint(model, [0], '>=', 2)
    model.solve()
    assert [2.0, 2.0] == model.solution.get_values()

def test_soft():
    model = cplex.Cplex()
    model.set_results_stream(None) # ignore standart  output
    model.variables.add(obj=[1, -1],
                            lb=[0, 0], 
                            ub=[4, 10])
    add_constraint(model, [0], '>=', 5)
    add_constraint(model, [1], '<=', 5)
    model.solve()
    assert 3 == model.solution.get_status() # infeasiable

    model = cplex.Cplex()
    model.set_results_stream(None) # ignore standart  output
    model.variables.add(obj=[1, -1],
                            lb=[0, 6], 
                            ub=[4, 10])
    add_soft_constraint(model, [0], '>=', 5, [1], 2, 1)
    add_soft_constraint(model, [1], '<=', 5, [1], 2, -1)
    model.solve()

    assert [4.0, 6.0, 1.0, 1.0] == model.solution.get_values()


def test_mix():
    model = cplex.Cplex()
    model.set_results_stream(None) # ignore standart  output
    model.variables.add(obj=[1],
                            lb=[0], 
                            ub=[4],
                            names=['MY_VAR'])
    model.variables.add(obj=[2],
                            lb=[0], 
                            ub=[4])
    add_soft_constraint(model, [1,'MY_VAR'], '>=', 5, [1,1], 0.5, 1)
    model.solve()
    print(model.solution.get_values())