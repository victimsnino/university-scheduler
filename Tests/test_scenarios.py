import pytest

from university import *
from general_utils import RoomType, debug, set_debug, Config, global_config, GroupType
from solver import Solver
import copy
from beautiful_out import open_as_html

def setup_function():
    global_config.reset()
    print()

def fill_16pmi(university):
    lect = university.add_lesson("Случайные процессы", ['16-pmi'], 11, RoomType.LECTURE,  ['Колданов'])
    practice = university.add_lesson("Случайные процессы", ['16-pmi'], 11, RoomType.PRACTICE,  ['Колданов'])
    practice.should_be_after_lesson(lect)
    university.add_friends_lessons([lect, practice])

    university.add_lesson("Научный семинар", ['16-pmi'], 10, RoomType.LECTURE,  ['Бабкина'])
    university.add_lesson("Академическое письмо", ['16-pmi'], 12, RoomType.PRACTICE,  ['Фролова'])
    university.add_lesson("Компьютерная лингвистика", ['16-pmi'], 22, RoomType.LECTURE,  ['Слащинин'])
    lect = university.add_lesson("Интернет вещей", ['16-pmi'], 11, RoomType.LECTURE,  ['Зеленов'])
    practice = university.add_lesson("Интернет вещей", ['16-pmi'], 11, RoomType.COMPUTER,  ['Зеленов']).should_be_after_lesson(lect)
    university.add_friends_lessons([lect, practice])

def test_full_module_for_our_group():
    global_config.soft_constraints.max_lessons_per_day = 3
    weeks = 12
    university = University(start_from_day_of_week = 3, end_by_day_of_week=1,weeks=weeks)
    
    LVOV = 1
    RADIK = 2

    university.add_room(RADIK, 206, RoomType.LECTURE | RoomType.PRACTICE, 40) 
    university.add_room(RADIK, 303, RoomType.COMPUTER,  30)
    university.add_room(LVOV,  309, RoomType.PRACTICE,  25) 

    university.add_group("16-pmi", 22, GroupType.BACHELOR)#.ban_time_slots(day=3, week=2)
    #university.add_group("16-pi", 30, GroupType.BACHELOR) 


    university.add_teacher('Колданов')
    university.add_teacher('Бабкина')
    university.add_teacher('Фролова')
    university.add_teacher('Слащинин')
    university.add_teacher('Зеленов')

    fill_16pmi(university)

    solver = Solver(university)
    res, output , by_teachers = solver.solve()
    assert res

    open_as_html(output, university, by_teachers)

    for group, weeks in sorted(output.items()):
        for _, days in sorted(weeks.items()):
            for _, tss in sorted(days.items()):
                assert len(tss) <= global_config.soft_constraints.max_lessons_per_day

def test_full_module_for_fourth_course():
    weeks = 12
    university = University(start_from_day_of_week = 3, end_by_day_of_week=1,weeks=weeks)
    
    LVOV = 1
    RADIK = 2

    university.add_room(RADIK, 207, RoomType.LECTURE | RoomType.PRACTICE, 40) 
    university.add_room(RADIK, 301, RoomType.LECTURE | RoomType.PRACTICE | RoomType.COMPUTER, 40) 
    university.add_room(RADIK, 302, RoomType.LECTURE | RoomType.PRACTICE | RoomType.COMPUTER, 40) 

    university.add_room(LVOV,  308, RoomType.PRACTICE,  25) 

    university.add_group("16-pmi", 22, GroupType.BACHELOR)

    university.add_teacher('Колданов')
    university.add_teacher('Бабкина')
    university.add_teacher('Фролова')
    university.add_teacher('Слащинин')
    university.add_teacher('Зеленов')

    fill_16pmi(university)
    
    solver = Solver(university)
    res, output , by_teachers = solver.solve()
    assert res

    open_as_html(output, university, by_teachers)

    for group, weeks in sorted(output.items()):
        for _, days in sorted(weeks.items()):
            for _, tss in sorted(days.items()):
                assert len(tss) <= global_config.soft_constraints.max_lessons_per_day


