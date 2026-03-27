import os
import mmap
import struct

# Base address (must be page-aligned!)
BASE_ADDR = 0x40000000
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
    def load_register_map(self, register_map_dir, debug=False):
        try:
            with open(register_map_dir, "r", errors = "ignore") as f:
                self.register_map = {}
                for line in f:
                    if debug:
                        print(line)
                    if line.strip() and line.startswith("?register"):
                        data = line.split("\t")
                        self.register_map[data[1].strip()] = int(data[2].strip(), 0)
                    elif line.strip() and line.startswith("?quit"):
                        if debug:
                            print("Successfully finished parsing")
                        break
            return True
        except Exception as e:
            print(f"Error loading register map: {e}")
            return False
            
            
        
    def write_register(self, register_name, value):
        if register_name not in self.register_map:
            raise ValueError(f"Register {register_name} not found in register map")
        mem_loc = self.register_map[register_name]
        relative_loc = mem_loc - self.base_addr
        self.mem[relative_loc:relative_loc+4] = struct.pack("<I", value)
        
        # checking that the value was written correctly
        read_value = self.read_register(register_name)
        if read_value != value:
            raise ValueError(f"Value {value} was not written correctly to register {register_name}, read back {read_value}")
        else:
            return True

    def read_register(self, register_name):
        if register_name not in self.register_map:
            raise ValueError(f"Register {register_name} not found in register map")
        mem_loc = self.register_map[register_name]
        relative_loc = mem_loc - self.base_addr
        return struct.unpack("<I", self.mem[relative_loc:relative_loc+4])[0]
    
    
    # # Write 42 to offset 0xC8
    # mem[OFFSET:OFFSET+4] = struct.pack("<I", 42)

    # # Read back
    # value = struct.unpack("<I", mem[OFFSET:OFFSET+4])[0]
    # print(value)

    # mem.close()