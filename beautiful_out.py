import webbrowser
from university import University
from general_utils import *

def open_as_html(solution, university):
    f = open('output.html','w', encoding='utf-8')
    message = "<html><head></head><body>"

    for group, weeks in sorted(solution.items()):
        message += '<table border="1" width="100%">'
        message += "<caption>"+str(university.groups[group])+"</caption>"
        for week in range(university.study_weeks):
            message += "<tr>"
            for day in range(global_config.study_days):
                message += '<td valign="top" align="center"><table rules="all" width="100%">'
                for ts in range(global_config.time_slots_per_day_available):
                    message += '<tr><td>'
                    listt = weeks.get(week, {}).get(day, {}).get(ts, None)
                    message += str(ts+1) + " "
                    if not listt is None:
                        corpus, room, lesson, _type, teacher, other_groups = listt
                        message += "C {0} r{1} {2} {3} {4}".format(corpus, room, lesson.lesson_name, str(_type).split('.')[1], university.teachers[teacher])
                    message += "</tr></td>"
                message += "</table></td>"
            message += "</tr>"
        message += "</table><br><br>"



    message += "</html>"
    f.write(message)
    f.close()
    webbrowser.open_new_tab('output.html')