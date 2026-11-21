# KEYUM (키음)

[KEYUM.exe 다운로드 (최신 버전)](https://github.com/minseo0812/keyum/releases/latest)

타자를 칠 때마다 부드러운 피아노 소리가 나는 프로그램이에요.
컴퓨터 어디서든(메모장, 브라우저, 코드 에디터, 게임 등) 키를 누르면 소리가 나요.

- 아무 키나 마구 쳐도 어울리도록 도·레·미·파·솔·라·시(C 장조)의 3화음으로 만들었어요.
- 페달을 밟은 듯한 울림(리버브)과 부드러운 시작음으로 "띡띡" 하는 기계음을 줄였어요.
- 소리 파일 없이 프로그램이 직접 소리를 합성해요.

## 개인정보 보호

KEYUM은 전역 키보드 입력을 듣는 프로그램이라서 먼저 밝혀둬요.

- 눌린 키를 **저장하거나 기록하지 않아요.** 키를 누르면 그에 맞는 소리를 재생하고 끝이에요.
- **인터넷에 연결하지 않아요.** 어디로도 데이터를 보내지 않아요.
- 키 입력은 막지 않고 그대로 앱에 전달돼요.
- 코드는 `keyum.py` 한 파일이라 누구나 직접 확인할 수 있어요.

## 실행 방법 (Windows)

Python 3.10 이상이 필요해요. (Python 3.14에서 확인했어요.)

```bash
python -m venv .venv
source .venv/Scripts/activate      # Git Bash 기준. PowerShell은 .venv\Scripts\Activate.ps1
pip install -r requirements.txt
python keyum.py
```

## 단축키

| 키  | 동작             |
| --- | ---------------- |
| F8  | 소리 켜기 / 끄기 |
| F9  | 프로그램 종료    |

## 소리 조절

`keyum.py` 위쪽의 설정 값을 바꾸면 돼요.

| 설정              | 설명                                              |
| ----------------- | ------------------------------------------------- |
| `MASTER_VOLUME`   | 전체 소리 크기 (0~1)                              |
| `REVERB_AMOUNT`   | 울림 정도 (0~1)                                   |
| `ATTACK`          | 소리가 시작될 때 올라오는 시간. 클수록 부드러워요 |
| `MAX_RINGING`     | 동시에 울리는 소리 개수 상한                      |
| `AUDIO_BUFFER`    | 소리가 지직거리면 2048, 반응이 늦으면 512         |
| `SOUND_MODIFIERS` | `False`면 Shift/Ctrl/Alt/Win 키는 소리 없음       |

## 키와 음

- 아랫줄(`Z`~`/`)이 기준이고, 가운데 줄은 1옥타브, 윗줄과 숫자 줄은 2옥타브 높게 같은 화음이 나요.
- Enter는 도·미·솔 화음, Space는 낮은 도·솔·도 화음이에요.
- 새 소리와 부딪히는 음(반음 등)이 아직 울리고 있으면 서서히 줄여서 탁하지 않게 해요.

## 사용한 것

Python, [pynput](https://pypi.org/project/pynput/)(전역 키 입력), [pygame-ce](https://pypi.org/project/pygame-ce/)(소리 재생), NumPy(소리 합성)

## 앞으로 할 일

- [ ] 설정을 JSON 파일로 분리
- [ ] 트레이 아이콘, 설정 화면 (Electron + React)
- [ ] 음색 프리셋

## 알려진 한계

- Windows 11에서 만들고 확인했어요. macOS와 Linux는 아직 테스트하지 않았어요.
- 실행하면 소리를 준비하느라 처음에 몇 초 걸려요.
- 전역 키 입력을 감지하는 프로그램이라 일부 백신이나 보안 프로그램이 경고할 수 있어요. 코드는 `keyum.py` 한 파일이고, 눌린 키는 저장하지 않아요.

## 라이선스

[MIT License](LICENSE)
