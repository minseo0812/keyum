import random
import time
from collections import deque

import numpy as np
import pygame
from pynput import keyboard

# ── 설정 ─────────────────────────────────────────
DEBUG = False            # True: 소리가 안 나는 키 이름을 터미널에 보여줌 (원인 찾을 때만)
SOUND_MODIFIERS = True   # False: Shift/Ctrl/Alt/Win 등은 소리 없음

MASTER_VOLUME = 0.30     # 전체 소리 크기 (0~1). 더 조용하게 하려면 낮추세요
REVERB_AMOUNT = 0.45     # 울림(페달 느낌) 정도 (0~1). 0이면 울림 없음
ATTACK = 0.015           # 소리가 시작될 때 올라오는 시간(초). 클수록 더 부드럽고 몽글해요
CHORD_STEPS = (0, 2, 4)  # 한 번 칠 때 같이 울리는 음 (0만 두면 한 음씩)
CHORD_WEIGHTS = (1.0, 0.65, 0.5)  # 화음 각 음의 세기
AUDIO_BUFFER = 1024      # 소리가 지직거리면 2048로. 반응이 늦으면 512로
DUCK_WINDOW = 1.5        # 빨리 칠 때: 최근 이 시간(초) 동안 친 키 개수를 세서
DUCK_STRENGTH = 0.2      # 많이 칠수록 새 소리를 작게 만들어요 (소리가 겹쳐서 찢어지는 것 방지)
CLASH_FADE_MS = 700      # 새 소리와 부딪히는 음(반음 등)이 울리고 있으면 이 시간(ms) 동안 서서히 줄여요. 0이면 끔
UPPER_CHORD_STEPS = (0, 2, 4)  # 가운데·윗줄·숫자 줄의 화음 (아랫줄과 같게)
MAX_RINGING = 3          # 동시에 울리는 소리 개수 상한. 넘으면 가장 오래된 소리를 서서히 줄여요

MAJOR = [0, 2, 4, 5, 7, 9, 11]  # 도 레 미 파 솔 라 시


