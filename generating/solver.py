import cplex
import re
from general_utils import * 
from university import University, Lesson, Teacher
import copy
import progressbar
from functools import wraps
import warnings


def _for_corpuses(function):
	@wraps(function)
	def _decorator(self, **kwargs):
		for corpus_i in self.university.corpuses:
			function(self, corpus_i=corpus_i, **kwargs)
	return _decorator

def _for_week_and_day(function):
	@wraps(function)
	def _decorator(self, **kwargs):
		for week_i, day_i in self.university.study_weeks_and_days:
			function(self, week_i=week_i, day_i=day_i, **kwargs)
	return _decorator

def _for_week_only(function):
	@wraps(function)
	def _decorator(self, **kwargs):
		for week_i in range(self.university.study_weeks):
			function(self, week_i=week_i, **kwargs)
	return _decorator

def _for_day_only(function):
	@wraps(function)
	def _decorator(self, **kwargs):
		for day_i in self.university.study_days:
			function(self, day_i=day_i, **kwargs)
	return _decorator

def _for_timeslots(function):
	@wraps(function)
	def _decorator(self, **kwargs):
		for timeslot_i in range(global_config.time_slots_per_day_available):
			function(self, timeslot_i=timeslot_i, **kwargs)
	return _decorator

def _for_rooms(function):
	@wraps(function)
	def _decorator(self, **kwargs):
		for corpus_i in self.university.corpuses:
			for room in self.university.corpuses[corpus_i]:
				function(self, corpus_i=corpus_i, room_i=room.room_number, **kwargs)
	return _decorator

def _for_groups_or_teachers(function):
	@wraps(function)
	def _decorator(self, **kwargs):
		for container, format_out, column in self._get_groups_teachers_list():
			for ith, teacher_or_group in enumerate(container):
				function(self, container=container, format_out=format_out, column=column, ith=ith, teacher_or_group=teacher_or_group, **kwargs)
	return _decorator

def _for_lessons(function):
	@wraps(function)
	def _decorator(self, **kwargs):
		for lesson_i, lesson in enumerate(self.university.lessons):
			function(self, lesson_i=lesson_i, lesson=lesson, **kwargs)
	return _decorator

def get_timeslots(function):
	@wraps(function)
	def _decorator(self, source=None,**kwargs):
		week_i       = kwargs.get('week_i', r'.*')
		day_i        = kwargs.get('day_i', r'.*')
		corpus_i     = kwargs.get('corpus_i', r'.*')
		room_i       = kwargs.get('room_i', r'.*')
		timeslot_i   = kwargs.get('timeslot_i', r'.*')
		lesson_i     = kwargs.get('lesson_i', r'.*')
		type_i       = kwargs.get('type_i', r'.*')
		column       = kwargs.get('column', None)
		ith          = kwargs.get('ith', None)

		indexes = _get_time_slot_tracker_by_filter(self.model.variables, week_i=week_i, day_i=day_i, corpus_i=corpus_i, room_i=room_i, timeslot_i=timeslot_i, lesson_i=lesson_i, type_i=type_i, source=source)
		temp = self.model.variables.get_names(indexes)
		if column:
			indexes = eval('_get_time_slot_tracker_by_filter(self.model.variables, source=temp,  %s=ith)' % column))
			temp = self.model.variables.get_names(indexes)

		function(self, source=temp, **kwargs)
	return _decorator

def get_corpus_tracker(function):
	@wraps(function)
	def _decorator(self, corpus_tracker_source=None,**kwargs):
		week_i       = kwargs.get('week_i', r'.*')
		day_i        = kwargs.get('day_i', r'.*')
		corpus_i     = kwargs.get('corpus_i', r'.*')
		column       = kwargs.get('column', None)
		ith          = kwargs.get('ith', None)

		indexes = _get_corpus_tracker_by_filter(self.model.variables, week_i=week_i, day_i=day_i, corpus_i=corpus_i, source=corpus_tracker_source)
		temp = self.model.variables.get_names(indexes)
		if column:
			indexes = eval('_get_corpus_tracker_by_filter(self.model.variables, source=temp,  %s=ith)' % column))
			temp = self.model.variables.get_names(indexes)

		function(self, corpus_tracker_source=temp, **kwargs)
	return _decorator

def get_room_tracker(function):
	@wraps(function)
	def _decorator(self, room_tracker_source=None,**kwargs):
		room_i       = kwargs.get('room_i', r'.*')
		week_i       = kwargs.get('week_i', r'.*')
		day_i        = kwargs.get('day_i', r'.*')
		corpus_i     = kwargs.get('corpus_i', r'.*')
		column       = kwargs.get('column', None)
		ith          = kwargs.get('ith', None)

		indexes = _get_room_tracker_by_filter(self.model.variables, room_i=room_i, week_i=week_i, day_i=day_i, corpus_i=corpus_i, source=room_tracker_source)
		temp = self.model.variables.get_names(indexes)
		if column:
			indexes = eval('_get_room_tracker_by_filter(self.model.variables, source=temp,  %s=ith)' % column))
			temp = self.model.variables.get_names(indexes)

		function(self, room_tracker_source=temp, **kwargs)
	return _decorator

def get_lesson_tracker(function):
	@wraps(function)
	def _decorator(self, lesson_tracker_source=None,**kwargs):
		week_i       = kwargs.get('week_i', r'.*')
		day_i        = kwargs.get('day_i', r'.*')
		lesson_i     = kwargs.get('lesson_i', r'.*')
		column       = kwargs.get('column', None)
		ith          = kwargs.get('ith', None)

		indexes = get_lesson_tracker_by_filter(self.model.variables, week_i=week_i, day_i=day_i, lesson_i=lesson_i, source=lesson_tracker_source)
		temp = self.model.variables.get_names(indexes)
		if column:
			indexes = eval('get_lesson_tracker_by_filter(self.model.variables, source=temp,  %s=ith)' % column))
			temp = self.model.variables.get_names(indexes)

		function(self, lesson_tracker_source=temp, **kwargs)
	return _decorator

