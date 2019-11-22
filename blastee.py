#!/usr/bin/env python3

from switchyard.lib.address import *
from switchyard.lib.packet import *
from switchyard.lib.userlib import *
from threading import *
import time

def switchy_main(net):
    my_interfaces = net.interfaces()
    mymacs = [intf.ethaddr for intf in my_interfaces]

    while True:
        gotpkt = True
        try:
            timestamp,dev,pkt = net.recv_packet()
            log_debug("Device is {}".format(dev))
        except NoPackets:
            log_debug("No packets available in recv_packet")
            gotpkt = False
        except Shutdown:
            log_debug("Got shutdown signal")
            break

        if gotpkt:
            log_debug("I got a packet from {}".format(dev))
            log_debug("Pkt: {}".format(pkt))

            # parse out what we need
            my_header_bytes = pkt[3].to_bytes()
            #seq_num_int = int.from_bytes(my_header_bytes[0:4], byteorder='big')
            seq_num_bytes = my_header_bytes[0:4]
            length_int = int.from_bytes(my_header_bytes[4:6], byteorder='big')

            # payload padding
            padding_bytes = 8 - length_int
            padding = bytes(max(0,padding_bytes))
            ack_payload_bytes = my_header[6:length_int] + padding

            # create an ACK
            # construct a packet to be received (below from switchyard documentation
            #p = Ethernet(src="00:11:22:33:44:55", dst="66:55:44:33:22:11") + \
            #IPv4(src="1.1.1.1", dst="2.2.2.2", protocol=IPProtocol.UDP, ttl=61) + \
            #UDP(src=5555, dst=8888) + b'some payload'
            #ack = Ethernet() + IPv4() + UDP()
            
            ack[Ethernet].src = my_interfaces[0].ethaddr
            ack[Ethernet].dst = '40:00:00:00:00:01'

            ack[IPv4].src = my_interfaces[0].ipaddr
            ack[IPv4].dst = '192.168.100.1'
            # do we need below 2?
            ack[IPv4].protocol = IPProtocol.UDP
            ack[IPv4].ttl = 61

            # from switchyard documentation
            #>>> p = Ethernet() + IPv4(protocol=IPProtocol.UDP) + UDP()
            #p[UDP].src = 4444
            #p[UDP].dst = 5555
            #p += b'These are some application data bytes'
            ack[UDP].src = 4444
            ack[UDP].dst = 5555
            
            # add seq #
            #pkt +=  RawPacketContents(seq_num_int.to_bytes(4, byteorder='big'))
            ack +=  RawPacketContents(seq_num_bytes)

            # add payload
            ack += RawPacketContents(ack_payload_bytes)

            net.send_packet(my_interfaces[0].name, ack)





    net.shutdown()
