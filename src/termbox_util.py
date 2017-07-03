#!/usr/bin/python
# -*- encoding: utf-8 -*-

import termbox
import inspect
from inspect import currentframe, getframeinfo

cf = currentframe()
filename = getframeinfo(cf).filename

import logging

# Implements a virtual screen of arbitary size.
# A rectangular view or views of a chosen size can be displayed on
# the real view.
# Handy for scrolling lists and things like that. Just draw the whole
# list then move the view window around.
# Implements the same drawing functions. Viewplanes in viewplanes are allowed.
#   Just call a_viewplane.draw_viewplane(sub_viewplane,...)
#             a_termbox_inst.draw_viewplane(a_viewplane,...)
#
# It doesn't implement getevent.
# It has a resize function that termbox doesn't.
#
# Copyright (c) 2015
# David Johnston
# dj@deadhat.com

class viewplane(object):
    def __init__(self,width,height,fg=termbox.WHITE,bg=termbox.BLACK):
        self.iwidth = width
        self.iheight = height
        
        self.mk_blanklines(fg=fg,bg=bg)
        #self.persistent_vp_list=list()
            
    def width(self):
        return self.iwidth
    
    def height(self):
        return self.iheight
        
    def mk_blanklines(self,fg=termbox.WHITE,bg=termbox.BLACK):
        self.chars = list()
        self.fgs = list()
        self.bgs = list()
        self.fgline=list()
        self.bgline=list()
        
        self.blankline = list()
        for c in range(self.iwidth):
            self.blankline.append(ord(u' '))
            self.fgline.append(fg)
            self.bgline.append(bg)
            
        for c in range(self.iheight):
            self.chars.append(self.blankline[:])
            self.fgs.append(self.fgline[:])
            self.bgs.append(self.bgline[:])
                    
    def getmaxxy(self):
        return (self.iwidth-1, self.iheight-1)
                    
    def getmaxyx(self):
        return (self.iheight-1, self.iwidth-1)
    
    def change_cell(self,x,y,ch,fg=termbox.WHITE,bg=termbox.BLACK):
        if (x > -1) and (x < self.iwidth) and (y > -1) and (y < self.iheight):
            self.chars[y][x]=ch
            self.bgs[y][x]=bg
            self.fgs[y][x]=fg
    
    def clear(self,fg=termbox.WHITE,bg=termbox.BLACK):
        self.mk_blanklines(fg=fg,bg=bg)
        
    def resize(self,width,height):
        if height < 1 or width < 1:
            return
            
        if height < self.iheight:
            self.chars=self.chars[:height]
            self.fgs=self.fgs[:height]
            self.bgs=self.bgs[:height]
            self.iheight = height
        
        if height > self.iheight:
            for i in range(height-self.iheight):
                self.chars.append(self.blankline)
                self.fgs.append(self.fgline)
                self.bgs.append(self.bgline)
                
            self.iheight = height
        
        # Trim off the ends if shrinking width.    
        if width < self.iwidth:
            self.fgline = self.fgline[:width]
            self.bgline = self.bgline[:width]
            for i in range(self.iheight):
                self.chars[i]=self.chars[i][:width]
                self.fgs[i] = self.fgs[i][:width]
                self.bgs[i] = self.bgs[i][:width]
            self.iwidth=width
        
        # Add blanks to ends of lines if increasing width
        if width > self.width:
            # First increase the length of the blank lines
            self.fgline=list()
            self.bgline=list()
            self.blankline = list()
            for c in range(width):
                self.blankline.append(ord(u' '))
                self.fgline.append(fg)
                self.bgline.append(bg)
            
            # Then tack blanks on the ends.
            for i in range(self.iheight):
                self.chars[i].join(self.blankline[self.iwidth:width])    
                self.fgs[i].join(self.fgline[self.iwidth:width])
                self.bgs[i].join(self.bgline[self.iwidth:width])
                
            self.iwidth = width
            
    #def present(self):
    #    for pvp in self.persistent_vp_list:
    #        (vp,width,height,srcx,srcy,viewx,viewy,active) = pvp
    #        if active:
    #            self.draw_viewplane_window(vp,width,height,srcx,srcy,viewx,viewy)
        
