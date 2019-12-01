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


    blastee_IP = get_file_info("b")
    num_packets = get_file_info("n")
    payload_len = get_file_info("l")
    sender_window_size = get_file_info("w")
    RTT = get_file_info("rtt")
    recv_timeout = get_file_info("r")
    alpha = get_file_info("alpha")
    est_rtt = RTT
    timeout = update_timeout(est_rtt)

    sliding_window = SlidingWindow(sender_window_size)

    while True:
        gotpkt = True
        if sliding_window.LHS > num_packets:
            break
        try:
            #Timeout value will be parameterized!
            #TODO is milliseconds ok for recv_timeout?
            timestamp,dev,pkt = net.recv_packet(timeout=recv_timeout)
        except NoPackets:
            log_debug("No packets available in recv_packet")
            gotpkt = False
        except Shutdown:
            log_debug("Got shutdown signal")
            break

        if gotpkt:
            log_debug("I got a packet")
            #QUES do we need to check if there's an ACK header here?
            seq_no = get_ack_seq_no(pkt)
            if sliding_window.is_seqNo_in_window(seq_no):
                index = seq_no - sliding_window.LHS
                sliding_window[index].is_acked = True
                sliding_window.refresh_LHS()
                #QUES should we recalculate RWMA for acks outside sliding window?
                #TODO calculate the RTT for the current packet to pass in as prior_rtt
                est_rtt = update_est_rtt(alpha,est_rtt,prior_rtt)
                timeout = update_timeout(est_rtt)

        else:

            #We know we can send if C1 is satisfied and we haven't
            #sent all our packets
            if sliding_window.can_send() and num_packets >= sliding_window.RHS:
                sliding_window.add_entry()
                #TODO send packets
            log_debug("Didn't receive anything")

            '''
            Creating the headers for the packet
            '''
            pkt = Ethernet() + IPv4() + UDP()
            pkt[1].protocol = IPProtocol.UDP

            '''
            Do other things here and send packet
            '''
            #TODO call sliding_window.check_timeouts(timeout)

    net.shutdown()

#Calvin I definitely just stole this straight from you lol
def get_ack_seq_no(pkt):
    my_header_bytes = pkt[3].to_bytes()
    #seq_num_int = int.from_bytes(my_header_bytes[0:4], byteorder='big')
    seq_num_bytes = my_header_bytes[0:4]
    length_int = int.from_bytes(my_header_bytes[4:6], byteorder='big')

def update_est_rtt(alpha,est_rtt,prior_rtt):
    new_est_rtt = ((1 - alpha)*est_rtt) + (alpha*prior_rtt)
    return new_est_rtt
    
def update_timeout(est_rtt):
    return est_rtt * 2

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


class SlidingWindow(object,window_size = 1,LHS = 1,RHS = 1):

    def __init__(self):
        self.window = []
        self.window_size = window_size
        self.LHS = LHS
        self.RHS = RHS
        #QUES do we need this?
        self.max_seqno = pow(2,32)

    def add_entry(self):
        sw_entry = SlidingWindowEntry(self.RHS)
        self.window.append(entry)
        self.RHS += 1

    def is_seqNo_in_window(self,seqNo):
        #QUES is this right? Book and assignment are different in this respect
        return seqNo >= self.LHS and seqNo <= self.RHS - 1

    def refresh_LHS(self,entry):
        for entry in window:
            if entry.is_acked == False:
                return
            else:
                self.window.remove(entry)
                #TODO if we have to handle wraparound handle this
                self.LHS += 1
        return

    def can_send(self):
        return self.RHS - self.refresh_LHS <= self.window_size

    def check_timeouts(timeout):
        for entry in self.window:
            if entry.is_acked == False:
                #TODO make sure units are comprable between time and timeout
                if time.time() - entry.time_last_sent >= timeout:
                    #TODO send packet with entry.seq_no

class SlidingWindowEntry(object):
    
    def __init__(self, seq_no = None, time_last_sent = time.time()):
        self.is_acked = False
        self.seq_no = seq_no
        self.time_last_sent = time_last_sent