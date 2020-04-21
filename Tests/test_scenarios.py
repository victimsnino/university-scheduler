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
    lect = university.add_lesson("Случайные процессы", ['16-pmi'], university.study_weeks, RoomType.LECTURE,  ['Колданов'])
    practice = university.add_lesson("Случайные процессы", ['16-pmi'], university.study_weeks, RoomType.PRACTICE,  ['Колданов'])
    practice.should_be_after_lesson(lect)
    university.add_friends_lessons([lect, practice])

    university.add_lesson("Научный семинар", ['16-pmi'], university.study_weeks, RoomType.LECTURE,  ['Бабкина'])
    university.add_lesson("Академическое письмо", ['16-pmi'], university.study_weeks, RoomType.PRACTICE,  ['Фролова'])
    lect = university.add_lesson("Компьютерная лингвистика", ['16-pmi'], university.study_weeks, RoomType.LECTURE,  ['Слащинин'])
    practice = university.add_lesson("Компьютерная лингвистика", ['16-pmi'], university.study_weeks, RoomType.PRACTICE,  ['Слащинин']).should_be_after_lesson(lect)
    university.add_friends_lessons([lect, practice])

    lect = university.add_lesson("Интернет вещей", ['16-pmi'], university.study_weeks, RoomType.LECTURE,  ['Зеленов'])
    practice = university.add_lesson("Интернет вещей", ['16-pmi'], university.study_weeks, RoomType.COMPUTER,  ['Зеленов']).should_be_after_lesson(lect)
    university.add_friends_lessons([lect, practice])

def fill_16bi(university):
    # general
    lect_methods = university.add_lesson("Методы машинного обучения", ['16-bi-1', '16-bi-2'], university.study_weeks, RoomType.LECTURE,  ['Баевский'])
    lect_model = university.add_lesson("Имитационное моделирование", ['16-bi-1', '16-bi-2'], university.study_weeks/2, RoomType.LECTURE,  ['Бабкина'])
    lect_analys = university.add_lesson("Анализ требований", ['16-bi-1', '16-bi-2'], university.study_weeks, RoomType.LECTURE,  ['Визгунов'])

    # 16-bi-2
    university.add_lesson("Академическое письмо", ['16-bi-2'], university.study_weeks, RoomType.PRACTICE,  ['Фролова'])

    pr = university.add_lesson("Анализ требований", ['16-bi-2'], university.study_weeks, RoomType.PRACTICE, ['Ларюшина']).should_be_after_lesson(lect_analys)
    university.add_friends_lessons([lect_analys, pr])

    pr = university.add_lesson("Методы машинного обучения", ['16-bi-2'], university.study_weeks, RoomType.PRACTICE,  ['Баевский']).should_be_after_lesson(lect_methods)
    university.add_friends_lessons([lect_methods, pr])

    pr = university.add_lesson("Имитационное моделирование", ['16-bi-2'], university.study_weeks/2, RoomType.PRACTICE,  ['Бабкина']).should_be_after_lesson(lect_model)
    university.add_friends_lessons([lect_model, pr])

    #16-bi-1
    university.add_lesson("Академическое письмо", ['16-bi-1'], university.study_weeks, RoomType.PRACTICE,  ['Фролова'])

    pr = university.add_lesson("Анализ требований", ['16-bi-1'], university.study_weeks, RoomType.PRACTICE, ['Визгунов']).should_be_after_lesson(lect_analys)
    university.add_friends_lessons([lect_analys, pr])

    pr = university.add_lesson("Методы машинного обучения", ['16-bi-1'], university.study_weeks, RoomType.PRACTICE,  ['Баевский'])#.should_be_after_lesson(lect_methods)
    university.add_friends_lessons([lect_methods, pr])

    pr = university.add_lesson("Имитационное моделирование", ['16-bi-1'], university.study_weeks/2, RoomType.PRACTICE,  ['Бабкина'])#.should_be_after_lesson(lect_model)
    university.add_friends_lessons([lect_model, pr])

