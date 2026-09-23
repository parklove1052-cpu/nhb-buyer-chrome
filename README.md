# NHB 바이어 수집기 (크롬 + Playwright)

API 키 없이 **크롬으로 구글 지도를 검색**해서 해외 바이어 후보(업체명·주소·전화·웹사이트)를 모으고, 주간 보고서를 만듭니다.

## 다른 PC에서 설치 (한 번만)

1. `git clone https://github.com/parklove1052-cpu/nhb-buyer-chrome.git`
2. 폴더에서 **`install.cmd` 더블클릭**
   - 파이썬 없으면 설치 → Playwright 설치 → 브라우저 설치 → 매주 월요일 09:00 자동 실행 등록
3. 바로 돌려보려면 **`run.cmd` 더블클릭**

## 결과 위치

| 파일 | 내용 |
|---|---|
| `data/leads.csv` | 모은 업체 전체 (엑셀로 열림, 중복 자동 제외) |
| `reports/report_날짜.md` | 주간 보고 (전체 / 최근 7일 새 후보) |
| `logs/run.log` | 실행 기록 |

`data/` `reports/` `profile/` 은 깃에 올라가지 않습니다 (바이어 자료 보호).

## 설정 — `config.json`

- `queries`: 구글 지도 검색어 (국가·도시·업종 바꾸면 다른 시장)
- `max_per_query`: 검색어당 최대 업체 수
- `headless`: `false` = 크롬 창이 보이게, `true` = 창 없이

## 명령

```
run.cmd            수집 + 보고
run.cmd collect    수집만
run.cmd report     보고만
```

설치된 크롬이 있으면 그걸 쓰고, 없으면 Playwright 크롬을 씁니다. 크롬 로그인 상태는 `profile/` 에 저장돼 다음 실행에도 유지됩니다.

## 주의

- 구글 지도 결과는 "후보"일 뿐 수입 실적이 아닙니다.
- 링크드인 자동 수집은 넣지 않았습니다 (계정 정지 위험).
- 자동 실행은 그 시간에 PC가 켜져 있어야 합니다.
