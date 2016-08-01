#!/usr/bin/env python
# -*- encoding: utf-8 -*-

import argparse
import sys
import os
import binascii
import copy

# The assembler, disassembler and simulator libraries
from asm6502 import asm6502
from dis6502 import dis6502
from sim6502 import sim6502

# The termbox library for writing to the screen
import termbox

# temrbox_util adds a curses like interface to termbox
from termbox_util import termbox_util
from termbox_util import termbox_editableline

# Also get the virtual viewplane support
# Allows virtual text screen that can be displayed
# on a real screen. Good for scrolling through lists.
# Have a static list (like a memory view) and move
# the viewport.
from termbox_util import viewplane

leftwidth = 40
memory_selected = True

current_pc_disassembly_line = 0
disassembly_count = 0
linelist=list()

def el_validator(e):  
    (type, ch, key, mod, w, h, x, y ) = e
    if type==termbox.EVENT_KEY and key == termbox.KEY_ENTER:
        return(7)
    else:
        return(ch)

def draw_commands_view(vptu):
    vptu.clear()
    vptu.border()
    vptu.addstr(x=4,y=0,thestring="COMMANDS",bold=False)
    vptu.addstr(x=1, y=1, thestring="r: Reset, I: Irq, N:Nmi, S:Step, K:sKip, G: Goto Addr, i/k:mem up/down, o/l:page up/down", bold=False)
    vptu.addstr(x=1, y=2, thestring="ESC: exit B: set Breakpoint M:Modify Memory", bold=False)

# 7	        6	        5	    4	    3	    2	        1	    0
# Negative	Overflow	(S)     Break	Decimal	Interrupt	Zero	Carry
# N	        V	        -	    B	    D	    I	        Z	    C
# -	        -	        -	    -	    -	    -	        -	    -    

def draw_registers_view(vptu,pc,a,x,y,sp,cc):
    cc = cc
    ccstr = ""
    for i in xrange(8):
        if (cc & 128)==128:
            ccstr += "1"
        else:
            ccstr += "."
        cc = cc << 1
        
    vptu.clear()
    vptu.border()
    vptu.addstr(x=4,y=0,thestring="REGISTERS",bold=False)
    vptu.addstr(x=1, y=1, thestring="PC:%04x A:%02x X:%02x Y:%02x NVsBDIZC" % (pc,a,x,y), bold=False)
    vptu.addstr(x=1, y=2, thestring="SP:%04x          Flags:%s" % (sp,ccstr), bold=False)  

def draw_action_view(vptu,actionstr):
    vptu.clear()
    vptu.border()
    vptu.addstr(x=4, y=0, thestring="ACTION", bold=False)
    vptu.addstr(x=1, y=1, thestring=actionstr, bold=False) 

def update_memory_inner_view(vptu,startaddr,object_code):
    vptu.clear()
    maxx,maxy = vptu.getmaxxy()
    
    startline = startaddr / 8
    endline = start + maxy
    for line in xrange(startline,endline+1):
        addr = line*8
        vptu.addstr(x=0,y=line,thestring="%04x"%addr,bold=False)
        for i in xrange(8):
            value = object_code[addr+i]
            if value >= 0:
                if (a.instruction_map[addr+i] == None):
                    vptu.addstr(x=5+(i*3),y=line,thestring="%02x"%object_code[addr+i],bold=False)
                    #vptu.addstr(x=5+(i*3),y=line,thestring="nn",bold=False)
                elif (a.instruction_map[addr+i] >= 0) and (a.instruction_map[addr+i] < 256):
                    vptu.addstr(x=5+(i*3),y=line,thestring="%02x"%object_code[addr+i],bold=True)
                else:
                    vptu.addstr(x=5+(i*3),y=line,thestring="%02x"%object_code[addr+i],bold=False)
                    #vptu.addstr(x=5+(i*3),y=line,thestring="xx",bold=False)
            if (value > 31) and (value < 128):
                vptu.addstr(x=29+i,y=line,thestring=chr(object_code[addr+i]),bold=False)
 