def test_full_module_for_our_group():
    global_config.soft_constraints.max_lessons_per_day = 3
    weeks = 12
    university = University(weeks=weeks)
    
    LVOV = 1
    RADIK = 2

    university.add_room(RADIK, 206, RoomType.LECTURE | RoomType.PRACTICE, 40) 
    university.add_room(RADIK, 303, RoomType.COMPUTER,  30)
    university.add_room(LVOV,  309, RoomType.PRACTICE,  25) 

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

def test_full_module_for_16bi():
    weeks = 4
    university = University(weeks=weeks)
    
    LVOV = 1
    RADIK = 2
    PECHOR = 3

    university.add_room(RADIK, 207, RoomType.LECTURE | RoomType.PRACTICE, 45) 
    university.add_room(RADIK, 301, RoomType.LECTURE | RoomType.PRACTICE | RoomType.COMPUTER, 45) 
    university.add_room(RADIK, 302, RoomType.LECTURE | RoomType.PRACTICE | RoomType.COMPUTER, 45) 

    university.add_room(PECHOR, 228, RoomType.PRACTICE | RoomType.COMPUTER, 45) 
    university.add_room(PECHOR, 302, RoomType.LECTURE, 45) 
    university.add_room(PECHOR, 314, RoomType.LECTURE, 45) 
    university.add_room(PECHOR, 216, RoomType.PRACTICE, 45) 
    university.add_room(PECHOR, 230, RoomType.PRACTICE, 45) 

    university.add_room(LVOV,  308, RoomType.PRACTICE,  45) 
    university.add_room(LVOV,  318, RoomType.LECTURE,  45) 
    university.add_room(LVOV,  201, RoomType.PRACTICE,  45) 
    university.add_room(LVOV,  301, RoomType.PRACTICE,  45) 

    university.add_group("16-bi-1", 20, GroupType.BACHELOR)
    university.add_group("16-bi-2", 20, GroupType.BACHELOR)

    university.add_teacher('Бабкина')
    university.add_teacher('Фролова')

    university.add_teacher('Ларюшина')
    university.add_teacher('Баевский')
    university.add_teacher('Визгунов')

    fill_16bi(university)


    solver = Solver(university)
    res, output , by_teachers = solver.solve()
    assert res

    open_as_html(output, university, by_teachers)

    for group, weeks in sorted(output.items()):
        for _, days in sorted(weeks.items()):
            for _, tss in sorted(days.items()):
                assert len(tss) <= global_config.soft_constraints.max_lessons_per_day

def test_full_module_for_fourth_course():
    weeks = 4
    university = University(weeks=weeks)
    
    LVOV = 1
    RADIK = 2
    PECHOR = 3

    university.add_room(RADIK, 207, RoomType.LECTURE | RoomType.PRACTICE, 45) 
    university.add_room(RADIK, 301, RoomType.LECTURE | RoomType.PRACTICE | RoomType.COMPUTER, 45) 
    university.add_room(RADIK, 302, RoomType.LECTURE | RoomType.PRACTICE | RoomType.COMPUTER, 45) 

    university.add_room(PECHOR, 228, RoomType.PRACTICE | RoomType.COMPUTER, 45) 
    university.add_room(PECHOR, 302, RoomType.LECTURE, 45) 
    university.add_room(PECHOR, 314, RoomType.LECTURE, 45) 
    university.add_room(PECHOR, 216, RoomType.PRACTICE, 45) 
    university.add_room(PECHOR, 230, RoomType.PRACTICE, 45) 

    university.add_room(LVOV,  308, RoomType.PRACTICE,  45) 
    university.add_room(LVOV,  318, RoomType.LECTURE,  45) 
    university.add_room(LVOV,  201, RoomType.PRACTICE,  45) 
    university.add_room(LVOV,  301, RoomType.PRACTICE,  45) 
    

    university.add_group("16-pmi", 22, GroupType.BACHELOR)
    university.add_group("16-bi-1", 20, GroupType.BACHELOR)
    university.add_group("16-bi-2", 20, GroupType.BACHELOR)

    university.add_teacher('Колданов')
    university.add_teacher('Бабкина')
    university.add_teacher('Фролова')
    university.add_teacher('Слащинин')
    university.add_teacher('Зеленов')

    university.add_teacher('Ларюшина')
    university.add_teacher('Баевский')
    university.add_teacher('Визгунов')

    fill_16pmi(university)
    fill_16bi(university)

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


