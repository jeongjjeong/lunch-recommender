# YouTube Channel Analytics Agent — 앱 설계 문서

> 작성일: 2026-04-12  
> 대상 독자: 개발자 (이 문서만 읽으면 바로 코딩 시작 가능)

---

## 1. 개요 및 목적

유튜브 채널 데이터를 자동 수집하고, Claude AI가 인사이트와 개선 방향을 제시하는 **AI 에이전트 툴**.

### 왜 앱이 아니라 에이전트인가?

| 구분 | 웹 대시보드 | AI 에이전트 (채택) |
|------|------------|------------------|
| 개발 공수 | 높음 (프론트+백+DB) | 낮음 (Python 스크립트) |
| 인사이트 품질 | 숫자 나열 | 자연어 분석 + 개선 제안 |
| 유연성 | 정해진 차트만 | 자유로운 질의응답 |
| 유지보수 | 높음 | 낮음 |

**결론**: Python CLI 에이전트로 구현. 터미널에서 대화하듯 채널을 분석하고, 리포트를 마크다운/HTML로 저장.

---

## 2. 기술 스택

```
Language     Python 3.11+
AI           Anthropic SDK (claude-sonnet-4-6)  ← 비용/성능 최적
YouTube API  google-api-python-client (YouTube Data API v3)
             youtube-analytics-api v2
Auth         OAuth 2.0 (채널 소유자 본인 인증)
Report       Markdown → HTML (Jinja2 템플릿)
CLI UX       rich (터미널 컬러/테이블 출력)
Config       python-dotenv (.env 파일)
```

### 설치 패키지

```
anthropic
google-api-python-client
google-auth-oauthlib
google-auth-httplib2
rich
jinja2
python-dotenv
```

---

## 3. 디렉터리 구조

```
youtube-analytics-agent/
├── DESIGN.md               ← 이 문서
├── main.py                 ← 진입점 (CLI 에이전트 루프)
├── agent.py                ← Claude 에이전트 로직 (tool use)
├── tools/
│   ├── __init__.py
│   ├── channel_info.py     ← 채널 기본 정보 조회
│   ├── video_list.py       ← 영상 목록 + 정렬
│   ├── analytics.py        ← 조회수/시청시간/구독자 증감
│   ├── audience.py         ← 시청자 인구통계 (나이/성별/지역)
│   ├── traffic_source.py   ← 유입 경로 분석
│   └── report.py           ← 리포트 생성 (마크다운/HTML)
├── auth/
│   └── youtube_oauth.py    ← OAuth 2.0 인증 처리
├── templates/
│   └── report.html.j2      ← HTML 리포트 Jinja2 템플릿
├── output/                 ← 생성된 리포트 저장
├── .env.example
└── requirements.txt
```

---

## 4. 인증 설정 (개발자 초기 세팅)

### 4-1. Google Cloud Console 설정

1. Google Cloud Console → 새 프로젝트 생성
2. `YouTube Data API v3` + `YouTube Analytics API` 활성화
3. OAuth 2.0 클라이언트 ID 생성 (데스크톱 앱 유형)
4. `client_secret.json` 다운로드 → 프로젝트 루트에 저장

### 4-2. `.env` 파일

```env
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_CLIENT_SECRET_FILE=client_secret.json
YOUTUBE_CHANNEL_ID=UCxxxxxxxxxxxxxxxxxx   # 본인 채널 ID
```

### 4-3. 첫 실행 시 OAuth 브라우저 인증 → `token.json` 자동 저장

---

## 5. 에이전트 설계 (핵심)

### 5-1. Claude Tool 목록

에이전트가 Claude에게 제공하는 도구 목록. Claude가 질문에 답하기 위해 필요한 도구를 스스로 선택·호출한다.

