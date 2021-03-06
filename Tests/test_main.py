import pytest

from university import *
from general_utils import RoomType, debug, set_debug, Config, global_config, GroupType
from solver import Solver
import copy
from beautiful_out import open_as_html

def setup_function():
    global_config.reset()
    print()

def test_empty():
    university = University()
    solver = Solver(university)
    res, _ , _ = solver.solve()
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
    res, _ , _ = solver.solve()
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
    res, output , _ = solver.solve()
    assert not res
    
    university = University(0,1,1)
    fill(university)

    solver = Solver(university)
    res, _ , _ = solver.solve()
    assert res
    
def test_multiple_teachers():
    university = University(0, 0, 1)
    university.add_room(1, 120, RoomType.LECTURE,   100) 
    university.add_room(2, 121, RoomType.PRACTICE,  30) 
    university.add_group("16-pmi", 30, GroupType.BACHELOR)
    university.add_group("17-pmi", 30, GroupType.BACHELOR)
    university.add_teacher('Бычков И С')

    temp_university = copy.deepcopy(university)
    university.add_lesson("прога", ['16-pmi'], 1, RoomType.LECTURE,  ['Бычков И С'])
    university.add_lesson("прога", ['17-pmi'], 1, RoomType.PRACTICE,  ['Бычков И С'])

    solver = Solver(university)
    res, _ , _ = solver.solve()
    assert not res
    temp_university.add_teacher('Фейк')
    temp_university.add_lesson("прога", ['16-pmi'], 1, RoomType.LECTURE,  ['Бычков И С', 'Фейк'])
    temp_university.add_lesson("прога", ['17-pmi'], 1, RoomType.PRACTICE,  ['Бычков И С', 'Фейк'])

    solver = Solver(temp_university)
    res, _ , _ = solver.solve()
    assert res

def test_count_of_lessons():
    university = University()
    university.add_room(1, 121, RoomType.PRACTICE,  30) 
    university.add_room(1, 120, RoomType.LECTURE,   100) 
    university.add_group("16-pmi", 30, GroupType.BACHELOR)
    university.add_teacher('Бычков И С')
    lecture_count = 10
    practice = university.add_lesson("прога", ['16-pmi'], lecture_count, RoomType.PRACTICE,  ['Бычков И С'])

    solver = Solver(university)
    res, output , _ = solver.solve()
    assert res

    index = 0
    total_lessons = 0
    for group, weeks in sorted(output.items()):
            for week, days in sorted(weeks.items()):
                for day, tss in sorted(days.items()):
                    for ts, listt in sorted(tss.items()):
                        total_lessons += 1
    assert total_lessons == lecture_count

def test_order_lessons():
    global_config.bachelor_time_slots_per_day = 5
    global_config.time_slots_per_day_available = 5
    university = University(0,1,1)
    university.add_room(1, 121, RoomType.PRACTICE,  30) 
    university.add_room(1, 120, RoomType.LECTURE,   100) 
    university.add_group("16-pmi", 30, GroupType.BACHELOR)
    university.add_teacher('Бычков И С')
    lecture_count = university.study_weeks*2
    practice_count = university.study_weeks*4
    practice = university.add_lesson("прога", ['16-pmi'], practice_count, RoomType.PRACTICE,  ['Бычков И С'])
    lection = university.add_lesson("прога", ['16-pmi'], lecture_count, RoomType.LECTURE,  ['Бычков И С'])

    practice.should_be_after_lesson(lection)

    solver = Solver(university)
    res, output , _ = solver.solve()
    assert res

    open_as_html(output, university)
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
    res, _ , _ = solver.solve()
    assert not res

    global_config.max_lessons_per_day = 6
    solver = Solver(university)
    res, _ , _ = solver.solve()
    assert res

def test_max_lessons_per_week():
    global_config.max_lessons_per_week = 2

    university = University(0,5,1)
    university.add_room(1, 120, RoomType.LECTURE,   100) 
    university.add_group("16-pmi", 30, GroupType.BACHELOR)
    university.add_teacher('Бычков И С')
    university.add_lesson("прога", ['16-pmi'], 5, RoomType.LECTURE,  ['Бычков И С'])

    solver = Solver(university)
    res, _ , _ = solver.solve()
    assert not res

    global_config.max_lessons_per_week = 6
    solver = Solver(university)
    res, _ , _ = solver.solve()
    assert res

