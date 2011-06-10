import random
import ai
import math
import itertools
from collections import defaultdict
from world import isValidSquare

AIClass="Wedge"

import sys
import os
require_dependency(module_name = "wedgeutil")
require_dependency(module_name = "buildinginfo")
require_dependency(module_name = "mapsearch")
require_dependency(module_name = "bullseye" )

from wedgeutil import closest_thing

class Wedge(ai.AI):
    PLAY_IN_LADDER = True
    
    def _init(self):
      # config
      self.perimeter_distance = 3
      self.wander_radius = 25      
      self.search_until = 100     # number of turns to search without fighting and without assisting other drones      

      # status
      self.setup_complete = False  # set to True when we get our first unit, we need info on sight etc from units

      # our default units
      self.drones = []
            
      # map info
      self.map = mapsearch.MapSearch()
      
      # buildings
      self.buildings = defaultdict(buildinginfo.BuildingInfo)

      # enemies
      self.enemies_attacked = {}
      self.enemy_predictor = defaultdict(bullseye.Predictor)

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

    # can/should the specified unit capture the specified building?
    def capture_target(self, unit, building):
      if unit.is_capturing:
        return True

      for friend in self.my_units:
        if friend != unit:
          if friend.is_capturing and friend.position == building.position:
            return False

      if unit.position == building.position:
        unit.capture(building)
      else:
        unit.move(building.position)

      return True

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

    # attack any in range units
    def attack(self, unit):
      enemies = unit.in_range_enemies
      if len(enemies) > 0:
				enemy = self.select_target(unit, enemies)
				
				unit.shoot( self.enemy_predictor[enemy].predict(unit.position, enemy.position) )
				return True

    def select_target(self, unit, units):
      for enemy in units:
        # don't attack the same enemy more than twice in the same turn, unless we have no other targets
        if self.enemies_attacked[enemy] < 2:
          self.enemies_attacked[enemy] =  self.enemies_attacked[enemy] + 1
          return enemy
        
      return units[0]
  
    # attempt to move to unexplored area of the map, if fully explored then wander
    def explore(self, unit):
      point = self.map.nearest(unit.position)
      if point == None:
        self.wander(unit)
      else:
        unit.move(point)

    # defends a particular building
    def defend(self, unit, buildinginfo):
      if not self.capture(unit):
        if not self.attack(unit):
          if not unit.is_moving:
            try:
              unit.move( buildinginfo.perimeter_cycler.next() )
            except StopIteration:
              self.wander(unit)

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
        
      for key, value in self.buildings.iteritems():
        if unit == value.defender:
          value.defener = None
          
    def _spin(self): 
      # run setup if needed
      if not self.setup_complete:
        if len(self.drones) > 0:
          self.map.setup( self.mapsize, self.drones[0].sight )
          self.setup_complete = True

      # print out highlights & debug info if needed
      self.highlight()
 
      # create lists 
      enemies = list(self.visible_enemies)
      targets = []  # list of buildings we don't own that we know about
      bases = []    # list of buildings we own

      # update enemies
      self.enemies_attacked = {}
      
      for enemy in enemies:
        self.enemies_attacked[enemy] = 0
        
        if not enemy in self.enemy_predictor:
					self.enemy_predictor[enemy] = bullseye.Predictor(enemy, self.mapsize)
                     
      # update our map
      self.map.update(self.my_units)      

      # Check for perimeter distance increase
      if self.current_turn % 250 == 0:
        self.perimeter_distance += 1  
        
      # Add new buildings we discover
      for building in self.visible_buildings:
        if not building in self.buildings:
          self.buildings[building] = buildinginfo.BuildingInfo(self, building)
          self.buildings[building].establish_perimeter(self.perimeter_distance)
          self.map.building(building)
         
      # Loop through all known buildings: 
      # value = BuildingInfo instance for the key = building
      for key, value in self.buildings.iteritems():
        if len(value.perimeter) == 0:
          value.establish_perimeter(self.perimeter_distance)
        
        # update perimeter if the distance has changed
        elif self.perimeter_distance != value.perimeter_distance:
          value.establish_perimeter(self.perimeter_distance)

        # our buildings require specific actions
        if key.team == self.team:
        
          # if the building has no defender, request one (preferably closest available unit)
          if value.defender == None:
            drone_assigned = closest_thing( value.building.position, self.drones )
                       
            # assign drone to defend & remove from drone pool
            if drone_assigned != None:
              value.defender = drone_assigned
              self.drones.remove(drone_assigned)
          # if we have a defender on this building, make sure its alive
          else:
            if value.defender.is_alive:
              self.defend(value.defender, value)
            else:
              value.defender = None
              continue
        
        # else building not on our team
        else:
          targets.append(key)
          
          # if there is still a defender, have them attempt a recapture!
          if value.defender != None:
            if value.defender.is_alive:
              self.defend(value.defender, value)
            else:
               value.defender = None
    
      # Loop through our drones
      for unit in self.drones:
        # Attempt to attack any enemies in range
        if not self.attack(unit):
          # Attempt to capture any building in range
          if not self.capture(unit):
            # Either: Explore map or assist other drones
            if self.current_turn <= self.search_until:
              self.explore(unit)
            else:
              # this area needs a lot of work, target selection is the weakest link right now
              goto = closest_thing( unit.position, list(targets + enemies) )
              
              if goto == None:
                self.explore(unit)
              else:
                if goto in targets:
                  self.capture_target(unit, goto)
                else:
                  unit.move( self.position_on_circle( unit.sight - 1, goto.position ) )
