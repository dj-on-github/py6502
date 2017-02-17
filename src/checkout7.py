#!/usr/bin/env python
import string
import subprocess
import decimal
import curses
import curses.textpad
import tempfile
import sys

if sys.platform=='darwin':
    #import pymysql as mdb
    import MySQLdb as mdb
else:
    import MySQLdb as mdb
from curses.ascii import *
import datetime
import sanitize
if sys.platform == 'win32':
    import tempfile
    import win32api
    import win32print
    do_syslog=False
    do_newwin=False
    do_derwin=False
    do_pcprint=True
    do_manualwin=True
elif sys.platform == 'darwin':
    import syslog
    do_syslog=True
    do_newwin=False
    do_derwin=False
    do_pcprint=False
    do_manualwin=True
else:             #We are in Linux
    import syslog
    do_syslog=True
    do_newwin=True
    do_derwin=False
    do_pcprint=False
    do_manualwin=False

import os

# Main data structure is self.thelist.
# This is a list of items in the order they are displayed on the screen 
#  thelist contains a tuple barcode, row, qty, currentprice, dp
#  row is a line pulled from the database tables:
#      row  = (products.id, categories.category, suppliers.name, products.name, products.description, products.retail_price, products.stock_qty)

def print_file_wrapper(thefilename):
    if do_pcprint:
        #print "thefilename: "+thefilename
        thenormfilename = os.path.normpath(thefilename)
        win32api.ShellExecute (
            0,
            "print",
            thenormfilename,
            #
            # If this is None, the default printer will
            # be used anyway.
            #
            '/d:"%s"' % win32print.GetDefaultPrinter (),
            ".",
            0
            )
    else:
        subprocess.call(["lp",thefilename])
        
def print_wrapper(receipt_desanitized_text):
    if do_pcprint:
        tmpfilename = tempfile.mktemp(".txt")
        tmpfile = os.open(tmpfilename,os.O_WRONLY)
        tmpfile.write(receipt_desanitized_text)
        tmpfile.close()
        win32api.ShellExecute (
            0,
            "print",
            tmpfilename,
            #
            # If this is None, the default printer will
            # be used anyway.
            #
            '/d:"%s"' % win32print.GetDefaultPrinter (),
            ".",
            0
            )
    else:
        printer=os.popen('lp','w')
        printer.write(receipt_desanitized_text)
        printer.close()
import os

# TO DO:
# Add a transaction report feature over months and years.
# Have the finalize button identify cash or card.

