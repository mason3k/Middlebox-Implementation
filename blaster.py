#!/usr/bin/env python3

from switchyard.lib.address import *
from switchyard.lib.packet import *
from switchyard.lib.userlib import *
import random
import time


def switchy_main(net):
    my_intf = net.interfaces()
    mymacs = [intf.ethaddr for intf in my_intf]
    myips = [intf.ipaddr for intf in my_intf]


    blastee_IP = get_file_info("b")
    num_packets = int(get_file_info("n"))
    payload_len = int(get_file_info("l"))
    sender_window_size = int(get_file_info("w"))
    RTT = float(get_file_info("rtt"))
    recv_timeout = get_file_info("r")
    recv_timeout = float(recv_timeout)
    recv_timeout = recv_timeout/1000
    alpha = float(get_file_info("alpha"))
    est_rtt = RTT
    timeout = update_timeout(est_rtt)

    sliding_window = SlidingWindow(sender_window_size)

    # For printing
    total_time_spefnt = None
    start_time = None
    last_ack_time = None
    num_resent = 0
    coarse_tos = 0
    throughput_length = 0
    throughput = 0
    goodput_length = 0
    goodput = 0
    final_est_rtt = 0 
    final_to = 0
    min_rtt = est_rtt
    max_rtt = est_rtt

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


        # Set the start time
        if start_time is None:
            start_time = time.time()

        if gotpkt:
            log_debug("I got a packet")
            if (not pkt.has_header(IPv4)):
                break
            #QUES do we need to check if there's an ACK header here?
            #cky - I think what we have is good.  we are getting the seq from the ack so that's probably all we need?

            seq_no = get_ack_seq_no(pkt)
            if sliding_window.is_seqNo_in_window(seq_no):
                index = seq_no - sliding_window.LHS
                pkt_sw_entry = sliding_window.window[index]
                if pkt_sw_entry.is_acked == False:
                    pkt_sw_entry.is_acked = True
                    # last ack received
                    last_ack_time = time.time()
                    prior_rtt = time.time() - pkt_sw_entry.time_first_sent
                    sliding_window.refresh_LHS()
                    #QUES should we recalculate RWMA for acks outside sliding window?
                    #TODO calculate the RTT for the current packet to pass in as prior_rtt
                    est_rtt = update_est_rtt(alpha,est_rtt,prior_rtt)
                    min_rtt = min(min_rtt, est_rtt)
                    max_rtt = max(max_rtt, est_rtt)
                    timeout = update_timeout(est_rtt)

        else:
            #We know we can send if C1 is satisfied and we haven't
            #sent all our packets
            if sliding_window.can_send() and num_packets >= sliding_window.RHS:
                seq_no = sliding_window.RHS
                sliding_window.add_entry()

                # cky - we should probably make below into a function
                # prep to send a new packet
                out_intf = my_intf[0]
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
                payload_byte = bytes(payload_int)

                pkt_to_send = pkt_to_send + RawPacketContents(payload_byte)

                net.send_packet(out_intf.name, pkt_to_send)
                throughput_length += payload_len
                goodput_length += payload_len

            # temp = number of times it was resubmitted
            temp = sliding_window.check_timeouts(timeout, net, payload_len, my_intf)
            num_resent = num_resent + temp
            coarse_tos  = coarse_tos + temp
            throughput_length = throughput_length + (temp * payload_len)

            log_debug("Didn't receive anything")


        # cky - should we break at some point? if LHS > num_packets
        if sliding_window.LHS > num_packets:
            break

    if last_ack_time is not None:
        total_time_spent = last_ack_time - start_time
        #num_resent = 0
        #coarse_tos = 0
        throughput = throughput_length / total_time_spent
        goodput = goodput_length / total_time_spent
        final_est_rtt = est_rtt
        final_to = timeout
        #min_rtt
        #max_rtt
        # print output here
        print_output(total_time_spent, num_resent, coarse_tos, throughput, goodput, final_est_rtt, final_to, min_rtt, max_rtt)

    net.shutdown()

#Calvin I definitely just stole this straight from you lol
def get_ack_seq_no(pkt):
    my_header_bytes = pkt[3].to_bytes()
    seq_num_int = int.from_bytes(my_header_bytes[0:4], byteorder='big')
    return  seq_num_int

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
        if key_index < len(line_list):
            return line_list[key_index + 1]
        else:
            return ""


def print_output(total_time, num_ret, num_tos, throughput, goodput, estRTT, t_out, min_rtt, max_rtt):

    print("Total TX time (s): " + str(total_time))
    print("Number of reTX: " + str(num_ret))
    print("Number of coarse TOs: " + str(num_tos))
    print("Throughput (Bps): " + str(throughput))
    print("Goodput (Bps): " + str(goodput))
    print("Final estRTT(ms): " + str(estRTT))
    print("Final TO(ms): " + str(t_out))
    print("Min RTT(ms):" + str(min_rtt))
    print("Max RTT(ms):" + str(max_rtt))



class SlidingWindow:

    def __init__(self,window_size = 1,LHS = 1,RHS = 1):
        self.window = []
        self.window_size = window_size
        self.LHS = LHS
        self.RHS = RHS

    def add_entry(self):
        sw_entry = SlidingWindowEntry(self.RHS)
        self.window.append(sw_entry)
        self.RHS += 1

    def is_seqNo_in_window(self,seqNo):
        #QUES is this right? Book and assignment are different in this respect
        return seqNo >= self.LHS and seqNo < self.RHS 

    def refresh_LHS(self):
        temp = self.window.copy()
        for entry in temp:
            if entry.is_acked == False:
                return
            else:
                self.window.remove(entry)
                self.LHS += 1
        return

    def can_send(self):
        return self.RHS - self.LHS < self.window_size

    def check_timeouts(self,timeout, net, payload_len, my_intf):
        temp_num_resent = 0
        

        for entry in self.window:
            if entry.is_acked == False:
                # cky - I think we have to divide timeout by 1000?
                if time.time() - entry.time_last_sent >= timeout/1000:
                    seq_no = entry.seq_no
                    entry.time_last_sent = time.time()

                    # cky - we can probably be smarter and move this part below as one fcn to be shared bewteen main and here....
                    out_intf = my_intf[0]
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
                    payload_byte = bytes(payload_int)

                    pkt_to_send = pkt_to_send + RawPacketContents(payload_byte)

                    net.send_packet(out_intf.name, pkt_to_send)
                    temp_num_resent += 1
                    

        return temp_num_resent


            

class SlidingWindowEntry:
    
    def __init__(self, seq_no = None, time_last_sent = time.time(), time_first_sent = time.time()):
        self.is_acked = False
        self.seq_no = seq_no
        self.time_last_sent = time_last_sent
        self.time_first_sent = time_first_sent
