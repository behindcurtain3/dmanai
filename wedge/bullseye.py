require_dependency( module_name = "euclid" )

from euclid import *

class Predictor(object):
	def __init__(self, target, size):
		self.target = target
		self.last = Vector2(target.position[0], target.position[1])
		self.current = self.last
		self.mapsize = size

	def set_position(self, pos):
		self.last = self.current
		self.current = Vector2(pos[0], pos[1])
				
	# returns a predicted position for the target
	def predict(self, firing):
		
		if self.current == self.last:
			return ( self.current.x, self.current.y )
		
		source = Vector2(firing[0], firing[1])
		
		# holds our directional velocities
		v = self.current - self.last
		
		i = self.intersect(source, self.current, v, self.mapsize / 10)
		
		if i == None:
			return self.target.position
		else:
			# make sure the position is valid
			clean_i = list(i)
			if clean_i[0] < 0:
				clean_i[0] = 0
			if clean_i[0] > self.mapsize:
				clean_i[0] = self.mapsize
			if clean_i[1] < 0:
				clean_i[1] = 0
			if clean_i[1] > self.mapsize:
				clean_i[1] = self.mapsize
			
			return clean_i
		
	# src = position we are firing from
	# target = position of target currently
	# v = velocity of target
	# s = projectile speed	
	def intersect(self, src, target, v, s):
		tx = target.x - src.x
		ty = target.y - src.y
		tvx = v.x
		tvy = v.y
		
		a = tvx * tvx + tvy * tvy - s * s
		b = 2 * (tvx * tx + tvy * ty)
		c = tx * tx + ty * ty
		
		ts = self.quad(a, b, c)
		
		sol = None
		if ts:
			t0 = ts[0]
			t1 = ts[1]
			
			t = min(t0, t1)
			if t < 0:
				t = max(t0, t1)
			if t > 0:
				sol = (
					int(target.x + v.x * t),
					int(target.y + v.y * t)
				)
				
		return sol
		
	def quad(self, a, b, c):
		sol = None
		if abs(a) < 1E-6:
			if abs(b) < 1E-6:
				sol = (0,0) if abs(c) < 1E-6 else None
			else:
				sol = ( -c / b, -c / b)
		else:
			disc = b * b - 4 * a * c
			if disc >= 0:
				disc = math.sqrt(disc)
				a = 2 * a
				sol = ( (-b - disc) / a, (-b + disc) / a )
				
		return sol 