```python
TOOLS = [
    {
        "name": "get_channel_overview",
        "description": "채널 기본 지표: 구독자 수, 총 조회수, 영상 수, 최근 30일 성장률",
        "input_schema": {
            "type": "object",
            "properties": {
                "days": {"type": "integer", "description": "분석 기간(일), 기본값 30"}
            }
        }
    },
    {
        "name": "get_top_videos",
        "description": "성과 상위/하위 영상 목록. 정렬 기준: views, watchTime, likes, comments",
        "input_schema": {
            "type": "object",
            "properties": {
                "metric":   {"type": "string", "enum": ["views","watchTime","likes","comments"]},
                "limit":    {"type": "integer", "description": "반환할 영상 수, 기본값 10"},
                "days":     {"type": "integer", "description": "분석 기간(일)"}
            },
            "required": ["metric"]
        }
    },
    {
        "name": "get_analytics_timeseries",
        "description": "날짜별 추이: 조회수, 순시청시간(분), 구독자 증감, 노출수, CTR",
        "input_schema": {
            "type": "object",
            "properties": {
                "metrics":    {"type": "array", "items": {"type": "string"},
                               "description": "예: [\"views\", \"estimatedMinutesWatched\", \"subscribersGained\"]"},
                "start_date": {"type": "string", "description": "YYYY-MM-DD"},
                "end_date":   {"type": "string", "description": "YYYY-MM-DD"}
            },
            "required": ["metrics", "start_date", "end_date"]
        }
    },
    {
        "name": "get_audience_demographics",
        "description": "시청자 인구통계: 나이/성별/국가 분포",
        "input_schema": {
            "type": "object",
            "properties": {
                "dimension": {"type": "string", "enum": ["ageGroup", "gender", "country"]},
                "days":      {"type": "integer"}
            },
            "required": ["dimension"]
        }
    },
    {
        "name": "get_traffic_sources",
        "description": "유입 경로별 조회수 비율: 검색, 추천, 외부, 직접 등",
        "input_schema": {
            "type": "object",
            "properties": {
                "days": {"type": "integer"}
            }
        }
    },
    {
        "name": "get_video_retention",
        "description": "특정 영상의 시청자 유지율 곡선 (이탈 구간 파악)",
        "input_schema": {
            "type": "object",
            "properties": {
                "video_id": {"type": "string", "description": "유튜브 영상 ID"}
            },
            "required": ["video_id"]
        }
    },
    {
        "name": "save_report",
        "description": "분석 결과를 마크다운 + HTML 파일로 output/ 폴더에 저장",
        "input_schema": {
            "type": "object",
            "properties": {
                "title":   {"type": "string"},
                "content": {"type": "string", "description": "마크다운 형식의 전체 리포트 내용"}
            },
            "required": ["title", "content"]
        }
    }
]
```

### 5-2. 에이전트 루프 (agent.py 핵심 로직)

```python
import anthropic

SYSTEM_PROMPT = """
당신은 유튜브 채널 성장 전문 AI 어시스턴트입니다.
채널 데이터를 분석하고 실질적인 개선 방향을 제시합니다.

분석 시 반드시 포함할 요소:
- 현재 수치 (What): 지표가 어떤 상태인지
- 원인 분석 (Why): 왜 그런 결과가 나왔는지
- 개선 액션 (How): PD가 당장 실행할 수 있는 구체적 행동
- 우선순위: 가장 임팩트 큰 개선사항 TOP 3

응답 언어: 한국어
"""

def run_agent(user_message: str, conversation_history: list) -> str:
    client = anthropic.Anthropic()
    
    conversation_history.append({"role": "user", "content": user_message})
    
    while True:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=8096,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=conversation_history
        )
        
        # 도구 호출이 없으면 최종 응답 반환
        if response.stop_reason == "end_turn":
            assistant_message = response.content[0].text
            conversation_history.append({"role": "assistant", "content": response.content})
            return assistant_message
        
        # 도구 호출 처리
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                result = execute_tool(block.name, block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": str(result)
                })
        
        conversation_history.append({"role": "assistant", "content": response.content})
        conversation_history.append({"role": "user", "content": tool_results})
```

---

## 6. 화면 구성 (CLI UX)

```
╔══════════════════════════════════════════════════════╗
║        YouTube Channel Analytics Agent              ║
║        채널: [채널명]  |  구독자: 12,345명           ║
╚══════════════════════════════════════════════════════╝

[사전 정의 분석 메뉴]
  1. 주간 채널 리포트 생성
  2. 최근 30일 성과 분석
  3. 상위 영상 심층 분석
  4. 시청자 인구통계 분석
  5. 유입 경로 최적화 분석
  6. 직접 질문하기

선택 (1-6) 또는 질문 입력 > _
```

### 직접 질문 예시 (자유 대화 모드)

```
> 저번 달에 구독자가 갑자기 줄었는데 왜 그럴까?
> 조회수 대비 구독 전환율이 낮은 영상은 어느 것야?
> 어떤 요일/시간에 영상을 올리면 좋을까?
> 지난 3개월 중 CTR이 가장 낮았던 영상 분석해줘
> 오늘 리포트 파일로 저장해줘
```

---

## 7. 데이터 흐름

```
사용자 입력
     │
     ▼
main.py (CLI 루프)
     │  메시지 전달
     ▼
agent.py (Claude API 호출)
     │  stop_reason == "tool_use"
     ▼
tools/ 모듈 실행
     │  YouTube API 호출
     ▼
YouTube Data API v3
YouTube Analytics API
     │  JSON 응답
     ▼
agent.py (tool_result → Claude 재호출)
     │  Claude가 데이터 해석 + 인사이트 생성
     ▼
사용자에게 응답 출력 (rich 콘솔)
     │  save_report 도구 호출 시
     ▼
output/YYYY-MM-DD-report.html 저장
```

---

## 8. 핵심 분석 기능 명세

