# NTP Server

A custom NTP server that clients on a local network can reference for time synchronization.

## Demo Video

https://github.com/user-attachments/assets/b385a62f-0ba1-44c3-85a7-66934fb29d33

## Current Setup

My Raspberry Pi is connected to my PC via Ethernet, with the PC acting as a DHCP server.

Although that may sound fancy, I simply configured my Ethernet port to share my network connection with anything connected via Ethernet, allowing my PC to act as a router for the Pi.

While setting this up, I realized that Raspberry Pis do not have a secure way of determining the current time. They generally trust any available time source and, in most cases, depend on a network connection to reach a pool of NTP servers, a local NTP server, or a GPS module.

On boot, Raspberry Pis typically do not know the current time and rely on an external source to correct it. This project explores that dependency and examines how far it can be pushed.

Through my research, I've found that a surprising number of systems are time-dependent, including package management, certificates, and containers, among others.

This project is primarily for learning purposes. I have worked with time synchronization before, and this project is an opportunity to deepen my understanding of networking concepts through hands-on experimentation.

## Milestones

As far as I am aware, Raspberry Pis send requests on port 123, the default port for NTP communication.

The goal is to create a Python program that listens for requests on this port and sends a custom packet containing time information back to the Pi.

The Pi runs `Chrony`, an NTP client and server, while the PC runs this Python script to send time information via UDP packets.

A future goal is to port this project to C and benchmark its performance.

Note that the script requires elevated permissions, as Linux treats any port below 1024 as privileged.

## Developer Notes

For setup instructions (disabling `Chrony` on the server, running the script with sudo, configuring a client to use this server as a reference, etc.), see [DEVELOPER_NOTES.md](DEVELOPER_NOTES.md).
