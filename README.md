# networkModule
# networkModule


# Overview

{Important!  Do not say in this section that this is college assignment.  Talk about what you are trying to accomplish as a software engineer to further your learning.}

{Provide a description the networking program that you wrote. Describe how to use your software.  If you did Client/Server, then you will need to describe how to start both.}

Description: This is a P2P filesharing program.

How to use it: 
    Step 1: On your first PC download the program. With your Machine's IP address in hand run the following:
    "
     ❯ python3 p2psharing.py --port 5000
    "
    Step 2: On your second PC run the same command on a different port. ie:
    "
    ❯ python3 p2psharing.py --port 5001
    "

    !IMPORTANT
    - The machine with the file to download has no further steps
    Step 3: Connect one machine to the other by entering in the following:
    "
    connect <ipv4 address of target machine> <port number of target machine>
    "
    Step 4:  Once connected these are the following commands you can run:
        list - lists all files in target machine's shared folder of the p2psharing.py program directory
        info <filename> - Returns information about a file.
        get <filename> - Downloads a file.

{Describe your purpose for writing this software.}
Purpose: This is a p2p filesharing program I wrote in python to concrete my current understanding in networking technologies.


[Software Demo Video] https://youtu.be/1pdlTC7IQec

# Network Communication

{Describe the architecture that you used (client/server or peer-to-peer)}
-The program uses a P2P architecture. Each person running the program on their machine can use their respective machines as both the client and the server. Both peers listen for TCP connections and allow another user to initiate connections to other peers. There isnt a single centralized server.


{Identify if you are using TCP or UDP and what port numbers are used.}
I used TCP and you can use any high non privlidge port number that isnt already oupied from 1024-65535

{Identify the format of messages being sent between the client and server or the messages sent between two peers.}

json. Specifially newline-delimited JSON (NDJSON)

# Development Environment

{Describe the tools that you used to develop the software}
socket for TCP networking
threading for concurrent connections
json for structured message formatting
os for filesystem access

Code oss (The free and open source version of Visual Studio code.)
Developed on CachyOS. (An operating systen with linux kernel on Arch base and custom patches)
Tested on CachyOS on PC1 and ArchLinux on PC2


{Describe the programming language that you used and any libraries.}
The programming language was python 3 and I used the following libraries:
1. socket
2. threading
3. json
4. os
# Useful Websites

{Make a list of websites that you found helpful in this project}
* [doc.python.org](https://docs.python.org/3/library/socket.html)
* [Wikipedia](https://en.wikipedia.org/wiki/Peer-to-peer)

# Future Work

{Make a list of things that you need to fix, improve, and add in the future.}
* Item 1 Add encryption and authentication for secure file sharing between peers.
* Item 2 Add auto peer discovery instead of adding an IP by hand.
* Item 3 Add a GUI. Like im use linux as my daily driver but I always prefer using a GUI to have a visualization of what it is I am using.