# The utility functions that operate over a termbox or viewplane
#             
class termbox_util():
    key_up   = 1
    key_down = 2
    key_left = 3
    key_right = 4
    key_escape = 5
    key_return = 6
    key_delete = 7
    key_backspace = 8
    key_tab = 9
    TB_KEY_F1               = (0xFFFF-0)
    TB_KEY_F2               = (0xFFFF-1)
    TB_KEY_F3               = (0xFFFF-2)
    TB_KEY_F4               = (0xFFFF-3)
    TB_KEY_F5               = (0xFFFF-4)
    TB_KEY_F6               = (0xFFFF-5)
    TB_KEY_F7               = (0xFFFF-6)
    TB_KEY_F8               = (0xFFFF-7)
    TB_KEY_F9               = (0xFFFF-8)
    TB_KEY_F10              = (0xFFFF-9)
    TB_KEY_F11              = (0xFFFF-10)
    TB_KEY_F12              = (0xFFFF-11)
    TB_KEY_INSERT           = (0xFFFF-12)
    TB_KEY_DELETE           = (0xFFFF-13)
    TB_KEY_HOME             = (0xFFFF-14)
    TB_KEY_END              = (0xFFFF-15)
    TB_KEY_PGUP             = (0xFFFF-16)
    TB_KEY_PGDN             = (0xFFFF-17)
    TB_KEY_ARROW_UP         = (0xFFFF-18)
    TB_KEY_ARROW_DOWN       = (0xFFFF-19)
    TB_KEY_ARROW_LEFT       = (0xFFFF-20)
    TB_KEY_ARROW_RIGHT      = (0xFFFF-21)
    TB_KEY_MOUSE_LEFT       = (0xFFFF-22)
    TB_KEY_MOUSE_RIGHT      = (0xFFFF-23)
    TB_KEY_MOUSE_MIDDLE     = (0xFFFF-24)
    TB_KEY_MOUSE_RELEASE    = (0xFFFF-25)
    TB_KEY_MOUSE_WHEEL_UP   = (0xFFFF-26)
    TB_KEY_MOUSE_WHEEL_DOWN = (0xFFFF-27)
    
    def __init__(self,tb):
        self.tb = tb
        self.fg = termbox.WHITE
        self.bg = termbox.BLACK
        self.persistent_vp_list=list() # for self displaying viewplanes
        
        #self.can_input = hasattr(tb, poll_event) and inspect.ismethod(getattr(tb, poll_event))
    
    def getmaxyx(self):
        x = self.tb.width()-1
        y = self.tb.height()-1
        self.maxx = x
        self.maxy = y
        return((y,x))
    
    def getmaxxy(self):
        x = self.tb.width()-1
        y = self.tb.height()-1
        self.maxx = x
        self.maxy = y
        return((x,y))

    def clear(self):
        self.tb.clear()
        #self.tb.present()

    def outside(self, x,y):
        maxy,maxx = self.getmaxyx()
        if ((x < 0) or (y < 0)):
            return True
        if x > maxx:
            return True
        if y > maxy:
            return True
        return False

    def addstr(self, x, y, thestring, bold=False):
        maxx,maxy = self.getmaxxy()

        # ignore attempts to place strings outside window boundary
        if y < 0 or y > maxy:
            return
            
        if x+len(thestring) < 1:
            return

        #truncate string so it doesn't run off edge of screen
        maxstringlen = maxx-x+1
        if (len(thestring)) > maxstringlen:
            thestring = thestring[:maxstringlen]

        # Then shave off the front if it isn't in the screen
        if x < 0:
            thestring = thestring[-x:]
            x = 0
            
        for i in range(len(thestring)):
            if bold:
                self.tb.change_cell(x+i, y, ord(thestring[i]), self.bg,self.fg)
            else:
                if (type(thestring) != str):
                    cf = currentframe()
                    lineno = cf.f_lineno
                    fn = getframeinfo(cf).filename
                    logging.debug(str("File: %s line: %d , Expecting sting, got %s" % (fn, lineno, thestring)))
                self.tb.change_cell(x+i, y, ord(thestring[i]), self.fg,self.bg)

    def hline(self,x1,y1,x2):
        # draw a horizontal line from x1,y1 to x2,y1
        
        #if self.outside(x1,y1):
        #    return
        #if self.outside(x2,y1):
        #    return

        if x1 > x2:
            (x1,x2) = (x2,x1)
        for x in range(x1,x2+1):
            self.tb.change_cell(x,y1,ord(u'─'),self.fg, self.bg)

    def vline(self,x1,y1,y2):
        # draw a vertical line from x1,y1 to x1,y2
        
        #if self.outside(x1,y1):
        #    return
        #if self.outside(x1,y2):
        #    return

        if y1 > y2:
            (y1,y2) = (y2,y1)
        for y in range(y1,y2+1):
            self.tb.change_cell(x1,y,ord(u'│'),self.fg, self.bg)
           
    def fill_area(self,ch,x1=0,y1=0,x2='maxx',y2='maxy',fg='fg', bg='bg'):
        # draw a filled rectangle from x1,y1 to x2,y2
        (maxx,maxy)=self.getmaxxy()
        if x2=='maxx':
            x2 = maxx
        if y2=='maxy':
            y2 = maxy
        if fg=='fg':
            fg=self.fg
        if bg=='bg':
            bg=self.bg
        
        ## Don't draw outside the screen
        #if self.outside(x1,y1):
        #    return
        #if self.outside(x2,y2):
        #    return
        
        # Switch corners so x1,y1 is top right
        if x1 > x2:
            (x1,y1,x2,y2) = (x2,y1,x1,y2)
        if y1 > x2:
            (x1,y1,x2,y2) = (x1,y2,x2,y1)
        
        width = 1+x2-x1
        height = 1+y2-y1
        
        #FillArea(x, y, w, h)
        for y in range(height):
            for x in range(width):
                self.tb.change_cell(x1+x, y1+y, ord(ch), fg, bg)
        
    def box(self,x1=0,y1=0,x2='maxx',y2='maxy'):
        # draw a box from x1,y1 to x2,y2
        (maxx,maxy)=self.getmaxxy()
        if x2=='maxx':
            x2 = maxx
        if y2=='maxy':
            y2 = maxy
        # Don't draw outside the screen
        #if self.outside(x1,y1):
        #    return
        #if self.outside(x2,y2):
        #    return
        
        # Switch corners so x1,y1 is top right
        if x1 > x2:
            (x1,y1,x2,y2) = (x2,y1,x1,y2)
        if y1 > x2:
            (x1,y1,x2,y2) = (x1,y2,x2,y1)

        #FillArea(x, y, w, h)
        self.hline(x1+1, y1, x2-1)       # top
        self.hline(x1+1, y2, x2-1)       # bottom
        self.vline(x1, y1+1, y2-1)       # left
        self.vline(x2, y1+1, y2-1)       # right
        self.tb.change_cell(x1, y1, ord(u'┌'), self.fg, self.bg)  # top-left corner
        self.tb.change_cell(x2, y1, ord(u'┐'), self.fg, self.bg)  # top-right corner
        self.tb.change_cell(x1, y2, ord(u'└'), self.fg, self.bg)  #bottom-left corner
        self.tb.change_cell(x2, y2, ord(u'┘'), self.fg, self.bg)  # bottom-right corner
        
    # Just draws a box around the full termbox
    # Avoids needing to put in the parameters to box.
    def border(self):
        #maxx,maxy = self.getmaxxy()
        self.box()

    
    def draw_viewplane(self,vp,viewx,viewy):
        (width,height)=vp.getmaxxy()
        width=width+1
        height=height+1
        
        for y in range(height):
            for x in range(width):
                ch = vp.chars[y][x]
                fg = vp.fgs[y][x]
                bg = vp.bgs[y][x]
                self.tb.change_cell(x+viewx,y+viewy, ch, fg, bg)

    def draw_viewplane_window(self,vp,width,height,srcx,srcy,viewx,viewy):
        if width < 1 or height < 1:
            return
        if width+srcx > vp.width():
            return
        if height+srcy > vp.height():
            return
        
        for line in range(height):
            for i in range(width):
                ch = vp.chars[line+srcy][i+srcx]
                fg = vp.fgs[line+srcy][i+srcx]
                bg = vp.bgs[line+srcy][i+srcx]
                self.tb.change_cell(viewx+i, viewy+line, ch, fg, bg)
            #print str(vp.chars[line+srcy])

    # The class holds onto a list of viewplane parameters and
    # present() displays them automatically. An active field is also added
    # which tells present() whether or not to display it.
    # So you can set up your viewplanes and work solely within
    # viewplanes and activate and deactivate them as needed.
    # The add_ method returns a pvid (persistent viewplane id) so it can be
    # referenced later.
    
    def add_persistent_viewplane(self,vp,viewx,viewy,active=True):
        (width,height)=vp.getmaxxy()
        width=width+1
        height=height+1
        
        pid = len(self.persistent_vp_list)
        self.persistent_vp_list.append((vp,width,height,0,0,viewx,viewy,active))
        return pid

    def add_persistent_viewplane_window(self,vp,width,height,srcx,srcy,viewx,viewy,active=True):
        abort = 0
        if width < 1 or height < 1:
            return None
        if width+srcx > vp.width():
            return None
        if height+srcy > vp.height():
            return None
        
        pid = len(self.persistent_vp_list)
        self.persistent_vp_list.append((vp,width,height,srcx,srcy,viewx,viewy, active))
        return pid
    
    def move_persistent_viewplane_window(self,pid,new_srcx,new_srcy):
        (vp,width,height,srcx,srcy,viewx,viewy, active) = self.persistent_vp_list[pid]
        self.persistent_vp_list[pid] = (vp,width,height,new_srcx,new_srcy,viewx,viewy,True)
        
    def activate_persistent_vp(self,pid):
        (vp,width,height,srcx,srcy,viewx,viewy, active) = self.persistent_vp_list[pid]
        self.persistent_vp_list[pid] = (vp,width,height,srcx,srcy,viewx,viewy,True)

    def deactivate_persistent_vp(self,pid):
        (vp,width,height,srcx,srcy,viewx,viewy, active) = self.persistent_vp_list[pid]
        self.persistent_vp_list[pid] = (vp,width,height,srcx,srcy,viewx,viewy,False)
    
    # Calls the underlaying present() but also draws any active persistent
    # viewplanes in the persistent_vp_list()
                
    def present(self):
        for pvp in self.persistent_vp_list:
            (vp,width,height,srcx,srcy,viewx,viewy,active) = pvp
            if active:
                self.draw_viewplane_window(vp,width,height,srcx,srcy,viewx,viewy)
        present_method = getattr(self.tb, "present", None)
        if callable(present_method):
            self.tb.present()
    
    # Asks the user to press a few keys, to build a dictionary of a key map
                
    def keymapper(self):
        keymap = dict()
        eventmap = dict()

        keys = ['key_up','key_down','key_left','key_right','key_escape',
                'key_return','key_delete','key_tab']


        self.clear()
        self.box()
        self.addstr(2,2,"Key Mapper")
                
        for name in keys:
            self.addstr(2,4,"Press %s            " % name)
            self.tb.present()
            event = self.tb.poll_event()
            keymap[name] = event
            eventmap[event] = name
                
        i = 0
        for akey in keymap:
            self.addstr(2,6+i,str(akey)+" = "+str(keymap[akey]))
            i = i+1
                
        return (keymap,eventmap)
            
