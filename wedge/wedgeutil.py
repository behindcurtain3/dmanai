import random
import math
from world import isValidSquare

toRadians = 3.14159 / 180

def calc_distance(a, b):
  return ( abs(a[0] - b[0]) + abs(a[1] - b[1]) )

def closest_thing(position, things):
  closest = 100000
  found = None
  
  for t in things:
    distance = calc_distance( position, t.position )

    if distance < closest:
      closest = distance
      found = t

  return found

def position_on_circle(radius, center, angle = None):
  x,y = -1,-1

  if angle == None:
    angle = random.randint(0,360)

  angle *= toRadians

  x = center[0] + radius * math.sin(angle)
  y = center[1] + radius * math.cos(angle)
  return (x,y)  