def test_teacher_ban_some_tss():
    global_config.time_slots_per_day_available = 3
    global_config.soft_constraints.timeslots_penalty = [0,0,0]

    university = University(0,0,1)
    university.add_room(1, 120, RoomType.LECTURE,   100) 
    university.add_group("16-pmi", 30, GroupType.BACHELOR)
    teacher = university.add_teacher('Бычков И С')
    teacher.ban_time_slots(0, 0, 0)
    university.add_lesson("прога", ['16-pmi'], 3, RoomType.LECTURE,  ['Бычков И С'])

    solver = Solver(university)
    res, _ , _ = solver.solve()
    assert not res

    global_config.time_slots_per_day_available = 4
    global_config.soft_constraints.timeslots_penalty = [0,0,0,0]
    solver = Solver(university)
    res, _ , _ = solver.solve()
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
    res, output , _ = solver.solve()
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
    global_config.windows_penalty = -1

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
    res, output , _ = solver.solve()
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
    global_config.windows_penalty = -1

    university = University()
    university.add_room(1, 120, RoomType.LECTURE,   100) 
    university.add_room(1, 121, RoomType.LECTURE,   100) 
    university.add_group("16-pmi", 30, GroupType.BACHELOR) 
    university.add_group("16-pi", 30, GroupType.BACHELOR) 


    university.add_teacher('Бычков И С')
    university.add_teacher('Прогер')
    university.add_lesson("прога", ['16-pmi'], 10, RoomType.LECTURE,  ['Бычков И С', 'Прогер'])
    university.add_lesson("прога", ['16-pi'], 10, RoomType.LECTURE,  ['Бычков И С', 'Прогер'])


    solver = Solver(university)
    res, output , _ = solver.solve()
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

def test_ban_windows_soft():
    global_config.time_slots_per_day_available = 4
    global_config.soft_constraints.timeslots_penalty = [0,0,0,0]
    
    university = University(0, 0, 1)

    university.add_room(1, 120, RoomType.LECTURE,   100) 
    university.add_group("16-pmi", 30, GroupType.BACHELOR) 


    teacher = university.add_teacher('Бычков И С')
    teacher.ban_time_slots(0, 0, 1)
    university.add_lesson("прога", ['16-pmi'], 3, RoomType.LECTURE,  ['Бычков И С'])

    solver = Solver(university)

    # in this case it is expected, that solution doesn't exists
    global_config.windows_penalty = -1
    res, output , _ = solver.solve()
    assert not res

    global_config.windows_penalty = 1
    solver1 = Solver(university)
    res, _, _ = solver1.solve()
    assert res

def test_one_teacher_per_lesson():
    university = University()
    university.add_room(1, 120, RoomType.LECTURE,   100) 
    university.add_room(1, 121, RoomType.LECTURE,   100) 
    university.add_group("16-pmi", 30, GroupType.BACHELOR) 
    university.add_group("16-pi", 30, GroupType.BACHELOR) 


    university.add_teacher('Бычков И С')
    university.add_teacher('Прогер')
    university.add_lesson("прога", ['16-pmi'], 10, RoomType.LECTURE,  ['Бычков И С', 'Прогер'])
    university.add_lesson("прога", ['16-pi'], 10, RoomType.LECTURE,  ['Бычков И С', 'Прогер'])


    solver = Solver(university)
    res, output , _ = solver.solve()
    assert res
    for group, weeks in sorted(output.items()):
        teachers = set()
        for _, days in sorted(weeks.items()):
            for _, tss in sorted(days.items()):
                for ts, data in sorted(tss.items()):
                    _, _, _, _, teacher, _ = data
                    teachers.add(teacher)

        assert len(teachers) == 1

def test_lessons_in_similar_day_and_ts_during_module():
    university = University(weeks=4)
    university.add_room(1, 120, RoomType.LECTURE,   100)
    university.add_group("16-pmi", 30, GroupType.BACHELOR)


    university.add_teacher('Бычков И С')
    university.add_teacher('Чистяков В В')
    university.add_lesson("прога", ['16-pmi'], 24, RoomType.LECTURE,  ['Бычков И С'])
    university.add_lesson("матан", ['16-pmi'], 8, RoomType.LECTURE,  ['Чистяков В В'])

    solver = Solver(university)
    res, output , _ = solver.solve()
    assert res
    
    #open_as_html(output, university)

    for group, weeks in sorted(output.items()):
        ts_by_weeks_days_and_lessons = {}
        for week, days in sorted(weeks.items()):
            for day, tss in sorted(days.items()):
                for ts, data in sorted(tss.items()):
                    corpus, room, lesson, _type, teacher, other_groups = data
                    ts_by_weeks_days_and_lessons.setdefault(week, {}).setdefault(day, {}).setdefault(lesson.self_index, []).append(ts)

        for i in range(len(ts_by_weeks_days_and_lessons)-2):
            assert ts_by_weeks_days_and_lessons[i] == ts_by_weeks_days_and_lessons[i+2]

