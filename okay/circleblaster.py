
# x = cx + r * cos(a)
# y = cy + r * sin(a)
import math
import ai
AIClass="CircleBlaster"
import random
from collections import defaultdict
from world import isValidSquare
import sys
import os
sys.path.append(os.path.dirname(__file__))
import okay

THIRTY_DEGREES=(180 / math.pi) * 30

class CircleBlaster(okay.OkayAI):
    def _init(self):
      self.cluster_size = 5
      self.expansion_phase = 0
      self.squads = []
      self.radian_offset = 0
      self.explorer = okay.CircleSquad(mapsize=self.mapsize)
      self.guarding = defaultdict(set)

    def _spin(self):
      available_units = filter(lambda x: not x.is_capturing, self.my_units)
      main_circle_size = len(available_units) - len(self.explorer)

      radius_m = 1
      if self.expansion_phase:
        self.expansion_phase -= 1
        radius_m = random.randint(5, 15)
      else:
        if len(self.my_units) > 10 and random.random() > 0.95:
          self.expansion_phase = random.randint(5, 10)


      for p in self.buildings:
        if not self.guarding[p]:
          for g in self.guarding:
            guards = self.guarding[g]
            if len(guards) > 2:
              leave_guard = guards[-1]
              leave_guard.base = p
              self.guarding[p].append(leave_guard)
              break

      for s in self.squads:
        radius = min(math.log(self.mapsize)*main_circle_size/2, 5)

        if not self.buildings[s.base].team == self.team:
          radius = 1

        s.radius = radius * radius_m
        s.destination = self.fuzz_position(s.base, s.sight)
        s.spin()

      # Send the explorer around
      if not self.explorer.is_moving():
        destination = self.searcher.next_destination(self.explorer)
        self.searcher.destinations[self.explorer] = destination
        self.searcher.visiting[destination] = self.explorer
        self.explorer.destination = destination
      self.explorer.radius = self.explorer.sight*len(self.explorer) / 4
      self.explorer.spin()


    def _unit_spawned(self, unit):
      def make_explorer():
        self.explorer.add_unit(unit)
        self.explorer.destination = unit.position
        self.explorer.base = unit.position

      # if we have no explorers...
      if len(self.explorer) == 0:
        make_explorer()
        return

      if len(self.my_units) / len(self.explorer) >= self.cluster_size:
        if len(self.explorer) < 3:
          make_explorer()
          return


      for s in self.squads:
        if len(s) < self.cluster_size:
          s.add_unit(unit)
          return


      s = okay.CircleSquad(base=unit.position, mapsize=self.mapsize)
      self.squads.append(s)
      s.add_unit(unit)
      s.radian_offset = random.randint(1, 30)*THIRTY_DEGREES
      self.guarding[s] = unit.position

    def _unit_died(self, unit):
      to_remove = []
      for s in self.squads:
        s.remove_unit(unit)
        if len(s) == 0:
          to_remove.append(s)

      self.explorer.remove_unit(unit)

      for s in to_remove:
        self.squads.remove(s)
        for g in self.guarding:
          guards = self.guarding[g]
          if s in guards:
            guards.remove(s)

