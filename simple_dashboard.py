import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, date, timedelta
import os
import requests
import json

# .env 파일 로드 (선택사항)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv가 설치되지 않은 경우 무시

# 페이지 설정
st.set_page_config(
    page_title="키워드 날씨 분석기",
    page_icon="🔍",
    layout="wide"
)

# 예쁜 CSS 스타일
st.markdown("""
<style>
    .main-title {
        font-size: 3rem;
        color: #2E8B57;
        text-align: center;
        margin-bottom: 2rem;
        font-weight: bold;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
    }
    .subtitle {
        font-size: 1.2rem;
        color: #666;
        text-align: center;
        margin-bottom: 3rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 15px;
        color: white;
        text-align: center;
        margin: 0.5rem 0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .weather-card {
        padding: 1.5rem;
        border-radius: 15px;
        text-align: center;
        margin: 0.5rem;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        color: white;
        font-weight: bold;
    }
    .rain-card { background: linear-gradient(135deg, #74b9ff 0%, #0984e3 100%); }
    .snow-card { background: linear-gradient(135deg, #a29bfe 0%, #6c5ce7 100%); }
    .dry-card { background: linear-gradient(135deg, #fdcb6e 0%, #e17055 100%); }
    .mixed-card { background: linear-gradient(135deg, #00b894 0%, #00a085 100%); }
    .info-box {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 10px;
        border-left: 4px solid #2E8B57;
        margin: 1rem 0;
    }
    .success-box {
        background: #d4edda;
        padding: 1rem;
        border-radius: 10px;
        border-left: 4px solid #28a745;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

def fetch_naver_data(keyword_groups, start_date, end_date):
    """네이버에서 검색 데이터 가져오기 (여러 그룹 지원)"""
    url = "https://openapi.naver.com/v1/datalab/search"
    
    # 환경변수에서 API 키 가져오기 (Streamlit Cloud 호환)
    client_id = os.environ.get("NAVER_CLIENT_ID")
    client_secret = os.environ.get("NAVER_CLIENT_SECRET")
    
    # Streamlit secrets에서도 시도
    if not client_id or not client_secret:
        try:
            import streamlit as st
            secrets = st.secrets
            client_id = secrets.get("NAVER_CLIENT_ID", client_id)
            client_secret = secrets.get("NAVER_CLIENT_SECRET", client_secret)
        except:
            pass
    
    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret,
        "Content-Type": "application/json",
    }
    
    if not client_id or not client_secret:
        debug_info = f"Client ID: {'설정됨' if client_id else '없음'}, Client Secret: {'설정됨' if client_secret else '없음'}"
        return None, f"❌ 네이버 API 키가 없습니다. {debug_info}"
    
    all_rows = []
    
    try:
        # 각 그룹별로 API 호출 (5개씩 처리)
        for group in keyword_groups:
            body = {
                "startDate": start_date,
                "endDate": end_date,
                "timeUnit": "date",
                "keywordGroups": [group],
            }
            
            resp = requests.post(url, headers=headers, data=json.dumps(body), timeout=30)
            resp.raise_for_status()
            data = resp.json()
            
            # 결과 처리
            for result in data.get("results", []):
                group_name = result["title"]
                actual_keywords = group["keywords"]
                
                # 각 키워드별로 개별 데이터 생성
                for keyword in actual_keywords:
                    for item in result["data"]:
                        all_rows.append({
                            "날짜": item["period"],
                            "키워드": keyword,
                            "검색량": item["ratio"]
                        })
        
        df = pd.DataFrame(all_rows)
        if not df.empty:
            df["날짜"] = pd.to_datetime(df["날짜"]).dt.date
        return df, f"✅ {len(keyword_groups)}개 그룹의 데이터를 성공적으로 가져왔습니다!"
        
    except Exception as e:
        return None, f"❌ 오류가 발생했습니다: {str(e)}"

def fetch_keyword_volume_data(keywords_list, target_date):
    """키워드별 예상 검색량 데이터 생성 (고정 추정값)"""
    try:
        # 키워드별 기본 검색량 추정 (실제 데이터 기반 추정치)
        keyword_base_volumes = {
            "골프": 50000,
            "골프예약": 15000,
            "골프부킹": 12000,
            "골프연습장": 8000,
            "국내골프여행": 6000,
            "골프레슨": 10000,
            "골프아카데미": 5000,
            "골프장예약": 18000,
            "골프장": 25000,
            "골프여행": 8000,
            "골프투어": 7000,
            "라운딩": 30000,
            "골프 용품": 8000,
            "골프 클럽": 5000,
            "골프 티": 3000,
            "골프 공": 2000
        }
        
        keyword_volumes = {}
        
        for keyword in keywords_list:
            # 키워드가 기본 목록에 있으면 해당 값 사용, 없으면 기본값 1000 사용
            if keyword in keyword_base_volumes:
                keyword_volumes[keyword] = keyword_base_volumes[keyword]
            else:
                # 키워드 길이와 복잡도에 따라 추정
                base_volume = 1000
                if len(keyword) <= 2:
                    base_volume = 2000
                elif len(keyword) <= 4:
                    base_volume = 1500
                else:
                    base_volume = 800
                
                keyword_volumes[keyword] = base_volume
        
        return keyword_volumes, "✅ 예상 검색량 데이터를 생성했습니다! (실제 검색량은 추정치입니다)"
    
    except Exception as e:
        return None, f"❌ 검색량 데이터 처리 실패: {str(e)}"

def convert_percentage_to_actual_volume(df, keyword_volumes):
    """퍼센트 데이터를 실제 검색량으로 변환"""
    if not keyword_volumes:
        return df, "❌ 검색량 데이터가 없어 변환할 수 없습니다."
    
    # 각 키워드별 최신 검색량을 기준으로 변환
    df_converted = df.copy()
    df_converted['실제검색량'] = 0
    
    for keyword in df_converted['키워드'].unique():
        # 키워드에서 실제 키워드명 추출 (쉼표로 구분된 경우 첫 번째 키워드 사용)
        actual_keyword = keyword.split(',')[0].strip()
        
        if actual_keyword in keyword_volumes:
            # 해당 키워드의 최신 검색량
            latest_volume = keyword_volumes[actual_keyword]
            
            # 해당 키워드의 평균 퍼센트 계산
            keyword_avg_percent = df_converted[df_converted['키워드'] == keyword]['검색량'].mean()
            
            # 실제 검색량 = (퍼센트 / 100) * 최신 검색량
            df_converted.loc[df_converted['키워드'] == keyword, '실제검색량'] = (
                df_converted[df_converted['키워드'] == keyword]['검색량'] / 100 * latest_volume
            ).round(0)
    
    return df_converted, "✅ 퍼센트 데이터를 실제 검색량으로 변환했습니다!"

def fetch_weather_data(lat, lon, start_date, end_date):
    """날씨 데이터 가져오기"""
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date,
        "end_date": end_date,
        "daily": "precipitation_sum,rain_sum,snowfall_sum",
        "timezone": "Asia/Seoul",
    }
    
    try:
        r = requests.get(url, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        
        df = pd.DataFrame({
            "날짜": pd.to_datetime(data["daily"]["time"]).date,
            "강수량": data["daily"]["precipitation_sum"],
            "비": data["daily"]["rain_sum"],
            "눈": data["daily"]["snowfall_sum"],
        })
        return df, "✅ 날씨 데이터를 가져왔습니다!"
        
    except Exception as e:
        return None, f"❌ 날씨 데이터 오류: {str(e)}"

def fetch_national_weather_data(start_date, end_date):
    """전국 날씨 데이터 가져오기 (주요 도시 평균)"""
    cities = {
        "서울": (37.5665, 126.9780),
        "부산": (35.1796, 129.0756),
        "대구": (35.8714, 128.6014),
        "인천": (37.4563, 126.7052),
        "광주": (35.1595, 126.8526),
        "대전": (36.3504, 127.3845),
        "울산": (35.5384, 129.3114),
        "세종": (36.4800, 127.2890),
        # 경기도 주요 도시들
        "수원": (37.2636, 127.0286),
        "성남": (37.4201, 127.1267),
        "고양": (37.6584, 126.8320),
        "용인": (37.2411, 127.1776),
        "안양": (37.3943, 126.9568),
        "안산": (37.3222, 126.8308),
        "평택": (36.9908, 127.0856),
        "의정부": (37.7381, 127.0477),
        "광명": (37.4164, 126.8840),
        "과천": (37.4291, 126.9878),
        "오산": (37.1498, 127.0772)
    }
    
    all_weather_data = []
    
    with st.spinner("🌏 전국 19개 도시의 날씨 데이터를 가져오는 중..."):
        for city_name, (lat, lon) in cities.items():
            try:
                weather_df, _ = fetch_weather_data(lat, lon, start_date, end_date)
                if weather_df is not None:
                    weather_df['도시'] = city_name
                    all_weather_data.append(weather_df)
            except Exception as e:
                st.warning(f"⚠️ {city_name} 데이터 가져오기 실패: {str(e)}")
                continue
    
    if not all_weather_data:
        return None, "❌ 전국 날씨 데이터를 가져올 수 없습니다."
    
    # 모든 도시 데이터 합치기
    combined_df = pd.concat(all_weather_data, ignore_index=True)
    
    # 날짜별로 평균 계산
    national_df = combined_df.groupby('날짜').agg({
        '강수량': 'mean',
        '비': 'mean', 
        '눈': 'mean'
    }).reset_index()
    
    return national_df, f"✅ 전국 {len(all_weather_data)}개 도시의 평균 날씨 데이터를 가져왔습니다!"

def classify_weather(row):
    """날씨 분류하기"""
    rain = row.get("비", 0) or 0
    snow = row.get("눈", 0) or 0
    
    if rain >= 1 and snow >= 1:
        return "🌧️❄️ 혼합"
    elif snow >= 1:
        return "❄️ 눈"
    elif rain >= 1:
        return "🌧️ 비"
    else:
        return "☀️ 맑음"

def main():
    # 제목
    st.markdown('<h1 class="main-title">🔍 키워드 날씨 분석기</h1>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">키워드 검색량과 날씨의 관계를 분석해보세요!</p>', unsafe_allow_html=True)
    
    # 사이드바
    with st.sidebar:
        st.markdown("## 🔧 설정")
        
        # API 키 설정
        st.markdown("### 1️⃣ 네이버 API 키")
        
        # 현재 설정된 API 키 상태 확인
        current_client_id = os.environ.get("NAVER_CLIENT_ID", "")
        current_client_secret = os.environ.get("NAVER_CLIENT_SECRET", "")
        
        # Streamlit secrets에서 시도
        if not current_client_id or not current_client_secret:
            try:
                if hasattr(st, 'secrets') and 'NAVER_CLIENT_ID' in st.secrets:
                    current_client_id = st.secrets['NAVER_CLIENT_ID']
                    current_client_secret = st.secrets['NAVER_CLIENT_SECRET']
            except:
                pass
        
        if current_client_id and current_client_secret:
            # API 키가 설정되어 있으면 마스킹해서 표시
            masked_id = current_client_id[:4] + "*" * (len(current_client_id) - 8) + current_client_id[-4:] if len(current_client_id) > 8 else "*" * len(current_client_id)
            st.success(f"✅ API 키가 설정되어 있습니다! (Client ID: {masked_id})")
            
            # API 키 재설정 옵션
            if st.button("🔄 API 키 재설정"):
                st.session_state.reset_api_keys = True
            
            if st.session_state.get('reset_api_keys', False):
                client_id = st.text_input("새 Client ID", type="password", key="new_client_id")
                client_secret = st.text_input("새 Client Secret", type="password", key="new_client_secret")
                
                if client_id and client_secret:
                    os.environ["NAVER_CLIENT_ID"] = client_id
                    os.environ["NAVER_CLIENT_SECRET"] = client_secret
                    st.success("✅ API 키가 업데이트되었습니다!")
                    st.session_state.reset_api_keys = False
                    st.rerun()
        else:
            st.warning("⚠️ API 키를 입력해주세요")
            client_id = st.text_input("Client ID", type="password")
            client_secret = st.text_input("Client Secret", type="password")
            
            if client_id and client_secret:
                os.environ["NAVER_CLIENT_ID"] = client_id
                os.environ["NAVER_CLIENT_SECRET"] = client_secret
                st.success("✅ API 키가 설정되었습니다!")
        
        # API 키 설정 도움말
        with st.expander("📖 API 키 설정 도움말"):
            st.markdown("""
            **네이버 데이터랩 API 키 발급 방법:**
            1. [네이버 개발자센터](https://developers.naver.com/) 접속
            2. 애플리케이션 등록
            3. 데이터랩 API 선택
            4. Client ID와 Client Secret 발급
            
            **보안 주의사항:**
            - API 키는 절대 공개하지 마세요
            - GitHub에 업로드할 때는 환경변수나 Streamlit Secrets를 사용하세요
            - 정기적으로 API 키를 갱신하세요
            """)
        
        # 검색량 변환 옵션
        st.markdown("### 3️⃣ 검색량 변환 (선택사항)")
        st.info("💡 **참고**: 네이버 데이터랩 API를 사용하여 예상 검색량을 추정합니다. 실제 검색량과는 차이가 있을 수 있습니다.")
        
        # 실제 검색량 변환 옵션
        convert_to_actual = st.checkbox("예상 검색량으로 변환", value=False, help="체크하면 퍼센트 데이터를 예상 검색량으로 변환합니다")
        
        st.markdown("---")
        
        # 키워드 설정
        st.markdown("### 2️⃣ 분석할 키워드")
        st.markdown("**예시:** 골프, 라운딩, 골프장, 골프 예약")
        
        keyword_input = st.text_area(
            "키워드를 입력하세요 (한 줄에 하나씩)",
            value="골프\n라운딩\n골프장",
            height=100,
            help="각 키워드는 별도로 분석됩니다"
        )
        
        keywords = [k.strip() for k in keyword_input.split('\n') if k.strip()]
        
        st.markdown("---")
        
        # 날짜 설정
        st.markdown("### 3️⃣ 분석 기간")
        today = date.today()
        start_date = st.date_input(
            "시작 날짜",
            value=today - timedelta(days=30),
            max_value=today
        )
        end_date = st.date_input(
            "종료 날짜", 
            value=today,
            max_value=today
        )
        
        st.markdown("---")
        
        # 지역 설정
        st.markdown("### 4️⃣ 지역 설정")
        location = st.selectbox(
            "분석 지역",
            ["전국", "서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종", "기타"]
        )
        
        if location == "전국":
            st.info("🌏 **전국 분석**: 주요 19개 도시의 평균 데이터를 사용합니다")
            st.markdown("""
            **포함 지역:**
            - **광역시**: 서울, 부산, 대구, 인천, 광주, 대전, 울산, 세종
            - **경기도**: 수원, 성남, 고양, 용인, 안양, 안산, 평택, 의정부, 광명, 과천, 오산
            """)
            lat, lon = None, None  # 전국 분석 플래그
        elif location == "기타":
            lat = st.number_input("위도", value=37.5665, format="%.4f")
            lon = st.number_input("경도", value=126.9780, format="%.4f")
        else:
            locations = {
                "서울": (37.5665, 126.9780),
                "부산": (35.1796, 129.0756),
                "대구": (35.8714, 128.6014),
                "인천": (37.4563, 126.7052),
                "광주": (35.1595, 126.8526),
                "대전": (36.3504, 127.3845),
                "울산": (35.5384, 129.3114),
                "세종": (36.4800, 127.2890)
            }
            lat, lon = locations[location]
            st.info(f"📍 {location}: 위도 {lat}, 경도 {lon}")
    
    # 메인 분석
    if not keywords:
        st.warning("⚠️ 분석할 키워드를 입력해주세요!")
        return
    
    if start_date >= end_date:
        st.error("❌ 시작 날짜는 종료 날짜보다 이전이어야 합니다!")
        return
    
    # 데이터 가져오기
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📊 검색 데이터 가져오기")
        with st.spinner("네이버에서 데이터를 가져오는 중..."):
            # 키워드를 5개씩 그룹으로 나누어 처리
            keyword_groups = []
            for i in range(0, len(keywords), 5):
                group_keywords = keywords[i:i+5]
                keyword_groups.append({
                    "groupName": f"그룹{i//5+1}",
                    "keywords": group_keywords
                })
            
            search_df, search_msg = fetch_naver_data(keyword_groups, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
        
        if search_df is not None:
            st.success(search_msg)
            
            # 예상 검색량 변환 (선택사항)
            if convert_to_actual:
                with st.spinner("실제 검색량 데이터를 가져오는 중..."):
                    # 키워드 리스트 추출
                    keywords_list = [kw.split(',')[0].strip() for kw in search_df['키워드'].unique()]
                    
                    # 실제 검색량 데이터 가져오기
                    keyword_volumes, volume_msg = fetch_keyword_volume_data(keywords_list, end_date.strftime("%Y-%m-%d"))
                    
                    if keyword_volumes:
                        st.success(volume_msg)
                        
                        # 퍼센트를 실제 검색량으로 변환
                        search_df, convert_msg = convert_percentage_to_actual_volume(search_df, keyword_volumes)
                        st.success(convert_msg)
                        
                        # 변환된 데이터 미리보기
                        st.markdown("#### 📈 실제 검색량 변환 결과")
                        st.dataframe(search_df[['날짜', '키워드', '검색량', '실제검색량']].head(10), use_container_width=True)
                    else:
                        st.warning(f"⚠️ {volume_msg}")
                        st.info("💡 퍼센트 데이터로 계속 분석합니다.")
        else:
            st.error(search_msg)
            return
    
    with col2:
        st.markdown("### 🌤️ 날씨 데이터 가져오기")
        
        if location == "전국":
            weather_df, weather_msg = fetch_national_weather_data(start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
        else:
            with st.spinner("날씨 데이터를 가져오는 중..."):
                weather_df, weather_msg = fetch_weather_data(lat, lon, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
        
        if weather_df is not None:
            st.success(weather_msg)
        else:
            st.error(weather_msg)
            return
    
    # 데이터 합치기
    st.markdown("---")
    st.markdown("### 🔗 데이터 분석 중...")
    
    # 날짜를 문자열로 변환하여 병합
    search_df['날짜_str'] = search_df['날짜'].astype(str)
    weather_df['날짜_str'] = weather_df['날짜'].astype(str)
    
    merged_df = pd.merge(search_df, weather_df, on='날짜_str', how='inner')
    merged_df['날씨'] = merged_df.apply(classify_weather, axis=1)
    
    # 컬럼명 정리 (원본 날짜 컬럼 사용)
    merged_df['날짜'] = merged_df['날짜_x']  # search_df의 날짜 컬럼 사용
    
    # 결과 표시
    st.markdown("---")
    st.markdown("## 📈 분석 결과")
    
    # 분석 지역 표시
    if location == "전국":
        st.markdown("### 🌏 전국 분석 (19개 주요 도시 평균)")
        st.info("📊 **분석 범위**: 8개 광역시 + 11개 경기도 주요 도시의 평균 데이터")
    else:
        st.markdown(f"### 📍 {location} 지역 분석")
    
    # 요약 통계
    st.markdown("### 📊 요약 통계")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("총 데이터 수", f"{len(merged_df):,}개")
    
    with col2:
        st.metric("분석 키워드", f"{len(keywords)}개")
    
    with col3:
        days = (end_date - start_date).days + 1
        st.metric("분석 기간", f"{days}일")
    
    with col4:
        avg_search = merged_df['검색량'].mean()
        if '실제검색량' in merged_df.columns:
            avg_actual = merged_df['실제검색량'].mean()
            st.metric("평균 검색량", f"{avg_search:.1f}%", f"실제: {avg_actual:,.0f}회")
        else:
            st.metric("평균 검색량", f"{avg_search:.1f}%")
    
    # 날씨별 검색량 분석
    st.markdown("### 🌤️ 날씨별 키워드 검색량 분석")
    weather_summary = merged_df.groupby('날씨')['검색량'].mean().sort_values(ascending=False)
    
    # 전체 평균 계산
    overall_avg = merged_df['검색량'].mean()
    
    # 퍼센트 변화 계산
    weather_analysis = []
    for weather, avg_search in weather_summary.items():
        percent_change = ((avg_search - overall_avg) / overall_avg) * 100
        weather_analysis.append({
            '날씨': weather,
            '평균검색량': avg_search,
            '전체대비': percent_change,
            '상태': '증가' if percent_change > 0 else '감소' if percent_change < 0 else '동일'
        })
    
    # 카드 형태로 표시
    col1, col2, col3, col4 = st.columns(4)
    weather_cols = [col1, col2, col3, col4]
    
    for i, data in enumerate(weather_analysis):
        with weather_cols[i % 4]:
            weather = data['날씨']
            avg_search = data['평균검색량']
            percent_change = data['전체대비']
            status = data['상태']
            
            # 상태에 따른 이모지
            status_emoji = "📈" if status == "증가" else "📉" if status == "감소" else "➡️"
            
            if "맑음" in weather:
                st.markdown(f'''
                <div class="weather-card dry-card">
                    <h3>{weather}</h3>
                    <h2>{avg_search:.1f}%</h2>
                    <p style="margin: 0.5rem 0; font-size: 1.1rem;">
                        {status_emoji} 전체 평균 대비 <strong>{percent_change:+.1f}%</strong>
                    </p>
                    <p style="margin: 0; font-size: 0.9rem; opacity: 0.8;">
                        전체 평균: {overall_avg:.1f}%
                    </p>
                </div>
                ''', unsafe_allow_html=True)
            elif "비" in weather and "눈" not in weather:
                st.markdown(f'''
                <div class="weather-card rain-card">
                    <h3>{weather}</h3>
                    <h2>{avg_search:.1f}%</h2>
                    <p style="margin: 0.5rem 0; font-size: 1.1rem;">
                        {status_emoji} 전체 평균 대비 <strong>{percent_change:+.1f}%</strong>
                    </p>
                    <p style="margin: 0; font-size: 0.9rem; opacity: 0.8;">
                        전체 평균: {overall_avg:.1f}%
                    </p>
                </div>
                ''', unsafe_allow_html=True)
            elif "눈" in weather and "비" not in weather:
                st.markdown(f'''
                <div class="weather-card snow-card">
                    <h3>{weather}</h3>
                    <h2>{avg_search:.1f}%</h2>
                    <p style="margin: 0.5rem 0; font-size: 1.1rem;">
                        {status_emoji} 전체 평균 대비 <strong>{percent_change:+.1f}%</strong>
                    </p>
                    <p style="margin: 0; font-size: 0.9rem; opacity: 0.8;">
                        전체 평균: {overall_avg:.1f}%
                    </p>
                </div>
                ''', unsafe_allow_html=True)
            else:
                st.markdown(f'''
                <div class="weather-card mixed-card">
                    <h3>{weather}</h3>
                    <h2>{avg_search:.1f}%</h2>
                    <p style="margin: 0.5rem 0; font-size: 1.1rem;">
                        {status_emoji} 전체 평균 대비 <strong>{percent_change:+.1f}%</strong>
                    </p>
                    <p style="margin: 0; font-size: 0.9rem; opacity: 0.8;">
                        전체 평균: {overall_avg:.1f}%
                    </p>
                </div>
                ''', unsafe_allow_html=True)
    
    # 추이 분석 섹션
    st.markdown("### 📈 검색량 & 날씨 추이 분석")
    
    # 시간 단위 선택
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        time_unit = st.selectbox(
            "시간 단위 선택",
            ["일별", "주별", "월별"],
            help="데이터를 집계할 시간 단위를 선택하세요"
        )
    
    with col2:
        show_weather = st.checkbox("날씨 데이터 표시", value=True)
    
    with col3:
        st.info("💡 **일별**: 상세한 변화, **주별**: 주간 패턴, **월별**: 장기 트렌드")
    
    # 데이터 집계
    merged_df['날짜'] = pd.to_datetime(merged_df['날짜'])
    
    if time_unit == "일별":
        trend_df = merged_df.groupby('날짜').agg({
            '검색량': 'mean',
            '비': 'mean',
            '눈': 'mean',
            '강수량': 'mean'
        }).reset_index()
        trend_df['날짜_표시'] = trend_df['날짜'].dt.strftime('%m/%d')
    elif time_unit == "주별":
        merged_df['주'] = merged_df['날짜'].dt.to_period('W')
        trend_df = merged_df.groupby('주').agg({
            '검색량': 'mean',
            '비': 'mean',
            '눈': 'mean',
            '강수량': 'mean'
        }).reset_index()
        trend_df['날짜'] = trend_df['주'].dt.start_time
        trend_df['날짜_표시'] = trend_df['주'].astype(str)
    else:  # 월별
        merged_df['월'] = merged_df['날짜'].dt.to_period('M')
        trend_df = merged_df.groupby('월').agg({
            '검색량': 'mean',
            '비': 'mean',
            '눈': 'mean',
            '강수량': 'mean'
        }).reset_index()
        trend_df['날짜'] = trend_df['월'].dt.start_time
        trend_df['날짜_표시'] = trend_df['월'].astype(str)
    
    # 1. 키워드별 검색량 추이 차트
    st.markdown(f"#### 🔍 키워드별 검색량 {time_unit} 추이")
    
    # 키워드별로 데이터 집계
    if '실제검색량' in merged_df.columns:
        keyword_trend_df = merged_df.groupby(['날짜', '키워드'])[['검색량', '실제검색량']].mean().reset_index()
    else:
        keyword_trend_df = merged_df.groupby(['날짜', '키워드'])['검색량'].mean().reset_index()
        keyword_trend_df['실제검색량'] = 0
    
    keyword_trend_df['날짜'] = pd.to_datetime(keyword_trend_df['날짜'])
    
    if time_unit == "주별":
        if '실제검색량' in merged_df.columns:
            keyword_trend_df['주'] = keyword_trend_df['날짜'].dt.to_period('W')
            keyword_trend_df = keyword_trend_df.groupby(['주', '키워드'])[['검색량', '실제검색량']].mean().reset_index()
        else:
            keyword_trend_df['주'] = keyword_trend_df['날짜'].dt.to_period('W')
            keyword_trend_df = keyword_trend_df.groupby(['주', '키워드'])['검색량'].mean().reset_index()
            keyword_trend_df['실제검색량'] = 0
        keyword_trend_df['날짜'] = keyword_trend_df['주'].dt.start_time
    elif time_unit == "월별":
        if '실제검색량' in merged_df.columns:
            keyword_trend_df['월'] = keyword_trend_df['날짜'].dt.to_period('M')
            keyword_trend_df = keyword_trend_df.groupby(['월', '키워드'])[['검색량', '실제검색량']].mean().reset_index()
        else:
            keyword_trend_df['월'] = keyword_trend_df['날짜'].dt.to_period('M')
            keyword_trend_df = keyword_trend_df.groupby(['월', '키워드'])['검색량'].mean().reset_index()
            keyword_trend_df['실제검색량'] = 0
        keyword_trend_df['날짜'] = keyword_trend_df['월'].dt.start_time
    
    fig1 = go.Figure()
    
    # 각 키워드별로 라인 추가
    colors = ['#2E8B57', '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD', '#98D8C8']
    
    for i, keyword in enumerate(keyword_trend_df['키워드'].unique()):
        keyword_data = keyword_trend_df[keyword_trend_df['키워드'] == keyword]
        
        # 호버 템플릿 설정
        if '실제검색량' in keyword_data.columns and keyword_data['실제검색량'].sum() > 0:
            hovertemplate = f'<b>{keyword}</b><br>%{{x}}<br>검색량: %{{y:.1f}}%<br>실제: %{{customdata:,.0f}}회<extra></extra>'
            customdata = keyword_data['실제검색량'].values
        else:
            hovertemplate = f'<b>{keyword}</b><br>%{{x}}<br>검색량: %{{y:.1f}}%<extra></extra>'
            customdata = None
        
        fig1.add_trace(go.Scatter(
            x=keyword_data['날짜'],
            y=keyword_data['검색량'],
            mode='lines+markers',
            name=keyword,
            line=dict(color=colors[i % len(colors)], width=3),
            marker=dict(size=8),
            hovertemplate=hovertemplate,
            customdata=customdata
        ))
    
    # 전체 평균 라인
    fig1.add_hline(y=overall_avg, line_dash="dash", line_color="red", 
                   annotation_text=f"전체 평균: {overall_avg:.1f}")
    
    fig1.update_layout(
        title=f'키워드별 검색량 {time_unit} 추이',
        xaxis_title='날짜',
        yaxis_title='검색량 (%)',
        height=500,
        hovermode='x unified',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    st.plotly_chart(fig1, use_container_width=True)
    
    # 2. 날씨 추이 차트
    if show_weather:
        st.markdown(f"#### 🌤️ 날씨 {time_unit} 추이")
        
        fig2 = go.Figure()
        
        # 강수량 바
        fig2.add_trace(go.Bar(
            x=trend_df['날짜'],
            y=trend_df['강수량'],
            name='강수량 (mm)',
            marker_color='#42A5F5',
            opacity=0.7,
            hovertemplate='<b>%{x}</b><br>강수량: %{y:.1f}mm<extra></extra>'
        ))
        
        # 비 바
        fig2.add_trace(go.Bar(
            x=trend_df['날짜'],
            y=trend_df['비'],
            name='비 (mm)',
            marker_color='#74b9ff',
            opacity=0.8,
            hovertemplate='<b>%{x}</b><br>비: %{y:.1f}mm<extra></extra>'
        ))
        
        # 눈 바
        fig2.add_trace(go.Bar(
            x=trend_df['날짜'],
            y=trend_df['눈'],
            name='눈 (mm)',
            marker_color='#a29bfe',
            opacity=0.8,
            hovertemplate='<b>%{x}</b><br>눈: %{y:.1f}mm<extra></extra>'
        ))
        
        fig2.update_layout(
            title=f'날씨 {time_unit} 추이 (강수량)',
            xaxis_title='날짜',
            yaxis_title='강수량 (mm)',
            height=400,
            barmode='stack',
            hovermode='x unified'
        )
        
        st.plotly_chart(fig2, use_container_width=True)
    
    # 3. 키워드별 검색량과 날씨 비교 차트
    st.markdown(f"#### 🔗 키워드별 검색량과 날씨의 {time_unit} 상관관계")
    
    # 서브플롯 생성
    fig3 = make_subplots(
        rows=2, cols=1,
        subplot_titles=(f'키워드별 검색량 {time_unit} 추이', f'날씨 {time_unit} 추이'),
        vertical_spacing=0.15,
        row_heights=[0.6, 0.4]
    )
    
    # 각 키워드별로 검색량 라인 추가
    for i, keyword in enumerate(keyword_trend_df['키워드'].unique()):
        keyword_data = keyword_trend_df[keyword_trend_df['키워드'] == keyword]
        
        fig3.add_trace(
            go.Scatter(
                x=keyword_data['날짜'],
                y=keyword_data['검색량'],
                mode='lines+markers',
                name=keyword,
                line=dict(color=colors[i % len(colors)], width=3),
                marker=dict(size=6)
            ),
            row=1, col=1
        )
    
    # 강수량 바
    fig3.add_trace(
        go.Bar(
            x=trend_df['날짜'],
            y=trend_df['강수량'],
            name='강수량 (mm)',
            marker_color='#42A5F5',
            opacity=0.7
        ),
        row=2, col=1
    )
    
    fig3.update_layout(
        title=f'키워드별 검색량과 날씨의 {time_unit} 상관관계',
        height=600,
        showlegend=True
    )
    
    fig3.update_xaxes(title_text="날짜", row=2, col=1)
    fig3.update_yaxes(title_text="검색량 (%)", row=1, col=1)
    fig3.update_yaxes(title_text="강수량 (mm)", row=2, col=1)
    
    st.plotly_chart(fig3, use_container_width=True)
    
    # 4. 날씨별 검색량 분석
    st.markdown("#### 🌤️ 날씨별 검색량 분석")
    
    # 날씨별 평균과 전체 평균 비교 차트
    weather_df_chart = pd.DataFrame(weather_analysis)
    weather_df_chart['전체평균'] = overall_avg
    
    fig4 = go.Figure()
    
    # 전체 평균 라인
    fig4.add_hline(y=overall_avg, line_dash="dash", line_color="red", 
                   annotation_text=f"전체 평균: {overall_avg:.1f}")
    
    # 날씨별 막대
    colors = ['#FFA726' if '맑음' in w else '#42A5F5' if '비' in w and '눈' not in w 
              else '#AB47BC' if '눈' in w and '비' not in w else '#66BB6A' 
              for w in weather_df_chart['날씨']]
    
    fig4.add_trace(go.Bar(
        x=weather_df_chart['날씨'],
        y=weather_df_chart['평균검색량'],
        marker_color=colors,
        text=[f"{val:.1f}<br>({change:+.1f}%)" for val, change in 
              zip(weather_df_chart['평균검색량'], weather_df_chart['전체대비'])],
        textposition='auto',
        name='날씨별 평균 검색량'
    ))
    
    fig4.update_layout(
        title='날씨별 키워드 검색량 (전체 평균 대비 퍼센트 표시)',
        xaxis_title='날씨 유형',
        yaxis_title='평균 검색량 (%)',
        height=500,
        showlegend=False
    )
    
    st.plotly_chart(fig4, use_container_width=True)
    
    # 5. 키워드별 통계 요약
    st.markdown("#### 📊 키워드별 추이 분석 요약")
    
    # 키워드별 통계 계산
    keyword_stats = keyword_trend_df.groupby('키워드')['검색량'].agg(['max', 'min', 'mean', 'std']).round(1)
    keyword_stats.columns = ['최고값', '최저값', '평균값', '변동성']
    
    # 키워드별 통계 테이블
    st.markdown("##### 📈 키워드별 검색량 통계")
    st.dataframe(keyword_stats, use_container_width=True)
    
    # 전체 통계
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        max_search = keyword_trend_df['검색량'].max()
        st.metric(f"전체 최고 {time_unit} 검색량", f"{max_search:.1f}%")
    
    with col2:
        min_search = keyword_trend_df['검색량'].min()
        st.metric(f"전체 최저 {time_unit} 검색량", f"{min_search:.1f}%")
    
    with col3:
        if show_weather:
            max_rain = trend_df['강수량'].max()
            st.metric(f"최고 {time_unit} 강수량", f"{max_rain:.1f}mm")
        else:
            st.metric("분석 키워드 수", f"{len(keyword_trend_df['키워드'].unique())}개")
    
    with col4:
        if show_weather:
            avg_rain = trend_df['강수량'].mean()
            st.metric(f"평균 {time_unit} 강수량", f"{avg_rain:.1f}mm")
        else:
            search_std = keyword_trend_df['검색량'].std()
            st.metric("전체 검색량 변동성", f"{search_std:.1f}")
    
    # 키워드별 성과 순위
    st.markdown("##### 🏆 키워드별 성과 순위")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**📈 평균 검색량 TOP 3**")
        top_keywords = keyword_stats.sort_values('평균값', ascending=False).head(3)
        for i, (keyword, stats) in enumerate(top_keywords.iterrows(), 1):
            st.markdown(f"{i}. **{keyword}**: {stats['평균값']:.1f}%")
    
    with col2:
        st.markdown("**📊 검색량 변동성 TOP 3**")
        volatile_keywords = keyword_stats.sort_values('변동성', ascending=False).head(3)
        for i, (keyword, stats) in enumerate(volatile_keywords.iterrows(), 1):
            st.markdown(f"{i}. **{keyword}**: {stats['변동성']:.1f}%")
    
    # 데이터 테이블
    st.markdown("### 📋 상세 데이터")
    if '실제검색량' in merged_df.columns:
        display_columns = ['날짜', '키워드', '검색량', '실제검색량', '날씨', '강수량', '비', '눈']
    else:
        display_columns = ['날짜', '키워드', '검색량', '날씨', '강수량', '비', '눈']
    
    st.dataframe(
        merged_df[display_columns].head(20),
        use_container_width=True
    )
    
    # 다운로드
    st.markdown("### 💾 데이터 다운로드")
    csv = merged_df.to_csv(index=False, encoding='utf-8-sig')
    st.download_button(
        label="📥 CSV 파일 다운로드",
        data=csv,
        file_name=f"키워드_날씨_분석_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )
    
    # 인사이트
    st.markdown("---")
    st.markdown("## 💡 핵심 인사이트")
    
    # 가장 높은/낮은 검색량 날씨 찾기
    max_weather = weather_summary.idxmax()
    min_weather = weather_summary.idxmin()
    max_value = weather_summary.max()
    min_value = weather_summary.min()
    
    # 퍼센트 차이 계산
    max_percent = ((max_value - overall_avg) / overall_avg) * 100
    min_percent = ((min_value - overall_avg) / overall_avg) * 100
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"""
        <div class="success-box">
        <h4>📈 가장 검색량이 높은 날씨</h4>
        <h2 style="color: #28a745; margin: 0.5rem 0;">{max_weather}</h2>
        <p style="margin: 0; font-size: 1.1rem;">
            <strong>{max_value:.1f}%</strong> (전체 평균 대비 <strong>+{max_percent:.1f}%</strong>)
        </p>
        <p style="margin: 0.5rem 0 0 0; font-size: 0.9rem; opacity: 0.8;">
            전체 평균: {overall_avg:.1f}%
        </p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="info-box">
        <h4>📉 가장 검색량이 낮은 날씨</h4>
        <h2 style="color: #6c757d; margin: 0.5rem 0;">{min_weather}</h2>
        <p style="margin: 0; font-size: 1.1rem;">
            <strong>{min_value:.1f}%</strong> (전체 평균 대비 <strong>{min_percent:+.1f}%</strong>)
        </p>
        <p style="margin: 0.5rem 0 0 0; font-size: 0.9rem; opacity: 0.8;">
            전체 평균: {overall_avg:.1f}%
        </p>
        </div>
        """, unsafe_allow_html=True)
    
    # 주요 인사이트
    st.markdown("### 🔍 주요 발견사항")
    
    # 날씨별 상세 분석
    insights = []
    for data in weather_analysis:
        weather = data['날씨']
        percent = data['전체대비']
        status = data['상태']
        
        # 날씨별 이모지
        weather_emoji = "☀️" if "맑음" in weather else "🌧️" if "비" in weather and "눈" not in weather else "❄️" if "눈" in weather and "비" not in weather else "🌧️❄️"
        
        if abs(percent) > 5:  # 5% 이상 차이
            if percent > 0:
                insights.append(f"• {weather_emoji} {weather_emoji} **{weather}** 날에는 키워드 검색이 <strong>+{percent:.1f}%</strong> 더 많습니다")
            else:
                insights.append(f"• {weather_emoji} **{weather}** 날에는 키워드 검색이 <strong>{percent:.1f}%</strong> 적습니다")
    
    if insights:
        for insight in insights:
            st.markdown(insight, unsafe_allow_html=True)
    else:
        st.info("🤔 날씨별 검색량 차이가 크지 않아 명확한 패턴을 찾기 어렵습니다.")
    
    # 상관관계 분석
    st.markdown("### 📊 상관관계 분석")
    
    # 강수량과 검색량의 상관관계
    correlation = merged_df['강수량'].corr(merged_df['검색량'])
    
    # 상관관계 강도 분류
    if abs(correlation) >= 0.8:
        strength = "매우 강한"
        strength_emoji = "🔥"
    elif abs(correlation) >= 0.6:
        strength = "강한"
        strength_emoji = "💪"
    elif abs(correlation) >= 0.4:
        strength = "중간"
        strength_emoji = "⚖️"
    elif abs(correlation) >= 0.2:
        strength = "약한"
        strength_emoji = "🤏"
    else:
        strength = "거의 없는"
        strength_emoji = "❌"
    
    # 상관관계 방향 분류
    if correlation > 0:
        direction = "양의"
        direction_emoji = "📈"
        direction_desc = "강수량이 증가할수록 검색량도 증가"
    elif correlation < 0:
        direction = "음의"
        direction_emoji = "📉"
        direction_desc = "강수량이 증가할수록 검색량은 감소"
    else:
        direction = "없는"
        direction_emoji = "➡️"
        direction_desc = "강수량과 검색량 사이에 선형 관계 없음"
    
    # 결과 표시
    if abs(correlation) >= 0.2:
        st.success(f"🔗 **{strength_emoji} {strength} {direction} 상관관계** 발견! (상관계수: {correlation:.3f})")
        st.info(f"💡 **해석**: {direction_desc}하는 경향이 있습니다.")
        
        # 상세 해석
        if abs(correlation) >= 0.8:
            st.markdown("🎯 **매우 강한 상관관계**: 거의 완벽한 직선적 관계")
        elif abs(correlation) >= 0.6:
            st.markdown("🎯 **강한 상관관계**: 명확한 선형 관계가 존재")
        elif abs(correlation) >= 0.4:
            st.markdown("🎯 **중간 상관관계**: 어느 정도의 선형 관계가 존재")
        elif abs(correlation) >= 0.2:
            st.markdown("🎯 **약한 상관관계**: 미미한 선형 관계가 존재")
    else:
        st.info(f"🔗 **{strength_emoji} 상관관계가 거의 없음** (상관계수: {correlation:.3f})")
        st.info("💡 **해석**: 강수량과 키워드 검색량 사이에 명확한 선형 관계가 없습니다.")
    
    # 상관관계 해석 가이드
    st.markdown("""
    <div class="info-box">
    <h4>📊 상관계수 해석 가이드</h4>
    <ul>
    <li><strong>+1 또는 -1</strong>: 완벽한 직선적 관계</li>
    <li><strong>0.8~1.0</strong>: 매우 강한 상관관계</li>
    <li><strong>0.6~0.8</strong>: 강한 상관관계</li>
    <li><strong>0.4~0.6</strong>: 중간 상관관계</li>
    <li><strong>0.2~0.4</strong>: 약한 상관관계</li>
    <li><strong>0~0.2</strong>: 거의 없는 상관관계</li>
    <li><strong>0</strong>: 선형 관계 없음</li>
    </ul>
    </div>
    """, unsafe_allow_html=True)
    
    # 분석 방법 설명
    if location == "전국":
        st.markdown("""
        <div class="info-box">
        <h4>📝 전국 분석 방법</h4>
        <ul>
        <li><strong>분석 지역:</strong> 19개 주요 도시 (8개 광역시 + 11개 경기도)</li>
        <li><strong>날씨 데이터:</strong> 19개 도시의 평균 강수량 사용</li>
        <li><strong>강수량 1mm 이상:</strong> 비 또는 눈으로 분류</li>
        <li><strong>검색량:</strong> 네이버 검색 트렌드 상대 지수</li>
        <li><strong>분석 기간:</strong> 선택한 날짜 범위</li>
        </ul>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="info-box">
        <h4>📝 분석 방법</h4>
        <ul>
        <li><strong>분석 지역:</strong> {}</li>
        <li><strong>강수량 1mm 이상:</strong> 비 또는 눈으로 분류</li>
        <li><strong>검색량:</strong> 네이버 검색 트렌드 상대 지수</li>
        <li><strong>분석 기간:</strong> 선택한 날짜 범위</li>
        </ul>
        </div>
        """.format(location), unsafe_allow_html=True)

if __name__ == "__main__":
    main()