def test_similar_room_every_week():
    university = University(weeks=4)
    university.add_room(1, 120, RoomType.LECTURE,   100)
    university.add_room(1, 123, RoomType.LECTURE,   100)
    university.add_room(1, 122, RoomType.LECTURE,   100)
    university.add_room(1, 136, RoomType.LECTURE,   100)
    university.add_room(1, 326, RoomType.LECTURE,   100)
    university.add_room(1, 426, RoomType.LECTURE,   100)
    university.add_room(1, 226, RoomType.LECTURE,   100)
    university.add_room(1, 222, RoomType.LECTURE,   100)
    university.add_room(1, 236, RoomType.LECTURE,   100)
    university.add_group("16-pmi", 30, GroupType.BACHELOR)


    university.add_teacher('Бычков И С').ban_time_slots(day=2).ban_time_slots(day=3)
    university.add_lesson("прога", ['16-pmi'], 36, RoomType.LECTURE,  ['Бычков И С'])

    solver = Solver(university)
    res, output , _ = solver.solve()
    assert res
    
    #open_as_html(output, university)

    for group, weeks in sorted(output.items()):
        ts_by_days = {}
        for week, days in sorted(weeks.items()):
            for day, tss in sorted(days.items()):
                for ts, data in sorted(tss.items()):
                    corpus, room, lesson, _type, teacher, other_groups = data
                    ts_by_days.setdefault(day, set()).add(room)
        
        for day in university.study_days:
            assert len(ts_by_days.get(day, [])) <= 1

def test_no_lessons_in_saturday():
    university = University(weeks=4)
    university.add_room(1, 1, RoomType.LECTURE, 10)
    university.add_group('Group', 1, GroupType.BACHELOR)
    university.add_teacher('Teacher').ban_time_slots(day=2).ban_time_slots(day=3).ban_time_slots(day=1).ban_time_slots(timeslot=3)
    university.add_lesson('Lesson1', ['Group'], 12, RoomType.LECTURE, ['Teacher'])
    university.add_lesson('Lesson2', ['Group'], 12, RoomType.LECTURE, ['Teacher'])
    university.add_lesson('Lesson3', ['Group'], 12, RoomType.LECTURE, ['Teacher'])

    solver = Solver(university)
    res, out , _ = solver.solve()
    assert res

    for group, weeks in sorted(out.items()):
        for week, days in sorted(weeks.items()):
            assert global_config.study_days-1 in days

    global_config.soft_constraints.last_day_in_week_penalty = 300

    solver1 = Solver(university)
    res, out, _ = solver1.solve()
    assert res

    for group, weeks in sorted(out.items()):
        for week, days in sorted(weeks.items()):
            assert not global_config.study_days-1 in days

def test_no_lessons_first_timeslot():
    global_config.soft_constraints.last_day_in_week_penalty = 0
    university = University(weeks=4)
    university.add_room(1, 1, RoomType.LECTURE, 10)
    university.add_group('Group', 1, GroupType.BACHELOR)
    university.add_teacher('Teacher').ban_time_slots(day=2).ban_time_slots(day=3).ban_time_slots(day=1).ban_time_slots(timeslot=2)
    university.add_lesson('Lesson1', ['Group'], 8, RoomType.LECTURE, ['Teacher'])
    university.add_lesson('Lesson2', ['Group'], 8, RoomType.LECTURE, ['Teacher'])
    university.add_lesson('Lesson3', ['Group'], 8, RoomType.LECTURE, ['Teacher'])

    solver = Solver(university)
    res, out , _ = solver.solve()
    assert res
    
    #open_as_html(out, university)

    for group, weeks in sorted(out.items()):
        for week, days in sorted(weeks.items()):
            for day, tss in sorted(days.items()):
                for ts, data in sorted(tss.items()):
                    assert ts > 0

