import random
import math
import ai
from world import isValidSquare

AIClass="MarcoPolo"

require_dependency(module_name = "wedgeutil")
require_dependency(module_name = "mapsearch")

from wedgeutil import *

class MarcoPolo(ai.AI):
    PLAY_IN_LADDER = True
    
    def _init(self):
      # config
      self.wander_radius = 25      

      # status
      self.setup_complete = False  # set to True when we get our first unit, we need info on sight etc from units

      # our default units
      self.drones = []
            
      # map info
      self.map = mapsearch.MapSearch()
      self.bases = []

    # Behavior methods
    # wanders the map, changing direction every self.wander_radius
    def wander(self, unit):
      if not unit.is_moving:  
        unit.move(self.position_on_circle(self.wander_radius, unit.position))

    # returns a random position on the circumference of a given circle
    def position_on_circle(self, radius, center):
      x,y = -1,-1

      while not isValidSquare( (x,y), self.mapsize):
        angle = random.randint(0,360)
        x = center[0] + radius * math.sin(angle)
        y = center[1] + radius * math.cos(angle)
      return (x,y)        

    # attempts to capture any visible building
    def capture(self, unit):
      if unit.is_capturing:
        return True

      for building in unit.visible_buildings:
        if building.team == self.team:
          continue

        friend_capturing = False
        for friend in self.my_units:
          if friend != unit:
            if friend.is_capturing and friend.position == building.position:
              friend_capturing = True

        if friend_capturing:
          continue
  
        if unit.position == building.position:
          unit.capture(building)
        else:
          unit.move(building.position)
        return True

  
    # attempt to move to unexplored area of the map, if fully explored then wander
    def explore(self, unit):
      point = self.map.nearest(unit.position)
      if point == None:
        self.wander(unit)
      else:
        unit.move(point)

    # draws highlights for debugging
    def highlight(self):
      # draw map search coords
      self.clearHighlights()
      for p in self.map.points:
        self.highlightLine( p, (p[0] + 1, p[1] + 1) )
    
    def _unit_spawned(self, unit):
      self.drones.append(unit)
      
    def _unit_died(self, unit):
      if unit in self.drones:
        self.drones.remove(unit)
        return
          
    def _spin(self): 
      # run setup if needed
      if not self.setup_complete:
        if len(self.drones) > 0:
          self.map.setup( self.mapsize, self.drones[0].sight )
          self.setup_complete = True

      # print out highlights & debug info if needed
      self.highlight()
 
      # update our map
      self.map.update(self.my_units)      

      # Add new buildings we discover
      for building in self.visible_buildings:
        if not building in self.bases:
          self.bases.append(building)

        self.map.building(building)

      targets = []
      for building in self.bases:
        if building.team != self.team:
          targets.append(building)
         
      # Loop through our drones
      for unit in self.drones:
        # Attempt to capture any building in range
        if not self.capture(unit):
          if len(targets) > 0:
            t = closest_thing(unit.position, targets)

            if (len(self.map.points) == 0) or (calc_distance(unit.position, t.position) < unit.sight * 2):
              unit.move(t.position)
              continue 
          
          if len(targets) == 0 and len(self.map.points) == 0:
            if unit.visible_enemies:
              unit.shoot(unit.visible_enemies[0].position)
              continue

          self.explore(unit)