def draw_memory_inner_view(vptu,object_code):
    vptu.clear()
    for line in xrange(8192):
        addr = line*8
        vptu.addstr(x=0,y=line,thestring="%04x"%addr,bold=False)
        astr = "%04x" % addr
        for i in xrange(8):
            value = object_code[addr+i]
            if value >= 0:
                if (a.instruction_map[addr+i] == None):
                    vptu.addstr(x=5+(i*3),y=line,thestring="%02x"%object_code[addr+i],bold=False)
                    #vptu.addstr(x=5+(i*3),y=line,thestring="nn",bold=False)
                elif (a.instruction_map[addr+i] >= 0) and (a.instruction_map[addr+i] < 256):
                    vptu.addstr(x=5+(i*3),y=line,thestring="%02x"%object_code[addr+i],bold=True)
                else:
                    vptu.addstr(x=5+(i*3),y=line,thestring="%02x"%object_code[addr+i],bold=False)
                    #vptu.addstr(x=5+(i*3),y=line,thestring="xx",bold=False)
            if (value > 31) and (value < 128):
                vptu.addstr(x=29+i,y=line,thestring=chr(object_code[addr+i]),bold=False)

def draw_memory_inner_view_partial(vptu,startline,endline,object_code):
    for line in xrange(startline,endline+1):
        addr = line*8
        vptu.addstr(x=0,y=line,thestring="%04x"%addr,bold=False)
        astr = "%04x" % addr
        for i in xrange(8):
            value = object_code[addr+i]
            if value >= 0:
                if (a.instruction_map[addr+i] == None):
                    vptu.addstr(x=5+(i*3),y=line,thestring="%02x"%object_code[addr+i],bold=False)
                    #vptu.addstr(x=5+(i*3),y=line,thestring="nn",bold=False)
                elif (a.instruction_map[addr+i] >= 0) and (a.instruction_map[addr+i] < 256):
                    vptu.addstr(x=5+(i*3),y=line,thestring="%02x"%object_code[addr+i],bold=True)
                else:
                    vptu.addstr(x=5+(i*3),y=line,thestring="%02x"%object_code[addr+i],bold=False)
                    #vptu.addstr(x=5+(i*3),y=line,thestring="xx",bold=False)
            if (value > 31) and (value < 128):
                vptu.addstr(x=29+i,y=line,thestring=chr(object_code[addr+i]),bold=False)
        
def draw_memory_outer_view(vptu,memory_selected):
    vptu.clear()
    vptu.border()
    vptu.addstr(x=4,y=0,thestring="MEMORY",bold=memory_selected)

def draw_disassembly_inner_view(vptu,object_code):
    vptu.clear()
    vptu.addstr(1,1,"wut?")
    # Start with PC. Disassemble a line and put it in a list of lines.
    # Then work backwards until we reach -49 lines or 0
    # Then work forwards until we reach +50 lines or ffff
    # Then we have a list of lines to display.
    # Show them in the window and highlight the instruction at pc.
    linelist = list()
    line = dis.disassemble_line(s.pc) # The first line at pc
    linelist.append(line)
    
    # Now work backwards from pc
    reversecount = 0
    address = s.pc
    while (reversecount < 49) and (address > 0): 
        if a.instruction_map[address-1] == -1:
            address = address -2
            thetype = "instruction"
        elif a.instruction_map[address-1]==-2:
            address = address -3
            thetype = "instruction"
        elif (a.instruction_map[address-1] >= 0) and (a.instruction_map[address-1] < 256):
            address = address -1
            thetype = "instruction"
        else:
            address = address -1
            thetype = "data"
            
        if thetype == "data":
            line = "           %04x %02x       DW  $%02x" % (address,object_code[address],object_code[address])
        else:
            line = dis.disassemble_line(address)
        linelist.insert(0,line)
        reversecount += 1
    vptu.addstr(2,2,"reversecount="+str(reversecount).ljust(17))    
    # Now work forwards
    forwardcount = 0
    address = s.pc
    while (forwardcount < 50) and (address < 0xffff): 
        if (a.instruction_map[address+1])==None:
            address = address+1
            thetype = "data"
        elif (a.instruction_map[address+1] >= 0) and (a.instruction_map[address+1] < 256):
            address = address +1
            thetype = "instruction"
        elif (a.instruction_map[address+1]==-1) and (a.instruction_map[address+2] >= 0) and (a.instruction_map[address+2] < 256):
            address = address +2
            thetype = "instruction"
        elif (a.instruction_map[address+1]==-1) and (a.instruction_map[address+3] >= 0) and (a.instruction_map[address+3] < 256):
            address = address +3
            thetype = "instruction"
        else:
            address = address +1
            thetype = "data"
            
        if thetype == "data":
            line = "           %04x %02x       DW  $%02x" % (address,object_code[address],object_code[address])
        else:
            line = dis.disassemble_line(address)
        linelist.append(line)
        forwardcount += 1
        
        # Now put the lines into the inner view with pc somewhere near the middle
     
    # Add the reverse list       
    for i in xrange(reversecount):
        vptu.addstr(x=0,y=i,thestring=linelist[i],bold=False)
        
    # Add the current instruction highlighted
    vptu.addstr(x=0,y=reversecount,thestring=linelist[reversecount],bold=True)
    
    # Add the forward list       
    for i in xrange(forwardcount):
        vptu.addstr(x=0,y=i+reversecount+1,thestring=linelist[i+1+reversecount],bold=False)
    
    current_pc_disassembly_line = reversecount
    disassembly_count = len(linelist)
    return (current_pc_disassembly_line,disassembly_count)
