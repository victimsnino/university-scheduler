
from university import University
from general_utils import RoomType, debug, set_debug
from solver import Solver

''' 
Done:
* __fill_lessons_to_time_slots
    * Type of lesson and room type are equil
    * Size of room >= size of groups of current lesson
    * Only one lesson can be filled in 1 timeslot

* __fill_lessons_constraints
    * Constraint: count of lessons == count of lessons in time-slots
    
* Easy parser for output - parse_output_and_create_schedule
'''


if __name__ == "__main__":
    set_debug(False)

    university = University()

    university.add_room(1, 320, RoomType.LECTURE, 38) 
    university.add_room(1, 321, RoomType.COMPUTER | RoomType.LECTURE,  60) 
    #university.add_room(1, 322, RoomType.LECTURE, 60) 

    university.add_group("16-pmi", 30)
    university.add_group("17-pmi", 20)

    university.add_lesson("матан", '16-pmi', 1, RoomType.LECTURE)
    university.add_lesson("матан", '16-pmi', 2, RoomType.LECTURE) # summarize with above
    university.add_lesson("прога", '17-pmi', 1, RoomType.COMPUTER)
    university.add_lesson("прога", ['17-pmi', '16-pmi'], 1, RoomType.LECTURE)

    debug(university)

    solver = Solver(university)
    solver.solve()

