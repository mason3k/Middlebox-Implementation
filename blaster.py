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
    recv_timeout = recv_timeout/1000
    alpha = get_file_info("alpha")
    est_rtt = RTT
    timeout = update_timeout(est_rtt)

    sliding_window = SlidingWindow(sender_window_size)

    # cky - track last time ack was received
    last_ack_recved = None

    while True:
        gotpkt = True
        if sliding_window.LHS > num_packets:
            break
        try:
            #Timeout value will be parameterized!
            #TODO is seconds ok for recv_timeout?
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
            #cky - I think what we have is good.  we are getting the seq from the ack so that's probably all we need?

            seq_no = get_ack_seq_no(pkt)
            if sliding_window.is_seqNo_in_window(seq_no):
                index = seq_no - sliding_window.LHS
                pkt_sw_entry = sliding_window[index]
                if pkt_sw_entry.is_acked == False:
                    pkt_sw_entry.is_acked = True
                    prior_rtt = time.time() - pkt_sw_entry.time_first_sent
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

                # cky - we should probably make below into a function
                # prep to send a new packet
                out_intf = my_intf[0]
                seq_no = sliding_window.RHS # new RHS updated
                # we also need payload_len

                pkt_to_send = Ethernet() + IPv4() + UDP()
                
                # Ethernet
                pkt_to_send[Ethernet].src = out_intf.ethaddr
                pkt_to_send[Ethernet].dst = '40:00:00:00:00:01'

                # IP
                pkt_to_send[IPv4].src = out_intf.ipaddr
                pkt_to_send[IPv4].dst = '192.168.200.1'
                pkt_to_send[1].protocol = IPProtocol.UDP

                # UDP (still not sure about 4444 5555.  It said it can be anything so I copied from the library example)
                pkt_to_send[UDP].src = 4444
                pkt_to_send[UDP].dst = 5555
                
                pkt_to_send = pkt_to_send + RawPacketContents(seq_no.to_bytes(4, byteorder='big') + payload_len.to_bytes(2, byteorder='big'))

                # we also need "Variable length payload".... how?
                #import random
                #a = []
                #for i in range(10):
                #    a.append(random.randint(0,255))
                #b = bytes(a)
                #print(a)
                #print(b)
                payload_int = []
                for i in range(payload_len):
                    payload_int.append(random.randint(0,255))
                payload_byte = byte(payload_int)

                pkt_to_send = pkt_to_send + RawPacketContents(payload_byte)

                net.send_packet(out_intf.name, pkt_to_send)

                #increment RHS by 1 after sending
                sliding_window.RHS = sliding_window.RHS + 1

            sliding_window.check_timeouts(timeout)

            log_debug("Didn't receive anything")

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
                self.LHS += 1
        return

    def can_send(self):
        return self.RHS - self.refresh_LHS <= self.window_size

    def check_timeouts(timeout, net, payload_len, my_intf):
        for entry in self.window:
            if entry.is_acked == False:
                #TODO make sure units are comprable between time and timeout
                # cky - I think we have to divide timeout by 1000?
                if time.time() - entry.time_last_sent >= timeout/1000:
                    entry.time_last_sent = time.time()

                    #TODO send packet with entry.seq_no
                    # cky - we can probably be smarter and move this part below as one fcn to be shared bewteen main and here....
                    out_intf = my_intf[0]
                    seq_no = entry.seq_no
                    # we also need payload_len

                    pkt_to_send = Ethernet() + IPv4() + UDP()
                
                    # Ethernet
                    pkt_to_send[Ethernet].src = out_intf.ethaddr
                    pkt_to_send[Ethernet].dst = '40:00:00:00:00:01'

                    # IP
                    pkt_to_send[IPv4].src = out_intf.ipaddr
                    pkt_to_send[IPv4].dst = '192.168.200.1'
                    pkt_to_send[1].protocol = IPProtocol.UDP

                    # UDP (still not sure about 4444 5555.  It said it can be anything so I copied from the library example)
                    pkt_to_send[UDP].src = 4444
                    pkt_to_send[UDP].dst = 5555
                
                    pkt_to_send = pkt_to_send + RawPacketContents(seq_no.to_bytes(4, byteorder='big') + payload_len.to_bytes(2, byteorder='big'))

                    # we also need "Variable length payload".... how?
                    #import random
                    #a = []
                    #for i in range(10):
                    #    a.append(random.randint(0,255))
                    #b = bytes(a)
                    #print(a)
                    #print(b)
                    payload_int = []
                    for i in range(payload_len):
                        payload_int.append(random.randint(0,255))
                    payload_byte = byte(payload_int)

                    pkt_to_send = pkt_to_send + RawPacketContents(payload_byte)

                    net.send_packet(out_intf.name, pkt_to_send)

                    #QUES should we increment RHS for resending? I don't think so

class SlidingWindowEntry(object):
    
    def __init__(self, seq_no = None, time_last_sent = time.time(), time_first_sent = time.time()):
        self.is_acked = False
        self.seq_no = seq_no
        self.time_last_sent = time_last_sent
        self.time_first_sent = time_first_sent
