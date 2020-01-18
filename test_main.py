import pytest

from university import University, Lesson
from general_utils import RoomType, debug, set_debug, Config, global_config
from solver import Solver
import copy

def setup_function():
    global_config.reset()

def test_empty():
    university = University()
    solver = Solver(university)
    res, _ = solver.solve()
    assert res

def test_add_group_twice():
    with pytest.raises(Exception) as e:
        university = University()
        university.add_group('16-pmi', 1)
        university.add_group('16-pmi', 1)
    print(e)

def test_add_teacher_twice():
    with pytest.raises(Exception) as e:
        university = University()
        university.add_teacher('t')
        university.add_teacher('t')
    print(e)

def test_add_lesson_without_group():
    with pytest.raises(Exception) as e:
        university = University()
        university.add_teacher('t')
        university.add_lesson('М', ['gr'], 1, RoomType.LECTURE, ['t'])
    print(e)

def test_1_room():
    university = University()
    university.add_room(1, 120, RoomType.LECTURE,   100) 
    university.add_group("16-pmi", 30)
    university.add_teacher('Бычков И С')
    university.add_lesson("прога", ['16-pmi'], 5, RoomType.LECTURE,  ['Бычков И С'])

    solver = Solver(university)
    res, _ = solver.solve()
    assert res

def test_ban_changin_corpus():
    global_config.study_days =  1
    global_config.study_weeks = 1

    university = University()
    university.add_room(1, 120, RoomType.LECTURE,   100) 
    university.add_room(2, 121, RoomType.PRACTICE,  30) 
    university.add_group("16-pmi", 30)
    university.add_teacher('Бычков И С')
    university.add_lesson("прога", ['16-pmi'], 1, RoomType.LECTURE,  ['Бычков И С'])
    university.add_lesson("прога", ['16-pmi'], 1, RoomType.PRACTICE,  ['Бычков И С'])

    solver = Solver(university)
    res, _ = solver.solve()
    assert not res
    
    global_config.study_days =  2
    solver = Solver(university)
    res, _ = solver.solve()
    assert res
    
def test_multiple_teachers():
    global_config.study_days =  1
    global_config.study_weeks = 1

    university = University()
    university.add_room(1, 120, RoomType.LECTURE,   100) 
    university.add_room(2, 121, RoomType.PRACTICE,  30) 
    university.add_group("16-pmi", 30)
    university.add_group("17-pmi", 30)
    university.add_teacher('Бычков И С')
    university.add_teacher('Фейк')

    temp_university = copy.deepcopy(university)
    university.add_lesson("прога", ['16-pmi'], 1, RoomType.LECTURE,  ['Бычков И С'])
    university.add_lesson("прога", ['17-pmi'], 1, RoomType.PRACTICE,  ['Бычков И С'])

    solver = Solver(university)
    res, _ = solver.solve()
    assert not res

    temp_university.add_lesson("прога", ['16-pmi'], 1, RoomType.LECTURE,  ['Бычков И С', 'Фейк'])
    temp_university.add_lesson("прога", ['17-pmi'], 1, RoomType.PRACTICE,  ['Бычков И С', 'Фейк'])

    solver = Solver(temp_university)
    res, _ = solver.solve()
    assert res

def test_order_lessons():
    global_config.study_days =  6
    global_config.study_weeks = 1

    university = University()
    university.add_room(1, 121, RoomType.PRACTICE,  30) 
    university.add_room(1, 120, RoomType.LECTURE,   100) 
    university.add_group("16-pmi", 30)
    university.add_teacher('Бычков И С')
    lecture_count = 10
    practice_count = 5
    practice = university.add_lesson("прога", ['16-pmi'], practice_count, RoomType.PRACTICE,  ['Бычков И С'])
    lection = university.add_lesson("прога", ['16-pmi'], lecture_count, RoomType.LECTURE,  ['Бычков И С'])

    practice.should_be_after_lessons(lection)

    solver = Solver(university)
    res, output = solver.solve()
    assert res

    index = 0
    for group, weeks in sorted(output.items()):
            for week, days in sorted(weeks.items()):
                for day, tss in sorted(days.items()):
                    for ts, listt in sorted(tss.items()):
                        corpus, room, lesson, _type, teacher, other_groups = listt
                        if _type == RoomType.PRACTICE:
                            index -= 1
                        elif _type == RoomType.LECTURE:
                            index += practice_count/lecture_count
                        assert index >= 0