# Implements a line of text that can be edited.
class termbox_editableline():
    def __init__(self,tbinst,tbutil, x,y, width):
        self.tbutil = tbutil
        self.tbinst = tbinst
        self.x = x
        self.y = y
        self.width = width
        self.contents=""
    
    # Highlights the edited textbox
    # Puts a cursor there
    # Takes in left-right for moving cursor
    # Adds ascii visibles at cursor position
    # Delete removes to the left of the cursor
    # Calls the validator (provided by caller) to handle the
    #   inputs. Validator returns:
    #      7 (CR) to finish editing.
    #      Ascii codes for typed characters
    #      Specials like escape need to be handled by the validator
    #         E.G. return a 7 and mark that esc was pressed to the
    #         program can know what to do next.  
    #      
    def edit(self,validator, contents="", max_width=None,presenter=None):
        original_contents=contents[:]
        blankstr = " "*self.width
        cursorpos=0
        ttype = 0
        tkey = 0
        windowstart=0
        event=" "
        if max_width==None:
            max_width=self.width

        #
        # Keep handling keystrokes until esc or return is pressed.
        #
        while True:
            # Erase what's there
            self.tbutil.addstr(self.x,self.y,blankstr,bold=True)
            
            # Work out what to display
            # Taking into account where in the string the window starts
            if len(contents)==0:
                displaystr=" "
            else:
                displaystr = contents[windowstart:]
                displaystr = displaystr[:self.width]
            #self.tbutil.addstr(self.x,self.y,displaystr,bold=True)

            # Then work out where to put the cursor
            if (cursorpos == windowstart):
                self.tbutil.addstr(self.x,self.y,displaystr[0],bold=False)
                self.tbutil.addstr(self.x+1,self.y,displaystr[1:],bold=True)
            elif (cursorpos == len(contents)):
                self.tbutil.addstr(self.x,self.y,displaystr,bold=True)
                self.tbutil.addstr(self.x+len(displaystr),self.y," ",bold=False)
            else:
                cpos = cursorpos-windowstart
                self.tbutil.addstr(self.x,self.y,displaystr[:cpos],bold=True)
                try:
                    self.tbutil.addstr(self.x+cpos,self.y,displaystr[cpos],bold=False)
                except:
                    pass
                try:
                    self.tbutil.addstr(self.x+cpos+1,self.y,displaystr[cpos+1:],bold=True)
                except:
                    pass
                try:
                    self.tbutil.addstr(self.x+len(displaystr),self.y,"  ",bold=False)
                except:
                    pass
                # Diagnostic output
                #self.tbutil.addstr(self.x,self.y+26,displaystr[:cpos]+"   ",bold=True)
                #self.tbutil.addstr(self.x,self.y+27,displaystr[cpos]+"   ",bold=False)
                #self.tbutil.addstr(self.x,self.y+28,displaystr[cpos+1:]+"   ",bold=True)
                #self.tbutil.addstr(self.x,self.y+29,str(cpos)+"    ",bold=True)
            
            # More Diagnostic Output 
            #self.tbutil.addstr(self.x,self.y+1,"  len(contents)="+str(len(contents))+" cursorpos="+str(cursorpos)+" windstrt="+str(windowstart)+"  ")
            #self.tbutil.addstr(self.x,self.y+24,"  contents  ="+contents+"   ")
            #self.tbutil.addstr(self.x,self.y+25,"  displaystr="+displaystr+"   ")

            # Show the screen then wait for input
            #
            if presenter==None:
                self.tbinst.present()
                event = self.tbinst.poll_event()
            else:
                presenter.present()
                event = presenter.poll_event()
            (ttype, ch, tkey, mod, w, h, x, y ) = event
            if event != None:
                c = validator(event,contents)
                #
                # Handle esc, return, delete, up, down, left, right and input characters. 
                #
            
                # Return Pressed
                if c == 7:
                    return (contents)
                elif (ttype==1) and (tkey ==  27): # ESC pressed
                    return (original_contents)
                elif (tkey ==  self.tbutil.key_left) or (tkey == self.tbutil.TB_KEY_ARROW_LEFT):
                    #self.tbutil.addstr(self.x,self.y+2," LEFT           ")
                    if cursorpos > 0:
                        cursorpos = cursorpos - 1
                elif (tkey ==  self.tbutil.key_right) or (tkey == self.tbutil.TB_KEY_ARROW_RIGHT):
                    #self.tbutil.addstr(self.x,self.y+2," RIGHT          ")
                    if cursorpos < (len(contents)):
                        cursorpos = cursorpos + 1
                elif (ttype==1) and (tkey==127): # delete pressed
                    if (cursorpos >= len(contents)) and (cursorpos > 0):  # cursor is at end. Take one off the end
                        #self.tbutil.addstr(self.x,self.y+2," DELETE END      ")
                        contents = contents[:-1]
                        cursorpos -= 1
                    elif (cursorpos > 0) and (cursorpos < len(contents)):  # cursor somewhere in the middle.
                        #self.tbutil.addstr(self.x,self.y+2," DELETE MID      ")
                        contents = contents[:cursorpos-1] + contents[cursorpos:]
                        cursorpos -= 1
                elif (ttype==1) and (tkey==32): # space pressed
                        contents = contents[:cursorpos] + " " + contents[cursorpos:]
                        cursorpos += 1
                        #self.tbutil.addstr(self.x,self.y+2," ADD SPACE      ")
                else:
                    if c != None:
                        if len(contents) < max_width:
                            contents = contents[:cursorpos] + str(c) + contents[cursorpos:]
                            cursorpos += 1
                            contents = contents[:max_width]
                        #self.tbutil.addstr(self.x,self.y+2," ADD CHAR      ")

            # Move window view 
            if (cursorpos >= self.width-1):
                windowstart = cursorpos+1-self.width
            if (cursorpos < windowstart):
                windowstart = cursorpos
            if windowstart < 0:
                windowstart = 0

def text_validator(e,contents):
    (type, ch, key, mod, w, h, x, y ) = e
    if type==termbox.EVENT_KEY and key == termbox.KEY_ENTER:
        return(7)
    else:
        return(ch)

def integer_validator(e,contents):
    (type, ch, key, mod, w, h, x, y ) = e
    if (type==1 and (ch in "0123456789")):
        return(ch)
    elif type==termbox.EVENT_KEY and key == termbox.KEY_ENTER:
        return(7)
    else:
        return(ch)

def hex_validator(e,contents):
    (type, ch, key, mod, w, h, x, y ) = e
    if (ch != None):
        if (type==1 and (ch in "ABCDEFabcdef0123456789")):
            return(ch)
    elif type==termbox.EVENT_KEY and key == termbox.KEY_ENTER:
        return(7)
    else:
        return(ch)
        
def decimal_validator(e,contents):
    (type, ch, key, mod, w, h, x, y ) = e
    if type==termbox.EVENT_KEY and key == termbox.KEY_ENTER:
        return(7)
    else:
        return(ch)