class checkout_form():
    def __init__(self,host,user,password,database,pretend_mode):
        self.instruction_lines = []
        self.instruction_lines.append(" esc-quit, up/down-select, f-finalize, digits+enter-add, c-customer")
        self.instruction_lines.append(" a-adjust price, A-revert price, x-delete, D-discount %, R-restart, S-split")
        self.instruction_lines.append(" t-review transactions, n-show numbers, +/- to inc/dec qty, <-/-> discount")
        self.lines_of_instructions=len(self.instruction_lines) 
        self.customer_line=self.lines_of_instructions+2
        self.list_startline=self.lines_of_instructions+4
        self.current_customer_num = 0
        self.current_customer_name = ""
        self.go_up = 0
        self.he_hit_esc = 0
        self.he_hit_r = 0
        self.pretend_mode=1
        self.host = host
        self.user = user
        self.password = password
        self.database_name = database
        self.pretend_mode = pretend_mode

        self.dbout = 0 # set to 1 to turn on key char output
        self.valid_set = set()
        self.thelist=list()   
        self.discount = 0
        self.selection_line=0
        self.discount = 0
        self.next_itemno=1
        self.lastfinaltotal="0.0"

        self.maxx=79
        self.maxy=49
        self.open = 0

    def db_connect(self):
        self.con = mdb.connect(self.host, self.user, self.password, self.database_name)
        self.cur = self.con.cursor()
        self.open = 1

    def db_close(self):
        if self.open == 1:
            self.con.close()
            self.open = 0

    def parsefloat(self,thestring):
        success = 1
        failure = 0
        if len(thestring) == 0:
            return (failure,0.0)
        elif (thestring.isdigit()):
            return (success,float(thestring))
        else:
            dotcount = 0
            errorchar = 0
            thestring = thestring.strip()
            if (thestring == ""):
                return (failure,0.0)
            elif (thestring=="."):
                return (failure,0.0)
            else:
                for c in thestring:
                    if c=='.':
                        dotcount = dotcount+1
                    elif not(isdigit(c)):
                        errorchar = 1
                if ((dotcount > 1) or (errorchar == 1)):
                    return(failure,0.0)
                else:
                    return (success,float(thestring))

        # Should probably display the receipt or something here and
        # let it be re-printed or add a return/exchange.

    def undo(self,trid):
        #Delete the transaction, the transaction items and revert the stock quantities.
        query = "SELECT id,product,quantity FROM transactionitem where transaction_id=%s;" % str(trid)
        #self.stdscr.addstr(6,2,"A:"+query)
        self.db_connect()
        self.cur.execute(query)
        rows = self.cur.fetchall()
        i = 0
        for row in rows:
            i = i+3
            item_id = row[0]
            product_id = row[1]
            qty = row[2]
            query = "SELECT id,stock_qty FROM products WHERE id=%s;" % str(product_id)        
            #self.stdscr.addstr(6+i,2,"B:"+query)
            self.cur.execute(query)
            therow = self.cur.fetchone()
            id = therow[0]
            stock_qty = therow[1]
            new_stock = stock_qty + qty
            query = """UPDATE products SET stock_qty=%d WHERE id=%d;""" % (new_stock, product_id)
            #self.stdscr.addstr(6+i+1,2,"B:"+query)
            self.cur.execute(query)
            query = """DELETE FROM transactionitem WHERE transaction_id=%d;""" % (trid)
            #self.stdscr.addstr(6+i+2,2,"C:"+query)
            self.cur.execute(query)
        query="DELETE FROM transactions WHERE id=%d;" % trid
        #self.stdscr.addstr(6+i+3,2,"C:"+query)
        self.cur.execute(query)
        self.db_close()
        #c=self.stdscr.getch()

    def transaction_form(self):
        while True:
            #Work out if there are receipts in the receipt list
            self.db_connect()
            query = "select count(*) from receipts"
            self.cur.execute(query)
            row=self.cur.fetchone()
            self.db_close()
            total_receipts = row[0]

            if total_receipts==0:
                self.stdscr.addstr(4,20,"No receipts in database")
                self.stdscr.refresh()
                return(0)
            self.clearlist()
     
            if do_newwin:
                self.receipt_win = curses.newwin(self.maxy-20,self.maxx-3,self.maxy-22,1)
            elif do_derwin:
                self.receipt_win = self.stdscr.derwin(self.maxy-20,self.maxx-3,self.maxy-22,1)
            elif do_manualwin:
                receipt_win_xorigin = 1
                receipt_win_yorigin = self.maxy-22
                receipt_win_ncols = self.maxx-3
                receipt_win_nrows = self.maxy-20
                receipt_win_clearline = ' ' * receipt_win_ncols

                # Clear the window
                for lineno in xrange(receipt_win_nrows):
                    #self.stdscr.addstr(receipt_win_yorigin+lineno, receipt_win_xorigin, receipt_win_clearline)
                    #self.stdscr.addstr(receipt_win_yorigin+lineno, receipt_win_xorigin, "-----")
                    if receipt_win_yorigin+lineno < self.maxy:
                        self.stdscr.addstr(receipt_win_yorigin+lineno, receipt_win_xorigin, receipt_win_clearline)
                        #self.stdscr.addstr(lineno, receipt_win_xorigin, "-----")
     
            self.stdscr.addstr(self.lines_of_instructions+4,10, "Recipt Search Criteria, p to print, U to undo")
            self.stdscr.addstr(self.lines_of_instructions+5,1, "First Name:".rjust(16))
            self.stdscr.addstr(self.lines_of_instructions+6,1, "Second Name:".rjust(16))
            self.stdscr.addstr(self.lines_of_instructions+7,1, "Transaction ID:".rjust(16))
            self.stdscr.refresh()

            # The windows for the textboxes
            name1_win = self.stdscr.derwin(1,40,self.lines_of_instructions+5,18)
            name2_win = self.stdscr.derwin(1,40,self.lines_of_instructions+6,18)
            trid_win = self.stdscr.derwin(1,40,self.lines_of_instructions+7,18)
     
     
            # the textboxes
            name1_tb = curses.textpad.Textbox(name1_win)
            name2_tb = curses.textpad.Textbox(name2_win)
            trid_tb = curses.textpad.Textbox(trid_win)
     
            field_list = [name1_tb, name2_tb, trid_tb]
            current_field = 0
     
            name1=""
            name2=""
            trid=""
     
            really_finished=0
            start_again = 0 
            padviewwidth=self.maxx-2
            padviewheight=self.maxy-(self.lines_of_instructions)-35
            padposx=1
            padposy=self.lines_of_instructions+9
            firstpad=1
            firstgoround=2
     
            self.he_hit_esc = 0
            self.go_up = 0
            self.go_down = 0
            match = "xxx"
            lastmatch = "yyy"

            # Get the tables into memory so we can query them fast, locally
            query_t = """SELECT id, thedate, price, number_of_items, customer_id,date FROM transactions"""
            query_c = """SELECT id, first_name, second_name FROM customers"""
            query_r = """SELECT id, when_made, receipt, transaction_id FROM receipts"""
     
            # Actually limit it to 90 days for speed.
            query_t = """SELECT id, thedate, price, number_of_items, customer_id,date FROM transactions WHERE date >= curdate() - INTERVAL DAYOFWEEK(curdate())+90 DAY"""
            query_c = """SELECT id, first_name, second_name FROM customers"""
            query_r = """SELECT id, when_made, receipt, transaction_id FROM receipts WHERE when_made >= curdate() - INTERVAL DAYOFWEEK(curdate())+90 DAY"""

            self.db_connect()
            self.cur.execute(query_t)
            t_rows = self.cur.fetchall()
            xtransactions=dict()
            for row in t_rows:
                transaction = (int(row[0]), row[1], row[2], row[3], row[4], row[5])
                xtransactions[int(row[0])] = transaction
                #syslog.syslog("ADDING transactions[%d] : type %s" % (int(row[0]), str(type(transaction))))
            self.cur.execute(query_c)
            c_rows = self.cur.fetchall()
            customers=dict()
            for row in c_rows:
                #syslog.syslog("row[0]=%s" % str(row[0]))
                customers[int(row[0])] = (int(row[0]), row[1], row[2])
               
            # special case, receipts are indexed by the transaction_id 
            self.cur.execute(query_r)
            r_rows = self.cur.fetchall()
            receipts=dict()
            for row in r_rows:
                receipts[int(row[3])] = (int(row[0]), row[1], row[2], row[3])

            self.db_close()

            san=sanitize.sanitize()
            while (really_finished==0):
                self.db_connect()
                finishup = 0
                while(finishup==0):
                    if firstgoround==2:
                        firstgoround=1
                    else:
                        latchmatch=match
                        if current_field==0:
                            name1=field_list[current_field].edit(self.transaction_form_validator)
                        elif current_field==1:
                            name2=field_list[current_field].edit(self.transaction_form_validator)
                        elif current_field==2:
                            trid=field_list[current_field].edit(self.transaction_form_validator)
                        match = name1+","+name2+","+trid

                    if (self.he_hit_esc == 0):
                        if (firstgoround==1):
                            firstgoround=0
                        elif self.go_up==1:
                            if (current_field > 0):
                                current_field = current_field-1
                        else:
                            current_field = current_field+1

                        if (lastmatch != match):
                            unsorted_fullrows = []
                            if (trid != ""):
                                transaction_id = int(trid)
                                transaction = xtransactions[transaction_id]
                                customer_id = int(transaction[4])
                                if customer_id != 0:
                                    customer = customers[customer_id]
                                else:
                                    customer = (0, "", "")
                                receipt = receipts[transaction_id]
                                thetuple = transaction+customer+receipt
                                unsorted_fullrows.append(thetuple)
                            elif (name1 != "") or (name2 != ""):
                                for transaction_id in xtransactions:
                                    transaction = xtransactions[transaction_id]
                                    customer_id = int(transaction[4])
                                    if (customer_id != 0):
                                        customer = customers[customer_id]
                                        first_name = customer[1].lower().strip()
                                        second_name = customer[2].lower().strip()
                                        name1s=name1.lower().strip()
                                        name2s=name2.lower().strip()
                                        if name1s in first_name:
                                            fnm = 1
                                        else:
                                            fnm = 0
                                        if name2s in second_name:
                                            snm = 1
                                        else:
                                            snm = 0
                                        if ((name1 == "") or (fnm == 1)) and ((name2 == "") or (snm == 1)):
                                            if (transaction_id in receipts):
                                                receipt = receipts[transaction_id]
                                            else:
                                                receipt = (transaction_id, "x", " No Receipt in Database", transaction_id)
                                            thetuple = transaction+customer+receipt
                                            unsorted_fullrows.append(thetuple)
                            else: #Just show everything
                                #syslog.syslog("C"+str(type(xtransactions))) 
                                #syslog.syslog("D"+str(type(xtransactions[1000])))
                                #xxx = len(xtransactions)
                                #syslog.syslog("E %d" % xxx)
                                #for key,(theid,thedate,price,number_of_items,customer_id) in xtransactions:
                                for transaction_id in xtransactions:
                                    transaction = xtransactions[transaction_id]
                                    customer_id = transaction[4]
                                    if (customer_id != 0):
                                        customer = customers[customer_id]
                                        first_name = customer[1]
                                        second_name = customer[2]
                                    else:
                                        customer = (0, "", "")

                                    if (transaction_id in receipts):
                                        receipt = receipts[transaction_id]
                                    else:
                                        receipt = (transaction_id, "x", " No Receipt in Database", transaction_id)
                                    thetuple = transaction+customer+receipt
                                    unsorted_fullrows.append(thetuple)

                        #Fill out the pad
                        if 'pad' in vars() or 'pad' in globals():
                            pass
                        else:
                            #if firstpad==1:
                            pad = curses.newpad(max(len(unsorted_fullrows),padviewheight),padviewwidth)
                            firstpad=0 

                        #if (len(rows) > 29):
                        #    self.stdscr.addstr(14,17,"Too Many Matches to Display")
                        #    if (current_field > 2):
                        #        current_field = 2 
                        #    self.stdscr.refresh()
                        if (len(unsorted_fullrows)==0):
                            self.stdscr.addstr(14,17," No Records Match          ")
                            if (current_field > 2):
                                current_field = 2 
                            self.stdscr.refresh()
                        else:
                            #self.stdscr.addstr(14,17,"                           ")
                            #self.stdscr.refresh()
                            c=","
                            #y = self.lines_of_instructions+10
                            y = 0
                            # Display the List of transactions
                            #for i in xrange(self.lines_of_instructions+9,self.maxy-4):
                            #    self.stdscr.hline(i,1," ",self.maxx-3)
                            rows = sorted(unsorted_fullrows, key= lambda row: -int(row[0]))
                            for row in rows:
                                receipt_string = str(row[0])
                                receipt_string = receipt_string.ljust(5)
                                receipt_string = receipt_string+str(row[1])
                                receipt_string = receipt_string+c+str(row[3])
                                receipt_string = receipt_string+c+str(row[5])
                                receipt_string = receipt_string.ljust(35)
                                receipt_string = receipt_string+" "+str(row[7])
                                receipt_string = receipt_string+" "+str(row[8])
                                #if (str(row[6])==""):
                                #    receipt_string=receipt_string+"[no phone number]"
                                #receipt_string = receipt_string+c+san.desanitize(row[2])
                                if (len(receipt_string) > (self.maxx-2)):
                                    receipt_string = receipt_string[0:(self.maxx-2)]
                                #self.stdscr.addstr(y,1,receipt_string)
                                #syslog.syslog("RECEIPT_STRINGi:"+receipt_string)
                                pad.addstr(y,0,receipt_string)
                                y=y+1
                            if (y<padviewheight):
                                numbertopad = 1+padviewheight-y
                                for i in xrange(numbertopad):
                                    pad.hline(y,0," ",padviewwidth)
                                    y=y+1
                            self.stdscr.refresh()
                            pad.refresh(0,0,padposy,padposx,padposy+padviewheight,padposx+padviewwidth)
                            if (current_field > 2): # There must be customers displayed below
                                finishup=1
                                current_field=0

                                 
                    else:  # else he_hit_esc == 1
                        finishup = 1
                        really_finished = 1
                        start_again = 0
                        del pad

                # We have finished searching. Now let the user select from the list of transactions 
                # or quit if there were no transactions found
                self.db_close()
                san = sanitize.sanitize() 
                if (len(rows)==0) or (self.he_hit_esc == 1) or (really_finished == 1):
                    self.current_receipt_num = 0
                    self.current_receipt_date = ""
                    return(0)
                else:
                    num_lines = len(rows)
                    current_selection = 1
                    endselection = 0
                    cursorpos=0
                    while (endselection==0):
                        startline = self.lines_of_instructions+10
                        y = 1
                        receipt_desanitized_text=""
                        for row in rows:
                            # query_t = """SELECT id, thedate, price, number_of_items, customer_id FROM transactions"""
                            # query_c = """SELECT id, first_name, second_name FROM customers"""
                            # query_r = """SELECT id, when_made, receipt, transaction_id FROM receipts"""
                            c = ","
                            receipt_string = str(row[0])
                            receipt_string = receipt_string.ljust(5)
                            receipt_string = receipt_string+str(row[1])
                            receipt_string = receipt_string+c+str(row[3])
                            receipt_string = receipt_string+c+str(row[5])
                            receipt_string = receipt_string.ljust(35)
                            receipt_string = receipt_string+" "+str(row[7])
                            receipt_string = receipt_string+" "+str(row[8])

                            # query_t = """SELECT id, thedate, price, number_of_items, customer_id FROM transactions"""
                            # query_c = """SELECT id, first_name, second_name FROM customers"""
                            # query_r = """SELECT id, when_made, receipt, transaction_id FROM receipts"""
                            if (len(receipt_string) > (padviewwidth)):
                                receipt_string=receipt_string[:padviewwidth]
                            #self.stdscr.hline(startline-1+y,1," ",self.maxx-3)
                            pad.hline(y-1,0," ",self.maxx-3)
                            if (y == current_selection):
                                selected_trid = row[0]
                                pad.addstr(y-1,0,receipt_string,curses.A_REVERSE)
                                if do_newwin:
                                    self.receipt_win.erase()
                                elif do_derwin:
                                    self.receipt_win.erase()
                                elif do_manualwin:
                                    # Clear the window
                                    for lineno in xrange(receipt_win_nrows):
                                        #self.stdscr.addstr(receipt_win_yorigin+lineno, receipt_win_xorigin, receipt_win_clearline)
                                        if receipt_win_yorigin+lineno < self.maxy :
                                            self.stdscr.addstr(receipt_win_yorigin+lineno, receipt_win_xorigin, receipt_win_clearline)
                                receipt_desanitized_text=str(san.desanitize(str(row[11])))
                                if do_newwin:
                                    self.receipt_win.addstr(0,0,receipt_desanitized_text)
                                elif do_derwin:
                                    self.receipt_win.addstr(0,0,receipt_desanitized_text)
                                elif do_manualwin:
                                    receipt_lines=receipt_desanitized_text.split("\n")
                                    for lineno in xrange(len(receipt_lines)):
                                        if receipt_win_yorigin+lineno < self.maxy:
                                            self.stdscr.addstr(receipt_win_yorigin+lineno, receipt_win_xorigin, receipt_lines[lineno])
                                    #self.stdscr.addstr(receipt_win_yorigin+lineno+1, receipt_win_xorigin, "END OF RECEIPT")
                                    
                                #self.receipt_win.addstr(0,0,row[2])
                            else:
                                pad.addstr(y-1,0,receipt_string,curses.A_NORMAL)
                            y=y+1
                        self.stdscr.refresh()
                        if do_newwin:
                            self.receipt_win.refresh()
                        elif do_derwin:
                            self.receipt_win.refresh()
                        pad.refresh(cursorpos,0,padposy,padposx,padposy+padviewheight,padposx+padviewwidth)
                        c = self.stdscr.getch()
                        start_again=0
                        if (c == curses.KEY_UP):
                            if current_selection == 1:
                                c=","
                                current_field = 2
                                current_selection = 0
                                endselection = 1
                                row = rows[0]                   # take highlight off first receipt in list
                                receipt_string = str(row[0])   # when exiting back to the editing fields
                                receipt_string = receipt_string.ljust(5)
                                receipt_string = receipt_string+str(row[1])
                                receipt_string = receipt_string+c+str(row[3])
                                receipt_string = receipt_string+c+str(row[5])
                                receipt_string = receipt_string.ljust(35)
                                receipt_string = receipt_string+" "+str(row[7])
                                receipt_string = receipt_string+" "+str(row[8])
                                #receipt_string = receipt_string+c+str(row[6])
                                #receipt_string = receipt_string+c+str(row[7])
                                #if (str(row[6])==""):
                                #    receipt_string=receipt_string+"[no phone number]"
                                #receipt_string = receipt_string+c+san.desanitize(row[2])
                                if (len(receipt_string) > (padviewwidth)):
                                    receipt_string = receipt_string[:padviewwidth]
                                pad.addstr(0,0,receipt_string,curses.A_NORMAL)
                                pad.refresh(0,0,padposy,padposx,padposy+padviewheight,padposx+padviewwidth)
                                #self.stdscr.addstr(startline,1,receipt_string,curses.A_NORMAL)
                                self.stdscr.refresh()
                            elif current_selection > 1:
                                current_selection = current_selection -1
                                if (current_selection==(cursorpos)):
                                    cursorpos=cursorpos-1
                        elif (c == curses.KEY_DOWN):
                            if current_selection < num_lines:
                                current_selection = current_selection +1
                                if (current_selection==(cursorpos+padviewheight)+2):
                                    cursorpos=cursorpos+1
                        #elif (c == ord('x'):
                        #    self.
                        elif ((c==ord('p')) or (c==ord('P'))):
                            if receipt_desanitized_text=="":
                                pass
                            else:
                                print_wrapper(receipt_desanitized_text)
                                #printer=os.popen('lp','w')
                                #printer.write(receipt_desanitized_text)
                                #printer.close()
                        elif (c==ord('U')):
                            self.stdscr.addstr(5,2,("Undoing Transaction %s [Press Y if you mean it]" % (str(selected_trid))),curses.A_REVERSE)
                            self.stdscr.refresh()
                            c = self.stdscr.getch()
                            if c==ord('Y'):
                                self.undo(selected_trid)
                                endselection = 1
                                really_finished = 1
                                start_again = 0
                            else:
                                endselection = 1
                                really_finished = 1
                                start_again=0
                            maxl = 50
                            if maxl+2 > self.maxx:
                                maxl = self.maxx -2
                            self.stdscr.addstr(5,2,(" "*maxl),curses.A_NORMAL)
                            self.stdscr.refresh()
                                 
                            # Delete a transaction here
                            # Back out the stock changes also
                            #
                        elif ((c == curses.KEY_ENTER) or (c == 13) or (c == 10)):
                            self.current_receipt_num = rows[current_selection-1][0]
                            self.current_receipt_date = rows[current_selection-1][1]
                            endselection = 1
                            really_finished = 1
                        elif (c == 27):    #ESC
                            self.current_receipt_num = 0
                            self.current_receipt_date = ""
                            endselection = 1
                            really_finished = 1
                            del pad
                        #self.stdscr.addstr(self.maxy-10,1,"current_selection=%d      " % current_selection,curses.A_REVERSE)
                        #self.stdscr.addstr(self.maxy-9,1, "current_field    =%d      " % current_field,curses.A_REVERSE)
            if (start_again == 0):
                break
            else:
                del pad
                self.stdscr.refresh()
 
    # Every time a key is pressed in the search form, this gets called

    # Trap TAB and return ctrl G to get the edit to exit
    # for tab navigation
    def transaction_form_validator(self,c):
        self.he_hit_esc = 0

        # Print the pressed character code in pretend mode
        # for analysis [urposes
        #if self.pretend_mode==1:
        #    self.stdscr.addstr(47,10,str(c)+"   ")
        #    self.stdscr.refresh()
        # Captues escape character and return 7 to exit the field edit form
        if (c==27):
            self.he_hit_esc = 1
            return(7)
        # Capture the down key and return 7 to exit the field edit form
        elif ((c==9) or (c==curses.KEY_DOWN)):
            self.go_up = 0
            return(7)
        # Capture the up key and return 7 to exit the field edit form
        elif (c==curses.KEY_UP):
            self.go_up =1
            return(7)
        # Otherwize, accept the character as typed.
        else:
            return(c)

    def review_numbers(self):
        lines = []
        outputs = []
        
        indexes = "ABCDEFGHIJKLMNOPQRSTUVWXYZ" 
        lines.append((1325, "ArtByEve")) 
        lines.append((1833, "Buttons - random")) 
        lines.append((1832, "Deidre MacImmie/Spinners Candy")) 
        lines.append((1834, "Donegal Tweed")) 
        lines.append((1847, "Jane Thompson")) 
        lines.append((1850, "Lynn Venghaus")) 
        lines.append((1254, "Nuts About Berries")) 
        lines.append((1808, "Reflective Yarn")) 
        lines.append((1858, "Teresa Ruch")) 
        lines.append((1839, "Thoroughly Thwacked")) 
        lines.append((1831, "Yarn Crawl Bag")) 
        lines.append(( 484, "Buy Voucher")) 
        lines.append(( 485, "Redeem Voucher")) 
        lines.append((1265, "Drum Carder (1 hour)"))
        lines.append((1000, "maxx:"+str(self.maxx)+" maxy:"+str(self.maxy)))

        y = self.lines_of_instructions+4
        x = 3

        # Max line length
        maxlen = 0
        for line in lines:
            if (line[0]!=0):
                if len(line[1]) > maxlen:
                    maxlen = len(line[1])

        cap = ""
        for i in xrange(maxlen+17):
            cap = cap + "_"

        filler = "|"
        for i in xrange(maxlen+17-2):
            filler = filler + " "
        filler = filler + "|"

        outputs.append(cap)
        outputs.append(filler)

        selections = dict()

        dataline = ""
        i=0
        for line in lines:
            if (line[0]!=0):
                dataline = "| "+indexes[i]+" - "+line[1].ljust(maxlen)+" - "+str(line[0]).rjust(6)+" |"
                outputs.append(dataline)
                selections[indexes[i]] = line[0]
                i+=1

        outputs.append(filler)
        outputs.append(cap)

        for line in outputs:
            self.stdscr.addstr(y,x, line)
            y = y + 1

        self.stdscr.refresh()
        c = self.stdscr.getch()

        if (c < 256):
            if (chr(c) in selections):
                return (selections[chr(c)])
        return 0
        
    def customer_form(self):
        #Work out if there are customers in the customer list
        self.db_connect()
        query = "select * from customers"
        self.cur.execute(query)
        rows = self.cur.fetchall()
        if len(rows) == 0:
            self.stdscr.addstr(4,20,"No customers in customer list")
            self.stdscr.refresh()
            self.db_close()
            return(0)
        self.db_close()
        total_customers=len(rows) 
        self.clearlist()

        self.stdscr.addstr(self.lines_of_instructions+4,10, "Customer Search Criteria") 
        self.stdscr.addstr(self.lines_of_instructions+5,1, "First Name:".rjust(15)) 
        self.stdscr.addstr(self.lines_of_instructions+6,1, "Second Name:".rjust(15)) 
        self.stdscr.addstr(self.lines_of_instructions+7,1, "Address1:".rjust(15)) 
        self.stdscr.addstr(self.lines_of_instructions+8,1, "Address2:".rjust(15))
        self.stdscr.addstr(self.lines_of_instructions+9,1, "Phone Number:".rjust(15)) 
        self.stdscr.addstr(self.lines_of_instructions+10,1,"email:".rjust(15))
        self.stdscr.refresh()

        # The windows for the textboxes
        name1_win = self.stdscr.derwin(1,40,self.lines_of_instructions+5,17)
        name2_win = self.stdscr.derwin(1,40,self.lines_of_instructions+6,17)
        addr1_win = self.stdscr.derwin(1,40,self.lines_of_instructions+7,17)
        addr2_win = self.stdscr.derwin(1,40,self.lines_of_instructions+8,17)
        phone_win = self.stdscr.derwin(1,40,self.lines_of_instructions+9,17)
        email_win = self.stdscr.derwin(1,40,self.lines_of_instructions+10,17)

        # the textboxes
        name1_tb = curses.textpad.Textbox(name1_win)
        name2_tb = curses.textpad.Textbox(name2_win)
        addr1_tb = curses.textpad.Textbox(addr1_win)
        addr2_tb = curses.textpad.Textbox(addr2_win)
        phone_tb = curses.textpad.Textbox(phone_win)
        email_tb = curses.textpad.Textbox(email_win)

        field_list = [name1_tb, name2_tb, addr1_tb, addr2_tb, phone_tb, email_tb]
        current_field = 0

        name1=""
        name2=""
        addr1=""
        addr2=""
        phone=""
        email=""

        really_finished=0

        padviewwidth=self.maxx-2
        padviewheight=self.maxy-(self.lines_of_instructions)-18
        padposx=1
        padposy=self.lines_of_instructions+12
        firstpad=1
        firstgoround=2

        self.he_hit_esc = 0
        self.go_up = 0
        self.go_down = 0
        while (really_finished==0):
            self.db_connect()
            finishup = 0
            while(finishup==0):
                if firstgoround==2:
                    firstgoround=1
                else:
                    if current_field==0:
                        name1=field_list[current_field].edit(self.customer_form_validator)
                    elif current_field==1:
                        name2=field_list[current_field].edit(self.customer_form_validator)
                    elif current_field==2:
                        addr1=field_list[current_field].edit(self.customer_form_validator)
                    elif current_field==3:
                        addr2=field_list[current_field].edit(self.customer_form_validator)
                    elif current_field==4:
                        phone=field_list[current_field].edit(self.customer_form_validator)
                    elif current_field==5:
                        email=field_list[current_field].edit(self.customer_form_validator)

                if (self.he_hit_esc == 0):
                    if (firstgoround==1):
                        firstgoround=0
                    elif (self.go_up==1):
                        if (current_field > 0):
                            current_field = current_field-1
                    else:
                        current_field = current_field+1

                    wherestring = ""
                    addand = 0
                    if (name2 != ""):
                        wherestring = """(second_name like '%%%s%%') """ % name2.strip()
                        addand=1
                    if (name1 != ""):
                        if (addand==1):
                            wherestring=wherestring+" and "
                        wherestring= wherestring+ """(first_name like '%%%s%%')""" % name1.strip()
                        addand=1
                    if (addr1 != ""):
                        if (addand==1):
                            wherestring=wherestring+" and "
                        wherestring= wherestring+ """(addr1 like '%%%s%%')""" % addr1.strip()
                        addand=1
                    if (addr2 != ""):
                        if (addand==1):
                            wherestring=wherestring+" and "
                        wherestring= wherestring+ """(addr2 like '%%%s%%')""" % addr2.strip()
                        addand=1
                    if (phone != ""):
                        if (addand==1):
                            wherestring=wherestring+" and "
                        wherestring= wherestring+ """(phone like '%%%s%%')""" % phone.strip()
                        addand=1
                    if (email != ""):
                        if (addand==1):
                            wherestring=wherestring+" and "
                        wherestring= wherestring+ """(email like '%%%s%%')""" % email.strip()

                    if (wherestring == ""):
                        query = """select * from customers"""
                    else:
                        query = """select * from customers where %s""" % wherestring
                    self.cur.execute(query)
                    rows = self.cur.fetchall()

                    #stdscr.hline(16,1," ",78)
                    #stdscr.addstr(16,1,query)
                    #stdscr.refresh()

                    #self.stdscr.addstr(13,16,"query:%s" % query)

                    #Fill out the pad
                    if firstpad==1:
                        pad = curses.newpad(max(total_customers,padviewheight),padviewwidth)
                        firstpad=0 

                    #if (len(rows) > 29):
                    #    self.stdscr.addstr(14,17,"Too Many Matches to Display:%d" % len(rows))
                    #    if (current_field > 5):
                    #        current_field = 5
                    #    self.stdscr.refresh()
                    if (len(rows)==0):
                        pad.clear()
                        pad.addstr(2,2," No Records Match          ")
                        if (current_field > 5):
                            current_field = 5
                        self.stdscr.refresh()
                        pad.refresh(0,0,padposy, padposx,padposy+padviewheight,padposx+padviewwidth)
                    else:
                        pad.clear()
                        #self.stdscr.addstr(14,17,"                           ")
                        #self.stdscr.refresh()
                        c=","
                        y = 0
                        # Display the List of customers
                        #for i in xrange(18,40):
                        #    self.stdscr.hline(i,1," ",self.maxx-3)
                        for row in rows:
                            customer_string = str(row[0])
                            for i in xrange(1,10):
                                customer_string = customer_string+c+row[i]
                            if (len(customer_string) > (self.maxx-2)):
                                customer_string = customer_string[:(self.maxx-3)]
                            #self.stdscr.addstr(y,1,customer_string)
                            pad.addstr(y,0,customer_string)
                            y=y+1
                        #self.stdscr.refresh()
                        self.stdscr.refresh()
                        pad.refresh(0,0,padposy,padposx,padposy+padviewheight,padposx+padviewwidth)
                        if (current_field > 5): # There must be customers displayed below
                            finishup=1
                            current_field=0

                             
                else:  # else he_hit_esc == 1
                    finishup = 1
                    really_finished = 1
                    del pad

            # We have finished searching. Now let the user select from the list of customers
            # or quit if there where no customers found
            self.db_close()
            if (len(rows)==0) or (self.he_hit_esc == 1) or (really_finished == 1):
                self.current_customer_num = 0
                self.current_customer_name = ""
                return(0)
            else:
                num_lines = len(rows)
                current_selection = 1
                endselection = 0
                cursorpos=0
                while (endselection==0):
                    y = 1
                    for row in rows:
                        customer_string = str(row[0])
                        for i in xrange(1,10):
                            customer_string = customer_string+","+str(row[i])
                        if (len(customer_string) > padviewwidth):
                            customer_string=customer_string[:padviewwidth]
                        pad.hline(y-1,0," ",self.maxx-3)
                        if (y == current_selection):
                            pad.addstr(y-1,0,customer_string,curses.A_REVERSE)
                        else:
                            pad.addstr(y-1,0,customer_string,curses.A_NORMAL)
                        y=y+1

                    #self.stdscr.addstr(3,40,"CS:%d  CP:%s " % (current_selection,cursorpos))
                    self.stdscr.refresh()
                    #pad.refresh(current_selection-1,0,padposy,padposx,padposy+padviewheight,padposx+padviewwidth)
                    pad.refresh(cursorpos,0,padposy,padposx,padposy+padviewheight,padposx+padviewwidth)
                    c = self.stdscr.getch()
                    if (c == curses.KEY_UP):
                        if current_selection == 1:
                            current_field = 5
                            current_selection = 0
                            endselection = 1
                            row = rows[0]                   # take highlight of first customer in list
                            customer_string = str(row[0])   # when exiting back to the editing fields
                            for i in xrange(1,10):
                                customer_string = customer_string+","+str(row[i])
                            pad.addstr(0,0,customer_string,curses.A_NORMAL)
                            pad.refresh(0,0,padposy,padposx,padposy+padviewheight,padposx+padviewwidth)
                            self.stdscr.refresh()
                        elif current_selection > 1:
                            current_selection = current_selection -1
                            if (current_selection==(cursorpos)):
                                cursorpos=cursorpos-1
                    elif (c == curses.KEY_DOWN):
                        if current_selection < num_lines:
                            current_selection = current_selection +1
                            if (current_selection==(cursorpos+padviewheight)+2):
                                cursorpos = cursorpos+1
                    #elif (c == 10):
                    elif ((c == curses.KEY_ENTER) or (c == 13) or (c == 10)):
                        self.current_customer_num = rows[current_selection-1][0]
                        self.current_customer_name = rows[current_selection-1][1]+" "+rows[current_selection-1][2]
                        endselection = 1
                        really_finished = 1
                    elif (c == 27):    #ESC
                        self.current_customer_num = 0
                        self.current_customer_name = ""
                        endselection = 1
                        really_finished = 1
                        del pad

    # Every time a key is pressed in the search form, this gets called

    # Trap TAB and return ctrl G to get the edit to exit
    # for tab navigation
    def customer_form_validator(self,c):
        self.he_hit_esc = 0
        self.go_up =0
        self.go_down =0

        # Print the pressed character code in pretend mode
        # for analysis [urposes
        #if self.pretend_mode==1:
        #    self.stdscr.addstr(47,10,str(c)+"   ")
        #    self.stdscr.refresh()
        # Captues escape character and return 7 to exit the field edit form
        if (c==27):
            self.he_hit_esc = 1
            return(7)
        # Capture the down key and return 7 to exit the field edit form 
        elif ((c==9) or (c==curses.KEY_DOWN)):
            self.go_down = 1
            return(7)
        # Capture the up key and return 7 to exit the field edit form
        elif (c==curses.KEY_UP):
            self.go_up =1
            return(7)
        # Otherwize, accept the character as typed.
        else:
            return(c)

    # If we change between pretend and real mode, we must
    # also swap the database 
    def change_pretend_mode(self):
        if (self.pretend_mode==1):
            self.pretend_mode=0
            self.database_name='blacksheep'
        else:
            self.pretend_mode=1
            self.database_name='test_blacksheep'

                # Change to correct database
        #self.con.close()

        self.thelist=list()
        self.discount=0
        self.next_itemno=1
        self.selection_line=0
        self.current_customer_num = 0
        self.current_customer_name = ""
        self.valid_set=set()

        #self.con = mdb.connect('blacksheepatorenco.com', 'blacksheep', 'bahbahbah', self.database_name)
        #self.cur = self.con.cursor()

        self.get_valid_productid_set()
        self.redraw_all()
        #self.drawtitle()
        #self.drawdiscount()
        #self.drawlist()

    def redraw_all(self):
        self.stdscr.clear()
        self.drawborder()
        self.drawtitle()
        self.drawlist()

    def drawdiscount(self):
        if (self.discount != 0):
            self.stdscr.addstr(0,self.maxx-17,"Discount: %s%%" % str(self.discount))
            self.stdscr.refresh()
        else:
            #self.stdscr.addstr(0,64,"               ")
            self.stdscr.hline(0,self.maxx-17,curses.ACS_HLINE,15)
            self.stdscr.refresh()

    def clearlist(self):
        self.stdscr.move(6,1)
        self.stdscr.refresh()
        for y in xrange(self.lines_of_instructions+4,self.maxy-4):            # clear the main panel
            self.stdscr.hline(y,1," ",self.maxx-2)
            self.stdscr.refresh()
        self.stdscr.addstr(self.maxy-2,self.maxx-9,"       ")   # Clear the total
        self.stdscr.refresh()

    def drawborder(self):
        self.stdscr.border()
        self.stdscr.hline(self.maxy-3,1,curses.ACS_HLINE,self.maxx-3)
        self.stdscr.refresh()

    def drawtitle(self):
        if (self.pretend_mode==1):
            self.stdscr.border()
            self.stdscr.addstr(0,17,("[pretend mode][Checkout Screen v7.0][last price $%s]" % (self.lastfinaltotal)))
        else:
            self.stdscr.border()
            #self.stdscr.addstr(0,int(self.maxx/2)-11,("[Checkout Screen V3.0][last price $%s]" % (self.lastfinaltotal)))
            self.stdscr.addstr(0,17,("[Checkout V7.0][last price $%s]" % (self.lastfinaltotal)))
        y=1
        for line in self.instruction_lines:
            self.stdscr.addstr(y,1,line)
            y=y+1
        #self.stdscr.addstr(1,1," esc-quit, up/down-select, f-finalize, digits+enter-add, c-customer")
        #self.stdscr.addstr(2,1," a-adjust price, A-revert price, x-delete, D-discount %, R-restart")
        #self.stdscr.addstr(3,1," C-add a customer, M-big scary menu, ETC")
        self.stdscr.hline(self.lines_of_instructions+1,1,curses.ACS_HLINE,self.maxx-3) 
        if (self.current_customer_name != ""):
            customer_string = str(self.current_customer_num)+" "+self.current_customer_name
            customer_string = customer_string.ljust(68)
            self.stdscr.addstr(self.lines_of_instructions+2,1," Customer: %s" % customer_string)
        else:
            self.stdscr.addstr(self.lines_of_instructions+2,1," No Customer                                                          ")
        self.stdscr.hline(self.lines_of_instructions+3,1,curses.ACS_HLINE,self.maxx-3) 
        self.stdscr.refresh()
        self.drawdiscount()

    def checkout(self):
        # Make a list sorted by itemno. More handy than a dictionary
        self.db_connect()
        total = 0
        alist = []

        #for listkey in self.thelist:
        #    stuff = self.thelist[listkey]
        #    alist.append(stuff)
        #sortedlist = sorted(alist, key= lambda item: item[0])
        
        #compute price
        for item in self.thelist:
            barcode, row, qty, currentprice,dp = item
            #retail_price = row[5]
            if (row[0]!=485):       #Don't include a redeemed voucher in the total 
                total = total+(qty*float(currentprice))

        #See if there was a redeemed voucher
        voucher_value=0.0
        for item in self.thelist:
            barcode, row, qty, currentprice,dp = item
            if (row[0]==485): 
                voucher_value = float(currentprice)

        totalstring = "%5.2f" % (total-voucher_value)

        # find date and time
        now = datetime.datetime.now()
        datestring = now.strftime("%m-%d-%Y %H:%M")
        mysqldatestring = now.strftime("%Y-%m-%d %H:%M:00")

        #compute number of items (not including duplicates)
        number_of_lines = len(self.thelist)

        #y=30
        #Subtract items in transaction from product quantities.
        for item in self.thelist:
            #y=y+1
            barcode, row, qty, currentprice,dp = item
            product_id = row[0]
            retail_price = row[5]
            stock_level = row[6]
            if (product_id !=485):
                new_stock = stock_level - qty
                query = """update products set stock_qty=%d where id=%d""" % (new_stock, product_id)
                #stdscr.addstr(y,0,query)
                #stdscr.refresh()
                #DO THE UPDATE HERE!
                self.cur.execute(query)

        #format string of [product_id,qty,currentprice]
        firstone = 1
        sale_string="("
        for item in self.thelist:
            barcode, row, qty, currentprice,dp = item
            product_id = row[0]
            if (firstone != 1):
                sale_string = sale_string+","
            firstone = 0
            sale_string = sale_string + "(" + str(product_id) + "," + str(qty) + "," + str(currentprice) + ")"
        if (len(self.thelist) == 1):
            sale_string = sale_string + ",)"
        else:
            sale_string = sale_string + ")"

        if (self.discount == 0):
            finaltotalstring = totalstring
            voucher_string = "%5.2f" % voucher_value
        else:
            discounttotal = float(total)*(float(self.discount)/100.0)
            discounttotalstring = "%5.2f" % discounttotal
            voucher_string = "%5.2f" % voucher_value
            finaltotal = float(total) - discounttotal - voucher_value
            finaltotalstring = "%5.2f" % finaltotal

        #Add entry to transaction table - transaction_id, date, time, price, #items, item_string
        query = """INSERT INTO transactions (thedate, price, number_of_items, item_string, customer_id,date) values ('%s', %s, %s, '%s', '%s','%s')""" % (datestring, finaltotalstring, str(number_of_lines), sale_string, self.current_customer_num,mysqldatestring)
        self.cur.execute(query)
        #stdscr.addstr(47,0,query)
        #stdscr.refresh()
        #Retreive the transaction ID back from database. It was assigned by the database.
        query = """SELECT id FROM transactions where ((thedate='%s') and (price=%s) and (number_of_items=%s) and (item_string='%s') and (customer_id=%s))""" % (datestring, finaltotalstring, str(number_of_lines), sale_string, self.current_customer_num)
        self.cur.execute(query)
        row=self.cur.fetchone()
        transaction_id = row[0]
       
        # Write the items to the transaction item table
        n = 0
        m = len(self.thelist)
        for item in self.thelist:
            barcode, row, qty, currentprice,dp = item
            n = n+1
            product_id = row[0]
            query = "INSERT INTO transactionitem (transaction_id, sell_price, quantity, product, itemnum, ofhowmany, discount, per_item_discount) VALUES "
            query = query + "(%d, %0.2f, %d, %d, %d, %d, %d, %d) " % (transaction_id, currentprice, qty, product_id, n, m, self.discount, dp)
            self.cur.execute(query)
        
        # make filename for recipt
        if (self.pretend_mode==1):
            filename = "/var/blacksheep/pretend_receipts/pretend_receipt-"+now.strftime("%m-%d-%Y-%H-%M-%S")+".txt"
        else:
            filename = "/var/blacksheep/receipts/receipt-"+now.strftime("%m-%d-%Y-%H-%M-%S")+".txt"

        #Write formatted output to file
        f = open(filename,'w')
        thewidth=70
        receipt_string = ""
        receipt_string = receipt_string +('-------------------------------------------------------------------------\n')
        receipt_string = receipt_string +("Black Sheep at Orenco".center(thewidth)+"\n")
        receipt_string = receipt_string +("RECEIPT".center(thewidth)+"\n")
        receipt_string = receipt_string +(datestring.center(thewidth)+"\n")
        if (self.current_customer_name != ""):
            receipt_string = receipt_string +(self.current_customer_name.center(thewidth)+"\n")
        receipt_string = receipt_string +('-------------------------------------------------------------------------\n')
        purchased_giftvoucher_total = 0.0
        itemno = 0
        for item in self.thelist:
            itemno = itemno+1
            barcode, row, qty, currentprice,dp = item
            retail_price = row[5]
            astring = "%d:%s,%s,%s,%s,%s" % (itemno,row[0],row[1],row[2],row[3],row[4])
            if (row[0] != 485):
                # Chop long strings into multiple lines
                while (len(astring) > 55):
                    firststring = astring[:55]
                    astring = astring[55:]
                    astring = "  "+astring;
                    linetext = firststring.ljust(55)+'\n'
                    receipt_string = receipt_string +(linetext)
                else:
                    dpstring=""
                    if dp > 0:
                        dpstring = "-"+str(dp)+"%"
                    qtystring = "%d" % qty
                    pricestring = "%3.2f" % (qty*currentprice)
                    linetext = astring.ljust(55)+" "+dpstring.ljust(4)+" "+qtystring.ljust(3)+" $"+pricestring.rjust(7)+'\n'
                    receipt_string = receipt_string +(linetext)
        receipt_string = receipt_string +('-------------------------------------------------------------------------\n')
        if (self.discount == 0):
            if (voucher_value != 0.0):
                linetext = '                                         Redeemed Voucher :   -$ '+voucher_string.rjust(8)+'\n'
                receipt_string = receipt_string +(linetext)
            linetext = '                                                    Total :    $ '+totalstring.rjust(8)+'\n'
            receipt_string = receipt_string +(linetext)
            discounttotal = 0.0
            discounttotalstring="0.0"
        else:
            discounttotal = float(total)*(float(self.discount)/100.0)
            discounttotalstring = "%5.2f" % discounttotal
            finaltotal = float(total) - discounttotal - voucher_value
            finaltotalstring = "%5.2f" % finaltotal
            #linetext = '                                                    Total :    $ '+totalstring.rjust(8)+'\n'
            #receipt_string = receipt_string +(linetext)
            linetext = '                                                 Discount :    % '+str(self.discount).rjust(8)+'\n'
            receipt_string = receipt_string +(linetext)
            discounttotalstring = "%5.2f" % discounttotal
            linetext = '                                          Discount Amount :   -$ '+discounttotalstring.rjust(8)+'\n'
            receipt_string = receipt_string +(linetext)
            if (voucher_value != 0.0):
                linetext = '                                         Redeemed Voucher :   -$ '+voucher_string.rjust(8)+'\n'
                receipt_string = receipt_string +(linetext)
            linetext = '                                                    Total :    $ '+finaltotalstring.rjust(8)+'\n'
            receipt_string = receipt_string +(linetext)
        receipt_string = receipt_string +('-------------------------------------------------------------------------\n')
        receipt_string = receipt_string + ('transaction_id = %s\n' % transaction_id)
        f.write(receipt_string)
        f.close()

        #print it.
        done = 0
        while done==0:
            self.stdscr.addstr(self.lines_of_instructions+1,25," Receipt - Press p to print, n to save paper ")
            c=self.stdscr.getch()
            #self.stdscr.addstr(self.lines_of_instructions+5,25,"%d" % c)
            self.stdscr.refresh()
            if (c==ord('p')) or (c==ord('n')) or (c==ord('P')) or (c==ord('N')):
                done = 1
            
        if (c==ord('p')) or (c==ord('P')):
            try:
                print_file_wrapper(filename)
            except:
                self.stdscr.addstr(self.lines_of_instructions+2,25," filename failed "+str(filename))
            #subprocess.call(["lp",filename])
            
        self.stdscr.addstr(self.lines_of_instructions+1,25," Receipt - Press enter to return to main screen ")
        c=self.stdscr.getch()
        self.lastfinaltotal = finaltotalstring
        self.stdscr.hline(self.lines_of_instructions+1,1,"-",self.maxx-3)
        self.stdscr.refresh()

        #Add the transaction ID
        #f = open(filename,'a')
        #f.write('transaction_id = %s\n' % transaction_id)
        #f.close
        san = sanitize.sanitize() 

        query = """INSERT INTO receipts (receipt, transaction_id, discount_percent, discount_value, redeemed_voucher, purchased_voucher) VALUES ("%s", %d, %d, %0.2f, %0.2f, %0.2f);""" % (san.sanitize(receipt_string), transaction_id, self.discount, discounttotal, voucher_value, purchased_giftvoucher_total)
        
        #query = """insert into receipts (id, receipt) values (%s, '%s')""" % (transaction_id, san.sanitize(receipt_string))
        #syslog.syslog("CHECKOUT_FORM7:query=%s\n" % query)
        self.cur.execute(query)
        self.current_customer_num = 0
        self.current_customer_name = ""
        self.db_close()
 
    def drawlist(self):
        y = self.lines_of_instructions+4;
        voucher_y = 0
        total = 0.0
        voucher_total = 0.0
        alist = []
        avoucherlist = []
        vouchers = 0
        if (len(self.thelist) > 0):
            for item in self.thelist:
                barcode, oldrow,qty,currentprice,dp = item
                newrow = self.get_new_item(barcode)
                if (newrow[0] == 485):  # if it is a voucher keep it in a voucher list
                    stuff=(barcode, newrow, qty, currentprice,dp)
                    avoucherlist.append(stuff)
                else:                   # Else its a normal thing
                    stuff=(barcode, newrow, qty, currentprice,dp)
                    alist.append(stuff)
            #sortedlist = sorted(alist,key = lambda item: item[0])
            #sortedvoucherlist = sorted(avoucherlist,key = lambda item: item[0])
            sortedlist = alist
            sortedvoucherlist = avoucherlist
            
            itemno = 0
            for item in sortedlist:
                itemno +=1
                barcode, row, qty, currentprice,dp = item
                #retail_price = row[5]
                retail_price = currentprice
                astring = "%d:%s,%s,%s,%s,%s" % (itemno,row[0],row[1].strip(),row[2].strip(),row[3].strip(),row[4].strip())
                if (len(astring) > self.maxx-21):
                    astring = astring[0:self.maxx-21]
                qtystring = "%d" % qty
                pricestring = "%3.2f" % (qty*retail_price)
                if (self.selection_line == itemno):
                        self.stdscr.addstr(y,1,astring.ljust(self.maxx-22),curses.A_REVERSE)
                else:
                        self.stdscr.addstr(y,1,astring.ljust(self.maxx-22),curses.A_NORMAL)
                self.stdscr.addstr(y,self.maxx-22,"|")
                if dp > 0:
                    dpstring = "-"+str(dp)+"%"
                    self.stdscr.addstr(y,self.maxx-21,dpstring.rjust(4))
                self.stdscr.addstr(y,self.maxx-17,"|")
                self.stdscr.addstr(y,self.maxx-16,qtystring.rjust(4))
                self.stdscr.addstr(y,self.maxx-11,"| $")
                self.stdscr.addstr(y,self.maxx-8,pricestring.rjust(7))
                total = total+float(qty*retail_price)
                y = y+1

                totalstring = "%4.2f" % total

            voucher_total=0
            if (len(avoucherlist)>0):
                #then print the vouchers
                voucher_y = self.maxy-4-len(avoucherlist)
                self.stdscr.hline(voucher_y,1," ",self.maxx-3)
                itemno = 0
                for item in sortedvoucherlist:
                    itemno += 1
                    barcode, row, qty, currentprice,dp = item
                    #retail_price = row[5]
                    retail_price = currentprice
                    astring = "%d:%s,%s,%s,%s,%s" % (itemno,row[0],row[1],row[2],row[3],row[4])
                    if (len(astring) > self.maxx-17):
                        astring = astring[0:self.maxx-17]
                    qtystring = "1" 
                    pricestring = "%3.2f" % (retail_price)
                    if (self.selection_line == len(sortedlist)+1):
                            self.stdscr.addstr(voucher_y,1,astring.ljust(self.maxx-14),curses.A_REVERSE)
                    else:
                            self.stdscr.addstr(voucher_y,1,astring.ljust(self.maxx-14),curses.A_NORMAL)
                    #self.stdscr.addstr(voucher_y,self.maxx-17,"|")
                    #self.stdscr.addstr(y,self.maxx-16,qtystring.rjust(4))
                    self.stdscr.addstr(voucher_y,self.maxx-11,"|-$")
                    self.stdscr.addstr(voucher_y,self.maxx-8,pricestring.rjust(7))
                    voucher_total = voucher_total+float(retail_price)
                    voucher_y = voucher_y+1
                    voucher_totalstring = "-%4.2f" % voucher_total
                self.stdscr.hline(self.maxy-5-len(avoucherlist),1,curses.ACS_HLINE,self.maxx-3)
                #self.stdscr.addstr(self.maxy-4,self.maxx-25,"Voucher Total: $")
                #self.stdscr.addstr(self.maxy-4,self.maxx-8,voucher_totalstring.rjust(7))
            non_discount_totalstring = "%4.2f" % (total - voucher_total)
                
            if (self.discount == 0):            
                self.stdscr.hline(self.maxy-2,1," ",self.maxx-3)
                self.stdscr.addstr(self.maxy-2,self.maxx-18,"Total: $")
                self.stdscr.addstr(self.maxy-2,self.maxx-10,non_discount_totalstring.rjust(7))
                self.stdscr.refresh()
            else:
                discounttotal = float(total) * (float(self.discount)/100.0)
                discounttotalstring = "%5.2f" % discounttotal
                finaltotal = float(total) - discounttotal - voucher_total
                finaltotalstring = "%4.2f" % finaltotal
                self.stdscr.hline(self.maxy-2,1," ",self.maxx-3)
                self.stdscr.addstr(self.maxy-2,2,"Total: $"+totalstring)
                self.stdscr.addstr(self.maxy-2,20,"Discount : $"+discounttotalstring)
                self.stdscr.addstr(self.maxy-2,self.maxx-29,"Discounted Total: $")
                self.stdscr.addstr(self.maxy-2,self.maxx-10,finaltotalstring.rjust(7))
                self.stdscr.refresh()
                   
        if (self.thelist == []):
            self.stdscr.hline(self.maxy-2,1," ",self.maxx-3)
            self.stdscr.refresh()

        self.stdscr.hline(y,1," ",self.maxx-3)
        self.stdscr.refresh()

    def get_new_item(self,barcode):
        self.db_connect()
        query = """select products.id, categories.category, suppliers.name,
               products.name, products.description, products.retail_price, products.stock_qty
               from ((products left join suppliers on products.supplier=suppliers.id)
                      left join categories on products.category=categories.id
                    )
               where barcode=%s order by products.id;""" % barcode 
        self.cur.execute(query)
        row = self.cur.fetchone()
        self.db_close()
        return(row)

    def get_valid_productid_set(self):
        #valid_set = set()
        self.db_connect()
        query = """select barcode from products;"""
        self.cur.execute(query)
        rows = self.cur.fetchall()
        for row in rows:
            barcode = row[0]
            self.valid_set.add(barcode)
        self.db_close()

    def adjust_price_form(self,barcode, currentprice, selection_line):
        self.db_connect()
        query = """select retail_price from products where barcode = %s""" % barcode
        self.cur.execute(query)
        row = self.cur.fetchone()
        self.db_close()
        retail_price = row[0]

        self.stdscr.addstr(self.lines_of_instructions+2,self.maxx-27, "Enter New Price:          ") 
        self.stdscr.refresh()
        # The windows for the textboxes
        newprice_win = self.stdscr.derwin(1,10,self.lines_of_instructions+2,self.maxx-10)

        # the textboxes
        price_tb = curses.textpad.Textbox(newprice_win)
        self.he_hit_esc = 0
        self.he_hit_r = 0
        newprice = price_tb.edit(self.new_price_validator)
        if (newprice[-1]=="x"):
            newprice=newprice[:-1]
        if (self.he_hit_esc==1):
            #syslog.syslog("CHECKOUT_FORM: ESC :"+str(currentprice)+":")
            return(str(currentprice).strip())
        elif (self.he_hit_r==1):   
            #syslog.syslog("CHECKOUT_FORM: Return :"+str(retail_price)+":")
            return(str(retail_price).strip())
        else:     
            #syslog.syslog("CHECKOUT_FORM: ELSE :"+str(newprice)+":")
            return(str(newprice).strip())
        
    def new_price_validator(self,c):
        # Captues escape character and return 7 to exit the field edit form
        if (c==27):
            self.he_hit_esc = 1
            return(7)
        if (c==ord('r')):
            self.he_hit_r = 1
            return(7)
        # Otherwize, accept the character as typed.
        else:
            self.he_hit_esc = 0
            return(c)
    #Start of the main program

    def main_loop(self): 
        try:
        #if (1==1):
            # Set up the curses library
            self.stdscr = curses.initscr()
            curses.noecho()
            curses.cbreak()
            self.stdscr.keypad(1)

            # Find the size of the screen
            (y,x)=self.stdscr.getmaxyx()
            self.maxx=x
            self.maxy=y

            #self.con = mdb.connect(self.host, self.user, self.password, self.database_name)
            #self.cur = self.con.cursor()

            #self.checkout(self.host,self.user,self.password,self.database_name)

            # Clear the screen and redraw it fresh.
            self.stdscr.clear()
            self.redraw_all()

            # If there is anything on the list (why would there be?) 
            # start on the first item. Otherwise no itemselected.
            numstring=""
            exit = 0
            if (self.thelist == []):
                self.selection_line = 0
            else:
                self.selection_line = 1

            # Read in the set of product IDs from the database
            # so we can reference them fast from memory
            self.get_valid_productid_set()

            # The main loop where we capture key strokes and do the next thing
            # This involves entering numbers in the SKU field
            # hitting enter to add the sku item to the list
            # editing the list by going up and down, adjusting prices etc.

            while (exit == 0):
                # Read a character from the keyboard.
                c = self.stdscr.getch()
                
                # Diagnostic output of the keycodes
                if (self.dbout==1):
                    self.stdscr.addstr(self.maxy-10, 4,"Char code %d " % c)
                    self.stdscr.refresh()    
        
                # In pretend mode, show the key on the top line 
                if (self.pretend_mode==1):
                    self.stdscr.addstr(self.maxy-1,4,"        ")
                    self.stdscr.addstr(self.maxy-1,4,str(c))
                    self.stdscr.refresh()

                # If it's a digit, you are typing in the sku number field
                if (isdigit(c)):
                    if len(numstring) < 15:
                        numstring += chr(c)
                        self.stdscr.hline(0,1,curses.ACS_HLINE,16)
                        self.stdscr.addstr(0,16-len(numstring),numstring)
                        self.stdscr.move(0,16)
                    self.stdscr.refresh()
                #elif ((c == 10) and (numstring != "")):

                # Pressing enter when a sku is entered gets you here.
                # Try to add the item with that sku to the list.
                elif (((c == curses.KEY_ENTER) or (c == 13) or (c == 10)) and (numstring != "")):
                    #if (self.dbout):
                    #    curses.stdscr.addstr(self.maxy-10, 4," Return hit")
                    #    curses.stdscr.refresh()     
                    barcode = int(numstring)
                    if barcode in self.valid_set:
                        row=self.get_new_item(barcode)

                        # See if we have this barcode already in the list
                        # Also check how many. If there's only 1, increment the quantity.
                        # But if there is more than 1, then add another, since that is what
                        # the user probably wants. How would the compute know which one to
                        # increment?
                        # Also keep a record of the index, so we can reference it in the next
                        # bit of code.
                        match_barcode_count = 0
                        match_barcode_index = -1
                        i = 0
                        for item in self.thelist:
                            item_barcode, item_row, item_qty, item_currentprice, item_dp = item
                            if item_barcode == barcode:
                                match_barcode_count += 1
                                match_barcode_index = i
                                match_item = item
                            i = i + 1

                        # Now increment or add the new item. Except if it's a voucher.
                        if ((match_barcode_count == 0) and (barcode != 485)):
                            currentprice=row[5]
                            newitem=(barcode,row,1,currentprice, 0)  #qty=1, line item discount = 0%
                            #insert the new item at the end
                            #Except if there is a redeemed voucher. Which must remain at the end
                            #So check for the voucher and if it is there, inserted just before it
                            if len(self.thelist) > 0:
                                lastitem = self.thelist[-1] # Check last item in list
                                (lastbarcode, lastrow, lastqty, lastcurrentprice, lastdp) = lastitem
                            else:
                                lastbarcode=0
                            if lastbarcode==485:
                                self.thelist.insert(len(self.thelist)-1,newitem)
                                self.selection_line = self.next_itemno
                                self.next_itemno = self.next_itemno + 1
                            else: 
                                self.thelist.append(newitem)
                                self.selection_line = self.next_itemno
                                self.next_itemno = self.next_itemno + 1
                        elif ((match_barcode_count == 1) and (barcode != 485)):
                            existingbarcode,existingrow,qty,currentprice,dp = self.thelist[match_barcode_index]
                            if (qty == -1):
                                qty = 1
                            else:
                                qty = qty + 1
                            self.thelist[match_barcode_index]=(existingbarcode,existingrow,qty,currentprice,dp)
                            self.selection_line = match_barcode_index+1
                        # If there is more than one entry for this barcode, then the user has split
                        # into two in the past, so probably wants additional ones to also be
                        # separate
                        elif ((match_barcode_count > 1) and (barcode != 485)):
                            currentprice=row[5]
                            newitem=(barcode,row,1,currentprice, 0)  #qty=1, line item discount = 0%
                            #insert the new item in the list right after the last one matched
                            self.thelist.insert(match_barcode_index+1,newitem)
                            self.selection_line = self.next_itemno
                            self.next_itemno = self.next_itemno + 1
                        # Handle the case that it's a voucher
                        # If we already have a voucher, do nothing. The user has to set the price to
                        # include all vouchers anyway.
                        # If we don't have a voucher, add it.
                        elif ((barcode == 485) and (match_barcode_count==0)):
                            currentprice=row[5]
                            self.thelist.append((485,row,1,0.00,0))
                            self.next_itemno = self.next_itemno+1
                            self.selection_line=len(self.thelist)
                        numstring=""
                        self.stdscr.hline(0,1,curses.ACS_HLINE,15)
                        self.drawlist()
                    else:
                        responsestr=numstring+":Not Valid  "
                        numstring=""
                        self.stdscr.addstr(0,1,responsestr)
                        self.stdscr.refresh()
                
                # Split an item into 2 so it can be separate changed
                elif ((c == ord('S'))) and (self.selection_line != 0):
                    item_to_split = self.selection_line-1
                    item = self.thelist[item_to_split]
                    self.thelist.insert(item_to_split,item)
                    self.next_itemno += 1
                    self.selection_line += 1
                    self.drawlist()
                    self.stdscr.refresh()
                     

                # Backspace.in the sku field
                elif ((c == curses.KEY_BACKSPACE) and (numstring != "")):
                    numstring = numstring[:-1]
                    self.stdscr.hline(0,1,curses.ACS_HLINE,16)
                    self.stdscr.addstr(0,16-len(numstring),numstring)
                    self.stdscr.move(0,16)
                    self.stdscr.refresh()
                
                # Leave the program if ESC it hit             
                elif (c == curses.ascii.ESC):
                    exit = 1

                # Move up the list
                elif (c == curses.KEY_UP):
                    if (self.selection_line > 1):
                        self.selection_line = self.selection_line-1
                        self.drawlist()
                        self.stdscr.refresh()

                # Move down the list
                elif (c == curses.KEY_DOWN):
                    if (self.selection_line < (self.next_itemno-1)):
                        self.selection_line = self.selection_line+1
                        self.drawlist()
                        self.stdscr.refresh()

                # Delete an item from the list
                elif ((c == ord('x'))):
                    if (self.selection_line != 0) and (self.selection_line < (len(self.thelist)+1)):
                        item_to_delete = self.selection_line
                        del self.thelist[self.selection_line-1]
                        self.next_itemno = self.next_itemno-1
                        if self.selection_line > 1:
                            self.selection_line = self.selection_line -1
                        self.redraw_all()

                # Decrement the quantity of an item by 1.
                # Skip over 0 from 1 to -1. Use x to delete.
                elif ((c == ord('-')) or (c== curses.KEY_BACKSPACE)):
                    if (self.selection_line != 0):
                        barcode, row, qty, currentprice,dp = self.thelist[self.selection_line-1]
                        if (qty != 1):
                            qty = qty-1
                            thing = barcode, row, qty, currentprice,dp
                            self.thelist[self.selection_line-1] = thing
                        else:  #qty==1
                            qty = -1
                            thing = barcode, row, qty, currentprice,dp
                            self.thelist[self.selection_line-1] = thing
                        #self.drawlist()
                        self.redraw_all()

                # Increment the quantity of an item by 1.
                # Skip over 0 from -1 to 1. Use x to delete.
                elif (c == ord('+')):
                    if (self.selection_line != 0):
                        barcode, row, qty, currentprice,dp = self.thelist[self.selection_line-1]
                        if (qty == -1):
                            qty = 1
                            thing = barcode, row, qty, currentprice,dp
                            self.thelist[self.selection_line-1] = thing
                        else: 
                            qty = qty+1 
                            thing = barcode, row, qty, currentprice,dp
                            self.thelist[self.selection_line-1] = thing
                        #self.drawlist()
                        self.redraw_all()

                # Switch between pretend mode and normal mode 
                elif (c == ord('P')):
                    self.change_pretend_mode()
                    self.redraw_all()

                # Bring up a window of unmemorable skus.
                elif (c == ord('n')):
                    selection = self.review_numbers()
                    if (selection == 0):
                        #self.stdscr.addstr(25,15,str(selection)+"    ")
                        #self.stdscr.refresh()
                        self.redraw_all()
                    else:
                        self.redraw_all()
                        numstring = str(selection)
                        self.stdscr.hline(0,1,curses.ACS_HLINE,16)
                        self.stdscr.addstr(0,16-len(numstring),numstring)
                        #self.stdscr.addstr(25,15,str(selection)+"      ")
                        self.stdscr.move(0,16)
                        self.stdscr.refresh()

                # Reload
                elif (c == ord('R')):
                    self.thelist=list()
                    self.discount=0
                    self.next_itemno=1
                    self.selection_line=0
                    #self.db_close()
                    #self.db_connect()
                    self.get_valid_productid_set()
                    self.current_customer_num = 0
                    self.current_customer_name = ""
                    self.redraw_all()

                # Finalize
                elif ((c == ord('f')) and (len(self.thelist) > 0)):
                    self.checkout()
                    self.current_customer_num = 0
                    self.current_customer_name = ""
                    self.thelist=list()
                    self.clearlist()
                    self.next_itemno=1
                    self.selection_line=0
                    self.discount=0
                    self.redraw_all()

                # Global Discount
                elif (c == ord('D')):
                    if (self.discount>=50):
                        self.discount=0
                    else:
                        self.discount=self.discount+5
                    self.drawdiscount()
                    self.drawlist()

                # Add customer name to purchase
                elif (c == ord('c')):
                    self.customer_form()
                    self.redraw_all()

                # Go to transaction form
                elif (c == ord('t')):
                    self.transaction_form()
                    self.redraw_all()

                # Adjust the price down by 5% for just one item
                # Discount percentage dp kept in thelist[] 
                # seperate from the global discount
                elif (c == curses.KEY_LEFT):
                    if (self.selection_line != 0):
                        item_to_adjust = self.selection_line-1
                        barcode, row, qty, currentprice,dp = self.thelist[item_to_adjust]
                        undiscounted_price = row[5];
                        if ((barcode != 485) and (undiscounted_price > 0)):
                            if dp < 95:
                                dp = dp + 5
                                newprice = float(undiscounted_price) * (100.0-dp)/100.0 
                                self.thelist[item_to_adjust]=(barcode, row, qty, newprice,dp)
                        self.redraw_all()

                # Adjust the price up by 5% for just one item
                # seperate from the global discount
                elif (c == curses.KEY_RIGHT):
                    if (self.selection_line != 0):
                        item_to_adjust = self.selection_line-1

                        # Now change the actual price based on the percentage
                        barcode, row, qty, currentprice,dp = self.thelist[item_to_adjust]
                        undiscounted_price = row[5];
                        if ((barcode != 485) and (undiscounted_price > 0)):
                            if dp > 4:
                                dp = dp - 5
                                newprice = float(undiscounted_price) * (100.0-dp)/100.0 
                                self.thelist[item_to_adjust]=(barcode, row, qty, newprice,dp)
                        self.redraw_all()

                # Adjust price by typing it in.
                elif (c == ord('a')):
                    if (self.selection_line != 0):
                        item_to_adjust = self.selection_line-1
                        barcode, row, qty, currentprice,dp = self.thelist[item_to_adjust]
                        newprice = self.adjust_price_form(barcode,currentprice,item_to_adjust)
                        success,fnewprice = self.parsefloat(newprice)
                        if (success == 1):
                            self.thelist[item_to_adjust]=(barcode, row, qty, fnewprice, dp)
                        else:
                            self.thelist[item_to_adjust]=(barcode, row, qty, currentprice, dp)
                        self.redraw_all()

                # Reset the price back to its default
                elif (c == ord('A')):
                    if (self.selection_line != 0):
                        item_to_adjust = self.selection_line-1
                        barcode, row, qty, currentprice,dp = self.thelist[item_to_adjust]
                        newprice = row[5];
                        self.thelist[item_to_adjust]=(barcode, row, qty, newprice,dp)
                        self.redraw_all()

                # Someone resized the window, so recalculate the dimensions of everything and redraw.
                elif (c == curses.KEY_RESIZE):
                    (y,x)=self.stdscr.getmaxyx()
                    self.maxy=y
                    self.maxx=x
                    self.redraw_all()
                else:
                    numstring=""
                    self.stdscr.hline(0,1,curses.ACS_HLINE,14)
                    self.stdscr.refresh()
                    self.get_valid_productid_set()

        finally:
        #if (1==1):
            self.db_close()
            #self.con.close()
            curses.nocbreak()
            self.stdscr.keypad(1)
            curses.echo()
            curses.endwin()

co = checkout_form('blacksheepatorenco.com','blacksheep','bahbahbah','blacksheep',pretend_mode=False)
co.main_loop()

