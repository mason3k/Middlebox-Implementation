#!/usr/bin/env python3

from switchyard.lib.address import *
from switchyard.lib.packet import *
from switchyard.lib.userlib import *
from random import randint
import time


def switchy_main(net):
    my_intf = net.interfaces()
    mymacs = [intf.ethaddr for intf in my_intf]
    myips = [intf.ipaddr for intf in my_intf]

    sliding_window = SlidingWindow()

    blastee_IP = get_file_info("b")
    num_packets = get_file_info("n")
    payload_len = get_file_info("l")
    sender_window_size = get_file_info("w")
    RTT = get_file_info("rtt")
    recv_timeout = get_file_info("alpha")

    while True:
        gotpkt = True
        try:
            #Timeout value will be parameterized!
            timestamp,dev,pkt = net.recv_packet(timeout=0.15)
        except NoPackets:
            log_debug("No packets available in recv_packet")
            gotpkt = False
        except Shutdown:
            log_debug("Got shutdown signal")
            break

        if gotpkt:
            log_debug("I got a packet")
            #TODO if we got an ack:
            #TODO if the ack seq number is in the window (use is_seqNo_in_window):
            #   -> Remove the entry and refresh LHS (use refresh_LHS)
        else:
            log_debug("Didn't receive anything")

            '''
            Creating the headers for the packet
            '''
            pkt = Ethernet() + IPv4() + UDP()
            pkt[1].protocol = IPProtocol.UDP

            '''
            Do other things here and send packet
            '''

    net.shutdown()

def get_file_info(key):
    f = open("blaster_params.txt", "r")
    key = "-"+key
    for line in f:
        line_list = line.split(" ")
        key_index = line_list.index(key)
        if key_index < line_list.len():
            return line_list[key_index + 1]
        else:
            return ""


class SlidingWindow(object,LHS = 1,RHS = 1):

    def __init__(self):
        self.window = []
        self.LHS = LHS
        self.RHS = RHS

    def add_entry(self,entry):
        self.window.append(entry)

    def is_seqNo_in_window(self,seqNo):
        pos = seqNo - self.LHS
        mas_pos = max - min + 1
        return pos < mas_pos

    def refresh_LHS(self,entry):
        for entry in window:
            if entry.is_acked == False:
                return
            else:
                self.window.remove(entry)
                self.LHS +=1
        return


class SlidingWindowEntry(object):
    
    def __init__(self, seq_no = None, time_last_sent = time.time()):
        self.is_acked = False
        self.seq_no = seq_no
        self.time_last_sent = time_last_sent