def test_lessons_grouped_by_lesson_id_during_week():
    university = University(weeks=4)
    university.add_room(1, 1, RoomType.PRACTICE, 10)
    university.add_group('Group', 1, GroupType.BACHELOR).ban_time_slots(day=0)
    university.add_teacher('Teacher').ban_time_slots(day=1).ban_time_slots(day=2)
    university.add_lesson('Lesson1', ['Group'], 12, RoomType.PRACTICE, ['Teacher'])
    university.add_lesson('Lesson2', ['Group'], 12, RoomType.PRACTICE, ['Teacher'])
    university.add_lesson('Lesson3', ['Group'], 12, RoomType.PRACTICE, ['Teacher'])

    solver = Solver(university)
    res, out , _ = solver.solve()
    open_as_html(out, university)

    for group, weeks in sorted(out.items()):
        for week, days in sorted(weeks.items()):
            for day, tss in sorted(days.items()):
                uniq_lessons = set()
                for ts, data in sorted(tss.items()):
                    corpus, room, lesson, _type, teacher, other_groups = data
                    uniq_lessons.add(lesson.self_index)
                assert len(uniq_lessons) <= 1

def test_lessons_grouped_by_lesson_id_during_day():
    university = University(weeks=4)
    university.add_room(1, 1, RoomType.PRACTICE, 10)
    university.add_group('Group', 1, GroupType.BACHELOR).ban_time_slots(day=0)
    university.add_teacher('Teacher').ban_time_slots(day=1).ban_time_slots(day=2)
    university.add_lesson('Lesson1', ['Group'], 16, RoomType.PRACTICE, ['Teacher'])
    university.add_lesson('Lesson2', ['Group'], 16, RoomType.PRACTICE, ['Teacher'])
    university.add_lesson('Lesson3', ['Group'], 16, RoomType.PRACTICE, ['Teacher'])

    solver = Solver(university)
    res, out , _ = solver.solve()
   # open_as_html(out, university)

    for group, weeks in sorted(out.items()):
        for week, days in sorted(weeks.items()):
            for day, tss in sorted(days.items()):
                lessons_cache = []
                for ts, data in sorted(tss.items()):
                    corpus, room, lesson, _type, teacher, other_groups = data
                    if not lesson.self_index in lessons_cache:
                        lessons_cache.append(lesson.self_index)
                    else:
                        assert lessons_cache.index(lesson.self_index) == len(lessons_cache) -1

def test_lessons_balanced_every_week_every_day():
    global_config.soft_constraints.timeslots_penalty = [0,0,0,0,0,0,0,0]

    university = University(weeks=3)
    university.add_room(1, 1, RoomType.PRACTICE, 10)
    university.add_group('Group', 1, GroupType.BACHELOR)
    university.add_teacher('Teacher').ban_time_slots(day=1).ban_time_slots(day=2)
    university.add_lesson('Lesson1', ['Group'], 3, RoomType.PRACTICE, ['Teacher'])
    university.add_lesson('Lesson2', ['Group'], 5, RoomType.PRACTICE, ['Teacher'])
    university.add_lesson('Lesson3', ['Group'], 4, RoomType.PRACTICE, ['Teacher'])
    university.add_lesson('Lesson4', ['Group'], 3, RoomType.PRACTICE, ['Teacher'])


    solver = Solver(university)
    res, out , _ = solver.solve()
    #open_as_html(out, university)

    for group, weeks in sorted(out.items()):
        lessons_by_day = {}
        timeslots_by_day = {}
        for week, days in sorted(weeks.items()):
            for day, tss in sorted(days.items()):
                for ts, data in sorted(tss.items()):
                    corpus, room, lesson, _type, teacher, other_groups = data
                    timeslots_by_day.setdefault(day, set()).add(ts)
                lessons_by_day.setdefault(day, 0)
                lessons_by_day[day] = max((lessons_by_day[day], len(tss)))
        for day, count in lessons_by_day.items():
            ts_values = timeslots_by_day[day]
            assert count == len(ts_values)

def test_friend_lessons():
    university = University(weeks=2)
    university.add_room(1, 1, RoomType.LECTURE | RoomType.PRACTICE, 10)
    university.add_group('Group', 1, GroupType.BACHELOR)
    university.add_teacher('Teacher').ban_time_slots(day=1).ban_time_slots(day=6)

    count = 8
    lect = university.add_lesson('Lesson', ['Group'], count, RoomType.LECTURE, ['Teacher'])
    practice = university.add_lesson('Lesson', ['Group'], count, RoomType.PRACTICE, ['Teacher'])

    practice.should_be_after_lesson(lect)
    university.add_friends_lessons([lect, practice])


    solver = Solver(university)
    res, out , _ = solver.solve()
    #open_as_htmlhtml(out, university)

    for group, weeks in sorted(out.items()):
        for week, days in sorted(weeks.items()):
            for day, tss in sorted(days.items()):
                uniq_lessons = set()
                for ts, data in sorted(tss.items()):
                    corpus, room, lesson, _type, teacher, other_groups = data
                    uniq_lessons.add(lesson.self_index)
                assert len(uniq_lessons) == 0 or len(uniq_lessons) == 2

