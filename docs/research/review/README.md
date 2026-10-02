# 검토 등록부 — 템플릿·레이아웃·참고 자료 검토와 승인

템플릿·레이아웃으로 만들 후보와 참고 자료(조사한 덱·사이트·파일)를 **등록하고, 미리 보며 검토하고, 승인**하는 도구다.
승인된 대상부터 nexa-slide 템플릿·레이아웃으로 구현해 서비스에 넣는다.

```bash
python3 docs/research/review/review_server.py            # → http://127.0.0.1:5590/
python3 docs/research/review/review_server.py --port 5591 --genspark D:\Projects\kiros33\_research\genspark-slides
python3 docs/research/review/import_genspark.py          # Genspark 조사 결과를 등록부에 (다시 실행해도 상태·날짜는 유지)
```

## 파일

| 파일 | 내용 |
|---|---|
| `registry.json` | **등록부**(저장소에 둔다) — 대상마다 종류·제목·출처·태그·메모·상태·등록일·검토일·승인일·이력 |
| `review_server.py` | 로컬 서버(표준 라이브러리) — 등록부 읽기·쓰기, 미리보기 자료, 조사 폴더 원본 제공 |
| `review.html` | 검토 화면 |
| `import_genspark.py` | `../genspark-skills/data/`(템플릿 후보·새 레이아웃 유형·참고 덱 156개)를 등록부로 |

원본(조사한 덱의 썸네일·장 HTML·그림)은 **저장소 밖** 조사 폴더에서 미리보기로만 읽는다(기본 `<저장소>/../_research/genspark-slides`, `--genspark` 또는 `NEXA_RESEARCH_GENSPARK`).
등록부에는 우리가 쓴 제목·메모·날짜·상태만 둔다.

## 대상

| 종류(`kind`) | 무엇 | 미리보기 |
|---|---|---|
| `template` | nexa 템플릿 후보(색·배치·구조) | 근거 덱들의 전체 장 |
| `layout` | 새 레이아웃 후보(낱장 구성) | 예시 장 |
| `reference-deck` | 참고 덱(조사한 원본) | 전체 장 · 장을 누르면 원본 HTML 을 실제 비율로 |
| `site` | 참고 사이트 | 새 탭 링크 |
| `file` | 참고 파일(PPTX·PDF·이미지 등) | 경로·있음 여부·크기 |

`source.type`: `genspark-template` · `genspark-layout` · `genspark-skill` · `site` · `file` — 새 출처가 생기면 `review_server.py` 의 `preview()` 에 더한다.

## 상태와 날짜

```
registered(등록) ─ 검토 시작 → reviewing(검토 중) ─ 승인 → approved(승인)
                                                 ├ 보류 → held
                                                 └ 제외 → rejected        (어느 상태든 "다시 등록 상태로" 가능)
```

| 필드 | 언제 |
|---|---|
| `registeredAt` | 등록할 때(가져오기·"+ 대상 추가") |
| `reviewedAt` | 처음 검토 시작·승인·보류·제외할 때(한 번만) |
| `approvedAt` | 승인할 때(다시 등록 상태로 돌리면 지움) |
| `history` | 모든 동작(등록·검토 시작·승인·보류·제외·다시 등록·메모)과 그때의 메모 |

화면은 기본으로 **최근 등록 순**(같은 시각이면 템플릿 → 레이아웃 → 참고 덱)이고, 최근 검토·승인 순, 상태·종류·검색으로 거른다.
주소 `#<대상 id>` 는 그 대상을, `#<대상 id>/v3` 은 3번째 장 보기 창까지 연다(링크 공유).

## 앞으로

- 새 참고 자료(파일·사이트)는 "+ 대상 추가"로 등록하고 최근 등록 순으로 검토한다.
- 승인된 `template`·`layout` 이 구현 대상이다 — 구현하면 메모에 엔진 템플릿·레이아웃 이름을 남긴다.
