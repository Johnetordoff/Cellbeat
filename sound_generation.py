import wave
import struct
import math
import random
import sys
import subprocess


def generate_wave(filename, waveform="sine", frequency=1000, duration=1.0, decay=1, sample_rate=44100, amplitude=32767):
    """
    Generate a sound file with the specified waveform and play it immediately.

    :param filename: Output filename for the generated WAV file.
    :param waveform: Type of waveform ("sine", "square", "sawtooth", "triangle", "am", "fm", "harmonic", "noise",
                     "pwm", "chorus", "ringmod", "detuned", "binaural").
    :param frequency: Base frequency of the sound in Hz.
    :param duration: Duration of the sound in seconds.
    :param decay: Exponential decay rate (higher = faster decay).
    :param sample_rate: Sample rate in Hz (default is 44100 Hz).
    :param amplitude: Maximum amplitude (default is 32767 for 16-bit PCM).
    """
    num_samples = int(sample_rate * duration)
    samples = []

    for i in range(num_samples):
        t = i / sample_rate  # Time in seconds
        env = math.exp(-decay * (t / duration))  # Normalized decay

        if waveform == "sine":
            value = amplitude * env * math.sin(2.0 * math.pi * frequency * t)

        elif waveform == "square":
            value = amplitude * env * (1 if math.sin(2.0 * math.pi * frequency * t) >= 0 else -1)

        elif waveform == "sawtooth":
            value = amplitude * env * (2 * (t * frequency - math.floor(0.5 + t * frequency)))

        elif waveform == "triangle":
            value = amplitude * env * (2 * abs(2 * (t * frequency - math.floor(0.5 + t * frequency))) - 1)

        elif waveform == "am":  # Amplitude Modulation (Tremolo effect)
            modulator = 0.5 * (1 + math.sin(2.0 * math.pi * 5 * t))  # 5 Hz tremolo effect
            value = amplitude * env * modulator * math.sin(2.0 * math.pi * frequency * t)

        elif waveform == "fm":  # Frequency Modulation
            mod_freq = 1  # Modulation frequency
            mod_index = 1  # Modulation depth
            mod_signal = mod_index * math.sin(2.0 * math.pi * mod_freq * t)
            value = amplitude * env * math.sin(2.0 * math.pi * (frequency + mod_signal) * t)

        elif waveform == "harmonic":  # Sum of sine waves at different harmonics
            value = amplitude * env * (
                0.6 * math.sin(2.0 * math.pi * frequency * t) +  # Fundamental
                0.3 * math.sin(2.0 * math.pi * 2 * frequency * t) +  # 2nd Harmonic
                0.1 * math.sin(2.0 * math.pi * 3 * frequency * t)  # 3rd Harmonic
            )

        elif waveform == "pwm":  # Pulse Width Modulation (PWM)
            duty_cycle = 0.5 + 0.2 * math.sin(2.0 * math.pi * 5 * t)  # Modulated duty cycle
            value = amplitude * env * (1 if math.sin(2.0 * math.pi * frequency * t) > duty_cycle else -1)

        elif waveform == "chorus":  # Chorus effect (slightly detuned oscillators)
            detune = 2  # Hz detune
            value = amplitude * env * (
                0.5 * math.sin(2.0 * math.pi * frequency * t) +
                0.3 * math.sin(2.0 * math.pi * (frequency + detune) * t) +
                0.2 * math.sin(2.0 * math.pi * (frequency - detune) * t)
            )

        elif waveform == "ringmod":  # Ring Modulation (multiplication of two sine waves)
            mod_freq = frequency * 0.5  # Modulation frequency at half the main frequency
            mod_signal = math.sin(2.0 * math.pi * mod_freq * t)
            value = amplitude * env * mod_signal * math.sin(2.0 * math.pi * frequency * t)

        elif waveform == "detuned":  # Slightly detuned harmonics
            value = amplitude * env * (
                0.5 * math.sin(2.0 * math.pi * frequency * t) +
                0.3 * math.sin(2.0 * math.pi * (frequency * 1.01) * t) +
                0.2 * math.sin(2.0 * math.pi * (frequency * 0.99) * t)
            )

        elif waveform == "binaural":  # Binaural beats (stereo effect, requires headphones)
            left_freq = frequency
            right_freq = frequency + 5  # Slightly different frequency in the right ear
            value = amplitude * env * (
                0.5 * math.sin(2.0 * math.pi * left_freq * t) +
                0.5 * math.sin(2.0 * math.pi * right_freq * t)
            )

        elif waveform == "noise":
            value = amplitude * env * (random.uniform(-1, 1))  # White noise

        else:
            raise ValueError("Invalid waveform type. Choose from available types.")

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
    # Generate and play long-duration waveforms
    # generate_wave("bell_harmonic.wav", waveform="harmonic", frequency=100)  # Harmonic Blend
    # generate_wave("bell_harmonic.wav", waveform="harmonic", frequency=200, duration=1)  # Harmonic Blend
    # generate_wave("bell_square.wav", waveform="square", frequency=100)
    # generate_wave("bell_sawtooth.wav", waveform="sawtooth", frequency=100)
    # generate_wave("bell_triangle.wav", waveform="triangle")
    # generate_wave("bell_am.wav", waveform="am")  # Amplitude Modulation
    generate_wave("bell_fm.wav", waveform="fm", duration=1, frequency=200)  # Frequency Modulation
    generate_wave("bell_fm.wav", waveform="am", duration=1, frequency=200)  # Frequency Modulation
    # generate_wave("bell_noise.wav", waveform="noise")  # White noise
    # generate_wave("bell_pwm.wav", waveform="pwm")
    # generate_wave("bell_chorus.wav", waveform="chorus")
    # generate_wave("bell_ringmod.wav", waveform="ringmod")
    # generate_wave("bell_detuned.wav", waveform="detuned")
    # generate_wave("bell_binaural.wav", waveform="binaural")
