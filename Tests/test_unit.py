import pytest

from university import *
from general_utils import RoomType, debug, set_debug, Config, global_config, GroupType
from solver import *
import copy
from beautiful_out import open_as_html
from id_wrapper import *
import cplex

def setup_function():
    global_config.reset()
    global variables_filter_cache
    variables_filter_cache.clear()
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

def test_timeslots_filter():
    timeslots = {}
    id = 0
    for week in range(0, 2):
        for day in range(0, 7):
            timeslots[id] = TimeSlotWrapper(week=week, day=day, corpus=1, room=1, timeslot=1, 
                                            lesson=1, group_id=[0], type=1, teacher_id=1)
            id += 1

    res = get_indexes_of_timeslots_by_filter(timeslots, week = 1)
    assert all(id >= 7 for id in res)

    res = get_indexes_of_timeslots_by_filter(timeslots, week = 0)
    assert all(id <= 6 for id in res)

    for day in range(0, 7):
        res = get_indexes_of_timeslots_by_filter(timeslots, day = day)
        assert all(id % 7 == day for id in res)

    
    for day in range(0, 7):
        res = get_indexes_of_timeslots_by_filter(timeslots, day = day, week = 0)
        assert all(id % 7 == day for id in res) and all(id <= 6 for id in res)

    for day in range(0, 7):
        res = get_indexes_of_timeslots_by_filter(timeslots, day = day, week = 1)
        assert all(id % 7 == day for id in res) and all(id >= 6 for id in res)
    
    assert len(get_indexes_of_timeslots_by_filter(timeslots)) == 2*7
    assert len(get_indexes_of_timeslots_by_filter(timeslots, week=10)) == 0

def test_timeslots_filter_2():
    timeslots = {}
    id = 0

    timeslots[id] = TimeSlotWrapper(week=1, day=1, corpus=1, room=1, timeslot=1, 
                                    lesson=1, group_id=[0], type=1, teacher_id=1)
    id += 1

    timeslots[id] = TimeSlotWrapper(week=1, day=1, corpus=1, room=1, timeslot=1, 
                                    lesson=1, group_id=[0,1,2,3], type=1, teacher_id=1)
    id += 1
    timeslots[id] = TimeSlotWrapper(week=1, day=1, corpus=1, room=1, timeslot=1, 
                                    lesson=1, group_id=[2,3], type=1, teacher_id=1)
    id += 1

    assert len(get_indexes_of_timeslots_by_filter(timeslots, group_id=0)) == 2
    assert len(get_indexes_of_timeslots_by_filter(timeslots, group_id=1)) == 1
    assert len(get_indexes_of_timeslots_by_filter(timeslots, group_id=2)) == 2
    assert len(get_indexes_of_timeslots_by_filter(timeslots, group_id=[2, 3])) == 2
    assert len(get_indexes_of_timeslots_by_filter(timeslots, group_id=[])) == 3

def test_corpus_tracker():
    tracker = CorpusTrackerWrapper(1, 1, 1)
    assert tracker.group_id == -1 and tracker.teacher_id == -1

    tracker = CorpusTrackerWrapper(1, 1, 1, 3)
    assert tracker.group_id == 3 and tracker.teacher_id == None

    tracker = CorpusTrackerWrapper(1, 1, 1, teacher_id = 3)
    assert tracker.group_id == None and tracker.teacher_id == 3

    with pytest.raises(Exception) as e:
        CorpusTrackerWrapper(group_id = 2, teacher_id = 3)
    
def test_corpus_tracker_filter():
    corpus_tracker = {}
    id = 0

    group_id = 1
    teacher_id = -1
    for corpus in range(0, 2):
        for week in range(0, 2):
            for day in range(0, 7):
                corpus_tracker[id] = CorpusTrackerWrapper(corpus=corpus, week=week, day=day, group_id=group_id, teacher_id=teacher_id)
                id += 1
    
    assert len(get_corpus_tracker_by_filter(corpus_tracker)) == 2*2*7
    assert len(get_corpus_tracker_by_filter(corpus_tracker, corpus=0)) == 2*7
    assert len(get_corpus_tracker_by_filter(corpus_tracker, corpus=1)) == 2*7
    assert len(get_corpus_tracker_by_filter(corpus_tracker, corpus=2)) == 0
    assert all(i < 2*7 for i in get_corpus_tracker_by_filter(corpus_tracker, corpus=0))
    assert all(i >= 2*7 for i in get_corpus_tracker_by_filter(corpus_tracker, corpus=1))
    assert len(get_corpus_tracker_by_filter(corpus_tracker, group_id=1)) == 2*2*7
    assert len(get_corpus_tracker_by_filter(corpus_tracker, group_id=2)) == 0
    with pytest.raises(Exception) as e:
        get_corpus_tracker_by_filter(corpus_tracker, group_id=2, teacher_id=3)

def test_corpus_tracker_filter_2():
    corpus_tracker = {}
    id = 0

    for corpus in range(0, 2):
        for week in range(0, 2):
            for day in range(0, 7):
                corpus_tracker[id] = CorpusTrackerWrapper(corpus=corpus, week=week, day=day, group_id=1, teacher_id=-1)
                id += 1
    
    for corpus in range(0, 2):
        for week in range(0, 2):
            for day in range(0, 7):
                corpus_tracker[id] = CorpusTrackerWrapper(corpus=corpus, week=week, day=day, group_id=-1, teacher_id=1)
                id += 1

    assert len(get_corpus_tracker_by_filter(corpus_tracker, corpus=0)) == 2*7*2
    assert len(get_corpus_tracker_by_filter(corpus_tracker, group_id=1)) == 2*2*7
    assert len(get_corpus_tracker_by_filter(corpus_tracker, teacher_id=1)) == 2*2*7
    assert all(i >= 2*2*7 for i in get_corpus_tracker_by_filter(corpus_tracker, teacher_id=1))
    assert all(i < 2*2*7 for i in get_corpus_tracker_by_filter(corpus_tracker, group_id=1))

