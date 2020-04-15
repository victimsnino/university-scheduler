
from university import University, Lesson
from general_utils import RoomType, debug, set_debug, Config, global_config, GroupType
from solver import Solver
import sys
import cProfile
from beautiful_out import open_as_html

''' 
Done:
* Added weeks and days

* __fill_lessons_to_time_slots
    * Type of lesson and room type are equil
    * Size of room >= size of groups of current lesson
    * Only one lesson can be filled in 1 timeslot + only 1 teacher can conducts a lesson

* __constraint_total_count_of_lessons
    * Constraint: count of lessons == count of lessons in time-slots

* __constraint_group_or_teacher_only_in_one_room_per_timeslot
    * Constraint: each group or teacher can be only in one room per time-slot

* __constraint_ban_changing_corpus_for_groups_or_teachers_during_day
    * Constraint: each group or teacher can has only 1 corpus per day

* __constraint_max_lessons_per_day_for_teachers_or_groups
    * Max lessons per day limited by config

* __constraint_max_lessons_per_week_for_teachers_or_groups
    * Max lessons per week limited by config

* __local_constraint_lesson_after_another_lesson
    * Availability for ordering lessons depend from each other (practice after lecture)

* __local_constraint_teacher_or_group_has_banned_ts
    * Some teacher or groups can have banned timeslots -> no lessons in the such day

* __constraint_ban_windows
    * Any teacher or group can't have window during a day
    * Now it is available to set it as a soft constraint
    
* __constraint_one_teacher_per_lessons
    * Only one teacher conducts one lesson during all module

* __soft_constraint_max_lessons_per_day
    * Desired maximal count of lessons per day (for avoiding looooong days)

*__soft_constraint_min_lessons_per_day
    * Desired minamal count of lessons per day (for avoiding 1 lessons per day)

* __soft_constraint_lessons_balanced_during_module
    * It is very cool, when lessons placed in the same day and ts each week

* __soft_constraint_count_of_lessons_more_than_count_of_rooms
    * Count of lessons >= count of rooms. It means, that it is require to have only 1 room for lesson during day
    
* __soft_constraint_last_day_in_week
    * Nobody wants to learn last day a week

*__soft_constraint_reduce_ratio_of_lessons_and_subjects
    * Grouping lessons by lessonid by days during week.

* __soft_constraint_ban_windows_between_one_subject_during_day
    * Grouping lessons by lessonid during day
    
* __soft_constraint_lessons_balanced_during_module_by_timeslots
    * Grouping by timeslots in selected day every week
    
* __soft_constraint_lessons_balanced_during_module_by_rooms
    * Grouping by rooms in selected day every week 

* Added friend lessons: it is so close lessons. For example "DummyLesson.Practice" and "DummyLesson.Lecture". These lessons so close.
* Split groups to bachelors and magistrecy for splitting by timeslots
* It is possible to set day of week for start or end of module and count of weeks
* Easy parser for output - parse_output_and_create_schedule
'''

def main():
    set_debug('--debug' in sys.argv)

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
    practice1 = university.add_lesson('Алгоритмы и структуры данных', ['17bi-1'], weeks, RoomType.PRACTICE, ['Демкин']).should_be_after_lessons(lect)
    practice2 = university.add_lesson('Алгоритмы и структуры данных', ['17bi-2'], weeks, RoomType.PRACTICE, ['Демкин']).should_be_after_lessons(lect)

    university.add_friends_lessons([lect, practice1])
    university.add_friends_lessons([lect, practice2])

    lect = university.add_lesson('Объектно -ориентированное программирование', ['17bi-1', '17bi-2'], weeks/2, RoomType.LECTURE, ['Демкин'])
    practice1 = university.add_lesson('Объектно -ориентированное программирование', ['17bi-1'], weeks/2, RoomType.PRACTICE, ['Демкин']).should_be_after_lessons(lect)
    practice2 = university.add_lesson('Объектно -ориентированное программирование', ['17bi-2'], weeks/2, RoomType.PRACTICE, ['Демкин']).should_be_after_lessons(lect)

    university.add_friends_lessons([lect, practice1])
    university.add_friends_lessons([lect, practice2])

    lect = university.add_lesson('Теория вероятностей', ['17bi-1', '17bi-2'], weeks, RoomType.LECTURE, ['Колданов']).should_be_after_lessons(lect)
    practice1 = university.add_lesson('Теория вероятностей', ['17bi-1'], weeks, RoomType.PRACTICE, ['Семенов']).should_be_after_lessons(lect)
    practice2 = university.add_lesson('Теория вероятностей', ['17bi-2'], weeks, RoomType.PRACTICE, ['Семенов']).should_be_after_lessons(lect)

    university.add_friends_lessons([lect, practice1])
    university.add_friends_lessons([lect, practice2])

    lect = university.add_lesson('Моделирование процессов и систем', ['17bi-1', '17bi-2'], weeks, RoomType.LECTURE, ['Асеева'])
    practice1 = university.add_lesson('Моделирование процессов и систем', ['17bi-1'], weeks, RoomType.PRACTICE, ['Куранова']).should_be_after_lessons(lect)
    practice2 = university.add_lesson('Моделирование процессов и систем', ['17bi-2'], weeks, RoomType.PRACTICE, ['Куранова']).should_be_after_lessons(lect)

    university.add_friends_lessons([lect, practice1])
    university.add_friends_lessons([lect, practice2])

    lect = university.add_lesson('Анализ данных', ['17bi-1', '17bi-2'], weeks, RoomType.LECTURE, ['Калягин'])
    practice1 = university.add_lesson('Анализ данных', ['17bi-1'], weeks, RoomType.PRACTICE, ['Казаков']).should_be_after_lessons(lect)
    university.add_friends_lessons([lect, practice1])

    university.add_lesson('Английский язык', ['17bi-1', '17bi-2'],  2*weeks, RoomType.PRACTICE, ['Фролова'])
    university.add_lesson('Английский язык1', ['17bi-1', '17bi-2'], 2*weeks, RoomType.PRACTICE, ['Фролова'])

    solver = Solver(university)
    res, output = solver.solve()

    # open_as_html(output, university)


if __name__ == "__main__":
    main()