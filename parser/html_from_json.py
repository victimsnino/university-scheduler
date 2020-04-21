import json
import webbrowser

FILENAME = 'Timetable_ALL_final.json'
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
            add_text('<td align="center">')
        else:
            add_text('<td>')

    def __del__(self):
        add_text("</td>")
def print_timeslots():
    t = tr()
    for ts in ["", "8.00-9.20", "9.30-10.50", "11.10-12.30",  "12.40-14.00", "14.20-15.40",  "15.50-17.10"]:
        t1 = td()
        add_text('<b>' + ts + '</b>')
        del t1

def print_schedule_for_group(data, name):
    tab = table(name)
    print_timeslots()

    for day, someone in list(data.items())[:6]:
        tr1, td1 = tr(), td()
        add_text(day)
        del td1
        for i, lessons in enumerate(someone.values()):
            td2 = td()
            add_text('<table rules="all" width="100%">')
            for i, lesson in enumerate(lessons['Дисциплина']):
                tr3, td3 = tr(), td()
                add_text(lesson)
                add_text(f"<br>Учитель: {lessons['Преподаватель'][i]}")
                add_text(f"<br>Тип: {lessons['Тип']}")
                del td3
                del tr3
            add_text("</table>")
            del td2
        del tr1

    del tab

def main():
    with open(FILENAME, "r", encoding="utf-8") as read_file:
        data = json.load(read_file)

    bacalavr = data['Бакалавриат']

    pmi = bacalavr['Прикладная математика и информатика']
    for _, course in sorted(pmi.items()):
        for name, group in course.items():
            print_schedule_for_group(group, name)


    f = open('temp_output.html','w', encoding='utf-8')
    add_text("</html>")
    f.write(message)
    f.close()
    webbrowser.open_new_tab('temp_output.html')

if __name__ == "__main__":
    main()