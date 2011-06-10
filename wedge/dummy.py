import ai
import itertools

AIClass = "TrainingDummy"


# just moves a unit back and forth across the center of the map, extra units go to 0,0
class TrainingDummy(ai.AI):
	
	def _init(self):
		self.patrol = [ (0, self.mapsize / 2), (self.mapsize, self.mapsize / 2) ] 
		self.station = itertools.cycle( self.patrol )
		
	def _spin(self):
		for unit in self.my_units:
			if not unit.is_moving:
				unit.move( self.station.next() )