### 8-1. 주간 리포트 (자동 분석 흐름)

에이전트가 메뉴 1 선택 시 아래 순서로 자동으로 도구를 호출하며 종합 리포트 작성:

1. `get_channel_overview(days=7)` → 이번 주 전체 지표
2. `get_analytics_timeseries(metrics=[...], 최근 7일)` → 일별 추이
3. `get_top_videos(metric="views", days=7)` → 이번 주 히트 영상
4. `get_traffic_sources(days=7)` → 유입 경로
5. `get_audience_demographics(dimension="country")` → 시청 국가
6. 전체 데이터 종합 → Claude 인사이트 생성
7. `save_report(title="주간리포트", content=...)` → 파일 저장

### 8-2. 영상별 심층 분석

```
입력: 영상 URL 또는 영상 ID
출력:
  - 조회수 / CTR / 평균 시청 지속 시간
  - 시청자 유지율 곡선 + 이탈 구간 분석
  - 댓글 감성 요약 (긍/부정 키워드)
  - 유사 성과 영상 비교
  - 개선 가능한 썸네일/제목 전략 제안
```

### 8-3. 채널 성장 진단

```
출력:
  - 구독자 성장 속도 추이 (가속/정체/감속 판단)
  - 조회수 vs 구독 전환율 (CVR) 분석
  - 노출 대비 클릭률 (CTR) 벤치마크 비교
  - 시청시간 기여 상위 영상 20% (파레토 분석)
  - 콘텐츠 카테고리별 성과 분류
```

---

## 9. 리포트 출력 형식

### 터미널 출력 (`rich` 라이브러리)

```
┌─────────────────────────────────────────┐
│  채널 주간 요약 (2026-04-05 ~ 04-12)    │
├──────────────┬──────────────────────────┤
│ 조회수       │ 45,231 (+12.3% ▲)        │
│ 시청시간     │ 2,104시간 (+8.1% ▲)      │
│ 신규 구독자  │ +234 (-5명 감소 포함)     │
│ 노출 CTR     │ 4.2% (업계 평균: 3.5%)   │
└──────────────┴──────────────────────────┘
```

### HTML 리포트 (`output/` 저장)

- Jinja2 템플릿 기반
- Chart.js로 시계열 그래프 인라인 포함
- 브라우저에서 바로 열람 가능
- 인사이트 섹션: Claude 분석 결과 마크다운 렌더링

---

## 10. 구현 우선순위 (스프린트 제안)

### Sprint 1 — 기반 (3~4일)
- [ ] OAuth 인증 모듈 (`auth/youtube_oauth.py`)
- [ ] `get_channel_overview` 도구 구현
- [ ] `get_analytics_timeseries` 도구 구현
- [ ] 기본 Claude 에이전트 루프 (`agent.py`)
- [ ] CLI 진입점 (`main.py`)

### Sprint 2 — 핵심 분석 (3~4일)
- [ ] `get_top_videos` 도구 구현
- [ ] `get_traffic_sources` 도구 구현
- [ ] `get_audience_demographics` 도구 구현
- [ ] `get_video_retention` 도구 구현
- [ ] rich 터미널 UI 적용

### Sprint 3 — 리포트 (2~3일)
- [ ] `save_report` 도구 구현
- [ ] HTML 리포트 템플릿 (Jinja2 + Chart.js)
- [ ] 메뉴 기반 사전 정의 분석 흐름

---

## 11. YouTube API 주요 엔드포인트 참조

| 기능 | API | 엔드포인트 |
|------|-----|-----------|
| 채널 기본 정보 | Data API v3 | `channels.list` |
| 영상 목록 | Data API v3 | `search.list`, `videos.list` |
| 조회수/시청시간 | Analytics API | `reports.query` (dimensions: day) |
| 인구통계 | Analytics API | `reports.query` (dimensions: ageGroup, gender) |
| 유입 경로 | Analytics API | `reports.query` (dimensions: insightTrafficSourceType) |
| 시청자 유지율 | Analytics API | `reports.query` (dimensions: elapsedVideoTimeRatio) |

> **주의**: YouTube Analytics API는 채널 소유자 OAuth 인증 필수.  
> 타인 채널 분석 불가 (본인 채널만 가능).

---

## 12. 확장 아이디어 (v2)

- **경쟁 채널 비교**: YouTube Data API로 타 채널 공개 데이터 수집
- **댓글 감성 분석**: Claude로 댓글 배치 분석 → 시청자 반응 요약
- **업로드 스케줄 최적화**: 시간대별 조회수 데이터로 최적 업로드 시간 추천
- **썸네일 A/B 분석**: CTR 변화와 썸네일 변경 이력 교차 분석
- **슬랙/이메일 알림**: 주간 리포트 자동 발송

---

*이 문서는 개발자가 바로 코딩 시작할 수 있도록 작성되었습니다.*
