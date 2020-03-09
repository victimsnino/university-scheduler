import cplex
import re
from general_utils import * 
from university import University, Lesson, Teacher
import copy
import progressbar
from functools import wraps
import warnings


#[[[cog
import cog
import xml.etree.ElementTree as ET
data = ET.parse('./xmls/decorators.xml')
data = data.getroot()
for decorator in data.getchildren():
    cog.outl('def {}(function):'.format(decorator.get('name')))
    cog.outl('\t@wraps(function)')
    cog.outl('\tdef _decorator(self, {0}**kwargs):'.format("{0}=None,".format(decorator.get('source', 0)) if decorator.get('source', 0) else ""))
    tabs = "\t\t"
    all_vars = []
    all_use_as = []
    for for_code in decorator.findall('./for'):
        vars = [var.get('name') for var in for_code.getchildren()]
        use_as = [var.get('use_as') if var.get('use_as', None) else var.get('name') for var in for_code.getchildren()]
        columns = [var.get('column') if var.get('column', None) else var.get('name') for var in for_code.getchildren()]
        all_vars.extend(columns)
        all_use_as.extend(use_as)

        cog.out(tabs)
        cog.outl('for {0} in {1}:'.format(", ".join(vars), for_code.get('source')))
        tabs+='\t'

    if decorator.get('source'):
        for code in decorator.findall('./temp_variable'):
            cog.out(tabs)
            cog.outl("{0:<13}= kwargs.get('{0}', {1})".format(code.get('name'), code.get('default')))
    
        cog.out('\n'+tabs)
        cog.out('indexes = {0}(self.model.variables, '.format(decorator.get('function')))
        var_names = []
        for code in decorator.findall('./temp_variable'):
            if code.get('default', None) != 'None':
                var_names.append(code.get('name'))

        cog.out(', '.join(var+'='+var for var in var_names))
        cog.outl(", source={0})".format(decorator.get('source')))

        cog.out(tabs)
        cog.outl('temp = self.model.variables.get_names(indexes)')

        cog.out(tabs)
        cog.outl("if column:")

        cog.out('\t'+tabs)
        cog.outl("indexes = eval('{0}(self.model.variables, source=temp,  %s=ith)' % column))".format(decorator.get('function')))
        cog.out('\t'+tabs)
        cog.outl('temp = self.model.variables.get_names(indexes)\n')

        all_vars.append(decorator.get('source'))
        all_use_as.append('temp')

    cog.out(tabs)
    cog.outl('function(self, {0}, **kwargs)'.format(", ".join("{0}={1}".format(var, all_use_as[i]) for i, var in enumerate(all_vars))))
    cog.outl('\treturn _decorator\n')

# ]]]
#[[[end]]]