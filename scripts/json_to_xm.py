import json
import struct

# XM note lookup table
NOTE_NAMES = ["C-", "C#", "D-", "D#", "E-", "F-", "F#", "G-", "G#", "A-", "A#", "B-"]

def note_from_string(note):
    """Convert readable note format (C-4, D#5, etc.) to XM note number (1-96)."""
    if note == "---":
        return 0  # No note
    note_name = note[:2]
    octave = int(note[2])
    if note_name in NOTE_NAMES:
        return (octave * 12) + NOTE_NAMES.index(note_name) + 1
    return 0

class JSONToXM:
    def __init__(self, json_file, output_file):
        self.json_file = json_file
        self.output_file = output_file
        self.data = None

    def read_json(self):
        """Reads the JSON file into memory."""
        with open(self.json_file, "r", encoding="utf-8") as f:
            self.data = json.load(f)

    def write_xm_file(self):
        """Writes the XM file based on parsed JSON data."""
        if self.data is None:
            raise ValueError("JSON data not loaded. Call read_json() first.")

        with open(self.output_file, "wb") as f:
            # Write Header
            f.write(self.data["header"]["id_text"].ljust(17, "\x00").encode("ascii"))
            f.write(self.data["header"]["module_name"].ljust(20, "\x00").encode("ascii"))
            f.write(bytes([0x1A]))  # XM identifier byte
            f.write(self.data["header"]["tracker_name"].ljust(20, "\x00").encode("ascii"))
            f.write(struct.pack("<H", int(self.data["header"]["version"] * 256)))
            f.write(struct.pack("<I", self.data["header"]["header_size"]))
            f.write(struct.pack("<H", self.data["header"]["song_length"]))  # Number of patterns in order list
            f.write(struct.pack("<H", self.data["header"]["restart_position"]))
            f.write(struct.pack("<H", self.data["header"]["num_channels"]))
            f.write(struct.pack("<H", self.data["header"]["num_patterns"]))  # Actual number of patterns
            f.write(struct.pack("<H", self.data["header"]["num_instruments"]))
            f.write(struct.pack("<H", self.data["header"]["flags"]))
            f.write(struct.pack("<H", self.data["header"]["tempo"]))
            f.write(struct.pack("<H", self.data["header"]["bpm"]))

            # Pattern Order Table
            order_table_size = 256  # XM requires 256 bytes for the pattern order table
            order_table = [i for i in range(self.data["header"]["song_length"])]  # Sequential order
            order_table += [0] * (order_table_size - len(order_table))  # Fill remaining space
            f.write(bytes(order_table))

            # Write Patterns
            for pattern in self.data["patterns"]:
                num_rows = len(pattern)  # Number of rows per pattern
                packed_data = b""

                for row in pattern:
                    for note_data in row:
                        note = note_from_string(note_data["note"])
                        instr = note_data["instrument"]
                        vol = note_data["volume"]
                        effect = note_data["effect"]
                        effect_param = note_data["effect_param"]

                        # Pack pattern data properly
                        packed_data += struct.pack("BBBBB", note, instr, vol, effect, effect_param)

                # Write pattern header
                pattern_header_size = 9  # Fixed size for each pattern header
                packed_size = len(packed_data)

                f.write(struct.pack("<I", pattern_header_size))  # Header size
                f.write(struct.pack("<B", 0))  # Packing type (always 0)
                f.write(struct.pack("<H", num_rows))  # Number of rows in pattern
                f.write(struct.pack("<H", packed_size))  # Packed data size

                # Write pattern data
                f.write(packed_data)

            # Write Instruments (XM requires proper instrument headers)
            for i in range(self.data["header"]["num_instruments"]):
                instrument_name = f"Instrument {i+1}"
                f.write(instrument_name.ljust(22, "\x00").encode("ascii"))  # Instrument name (22 bytes)
                f.write(struct.pack("<B", 0))  # Instrument type (always 0)
                f.write(struct.pack("<H", 33))  # Instrument size (fixed for now)

                # Sample Mapping: Map sample 1-to-1 for now
                f.write(struct.pack("<B", 1))  # Number of samples
                f.write(bytes([0] * 96))  # Sample map (no actual mapping)
                f.write(bytes([0] * 48))  # Volume & panning envelopes
                f.write(struct.pack("<B", 0))  # Volume envelope points
                f.write(struct.pack("<B", 0))  # Panning envelope points
                f.write(bytes([0] * 11))  # Unused fields

                # Sample Header
                sample_length = 500  # Placeholder length
                loop_start = 0
                loop_length = 0
                volume = 64  # Full volume
                finetune = 0
                sample_type = 0  # No looping
                panning = 128  # Centered
                relative_note = 0  # No transposition

                f.write(struct.pack("<I", sample_length))  # Sample length
                f.write(struct.pack("<I", loop_start))  # Loop start
                f.write(struct.pack("<I", loop_length))  # Loop length
                f.write(struct.pack("<B", volume))  # Volume
                f.write(struct.pack("<b", finetune))  # Finetune
                f.write(struct.pack("<B", sample_type))  # Sample type
                f.write(struct.pack("<B", panning))  # Panning
                f.write(struct.pack("<b", relative_note))  # Relative note
                f.write(struct.pack("<B", 0))  # Reserved

                # Placeholder sample data (silence)
                f.write(bytes(sample_length))

        print(f"🎵 XM file successfully created: {self.output_file}")

    def convert(self):
        """Reads JSON and writes XM file."""
        self.read_json()
        self.write_xm_file()


if __name__ == "__main__":
    json_filename = input("Enter the JSON file path: ")
    xm_filename = input("Enter the output .xm file path: ")
    converter = JSONToXM(json_filename, xm_filename)
    converter.convert()
