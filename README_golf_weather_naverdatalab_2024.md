
# Golf × Weather × Naver DataLab (2024, KR)

본 스크립트는 2024년 1월 1일 ~ 12월 31일 기간 동안
네이버 데이터랩(검색어 트렌드, 일별) 지표와 Open‑Meteo 히스토리컬 날씨 데이터를 결합하여
`라운딩`, `골프 예약`, `골프 부킹`, `골프장` 검색 지표가
비/눈/건조(강수無) 일자에 따라 어떻게 달라졌는지 비교합니다.

## 무엇을 만드나요?
- `naver_golf_trend_weather_daily_2024.csv` : 날짜별(일), 키워드별 검색지표 + 강수량/적설량 + 일자 유형(dry/rain/snow/mixed)
- `naver_golf_trend_weather_summary_2024.csv` : 키워드별 날씨유형 평균 지표 및 dry 대비 증감
- `naver_golf_trend_by_weather_2024.png` : 요약 막대 그래프

## 필요조건
1) **Naver DataLab API 자격증명**
   - 환경변수 설정 (터미널/파워셸 등):
     - macOS/Linux:  
       ```bash
       export NAVER_CLIENT_ID="your_client_id_here"
       export NAVER_CLIENT_SECRET="your_client_secret_here"
       ```
     - Windows (PowerShell):  
       ```powershell
       setx NAVER_CLIENT_ID "your_client_id_here"
       setx NAVER_CLIENT_SECRET "your_client_secret_here"
       ```
   - 데이터랩 Search Trend 문서 참고.

2) **날씨 데이터 (Open‑Meteo)**  
   - API Key 불필요. 서울 좌표(37.5665, 126.9780) 기준으로 일별 강수/적설 합계를 수집합니다.
   - 필요 시 지역별 좌표로 확장하여 가중평균(예: 인구가중) 가능.

## 설치 & 실행
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements_golf_weather_naverdatalab_2024.txt

python golf_weather_naverdatalab_2024.py
```

## 분석 로직 개요
- **일별 검색지표**: Naver DataLab Search Trend `timeUnit=date`로 수집 (상대지표, ratio).
- **일별 날씨**: Open‑Meteo Historical Weather `precipitation_sum`, `rain_sum`, `snowfall_sum` 수집.
- **일자 분류 기준**:
  - `rain` : `rain_sum ≥ 1.0mm`
  - `snow` : `snowfall_sum ≥ 1.0mm`
  - `mixed`: 위 두 조건 동시 충족
  - `dry`  : 나머지
  - (현업 기준에 맞게 임계값을 조정하세요)
- **요약지표**: 키워드×날씨유형 평균(ratio) 및 `*_vs_dry` 차이(효과 크기 추정).

## 응용 팁
- 키워드/그룹을 더 추가하고, 성/연령/디바이스 필터를 걸어 세그먼트별로 재추정하세요.
- 날씨는 서울 대신 **주요 라운드 지역(여주/원주/충주/제주 등)** 좌표를 다수 선택해 평균(또는 가중) 처리하면 더 정밀해집니다.
- 골프장 예약 실거래/페이지뷰/앱 DAU 같은 **비즈니스 KPI와 공적합성(co-movement)** 도 추가로 확인해보세요.

## 파일 설명
- `golf_weather_naverdatalab_2024.py` : 수집→결합→집계→시각화 end-to-end 스크립트
- `requirements_golf_weather_naverdatalab_2024.txt` : 의존 라이브러리 명세
- 출력물: CSV 2종 + PNG 1종

---

© 2025
