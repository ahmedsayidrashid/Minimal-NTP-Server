#!/usr/bin/env python3
"""
Minimal NTP Server
Responds to NTP requests on UDP port 123 with custom or current system time.
"""

import socket
import struct
import time
import datetime
import os
import click

# NTP epoch: January 1, 1900 00:00:00 UTC
NTP_EPOCH = datetime.datetime(1900, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)


def datetime_to_ntp_timestamp(dt):
    """
    Convert a datetime object to NTP timestamp format.
    NTP timestamp is a 64-bit fixed-point number:
    - Upper 32 bits: seconds since NTP epoch (1900-01-01)
    - Lower 32 bits: fractional seconds
    """
    if dt.tzinfo is None:
        # Assume UTC if no timezone info
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    
    # Convert to UTC
    dt_utc = dt.astimezone(datetime.timezone.utc)
    
    # Calculate seconds since NTP epoch
    delta = dt_utc - NTP_EPOCH
    seconds = int(delta.total_seconds())
    
    # Calculate fractional seconds (microseconds / 1,000,000 * 2^32)
    # Convert microseconds to seconds, than to a 32 bit integer
    microseconds = delta.microseconds
    fractional = int((microseconds / 1_000_000) * (2 ** 32))
    return (seconds << 32) | fractional


def ntp_timestamp_to_datetime(ntp_timestamp):
    """
    Convert NTP timestamp to datetime object.
    """
    # Unpack the NTP timestamp into seconds and fractional seconds
    # Upper 32 bits: seconds
    # Lower 32 bits: fractional seconds
    seconds = (ntp_timestamp >> 32) & 0xFFFFFFFF
    fractional = ntp_timestamp & 0xFFFFFFFF
    microseconds = int((fractional / (2 ** 32)) * 1_000_000)
    
    dt = NTP_EPOCH + datetime.timedelta(seconds=seconds, microseconds=microseconds)
    return dt.replace(tzinfo=datetime.timezone.utc)


def parse_custom_time(time_str):
    """
    Parse a custom time string in ISO 8601 format or Unix timestamp.
    Returns a datetime object in UTC.
    """
    if not time_str:
        return None
    
    # Try parsing as Unix timestamp (numeric string)
    try:
        unix_timestamp = float(time_str)
        return datetime.datetime.fromtimestamp(unix_timestamp, tz=datetime.timezone.utc)
    except (ValueError, OSError):
        pass
    
    # Try parsing as ISO 8601 format
    try:
        # Try with timezone
        dt = datetime.datetime.fromisoformat(time_str.replace('Z', '+00:00'))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        return dt.astimezone(datetime.timezone.utc)
    except ValueError:
        pass
    
    # Try common ISO formats
    formats = [
        '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%dT%H:%M:%S.%f',
        '%Y-%m-%d %H:%M:%S.%f',
    ]
    
    for fmt in formats:
        try:
            dt = datetime.datetime.strptime(time_str, fmt)
            return dt.replace(tzinfo=datetime.timezone.utc)
        except ValueError:
            continue
    
    raise ValueError(f"Unable to parse time string: {time_str}")


def get_custom_time(cli_time=None):
    """
    Get custom time from CLI argument or environment variable.
    Priority: CLI argument > Environment variable > Current system time
    Returns a datetime object in UTC.
    """
    # Check CLI argument first
    if cli_time:
        return parse_custom_time(cli_time)
    
    # Check environment variable
    env_time = os.environ.get('NTP_CUSTOM_TIME')
    if env_time:
        return parse_custom_time(env_time)
    
    # Default to current system time
    return datetime.datetime.now(datetime.timezone.utc)


def parse_ntp_request(data):
    """
    Parse an NTP request packet and extract the origin timestamp.
    Returns the origin timestamp as a 64-bit integer, or None if invalid.
    """
    if len(data) < 48:
        return None
    
    try:
        print(f"Data received: {data}")
        # Extract origin timestamp (bytes 24-31)
        origin_timestamp = struct.unpack('!Q', data[24:32])[0]
        print(f"Origin timestamp: {origin_timestamp}")
        return origin_timestamp
    except struct.error:
        print(f"Error parsing NTP request: {struct.error}")
        return None


