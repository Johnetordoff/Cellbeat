#include <Python.h>
#include <AudioToolbox/AudioToolbox.h>
#include <pthread.h>
#include <unistd.h>
#include <math.h>
#include <stdlib.h>
#include <stdio.h>
#include <stdint.h>
#include <string.h>

#define SAMPLE_RATE 44100
#define PI 3.14159265358979323846
#define MAX_VOLUME 32767
#define MAX_POLYPHONY 16
#define NUM_BUFFERS 3
#define BUFFER_SIZE 1024
#define MAX_HARMONICS 100

#define ATTACK_TIME 0.001
#define DECAY_TIME  0.04
#define SUSTAIN_LEVEL 0.2
#define RELEASE_TIME 0.2
#define CLIP_THRESHOLD 0.95

typedef struct {
    int active;
    double frequency;
    double duration;
    double phase;
    double phase_increment;
    double elapsedTime;
    int num_harmonics;
    double harmonic_weights[MAX_HARMONICS];
} Voice;

typedef struct {
    AudioQueueRef queue;
    AudioQueueBufferRef buffers[NUM_BUFFERS];
    Voice voices[MAX_POLYPHONY];
    pthread_mutex_t voice_mutex;
    FILE *wav_file;
    uint32_t total_samples_written;
    int recording;
} Synth;

Synth synth;

void write_wav_header(FILE *file, uint32_t sample_rate, uint16_t bits_per_sample, uint16_t channels);
void finalize_wav_file(FILE *file, uint32_t total_samples);
void* synth_thread(void* args);
void audio_callback_synth(void* userData, AudioQueueRef queue, AudioQueueBufferRef buffer);
double adsr_envelope(Voice *voice);
double soft_clip(double sample);
void play_tone(double freq, double duration, double* harmonics, int num_harmonics, int velocity);
void start_recording(const char *filename);
void stop_recording(void);

double adsr_envelope(Voice *voice) {
    double time = voice->elapsedTime;
    if (time < ATTACK_TIME)
        return time / ATTACK_TIME;
    else if (time < ATTACK_TIME + DECAY_TIME)
        return 1.0 - (1.0 - SUSTAIN_LEVEL) * ((time - ATTACK_TIME) / DECAY_TIME);
    else if (time < voice->duration - RELEASE_TIME)
        return SUSTAIN_LEVEL;
    else if (time < voice->duration)
        return SUSTAIN_LEVEL * (1.0 - (time - (voice->duration - RELEASE_TIME)) / RELEASE_TIME);
    else
        return 0.0;
}

double soft_clip(double sample) {
    double threshold = CLIP_THRESHOLD;
    if (sample > threshold)
        sample = threshold + (sample - threshold) / (1.0 + pow((sample - threshold) / (1.0 - threshold), 2));
    else if (sample < -threshold)
        sample = -threshold + (sample + threshold) / (1.0 + pow((sample + threshold) / (1.0 - threshold), 2));
    return sample;
}

void* synth_thread(void* args) {
    AudioStreamBasicDescription format = {
        .mSampleRate = SAMPLE_RATE,
        .mFormatID = kAudioFormatLinearPCM,
        .mFormatFlags = kLinearPCMFormatFlagIsSignedInteger | kLinearPCMFormatFlagIsPacked,
        .mFramesPerPacket = 1,
        .mChannelsPerFrame = 1,
        .mBitsPerChannel = 16,
        .mBytesPerPacket = 2,
        .mBytesPerFrame = 2
    };

    OSStatus status = AudioQueueNewOutput(&format, audio_callback_synth, &synth, NULL, NULL, 0, &synth.queue);
    if (status != noErr) {
        printf("AudioQueueNewOutput error: %d\n", (int)status);
        return NULL;
    }

    for (int i = 0; i < NUM_BUFFERS; i++) {
        AudioQueueAllocateBuffer(synth.queue, BUFFER_SIZE * sizeof(int16_t), &synth.buffers[i]);
        audio_callback_synth(&synth, synth.queue, synth.buffers[i]);
    }

    AudioQueueStart(synth.queue, NULL);
    while (1) sleep(1);
    return NULL;
}

void play_tone(double freq, double duration, double* harmonics, int num_harmonics, int velocity) {
    if (num_harmonics > MAX_HARMONICS) num_harmonics = MAX_HARMONICS;

    pthread_mutex_lock(&synth.voice_mutex);
    for (int v = 0; v < MAX_POLYPHONY; v++) {
        if (!synth.voices[v].active) {
            Voice *voice = &synth.voices[v];
            voice->active = 1;
            voice->frequency = freq;
            voice->duration = duration;
            voice->phase = ((double)rand() / RAND_MAX) * 2.0 * PI;  // Random phase for realism
            voice->phase_increment = 2.0 * PI * freq / SAMPLE_RATE;
            voice->elapsedTime = 0.0;
            voice->num_harmonics = num_harmonics;
            double velocity_scale = fmin(fmax(velocity / 127.0, 0.0), 1.0);
            for (int i = 0; i < num_harmonics; i++)
                voice->harmonic_weights[i] = harmonics[i] * velocity_scale;
            printf("Playing tone %.2f Hz with %d harmonics\n", freq, num_harmonics);
            break;
        }
    }
    pthread_mutex_unlock(&synth.voice_mutex);
}

