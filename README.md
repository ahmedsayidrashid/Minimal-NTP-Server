# Custom NTP Server

Custom NTP Server for any clients on local networks to reference.

## Current Setup

At the moment, I have my PI connected to my PC via ethernet, where my PC is acting as a 'mini DHCP server'.

Although that may sound fancy, I just set up my ethernet port to share the network connection to anything connected via ethernet, and my PC acts as a router to my PI.

Digging into my setup, I realized that PI's don't really have much have a secure way to find out what time it is. It pretty much blindly follows any time source, and in most cases, it depends on a network connection to use it's pool of NTP servers, a local NTP server, or a GPS.

On boot, PI's usually don't know the time, and often rely on a time source to correct it, however, this project is to tinker with this capability and see how much I can play with this concept.

Doing my little research, I've noticed that **a lot** of things are time dependent, such as anything to do with **trust** (package management, certificates, containers etc).

This project is mainly for learning experiences, I've played with time source synchornization before, this project is more so for learning networking and other learning experineces.

## Milestones

As far as I am aware, PI's expect requests on port 123 (default port for NTP information).

Create a python program that waits for request on this port, and send a custom packet to my PI that repersents time information.

Of course, the PI will be running `Chrony`, an NTP client and server. My PC will be running this Python script as NTP server.

Eventually, I'd love to port over this project to C.