def test_full_module_for_second_course():
    #global_config.soft_constraints.minimize_count_of_rooms_per_day_penalty = 0
    #global_config.timelimit_for_solve = 0
    weeks = 2
    university = University(weeks=weeks)

    university.add_room(1, 147, RoomType.PRACTICE, 100)
    university.add_room(1, 146, RoomType.PRACTICE, 100)
    university.add_room(1, 224, RoomType.LECTURE | RoomType.PRACTICE, 100)
    university.add_room(1, 202, RoomType.PRACTICE, 100)
    university.add_room(1, 301, RoomType.PRACTICE, 100)
    university.add_room(1, 306, RoomType.PRACTICE, 100)

    university.add_room(2, 216, RoomType.PRACTICE, 100)
    university.add_room(2, 402, RoomType.LECTURE | RoomType.PRACTICE, 100)
    

    university.add_group('17bi-1', 15, GroupType.BACHELOR)
    university.add_group('17bi-2', 15, GroupType.BACHELOR)

    university.add_teacher('Демкин')
    university.add_teacher('Семенов')
    university.add_teacher('Куранова')
    university.add_teacher('Колданов')
    university.add_teacher('Фролова')
    university.add_teacher('Казаков')
    university.add_teacher('Калягин')
    university.add_teacher('Асеева')

    lect = university.add_lesson('Алгоритмы и структуры данных', ['17bi-1', '17bi-2'], weeks, RoomType.LECTURE, ['Демкин'])
    practice1 = university.add_lesson('Алгоритмы и структуры данных', ['17bi-1'], weeks, RoomType.PRACTICE, ['Демкин']).should_be_after_lesson(lect)
    practice2 = university.add_lesson('Алгоритмы и структуры данных', ['17bi-2'], weeks, RoomType.PRACTICE, ['Демкин']).should_be_after_lesson(lect)

    university.add_friends_lessons([lect, practice1])
    university.add_friends_lessons([lect, practice2])

    lect = university.add_lesson('Объектно -ориентированное программирование', ['17bi-1', '17bi-2'], weeks/2, RoomType.LECTURE, ['Демкин'])
    practice1 = university.add_lesson('Объектно -ориентированное программирование', ['17bi-1'], weeks/2, RoomType.PRACTICE, ['Демкин']).should_be_after_lesson(lect)
    practice2 = university.add_lesson('Объектно -ориентированное программирование', ['17bi-2'], weeks/2, RoomType.PRACTICE, ['Демкин']).should_be_after_lesson(lect)

    university.add_friends_lessons([lect, practice1])
    university.add_friends_lessons([lect, practice2])

    lect = university.add_lesson('Теория вероятностей', ['17bi-1', '17bi-2'], weeks, RoomType.LECTURE, ['Колданов'])
    practice1 = university.add_lesson('Теория вероятностей', ['17bi-1'], weeks, RoomType.PRACTICE, ['Семенов']).should_be_after_lesson(lect)
    practice2 = university.add_lesson('Теория вероятностей', ['17bi-2'], weeks, RoomType.PRACTICE, ['Семенов']).should_be_after_lesson(lect)

    university.add_friends_lessons([lect, practice1])
    university.add_friends_lessons([lect, practice2])

    lect = university.add_lesson('Моделирование процессов и систем', ['17bi-1', '17bi-2'], weeks, RoomType.LECTURE, ['Асеева'])
    practice1 = university.add_lesson('Моделирование процессов и систем', ['17bi-1'], weeks, RoomType.PRACTICE, ['Куранова']).should_be_after_lesson(lect)
    practice2 = university.add_lesson('Моделирование процессов и систем', ['17bi-2'], weeks, RoomType.PRACTICE, ['Куранова']).should_be_after_lesson(lect)

    university.add_friends_lessons([lect, practice1])
    university.add_friends_lessons([lect, practice2])

    lect = university.add_lesson('Анализ данных', ['17bi-1', '17bi-2'], weeks, RoomType.LECTURE, ['Калягин'])
    practice1 = university.add_lesson('Анализ данных', ['17bi-1'], weeks, RoomType.PRACTICE, ['Казаков']).should_be_after_lesson(lect)
    university.add_friends_lessons([lect, practice1])

    university.add_lesson('Английский язык', ['17bi-1', '17bi-2'],  2*weeks, RoomType.PRACTICE, ['Фролова'])
    university.add_lesson('Английский язык1', ['17bi-1', '17bi-2'], 2*weeks, RoomType.PRACTICE, ['Фролова'])

    solver = Solver(university)
    res, output , by_teachers = solver.solve()
    assert res
    open_as_html(output, university, by_teachers)

    return
    for group, weeks in sorted(output.items()):
        ts_by_days = {}
        for week, days in sorted(weeks.items()):
            for day, tss in sorted(days.items()):
                assert len(tss) == 0 or len(tss) >= 2