def test_friend_lessons_diff_groups_diff_lections():
    university = University(weeks=2)
    university.add_room(1, 1, RoomType.LECTURE | RoomType.PRACTICE, 10)
    university.add_group('Group1', 1, GroupType.BACHELOR)
    university.add_group('Group2', 1, GroupType.BACHELOR)
    university.add_teacher('Teacher').ban_time_slots(day=0)

    count = 4
    lect1 = university.add_lesson('Lesson', ['Group1'], count, RoomType.LECTURE, ['Teacher'])
    lect2 = university.add_lesson('Lesson', ['Group2'], count, RoomType.LECTURE, ['Teacher'])
    practice1 = university.add_lesson('Lesson', ['Group1'], count, RoomType.PRACTICE, ['Teacher'])
    practice2 = university.add_lesson('Lesson', ['Group2'], count, RoomType.PRACTICE, ['Teacher'])

    practice1.should_be_after_lesson(lect1)
    practice2.should_be_after_lesson(lect2)

    university.add_friends_lessons([lect1, practice1])
    university.add_friends_lessons([lect2, practice2])


    solver = Solver(university)
    res, out , _ = solver.solve()
    #open_as_html(out, university)

    for group, weeks in sorted(out.items()):
        for week, days in sorted(weeks.items()):
            for day, tss in sorted(days.items()):
                uniq_lessons = set()
                for ts, data in sorted(tss.items()):
                    corpus, room, lesson, _type, teacher, other_groups = data
                    uniq_lessons.add(lesson.self_index)
                assert len(uniq_lessons) == 0 or len(uniq_lessons) == 2

def test_friend_lessons_diff_groups_common_lecture():
    global_config.timelimit_for_solve = 0

    university = University(weeks=2)
    university.add_room(1, 1, RoomType.LECTURE | RoomType.PRACTICE, 10)
    university.add_room(1, 2, RoomType.LECTURE | RoomType.PRACTICE, 10)
    university.add_room(1, 3, RoomType.LECTURE | RoomType.PRACTICE, 10)
    university.add_room(1, 4, RoomType.LECTURE | RoomType.PRACTICE, 10)
    university.add_group('Group1', 1, GroupType.BACHELOR).ban_time_slots(day=3)
    university.add_group('Group2', 1, GroupType.BACHELOR).ban_time_slots(day=2).ban_time_slots(day=1).ban_time_slots(day=3)
    university.add_teacher('Teacher')
    university.add_teacher('Teacher1')

    count = 4
    lect = university.add_lesson('Lesson', ['Group1', 'Group2'], count, RoomType.LECTURE, ['Teacher'])
    practice1 = university.add_lesson('Lesson', ['Group1'], count, RoomType.PRACTICE, ['Teacher'])
    practice2 = university.add_lesson('Lesson', ['Group2'], count, RoomType.PRACTICE, ['Teacher'])
    for i in range(count):
        university.add_lesson('DummyLesson'+str(i), ['Group1'], 1, RoomType.PRACTICE, ['Teacher1'])
        university.add_lesson('DummyLesson'+str(i), ['Group2'], 1, RoomType.PRACTICE, ['Teacher1'])    

    practice1.should_be_after_lesson(lect)
    practice2.should_be_after_lesson(lect)

    university.add_friends_lessons([lect, practice1])
    university.add_friends_lessons([lect, practice2])


    solver = Solver(university)
    res, out , by_teacher = solver.solve()
    #open_as_html(out, university, by_teacher)

    for group, weeks in sorted(out.items()):
        for week, days in sorted(weeks.items()):
            for day, tss in sorted(days.items()):
                uniq_lessons = set()
                for ts, data in sorted(tss.items()):
                    corpus, room, lesson, _type, teacher, other_groups = data
                    uniq_lessons.add(lesson.self_index)
                print(uniq_lessons)
                assert len(uniq_lessons) == 0 or len(uniq_lessons) == 3

