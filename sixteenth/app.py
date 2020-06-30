import math
import random
import numpy as np

from fourth.app import *  # based on 4th lab


def get_y(c, t):
    global w_last
    print('using 16th lab')
    eps = sum(random.random() for _ in range(12)) - 6
    eps += (eps ** 3 - 3 * eps) / 240.0
    wti1 = w_last + math.sqrt(dt) * eps
    w_last = wti1
    return c * math.exp((mu - ((sigma ** 2) / 2)) * dt + sigma * wti1)


custom_data['get_y'] = get_y
custom_data['current'] = 'sixteenth'
dt, mu, sigma = 0.01, 0.5, 0.1
w_last = 0