# 음계 번호(idx) → MIDI 번호. idx 0 = 낮은 도(C2), 7 = C3, 14 = C4 ...
def scale_note(idx):
    return 36 + 12 * (idx // 7) + MAJOR[idx % 7]


# (키 10개, 시작 음계 번호, 볼륨, 화음 구성)
ROWS = [
    ("1234567890", 7 * 2, 0.9, UPPER_CHORD_STEPS),  # 숫자 줄: 아랫줄과 같은 화음, 2옥타브 위
    ("qwertyuiop", 7 * 2, 0.9, UPPER_CHORD_STEPS),   # 윗줄: 아랫줄과 같은 화음, 2옥타브 위
    ("asdfghjkl;", 7 * 1, 1.0, UPPER_CHORD_STEPS),   # 가운데 줄: 아랫줄과 같은 화음, 1옥타브 위
    ("zxcvbnm,./", 0, 1.0, CHORD_STEPS),         # 아랫줄: 낮은 음 (세 음 화음)
]

# 기호 키 (음계 번호). ₩ 키도 포함
EXTRA_CHARS = {
    "-": 15, "=": 16, "[": 11, "]": 13,
    "\\": 9, "₩": 9, "'": 8, "`": 10,
}

# 특수 키: 이름 → (MIDI 음 목록, 볼륨)
SPECIAL_RAW = {
    "space": ([36, 43, 48], 1.0),
    "enter": ([48, 52, 55], 1.0),  # 마음에 든다고 했던 그 화음
    "backspace": ([40, 45], 0.8),
    "tab": ([52], 0.6),
    "caps_lock": ([38], 0.6),
    "esc": ([76], 0.4),
}
MODIFIER_RAW = {
    "shift": ([64], 0.3), "shift_l": ([64], 0.3), "shift_r": ([64], 0.3),
    "ctrl": ([45], 0.3), "ctrl_l": ([45], 0.3), "ctrl_r": ([45], 0.3),
    "alt": ([57], 0.3), "alt_l": ([57], 0.3), "alt_r": ([57], 0.3), "alt_gr": ([57], 0.3),
    "cmd": ([60], 0.3), "cmd_l": ([60], 0.3), "cmd_r": ([60], 0.3),
}

TOGGLE_KEY = keyboard.Key.f8  # 켜기/끄기
QUIT_KEY = keyboard.Key.f9    # 종료

# ── 키 → 음 매핑표 만들기 ───────────────────────


def fold(midi):
    # 너무 높은 음은 한 옥타브씩 내려서 날카로운 소리를 막아요
    while midi > 90:
        midi -= 12
    return midi


def chord_for(idx, steps=CHORD_STEPS):
    if idx % 7 == 6:  # 시(B) 위의 화음은 시-레-솔로 바꿔서 어울리게
        steps = tuple(5 if s == 4 else s for s in steps)
    return tuple(fold(scale_note(idx + s)) for s in steps)


key_map = {}
for keys, base_idx, volume, steps in ROWS:
    for i, ch in enumerate(keys):
        key_map[ch] = (chord_for(base_idx + i, steps), volume)
for ch, idx in EXTRA_CHARS.items():
    key_map[ch] = (chord_for(idx, UPPER_CHORD_STEPS), 0.7)

special_map = {}
raw = dict(SPECIAL_RAW)
if SOUND_MODIFIERS:
    raw.update(MODIFIER_RAW)
for name, (notes, volume) in raw.items():
    k = getattr(keyboard.Key, name, None)
    if k is not None:
        special_map[k] = (tuple(notes), volume)

# ── 소리 만들기 ─────────────────────────────────
RATE = 44100
DUR = 4.5  # 한 번 울리는 시간(초). 길수록 페달을 밟은 느낌

pygame.mixer.pre_init(RATE, -16, 1, AUDIO_BUFFER)
pygame.mixer.init()
pygame.mixer.set_num_channels(64)  # 동시에 울릴 수 있는 소리 개수

t = np.arange(int(RATE * DUR)) / RATE

# 울림(리버브)용 임펄스: 서서히 사라지는 잡음을 부드럽게 깎은 것
_rng = np.random.default_rng(7)
_n_ir = int(RATE * 2.5)
_ir = _rng.standard_normal(_n_ir) * np.exp(-np.arange(_n_ir) / RATE * 3.0)
_ir = np.convolve(_ir, np.ones(24) / 24, mode="same")  # 높은 소리를 깎아 따뜻하게
_pre = int(RATE * 0.01)
_ir[:_pre] *= np.linspace(0, 1, _pre)
_FFT_N = 1 << (len(t) + _n_ir - 1).bit_length()
_IR_F = np.fft.rfft(_ir, _FFT_N)


def render_voice(midi):
    freq = 440 * 2 ** ((midi - 69) / 12)
    w = np.zeros_like(t)
    tone_decay = max(0.5, 1 + (min(midi, 60) - 60) / 90)  # 낮은 음은 조금 더 길게. 높아져도 같은 길이
    for detune_hz in (-0.25, 0.25):  # 줄 2개를 아주 살짝 다르게 → 풍성하고 따뜻하게 (모든 음에서 느린 울렁임)
        for n in range(1, 6):
            f = (freq + detune_hz) * n * (1 + 0.0001 * n * n)
            if f >= RATE / 2:
                break
            amp = 1 / n ** 2.0  # 높은 배음은 아주 약하게 → 부드러운 소리
            decay = (0.45 + 0.6 * n) * tone_decay  # 천천히 사라짐 (페달 느낌)
            w += amp * np.sin(2 * np.pi * f * t) * np.exp(-decay * t)
    w *= 1 - np.exp(-t / ATTACK)  # 부드러운 시작

    wet = np.fft.irfft(np.fft.rfft(w, _FFT_N) * _IR_F, _FFT_N)[: len(w)]
    wet *= np.sqrt(np.mean(w ** 2) / np.mean(wet ** 2))  # 울림 소리 크기를 원음과 맞춤
    w = (1 - REVERB_AMOUNT) * w + REVERB_AMOUNT * wet
    return (w / np.max(np.abs(w))).astype(np.float32)


def make_sound(notes, voice_cache):
    mix = np.zeros(len(t), dtype=np.float32)
    for i, m in enumerate(notes):
        shift = int(RATE * 0.022 * i)  # 화음을 아주 살짝 펼쳐서 (아르페지오) 사람이 친 느낌
        weight = CHORD_WEIGHTS[min(i, len(CHORD_WEIGHTS) - 1)]
        v = voice_cache[m]
        mix[shift:] += weight * v[: len(v) - shift]
    fade = int(RATE * 0.4)  # 끝부분은 서서히 줄여서 뚝 끊김 방지
    mix[-fade:] *= np.linspace(1, 0, fade)
    mix = mix / np.max(np.abs(mix)) * MASTER_VOLUME * 32767
    return pygame.mixer.Sound(buffer=mix.astype(np.int16).tobytes())


all_chords = {c for c, _ in key_map.values()} | {c for c, _ in special_map.values()}
all_notes = {m for c in all_chords for m in c}

print("소리 준비 중... (몇 초 걸려요)")
_voices = {m: render_voice(m) for m in all_notes}
sounds = {c: make_sound(c, _voices) for c in all_chords}
del _voices
print("KEYUM 시작! F8: 켜기/끄기, F9: 종료")

# ── 키 입력 처리 ────────────────────────────────
OEM_KEYS = {
    0xBA: ";", 0xBB: "=", 0xBC: ",", 0xBD: "-", 0xBE: ".", 0xBF: "/",
    0xC0: "`", 0xDB: "[", 0xDC: "\\", 0xDD: "]", 0xDE: "'",
}


def key_to_char(key):
    vk = getattr(key, "vk", None)  # 키 위치(코드)를 먼저 봐서 Shift·한글 모드와 상관없이 같은 음
    if vk is not None:
        if 0x30 <= vk <= 0x39 or 0x41 <= vk <= 0x5A:
            return chr(vk).lower()
        if 0x60 <= vk <= 0x69:  # 숫자패드
            return chr(vk - 0x60 + 0x30)
        if vk in OEM_KEYS:
            return OEM_KEYS[vk]
    ch = getattr(key, "char", None)
    return ch.lower() if ch else None


enabled = True
pressed = set()
recent_presses = deque()  # 최근에 친 시각들
active = []  # (채널, 소리, 음 목록): 지금 울리고 있는 소리들


def clashes(a, b):
    # 반음(단2도), 장7도, 증4도로 부딪히는 음이 있으면 True
    return any(abs(x - y) % 12 in (1, 6, 11) for x in a for y in b)


def fade_clashing(new_notes):
    global active
    still = []
    for ch, snd, notes in active:
        if not ch.get_busy() or ch.get_sound() is not snd:
            continue  # 이미 끝난 소리
        if clashes(notes, new_notes):
            ch.fadeout(CLASH_FADE_MS)  # 부딪히는 소리는 서서히 사라지게
        else:
            still.append((ch, snd, notes))
    active = still


def on_press(key):
    global enabled
    if key == QUIT_KEY:
        return False
    if key in pressed:  # 꾹 누르고 있을 때 반복 방지
        return
    pressed.add(key)

    if key == TOGGLE_KEY:
        enabled = not enabled
        print("ON" if enabled else "OFF")
        return
    if not enabled:
        return

    entry = special_map.get(key) or key_map.get(key_to_char(key))
    if entry is None:
        if DEBUG:
            print("소리 없는 키:", key)
        return
    notes, volume = entry

    now = time.monotonic()
    while recent_presses and now - recent_presses[0] > DUCK_WINDOW:
        recent_presses.popleft()
    volume /= 1 + DUCK_STRENGTH * len(recent_presses)  # 빨리 칠수록 한 음은 작게
    recent_presses.append(now)

    if CLASH_FADE_MS > 0:
        try:
            fade_clashing(notes)
        except Exception as e:  # 정리에 실패해도 소리는 계속 나게
            if DEBUG:
                print("소리 정리 오류:", e)

    if MAX_RINGING > 0:
        try:
            while len(active) >= MAX_RINGING:  # 너무 많이 울리면 가장 오래된 소리부터 줄이기
                old_ch, old_snd, _ = active.pop(0)
                if old_ch.get_busy() and old_ch.get_sound() is old_snd:
                    old_ch.fadeout(CLASH_FADE_MS)
        except Exception as e:
            if DEBUG:
                print("소리 정리 오류:", e)

    channel = sounds[notes].play()
    if channel:  # 칠 때마다 세기를 아주 조금씩 다르게 → 기계적이지 않게
        channel.set_volume(volume * random.uniform(0.75, 1.0))
        active.append((channel, sounds[notes], notes))


def on_release(key):
    pressed.discard(key)


# 개인정보 보호: 눌린 키를 저장하지 않아요. (DEBUG를 켰을 때만 소리 없는 키를 화면에 출력)
with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
    listener.join()