def build_ntp_response(origin_time, receive_time, transmit_time):
    """
    Build a 48-byte NTP response packet.
    
    Args:
        origin_time: Origin timestamp from client request (64-bit NTP timestamp)
        receive_time: When server received the request (datetime object)
        transmit_time: Time to send in response (datetime object)
    
    Returns:
        48-byte NTP response packet as bytes
    """
    # Convert datetime objects to NTP timestamps
    receive_ntp = datetime_to_ntp_timestamp(receive_time)
    transmit_ntp = datetime_to_ntp_timestamp(transmit_time)
    
    # First byte: LI (2 bits), VN (3 bits), Mode (3 bits)
    # LI = 0 (no leap second), VN = 4 (NTP version 4), Mode = 4 (server)
    flags = (0 << 6) | (4 << 3) | 4
    
    # Stratum: 1 (primary server) - this is the server that is directly connected to the GPS or other time source
    # stratum 2 is a secondary server
    stratum = 2
    
    # Poll interval: 4 (16 seconds) - reasonable default
    # note this is only a hint, chrony will determine how often to poll the server dynamically
    poll = 1
    
    # Precision: -20 (2^-20 seconds ≈ 1 microsecond)
    # NTP precision is a signed 8-bit integer, but we'll pack it correctly
    precision = -20
    
    # Root delay: 1 ms delay
    # added a little bit of delay for chrony to not be suspicious about a fake time source
    # this feild is to indicate the delay between getting the time from the source (GPS or other time source)
    root_delay = int(0.001 * (1 << 16)) 
    
    # Root dispersion: 0 (no dispersion for primary server)
    # some here, little delay for chrony to not be suspicious
    # this feild is to indicate the uncertainty and maximum error of the time from the source (GPS or other time source)
    root_dispersion = int(0.001 * (1 << 16)) 
    
    # Reference ID: "LOCL" (local clock)
    ref_id = b'LOCL'
    
    # Reference timestamp: same as transmit time (we're the source)
    ref_timestamp = transmit_ntp
    
    # Build the packet using struct
    # Pack first 3 bytes as unsigned, precision separately as signed
    packet = struct.pack('!BBB',
                         flags,      # Flags
                         stratum,    # Stratum
                         poll)       # Poll interval
    packet += struct.pack('!b', precision)  # Precision (signed byte)
    
    packet += struct.pack('!I', root_delay)      # Root delay (4 bytes)
    packet += struct.pack('!I', root_dispersion)  # Root dispersion (4 bytes)
    packet += ref_id                              # Reference ID (4 bytes)
    packet += struct.pack('!Q', ref_timestamp)   # Reference timestamp (8 bytes)
    packet += struct.pack('!Q', origin_time)     # Origin timestamp (8 bytes)
    packet += struct.pack('!Q', receive_ntp)     # Receive timestamp (8 bytes)
    packet += struct.pack('!Q', transmit_ntp)     # Transmit timestamp (8 bytes)
    
    return packet


@click.command()
@click.option('--time', '-t', 'custom_time', 
              help='Custom time in ISO 8601 format (e.g., "2024-01-15T10:30:00") or Unix timestamp. '
                   'Overrides NTP_CUSTOM_TIME environment variable.')
@click.option('--port', '-p', default=123, type=int,
              help='UDP port to listen on (default: 123, requires root privileges)')
def main(custom_time, port):
    """
    Minimal NTP Server
    
    Responds to NTP requests with custom or current system time.
    Custom time can be set via --time/-t CLI argument or NTP_CUSTOM_TIME environment variable.
    """
    # Get the custom time (or current time if not specified)
    base_time = get_custom_time(custom_time)
    use_custom_time = custom_time or os.environ.get('NTP_CUSTOM_TIME')
    
    # Track server start time for calculating offsets
    server_start_time = time.time()
    
    print(f"NTP server starting on port {port}")
    if use_custom_time:
        print(f"Using custom time: {base_time.isoformat()}")
    else:
        print("Using current system time")
    
    # Create UDP socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    try:
        # Bind to the specified port
        server_socket.bind(('0.0.0.0', port))
        print(f"NTP server is running on port {port}")
        print("Waiting for NTP requests...")
        
        while True:
            # Receive NTP request
            data, addr = server_socket.recvfrom(1024)
            
            # Parse the request to get origin timestamp
            origin_timestamp = parse_ntp_request(data)
            
            if origin_timestamp is None:
                print(f"Received invalid NTP request from {addr}, ignoring...")
                continue
            
            # Get receive time (when we received the request)
            receive_time = datetime.datetime.now(datetime.timezone.utc)
            
            # Get transmit time (the time we want to send)
            if use_custom_time:
                # Calculate elapsed time since server started
                elapsed_seconds = time.time() - server_start_time
                # Add elapsed time to the custom base time
                transmit_time = base_time + datetime.timedelta(seconds=elapsed_seconds)
            else:
                transmit_time = receive_time
            
            # Build NTP response packet
            response = build_ntp_response(origin_timestamp, receive_time, transmit_time)
            
            # Send response back to client
            server_socket.sendto(response, addr)
            
            transmit_str = transmit_time.isoformat()
            print(f"Sent NTP response to {addr[0]}:{addr[1]} (transmit time: {transmit_str})")
    
    except PermissionError:
        print(f"Error: Permission denied. Port {port} requires root/administrator privileges.")
        print("Please run with sudo or as administrator.")
        return 1
    except KeyboardInterrupt:
        print("\nShutting down NTP server...")
        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 1
    finally:
        server_socket.close()
    return 0

if __name__ == '__main__':
    exit(main())