void audio_callback_synth(void* userData, AudioQueueRef queue, AudioQueueBufferRef buffer) {
    Synth *s = (Synth*)userData;
    int16_t* samples = (int16_t*)buffer->mAudioData;
    int frames = buffer->mAudioDataBytesCapacity / 2;

    memset(samples, 0, frames * sizeof(int16_t));
    pthread_mutex_lock(&s->voice_mutex);

    // Generate all voices into samples
    for (int v = 0; v < MAX_POLYPHONY; v++) {
        Voice *voice = &s->voices[v];
        if (!voice->active) continue;

        for (int i = 0; i < frames; i++) {
            if (voice->elapsedTime >= voice->duration) {
                voice->active = 0;
                break;
            }

            double env = adsr_envelope(voice);
            double val = 0.0;

            for (int h = 0; h < voice->num_harmonics; h++) {
                val += voice->harmonic_weights[h] * sin((h + 1) * voice->phase);
            }

            val *= env;

            int32_t sample_val = samples[i];
            sample_val += (int32_t)(val * (MAX_VOLUME / MAX_POLYPHONY));
            samples[i] = (int16_t)(soft_clip(sample_val / (double)MAX_VOLUME) * MAX_VOLUME);

            voice->phase += voice->phase_increment;
            if (voice->phase >= 2.0 * PI) voice->phase -= 2.0 * PI;
            voice->elapsedTime += 1.0 / SAMPLE_RATE;
        }
    }

    pthread_mutex_unlock(&s->voice_mutex);

    buffer->mAudioDataByteSize = frames * sizeof(int16_t);
    AudioQueueEnqueueBuffer(queue, buffer, 0, NULL);

    // ✅ Now write entire buffer to WAV file after mixing all voices
    if (s->recording && s->wav_file) {
        fwrite(samples, sizeof(int16_t), frames, s->wav_file);
        s->total_samples_written += frames;
    }
}

void start_recording(const char *filename) {
    if (synth.recording) return;
    synth.wav_file = fopen(filename, "wb");
    if (!synth.wav_file) return;
    synth.total_samples_written = 0;
    synth.recording = 1;
    write_wav_header(synth.wav_file, SAMPLE_RATE, 16, 1);
}

void stop_recording() {
    if (!synth.recording) return;
    synth.recording = 0;
    finalize_wav_file(synth.wav_file, synth.total_samples_written);
    fclose(synth.wav_file);
    synth.wav_file = NULL;
}

void write_wav_header(FILE *file, uint32_t sample_rate, uint16_t bits_per_sample, uint16_t channels) {
    uint32_t byte_rate = sample_rate * channels * bits_per_sample / 8;
    uint16_t block_align = channels * bits_per_sample / 8;
    fwrite("RIFF", 1, 4, file);
    uint32_t chunk_size = 0;
    fwrite(&chunk_size, 4, 1, file);
    fwrite("WAVE", 1, 4, file);
    fwrite("fmt ", 1, 4, file);
    uint32_t subchunk1_size = 16;
    fwrite(&subchunk1_size, 4, 1, file);
    uint16_t audio_format = 1;
    fwrite(&audio_format, 2, 1, file);
    fwrite(&channels, 2, 1, file);
    fwrite(&sample_rate, 4, 1, file);
    fwrite(&byte_rate, 4, 1, file);
    fwrite(&block_align, 2, 1, file);
    fwrite(&bits_per_sample, 2, 1, file);
    fwrite("data", 1, 4, file);
    uint32_t data_chunk_size = 0;
    fwrite(&data_chunk_size, 4, 1, file);
}

void finalize_wav_file(FILE *file, uint32_t total_samples) {
    uint32_t data_chunk_size = total_samples * sizeof(int16_t);
    uint32_t chunk_size = 36 + data_chunk_size;
    fseek(file, 4, SEEK_SET);
    fwrite(&chunk_size, 4, 1, file);
    fseek(file, 40, SEEK_SET);
    fwrite(&data_chunk_size, 4, 1, file);
}

static PyObject* py_play_tone(PyObject* self, PyObject* args) {
    double freq, duration;
    int velocity;
    PyObject* harmonic_list;

    if (!PyArg_ParseTuple(args, "ddiO", &freq, &duration, &velocity, &harmonic_list))
        return NULL;

    if (!PyList_Check(harmonic_list)) return NULL;

    int count = PyList_Size(harmonic_list);
    if (count > MAX_HARMONICS) count = MAX_HARMONICS;

    double weights[MAX_HARMONICS];
    for (int i = 0; i < count; i++) {
        PyObject* item = PyList_GetItem(harmonic_list, i);
        weights[i] = PyFloat_AsDouble(item);
    }

    play_tone(freq, duration, weights, count, velocity);
    Py_RETURN_NONE;
}

static PyObject* py_start_recording(PyObject* self, PyObject* args) {
    const char* filename;
    if (!PyArg_ParseTuple(args, "s", &filename)) return NULL;
    start_recording(filename);
    Py_RETURN_NONE;
}

static PyObject* py_stop_recording(PyObject* self, PyObject* args) {
    stop_recording();
    Py_RETURN_NONE;
}

static PyMethodDef AudioMethods[] = {
    {"play_tone", py_play_tone, METH_VARARGS, "Play tone with harmonic weights."},
    {"start_recording", py_start_recording, METH_VARARGS, "Start recording to WAV file."},
    {"stop_recording", py_stop_recording, METH_VARARGS, "Stop recording."},
    {NULL, NULL, 0, NULL}
};

static struct PyModuleDef audiomodule = {
    PyModuleDef_HEAD_INIT, "audio", NULL, -1, AudioMethods
};

PyMODINIT_FUNC PyInit_audio(void) {
    pthread_mutex_init(&synth.voice_mutex, NULL);
    memset(synth.voices, 0, sizeof(synth.voices));
    synth.recording = 0;
    synth.wav_file = NULL;
    pthread_t thread;
    pthread_create(&thread, NULL, synth_thread, NULL);
    pthread_detach(thread);
    return PyModule_Create(&audiomodule);
}
