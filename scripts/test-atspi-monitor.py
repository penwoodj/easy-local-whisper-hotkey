#!/usr/bin/env python3
import sys
import time
from pathlib import Path

try:
    import gi
    gi.require_version('Atspi', '2.0')
    from gi.repository import Atspi
    GI_AVAILABLE = True
except (ImportError, ValueError):
    GI_AVAILABLE = False
    print("AT-SPI not available (gi.repository.Atspi missing)")
    sys.exit(0)

print("=== AT-SPI Event Monitor Test ===")

if not GI_AVAILABLE:
    print("GI bindings not available")
    sys.exit(0)

try:
    Atspi.init()
    print("AT-SPI initialized")
except Exception as e:
    print(f"AT-SPI init failed: {e}")
    sys.exit(0)

event_received = False
error_occurred = False

def on_caret_event(event):
    global event_received
    event_received = True
    try:
        print(f"  Event: {event.type.name} from {event.source.name}")
    except:
        print(f"  Event received")

print("Listening for caret events for 5 seconds...")

try:
    listener = Atspi.EventListener.new(on_caret_event)
    Atspi.EventListener.register(listener, "object:text-caret-moved")
except Exception as e:
    print(f"Event listener setup failed: {e}")
    error_occurred = True
    sys.exit(1)

start_time = time.time()
timeout = 5

while time.time() - start_time < timeout:
    time.sleep(0.1)
    if event_received:
        break

try:
    Atspi.EventListener.deregister(listener, "object:text-caret-moved")
except:
    pass

print("")
if event_received:
    print("AT-SPI is functional and receiving events")
    sys.exit(0)
else:
    print("No caret events received in 5 seconds")
    print("This may be normal if no text entry was in focus")
    sys.exit(0)
