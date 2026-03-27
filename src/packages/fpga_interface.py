import os
import mmap
import struct

# Base address (must be page-aligned!)
BASE_ADDR = 0x40000000
OFFSET = 0xC8  # your register offset

PAGE_SIZE = mmap.PAGESIZE
MAP_SIZE = PAGE_SIZE

class FPGAInterface:
    def __init__(self, base_addr=BASE_ADDR, map_size=MAP_SIZE):
        self.base_addr = base_addr
        self.map_size = map_size
        self.mem = None
       

    def map_memory(self):
        with open("/dev/mem", "r+b") as f:
            self.mem = mmap.mmap(
                f.fileno(),
                self.map_size,
                offset=self.base_addr
            )

    # Parse the .fpg file to get register names and offsets, and store in a dictionary
    def load_register_map(self, register_map):
        with open(register_map, "r") as f:
            self.register_map = {}
            for line in f:
                if line.strip() and line.startswith("?register"):
                    data = line.split(" ")
                    self.register_map[data[1].strip()] = int(data[2].strip(), 0)
    
    def write_int(self, offset, value):
        if self.mem is None:
            raise RuntimeError("Memory not mapped")
        if offset < 0 or offset + 4 > self.map_size:
            raise ValueError("Offset out of bounds")
        
        self.mem[offset:offset+4] = struct.pack("<I", value)
    

    
    
    # # Write 42 to offset 0xC8
    # mem[OFFSET:OFFSET+4] = struct.pack("<I", 42)

    # # Read back
    # value = struct.unpack("<I", mem[OFFSET:OFFSET+4])[0]
    # print(value)

    # mem.close()