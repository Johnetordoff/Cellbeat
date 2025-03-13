import wave
import struct
import math
import random
import sys
import subprocess


def generate_pitch_variation_wave(filename, waveform="sine", start_freq=400, end_freq=800, duration=1.0,
                                  pitch_curve="linear", vibrato_rate=0, vibrato_depth=0, decay=2,
                                  sample_rate=44100, amplitude=32767):
    """
    Generate a sound file with a gradual pitch change and play it.

    :param filename: Output filename for the generated WAV file.
    :param waveform: Type of waveform ("sine", "square", "sawtooth", "triangle", "fm", "harmonic").
    :param start_freq: Starting frequency of the sound in Hz.
    :param end_freq: Ending frequency of the sound in Hz.
    :param duration: Duration of the sound in seconds.
    :param pitch_curve: Type of pitch transition ("linear", "exponential").
    :param vibrato_rate: Frequency of vibrato modulation (Hz).
    :param vibrato_depth: Amount of vibrato in Hz.
    :param decay: Exponential decay rate (higher = faster decay).
    :param sample_rate: Sample rate in Hz.
    :param amplitude: Maximum amplitude for 16-bit PCM.
    """
    num_samples = int(sample_rate * duration)
    samples = []

    for i in range(num_samples):
        t = i / sample_rate  # Time in seconds
        env = math.exp(-decay * t)  # Exponential decay envelope

        # Compute frequency change based on the selected curve
        if pitch_curve == "linear":
            frequency = start_freq + (end_freq - start_freq) * (i / num_samples)
        elif pitch_curve == "exponential":
            frequency = start_freq * ((end_freq / start_freq) ** (i / num_samples))
        else:
            raise ValueError("Invalid pitch curve. Choose 'linear' or 'exponential'.")

        # Apply vibrato modulation
        if vibrato_rate > 0 and vibrato_depth > 0:
            frequency += vibrato_depth * math.sin(2.0 * math.pi * vibrato_rate * t)

        # Generate waveform samples
        if waveform == "sine":
            value = amplitude * env * math.sin(2.0 * math.pi * frequency * t)

        elif waveform == "square":
            value = amplitude * env * (1 if math.sin(2.0 * math.pi * frequency * t) >= 0 else -1)

        elif waveform == "sawtooth":
            value = amplitude * env * (2 * (t * frequency - math.floor(0.5 + t * frequency)))

        elif waveform == "triangle":
            value = amplitude * env * (2 * abs(2 * (t * frequency - math.floor(0.5 + t * frequency))) - 1)

        elif waveform == "fm":  # Frequency Modulation
            mod_freq = 10  # Modulation frequency
            mod_index = 50  # Modulation depth
            mod_signal = mod_index * math.sin(2.0 * math.pi * mod_freq * t)
            value = amplitude * env * math.sin(2.0 * math.pi * (frequency + mod_signal) * t)

        elif waveform == "harmonic":  # Sum of sine waves at different harmonics
            value = amplitude * env * (
                0.6 * math.sin(2.0 * math.pi * frequency * t) +  # Fundamental
                0.3 * math.sin(2.0 * math.pi * 2 * frequency * t) +  # 2nd Harmonic
                0.1 * math.sin(2.0 * math.pi * 3 * frequency * t)  # 3rd Harmonic
            )

        else:
            raise ValueError("Invalid waveform type. Choose from 'sine', 'square', 'sawtooth', 'triangle', 'fm', 'harmonic'.")

        samples.append(struct.pack('<h', int(value)))  # Convert to 16-bit PCM

    # Write the WAV file
    with wave.open(filename, "wb") as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 16-bit PCM
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(b''.join(samples))  # Write data

    # Play the generated sound
    play_wave(filename)


def play_wave(filename):
    """ Plays a WAV file using the system's default player. """
    try:
        if sys.platform.startswith("darwin"):  # macOS
            subprocess.run(["afplay", filename], check=True)
        elif sys.platform.startswith("linux"):  # Linux
            subprocess.run(["aplay", filename], check=True)
        elif sys.platform.startswith("win"):  # Windows
            subprocess.run(["cmd", "/c", "start", filename], shell=True, check=True)
        else:
            print(f"Unsupported OS: Cannot play {filename} automatically.")
    except Exception as e:
        print(f"Error playing {filename}: {e}")


if __name__ == "__main__":
    # Generate and play waveforms with gradual pitch changes
    generate_pitch_variation_wave("glide_linear.wav", waveform="sine", start_freq=100, end_freq=1000,  pitch_curve="exponential")
    generate_pitch_variation_wave("glide_linear.wav", waveform="sine", start_freq=100, end_freq=1000,  pitch_curve="linear")
    generate_pitch_variation_wave("glide_linear.wav", waveform="sawtooth", start_freq=100, end_freq=1000,  pitch_curve="exponential")
    generate_pitch_variation_wave("glide_linear.wav", waveform="sawtooth", start_freq=100, end_freq=1000,  pitch_curve="linear")
    generate_pitch_variation_wave("glide_linear.wav", waveform="triangle", start_freq=100, end_freq=1000, pitch_curve="exponential")
    generate_pitch_variation_wave("glide_linear.wav", waveform="triangle", start_freq=100, end_freq=1000, pitch_curve="linear")
    generate_pitch_variation_wave("glide_linear.wav", waveform="square", start_freq=100, end_freq=1000,  pitch_curve="exponential")
    generate_pitch_variation_wave("glide_linear.wav", waveform="square", start_freq=100, end_freq=1000,  pitch_curve="linear")
    generate_pitch_variation_wave("glide_linear.wav", waveform="harmonic", start_freq=100, end_freq=1000,  pitch_curve="exponential")
    generate_pitch_variation_wave("glide_linear.wav", waveform="harmonic", start_freq=100, end_freq=1000,  pitch_curve="linear")
    generate_pitch_variation_wave("glide_linear.wav", waveform="fm", start_freq=100, end_freq=1000,  pitch_curve="exponential")
    generate_pitch_variation_wave("glide_linear.wav", waveform="fm", start_freq=100, end_freq=1000,  pitch_curve="linear")
    # generate_pitch_variation_wave("glide_exponential.wav", waveform="sawtooth", start_freq=200, end_freq=800, duration=2, pitch_curve="exponential")
    # generate_pitch_variation_wave("vibrato_sine.wav", waveform="sine", start_freq=500, end_freq=500, duration=2, vibrato_rate=5, vibrato_depth=20)
    # generate_pitch_variation_wave("vibrato_triangle.wav", waveform="triangle", start_freq=400, end_freq=400, duration=2, vibrato_rate=6, vibrato_depth=30)
    # generate_pitch_variation_wave("glide_fm.wav", waveform="fm", start_freq=300, end_freq=900, duration=2, pitch_curve="linear")
