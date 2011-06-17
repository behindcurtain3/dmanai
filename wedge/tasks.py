import ai
import random

require_dependency(module_name = "wedgeutil")
require_dependency(module_name = "mapsearch")

from wedgeutil import *

# A task can be something like "defend x" or "attack x"
# Tasks are all given to a position on the map
# For instance, when we take over a new base we'd create a task DefendTask
# the task will automatically request & release units as needed
class Task(object):
  def __init__(self, ai, position):
    self.ai = ai                # holds our AI so we can query it
    self.name = "Task"          # AI can query to find type of task it is
    self.position = position    # all tasks have a position associated with them where the task is to be accomplished
    self.priority = 0           # the task priority, higher priority tasks have their unit needs filled first
    self.units_needed = 0       # how many units does the task need? (This is "requested" number)
    self.units_minimum = 0      # this is the minimum number needed, (For instance, ExploreTask sets this to 1 so we always have 1 unit exploring)
                                # units_minimum are filled before units_needed
    self.units_assigned = []    # track the assigned units
    self.is_default = False        # if true, this is the "default task" which is assigned all extra units

  def is_full(self):
    return len(self.units_assigned) >= self.units_needed

  # default to set the task to never finish
  def is_finished(self):
    return False

  # update task logic, do not carry out any actions
  def update(self):
    pass
  
  # carry out actions here
  def do_actions(self):
    pass

  def add_unit(self, unit):
    if not unit in self.units_assigned:
      self.units_assigned.append(unit)

  def dead_unit(self, unit):
    if unit in self.units_assigned:
      self.units_assigned.remove(unit)

  # attack any in range units
  def attack(self, unit):
    enemies = unit.in_range_enemies
    if len(enemies) > 0:
      enemy = self.select_target(unit, enemies)
      shoot_at = self.ai.enemy_predictor[enemy].predict(unit.position, settings.bullet.speed)
      victims = unit.calcVictims(shoot_at)			

      for v in victims:
        if v in self.ai.my_units:
          return False

      unit.shoot( shoot_at )
      return True

  def select_target(self, unit, units):
    for enemy in units:
      # don't attack the same enemy more than twice in the same turn, unless we have no other targets
      if self.ai.enemies_attacked[enemy] < 2:
        self.ai.enemies_attacked[enemy] = self.ai.enemies_attacked[enemy] + 1
        return enemy
      
    return units[0]   

  # can/should the specified unit capture the specified building?
  def capture_target(self, unit, building):
    if unit.is_capturing:
      return True

    for friend in self.units_assigned:
      if friend != unit:
        if friend.is_capturing and friend.position == building.position:
          return False

    if unit.position == building.position:
      unit.capture(building)
    else:
      unit.move(building.position)

    return True

class BuildingTask(Task):
  def __init__(self, ai, building):
    Task.__init__(self, ai, building.position)
    self.building = building

  def is_enemy(self, x): return x.team != self.ai.team

  def capture(self, unit):
    if unit.is_capturing:
        return True

    for friend in self.ai.my_units:
      if friend != unit:
        if friend.is_capturing and friend.position == self.building.position:
          return False

    if unit.position == self.building.position:
      unit.capture(self.building)
    else:
      unit.move(self.building.position)

    return True  

class DefendTask(BuildingTask):
  def __init__(self, ai, building):
    BuildingTask.__init__(self, ai, building)
    self.name = "Defend"
    self.priority = 8

    # defend specific variables
    self.deaths = 0
    self.last_death = 0
    self.enemies = []

    self.calcUnitsNeeded()

  def is_finished(self):
    return self.building.team != self.ai.team

  def dead_unit(self, unit):
    if unit in self.units_assigned:
      self.units_assigned.remove(unit)
      self.deaths += 1
      self.last_death = 0
      self.calcUnitsNeeded()

  def update(self):
    if len(self.units_assigned) == 0:
      return

    self.enemies = []

    # make list of nearby enemies
    for unit in self.units_assigned:
      d = calc_distance(unit.position, self.position)

      if d > unit.sight:
        continue

      for enemy in unit.in_range_enemies:
        if not enemy in self.enemies:
          self.enemies.append(enemy)

  
    self.priority = 8
    if len(self.enemies) >= len(self.units_assigned):
      self.priority = 1
    elif len(self.units_assigned) == 0:
      self.priority = 2

    if self.deaths > 0:
      self.last_death += 1
      if self.last_death % 100 == 0:
        self.deaths -= 1

    self.calcUnitsNeeded()

    while len(self.units_assigned) > self.units_needed:
      u = self.units_assigned[-1]
      self.ai.drones.append(u)
      self.units_assigned.remove(u)

  def do_action(self):
    for unit in self.units_assigned:
      if not self.attack(unit):
        if len(unit.visible_buildings) > 0:
            enemy_buildings = filter(self.is_enemy, unit.visible_buildings)
            b = closest_thing(unit.position, enemy_buildings)
            if b != None:
              if self.capture_target(unit, b):
                continue

        if len(self.enemies) > 0:
          closest = closest_thing(unit.position, self.enemies)
          unit.move(closest.position)
          continue

        d = calc_distance(unit.position, self.position)

        if not unit.is_moving or d > unit.sight * 0.5:
          p = (-1,-1)

          while not isValidSquare(p, self.ai.mapsize):
            p = position_on_circle(unit.sight * 0.5, self.position)
          
          unit.move(p)

  def calcUnitsNeeded(self):
    size = self.ai.mapsize
    radius = size / 2
    
    # for defending, the closer we are to the middle of the map, the more units we need
    # we also need to take into account what turn it is, at the beginning we don't need a huge defence

    # distance from middle
    distance = calc_distance(self.position, (radius, radius))

    if distance > radius:
      self.units_needed = 2
    elif distance > radius * .75:
      self.units_needed = 3
    elif distance > radius * .5:
      self.units_needed = 4
    elif distance > radius * .25:
      self.units_needed = 5
    else:
      self.units_needed = 6

    self.units_needed += self.deaths

    if self.ai.current_turn < settings.building.spawn_time * 3:
      self.units_needed = 1
    elif self.ai.current_turn < settings.building.spawn_time * 6:
      self.units_needed = min(self.units_needed, 2)
    else:
      self.units_needed = min(self.units_needed, 8) # 8 is the max units set to defend

