# 🔍 키워드 날씨 분석기

키워드 검색량과 날씨의 관계를 분석하는 웹 애플리케이션입니다.

## ✨ 주요 기능

- **다중 키워드 분석**: 여러 키워드를 동시에 분석
- **실시간 데이터**: 네이버 검색 트렌드 + Open-Meteo 날씨 데이터
- **전국 분석**: 19개 주요 도시 (8개 광역시 + 11개 경기도)
- **다양한 차트**: 일별/주별/월별 추이 분석
- **상관관계 분석**: 날씨와 검색량의 관계 분석
- **예상 검색량**: 퍼센트 데이터를 실제 검색량으로 변환

## 🚀 사용 방법

1. **키워드 입력**: 분석할 키워드들을 한 줄씩 입력
2. **날짜 선택**: 분석할 기간 설정
3. **지역 선택**: 전국 또는 특정 지역 선택
4. **검색량 변환**: 선택적으로 실제 검색량으로 변환
5. **분석 결과 확인**: 다양한 차트와 인사이트 확인

## 📊 지원 키워드

- 골프, 골프예약, 골프부킹, 골프연습장
- 국내골프여행, 골프레슨, 골프아카데미
- 골프장예약, 골프장, 골프여행, 골프투어
- 기타 원하는 키워드

## 🌤️ 날씨 분류

- **☀️ 맑음**: 강수량 1mm 미만
- **🌧️ 비**: 강수량 1mm 이상 (눈 제외)
- **❄️ 눈**: 눈 1mm 이상 (비 제외)
- **🌧️❄️ 혼합**: 비와 눈 모두 1mm 이상

## 🔧 기술 스택

- **Frontend**: Streamlit
- **Data**: Pandas, Plotly
- **APIs**: Naver DataLab API, Open-Meteo API
- **Deployment**: Streamlit Cloud

## 🔐 API 키 보안 설정

### ⚠️ 중요: API 키 보안

이 프로젝트는 네이버 데이터랩 API를 사용합니다. API 키를 안전하게 관리하는 것이 매우 중요합니다.

### 🛡️ 보안 설정 방법

#### 1. 로컬 실행시

**방법 1: 환경변수 설정**
```bash
export NAVER_CLIENT_ID="your_client_id"
export NAVER_CLIENT_SECRET="your_client_secret"
```

**방법 2: .env 파일 사용**
```bash
# env_example.txt를 .env로 복사
cp env_example.txt .env

# .env 파일 편집하여 실제 API 키 입력
NAVER_CLIENT_ID=your_actual_client_id
NAVER_CLIENT_SECRET=your_actual_client_secret
```

**방법 3: Streamlit Secrets 파일 사용**
```bash
# secrets.toml.example을 secrets.toml로 복사
cp .streamlit/secrets.toml.example .streamlit/secrets.toml

# secrets.toml 파일 편집하여 실제 API 키 입력
[secrets]
NAVER_CLIENT_ID = "your_actual_client_id"
NAVER_CLIENT_SECRET = "your_actual_client_secret"
```

#### 2. Streamlit Cloud 배포시

1. Streamlit Cloud 대시보드 접속
2. Settings → Secrets 이동
3. 다음 내용 추가:
```toml
NAVER_CLIENT_ID = "your_actual_client_id"
NAVER_CLIENT_SECRET = "your_actual_client_secret"
```

### 🚨 보안 주의사항

- ❌ **절대 하지 말 것**:
  - API 키를 코드에 직접 입력
  - API 키를 GitHub에 업로드
  - API 키를 공개 채널에 공유
  - `.streamlit/secrets.toml` 파일을 GitHub에 업로드

- ✅ **반드시 할 것**:
  - 환경변수 또는 Streamlit Secrets 사용
  - .gitignore에 .env 및 .streamlit/secrets.toml 파일 추가
  - 정기적으로 API 키 갱신
  - API 사용량 모니터링

### 📋 API 키 발급 방법

1. [네이버 개발자센터](https://developers.naver.com/) 접속
2. 애플리케이션 등록
3. 데이터랩 API 선택
4. Client ID와 Client Secret 발급

### 🔍 보안 상태 확인

프로젝트에는 다음 보안 기능이 포함되어 있습니다:
- API 키 마스킹 표시
- 환경변수 자동 감지
- Streamlit Secrets 지원
- 보안 오류 메시지

## 📝 라이선스

MIT License
