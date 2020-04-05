import webbrowser
from university import University
from general_utils import *

days = ['ПН', 'ВТ', 'СР', 'ЧТ', 'ПТ', 'СБ']
message = "<html><head></head><body>"

def add_text(text):
    global message
    message += text

class table:
    def __init__(self, name):
        add_text('<table border="1" width="100%">')
        add_text( "<caption>"+name+"</caption>")

    def __del__(self):
        add_text("</table><br><br>")

class tr:
    def __init__(self):
        add_text('<tr>')

    def __del__(self):
        add_text("</tr>")
           

class td:
    def __init__(self, center = True):
        if center:
            add_text('<td valign="top" align="center">')
        else:
            add_text('<td>')

    def __del__(self):
        add_text("</td>")

def print_days():
    t = tr()
    for day in range(global_config.study_days):
        t1 = td()
        add_text('<b>' + str(days[day]) + '</b>')
        del t1

def open_as_html(solution, university):
    global message
    f = open('output.html','w', encoding='utf-8')

    for group, weeks in sorted(solution.items()):
        tab = table(str(university.groups[group]))
        print_days()

        for week in range(university.study_weeks):
            tr1 = tr()
            for day in range(global_config.study_days):
                td1 = td()
                add_text('<table rules="all" width="100%">')
                for ts in range(global_config.time_slots_per_day_available):
                    tr2 = tr()
                    td2 = td(False)
                    listt = weeks.get(week, {}).get(day, {}).get(ts, None)
                    add_text(str(ts+1) + " ")
                    if not listt is None:
                        corpus, room, lesson, _type, teacher, other_groups = listt
                        add_text("C {0} r{1} {2} {3} {4}".format(corpus, room, lesson.lesson_name, str(_type).split('.')[1], university.teachers[teacher]))
                    del td2
                    del tr2
                add_text("</table>")
                del td1
            del tr1
        del tab
    



    add_text("</html>")
    f.write(message)
    f.close()
    webbrowser.open_new_tab('output.html')