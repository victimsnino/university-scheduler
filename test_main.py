import pytest

from university import University, Lesson
from general_utils import RoomType, debug, set_debug, Config, global_config, GroupType
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
        university.add_group('16-pmi', 1, GroupType.BACHELOR)
        university.add_group('16-pmi', 1, GroupType.BACHELOR)
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
    university.add_group("16-pmi", 30, GroupType.BACHELOR)
    university.add_teacher('Бычков И С')
    university.add_lesson("прога", ['16-pmi'], 5, RoomType.LECTURE,  ['Бычков И С'])

    solver = Solver(university)
    res, _ = solver.solve()
    assert res

def test_ban_changing_corpus():

    def fill(university):
        university.add_room(1, 120, RoomType.LECTURE,   100) 
        university.add_room(2, 121, RoomType.PRACTICE,  30) 
        university.add_group("16-pmi", 30, GroupType.BACHELOR)
        university.add_teacher('Бычков И С')
        university.add_lesson("прога", ['16-pmi'], 1, RoomType.LECTURE,  ['Бычков И С'])
        university.add_lesson("прога", ['16-pmi'], 1, RoomType.PRACTICE,  ['Бычков И С'])

    university = University(0,0,1)
    fill(university)

    solver = Solver(university)
    res, _ = solver.solve()
    assert not res
    
    university = University(0,1,1)
    fill(university)

    solver = Solver(university)
    res, _ = solver.solve()
    assert res
    
def test_multiple_teachers():
    university = University(0, 0, 1)
    university.add_room(1, 120, RoomType.LECTURE,   100) 
    university.add_room(2, 121, RoomType.PRACTICE,  30) 
    university.add_group("16-pmi", 30, GroupType.BACHELOR)
    university.add_group("17-pmi", 30, GroupType.BACHELOR)
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
    university = University(0,5,2)
    university.add_room(1, 121, RoomType.PRACTICE,  30) 
    university.add_room(1, 120, RoomType.LECTURE,   100) 
    university.add_group("16-pmi", 30, GroupType.BACHELOR)
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

def test_max_lessons_per_day():
    global_config.max_lessons_per_day = 2

    university = University(0,0,1)
    university.add_room(1, 120, RoomType.LECTURE,   100) 
    university.add_group("16-pmi", 30, GroupType.BACHELOR)
    university.add_teacher('Бычков И С')
    university.add_lesson("прога", ['16-pmi'], 5, RoomType.LECTURE,  ['Бычков И С'])

    solver = Solver(university)
    res, _ = solver.solve()
    assert not res

    global_config.max_lessons_per_day = 6
    solver = Solver(university)
    res, _ = solver.solve()
    assert res

def test_max_lessons_per_week():
    global_config.max_lessons_per_week = 2

    university = University(0,5,1)
    university.add_room(1, 120, RoomType.LECTURE,   100) 
    university.add_group("16-pmi", 30, GroupType.BACHELOR)
    university.add_teacher('Бычков И С')
    university.add_lesson("прога", ['16-pmi'], 5, RoomType.LECTURE,  ['Бычков И С'])

    solver = Solver(university)
    res, _ = solver.solve()
    assert not res

    global_config.max_lessons_per_week = 6
    solver = Solver(university)
    res, _ = solver.solve()
    assert res

def test_teacher_ban_some_tss():
    global_config.time_slots_per_day_available = 3

    university = University(0,0,1)
    university.add_room(1, 120, RoomType.LECTURE,   100) 
    university.add_group("16-pmi", 30, GroupType.BACHELOR)
    teacher = university.add_teacher('Бычков И С')
    teacher.ban_time_slots(0, 0, 0)
    university.add_lesson("прога", ['16-pmi'], 3, RoomType.LECTURE,  ['Бычков И С'])

    solver = Solver(university)
    res, _ = solver.solve()
    assert not res

    global_config.time_slots_per_day_available = 4
    solver = Solver(university)
    res, _ = solver.solve()
    assert res