def draw_disassembly_outer_view(vptu,memory_selected):
    vptu.clear()
    vptu.border()
    vptu.addstr(x=4,y=0,thestring="DISASSEMBLY",bold=not(memory_selected))

def dbg6502(object_code, symbol_table):
    object_code = s.object_code
    memory_selected = True
    # Use a real termbox window tbinst.   
    with termbox.Termbox() as tb:
        # The things we seen in the main view are composed
        # in virtual viewplanes which are placed within
        # the physical termbox view
        tbtu = termbox_util(tb)
        tbtu.clear()
        
        # Compute some positions
        maxx,maxy=tbtu.getmaxxy()
        memorywindowheight=maxy -12
        rightwidth = maxx-leftwidth
              
        # A viewplane to hold the command information      
        vp_commands=viewplane(width=maxx+1,height=4)
        vptu_commands = termbox_util(vp_commands) 
        draw_commands_view(vptu_commands)
        
        # A viewplane to hold the register state   
        vp_registers=viewplane(width=leftwidth,height=4)
        vptu_registers = termbox_util(vp_registers)
        draw_registers_view(vptu_registers,0,0,0,0,0x100,0)

        # A viewplane to hold the action view  
        vp_action=viewplane(width=leftwidth,height=4)
        vptu_action = termbox_util(vp_action)
        draw_action_view(vptu_action,"Nothing Yet")
        
        # Since we have a sliding memory view but want a box around the
        # visible window, we will have a two deep hierarchy - the outer
        # with the border and the inner, set inside with the scrolling
        # view.
        
        # A viewplane to hold the inner memory view, 8 bytes per line * 8192 = 64k  
        vp_memory_inner=viewplane(width=leftwidth-2,height=8192)
        vptu_memory_inner = termbox_util(vp_memory_inner)
        draw_memory_inner_view(vptu_memory_inner, object_code)
        
        # The outer to hold the border and the innner
        vp_memory_outer=viewplane(width=leftwidth,height=memorywindowheight)
        vptu_memory_outer = termbox_util(vp_memory_outer)
        draw_memory_outer_view(vptu_memory_outer,memory_selected)
        
        # Add the views as persistent views in the terminal view
        pvid_commands = tbtu.add_persistent_viewplane(vp_commands,0,0)
        pvid_registers = tbtu.add_persistent_viewplane(vp_registers,0,4)
        pvid_action = tbtu.add_persistent_viewplane(vp_action,0,8)
        
        # The memory view is a window into the viewplane since the
        # viewplane has the whole of memory laid out in.
        # Parameters are : vp,width,height,srcx,srcy,viewx,viewy,active
        pvid_memory_outer = tbtu.add_persistent_viewplane(vp_memory_outer,0,12)
        
        # Put the inner memory view in the outer memory view
        pvid_memory_inner = vptu_memory_outer.add_persistent_viewplane_window(vp_memory_inner,leftwidth-2,memorywindowheight-2,0,0,1,1,True)
        
        # The disassembly view
        vp_disassembly_inner=viewplane(width=maxx+1-leftwidth-2,height=100)
        vptu_disassembly_inner = termbox_util(vp_disassembly_inner)
        s.pc = 0
        draw_disassembly_inner_view(vptu_disassembly_inner, object_code)
        
        # The outer to hold the border and the innner
        vp_disassembly_outer=viewplane(width=maxx+1-leftwidth,height=maxy-12)
        vptu_disassembly_outer = termbox_util(vp_disassembly_outer)
        draw_disassembly_outer_view(vptu_disassembly_outer,memory_selected)
        
        # The disassembly view is a window into the viewplane since the
        # viewplane has a lot of listing laid out in.
        # Parameters are : vp,width,height,srcx,srcy,viewx,viewy,active
        pvid_disassembly_outer = tbtu.add_persistent_viewplane(vp_disassembly_outer,leftwidth,12)
        
        # Put the inner memory view in the outer memory view
        pvid_disassembly_inner = vptu_disassembly_outer.add_persistent_viewplane_window(vp_disassembly_inner,(maxx-leftwidth-2),maxy-14,0,0,1,1,True)
        
        # The main loop
        # Listen for keypresses and do what is asked
        # Quit when esc is pressed
        
        memaddr = 0
        
        while True:            
            #Refresh the screen
            (cpdl,dc) = draw_disassembly_inner_view(vptu_disassembly_inner,object_code)
            #draw_memory_inner_view(vptu_memory_inner, object_code)
            vptu_memory_outer.present()
            new_srcx=0
            if cpdl > 0:
                new_srcy = cpdl -10
                if new_srcy < 0:
                    new_srcy = 0
            else:
                new_srcy = 0
            vptu_disassembly_outer.move_persistent_viewplane_window(pvid_memory_inner,new_srcx,new_srcy) 
            #vptu_disassembly_outer.addstr(20,0,"cpdl="+str(cpdl)+" len="+str(dc)+" ")
            vptu_disassembly_outer.present() 
            draw_registers_view(vptu_registers,s.pc,s.a,s.x,s.y,s.sp,s.cc)                   
            tbtu.present()
            
            # Get a keypress
            event = tb.poll_event()
            # untangle it's fields
            (type, ch, key, mod, w, h, x, y ) = event
            
            ## Go to an edit box if the user presses 'e'
            #if type==termbox.EVENT_KEY and ch=='e':
            #    content=el.edit(el_validator,max_width=10)
 
            tbtu.addstr(leftwidth+3,5,str(event))
            # Exit when escape pressed.
            if type==termbox.EVENT_KEY and key == termbox.KEY_ESC:
                return event
            
            if type==type==termbox.EVENT_KEY and key == termbox_util.key_tab:
                memory_selected = not(memory_selected)
                draw_memory_outer_view(vptu_memory_outer,memory_selected)
                draw_disassembly_outer_view(vptu_disassembly_outer,memory_selected)
                
            # When r is pressed, sent a reset to the simulator
            elif type==termbox.EVENT_KEY and ch=='R':
                s.reset()
                vptu_action.addstr(1,1,"RESET          ")
                draw_memory_inner_view(vptu_memory_inner, object_code)
                
            
            # When r is pressed, sent a reset to the simulator
            elif type==termbox.EVENT_KEY and ch=='I':
                s.irq()
                vptu_action.addstr(1,1,"IRQ            ")
                draw_memory_inner_view(vptu_memory_inner, object_code)
            
            # When r is pressed, sent a reset to the simulator
            elif type==termbox.EVENT_KEY and ch=='N':
                s.reset()
                vptu_action.addstr(1,1,"NMI            ")
                draw_memory_inner_view(vptu_memory_inner, object_code)
                    
            # When s is pressed, execute one instruction
            elif type==termbox.EVENT_KEY and ch=='s':
                distxt = dis.disassemble_line(s.pc)
                (action, addr) = s.execute()
                vptu_action.addstr(1,1,distxt.ljust(leftwidth-2))
                draw_registers_view(vptu_registers,s.pc,s.a,s.x,s.y,s.sp,s.cc)
                draw_disassembly_inner_view(vptu_disassembly_inner,object_code)
                
                # simulator indicated it tried to run uninitialized memory
                if action=="weeds":
                    vptu_action.addstr(1,2,"In unitialized mem    ".ljust(leftwidth-2))
                    
                # Memory changed so update that part of the memory view
                # Back up a bit in case we are in a multi byte stack op
                elif action=="w":
                    startline = addr / 8
                    startline -= 1
                    endline = startline+2
                    vptu_action.addstr(1,2,("modified %04x=%02x    " % (addr,s.object_code[addr])).ljust(leftwidth-2))
                    draw_memory_inner_view_partial(vptu_memory_inner,startline,endline,object_code)
                    vptu_memory_outer.present()
                elif action == "stack":
                    startline = 0x100
                    endline = 0x200
                    vptu_action.addstr(1,2,"modified stack  ".ljust(leftwidth-2))
                    draw_memory_inner_view_partial(vptu_memory_inner,startline,endline,object_code)
                    vptu_memory_outer.present()
                elif action == "not_instruction":
                    vptu_action.addstr(1,2,"Not an instruction  ".ljust(leftwidth-2))
                else:
                    vptu_action.addstr(1,2,"      ".ljust(leftwidth-2))   
                     
            # Move memory window with the mouse wheel
            elif type==termbox.EVENT_KEY and key==termbox_util.TB_KEY_ARROW_UP:
            #elif type==termbox.EVENT_KEY and ch=='i':
                memaddr -= 8
                if memaddr < 0:
                    memaddr = 0
                    
                new_srcy = memaddr/8
                new_srcx = 0
                vptu_memory_outer.move_persistent_viewplane_window(pvid_memory_inner,new_srcx,new_srcy)
                
            # Move memory window with the mouse wheel
            #elif type==termbox.EVENT_KEY and key==termbox_util.TB_KEY_ARROW_UP:
            elif type==termbox.EVENT_KEY and ch=='o':
                memaddr -= 8*32
                if memaddr < 0:
                    memaddr = 0
                    
                new_srcy = memaddr/8
                new_srcx = 0         
                vptu_memory_outer.move_persistent_viewplane_window(pvid_memory_inner,new_srcx,new_srcy)

            elif type==termbox.EVENT_KEY and key==termbox_util.TB_KEY_ARROW_DOWN:
            #elif type==termbox.EVENT_KEY and ch=='k':
                memaddr += 8
                line = memaddr/8
                if (line+memorywindowheight-2) < 8192:
                    memaddr = memaddr % 65536
                    new_srcy = line
                    new_srcx = 0
                    vptu_memory_outer.move_persistent_viewplane_window(pvid_memory_inner,new_srcx,new_srcy)

            #elif type==termbox.EVENT_KEY and key==termbox_util.TB_KEY_MOUSE_WHEEL_DOWN:
            elif type==termbox.EVENT_KEY and ch=='l':
                memaddr += 8*32
                line = memaddr/8
                if (line+memorywindowheight-2) < 8192:
                    memaddr = memaddr % 65536
                    new_srcy = line
                    new_srcx = 0
                    vptu_memory_outer.move_persistent_viewplane_window(pvid_memory_inner,new_srcx,new_srcy)


