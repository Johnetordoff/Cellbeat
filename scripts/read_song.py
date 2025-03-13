import struct

# XM note lookup table
NOTE_NAMES = ["C-", "C#", "D-", "D#", "E-", "F-", "F#", "G-", "G#", "A-", "A#", "B-"]

def note_to_string(note):
    """Convert note number (1-96) to readable format (C-4, D#5, etc.)."""
    if note == 0:
        return "---"  # No note
    note -= 1  # Shift to 0-based
    octave = note // 12
    note_name = NOTE_NAMES[note % 12]
    return f"{note_name}{octave}"

class XMParser:
    def __init__(self, filename):
        self.filename = filename
        self.file_data = None
        self.header = {}
        self.patterns = []

    def read_xm_file(self):
        """Reads the entire .xm file into memory."""
        with open(self.filename, "rb") as f:
            self.file_data = f.read()

    def parse_header(self):
        """Parses the XM header information."""
        if self.file_data is None:
            raise ValueError("File data is not loaded. Call read_xm_file() first.")

        # XM header structure
        self.header["id_text"] = self.file_data[:17].decode("ascii").strip("\x00")
        self.header["module_name"] = self.file_data[17:37].decode("ascii").strip("\x00")
        self.header["tracker_name"] = self.file_data[38:58].decode("ascii").strip("\x00")
        self.header["version"] = struct.unpack("<H", self.file_data[58:60])[0] / 0x100
        self.header["header_size"] = struct.unpack("<I", self.file_data[60:64])[0]
        self.header["song_length"] = struct.unpack("<H", self.file_data[64:66])[0]
        self.header["restart_position"] = struct.unpack("<H", self.file_data[66:68])[0]
        self.header["num_channels"] = struct.unpack("<H", self.file_data[68:70])[0]
        self.header["num_patterns"] = struct.unpack("<H", self.file_data[70:72])[0]
        self.header["num_instruments"] = struct.unpack("<H", self.file_data[72:74])[0]
        self.header["flags"] = struct.unpack("<H", self.file_data[74:76])[0]
        self.header["tempo"] = struct.unpack("<H", self.file_data[76:78])[0]
        self.header["bpm"] = struct.unpack("<H", self.file_data[78:80])[0]

    def parse_patterns(self):
        """Parses the pattern data to extract notes."""
        if self.file_data is None:
            raise ValueError("File data is not loaded. Call read_xm_file() first.")

        offset = 60 + self.header["header_size"]
        self.patterns = []

        for pattern_idx in range(self.header["num_patterns"]):
            pattern_header_length = struct.unpack("<I", self.file_data[offset : offset + 4])[0]
            num_rows = struct.unpack("<H", self.file_data[offset + 5 : offset + 7])[0]
            packed_size = struct.unpack("<H", self.file_data[offset + 7 : offset + 9])[0]
            pattern_data_offset = offset + pattern_header_length

            pattern = []
            pattern_data = self.file_data[pattern_data_offset : pattern_data_offset + packed_size]
            pattern_offset = 0

            for _ in range(num_rows):
                row = []
                for _ in range(self.header["num_channels"]):
                    note, instr, vol, effect, effect_param = (0, 0, 0, 0, 0)
                    first_byte = pattern_data[pattern_offset]
                    pattern_offset += 1

                    if first_byte & 0x80:  # Compressed note data
                        if first_byte & 0x01:
                            note = pattern_data[pattern_offset]
                            pattern_offset += 1
                        if first_byte & 0x02:
                            instr = pattern_data[pattern_offset]
                            pattern_offset += 1
                        if first_byte & 0x04:
                            vol = pattern_data[pattern_offset]
                            pattern_offset += 1
                        if first_byte & 0x08:
                            effect = pattern_data[pattern_offset]
                            pattern_offset += 1
                        if first_byte & 0x10:
                            effect_param = pattern_data[pattern_offset]
                            pattern_offset += 1
                    else:  # Uncompressed
                        note = first_byte
                        instr = pattern_data[pattern_offset]
                        vol = pattern_data[pattern_offset + 1]
                        effect = pattern_data[pattern_offset + 2]
                        effect_param = pattern_data[pattern_offset + 3]
                        pattern_offset += 4

                    row.append((note_to_string(note), instr, vol, effect, effect_param))
                pattern.append(row)

            self.patterns.append(pattern)
            offset = pattern_data_offset + packed_size

    def display_info(self):
        """Displays the parsed XM file information."""
        print(f"Title: {self.header['module_name']}")
        print(f"Tracker: {self.header['tracker_name']}")
        print(f"Version: {self.header['version']}")
        print(f"Channels: {self.header['num_channels']}")
        print(f"Patterns: {self.header['num_patterns']}")
        print(f"Instruments: {self.header['num_instruments']}")
        print(f"Tempo: {self.header['tempo']}")
        print(f"BPM: {self.header['bpm']}")

    def display_patterns(self):
        """Displays extracted pattern data in readable music notation."""
        for pattern_idx, pattern in enumerate(self.patterns):
            print(f"\n=== Pattern {pattern_idx} ===")
            for row_idx, row in enumerate(pattern):
                row_str = f"{row_idx:02d} | "
                for note, instr, vol, effect, effect_param in row:
                    row_str += f"{note} | "
                print(row_str)

    def parse(self):
        """Parses the XM file and displays notation."""
        self.read_xm_file()
        self.parse_header()
        self.parse_patterns()
        self.display_info()
        self.display_patterns()


if __name__ == "__main__":
    filename = input("Enter the .xm file path: ")
    parser = XMParser(filename)
    parser.parse()
