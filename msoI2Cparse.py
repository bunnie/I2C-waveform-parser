# parse and render I2C oscilloscope data
# input is CSB file created by MSO series oscilloscopes
# assumes channel 0 is SDC, channel 1 is SDA

# bunnie (c) 2012, BSD license

import sys
import re
import curses
import os
import string

digs = string.digits + string.lowercase
def int2base(x, base):
    if x < 0: sign = -1
    elif x==0: return '0'
    else: sign = 1
    x *= sign
    digits = []
    while x:
        digits.append(digs[x % base])
        x /= base
    if sign < 0:
        digits.append('-')
    digits.reverse()
    return ''.join(digits)

term_rows, term_cols = os.popen('stty size', 'r').read().split()

one = '-'
zero = '_'

threshold = 2.5

wave = []

####### 
if len(sys.argv) != 2:
    print 'usage: ' + sys.argv[0] + ' <filename>'
    exit(0)

print 'Parsing input data (press space when done to continue)...',
lines = 0
with open( sys.argv[1], 'r' ) as f:
    for line in f:
        lines = lines + 1
        if lines % 50000 == 0:
            sys.stdout.write('.')
            sys.stdout.flush()
        if re.match('^\d', line):
            data = line.split(',')
            if float(data[2]) > threshold: # swap in the CSV column index for your clock data
                ck = one
            else:
                ck = zero
            if float(data[4]) > threshold: # swap in the CSV column index for your data data
                dt = one
            else:
                dt = zero
            wave.append([ck,dt])
        else:
            continue

sys.stdout.flush()

stdscr = curses.initscr()
curses.noecho()
curses.cbreak()
stdscr.keypad(1)

index = 0
width = int(term_cols) - 4
orig_y = 1
orig_x = 1
height = 9

label_width = 6
scale = 1

hexline = 7

try:
    win = curses.newwin(height, width, orig_x, orig_y)
    state = 'idle'
    bitcnt = 0
    bitval = 0
    while 1:
        try:
            oldclk = wave[index][0]
            olddat = wave[index][1]
            win.clear()
        except IndexError:
            pass

        clkrise = False
        clkfall = False
        datrise = False
        datfall = False

        for x in range(0, width * scale):
            try:
                if (x % scale) == 0:
                    win.addch(2, x / scale + label_width, wave[index + x][0])
                    win.addch(4, x / scale + label_width, wave[index + x][1])
                if (x % (10 * scale)) == 0:
                    win.addstr(1, x / scale + label_width, str(index + x) + ' ' * 3) 

                clkrise = (oldclk == zero) and (wave[index + x][0] == one) 
                clkfall = (oldclk == one) and (wave[index + x][0] == zero) 
                datrise = (olddat == zero) and (wave[index + x][1] == one) 
                datfall = (olddat == one) and (wave[index + x][1] == zero) 
                
                if (wave[index + x][0] == one) and datfall:
                    win.addch(6, x / scale + label_width, 'S')
                    state = 'started'
                    bitcnt = 0
                    bitval = 0
                elif (wave[index + x][0] == one) and datrise:
                    win.addch(6, x / scale + label_width, 'P')
                    state = 'idle'
                    bitcnt = 0
                    bitval = 0
                elif clkrise:
                    bit = 0
                    if olddat == one:
                        win.addch(6, x / scale + label_width, '1' )
                        bit = 1
                    else:
                        win.addch(6, x / scale + label_width, '0' )
                        bit = 0
                    if state == 'started':
                        bitval = bitval << 1
                        bitval = bitval | bit
                        bitcnt = bitcnt + 1
                        if (bitcnt % 4) == 0 and bitcnt != 0:
                            win.addch(hexline, x / scale + label_width, int2base(bitval & 0xF,16) )
                        if bitcnt == 9:
                            if olddat == one: 
                                ack = 'v'  # nack state
                            else:
                                ack = '^'  # ack state
                            win.addch(hexline, x / scale + label_width, ack)
                            bitcnt = 0
                            bitval = 0
                            

                oldclk = wave[index + x][0]
                olddat = wave[index + x][1]
            except curses.error: 
                pass
            except IndexError:
                pass
        
        win.addstr(0, 0, '+/- zoom; ,/. scroll; q to quit')
        win.addstr(1, 0, 'time')
        win.addstr(2, 0, 'clk')
        win.addstr(4, 0, 'dat')
        win.addstr(6, 0, 'meta')
        win.addstr(hexline, 0, 'hex')
        win.refresh()
        
        curses.flushinp()
        c = stdscr.getch()
        if c == ord('q'):
            break
        elif c == ord('.'):
            if index < (len(wave) - (width * scale * 1.5) ):
                index = index + width / 2
            else:
                index = len(wave)
        elif c == ord(','):
            if index > width / 2:
                index = index - width / 2
            else:
                index = 0
        elif c == ord('-'):
            if scale < 10:
                scale = scale + 1
        elif c == ord('+'):
            if scale > 1:
                scale = scale - 1

finally:
    curses.nocbreak(); stdscr.keypad(0); curses.echo()
    curses.endwin()