def test_magistracy_and_bachelor():
    university = University(0,0,1)
    university.add_room(1, 120, RoomType.LECTURE,   100) 
    university.add_room(1, 121, RoomType.LECTURE,   100) 
    university.add_group("16-pmi", 30, GroupType.BACHELOR) 
    university.add_group("16-pi", 30, GroupType.BACHELOR) 
    university.add_group("16-iad", 30, GroupType.MAGISTRACY) 
    university.add_group("17-iad", 30, GroupType.MAGISTRACY) 

    university.add_teacher('Бычков И С')
    university.add_teacher('Прогер')
    university.add_lesson("прога", ['16-pmi'], 3, RoomType.LECTURE,  ['Бычков И С', 'Прогер'])
    university.add_lesson("прога", ['16-iad'], 2, RoomType.LECTURE,  ['Бычков И С', 'Прогер'])
    university.add_lesson("прога", ['16-pi'], 3, RoomType.LECTURE,  ['Бычков И С', 'Прогер'])
    university.add_lesson("прога", ['17-iad'], 2, RoomType.LECTURE,  ['Бычков И С', 'Прогер'])

    solver = Solver(university)
    res, output = solver.solve()
    assert res
    for group, weeks in sorted(output.items()):
        for _, days in sorted(weeks.items()):
            for _, tss in sorted(days.items()):
                for ts, _ in sorted(tss.items()):
                    if group in [0,1]: # bachelor
                        assert ts < global_config.bachelor_time_slots_per_day
                    else: # magistracy
                        assert ts >= global_config.bachelor_time_slots_per_day

def test_ban_windows_1():
    university = University()
    university.add_room(1, 120, RoomType.LECTURE,   100) 
    university.add_room(1, 121, RoomType.LECTURE,   100) 
    university.add_group("16-pmi", 30, GroupType.BACHELOR) 
    university.add_group("16-pi", 30, GroupType.BACHELOR) 
    university.add_group("16-iad", 30, GroupType.MAGISTRACY) 
    university.add_group("17-iad", 30, GroupType.MAGISTRACY) 

    university.add_teacher('Бычков И С')
    university.add_teacher('Прогер')
    university.add_lesson("прога", ['16-pmi'], 7, RoomType.LECTURE,  ['Бычков И С', 'Прогер'])
    university.add_lesson("прога", ['16-iad'], 2, RoomType.LECTURE,  ['Бычков И С', 'Прогер'])
    university.add_lesson("прога", ['16-pi'], 3, RoomType.LECTURE,  ['Бычков И С', 'Прогер'])
    university.add_lesson("прога", ['17-iad'], 2, RoomType.LECTURE,  ['Бычков И С', 'Прогер'])

    solver = Solver(university)
    res, output = solver.solve()
    assert res
    for group, weeks in sorted(output.items()):
        for _, days in sorted(weeks.items()):
            for _, tss in sorted(days.items()):
                current_ts = -1
                for ts, _ in sorted(tss.items()):
                    if current_ts == -1:
                        current_ts = ts
                        continue
                    
                    assert ts - current_ts <= 1
                    current_ts = ts

def test_ban_windows_2():
    university = University()
    university.add_room(1, 120, RoomType.LECTURE,   100) 
    university.add_room(1, 121, RoomType.LECTURE,   100) 
    university.add_group("16-pmi", 30, GroupType.BACHELOR) 
    university.add_group("16-pi", 30, GroupType.BACHELOR) 


    university.add_teacher('Бычков И С')
    university.add_teacher('Прогер')
    university.add_lesson("прога", ['16-pmi'], 8, RoomType.LECTURE,  ['Бычков И С'])
    university.add_lesson("прога", ['16-pi'], 8, RoomType.LECTURE,  ['Бычков И С'])


    solver = Solver(university)
    res, output = solver.solve()
    assert res
    for group, weeks in sorted(output.items()):
        for _, days in sorted(weeks.items()):
            for _, tss in sorted(days.items()):
                current_ts = -1
                for ts, _ in sorted(tss.items()):
                    if current_ts == -1:
                        current_ts = ts
                        continue
                    
                    assert ts - current_ts <= 1
                    current_ts = ts