# Start with argument parsing

parser = argparse.ArgumentParser(description='A 65C02 debugger built on the py6502 assembler, simulator and debugger')

parser.add_argument("-v","--verbose",action="store_true", dest="verbose", default=False, help="Print status messages to stderr")
parser.add_argument("filename", help="read assembly from filename", nargs='?', metavar="FILE")

options = parser.parse_args()

filename = str(options.filename)
if (options.filename == None):
    print "[py6502 Debugger] Error - A filename of an assembly file is required"
    quit()

if (options.verbose==True):
    verbose = True
else:
    verbose = False

if (verbose):
    sys.stderr.write("filename:"+str(filename)+"\n")
    sys.stderr.write("verbose :"+str(verbose)+"\n")

# open the assembly file
f = open(str(options.filename))

# Read the file
try:
    lines = f.readlines()
except IOError:
    sys.stderr.write("ERROR: File Error")
    try:
        sys.stderr.close()
    except IOError:
        pass
    quit()

#
# Assemble the file
#

a = asm6502()
a.assemble(lines)

object_code = copy.deepcopy(a.object_code)
symbol_table = copy.deepcopy(a.symbols)

# Simulator instance
s = sim6502(object_code,symbols=symbol_table)

# Disassembler Instance
dis = dis6502(s.object_code,symbols=symbol_table)

# start the debugger
d = dbg6502(object_code,symbol_table)
#print d

print "Exited 6502 Debugger"

