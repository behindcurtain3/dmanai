import ai
import random
import math
from collections import defaultdict

AIClass = "WorkSmarter"

require_dependency(module_name = "wedgeutil")
require_dependency(module_name = "bullseye")
require_dependency(module_name = "mapsearch")
require_dependency(module_name = "tasks")

from wedgeutil import *

class WorkSmarter(ai.AI):
  PLAY_IN_LADDER = True

  def _init(self):
    self.drones = []
    self.task_list = []
    self.buildings = defaultdict(bool)
  
    # add a default task, all drones not assigned another task will do this
    self.task_list.append( tasks.ExploreTask(self, (0,0) ) )

    # enemies
    self.enemies_attacked = {}
    self.enemy_predictor = defaultdict(bullseye.Predictor)

    # map
    self.map = mapsearch.MapSearch()
    self.map.setup(self.mapsize, settings.unit.sight)

  def _unit_spawned(self, unit):
    self.receive_unit(unit)    

  def _unit_died(self, unit):
    if unit in self.drones:
      self.drones.remove(unit)

    for task in self.task_list:
      task.dead_unit(unit)

  def receive_unit(self, unit):
    if not unit in self.drones:
      self.drones.append(unit)

  def get_defend_tasks(self, no_full_tasks = True):
    tasks = []

    for task in self.task_list:
      if task.name == "Defend":
        if no_full_tasks:
          if not task.is_full():
            tasks.append( task )
            continue
        tasks.append(task)

    return tasks

  def _spin(self):
    # update enemies
    for enemy in self.visible_enemies:
      self.enemies_attacked[enemy] = 0

      # update our position tracking
      if not enemy in self.enemy_predictor:
				self.enemy_predictor[enemy] = bullseye.Predictor(enemy, self.mapsize)
      else:
        self.enemy_predictor[enemy].set_position(enemy.position)

    # look for new buildings
    for b in self.visible_buildings:
      if not b in self.buildings:
        if b.team == self.team:
          self.task_list.append( tasks.DefendTask(self, b) )
        else:
          self.task_list.append( tasks.CaptureTask(self, b) )
      
      self.buildings[b] = (b.team == self.team)

    # remove completed tasks
    for task in self.task_list[:]:
      if task.is_finished():
        if task.name == "Capture":
          t = tasks.DefendTask(self, task.building)
          t.units_assigned = task.units_assigned
          task.units_assigned = []
          self.task_list.append( t )
        elif task.name == "Defend":
          t = tasks.CaptureTask(self, task.building)
          t.units_assigned = task.units_assigned
          task.units_assigned = []
          self.task_list.append( t )
        elif task.name == "Explore":
          self.task_list.append( tasks.WanderAndKillTask(self, (0,0) ) )

        # reclaim the units
        if not task.is_default:
          self.drones.extend( task.units_assigned )
  
        self.task_list.remove(task)
        
    # sort tasks based on priority
    self.task_list = sorted(self.task_list, key = lambda t: t.priority)
    
    # assign units
    for task in self.task_list:      
      if task.is_default: # default task should always be lowest priority and hence called last
        task.units_assigned = self.drones
      else:
        while not task.is_full() and len(self.drones) > 0:
          # get closest drone
          drone = closest_thing( task.position, self.drones )
          task.add_unit(drone)
          self.drones.remove(drone)
    
    # update tasks
    for task in self.task_list:
      task.update()

    # do actions for each task
    for task in self.task_list:
      task.do_action()