def test_room_tracker():
    tracker = RoomTrackerWrapper(1, 1, 1, 1)
    assert tracker.group_id == -1 and tracker.teacher_id == -1

    tracker = RoomTrackerWrapper(1, 1, 1, 1, 3)
    assert tracker.group_id == 3 and tracker.teacher_id == None

    tracker = RoomTrackerWrapper(1, 1, 1, 1, teacher_id = 3)
    assert tracker.group_id == None and tracker.teacher_id == 3

    with pytest.raises(Exception) as e:
        RoomTrackerWrapper(group_id = 2, teacher_id = 3)
    
def test_room_tracker_filter_as_corpus():
    room_tracker = {}
    id = 0

    group_id = 1
    teacher_id = -1
    for corpus in range(0, 2):
        for week in range(0, 2):
            for day in range(0, 7):
                room_tracker[id] = RoomTrackerWrapper(corpus=corpus, week=week, day=day, group_id=group_id, teacher_id=teacher_id)
                id += 1

    assert len(get_room_tracker_by_filter(room_tracker)) == 2*2*7
    assert len(get_room_tracker_by_filter(room_tracker, corpus=0)) == 2*7
    assert len(get_room_tracker_by_filter(room_tracker, corpus=1)) == 2*7
    assert len(get_room_tracker_by_filter(room_tracker, corpus=2)) == 0
    assert all(i < 2*7 for i in get_room_tracker_by_filter(room_tracker, corpus=0))
    assert all(i >= 2*7 for i in get_room_tracker_by_filter(room_tracker, corpus=1))
    assert len(get_room_tracker_by_filter(room_tracker, group_id=1)) == 2*2*7
    assert len(get_room_tracker_by_filter(room_tracker, group_id=2)) == 0
    with pytest.raises(Exception) as e:
        get_room_tracker_by_filter(room_tracker, group_id=2, teacher_id=3)

def test_room_tracker_filter():
    room_tracker = {}
    id = 0

    group_id = 1
    teacher_id = -1
    for room in range(0, 3):
        for corpus in range(0, 2):
            for week in range(0, 2):
                for day in range(0, 7):
                    room_tracker[id] = RoomTrackerWrapper(room=room, corpus=corpus, week=week, day=day, group_id=group_id, teacher_id=teacher_id)
                    id += 1
    
    assert len(get_room_tracker_by_filter(room_tracker, room=1)) == 2*2*7
    assert len(get_room_tracker_by_filter(room_tracker, room=2)) == 2*2*7
    assert len(get_room_tracker_by_filter(room_tracker, room=-1)) == 3*2*2*7
    assert len(get_room_tracker_by_filter(room_tracker, room=4)) == 0
    assert all(i < 2*2*7 for i in get_room_tracker_by_filter(room_tracker, room=0))

def test_lesson_tracker():
    tracker = LessonTrackerWrapper(week=1, day=1, lesson=2, group_id=1)
    other = LessonTrackerWrapper(week=1, day=1, lesson=1, teacher_id=2)
    assert tracker != other
    assert other != tracker
    assert tracker == tracker
    assert other == other

    tracker = LessonTrackerWrapper(week=1, day=1, lesson=2)
    other = LessonTrackerWrapper(week=1, day=1, lesson=1)
    assert tracker != other
    assert other != tracker
    assert tracker == tracker
    assert other == other

def test_lesson_tracker_filter():
    lesson_tracker = {}
    id = 0

    for week in range(0, 2):
        for day in range(0, 2):
            for lesson in range(0, 3):
                lesson_tracker[id] = LessonTrackerWrapper(week=week, day=day, lesson=lesson, group_id=1, teacher_id=-1)
                id += 1
    
    for week in range(0, 2):
        for day in range(0, 2):
            for lesson in range(0, 3):
                lesson_tracker[id] = LessonTrackerWrapper(week=week, day=day, lesson=lesson, group_id=-1, teacher_id=2)
                id += 1

    assert len(get_lesson_tracker_by_filter(lesson_tracker, teacher_id=1)) == 0
    assert len(get_lesson_tracker_by_filter(lesson_tracker, teacher_id=2)) == 2*2*3
    assert len(get_lesson_tracker_by_filter(lesson_tracker, day=1)) == 2*2*3
    assert len(get_lesson_tracker_by_filter(lesson_tracker, lesson_id=1)) == 2*2*2
    assert all(i % 3 == 1 for i in get_lesson_tracker_by_filter(lesson_tracker, lesson_id=1))

def test_getter_return_not_reference():
    trackers = {}
    trackers[0] = TimeSlotWrapper()
    indexes = get_indexes_of_timeslots_by_filter(trackers)
    assert len(indexes) == 1
    indexes.append(1)
    assert len(indexes) == 2

    indexes = get_indexes_of_timeslots_by_filter(trackers)
    assert len(indexes) == 1
    indexes.append(1)
    assert len(indexes) == 2

    new_indexes = get_indexes_of_timeslots_by_filter(trackers)
    assert len(new_indexes) == 1
    new_indexes.append(1)
    assert len(new_indexes) == 2

    last_indexes = get_indexes_of_timeslots_by_filter(trackers)
    assert len(last_indexes) == 1

#