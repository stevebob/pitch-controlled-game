import pygame
from pygame.locals import *
import struct
from numpy.fft import fft
import numpy
import pyaudio
import wave
import sys
import os
import math

N = 1024

WHITE = (255, 255, 255)
BLUE = (100, 150, 255)
RED = (200, 0, 0)
BLACK = (0, 0, 0)
WIDTH = 600
HEIGHT = 400
RES = 2

pygame.init()
surface = pygame.display.set_mode((WIDTH,HEIGHT))
pygame.display.set_caption('Pitch Controlled Game')

# This function takes a collection of data given as a list of floats,
# and returns those numers plotted on a log scale. The resulting data
# can be plotted on with 'output_range' as the x axis. The input data
# is linearly interpolated between points in the output_range to get
# the resulting data.
# data: points to be plotted (pre logged)
# output_range: the x values at which plots will occur
def log_interpolate(data, output_range, x_scale):

  # find the points on the x axis where the given data will be plotted
  logged_range = map(lambda x: math.log(x + 1)*x_scale, range(len(data)))

  # index into the logged x range
  i_log = 0

  # index into the output x range
  i_out = 0

  # create the array to hold the resulting data
  output_data = [0] * len(output_range)

  # zero fill the desired output if there are any unknown requests
  while output_range[i_out] < logged_range[0]:
    i_out += 1

  # eat any logged x points before the output points begin
  while logged_range[i_log] < output_range[0]:
    i_log += 1

  # outer loop - for each logged range value
  while i_log < len(logged_range) and i_out < len(output_range):
    # determine the gradient between the current and previous logged value
    dy = data[i_log] - data[i_log-1]
    dx = logged_range[i_log] - logged_range[i_log-1]
    gradient = float(dy)/float(dx)
    y_icp = data[i_log] - gradient * logged_range[i_log]

    # interpolate the values between the current and last logged values
    while i_out < len(output_range) and output_range[i_out] < logged_range[i_log]:
      output_data[i_out] = gradient * output_range[i_out] + y_icp
      i_out += 1

    # increment the outer loop counter
    while i_log < len(logged_range) and i_out < len(output_range) and not(output_range[i_out] < logged_range[i_log]):
      i_log += 1

  return map(int, output_data)



def display_freq(interpolated, base, offset, colour):

  x_val = 0

  for i in interpolated:
    x_pos = x_val
    y_pos = i
    pygame.draw.line(surface, colour, (x_pos, HEIGHT), (x_pos, HEIGHT - y_pos))
    x_val += + RES


if len(sys.argv) < 2:
    print("Plays a wave file.\n\nUsage: %s filename.wav" % sys.argv[0])
    sys.exit(-1)

wf = wave.open(sys.argv[1], 'rb')

p = pyaudio.PyAudio()

stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
                channels=wf.getnchannels(),
                rate=wf.getframerate(),
                output=True)
nchannels = wf.getnchannels()

# used for finding the "dominant frequency"
main_freq = -1
move_count = 0


data = None
while data != '':

    data = wf.readframes(N)
    data_unpacked = numpy.array(struct.unpack("%dh" % (N * nchannels), data))
    channel_l = data_unpacked[::2]
    channel_r = data_unpacked[1::2]
    channel_l_freq = fft(channel_l)[:len(channel_l)/4]
#    channel_r_freq = fft(channel_r)[:len(channel_r)/2]

    surface.fill(BLACK)

    freq = map(lambda x: min(x/7000, 700), map(int, map(abs, channel_l_freq)))
    interpolated = log_interpolate(map(lambda x: math.log(x+1)*40, freq), map(lambda x: RES * x, range(WIDTH/RES)), 110)

    # find the "dominant frequency"
    t_start = (len(interpolated)*2)/5
    t_end = (len(interpolated)*3)/4
    treble = interpolated[t_start:t_end]
    max_amp = treble[0]
    freq = t_start
    j = 0
    for i in treble:
      if i > max_amp:
        max_amp = i
        freq = j
      j += 1

    if main_freq == -1:
      main_freq = freq
    elif abs(main_freq - freq) < 20:
      main_freq = freq
      move_count = 0
    else:
      move_count += 1
      if move_count > 1000:
        main_freq = freq
        move_count = 0

    # draw the spectograph
    display_freq(interpolated, 1, 0, WHITE)
    pygame.draw.rect(surface, RED, pygame.Rect((t_start + main_freq)*RES - 10, HEIGHT - 20, 20, 20))
    pygame.display.update()

    stream.write(data)

stream.stop_stream()
stream.close()

p.terminate()
