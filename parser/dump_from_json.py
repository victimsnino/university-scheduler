from university import *
from solver import Solver
from beautiful_out import open_as_html
import pytest

def test_main():
    university = University(weeks=2)
#[[[cog
import cog
import json


FILENAME = 'Timetable_ALL_final.json'

with open(FILENAME, "r", encoding="utf-8") as read_file:
    data = json.load(read_file)

bacalavr = data['Бакалавриат']

stats_by_group = {}
uniq_teachers = {}
rooms = {}

pmi = bacalavr['Прикладная математика и информатика']
for _, course in sorted(pmi.items()):
    for name, group in course.items():
        stats = stats_by_group.setdefault(name, {})
        for day, lessons_in_day in list(group.items())[:6]:
            for timeslot, slot in lessons_in_day.items():
                if slot['Тип'] == '-':
                    continue
                for i, _ in enumerate(slot['Дисциплина']):
                    if slot['Дисциплина'][i].lower() in ['-', 'майнор', 'английский язык']:
                        continue
                    corpus = rooms.setdefault(slot['Кампус'], set())

                    room = slot['Аудитория'][i] if len(slot['Аудитория']) > i else slot['Аудитория'][0]
                    corpus.add(int(room))

                    teacher_name = slot['Преподаватель'][i].split(' ', 1)[0]
                    uniq_teachers[teacher_name] = uniq_teachers.get(teacher_name, 0) + 1
                    key = slot['Дисциплина'][i]+":"+teacher_name+":"+slot['Тип']
                    stats[key] = stats.get(key, 0) + (1 if len(slot['Дисциплина']) == 1 else 0.5)

cog.outl('#')
for i, rooms_in_corpus in enumerate(rooms.values()):
    for room in rooms_in_corpus:
        cog.outl(f"    university.add_room({i+1}, {room}, RoomType.LECTURE | RoomType.PRACTICE | RoomType.COMPUTER, 100)")

cog.outl()

for group_name in stats_by_group.keys():
    cog.outl(f"    university.add_group('{group_name}', 1, GroupType.BACHELOR)")

cog.outl()

for teacher, lessons in uniq_teachers.items():
    if lessons <= 0:
        continue
    cog.outl(f"    university.add_teacher('{teacher}')")


cog.outl('    ')

for group_name, lessons in stats_by_group.items():
    temp_lessons = {}
    for packed_lesson, count in lessons.items():
        lesson_name, teacher, type = packed_lesson.split(':')
        prev_type = temp_lessons.get(lesson_name, None)
        if prev_type:
            if prev_type == type:
                if prev_type == 'Семинар':
                    type = 'Лекция'
                elif prev_type == 'Лекция':
                    type = 'Семинар'

        temp_lessons[lesson_name] = type

        if type == 'Семинар':
            my_type = 'RoomType.PRACTICE'
        elif type == 'Лекция':
            my_type = 'RoomType.LECTURE'
        else:
            raise Exception('')
        
        temp_count = int(count) if count >= 1 else count
        cog.outl(f"    university.add_lesson('{lesson_name}', ['{group_name}'], {temp_count}*university.study_weeks, {my_type}, ['{teacher}'])")
    cog.outl()
-# ]]]
-#[[[end]]]

    solver = Solver(university)
    res, output , by_teachers = solver.solve()
    assert res

    open_as_html(output, university, by_teachers)