class CaptureTask(BuildingTask):
  def __init__(self, ai, building):
    BuildingTask.__init__(self, ai, building)
    self.name = "Capture"
    self.priority = 10
    self.units_needed = 1

    self.attack_launched = False
    self.rally = (0,0)
    self.last_death = 0
    
  def is_finished(self):
    return self.building.team == self.ai.team

  def dead_unit(self, unit):
    if unit in self.units_assigned:
      self.units_assigned.remove(unit)
      self.units_needed += 1
      self.units_needed = min(self.units_needed, 8)
      self.last_death = self.ai.current_turn

  def update(self):
    if len(self.units_assigned) == 0:
      return

    if self.ai.current_turn >= self.last_death + 50 and self.last_death != 0 and self.units_needed > 1:
      self.units_needed -= 1

    self.priority = min(self.units_needed + 10, 20)

    # set rally point
    b = closest_thing(self.building.position, self.ai.my_buildings)

    if b == None:
      self.rally = self.building.position
    else:
      self.rally = b.position

    if len(self.units_assigned) >= self.units_needed:
      self.attack_launched = True

    if self.attack_launched:
      # if we've lost over 2/3 of ours units retreat
      if self.units_needed > 2 and (len(self.units_assigned) / self.units_needed) < 0.33:
        self.attack_launched = False

  def do_action(self):
    for unit in self.units_assigned:
      # always attack enemy units
      if not self.attack(unit):
        # has the attack launched?
        if self.attack_launched:
          if len(unit.visible_buildings) > 0:
            enemy_buildings = filter(self.is_enemy, unit.visible_buildings)
            b = closest_thing(unit.position, enemy_buildings)
            if b != None:
              if self.capture_target(unit, b):
                continue
          self.capture(unit) 
        else:
          if not unit.is_moving:
            p = (-1,-1)

            while not isValidSquare(p, self.ai.mapsize):
              p = position_on_circle(unit.sight * .75, self.rally)
            
            unit.move(p)

          

# Explore task will act a default task, any extra units are assigned to it until it is finished
class ExploreTask(Task):
  def __init__(self, ai, position):
    Task.__init__(self, ai, position)
    self.name = "Explore"
    self.priority = 100
    self.units_needed = 200
    self.units_minimum = 1
    self.is_default = True

  def is_finished(self):
    return len(self.ai.map.points) == 0

  def update(self):
    # add any new buildings
    for building in self.ai.visible_buildings:
      self.ai.map.building(building)

    # map should update based off of all units, not just those assigned
    self.ai.map.update(self.ai.my_units)

  def do_action(self):
    for unit in self.units_assigned:
      if not self.attack(unit):
        point = self.ai.map.nearest(unit.position)
        if point != None:
          unit.move( point )

class WanderAndKillTask(Task):
  def __init__(self, ai, position):
    Task.__init__(self, ai, position)
    self.name = "WanderAndKill"
    self.priority = 100
    self.units_needed = 200
    self.is_default = True

  def update(self):
    pass

  def do_action(self):
    for unit in self.units_assigned:
      if not self.attack(unit):
        if not unit.is_moving:
          p = (-1,-1)

          while not isValidSquare(p, self.ai.mapsize):
            p = position_on_circle(unit.sight * 2, unit.position)
          
          unit.move(p)

class AlwaysExploreTask(ExploreTask):
  def __init__(self, ai, position):
    ExploreTask.__init__(self,ai,position)
    self.name = "AlwaysExplore"
    self.priority = 9
    self.units_needed = 1
    self.is_default = False

  def is_finished(self):
    if len(self.ai.map.points) == 0:
      return True

    # if we get past 250 turns and only have 1 building we are losing, stop wasting a unit on this
    if self.ai.current_turn >= 250 and len(self.ai.my_buildings) <= 1:
      return True

    return False

  def do_action(self):
    self.ai.clearHighlights()
    for unit in self.units_assigned:
      if len(unit.visible_enemies) == 0 and len(unit.visible_buildings) > 0:      
        for b in unit.visible_buildings:
          if b.team != self.ai.team:
            if self.capture_target(unit, b):
              return

      point = self.ai.map.nearest(unit.position)
      if point != None:
        unit.move( point )
  
