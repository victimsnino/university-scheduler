
from university import University, Lesson
from general_utils import RoomType, debug, set_debug, Config, global_config
from solver import Solver
import sys


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

* __local_constraint_lesson_after_another_lesson
    * Some lessons have dependencies from each others. Added logic, that total sum of costs lectures 'after' should be >= total cost of lectures 'before'
    * It is doesn't require, that one lesson places strongly after another.... Only 'summary'

    
* Easy parser for output - parse_output_and_create_schedule
'''


if __name__ == "__main__":
    set_debug('--debug' in sys.argv)

    university = University()

    university.add_room(1, 120, RoomType.LECTURE,   100) 
    university.add_room(1, 121, RoomType.PRACTICE,  30) 

    university.add_room(2, 203, RoomType.COMPUTER,  30) 
    university.add_room(2, 205, RoomType.LECTURE,   50) 
    university.add_room(2, 206, RoomType.COMPUTER,  30) 

    university.add_room(3, 305, RoomType.LECTURE,   60) 

    university.add_group("16-pmi", 30)
    university.add_group("17-pmi", 20)
    university.add_group('16-pi', 25)
    university.add_group('15-pi', 60)
    university.add_group('14-pi', 20)

    university.add_teacher('Бычков И С')
    university.add_teacher('Чистяков В В')
    university.add_teacher('Фейковый Матанщик')
    university.add_teacher('Фейковый Прогер')

    university.add_lesson("матан", ['16-pmi', '17-pmi'], 2, RoomType.LECTURE, ['Чистяков В В', 'Фейковый Матанщик'])
    university.add_lesson("матан", ['16-pmi'], 4, RoomType.PRACTICE, ['Чистяков В В', 'Фейковый Матанщик'])
    university.add_lesson("матан", ['17-pmi'], 3, RoomType.PRACTICE, ['Чистяков В В', 'Фейковый Матанщик'])

    pr_lection = university.add_lesson("прога", ['16-pi'], 10, RoomType.LECTURE,  ['Бычков И С'])
    pr_practice = university.add_lesson("прога", ['16-pi'], 10, RoomType.COMPUTER, ['Бычков И С'])

    pr_practice.should_be_after_lessons(pr_lection)

    university.add_lesson("прога", ['14-pi'], 1, RoomType.COMPUTER, ['Бычков И С', 'Фейковый Прогер'])
    university.add_lesson("прога", ['15-pi'], 5, RoomType.LECTURE, ['Бычков И С', 'Фейковый Прогер'])

    debug(university)

    solver = Solver(university)
    solver.solve()
